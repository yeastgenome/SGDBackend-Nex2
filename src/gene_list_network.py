"""Gene list tools: a network of how the genes in a list are connected.

get_list_network() returns the genes of a list and the edges between them:

- physical / genetic: BioGRID interactions, one edge per gene pair with the
  number of supporting records and references and the experiment types
- regulation: regulator -> target edges (directed)
- coexpression: pairs where one gene is among the other's top co-expressed
  genes (the per-gene JSON on S3 written by
  scripts/loading/dataset/compute_coexpression.py)
- shared_go: pairs annotated to at least go_min_shared of the same specific
  GO terms (terms with at most GO_MAX_TERM_GENES genes), like the locus
  page "Shared Annotations" network

Optionally the genes outside the list that connect the most list genes
(physical / genetic / regulation) are added as neighbors. Networks larger
than max_edges are cut down by raising the evidence threshold, then by
keeping the strongest edges of each type; the response says what was left
out.
"""
from collections import defaultdict
from sqlalchemy import text

from .gene_list_helpers import MAX_INPUT_IDENTIFIERS, coexpression_partners, get_lookup, resolve_identifiers
from .gene_list_terms import get_go
from .models import DBSession

EDGE_TYPES = ('physical', 'genetic', 'regulation', 'coexpression', 'shared_go')
DEFAULT_EDGE_TYPES = ('physical', 'regulation')
EVIDENCE_TYPES = ('physical', 'genetic', 'regulation')
EVIDENCE_STEPS = (1, 2, 3, 5, 10, 20, 50)
SMALL_LIST = 100            # lists this small default to min_evidence 1, larger ones to 2
MAX_NEIGHBORS = 100
DEFAULT_MAX_NODES = 300
DEFAULT_MAX_EDGES = 2000
MAX_EDGES_LIMIT = 5000
MAX_COEXPRESSION_GENES = 500
GO_MAX_TERM_GENES = 100
GO_ANNOTATION_TYPES = ('manually curated', 'high-throughput')

INTERACTION_TABLES = {'physical': 'physinteractionannotation', 'genetic': 'geninteractionannotation'}


def default_min_evidence(list_size):
    return 1 if list_size < SMALL_LIST else 2


def _int(value, name, low, high):
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError('%s must be a number' % name)
    if not low <= value <= high:
        raise ValueError('%s must be between %d and %d' % (name, low, high))
    return value


def _interaction_edges(kind, ids, both_in_list):
    """{(gene1, gene2): edge} for one interaction table, gene1 < gene2."""
    where = ("a.dbentity1_id = ANY(:ids) AND a.dbentity2_id = ANY(:ids)" if both_in_list
             else "(a.dbentity1_id = ANY(:ids) OR a.dbentity2_id = ANY(:ids))")
    edges = {}
    for row in DBSession.execute(text(
            "SELECT least(a.dbentity1_id, a.dbentity2_id) AS g1, greatest(a.dbentity1_id, a.dbentity2_id) AS g2, "
            "       count(*) AS records, count(DISTINCT a.reference_id) AS refs, "
            "       array_agg(DISTINCT a.biogrid_experimental_system) AS systems, "
            "       bool_and(a.annotation_type = 'high-throughput') AS ht_only "
            "FROM nex." + INTERACTION_TABLES[kind] + " a WHERE " + where +
            " AND a.dbentity1_id <> a.dbentity2_id GROUP BY 1, 2"), {'ids': list(ids)}):
        edges[(row.g1, row.g2)] = {'type': kind, 'source': row.g1, 'target': row.g2, 'weight': row.records,
                                   'evidence': row.records, 'references': row.refs,
                                   'detail': sorted(s for s in row.systems if s), 'high_throughput_only': row.ht_only}
    return edges


def _regulation_edges(ids, both_in_list):
    """{(regulator, target): edge}."""
    where = ("regulator_id = ANY(:ids) AND target_id = ANY(:ids)" if both_in_list
             else "(regulator_id = ANY(:ids) OR target_id = ANY(:ids))")
    edges = {}
    for row in DBSession.execute(text(
            "SELECT regulator_id, target_id, count(*) AS records, count(DISTINCT reference_id) AS refs, "
            "       array_agg(DISTINCT regulation_type) AS types, array_agg(DISTINCT direction) AS directions "
            "FROM nex.regulationannotation WHERE " + where + " AND regulator_id <> target_id GROUP BY 1, 2"),
            {'ids': list(ids)}):
        directions = sorted(d for d in row.directions if d)
        edges[(row.regulator_id, row.target_id)] = {
            'type': 'regulation', 'source': row.regulator_id, 'target': row.target_id, 'weight': row.records,
            'evidence': row.records, 'references': row.refs, 'detail': sorted(t for t in row.types if t),
            'direction': directions[0] if len(directions) == 1 else ('mixed' if directions else None)}
    return edges


def _coexpression_edges(ids, loci):
    sgdids = [loci[i]['sgdid'] for i in ids]
    partners_by_gene = coexpression_partners(sgdids)
    by_sgdid = {loci[i]['sgdid']: i for i in ids}
    edges = {}
    for sgdid in sgdids:
        for partner, score, rank in partners_by_gene[sgdid]:
            if partner not in by_sgdid or partner == sgdid:
                continue
            g1, g2 = sorted((by_sgdid[sgdid], by_sgdid[partner]))
            edge = edges.get((g1, g2))
            if edge is None or score > edge['weight']:
                edges[(g1, g2)] = {'type': 'coexpression', 'source': g1, 'target': g2, 'weight': score,
                                   'score': score, 'rank': rank}
            else:
                edge['rank'] = min(edge['rank'], rank)
    return edges


def _shared_go_edges(ids, min_shared):
    terms, _, _, annotations = get_go()
    members = set(ids)
    shared = defaultdict(list)
    for go_id, by_type in annotations.items():
        genome = set().union(*by_type.values())
        if len(genome) > GO_MAX_TERM_GENES:
            continue
        in_list = set()
        for annotation_type in GO_ANNOTATION_TYPES:
            in_list |= by_type.get(annotation_type, set()) & members
        if len(in_list) < 2:
            continue
        in_list = sorted(in_list)
        for i, g1 in enumerate(in_list):
            for g2 in in_list[i + 1:]:
                shared[(g1, g2)].append((len(genome), terms[go_id]['display_name']))
    edges = {}
    for (g1, g2), go_terms in shared.items():
        if len(go_terms) < min_shared:
            continue
        go_terms.sort()
        edges[(g1, g2)] = {'type': 'shared_go', 'source': g1, 'target': g2, 'weight': len(go_terms),
                           'shared_terms': len(go_terms), 'detail': [name for _, name in go_terms[:5]]}
    return edges


def _pick_neighbors(edges, members, count, max_new):
    """Genes outside the list connected to at least two list genes, most
    connected first."""
    reach = defaultdict(set)
    evidence = defaultdict(int)
    for edge in edges:
        a, b = edge['source'], edge['target']
        for outside, inside in ((a, b), (b, a)):
            if outside not in members and inside in members:
                reach[outside].add(inside)
                evidence[outside] += edge['evidence']
    ranked = sorted((g for g in reach if len(reach[g]) >= 2), key=lambda g: (-len(reach[g]), -evidence[g], g))
    return ranked[:min(count, max_new)], {g: len(reach[g]) for g in ranked}


def _limit_edges(edges, max_edges, min_evidence):
    """Keep at most max_edges: raise the evidence threshold of the
    interaction / regulation edges first, then keep the strongest edges of
    each type in proportion to its size."""
    notes = []
    used = min_evidence
    for step in EVIDENCE_STEPS:
        if len(edges) <= max_edges:
            break
        if step <= used:
            continue
        kept = [e for e in edges if e['type'] not in EVIDENCE_TYPES or e['evidence'] >= step]
        if len(kept) == len(edges):
            continue
        edges, used = kept, step
    if used != min_evidence:
        notes.append('evidence threshold raised to %d to fit the network' % used)
    if len(edges) > max_edges:
        by_type = defaultdict(list)
        for edge in edges:
            by_type[edge['type']].append(edge)
        total = len(edges)
        edges = []
        for kind, group in by_type.items():
            group.sort(key=lambda e: -e['weight'])
            edges += group[:max(1, max_edges * len(group) // total)]
        notes.append('only the strongest edges of each type are shown')
    return edges, used, notes


def get_list_network(body):
    if body.get('genes'):
        ids = resolve_identifiers(body['genes'])['resolved_ids']
    else:
        ids = body.get('bioent_ids') or []
    if not isinstance(ids, list) or not ids:
        raise ValueError('Pass a non-empty list of bioent_ids, or genes')
    if len(ids) > MAX_INPUT_IDENTIFIERS:
        raise ValueError('At most %d genes' % MAX_INPUT_IDENTIFIERS)
    loci = get_lookup()[0]
    ids = list(dict.fromkeys(int(i) for i in ids if int(i) in loci))
    if not ids:
        raise ValueError('None of the genes are current SGD loci')
    members = set(ids)

    edge_types = body.get('edge_types') or list(DEFAULT_EDGE_TYPES)
    unknown = set(edge_types) - set(EDGE_TYPES)
    if unknown:
        raise ValueError('Unknown edge type(s): %s' % ', '.join(sorted(unknown)))
    min_evidence = body.get('min_evidence')
    min_evidence = default_min_evidence(len(ids)) if min_evidence in (None, '') else \
        _int(min_evidence, 'min_evidence', 1, 1000)
    neighbors = _int(body.get('neighbors') or 0, 'neighbors', 0, MAX_NEIGHBORS)
    go_min_shared = _int(body.get('go_min_shared') or 2, 'go_min_shared', 1, 20)
    max_nodes = _int(body.get('max_nodes') or DEFAULT_MAX_NODES, 'max_nodes', 10, 1000)
    max_edges = _int(body.get('max_edges') or DEFAULT_MAX_EDGES, 'max_edges', 10, MAX_EDGES_LIMIT)
    notes = []

    # interaction / regulation edges with at least min_evidence records whose
    # ends are both current loci; with neighbors, also edges to outside genes
    edges = []
    for kind in EVIDENCE_TYPES:
        if kind not in edge_types:
            continue
        found = _regulation_edges(ids, not neighbors) if kind == 'regulation' else \
            _interaction_edges(kind, ids, not neighbors)
        edges += [e for e in found.values()
                  if e['evidence'] >= min_evidence and e['source'] in loci and e['target'] in loci]

    neighbor_ids = []
    if neighbors:
        neighbor_ids, _ = _pick_neighbors(edges, members, neighbors, max(0, max_nodes - len(ids)))
        if len(ids) >= max_nodes:
            notes.append('no neighbors added: the list already has %d genes' % len(ids))
    shown = members | set(neighbor_ids)
    edges = [e for e in edges if e['source'] in shown and e['target'] in shown]

    if 'coexpression' in edge_types:
        if len(ids) > MAX_COEXPRESSION_GENES:
            notes.append('co-expression edges are only computed for lists of up to %d genes'
                         % MAX_COEXPRESSION_GENES)
        else:
            edges += list(_coexpression_edges(ids, loci).values())
    if 'shared_go' in edge_types:
        edges += list(_shared_go_edges(ids, go_min_shared).values())

    total_edges = len(edges)
    edges, min_evidence_used, limit_notes = _limit_edges(edges, max_edges, min_evidence)
    notes += limit_notes

    degree = defaultdict(int)
    for edge in edges:
        degree[edge['source']] += 1
        degree[edge['target']] += 1
    nodes = []
    for gene_id in ids + neighbor_ids:
        locus = loci[gene_id]
        nodes.append({'id': gene_id, 'name': locus['display_name'], 'systematic_name': locus['systematic_name'],
                      'link': locus['link'], 'description': locus['description'] or '',
                      'in_list': gene_id in members, 'degree': degree[gene_id]})

    counts = defaultdict(int)
    for edge in edges:
        counts[edge['type']] += 1
    return {
        'nodes': nodes,
        'edges': edges,
        'edge_types': [t for t in EDGE_TYPES if t in edge_types],
        'list_size': len(ids),
        'neighbors_added': len(neighbor_ids),
        'min_evidence': min_evidence,
        'min_evidence_used': min_evidence_used,
        'go_min_shared': go_min_shared,
        'total_edges': total_edges,
        'shown_edges': len(edges),
        'edge_counts': dict(counts),
        'notes': notes,
    }

