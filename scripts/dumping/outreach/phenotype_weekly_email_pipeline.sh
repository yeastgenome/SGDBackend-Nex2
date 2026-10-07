#!/bin/sh
# Weekly phenotype author outreach: email the authors of papers behind
# phenotype annotations added since the last run. Chain:
#
#   extract_new_phenotype_annotations.py  (pmid, gene) pairs from the DB
#                                         with date_created >= $SINCE
#   resolve_pmid_emails.py --pmid-file    emails from ABC API -> PubMed -> PMC
#   send_phenotype_annotation_emails.py   one email per (PMID, author email);
#                                         the sent log guarantees a gene is
#                                         never mentioned to the same author
#                                         for the same paper twice
#
# Called every Monday from system_config/cron/phenotype_outreach_email.sh
# with --send. Needs NEX2_URI (prod_variables.sh) and a python with
# sqlalchemy (the repo venv). Run manually with --dry-run (previews only,
# default) or --test (emails go to the test recipients) to inspect a batch
# before a production send.
#
# SINCE = last successful --send run minus a buffer, never before
# 2026-01-01. The buffer lets a paper whose author email only becomes
# resolvable later (e.g. added to ABC) still get its email; the sent log
# makes the overlap cost lookups only, never duplicate emails.

set -e
cd "$(dirname "$0")"

MODE="${1:---dry-run}"
STATE_FILE=phenotype_weekly_email_pipeline.state
SENT_LOG=sgd_phenotype_email_sent_log.tsv
SINCE_DEFAULT=2026-01-01
BUFFER_DAYS=120

SINCE=$SINCE_DEFAULT
if [ -s "$STATE_FILE" ]; then
    SINCE=$(date -d "$(cat "$STATE_FILE") -${BUFFER_DAYS} days" +%F)
    if [ "$(printf '%s\n%s\n' "$SINCE" "$SINCE_DEFAULT" | sort | head -1)" = "$SINCE" ]; then
        SINCE=$SINCE_DEFAULT
    fi
fi
echo "mode=$MODE since=$SINCE"

python3 extract_new_phenotype_annotations.py --since "$SINCE" \
    -o sgd_phenotype_new_annotations.tsv

python3 resolve_pmid_emails.py --pmid-file sgd_phenotype_new_annotations.tsv \
    -o sgd_phenotype_emails.tsv -d data

if [ "$MODE" = "--dry-run" ]; then
    python3 send_phenotype_annotation_emails.py -a sgd_phenotype_new_annotations.tsv \
        -e sgd_phenotype_emails.tsv -l "$SENT_LOG" -d data
else
    python3 send_phenotype_annotation_emails.py -a sgd_phenotype_new_annotations.tsv \
        -e sgd_phenotype_emails.tsv -l "$SENT_LOG" -d data "$MODE"
fi

# only mark a successful production run; test/dry runs must not move the window
if [ "$MODE" = "--send" ]; then
    date +%F > "$STATE_FILE"
fi
