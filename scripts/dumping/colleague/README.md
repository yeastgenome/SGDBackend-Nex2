# SGD colleague → ABC

Tools to load SGD colleague data (`nex.colleague*`) into the ABC
(`agr_literature_service`) literature database as `person` / `laboratory` /
`person_lineage` records.

The pipeline is decoupled into two steps connected by a single JSON file, so the
ABC loader never connects to SGD directly:

```
SGD (nex.colleague*) ──dumpColleague.py──▶ colleague.json ──load_sgd_colleagues.py──▶ ABC
```

| File | Repo | Role |
|---|---|---|
| `dumpColleague.py` | SGDBackend-Nex2 (this dir) | Extract SGD colleague data → one JSON file |
| `load_sgd_colleagues.py` | agr_literature_service `lit_processing/oneoff_scripts/` | Sync that JSON into ABC |
| `SGD_to_ABC_mapping.md` | this dir | Field-by-field SGD → ABC column mapping |

## 1. Dump (in SGDBackend-Nex2)

```bash
set -a; source .env_cc; set +a            # provides NEX2_URI (SGD QA)
PYTHONPATH=. python scripts/dumping/colleague/dumpColleague.py \
    --outfile scripts/dumping/colleague/data/colleague.json
```

The JSON holds every colleague (with embedded research-summary/lab URLs and
keywords), `lab_relations` (Head-of-Lab PI↔member edges), `associate_relations`
(deduped collaborator pairs), and a `metadata` block of source counts. Do **not**
commit the JSON data file.

## 2. Load / sync (in agr_literature_service)

```bash
set -a; source .env_cc; set +a            # ABC: PSQL_*, ID_MATI_URL, ENV_STATE
# the .env_cc XML_PATH is a server path; override it to a writable local dir
export XML_PATH=/tmp/sgd_load PYTHONPATH=.

# read-only dry-run (default) — previews exact add/update/delete counts
venv/bin/python -m agr_literature_service.lit_processing.oneoff_scripts.load_sgd_colleagues \
    --datafile /path/to/colleague.json

# apply: add new + update changed (no deletes)
... load_sgd_colleagues --datafile colleague.json --commit

# apply incl. deleting colleagues/labs/lineage that left SGD
... load_sgd_colleagues --datafile colleague.json --commit --prune

# one-time repair of existing email duplicates
... load_sgd_colleagues --datafile colleague.json --commit --merge-email-dups
```

### Flags
| Flag | Effect |
|---|---|
| `--datafile PATH` | (required) the JSON produced by `dumpColleague.py` |
| `--commit` | write to ABC; without it the run is a read-only dry-run |
| `--prune` | also DELETE rows whose `colleague_id`/PI left the dump (full run only; ignored with `--limit`) |
| `--merge-email-dups` | merge an SGD person into a pre-existing non-SGD person sharing its email |
| `--limit N` | process only the first N colleagues (testing) |
| `--outdir DIR` | where dry-run TSV previews are written |

## Behavior

**Incremental sync, keyed on `colleague_id`.** Re-runnable whenever SGD changes:
adds new colleagues, updates changed ones (SGD is the source of truth, only
differing rows are written), and — with `--prune` — deletes those removed from
SGD. The default dry-run runs the same code with writes suppressed and rolled
back, so its counts match a commit exactly. Re-runs are convergent (a no-op when
SGD is unchanged).

**Email de-duplication.** A colleague new to ABC whose email already belongs to
a pre-existing *non-SGD* person (e.g. AGR staff/author) is attached to that
person rather than duplicated. Matching is restricted to non-SGD persons because
institutional emails are shared by distinct colleagues. `--merge-email-dups`
repairs such duplicates that already exist (one non-SGD + one SGD person per
email); ambiguous groups are reported and skipped.

**Delete safety.** Hard deletes never remove a person linked to a `users`
account or a lab with `laboratory_allele_designation` rows (reported instead);
collaborator_of deletes only touch edges between two SGD persons.

**Cost.** In `--commit` mode each newly created person/laboratory consumes one
real MATI id (`ENV_STATE != 'test'`); updates, deletes and merges consume none.

See **[SGD_to_ABC_mapping.md](SGD_to_ABC_mapping.md)** for the full field mapping.
