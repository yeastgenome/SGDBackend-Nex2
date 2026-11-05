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
genes of a pathway, the proteins with an InterPro domain (these four are the
gene sets the enrichment tests use), a Yeast GO-Slim term, a chemical (genes
with a mutant phenotype observed under it), a paper (its Literature Guide
genes) or a gene and its top co-expressed genes.

The GO / APO graphs and the annotations are cached per process like the
other gene list tables (see gene_list_helpers._cached).
"""
import re
from collections import defaultdict

from sqlalchemy import text

from .gene_list_helpers import MAX_INPUT_IDENTIFIERS, _cached, coexpression_partners, get_annotation_sets, get_lookup
from .models import DBSession, Disease, Go

GO_ANNOTATION_TYPES = ['manually curated', 'high-throughput', 'computational']
OBSERVABLE_ROOT = 'APO:0000017'
GOID_RE = re.compile(r'^GO:?(\d{7})$', re.IGNORECASE)
APOID_RE = re.compile(r'^APO:?(\d{7})$', re.IGNORECASE)
MAX_SUGGESTIONS = 20
DOID_RE = re.compile(r'^DOID:?(\d+)$', re.IGNORECASE)
# other categories a list can be built from (phenotype and GO have their own sources)
LIST_CATEGORIES = ('disease', 'regulator', 'complex', 'pathway', 'domain', 'goslim', 'chemical', 'paper',
                   'coexpression')
# categories small enough to list in full (an empty query returns every term)
BROWSABLE_CATEGORIES = ('goslim',)
GO_SLIM = 'Yeast GO-Slim'
GO_SLIM_ROOTS = ('biological_process', 'molecular_function', 'cellular_component')
LITERATURE_TOPICS = ('Primary Literature', 'Additional Literature', 'Reviews', 'Omics')
COEXPRESSION_TOP = (10, 25, 50, 100)
PMID_RE = re.compile(r'^(?:PMID:?\s*)?(\d{1,9})$', re.IGNORECASE)
SGDID_RE = re.compile(r'^(?:SGD:)?(S\d{9})$', re.IGNORECASE)


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


def _build_goslim():
    """Yeast GO-Slim terms (without the three ontology roots) and their genes."""
    terms = {}
    for goslim_id, name, link, goid in DBSession.execute(text(
            "SELECT s.goslim_id, s.display_name, s.obj_url, g.goid FROM nex.goslim s "
            "JOIN nex.go g ON g.go_id = s.go_id WHERE s.slim_name = :slim"), {'slim': GO_SLIM}):
        if name not in GO_SLIM_ROOTS:
            terms[goslim_id] = {'id': goid, 'display_name': name, 'link': link}
    loci = get_lookup()[0]
    annotations = defaultdict(set)
    for goslim_id, locus_id in DBSession.execute(text(
            "SELECT goslim_id, dbentity_id FROM nex.goslimannotation")):
        if goslim_id in terms and locus_id in loci:
            annotations[goslim_id].add(locus_id)
    return terms, {}, dict(annotations)


def _build_chemicals():
    """Chemicals in phenotype conditions and the genes with a mutant
    phenotype (not "normal") observed under each, keyed by lower-case name."""
    loci = get_lookup()[0]
    names = {}
    annotations = defaultdict(set)
    for name, locus_id, qualifier in DBSession.execute(text(
            "SELECT c.condition_name, a.dbentity_id, q.display_name "
            "FROM nex.phenotypeannotation_cond c "
            "JOIN nex.phenotypeannotation a ON a.annotation_id = c.annotation_id "
            "JOIN nex.phenotype p ON p.phenotype_id = a.phenotype_id "
            "LEFT JOIN nex.apo q ON q.apo_id = p.qualifier_id "
            "WHERE c.condition_class = 'chemical'")):
        if locus_id not in loci or _is_normal(qualifier) or not name:
            continue
        key = name.strip().lower()
        names.setdefault(key, name.strip())
        annotations[key].add(locus_id)
    chebi = {}
    if names:
        for name, chebiid, link in DBSession.execute(text(
                "SELECT lower(display_name), chebiid, obj_url FROM nex.chebi WHERE lower(display_name) = ANY(:names)"),
                {'names': list(names)}):
            chebi.setdefault(name, (chebiid, link))
    terms = {key: {'id': chebi.get(key, (None, None))[0], 'display_name': name, 'link': chebi.get(key, (None, None))[1]}
             for key, name in names.items()}
    return terms, {}, dict(annotations)


def _build_chemical_synonyms():
    """lower-case ChEBI synonym -> chemical key, for chemicals in phenotype
    conditions (SGD uses the ChEBI name: "rapamycin" is "sirolimus")."""
    terms = _category_sets('chemical')[0]
    by_chebi = {t['id']: key for key, t in terms.items() if t['id']}
    synonyms = {}
    if by_chebi:
        for synonym, chebiid in DBSession.execute(text(
                "SELECT lower(a.display_name), ch.chebiid FROM nex.chebi_alias a "
                "JOIN nex.chebi ch ON ch.chebi_id = a.chebi_id "
                "WHERE a.alias_type IN ('EXACT', 'RELATED') AND length(a.display_name) <= 60 "
                "  AND ch.chebiid = ANY(:ids)"), {'ids': list(by_chebi)}):
            if synonym not in terms:
                synonyms.setdefault(synonym, by_chebi[chebiid])
    return synonyms


def _chemical_synonyms():
    return _cached('chemical_synonyms', _build_chemical_synonyms)


def _category_sets(category):
    """(terms, children, annotations) for a list category; only disease has
    a hierarchy."""
    if category not in LIST_CATEGORIES or category in ('paper', 'coexpression'):
        raise ValueError('Unknown category: %s' % category)
    if category == 'disease':
        return get_diseases()
    if category == 'goslim':
        return _cached('goslim_terms', _build_goslim)
    if category == 'chemical':
        return _cached('chemical_terms', _build_chemicals)
    terms, term_genes, _ = get_annotation_sets(category)
    return terms, {}, term_genes


def _term_label(category, term):
    # the regulator, complex and pathway terms are named, not numbered
    return term['id'] if category in ('disease', 'domain', 'goslim', 'chemical') else None


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
    if category == 'chemical' and lowered in _chemical_synonyms():
        return _chemical_synonyms()[lowered]
    raise LookupError('Term not found: %s' % query)


def search_category_terms(category, query):
    """Term suggestions for a category, ranked like search_go_terms, with the
    number of genes (for disease including descendant terms). For GO slim an
    empty query lists every term."""
    if category == 'paper':
        return search_papers(query)
    if category == 'coexpression':
        return search_genes(query)
    terms, children, annotations = _category_sets(category)
    q = (query or '').strip().lower()
    if not q and category in BROWSABLE_CATEGORIES:
        out = [dict(t, key=str(term_id), accession=_term_label(category, t), gene_count=len(annotations[term_id]))
               for term_id, t in terms.items() if annotations.get(term_id)]
        return sorted(out, key=lambda t: t['display_name'].lower())
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
    matched = {}
    if category == 'chemical':
        # an exact synonym ranks right after an exact name, other synonym
        # matches after all name matches; each chemical once
        found = {term_id for _, _, _, term_id in hits}
        for synonym, key in sorted(_chemical_synonyms().items(), key=lambda x: (x[0] != q, len(x[0]))):
            pos = synonym.find(q)
            if pos >= 0 and key not in found:
                found.add(key)
                matched[key] = synonym
                hits.append((0.5 if synonym == q else 3 if pos == 0 else 4, len(synonym), synonym, key))
    hits.sort()
    out = []
    for _, _, _, term_id in hits:
        locus_ids = set()
        for i in _walk(term_id, children):
            locus_ids |= annotations.get(i, set())
        if locus_ids:
            out.append(dict(terms[term_id], key=str(term_id), accession=_term_label(category, terms[term_id]),
                            gene_count=len(locus_ids), synonym=matched.get(term_id)))
        if len(out) == MAX_SUGGESTIONS:
            break
    return out


def category_term_genes(category, term, include_descendants=True, topic=None, top=25):
    """Genes of one term in a list category (disease term by DOID or name;
    regulator, complex or pathway by name; domain by InterPro ID or name;
    GO slim term by GO ID or name; chemical by name or ChEBI ID; paper by
    PMID or SGDID, optionally one literature topic; a gene and its top
    co-expressed genes)."""
    if category == 'paper':
        return paper_genes(term, topic)
    if category == 'coexpression':
        return coexpressed_genes(term, top)
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


# ---------------------------------------------------------------------------
# Papers (Literature Guide) and co-expressed genes

def _paper_where(query):
    """SQL condition and parameters selecting references for a query: a
    PMID, an SGDID, or text in the citation."""
    m = PMID_RE.match(query)
    if m:
        return "r.pmid = :pmid", {'pmid': int(m.group(1))}
    m = SGDID_RE.match(query)
    if m:
        return "d.sgdid = :sgdid", {'sgdid': m.group(1).upper()}
    return "r.citation ILIKE :text", {'text': '%' + query.replace('%', '').replace('_', '\\_') + '%'}


def _paper_term(row):
    return {'id': 'PMID:%s' % row.pmid if row.pmid else row.sgdid, 'display_name': row.display_name,
            'link': row.obj_url, 'citation': row.citation, 'key': 'ref:%d' % row.dbentity_id,
            'accession': 'PMID:%s' % row.pmid if row.pmid else row.sgdid}


def search_papers(query):
    """Papers with Literature Guide genes matching a PMID, SGDID or citation
    text (at least 4 characters), newest first."""
    query = (query or '').strip()
    if not PMID_RE.match(query) and not SGDID_RE.match(query) and len(query) < 4:
        return []
    where, params = _paper_where(query)
    loci = get_lookup()[0]
    out = []
    for row in DBSession.execute(text(
            "SELECT r.dbentity_id, d.sgdid, d.display_name, d.obj_url, r.pmid, r.citation, r.year, "
            "       array_agg(DISTINCT l.dbentity_id) AS genes "
            "FROM nex.referencedbentity r JOIN nex.dbentity d ON d.dbentity_id = r.dbentity_id "
            "JOIN nex.literatureannotation l ON l.reference_id = r.dbentity_id "
            "WHERE " + where + " GROUP BY 1, 2, 3, 4, 5, 6, 7 ORDER BY r.year DESC NULLS LAST, 1 DESC LIMIT :limit"),
            dict(params, limit=MAX_SUGGESTIONS * 2)):
        gene_count = sum(1 for g in row.genes if g in loci)
        if gene_count:
            out.append(dict(_paper_term(row), gene_count=gene_count))
        if len(out) == MAX_SUGGESTIONS:
            break
    return out


def paper_genes(term, topic=None):
    """Genes the Literature Guide links to a paper (by its suggestion key,
    PMID or SGDID), optionally only for one topic."""
    if topic and topic not in LITERATURE_TOPICS:
        raise ValueError('Unknown literature topic: %s' % topic)
    query = (term or '').strip()
    if query.lower().startswith('ref:') and query[4:].isdigit():
        # the key of a suggestion
        where, params = "r.dbentity_id = :ref", {'ref': int(query[4:])}
    elif PMID_RE.match(query) or SGDID_RE.match(query):
        where, params = _paper_where(query)
    else:
        raise LookupError('Give a PMID or SGDID for the paper: %s' % query)
    row = DBSession.execute(text(
        "SELECT r.dbentity_id, d.sgdid, d.display_name, d.obj_url, r.pmid, r.citation "
        "FROM nex.referencedbentity r JOIN nex.dbentity d ON d.dbentity_id = r.dbentity_id WHERE " + where +
        " LIMIT 1"), params).fetchone()
    if row is None:
        raise LookupError('Paper not found: %s' % query)
    sql = "SELECT DISTINCT dbentity_id FROM nex.literatureannotation WHERE reference_id = :ref"
    if topic:
        sql += " AND topic = :topic"
    locus_ids = {r[0] for r in DBSession.execute(text(sql), {'ref': row.dbentity_id, 'topic': topic})}
    return {
        'source': 'paper',
        'term': _paper_term(row),
        'include_descendants': False,
        'term_count': 1,
        'topic': topic,
        'genes': _locus_list(locus_ids),
    }


def search_genes(query):
    """Gene name / systematic name suggestions (for co-expressed genes)."""
    q = (query or '').strip().upper()
    if len(q) < 2:
        return []
    hits = []
    for locus_id, locus in get_lookup()[0].items():
        names = [n.upper() for n in (locus['gene_name'], locus['systematic_name']) if n]
        if not any(n.startswith(q) for n in names):
            continue
        rank = 0 if q in names else 1
        hits.append((rank, len(locus['display_name']), locus['display_name'], locus_id))
    hits.sort()
    loci = get_lookup()[0]
    return [{'id': loci[i]['systematic_name'], 'display_name': loci[i]['display_name'], 'link': loci[i]['link'],
             'key': loci[i]['sgdid'], 'description': loci[i]['description'],
             'accession': loci[i]['systematic_name'] if loci[i]['gene_name'] else None, 'gene_count': None}
            for _, _, _, i in hits[:MAX_SUGGESTIONS]]


def coexpressed_genes(term, top=25):
    """A gene and its top co-expressed genes (by gene name, systematic name
    or SGDID)."""
    try:
        top = int(top)
    except (TypeError, ValueError):
        raise ValueError('top must be a number')
    if top not in COEXPRESSION_TOP:
        raise ValueError('top must be one of %s' % ', '.join(str(t) for t in COEXPRESSION_TOP))
    loci, index, _ = get_lookup()
    query = (term or '').strip().upper()
    by_sgdid = {locus['sgdid']: i for i, locus in loci.items()}
    if query in by_sgdid:
        gene_id = by_sgdid[query]
    else:
        matches = {locus_id for locus_id, match in index.get(query, ()) if match in (
            'gene name', 'systematic name', 'SGDID', 'protein name')}
        if len(matches) != 1:
            raise LookupError('Gene not found: %s' % term)
        gene_id = matches.pop()
    gene = loci[gene_id]
    partners = coexpression_partners([gene['sgdid']])[gene['sgdid']]
    if not partners:
        raise LookupError('No co-expression data for %s' % gene['display_name'])
    locus_ids = [gene_id] + [by_sgdid[p] for p, _, _ in partners[:top] if p in by_sgdid]
    return {
        'source': 'coexpression',
        'term': {'id': gene['systematic_name'], 'display_name': gene['display_name'], 'link': gene['link'],
                 'key': gene['sgdid'], 'accession': gene['systematic_name'] if gene['gene_name'] else None},
        'include_descendants': False,
        'term_count': 1,
        'top': top,
        'genes': _locus_list(locus_ids),
    }
