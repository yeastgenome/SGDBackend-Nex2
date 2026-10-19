"""Load SPELL expression values into nex.expressionannotation.

Input is a SPELL dump (tab-separated, no header), one row per gene per PCL file:

    pmid  pcl_file  description  condition_count  conditions  values  systematic_name

conditions are separated by '~' (or '|' in some older PCL files) and values are
comma-separated, one per condition ('NA' = no value; those are skipped).

Each PCL file is mapped to a dataset by its GSE number (falling back to the
datasets linked to its PMID), and each condition to a datasetsample of that
dataset by name: exact first, then normalized (case, punctuation, delta/mu/plus
spellings). When a PCL has exactly as many conditions as its dataset has
samples and every name that did match sits at its own position, the remaining
conditions are assigned by sample order. Conditions that still can't be mapped
are reported, never guessed.

Samples that already have expression rows are skipped (use
--include-loaded-samples to fill gaps in them), and inserts use ON CONFLICT DO
NOTHING on (datasetsample_id, dbentity_id), so re-running is safe.

Values follow the 2017 load:
  - 2-channel: normalized_expression_value = log_ratio_value = SPELL value
  - 1-channel: normalized_expression_value = SPELL value,
               log_ratio_value = log2(value / mean of the positive values in the
               gene's PCL row), rounded to 2 decimals; 0 when the value is <= 0
When a sample is in more than one PCL file (e.g. GSE7820_set0 + _set1 + the
combined _setA), it is loaded from the PCL with the most conditions, as in 2017.
Datasets with no channel_count are reported and skipped.

Dry run by default: prints per-dataset counts of rows that would be added and
writes a per-PCL mapping report. Pass --load to insert.

Expression pages read precomputed S3 JSON, so after a load run
upload_expression_details.py (same folder) to publish the new values.

usage (from the repo root, with the env script sourced):
    python scripts/loading/dataset/load_expression_data.py \\
        scripts/loading/dataset/data/spell_dump.tsv [--load] [--only GSE86358,GSE24681]
"""
import argparse
import collections
import logging
import math
import os
import re
import unicodedata

from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text

from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']
TAXID = 'TAX:4932'  # taxonomy used by all existing expressionannotation rows
REPORT_FILE = 'scripts/loading/dataset/data/load_expression_report.tsv'
BATCH_SIZE = 5000

INSERT_SQL = """
    INSERT INTO nex.expressionannotation
        (dbentity_id, source_id, taxonomy_id, reference_id, datasetsample_id,
         normalized_expression_value, log_ratio_value, created_by)
    VALUES %s
    ON CONFLICT (datasetsample_id, dbentity_id) DO NOTHING
"""


def normalize_name(name):

    name = unicodedata.normalize('NFKC', name)
    name = name.replace('Δ', 'delta').replace('μ', 'u').replace('µ', 'u').replace('+', 'plus')
    return re.sub(r'[^a-z0-9]+', '', name.lower())


def split_conditions(conditions):

    return [x.strip() for x in re.split(r'[~|]', conditions)]


def get_data(nex_session):

    data = {}
    data['locus'] = dict(nex_session.execute(text(
        "SELECT systematic_name, dbentity_id FROM nex.locusdbentity")).fetchall())
    data['pmid'] = dict(nex_session.execute(text(
        "SELECT pmid, dbentity_id FROM nex.referencedbentity WHERE pmid IS NOT NULL")).fetchall())
    data['source_id'] = nex_session.execute(text(
        "SELECT source_id FROM nex.source WHERE format_name = 'SGD'")).scalar()
    data['taxonomy_id'] = nex_session.execute(text(
        "SELECT taxonomy_id FROM nex.taxonomy WHERE taxid = :taxid"), {'taxid': TAXID}).scalar()

    data['dataset'] = {}           # dataset_id -> (format_name, channel_count)
    data['format_to_ids'] = collections.defaultdict(list)  # GSE12345 -> dataset_ids (incl. GSE12345-1)
    for dataset_id, format_name, channel_count in nex_session.execute(text(
            "SELECT dataset_id, format_name, channel_count FROM nex.dataset")).fetchall():
        data['dataset'][dataset_id] = (format_name, channel_count)
        data['format_to_ids'][re.sub(r'-\d+$', '', format_name)].append(dataset_id)

    data['samples'] = collections.defaultdict(list)  # dataset_id -> [(datasetsample_id, name)] by sample_order
    for dataset_id, datasetsample_id, name in nex_session.execute(text(
            "SELECT dataset_id, datasetsample_id, display_name FROM nex.datasetsample "
            "ORDER BY dataset_id, sample_order, datasetsample_id")).fetchall():
        data['samples'][dataset_id].append((datasetsample_id, name.strip()))

    data['pmid_to_dataset_ids'] = collections.defaultdict(set)
    data['dataset_to_reference_ids'] = collections.defaultdict(set)
    for dataset_id, reference_id, pmid in nex_session.execute(text(
            "SELECT dr.dataset_id, dr.reference_id, r.pmid FROM nex.dataset_reference dr "
            "JOIN nex.referencedbentity r ON r.dbentity_id = dr.reference_id")).fetchall():
        data['dataset_to_reference_ids'][dataset_id].add(reference_id)
        if pmid is not None:
            data['pmid_to_dataset_ids'][pmid].add(dataset_id)

    # samples that already have expression rows (index probe per sample, no table scan)
    data['loaded_samples'] = set(x[0] for x in nex_session.execute(text(
        "SELECT s.datasetsample_id FROM nex.datasetsample s WHERE EXISTS "
        "(SELECT 1 FROM nex.expressionannotation e WHERE e.datasetsample_id = s.datasetsample_id)")).fetchall())

    data['sample_to_dataset'] = dict((sid, did) for did, samples in data['samples'].items() for sid, _ in samples)
    return data


def candidate_datasets(data, pmid, pcl):

    gse = re.match(r'(GSE\d+)', pcl)
    if gse and gse.group(1) in data['format_to_ids']:
        return data['format_to_ids'][gse.group(1)]
    return sorted(data['pmid_to_dataset_ids'].get(pmid, []))


def map_conditions(data, dataset_ids, conditions):
    """Return ([datasetsample_id or None per condition], {method: count})."""

    exact = collections.defaultdict(set)
    normalized = collections.defaultdict(set)
    for dataset_id in dataset_ids:
        for datasetsample_id, name in data['samples'][dataset_id]:
            exact[name].add(datasetsample_id)
            normalized[normalize_name(name)].add(datasetsample_id)

    mapped = []
    methods = collections.Counter()
    for condition in conditions:
        hits = exact.get(condition, set())
        method = 'exact'
        if len(hits) != 1:
            hits = normalized.get(normalize_name(condition), set())
            method = 'normalized'
        if len(hits) == 1:
            mapped.append(next(iter(hits)))
            methods[method] += 1
        else:
            mapped.append(None)

    # two conditions on the same sample means the names can't be trusted
    counts = collections.Counter(x for x in mapped if x is not None)
    for i, datasetsample_id in enumerate(mapped):
        if datasetsample_id is not None and counts[datasetsample_id] > 1:
            mapped[i] = None
            methods['conflict'] += 1

    # fall back to sample order when the matched names all sit at their own position
    if None in mapped and len(dataset_ids) == 1:
        ordered = [x[0] for x in data['samples'][dataset_ids[0]]]
        matched = [(i, x) for i, x in enumerate(mapped) if x is not None]
        if len(ordered) == len(conditions) and matched and all(ordered[i] == x for i, x in matched):
            methods['order'] += mapped.count(None)
            mapped = ordered

    return mapped, methods


def log_ratio(value, row_mean, channel_count):

    if channel_count == 2:
        return value
    if value <= 0 or row_mean <= 0:
        return 0.0
    return round(math.log(value / row_mean, 2), 2)


def parse_value(value):

    value = value.strip()
    if value.upper() in ('', 'NA', 'NAN', 'NULL'):
        return None
    return float(value)


class PclState:
    """Mapping and counts for one PCL file (cached: a PCL may appear in more than one block)."""

    def __init__(self, data, pmid, pcl, conditions, include_loaded):

        self.pcl = pcl
        self.pmid = pmid
        self.conditions = conditions
        self.problem = ''
        self.mapped = [None] * len(conditions)
        self.channel_count = None
        self.in_larger_pcl = 0
        self.methods = collections.Counter()
        self.skipped_loaded = 0
        self.rows = 0
        self.unknown_genes = 0
        self.na_values = 0
        self.unmapped_conditions = []
        pmid_int = int(pmid) if pmid.strip().isdigit() else None
        self.dataset_ids = candidate_datasets(data, pmid_int, pcl)
        self.reference_id = data['pmid'].get(pmid_int)

        if not self.dataset_ids:
            self.problem = 'no dataset for GSE/PMID'
            return
        self.mapped, self.methods = map_conditions(data, self.dataset_ids, conditions)
        self.unmapped_conditions = [c for c, x in zip(conditions, self.mapped) if x is None]

        channel_counts = set(data['dataset'][data['sample_to_dataset'][x]][1] for x in self.mapped if x)
        if None in channel_counts:
            self.problem = 'dataset has no channel_count'
            self.mapped = [None] * len(conditions)
            return
        if len(channel_counts) > 1:
            self.problem = 'conditions span datasets with different channel_count'
            self.mapped = [None] * len(conditions)
            return
        self.channel_count = channel_counts.pop() if channel_counts else None

        if self.reference_id is None:
            references = set()
            for x in self.mapped:
                if x:
                    references |= data['dataset_to_reference_ids'][data['sample_to_dataset'][x]]
            if len(references) == 1:
                self.reference_id = references.pop()

        if not include_loaded:
            for i, x in enumerate(self.mapped):
                if x in data['loaded_samples']:
                    self.mapped[i] = None
                    self.skipped_loaded += 1

    def unmapped(self):

        if self.problem:
            return len(self.conditions)
        return sum(1 for x in self.mapped if x is None) - self.skipped_loaded - self.in_larger_pcl

    def datasets(self, data):

        return ','.join(sorted(set(data['dataset'][x][0] for x in self.dataset_ids)))


def read_dump(infile, only):
    """Yield (pmid, pcl, conditions, values, systematic_name) for each well-formed line."""

    with open(infile, encoding='utf-8', errors='replace') as f:
        for line in f:
            pieces = line.rstrip('\n').split('\t')
            if len(pieces) != 7:
                log.info("Skipping malformed line: %s", line[:100])
                continue
            pmid, pcl, _, _, conditions, values, systematic_name = pieces
            if only and not any(pcl.startswith(x) for x in only):
                continue
            yield pmid, pcl, conditions, values, systematic_name.strip()


def map_pcl_files(data, infile, only, include_loaded):
    """First pass: map every PCL file's conditions to samples."""

    states = {}
    order = []
    for pmid, pcl, conditions, _, _ in read_dump(infile, only):
        if pcl not in states:
            states[pcl] = PclState(data, pmid, pcl, split_conditions(conditions), include_loaded)
            order.append(pcl)

    # a sample in several PCL files is loaded from the one with the most conditions
    owner = {}
    for pcl in order:
        for x in states[pcl].mapped:
            if x and (x not in owner or len(states[pcl].conditions) > len(states[owner[x]].conditions)):
                owner[x] = pcl
    for pcl in order:
        state = states[pcl]
        for i, x in enumerate(state.mapped):
            if x and owner[x] != pcl:
                state.mapped[i] = None
                state.in_larger_pcl += 1
    return states, order


def load_data(infile, do_load, only, include_loaded):

    nex_session = get_session()
    log.info("Reading datasets, samples, genes and references...")
    data = get_data(nex_session)
    log.info("%d datasets, %d samples (%d already have expression rows)",
             len(data['dataset']), len(data['sample_to_dataset']), len(data['loaded_samples']))
    only = set(only) if only else None

    log.info("Mapping PCL files to datasets and samples...")
    states, order = map_pcl_files(data, infile, only, include_loaded)

    nex_session.close()

    # inserts go through their own DBAPI connection, committed after each PCL file
    connection = create_engine(os.environ['NEX2_URI']).raw_connection() if do_load else None
    cursor = connection.cursor() if do_load else None
    batch = []
    inserted = 0
    current_pcl = None

    def flush():
        nonlocal inserted, batch
        if batch and cursor is not None:
            execute_values(cursor, INSERT_SQL, batch, page_size=BATCH_SIZE)
            inserted += cursor.rowcount
        batch = []

    log.info("Loading..." if do_load else "Counting rows to add...")
    for _, pcl, _, values, systematic_name in read_dump(infile, only):
        state = states[pcl]
        if pcl != current_pcl:
            current_pcl = pcl
            if do_load:
                flush()
                connection.commit()
        if state.problem or not any(state.mapped):
            continue

        dbentity_id = data['locus'].get(systematic_name)
        if dbentity_id is None:
            state.unknown_genes += 1
            continue

        values = [parse_value(x) for x in values.split(',')]
        if len(values) != len(state.conditions):
            log.info("Skipping %s %s: %d values for %d conditions",
                     pcl, systematic_name, len(values), len(state.conditions))
            continue
        positive = [x for x in values if x is not None and x > 0]
        row_mean = sum(positive) / len(positive) if positive else 0

        for datasetsample_id, value in zip(state.mapped, values):
            if datasetsample_id is None:
                continue
            if value is None:
                state.na_values += 1
                continue
            state.rows += 1
            if do_load:
                batch.append((dbentity_id, data['source_id'], data['taxonomy_id'], state.reference_id,
                              datasetsample_id, value, log_ratio(value, row_mean, state.channel_count),
                              CREATED_BY))
                if len(batch) >= BATCH_SIZE:
                    flush()

    flush()
    if do_load:
        connection.commit()
        connection.close()

    write_report(data, states, order)
    summarize(data, states, order, do_load, inserted)


def write_report(data, states, order):

    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    with open(REPORT_FILE, 'w') as fw:
        fw.write('\t'.join(['pcl', 'pmid', 'datasets', 'conditions', 'exact', 'normalized', 'order',
                            'already_loaded', 'in_larger_pcl', 'unmapped', 'rows_to_add', 'unknown_genes', 'na_values',
                            'reference_id', 'problem', 'unmapped_conditions']) + '\n')
        for pcl in order:
            s = states[pcl]
            unmapped = [] if s.problem else s.unmapped_conditions
            fw.write('\t'.join(str(x) for x in [
                pcl, s.pmid, s.datasets(data), len(s.conditions), s.methods['exact'], s.methods['normalized'],
                s.methods['order'], s.skipped_loaded, s.in_larger_pcl, s.unmapped(), s.rows, s.unknown_genes,
                s.na_values, s.reference_id or '', s.problem, ' ~ '.join(unmapped)]) + '\n')
    log.info("Per-PCL report: %s", REPORT_FILE)


def summarize(data, states, order, do_load, inserted):

    by_dataset = collections.Counter()
    for pcl in order:
        s = states[pcl]
        if s.rows:
            by_dataset[s.datasets(data)] += s.rows

    totals = collections.Counter()
    for pcl in order:
        s = states[pcl]
        totals['pcl files'] += 1
        totals['conditions'] += len(s.conditions)
        totals['already loaded'] += s.skipped_loaded
        totals['unmapped'] += s.unmapped()
        totals['rows'] += s.rows
        totals['pcl files with a problem'] += bool(s.problem)
        totals['pcl files with rows to add'] += bool(s.rows)

    log.info("")
    log.info("Datasets with rows to add:")
    for name, rows in sorted(by_dataset.items()):
        log.info("  %-40s %10d", name, rows)
    log.info("")
    for key in ['pcl files', 'pcl files with rows to add', 'pcl files with a problem', 'conditions',
                'already loaded', 'unmapped', 'rows']:
        log.info("%-28s %d", key, totals[key])
    if do_load:
        log.info("Inserted %d rows (rest already present)", inserted)
        if inserted:
            # expression pages read precomputed S3 JSON, not the database
            log.info("")
            log.info("REMINDER: expression pages still show the old values until the S3 JSON is regenerated.")
            log.info("  all loci:      python scripts/loading/dataset/upload_expression_details.py")
            log.info("  some loci:     python scripts/loading/dataset/upload_expression_details.py S000001855 ...")
            log.info("  Run it with the same environment (NEX2_URI) as this load; a full run takes hours.")
    else:
        log.info("Dry run: nothing written. Re-run with --load to insert.")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('infile', help='SPELL dump (tab-separated)')
    parser.add_argument('--load', action='store_true', help='insert rows (default: dry run)')
    parser.add_argument('--only', help='comma-separated PCL file prefixes to process, e.g. GSE86358,GSE24681')
    parser.add_argument('--include-loaded-samples', action='store_true',
                        help='also fill missing genes in samples that already have rows')
    args = parser.parse_args()

    load_data(args.infile, args.load, args.only.split(',') if args.only else None, args.include_loaded_samples)
