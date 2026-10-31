"""Expression heatmap data for a gene list.

get_list_expression() returns log2 expression ratios for up to MAX_GENES genes
across the samples of one dataset, or of the datasets in which the list genes
respond most specifically, together with the datasets ranked that way, a
category per dataset (from its curated keywords) and hierarchical-clustering
orders for the genes and the samples.

A dataset's score for a list is the mean standard deviation of the list
genes' log2 ratios across its samples minus the median standard deviation
of a fixed sample of genes in that dataset: the list's excess spread, so
neither datasets where every gene varies a lot nor quiet datasets with
tiny, noisy differences dominate.

Some datasets have most of their stored log2 ratios set to exactly 0 (e.g.
single-channel data that was already log-scale, where the loader's
log2(value / row mean) rule zeroes every value <= 0). Such "flattened"
datasets (> MAX_ZERO_FRACTION zeros in the baseline sample) are left out of
the default view and ranked last, flagged, but can still be picked.
"""
import re
from collections import OrderedDict

import numpy as np
from sqlalchemy import text

from .gene_list_helpers import MAX_INPUT_IDENTIFIERS, _cached, get_lookup, resolve_identifiers
from .models import DBSession

MAX_GENES = 100
DEFAULT_TOP_DATASETS = 12
MAX_COLUMNS = 400
MAX_OVERVIEW_SAMPLES = 60   # larger datasets are only shown when picked individually
MIN_GENE_FRACTION = 0.5     # a dataset must measure this fraction of the list genes to be ranked
BASELINE_GENES = 200        # genes sampled to estimate each dataset's typical per-gene spread
MAX_ZERO_FRACTION = 0.2     # datasets with more exact-zero log ratios are treated as flattened (see below)

# Dataset keyword -> category, in priority order (a dataset gets the first match)
CATEGORIES = OrderedDict([
    ('Stress response', ['stress', 'heat shock', 'oxidative stress', 'osmotic stress', 'metal or metalloid ion stress',
                         'DNA damage stimulus', 'response to unfolded protein', 'chemical stimulus',
                         'oxygen level alteration']),
    ('Nutrients & metabolism', ['carbon utilization', 'nitrogen utilization', 'phosphorus utilization',
                                'amino acid utilization', 'nutrient utilization', 'fermentation', 'respiration',
                                'diauxic shift', 'starvation', 'lipid metabolism']),
    ('Cell cycle & development', ['mitotic cell cycle', 'cell cycle regulation', 'sporulation', 'cell aging',
                                  'filamentous growth', 'DNA replication, recombination and repair',
                                  'cell wall organization']),
    ('Gene regulation & chromatin', ['transcription', 'transcriptional regulation', 'chromatin organization',
                                     'histone modification', 'mRNA processing', 'RNA catabolism',
                                     'translational regulation', 'signaling', 'protein phosphorylation']),
])
OTHER_CATEGORY = 'Other'
TAG_RE = re.compile(r'<[^>]+>')


def _build_datasets():
    """dataset_id -> {id, name, link, category, keywords, samples:[(sample_id, label)]}
    for datasets with expression values."""
    datasets = OrderedDict()
    for r in DBSession.execute(text(
            "SELECT d.dataset_id, d.display_name, d.format_name, d.obj_url, d.channel_count, "
            "       ds.datasetsample_id, ds.display_name AS sample "
            "FROM nex.dataset d JOIN nex.datasetsample ds ON ds.dataset_id = d.dataset_id "
            "WHERE EXISTS (SELECT 1 FROM nex.expressionannotation ea "
            "              WHERE ea.datasetsample_id = ds.datasetsample_id) "
            "ORDER BY d.dataset_id, ds.sample_order, ds.datasetsample_id")):
        if r.dataset_id not in datasets:
            datasets[r.dataset_id] = {'id': r.dataset_id, 'name': TAG_RE.sub('', r.display_name),
                                      'accession': r.format_name,
                                      'link': r.obj_url, 'channel_count': r.channel_count, 'keywords': [],
                                      'samples': []}
        datasets[r.dataset_id]['samples'].append((r.datasetsample_id, TAG_RE.sub('', r.sample or '')))
    for dataset_id, keyword in DBSession.execute(text(
            "SELECT dk.dataset_id, k.display_name FROM nex.dataset_keyword dk "
            "JOIN nex.keyword k ON k.keyword_id = dk.keyword_id ORDER BY k.display_name")):
        if dataset_id in datasets:
            datasets[dataset_id]['keywords'].append(keyword)
    for d in datasets.values():
        d['category'] = _category(d['keywords'])
    return datasets


def _category(keywords):
    for category, members in CATEGORIES.items():
        if any(k in members for k in keywords):
            return category
    return OTHER_CATEGORY


def get_datasets():
    return _cached('expression_datasets', _build_datasets)


def _average_linkage_order(matrix):
    """Leaf order of average-linkage hierarchical clustering of the rows of
    matrix (NaN = missing), with 1 - Pearson correlation as the distance."""
    n = matrix.shape[0]
    if n < 3:
        return list(range(n))
    x = matrix - np.nanmean(matrix, axis=1, keepdims=True)
    x = np.nan_to_num(x, nan=0.0)
    norms = np.linalg.norm(x, axis=1)
    norms[norms == 0] = 1.0
    x = x / norms[:, None]
    dist = 1.0 - np.clip(x @ x.T, -1.0, 1.0)
    np.fill_diagonal(dist, np.inf)
    members = [[i] for i in range(n)]
    active = np.ones(n, dtype=bool)
    for _ in range(n - 1):
        a, b = np.unravel_index(np.argmin(dist), dist.shape)
        a, b = min(a, b), max(a, b)
        size_a, size_b = len(members[a]), len(members[b])
        merged = (dist[a] * size_a + dist[b] * size_b) / (size_a + size_b)
        merged[~active] = np.inf
        dist[a, :] = merged
        dist[:, a] = merged
        dist[a, a] = np.inf
        dist[b, :] = np.inf
        dist[:, b] = np.inf
        active[b] = False
        members[a] = members[a] + members[b]
        members[b] = []
    return members[int(np.flatnonzero(active)[0])]


def _fetch_values(gene_ids):
    """{(gene_id, sample_id): log2 ratio} for the genes."""
    values = {}
    for gene_id, sample_id, value in DBSession.execute(text(
            "SELECT dbentity_id, datasetsample_id, log_ratio_value FROM nex.expressionannotation "
            "WHERE dbentity_id = ANY(:ids)"), {'ids': list(gene_ids)}):
        if value is not None:
            values[(gene_id, sample_id)] = float(value)
    return values


def _dataset_spreads(gene_ids, values, datasets):
    """Yield (dataset, per-gene std array for genes with >= 2 values) per
    dataset with at least 2 samples."""
    sample_col = {}
    spans = []
    for d in datasets.values():
        start = len(sample_col)
        for sample_id, _ in d['samples']:
            sample_col[sample_id] = len(sample_col)
        spans.append((d, start, len(sample_col)))
    row_of = {g: i for i, g in enumerate(gene_ids)}
    matrix = np.full((len(gene_ids), len(sample_col)), np.nan)
    for (g, sample_id), v in values.items():
        col = sample_col.get(sample_id)
        if col is not None:
            matrix[row_of[g], col] = v
    with np.errstate(invalid='ignore'):
        for d, start, end in spans:
            if end - start < 2:
                continue
            block = matrix[:, start:end]
            measured = np.sum(np.isfinite(block), axis=1) >= 2
            yield d, np.nanstd(block[measured], axis=1)


def _build_baseline():
    """dataset_id -> {'sd': median per-gene std of log2 ratios, 'zero_fraction':
    fraction of log2 ratios that are exactly 0}, from every Nth gene with
    expression data (deterministic sample of ~BASELINE_GENES genes)."""
    gene_ids = [r[0] for r in DBSession.execute(text(
        "SELECT dbentity_id FROM nex.locusdbentity WHERE has_expression ORDER BY dbentity_id"))]
    step = max(1, len(gene_ids) // BASELINE_GENES)
    sample = gene_ids[::step]
    values = _fetch_values(sample)
    datasets = get_datasets()
    dataset_of = {s: d['id'] for d in datasets.values() for s, _ in d['samples']}
    totals, zeros = {}, {}
    for (_, sample_id), v in values.items():
        d_id = dataset_of.get(sample_id)
        if d_id is not None:
            totals[d_id] = totals.get(d_id, 0) + 1
            zeros[d_id] = zeros.get(d_id, 0) + (v == 0)
    return {d['id']: {'sd': float(np.median(spreads)), 'zero_fraction': zeros[d['id']] / totals[d['id']]}
            for d, spreads in _dataset_spreads(sample, values, datasets) if len(spreads) and totals.get(d['id'])}


def is_flattened(dataset_id):
    info = get_baseline().get(dataset_id)
    return bool(info) and info['zero_fraction'] > MAX_ZERO_FRACTION


def get_baseline():
    return _cached('expression_baseline', _build_baseline)


def rank_datasets(gene_ids, values, datasets):
    """Datasets measuring at least MIN_GENE_FRACTION of the genes, ranked by
    the list genes' mean std of log2 ratios minus the dataset's typical
    per-gene std (excess spread, log2 units). Flattened datasets come last."""
    baseline = get_baseline()
    ranked = []
    for d, spreads in _dataset_spreads(gene_ids, values, datasets):
        n = len(spreads)
        info = baseline.get(d['id'])
        if n == 0 or n < MIN_GENE_FRACTION * len(gene_ids) or info is None:
            continue
        mean_sd = float(np.mean(spreads))
        flattened = info['zero_fraction'] > MAX_ZERO_FRACTION
        ranked.append((flattened, mean_sd - info['sd'], mean_sd, n, d))
    ranked.sort(key=lambda t: (t[0], -t[1]))
    return [{'id': d['id'], 'name': d['name'], 'accession': d['accession'], 'link': d['link'],
             'category': d['category'], 'keywords': d['keywords'], 'sample_count': len(d['samples']),
             'genes_measured': n, 'score': round(score, 2), 'mean_sd': round(mean_sd, 3), 'flattened': flattened}
            for flattened, score, mean_sd, n, d in ranked]


def get_list_expression(body):
    """Entry point for POST /gene_list/expression. body keys: bioent_ids or
    genes; dataset_id (optional: show that dataset instead of the top ones);
    top_datasets (default 12)."""
    if body.get('genes'):
        gene_ids = resolve_identifiers(body['genes'])['resolved_ids']
    else:
        gene_ids = [int(x) for x in body.get('bioent_ids') or []]
    loci = get_lookup()[0]
    gene_ids = [g for g in OrderedDict.fromkeys(gene_ids) if g in loci]
    if not gene_ids:
        raise ValueError('No genes given: pass "bioent_ids" or "genes"')
    if len(gene_ids) > MAX_INPUT_IDENTIFIERS:
        raise ValueError('At most %d genes are allowed' % MAX_INPUT_IDENTIFIERS)
    truncated = len(gene_ids) > MAX_GENES
    gene_ids = gene_ids[:MAX_GENES]
    top = int(body.get('top_datasets') or DEFAULT_TOP_DATASETS)
    if not 1 <= top <= 50:
        raise ValueError('top_datasets must be between 1 and 50')

    datasets = get_datasets()
    values = _fetch_values(gene_ids)
    ranked = rank_datasets(gene_ids, values, datasets)

    dataset_id = body.get('dataset_id')
    if dataset_id is not None:
        dataset_id = int(dataset_id)
        if dataset_id not in datasets:
            raise ValueError('Unknown dataset_id %s' % dataset_id)
        shown = [dataset_id]
    else:
        shown = []
        columns_so_far = 0
        for d in ranked:
            n = len(datasets[d['id']]['samples'])
            if d['flattened'] or n > MAX_OVERVIEW_SAMPLES or columns_so_far + n > MAX_COLUMNS:
                continue
            shown.append(d['id'])
            columns_so_far += n
            if len(shown) == top:
                break

    columns = []
    for d_id in shown:
        for sample_id, label in datasets[d_id]['samples'][:MAX_COLUMNS]:
            columns.append({'sample_id': sample_id, 'label': label, 'dataset_id': d_id})
    columns_truncated = dataset_id is not None and len(datasets[dataset_id]['samples']) > MAX_COLUMNS
    matrix = np.full((len(gene_ids), len(columns)), np.nan)
    for i, g in enumerate(gene_ids):
        for j, c in enumerate(columns):
            v = values.get((g, c['sample_id']))
            if v is not None:
                matrix[i, j] = v

    # Genes without values in the shown columns are left out of the grid and
    # reported separately (e.g. genes not in S288C have no expression data).
    measured = [i for i in range(len(gene_ids)) if np.isfinite(matrix[i]).any()]
    gene_order = [measured[k] for k in _average_linkage_order(matrix[measured])] if measured else []
    has_any_data = {g for g, _ in values}
    genes_without_data = [{'index': i, 'reason': 'not measured in the datasets shown' if gene_ids[i] in has_any_data
                           else 'no expression data'}
                          for i in range(len(gene_ids)) if i not in set(measured)]
    # Samples are clustered within each dataset, so datasets stay contiguous
    # (labelled) blocks in both the clustered and the original order.
    column_order = []
    for d_id in shown:
        block = [j for j, c in enumerate(columns) if c['dataset_id'] == d_id]
        if measured and len(block) > 2:
            column_order += [block[k] for k in _average_linkage_order(matrix[np.ix_(measured, block)].T)]
        else:
            column_order += block

    dataset_info = {d['id']: d for d in ranked}
    for d_id in shown:
        if d_id not in dataset_info:
            d = datasets[d_id]
            dataset_info[d_id] = {'id': d_id, 'name': d['name'], 'accession': d['accession'], 'link': d['link'],
                                  'category': d['category'], 'keywords': d['keywords'],
                                  'sample_count': len(d['samples']), 'genes_measured': None, 'score': None,
                                  'mean_sd': None, 'flattened': is_flattened(d_id)}

    genes = []
    for g in gene_ids:
        locus = loci[g]
        genes.append({'id': g, 'display_name': locus['display_name'], 'systematic_name': locus['systematic_name'],
                      'link': locus['link'], 'description': locus['description'] or ''})
    return {
        'genes': genes,
        'genes_truncated': truncated,
        'max_genes': MAX_GENES,
        'columns': columns,
        'columns_truncated': columns_truncated,
        'max_columns': MAX_COLUMNS,
        'values': [[None if not np.isfinite(v) else round(float(v), 2) for v in row] for row in matrix],
        'gene_order': gene_order,
        'genes_without_data': genes_without_data,
        'column_order': column_order,
        'shown_datasets': [dataset_info[d_id] for d_id in shown],
        'ranked_datasets': ranked,
        'categories': list(CATEGORIES) + [OTHER_CATEGORY],
        'value_type': 'log2 ratio',
    }
