"""Gene list tools: build a gene list from a GO term or a phenotype.

go_term_genes() lists the current SGD genes annotated to a GO term and,
optionally, to its descendant terms (following the same is a / part of /
regulates relations as the GO term pages). NOT annotations are skipped and
annotations can be limited by type (manually curated, high-throughput,
computational).

phenotype_genes() lists the genes annotated to a phenotype observable
(APO term) and, optionally, its descendants. By default results with a
"normal" qualifier (the mutant showed no phenotype) are left out.

category_term_genes() lists the genes of one term in another annotation
category: a human disease (Disease Ontology, optionally with descendants),
the targets of a transcriptional regulator, the subunits of a complex, the
genes of a pathway or the proteins with an InterPro domain. Apart from
disease these are the same gene sets the enrichment tests use.

The GO / APO graphs and the annotations are cached per process like the
other gene list tables (see gene_list_helpers._cached).
"""
import re
from collections import defaultdict

from sqlalchemy import text

from .gene_list_helpers import MAX_INPUT_IDENTIFIERS, _cached, get_annotation_sets, get_lookup
from .models import DBSession, Disease, Go

GO_ANNOTATION_TYPES = ['manually curated', 'high-throughput', 'computational']
OBSERVABLE_ROOT = 'APO:0000017'
GOID_RE = re.compile(r'^GO:?(\d{7})$', re.IGNORECASE)
APOID_RE = re.compile(r'^APO:?(\d{7})$', re.IGNORECASE)
MAX_SUGGESTIONS = 20
DOID_RE = re.compile(r'^DOID:?(\d+)$', re.IGNORECASE)
# enrichment categories a list can be built from (phenotype and GO have their own sources)
LIST_CATEGORIES = ('disease', 'regulator', 'complex', 'pathway', 'domain')


def _walk(focus_id, children):
    """Return focus_id plus every descendant in the children map."""
    seen = {focus_id}
    stack = [focus_id]
    while stack:
        for child_id in children.get(stack.pop(), ()):
            if child_id not in seen:
                seen.add(child_id)
                stack.append(child_id)
    return seen


def _locus_list(locus_ids):
    loci = get_lookup()[0]
    genes = [loci[i] for i in locus_ids if i in loci]
    genes.sort(key=lambda g: (g['gene_name'] is None, (g['gene_name'] or g['systematic_name']).upper()))
    if len(genes) > MAX_INPUT_IDENTIFIERS:
        raise ValueError('The term covers %d genes; the gene list tools take at most %d. Choose a more specific '
                         'term or leave out descendant terms.' % (len(genes), MAX_INPUT_IDENTIFIERS))
    return genes


# ---------------------------------------------------------------------------
# GO

def _build_go():
    """Return (terms, by_goid, children, annotations): terms maps go_id ->
    {goid, display_name, namespace, link}; by_goid maps 'GO:nnnnnnn' -> go_id;
    children maps go_id -> child go_ids; annotations maps go_id ->
    {annotation_type: set of active locus ids} (NOT annotations excluded)."""
    terms = {}
    by_goid = {}
    for go_id, goid, name, namespace, link in DBSession.execute(text(
            "SELECT go_id, goid, display_name, go_namespace, obj_url FROM nex.go WHERE is_obsolete = false")):
        terms[go_id] = {'id': goid, 'display_name': name, 'namespace': namespace, 'link': link}
        by_goid[goid.upper()] = go_id

    children = defaultdict(list)
    for parent_id, child_id in DBSession.execute(text(
            "SELECT parent_id, child_id FROM nex.go_relation WHERE ro_id IN :ro"),
            {'ro': tuple(Go.allowed_relationships)}):
        if parent_id in terms and child_id in terms:
            children[parent_id].append(child_id)

    loci = get_lookup()[0]
    annotations = defaultdict(lambda: defaultdict(set))
    for go_id, locus_id, annotation_type in DBSession.execute(text(
            "SELECT go_id, dbentity_id, annotation_type FROM nex.goannotation "
            "WHERE go_qualifier NOT LIKE '%NOT%'")):
        if locus_id in loci:
            annotations[go_id][annotation_type].add(locus_id)
    return terms, by_goid, dict(children), {k: dict(v) for k, v in annotations.items()}


def get_go():
    return _cached('go_terms', _build_go)


def _find_go_term(term):
    terms, by_goid, _, _ = get_go()
    term = (term or '').strip()
    m = GOID_RE.match(term)
    if m:
        go_id = by_goid.get('GO:' + m.group(1))
    else:
        lowered = term.lower()
        go_id = next((i for i, t in terms.items() if t['display_name'].lower() == lowered), None)
    if go_id is None:
        raise LookupError('GO term not found: %s' % term)
    return go_id


def go_term_genes(term, include_descendants=True, annotation_types=None):
    """Genes annotated to a GO term (GO ID or exact term name)."""
    annotation_types = annotation_types or GO_ANNOTATION_TYPES
    unknown = set(annotation_types) - set(GO_ANNOTATION_TYPES)
    if unknown:
        raise ValueError('Unknown annotation type(s): %s' % ', '.join(sorted(unknown)))
    terms, _, children, annotations = get_go()
    go_id = _find_go_term(term)
    term_ids = _walk(go_id, children) if include_descendants else {go_id}
    locus_ids = set()
    for term_id in term_ids:
        by_type = annotations.get(term_id, {})
        for annotation_type in annotation_types:
            locus_ids |= by_type.get(annotation_type, set())
    return {
        'source': 'go',
        'term': terms[go_id],
        'include_descendants': include_descendants,
        'term_count': len(term_ids),
        'annotation_types': [t for t in GO_ANNOTATION_TYPES if t in annotation_types],
        'genes': _locus_list(locus_ids),
    }


def search_go_terms(query):
    """GO term suggestions for a name or GO ID: exact match first, then names
    starting with the query, then other names containing it, shorter (broader)
    names first. Only terms with annotations (directly or below) are kept."""
    terms, by_goid, _, _ = get_go()
    query = (query or '').strip()
    m = GOID_RE.match(query)
    if m:
        go_id = by_goid.get('GO:' + m.group(1))
        return [terms[go_id]] if go_id else []
    q = query.lower()
    if len(q) < 3:
        return []
    annotated = _annotated_go_ids()
    hits = []
    for go_id, t in terms.items():
        name = t['display_name'].lower()
        pos = name.find(q)
        if pos < 0 or go_id not in annotated:
            continue
        rank = 0 if name == q else 1 if pos == 0 else 2
        hits.append((rank, len(name), name, go_id))
    hits.sort()
    return [terms[go_id] for _, _, _, go_id in hits[:MAX_SUGGESTIONS]]


def _build_annotated_go_ids():
    """go_ids with at least one annotation to the term or a descendant."""
    _, _, children, annotations = get_go()
    parents = defaultdict(list)
    for parent_id, child_ids in children.items():
        for child_id in child_ids:
            parents[child_id].append(parent_id)
    return frozenset(_walk_all(annotations.keys(), parents))


def _walk_all(start_ids, edges):
    seen = set(start_ids)
    stack = list(seen)
    while stack:
        for next_id in edges.get(stack.pop(), ()):
            if next_id not in seen:
                seen.add(next_id)
                stack.append(next_id)
    return seen


def _annotated_go_ids():
    return _cached('go_terms_annotated', _build_annotated_go_ids)


# ---------------------------------------------------------------------------
# Phenotype (APO observable)

def _build_observables():
    """Return (terms, children, annotations): terms maps apo_id -> {id,
    display_name, link}; children maps apo_id -> child apo_ids; annotations
    maps apo_id -> {qualifier or None: set of active locus ids}."""
    terms = {}
    for apo_id, apoid, name, link in DBSession.execute(text(
            "SELECT apo_id, apoid, display_name, obj_url FROM nex.apo "
            "WHERE apo_namespace = 'observable' AND is_obsolete = false")):
        terms[apo_id] = {'id': apoid, 'display_name': name, 'link': link}

    children = defaultdict(list)
    for parent_id, child_id in DBSession.execute(text("SELECT parent_id, child_id FROM nex.apo_relation")):
        if parent_id in terms and child_id in terms:
            children[parent_id].append(child_id)

    loci = get_lookup()[0]
    annotations = defaultdict(lambda: defaultdict(set))
    for observable_id, qualifier, locus_id in DBSession.execute(text(
            "SELECT p.observable_id, q.display_name, a.dbentity_id "
            "FROM nex.phenotypeannotation a "
            "JOIN nex.phenotype p ON p.phenotype_id = a.phenotype_id "
            "LEFT JOIN nex.apo q ON q.apo_id = p.qualifier_id")):
        if locus_id in loci:
            annotations[observable_id][qualifier].add(locus_id)
    return terms, dict(children), {k: dict(v) for k, v in annotations.items()}


def get_observables():
    return _cached('observable_terms', _build_observables)


def _is_normal(qualifier):
    return bool(qualifier) and qualifier.startswith('normal')


def phenotype_terms():
    """The observable tree, depth-first and sorted by name, with the number of
    genes annotated to each term or its descendants (excluding normal)."""
    return _cached('observable_term_list', _build_phenotype_terms)


def _build_phenotype_terms():
    terms, children, annotations = get_observables()
    root = next((i for i, t in terms.items() if t['id'] == OBSERVABLE_ROOT), None)
    out = []

    def gene_count(apo_id):
        locus_ids = set()
        for term_id in _walk(apo_id, children):
            for qualifier, ids in annotations.get(term_id, {}).items():
                if not _is_normal(qualifier):
                    locus_ids |= ids
        return len(locus_ids)

    def visit(apo_id, depth, path):
        for child_id in sorted(children.get(apo_id, ()), key=lambda i: terms[i]['display_name'].lower()):
            if child_id in path:
                continue
            out.append(dict(terms[child_id], depth=depth, gene_count=gene_count(child_id)))
            visit(child_id, depth + 1, path | {child_id})

    if root is not None:
        visit(root, 0, {root})
    return {'terms': out, 'qualifiers': phenotype_qualifiers()}


def phenotype_qualifiers():
    _, _, annotations = get_observables()
    counts = defaultdict(int)
    for by_qualifier in annotations.values():
        for qualifier, ids in by_qualifier.items():
            if qualifier:
                counts[qualifier] += len(ids)
    return sorted(counts, key=lambda q: -counts[q])


def _find_observable(term):
    terms, _, _ = get_observables()
    term = (term or '').strip()
    m = APOID_RE.match(term)
    lowered = term.lower()
    for apo_id, t in terms.items():
        if (m and t['id'] == 'APO:' + m.group(1)) or (not m and t['display_name'].lower() == lowered):
            return apo_id
    raise LookupError('Phenotype term not found: %s' % term)


def phenotype_genes(term, include_descendants=True, qualifier=None, include_normal=False):
    """Genes annotated to a phenotype observable (APO ID or exact name).

    qualifier limits to one qualifier (e.g. 'decreased'); otherwise "normal"
    results are left out unless include_normal is set. Annotations without a
    qualifier are kept.
    """
    terms, children, annotations = get_observables()
    apo_id = _find_observable(term)
    term_ids = _walk(apo_id, children) if include_descendants else {apo_id}
    locus_ids = set()
    for term_id in term_ids:
        for q, ids in annotations.get(term_id, {}).items():
            if qualifier:
                if q == qualifier:
                    locus_ids |= ids
            elif include_normal or not _is_normal(q):
                locus_ids |= ids
    return {
        'source': 'phenotype',
        'term': terms[apo_id],
        'include_descendants': include_descendants,
        'term_count': len(term_ids),
        'qualifier': qualifier or None,
        'include_normal': bool(include_normal) and not qualifier,
        'genes': _locus_list(locus_ids),
    }


# ---------------------------------------------------------------------------
# Human disease and the other enrichment categories

def _build_diseases():
    """Return (terms, children, annotations) for the Disease Ontology like
    _build_go: terms maps disease_id -> {id (DOID), display_name, link};
    annotations maps disease_id -> set of active locus ids (NOT excluded; most
    annotations have no qualifier)."""
    terms = {}
    for disease_id, doid, name, link in DBSession.execute(text(
            "SELECT disease_id, doid, display_name, obj_url FROM nex.disease WHERE is_obsolete = false")):
        terms[disease_id] = {'id': doid, 'display_name': name, 'link': link}

    children = defaultdict(list)
    for parent_id, child_id in DBSession.execute(text(
            "SELECT parent_id, child_id FROM nex.disease_relation WHERE ro_id IN :ro"),
            {'ro': tuple(Disease.allowed_relationships)}):
        if parent_id in terms and child_id in terms:
            children[parent_id].append(child_id)

    loci = get_lookup()[0]
    annotations = defaultdict(set)
    for disease_id, locus_id in DBSession.execute(text(
            "SELECT disease_id, dbentity_id FROM nex.diseaseannotation "
            "WHERE disease_qualifier IS NULL OR disease_qualifier NOT LIKE '%NOT%'")):
        if locus_id in loci:
            annotations[disease_id].add(locus_id)
    return terms, dict(children), dict(annotations)


def get_diseases():
    return _cached('disease_terms', _build_diseases)


def _category_sets(category):
    """(terms, children, annotations) for a list category; only disease has
    a hierarchy."""
    if category not in LIST_CATEGORIES:
        raise ValueError('Unknown category: %s' % category)
    if category == 'disease':
        return get_diseases()
    terms, term_genes, _ = get_annotation_sets(category)
    return terms, {}, term_genes


def _term_label(category, term):
    # the regulator, complex and pathway terms are named, not numbered
    return term['id'] if category in ('disease', 'domain') else None


def _find_category_term(category, term):
    terms, _, _ = _category_sets(category)
    query = (term or '').strip()
    lowered = query.lower()
    m = DOID_RE.match(query)
    if m:
        lowered = 'doid:' + m.group(1)
    for term_id, t in terms.items():
        if str(term_id) == query or t['display_name'].lower() == lowered or str(t['id']).lower() == lowered:
            return term_id
    raise LookupError('Term not found: %s' % query)


def search_category_terms(category, query):
    """Term suggestions for a category, ranked like search_go_terms, with the
    number of genes (for disease including descendant terms)."""
    terms, children, annotations = _category_sets(category)
    q = (query or '').strip().lower()
    if len(q) < 2:
        return []
    hits = []
    for term_id, t in terms.items():
        name = t['display_name'].lower()
        pos = name.find(q)
        if pos < 0 and q != str(t['id']).lower():
            continue
        rank = 0 if name == q or q == str(t['id']).lower() else 1 if pos == 0 else 2
        hits.append((rank, len(name), name, term_id))
    hits.sort()
    out = []
    for _, _, _, term_id in hits:
        locus_ids = set()
        for i in _walk(term_id, children):
            locus_ids |= annotations.get(i, set())
        if locus_ids:
            out.append(dict(terms[term_id], key=str(term_id), accession=_term_label(category, terms[term_id]),
                            gene_count=len(locus_ids)))
        if len(out) == MAX_SUGGESTIONS:
            break
    return out


def category_term_genes(category, term, include_descendants=True):
    """Genes of one term in a list category (disease term by DOID or name;
    regulator, complex or pathway by name; domain by InterPro ID or name)."""
    terms, children, annotations = _category_sets(category)
    term_id = _find_category_term(category, term)
    include_descendants = include_descendants and bool(children)
    term_ids = _walk(term_id, children) if include_descendants else {term_id}
    locus_ids = set()
    for i in term_ids:
        locus_ids |= annotations.get(i, set())
    return {
        'source': category,
        'term': dict(terms[term_id], key=str(term_id), accession=_term_label(category, terms[term_id])),
        'include_descendants': include_descendants,
        'term_count': len(term_ids),
        'genes': _locus_list(locus_ids),
    }
