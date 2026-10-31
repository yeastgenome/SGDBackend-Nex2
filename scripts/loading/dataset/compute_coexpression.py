"""Precompute gene co-expression from the expression matrix (SPELL data).

Method (after SPELL, Hibbs et al. 2007, without query-specific weighting):
for every dataset with at least --min-samples samples, each gene's log-ratio
profile is centred and scaled, Pearson correlations between all gene pairs
are Fisher z-transformed, and the z-scores are standardised within the
dataset (so datasets where everything is correlated do not dominate). A
pair's score is the mean standardised z over all datasets measuring both
genes, shrunk towards 0 for pairs with little evidence: sum / (n + --prior),
where n is the number of datasets measuring both (so a pair seen in 500
datasets keeps ~90% of its mean and one seen in 30 keeps ~40%). A pair must
be measured together in at least --min-datasets datasets and in at least
--min-shared of the datasets of the less-measured gene.

Datasets with more than --max-zero-fraction of their log ratios exactly 0
are skipped: their stored ratios are flattened (e.g. single-channel data that
was already log-scale, where the loader's log2(value / row mean) rule zeroes
every value <= 0), so their correlations would be artefacts.

Writes one JSON file per gene, <SGDID>.json, to --out-dir with the top --top
partners and a small network (the gene, its top --network partners and the
partner-partner edges at least as strong as the weakest gene-partner edge).
upload_coexpression.py puts the files on S3 for the locus expression pages.

Usage:
    python scripts/loading/dataset/compute_coexpression.py --out-dir data/coexpression
    python scripts/loading/dataset/compute_coexpression.py --limit-datasets 50 --out-dir /tmp/coexp_test
"""
import argparse
import datetime
import json
import logging
import os
import time

import numpy as np
from sqlalchemy import create_engine, text

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
log = logging.getLogger('coexpression')

MIN_SAMPLES = 6         # datasets with fewer samples give unstable correlations
MIN_COVERAGE = 0.7      # a gene must be measured in this fraction of a dataset's samples
MAX_ZERO_FRACTION = 0.2  # skip datasets with more exact-zero log ratios (flattened values)
MIN_DATASETS = 20       # a pair must be measured together in this many datasets ...
MIN_SHARED = 0.3        # ... and in this fraction of the less-measured gene's datasets
PRIOR_DATASETS = 50     # shrinkage: score = sum / (n + PRIOR_DATASETS)
TOP_PARTNERS = 100
NETWORK_PARTNERS = 20
R_CLIP = 0.999
GENE_CAPACITY = 8000


def get_active_loci(conn):
    """dbentity_id -> (sgdid, systematic_name, gene_name, display_name, headline) for active loci."""
    rows = conn.execute(text(
        "SELECT d.dbentity_id, d.sgdid, l.systematic_name, l.gene_name, d.display_name, l.headline "
        "FROM nex.dbentity d JOIN nex.locusdbentity l ON l.dbentity_id = d.dbentity_id "
        "WHERE d.dbentity_status = 'Active'")).fetchall()
    return {r[0]: (r[1], r[2], r[3], r[4], r[5]) for r in rows}


def get_datasets(conn, min_samples):
    """dataset_id -> [datasetsample_id, ...] for datasets with expression values."""
    rows = conn.execute(text(
        "SELECT ds.dataset_id, ds.datasetsample_id FROM nex.datasetsample ds "
        "WHERE EXISTS (SELECT 1 FROM nex.expressionannotation ea "
        "              WHERE ea.datasetsample_id = ds.datasetsample_id) "
        "ORDER BY ds.dataset_id, ds.sample_order, ds.datasetsample_id")).fetchall()
    datasets = {}
    for dataset_id, sample_id in rows:
        datasets.setdefault(dataset_id, []).append(sample_id)
    return {k: v for k, v in datasets.items() if len(v) >= min_samples}


def load_matrix(conn, sample_ids, active):
    """Return (gene_ids, matrix genes x samples with NaN for missing)."""
    rows = conn.execute(text(
        "SELECT datasetsample_id, dbentity_id, log_ratio_value FROM nex.expressionannotation "
        "WHERE datasetsample_id = ANY(:ids)"), {'ids': list(sample_ids)}).fetchall()
    col = {s: i for i, s in enumerate(sample_ids)}
    genes = sorted({r[1] for r in rows if r[1] in active})
    row = {g: i for i, g in enumerate(genes)}
    matrix = np.full((len(genes), len(sample_ids)), np.nan, dtype=np.float64)
    for sample_id, gene_id, value in rows:
        if gene_id in row and value is not None:
            matrix[row[gene_id], col[sample_id]] = value
    return np.array(genes, dtype=np.int64), matrix


def dataset_zscores(matrix, min_coverage):
    """Standardised Fisher-z correlation matrix for the genes that pass the
    coverage/variance filters. Returns (kept row indices, z matrix or None)."""
    n_samples = matrix.shape[1]
    coverage = np.sum(~np.isnan(matrix), axis=1) / n_samples
    keep = coverage >= min_coverage
    x = matrix[keep]
    x = x - np.nanmean(x, axis=1, keepdims=True)
    x = np.nan_to_num(x, nan=0.0)          # missing values -> gene mean
    norms = np.linalg.norm(x, axis=1)
    varying = norms > 1e-9
    kept = np.flatnonzero(keep)[varying]
    x = x[varying] / norms[varying, None]
    if len(kept) < 3:
        return kept, None
    r = np.clip(x @ x.T, -R_CLIP, R_CLIP)
    z = np.arctanh(r).astype(np.float32)
    upper = z[np.triu_indices(len(kept), k=1)]
    mean, std = float(upper.mean()), float(upper.std())
    if std < 1e-6:
        return kept, None
    z -= mean
    z /= std
    np.fill_diagonal(z, 0.0)
    return kept, z


def zero_fraction(matrix):
    measured = matrix[np.isfinite(matrix)]
    return float(np.mean(measured == 0)) if measured.size else 1.0


def accumulate(conn, active, datasets, min_coverage, max_zero_fraction=MAX_ZERO_FRACTION):
    """Sum standardised z and count datasets per gene pair. The diagonal of
    the counts is the number of datasets measuring each gene. Returns
    (ids, sums, counts, datasets used, datasets skipped as flattened)."""
    gene_index = {}
    sums = np.zeros((GENE_CAPACITY, GENE_CAPACITY), dtype=np.float32)
    counts = np.zeros((GENE_CAPACITY, GENE_CAPACITY), dtype=np.uint16)
    start = time.time()
    used = 0
    flattened = 0
    for n, dataset_id in enumerate(sorted(datasets), 1):
        genes, matrix = load_matrix(conn, datasets[dataset_id], active)
        if zero_fraction(matrix) > max_zero_fraction:
            flattened += 1
            continue
        kept, z = dataset_zscores(matrix, min_coverage)
        if z is not None:
            used += 1
            for g in genes[kept]:
                if g not in gene_index:
                    gene_index[g] = len(gene_index)
            if len(gene_index) > GENE_CAPACITY:
                raise RuntimeError('more than %d genes; raise GENE_CAPACITY' % GENE_CAPACITY)
            idx = np.array([gene_index[g] for g in genes[kept]])
            block = np.ix_(idx, idx)
            sums[block] += z
            counts[block] += 1
        if n % 25 == 0 or n == len(datasets):
            log.info('%d/%d datasets, %d genes, %d skipped as flattened, %.0fs', n, len(datasets), len(gene_index),
                     flattened, time.time() - start)
    size = len(gene_index)
    ids = np.empty(size, dtype=np.int64)
    for g, i in gene_index.items():
        ids[i] = g
    return ids, sums[:size, :size], counts[:size, :size], used, flattened


def score_matrix(sums, counts, min_datasets, min_shared, prior=PRIOR_DATASETS):
    """Shrunk mean standardised z per pair, -inf where the pair is not
    measured in enough datasets."""
    per_gene = np.diag(counts).astype(np.float32)
    required = np.maximum(min_datasets, min_shared * np.minimum.outer(per_gene, per_gene))
    with np.errstate(invalid='ignore', divide='ignore'):
        scores = np.where(counts >= required, sums / (counts.astype(np.float32) + prior), -np.inf).astype(np.float32)
    np.fill_diagonal(scores, -np.inf)
    return scores


def top_indices(row, k):
    k = min(k, int(np.isfinite(row).sum()))
    if k == 0:
        return np.array([], dtype=np.int64)
    best = np.argpartition(-row, k - 1)[:k]
    return best[np.argsort(-row[best])]


def gene_json(i, ids, scores, counts, active, top, network_size, metadata):
    sgdid, systematic_name, gene_name, display_name, _ = active[int(ids[i])]

    def locus(j):
        p_sgdid, p_systematic, p_gene, p_display, _ = active[int(ids[j])]
        return {'sgdid': p_sgdid, 'systematic_name': p_systematic, 'gene_name': p_gene,
                'display_name': p_display, 'link': '/locus/' + p_sgdid}

    best = top_indices(scores[i], top)
    partners = []
    for rank, j in enumerate(best, 1):
        partner = locus(j)
        partner.update({'description': active[int(ids[j])][4] or '', 'rank': rank,
                        'score': round(float(scores[i, j]), 3), 'dataset_count': int(counts[i, j])})
        partners.append(partner)

    nodes = [int(i)] + [int(j) for j in best[:network_size]]
    edges = [{'source': ids[i], 'target': ids[j], 'score': round(float(scores[i, j]), 3)}
             for j in best[:network_size]]
    if len(nodes) > 1:
        threshold = float(scores[i, nodes[-1]])
        for a in range(1, len(nodes)):
            for b in range(a + 1, len(nodes)):
                s = float(scores[nodes[a], nodes[b]])
                if np.isfinite(s) and s >= threshold:
                    edges.append({'source': ids[nodes[a]], 'target': ids[nodes[b]], 'score': round(s, 3)})
    sgdid_of = {int(ids[n]): active[int(ids[n])][0] for n in nodes}
    for e in edges:
        e['source'], e['target'] = sgdid_of[int(e['source'])], sgdid_of[int(e['target'])]

    return {
        'locus': {'sgdid': sgdid, 'systematic_name': systematic_name, 'gene_name': gene_name,
                  'display_name': display_name, 'dataset_count': int(counts[i, i])},
        'partners': partners,
        'network': {'nodes': [dict(locus(n), focus=bool(n == i)) for n in nodes], 'edges': edges},
        'method': metadata,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out-dir', required=True, help='directory for the <SGDID>.json files')
    parser.add_argument('--top', type=int, default=TOP_PARTNERS)
    parser.add_argument('--network', type=int, default=NETWORK_PARTNERS)
    parser.add_argument('--min-samples', type=int, default=MIN_SAMPLES)
    parser.add_argument('--min-coverage', type=float, default=MIN_COVERAGE)
    parser.add_argument('--min-datasets', type=int, default=MIN_DATASETS)
    parser.add_argument('--min-shared', type=float, default=MIN_SHARED)
    parser.add_argument('--prior', type=float, default=PRIOR_DATASETS, help='shrinkage pseudo-count of datasets')
    parser.add_argument('--max-zero-fraction', type=float, default=MAX_ZERO_FRACTION)
    parser.add_argument('--limit-datasets', type=int, help='only the first N datasets (testing)')
    parser.add_argument('--matrix', help='.npz checkpoint of the accumulated sums/counts: written after the '
                                         'database pass, or read instead of it if the file exists')
    args = parser.parse_args()

    engine = create_engine(os.environ['NEX2_URI'])
    with engine.connect() as conn:
        active = get_active_loci(conn)
        if args.matrix and os.path.exists(args.matrix):
            saved = np.load(args.matrix)
            ids, sums, counts, used = saved['ids'], saved['sums'], saved['counts'], int(saved['used'])
            flattened = int(saved['flattened']) if 'flattened' in saved else 0
            log.info('loaded %s: %d genes, %d datasets', args.matrix, len(ids), used)
        else:
            datasets = get_datasets(conn, args.min_samples)
            if args.limit_datasets:
                datasets = {k: datasets[k] for k in sorted(datasets)[:args.limit_datasets]}
            log.info('%d datasets with >= %d samples', len(datasets), args.min_samples)
            ids, sums, counts, used, flattened = accumulate(conn, active, datasets, args.min_coverage,
                                                            args.max_zero_fraction)
            if args.matrix:
                np.savez(args.matrix, ids=ids, sums=sums, counts=counts, used=used, flattened=flattened)
                log.info('saved %s', args.matrix)

    scores = score_matrix(sums, counts, args.min_datasets, args.min_shared, args.prior)
    del sums
    metadata = {
        'computed': datetime.date.today().isoformat(),
        'datasets': used,
        'datasets_skipped_flattened': flattened,
        'description': 'Mean standardised Fisher-z Pearson correlation of log-ratio expression profiles '
                       'across SGD/SPELL expression datasets measuring both genes (after SPELL, Hibbs et al. 2007), '
                       'shrunk towards 0 for pairs measured in few datasets.',
        'min_datasets': args.min_datasets,
        'min_shared': args.min_shared,
        'prior_datasets': args.prior,
    }
    os.makedirs(args.out_dir, exist_ok=True)
    written = 0
    for i in range(len(ids)):
        data = gene_json(i, ids, scores, counts, active, args.top, args.network, metadata)
        if not data['partners']:
            continue
        with open(os.path.join(args.out_dir, data['locus']['sgdid'] + '.json'), 'w') as fw:
            json.dump(data, fw, separators=(',', ':'))
        written += 1
    log.info('wrote %d gene files (%d genes measured, %d datasets used) to %s',
             written, len(ids), used, args.out_dir)


if __name__ == '__main__':
    main()
