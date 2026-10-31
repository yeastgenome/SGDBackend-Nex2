"""Recompute log_ratio_value for single-channel datasets that are not linear.

The 2017 load (and the 2026 SPELL load, which reproduced it) computed every
1-channel log ratio as log2(value / row mean), 0 for values <= 0. That only
fits linear intensities. This script classifies each 1-channel dataset from
its stored normalized_expression_value (same rules as the loader, see
expression_value_scale.py) and sets

    log-scale datasets:  log_ratio_value = round(value - mean of the gene's
                         values in the dataset, 2)
    ratio datasets:      log_ratio_value = value (already log ratios)
    linear datasets:     unchanged

The loader centres on the gene's PCL row; a dataset is one PCL file except for
a few built from several, which must be excluded here (--exclude) and redone
per file with load_expression_data.py --recompute-log-ratios. Only rows whose
value changes are updated, so a re-run is a no-op.

Dry run by default: writes a per-dataset report and changes nothing.
With --apply, the current values of each dataset are first saved to a gzipped
backup (dataset_id, annotation_id, log_ratio_value), then each dataset is
updated in its own transaction. --restore <backup> puts the saved values back.

The schema's expressionannotation_audr trigger writes an updatelog row per
changed log_ratio_value; the script stops if it is installed unless
--allow-audit-trigger is given.

After applying: regenerate the expression details S3 JSON
(upload_expression_details.py) and recompute co-expression
(compute_coexpression.py).

usage (from the repo root, with the env script sourced):
    python scripts/loading/dataset/fix_log_scale_log_ratios.py                 # dry run + report
    python scripts/loading/dataset/fix_log_scale_log_ratios.py --apply --backup-dir /data/tmp/expr \
        --exclude GSE28213,GSE3729,GSE3200,GSE12222,GSE6018
    python scripts/loading/dataset/fix_log_scale_log_ratios.py --only GSE20155,GSE72356-2 --apply ...
    python scripts/loading/dataset/fix_log_scale_log_ratios.py --restore /data/tmp/expr/log_ratio_backup_....tsv.gz
"""
import argparse
import datetime
import gzip
import logging
import os
import time

from sqlalchemy import create_engine, text

from scripts.loading.dataset.expression_value_scale import LINEAR, LOG, LOG_SCALE_MEDIAN, RATIO, ValueScale

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
log = logging.getLogger('fix_log_ratios')

REPORT_FILE = 'scripts/loading/dataset/data/fix_log_scale_log_ratios_report.tsv'

STATS_SQL = """
    SELECT d.dataset_id, d.format_name, count(*) AS n,
           sum((e.normalized_expression_value < 0)::int) AS negative,
           sum((e.normalized_expression_value >= :median)::int) AS at_least_median,
           max(e.normalized_expression_value) AS maximum,
           stddev(e.log_ratio_value) AS sd
    FROM nex.expressionannotation e
    JOIN nex.datasetsample ds ON ds.datasetsample_id = e.datasetsample_id
    JOIN nex.dataset d ON d.dataset_id = ds.dataset_id
    WHERE d.channel_count = 1
    GROUP BY d.dataset_id, d.format_name
    ORDER BY d.format_name
"""

SAMPLE_MEANS_SQL = """
    SELECT ds.dataset_id, avg(e.normalized_expression_value) AS mean
    FROM nex.expressionannotation e
    JOIN nex.datasetsample ds ON ds.datasetsample_id = e.datasetsample_id
    JOIN nex.dataset d ON d.dataset_id = ds.dataset_id
    WHERE d.channel_count = 1
    GROUP BY ds.dataset_id, ds.datasetsample_id
"""

GENE_SPREAD_SQL = """
    WITH v AS (
        SELECT ds.dataset_id, e.dbentity_id, e.normalized_expression_value AS x
        FROM nex.expressionannotation e
        JOIN nex.datasetsample ds ON ds.datasetsample_id = e.datasetsample_id
        WHERE ds.dataset_id = ANY(:ids)),
    g AS (SELECT dataset_id, dbentity_id, avg(x) AS m FROM v GROUP BY 1, 2)
    SELECT v.dataset_id, stddev_pop(v.x - g.m) / NULLIF(stddev_pop(v.x), 0) AS spread
    FROM v JOIN g USING (dataset_id, dbentity_id)
    GROUP BY v.dataset_id
"""

RATIO_UPDATE_SQL = """
    UPDATE nex.expressionannotation e
    SET log_ratio_value = e.normalized_expression_value
    FROM nex.datasetsample ds
    WHERE ds.datasetsample_id = e.datasetsample_id
      AND ds.dataset_id = %(dataset_id)s
      AND e.log_ratio_value IS DISTINCT FROM e.normalized_expression_value
"""

UPDATE_SQL = """
    UPDATE nex.expressionannotation e
    SET log_ratio_value = round((e.normalized_expression_value - m.mean)::numeric, 2)
    FROM nex.datasetsample ds,
         (SELECT e2.dbentity_id, avg(e2.normalized_expression_value) AS mean
          FROM nex.expressionannotation e2
          JOIN nex.datasetsample ds2 ON ds2.datasetsample_id = e2.datasetsample_id
          WHERE ds2.dataset_id = %(dataset_id)s
          GROUP BY e2.dbentity_id) m
    WHERE ds.datasetsample_id = e.datasetsample_id
      AND ds.dataset_id = %(dataset_id)s
      AND e.dbentity_id = m.dbentity_id
      AND e.log_ratio_value IS DISTINCT FROM round((e.normalized_expression_value - m.mean)::numeric, 2)
"""

SD_SQL = """
    SELECT stddev(e.log_ratio_value) FROM nex.expressionannotation e
    JOIN nex.datasetsample ds ON ds.datasetsample_id = e.datasetsample_id
    WHERE ds.dataset_id = %(dataset_id)s
"""

BACKUP_SQL = """
    COPY (SELECT ds.dataset_id, e.annotation_id, e.log_ratio_value
          FROM nex.expressionannotation e
          JOIN nex.datasetsample ds ON ds.datasetsample_id = e.datasetsample_id
          WHERE ds.dataset_id = {dataset_id}) TO STDOUT
"""


def audit_trigger_installed(engine):
    with engine.connect() as conn:
        return conn.execute(text(
            "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'nex' AND c.relname = 'expressionannotation' "
            "AND t.tgname = 'expressionannotation_audr' AND t.tgenabled <> 'D'")).scalar() > 0


def classify(engine, only, exclude):
    """[(dataset_id, accession, n, scale, sd)] for single-channel datasets."""
    with engine.connect() as conn:
        rows = conn.execute(text(STATS_SQL), {'median': LOG_SCALE_MEDIAN}).fetchall()
        sample_means = {}
        for dataset_id, mean in conn.execute(text(SAMPLE_MEANS_SQL)):
            sample_means.setdefault(dataset_id, []).append(float(mean))
    out = []
    for r in rows:
        if only and r.format_name not in only and str(r.dataset_id) not in only:
            continue
        if exclude and (r.format_name in exclude or str(r.dataset_id) in exclude):
            continue
        scale = ValueScale(r.n, r.negative, r.at_least_median, r.maximum, sample_means=sample_means[r.dataset_id],
                           gene_spread=1.0)
        out.append((r.dataset_id, r.format_name, r.n, scale, float(r.sd or 0)))
    # the gene-level test is only needed (and only computed) for centred candidates
    candidates = [d[0] for d in out if d[3].kind() == RATIO]
    if candidates:
        with engine.connect() as conn:
            spreads = dict(conn.execute(text(GENE_SPREAD_SQL), {'ids': candidates}).fetchall())
        for d in out:
            if d[0] in spreads:
                d[3]._gene_spread = float(spreads[d[0]] or 0)
    return out


def backup(raw, dataset_id, fw):
    cursor = raw.cursor()
    cursor.copy_expert(BACKUP_SQL.format(dataset_id=int(dataset_id)), fw)
    cursor.close()


def apply_fix(engine, datasets, backup_dir):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, 'log_ratio_backup_%s.tsv.gz' % stamp)
    raw = engine.raw_connection()
    results = {}
    start = time.time()
    try:
        with gzip.open(backup_file, 'wt') as fw:
            for n, (dataset_id, accession, _, scale, _) in enumerate(datasets, 1):
                backup(raw, dataset_id, fw)
                cursor = raw.cursor()
                cursor.execute(RATIO_UPDATE_SQL if scale.kind() == RATIO else UPDATE_SQL, {'dataset_id': dataset_id})
                updated = cursor.rowcount
                cursor.execute(SD_SQL, {'dataset_id': dataset_id})
                sd_after = float(cursor.fetchone()[0] or 0)
                raw.commit()
                cursor.close()
                results[dataset_id] = (updated, sd_after)
                log.info('%d/%d %s (%s): %d rows updated, log ratio SD now %.3f (%.0fs)',
                         n, len(datasets), accession, scale.kind(), updated, sd_after, time.time() - start)
    finally:
        raw.close()
    log.info('backup of the previous values: %s', backup_file)
    return results


def restore(engine, backup_file):
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("CREATE TEMP TABLE log_ratio_restore "
                       "(dataset_id bigint, annotation_id bigint, log_ratio_value double precision)")
        with gzip.open(backup_file, 'rt') as f:
            cursor.copy_expert("COPY log_ratio_restore FROM STDIN", f)
        cursor.execute("UPDATE nex.expressionannotation e SET log_ratio_value = r.log_ratio_value "
                       "FROM log_ratio_restore r WHERE e.annotation_id = r.annotation_id "
                       "AND e.log_ratio_value IS DISTINCT FROM r.log_ratio_value")
        log.info('restored %d rows from %s', cursor.rowcount, backup_file)
        raw.commit()
    finally:
        raw.close()


def write_report(datasets, results):
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    with open(REPORT_FILE, 'w') as fw:
        fw.write('\t'.join(['dataset_id', 'accession', 'values', 'pct_negative', 'pct_at_least_median', 'max',
                            'median_abs_sample_mean', 'gene_spread', 'scale', 'log_ratio_sd_before', 'rows_updated',
                            'log_ratio_sd_after']) + '\n')
        for dataset_id, accession, n, scale, sd in datasets:
            updated, sd_after = results.get(dataset_id, ('', ''))
            fw.write('\t'.join(str(x) for x in [
                dataset_id, accession, n, round(100.0 * scale.negative / n, 1),
                round(100.0 * scale.at_least_median / n, 1), round(scale.max, 2),
                round(sorted(abs(m) for m in scale.sample_means())[len(scale.sample_means()) // 2], 3),
                round(scale.gene_spread(), 2), scale.kind(), round(sd, 3),
                updated, round(sd_after, 3) if sd_after != '' else '']) + '\n')
    log.info('report: %s', REPORT_FILE)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true', help='update the database (default: dry run)')
    parser.add_argument('--only', help='comma-separated dataset accessions (format_name) or dataset_ids')
    parser.add_argument('--backup-dir', default='scripts/loading/dataset/data',
                        help='where --apply writes the backup of the previous values')
    parser.add_argument('--exclude', help='comma-separated dataset accessions or dataset_ids to leave alone '
                                          '(datasets built from several PCL files)')
    parser.add_argument('--restore', metavar='BACKUP', help='put back the values saved in a backup file')
    parser.add_argument('--allow-audit-trigger', action='store_true',
                        help='run even though expressionannotation_audr will log every changed value')
    args = parser.parse_args()

    engine = create_engine(os.environ['NEX2_URI'])
    if (args.apply or args.restore) and audit_trigger_installed(engine) and not args.allow_audit_trigger:
        raise SystemExit('expressionannotation_audr is enabled: every changed value would be written to '
                         'nex.updatelog. Disable it for the repair or pass --allow-audit-trigger.')
    if args.restore:
        restore(engine, args.restore)
        return

    only = set(args.only.split(',')) if args.only else None
    exclude = set(args.exclude.split(',')) if args.exclude else None
    datasets = classify(engine, only, exclude)
    kinds = [d[3].kind() for d in datasets]
    to_fix = [d for d, k in zip(datasets, kinds) if k in (LOG, RATIO)]
    log.info('%d single-channel datasets: %d log-scale, %d ratio (%d values to check), %d linear',
             len(datasets), kinds.count(LOG), kinds.count(RATIO), sum(d[2] for d in to_fix), kinds.count(LINEAR))
    results = apply_fix(engine, to_fix, args.backup_dir) if args.apply else {}
    write_report(datasets, results)
    if args.apply:
        log.info('next: regenerate the expression S3 JSON and recompute co-expression')


if __name__ == '__main__':
    main()
