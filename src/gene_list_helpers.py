"""Gene list tools: identifier resolution and multi-category enrichment.

resolve_identifiers() maps a pasted list of gene identifiers (systematic or
standard names, aliases, SGDIDs, UniProtKB, NCBI Gene and RefSeq IDs, retired
or merged names) to current SGD loci.

run_list_enrichment() tests a resolved gene list for over-representation of
transcriptional regulators, phenotypes, complexes, pathways, InterPro domains
and diseases (hypergeometric test + Benjamini-Hochberg FDR, computed here from
the database), plus GO via the existing termfinder (BATTER) service.

Lookup tables and annotation sets only change on data loads, so they are built
once per process and cached for GENE_LIST_CACHE_TTL seconds.
"""
import logging
import re
import threading
import time
from collections import defaultdict
from math import exp, lgamma

from sqlalchemy import text

from .models import DBSession, run_batter_enrichment

logger = logging.getLogger(__name__)

GENE_LIST_CACHE_TTL = 86400
MAX_INPUT_IDENTIFIERS = 5000
MAX_BACKGROUND_IDS = 20000
MAX_RESULTS_PER_CATEGORY = 200

_cache = {}
_cache_lock = threading.RLock()

# Alias types usable as gene identifiers, in order of precedence. Homolog IDs
# (CGD, FungiDB, PomBase, Alliance) and shared accessions (PDB, DNA accession)
# are deliberately excluded: they do not identify a single S. cerevisiae gene.
ALIAS_MATCH_TYPES = [
    ('Uniform', 'alias'),
    ('Non-uniform', 'alias'),
    ('Retired name', 'retired name'),
    ('SGDID Secondary', 'secondary SGDID'),
    ('UniProtKB ID', 'UniProtKB ID'),
    ('Gene ID', 'NCBI Gene ID'),
    ('RefSeq protein version ID', 'RefSeq protein ID'),
    ('RefSeq nucleotide version ID', 'RefSeq nucleotide ID'),
]

# Lower number = stronger match; an identifier resolves at the strongest tier
# that has any hit.
MATCH_TIER = {
    'systematic name': 0,
    'gene name': 0,
    'SGDID': 0,
    'protein name': 1,
    'merged into': 2,
    'alias': 3,
    'retired name': 3,
    'secondary SGDID': 3,
    'UniProtKB ID': 3,
    'NCBI Gene ID': 3,
    'RefSeq protein ID': 3,
    'RefSeq nucleotide ID': 3,
}

SPLIT_RE = re.compile(r'[\s,;|]+')
VERSION_RE = re.compile(r'^(.+)\.\d+$')


def _cached(key, builder):
    entry = _cache.get(key)
    if entry and time.time() - entry[0] < GENE_LIST_CACHE_TTL:
        return entry[1]
    with _cache_lock:
        entry = _cache.get(key)
        if entry and time.time() - entry[0] < GENE_LIST_CACHE_TTL:
            return entry[1]
        value = builder()
        _cache[key] = (time.time(), value)
        return value


def split_identifiers(raw):
    """Accept a list of strings or one pasted string; return de-duplicated
    identifiers in input order."""
    if isinstance(raw, str):
        raw = [raw]
    seen = set()
    out = []
    for item in raw or []:
        for token in SPLIT_RE.split(str(item)):
            token = token.strip().strip('"\'')
            if token and token.upper() not in seen:
                seen.add(token.upper())
                out.append(token)
    return out


def _normalize(identifier):
    key = identifier.strip().upper()
    if key.startswith('SGD:'):
        key = key[4:]
    return key


def _locus_dict(row):
    return {
        'id': row['dbentity_id'],
        'sgdid': row['sgdid'],
        'systematic_name': row['systematic_name'],
        'gene_name': row['gene_name'],
        'display_name': row['display_name'],
        'qualifier': row['qualifier'],
        'description': row['description'],
        'link': row['obj_url'],
    }


def _build_lookup():
    """Return (loci, index, retired): loci maps dbentity_id -> locus dict for
    active loci; index maps an upper-cased key -> set of (dbentity_id,
    match_type); retired maps upper-cased name/SGDID of deleted or merged loci
    -> {status, systematic_name, sgdid}."""
    rows = DBSession.execute(text(
        "SELECT d.dbentity_id, d.sgdid, d.display_name, d.obj_url, d.dbentity_status, "
        "       l.systematic_name, l.gene_name, l.qualifier, l.description "
        "FROM nex.dbentity d JOIN nex.locusdbentity l ON l.dbentity_id = d.dbentity_id")).mappings().all()

    loci = {}
    index = defaultdict(set)
    retired = {}
    for row in rows:
        if row['dbentity_status'] != 'Active':
            info = {'status': row['dbentity_status'].lower(),
                    'systematic_name': row['systematic_name'],
                    'sgdid': row['sgdid']}
            for key in (row['systematic_name'], row['sgdid']):
                if key:
                    retired[key.upper()] = info
            continue
        locus_id = row['dbentity_id']
        loci[locus_id] = _locus_dict(row)
        index[row['systematic_name'].upper()].add((locus_id, 'systematic name'))
        index[row['sgdid'].upper()].add((locus_id, 'SGDID'))
        if row['gene_name']:
            index[row['gene_name'].upper()].add((locus_id, 'gene name'))
            # Protein names as written in papers, e.g. Act1p
            index[row['gene_name'].upper() + 'P'].add((locus_id, 'protein name'))

    match_type_by_alias = dict(ALIAS_MATCH_TYPES)
    alias_rows = DBSession.execute(text(
        "SELECT a.locus_id, a.display_name, a.alias_type "
        "FROM nex.locus_alias a JOIN nex.source s ON s.source_id = a.source_id "
        "WHERE a.alias_type IN :types "
        "  AND (a.alias_type <> 'Gene ID' OR s.display_name = 'NCBI')"),
        {'types': tuple(match_type_by_alias)}).mappings().all()
    for row in alias_rows:
        if row['locus_id'] not in loci:
            continue
        match_type = match_type_by_alias[row['alias_type']]
        key = row['display_name'].strip().upper()
        index[key].add((row['locus_id'], match_type))
        # Accept RefSeq accessions with or without the version suffix
        if match_type.startswith('RefSeq'):
            m = VERSION_RE.match(key)
            if m:
                index[m.group(1)].add((row['locus_id'], match_type))

    # A merged locus' old systematic name / SGDID is kept as an alias of the
    # surviving locus; record that as a "merged into" match.
    for key, info in retired.items():
        if info['status'] != 'merged':
            continue
        successors = {locus_id for locus_id, _ in index.get(key, ())}
        for locus_id in successors:
            index[key].add((locus_id, 'merged into'))

    return loci, dict(index), retired


def get_lookup():
    return _cached('lookup', _build_lookup)


def resolve_identifiers(raw_identifiers):
    """Resolve identifiers to active SGD loci.

    Each result row has status 'matched', 'ambiguous', 'retired' or
    'not_found'. A matched name that is also an alias of other genes carries
    those genes in 'also_alias_of' so users can double-check.
    """
    identifiers = split_identifiers(raw_identifiers)
    if len(identifiers) > MAX_INPUT_IDENTIFIERS:
        raise ValueError('At most %d identifiers are allowed; got %d' % (MAX_INPUT_IDENTIFIERS, len(identifiers)))

    loci, index, retired = get_lookup()
    results = []
    resolved_ids = []
    seen_ids = set()
    counts = defaultdict(int)

    for identifier in identifiers:
        key = _normalize(identifier)
        hits = index.get(key, set())
        row = {'input': identifier, 'status': 'not_found', 'match_type': None, 'loci': [], 'also_alias_of': []}
        if hits:
            best_tier = min(MATCH_TIER[match_type] for _, match_type in hits)
            best = {}
            for locus_id, match_type in hits:
                if MATCH_TIER[match_type] == best_tier:
                    best.setdefault(locus_id, match_type)
            row['loci'] = sorted((loci[i] for i in best), key=lambda x: x['systematic_name'])
            row['match_type'] = sorted(set(best.values()))[0]
            if len(best) == 1:
                row['status'] = 'matched'
                others = {locus_id for locus_id, match_type in hits
                          if locus_id not in best and match_type == 'alias'}
                row['also_alias_of'] = sorted((loci[i] for i in others), key=lambda x: x['systematic_name'])
                locus_id = next(iter(best))
                if locus_id not in seen_ids:
                    seen_ids.add(locus_id)
                    resolved_ids.append(locus_id)
            else:
                row['status'] = 'ambiguous'
        elif key in retired:
            row['status'] = 'retired'
            row['match_type'] = retired[key]['status']
            row['retired'] = retired[key]
        counts[row['status']] += 1
        results.append(row)

    return {
        'summary': {
            'total': len(identifiers),
            'matched': counts['matched'],
            'ambiguous': counts['ambiguous'],
            'retired': counts['retired'],
            'not_found': counts['not_found'],
            'unique_loci': len(resolved_ids),
        },
        'resolved_ids': resolved_ids,
        'results': results,
    }


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

# Each query returns (term_id, term_name, term_link, locus_id).
ENRICHMENT_CATEGORIES = {
    'regulator': {
        'label': 'Transcriptional regulators',
        'description': 'Regulators with an unexpectedly high number of targets in the list',
        'sql': "SELECT r.regulator_id, d.display_name, d.obj_url, r.target_id "
               "FROM nex.regulationannotation r JOIN nex.dbentity d ON d.dbentity_id = r.regulator_id "
               "WHERE r.regulation_type = 'transcription'",
    },
    'phenotype': {
        'label': 'Phenotypes',
        'description': 'Mutant phenotypes shared by genes in the list',
        'sql': "SELECT p.phenotype_id, p.display_name, p.obj_url, a.dbentity_id "
               "FROM nex.phenotypeannotation a JOIN nex.phenotype p ON p.phenotype_id = a.phenotype_id",
    },
    'complex': {
        'label': 'Macromolecular complexes',
        'description': 'Complexes whose subunits are over-represented in the list',
        'sql': "SELECT c.complex_id, d.display_name, d.obj_url, i.locus_id "
               "FROM nex.complexbindingannotation c "
               "JOIN nex.interactor i ON i.interactor_id = c.interactor_id "
               "JOIN nex.dbentity d ON d.dbentity_id = c.complex_id "
               "WHERE i.locus_id IS NOT NULL",
    },
    'pathway': {
        'label': 'Pathways',
        'description': 'YeastPathways metabolic pathways',
        'sql': "SELECT p.pathway_id, d.display_name, d.obj_url, p.dbentity_id "
               "FROM nex.pathwayannotation p JOIN nex.dbentity d ON d.dbentity_id = p.pathway_id",
    },
    'domain': {
        'label': 'Protein domains (InterPro)',
        'description': 'InterPro entries shared by proteins in the list (S288C)',
        'sql': "SELECT pd.interpro_id, min(pd.description), NULL, a.dbentity_id "
               "FROM nex.proteindomainannotation a "
               "JOIN nex.proteindomain pd ON pd.proteindomain_id = a.proteindomain_id "
               "JOIN nex.taxonomy t ON t.taxonomy_id = a.taxonomy_id "
               "WHERE pd.interpro_id IS NOT NULL AND pd.interpro_id <> '' "
               "  AND t.display_name = 'Saccharomyces cerevisiae S288C' "
               "GROUP BY pd.interpro_id, a.dbentity_id",
    },
    'disease': {
        'label': 'Human diseases',
        'description': 'Disease Ontology terms associated with genes in the list',
        'sql': "SELECT d.disease_id, d.display_name, d.obj_url, a.dbentity_id "
               "FROM nex.diseaseannotation a JOIN nex.disease d ON d.disease_id = a.disease_id",
    },
}

GO_CATEGORIES = {
    'go_process': ('P', 'GO biological process'),
    'go_function': ('F', 'GO molecular function'),
    'go_component': ('C', 'GO cellular component'),
}

DEFAULT_CATEGORIES = ['regulator', 'phenotype', 'complex', 'pathway', 'domain', 'disease']


def list_enrichment_categories():
    cats = [{'key': k, 'label': v['label'], 'description': v['description']}
            for k, v in ENRICHMENT_CATEGORIES.items()]
    cats += [{'key': k, 'label': label, 'description': 'GO Term Finder (SGD termfinder service)'}
             for k, (_, label) in GO_CATEGORIES.items()]
    return cats


def _build_annotation_sets(category):
    """Return (terms, term_genes, annotated): terms maps term_id ->
    {id, display_name, link}; term_genes maps term_id -> frozenset of active
    locus ids; annotated is the union (the category's default background)."""
    loci = get_lookup()[0]
    terms = {}
    term_genes = defaultdict(set)
    for term_id, name, link, locus_id in DBSession.execute(text(ENRICHMENT_CATEGORIES[category]['sql'])):
        if locus_id not in loci:
            continue
        if term_id not in terms:
            if category == 'domain':
                link = 'https://www.ebi.ac.uk/interpro/entry/InterPro/%s/' % term_id
            terms[term_id] = {'id': term_id, 'display_name': name or str(term_id), 'link': link}
        term_genes[term_id].add(locus_id)
    term_genes = {t: frozenset(g) for t, g in term_genes.items()}
    annotated = frozenset().union(*term_genes.values()) if term_genes else frozenset()
    return terms, term_genes, annotated


def get_annotation_sets(category):
    return _cached('annotations:' + category, lambda: _build_annotation_sets(category))


def _log_choose(n, k):
    return lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)


def hypergeom_sf(k, N, K, n):
    """P(X >= k) for X ~ Hypergeometric(population N, K successes, n draws)."""
    upper = min(K, n)
    if k <= 0:
        return 1.0
    if k > upper:
        return 0.0
    log_total = _log_choose(N, n)
    terms = [_log_choose(K, i) + _log_choose(N - K, n - i) - log_total for i in range(k, upper + 1)]
    peak = max(terms)
    return min(1.0, exp(peak) * sum(exp(t - peak) for t in terms))


def benjamini_hochberg(pvalues, num_tests):
    """BH-adjusted q-values for pvalues (in any order), where num_tests >=
    len(pvalues) counts the untested terms (p = 1) as well."""
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    qvalues = [1.0] * len(pvalues)
    running = 1.0
    for rank in range(len(order), 0, -1):
        i = order[rank - 1]
        running = min(running, pvalues[i] * num_tests / rank)
        qvalues[i] = min(1.0, running)
    return qvalues


def enrich_category(category, gene_ids, background_ids=None, fdr_cutoff=0.05, min_overlap=2):
    terms, term_genes, annotated = get_annotation_sets(category)
    loci = get_lookup()[0]
    universe = annotated if background_ids is None else annotated & background_ids
    query = frozenset(gene_ids) & universe
    N, n = len(universe), len(query)

    tested = []
    num_tests = 0
    for term_id, genes in term_genes.items():
        genes = genes & universe if background_ids is not None else genes
        K = len(genes)
        if K == 0:
            continue
        num_tests += 1
        hits = genes & query
        if len(hits) < max(min_overlap, 1):
            continue
        tested.append((term_id, K, hits, hypergeom_sf(len(hits), N, K, n)))

    qvalues = benjamini_hochberg([t[3] for t in tested], num_tests)
    results = []
    for (term_id, K, hits, pvalue), qvalue in zip(tested, qvalues):
        if qvalue > fdr_cutoff:
            continue
        k = len(hits)
        genes = sorted((loci[i] for i in hits), key=lambda x: x['display_name'])
        results.append({
            'term': terms[term_id],
            'list_count': k,
            'list_total': n,
            'background_count': K,
            'background_total': N,
            'fold_enrichment': round((k / n) / (K / N), 2) if n and K else None,
            'pvalue': pvalue,
            'fdr': qvalue,
            'genes': [{'id': g['id'], 'display_name': g['display_name'],
                       'systematic_name': g['systematic_name'], 'link': g['link']} for g in genes],
        })
    results.sort(key=lambda r: (r['pvalue'], -r['list_count']))
    return {
        'category': category,
        'label': ENRICHMENT_CATEGORIES[category]['label'],
        'list_annotated': n,
        'list_unannotated': len(frozenset(gene_ids) - universe),
        'background_total': N,
        'terms_tested': num_tests,
        'results': results[:MAX_RESULTS_PER_CATEGORY],
        'truncated': len(results) > MAX_RESULTS_PER_CATEGORY,
    }


def enrich_go(category, gene_ids, fdr_cutoff=0.05):
    """GO enrichment through the termfinder (BATTER) service, reshaped to the
    same row format. The service uses its own background and returns
    multiple-test-corrected p-values (as strings), which are filtered by
    fdr_cutoff like the other categories."""
    aspect, label = GO_CATEGORIES[category]
    loci = get_lookup()[0]
    names = [loci[i]['systematic_name'] for i in gene_ids if i in loci]
    results = []
    for row in run_batter_enrichment(names, aspect=aspect, context='gene_list_enrichment'):
        try:
            pvalue = float(row['pvalue'])
            list_count = int(row['match_count'])
        except (TypeError, ValueError):
            continue
        if pvalue <= fdr_cutoff:
            results.append({'term': row['go'], 'list_count': list_count, 'pvalue': pvalue, 'fdr': None, 'genes': []})
    results.sort(key=lambda r: (r['pvalue'], -r['list_count']))
    return {
        'category': category,
        'label': label,
        'list_annotated': None,
        'background_total': None,
        'terms_tested': None,
        'results': results[:MAX_RESULTS_PER_CATEGORY],
        'truncated': len(results) > MAX_RESULTS_PER_CATEGORY,
        'note': 'Computed by GO Term Finder with the default genome background; p-values are '
                'multiple-test corrected by the service.',
    }


def run_list_enrichment(body):
    """Entry point for POST /gene_list/enrichment. body keys:
    bioent_ids (list of ints) or genes (identifiers to resolve);
    categories (default: all non-GO categories); background_ids or
    background_genes (optional); fdr_cutoff (default 0.05); min_overlap
    (default 2)."""
    resolution = None
    if body.get('genes'):
        resolution = resolve_identifiers(body['genes'])
        gene_ids = resolution['resolved_ids']
    else:
        gene_ids = [int(x) for x in body.get('bioent_ids') or []]
    if not gene_ids:
        raise ValueError('No genes given: pass "bioent_ids" or "genes"')
    if len(gene_ids) > MAX_INPUT_IDENTIFIERS:
        raise ValueError('At most %d genes are allowed' % MAX_INPUT_IDENTIFIERS)

    background_ids = None
    if body.get('background_genes'):
        background_ids = resolve_identifiers(body['background_genes'])['resolved_ids']
    elif body.get('background_ids'):
        background_ids = [int(x) for x in body['background_ids']]
    if background_ids is not None:
        if len(background_ids) > MAX_BACKGROUND_IDS:
            raise ValueError('At most %d background genes are allowed' % MAX_BACKGROUND_IDS)
        background_ids = frozenset(background_ids) | frozenset(gene_ids)

    categories = body.get('categories') or DEFAULT_CATEGORIES
    unknown = [c for c in categories if c not in ENRICHMENT_CATEGORIES and c not in GO_CATEGORIES]
    if unknown:
        raise ValueError('Unknown categories: %s' % ', '.join(unknown))

    fdr_cutoff = float(body.get('fdr_cutoff', 0.05))
    min_overlap = int(body.get('min_overlap', 2))
    if not 0 < fdr_cutoff <= 1:
        raise ValueError('fdr_cutoff must be in (0, 1]')

    out = {
        'gene_count': len(set(gene_ids)),
        'background': 'custom' if background_ids is not None else 'annotated genes per category',
        'fdr_cutoff': fdr_cutoff,
        'min_overlap': min_overlap,
        'categories': [],
    }
    if resolution is not None:
        out['resolution_summary'] = resolution['summary']
    for category in categories:
        if category in GO_CATEGORIES:
            out['categories'].append(enrich_go(category, gene_ids, fdr_cutoff))
        else:
            out['categories'].append(enrich_category(category, gene_ids, background_ids, fdr_cutoff, min_overlap))
    return out
