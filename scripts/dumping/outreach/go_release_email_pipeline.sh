#!/bin/sh
# GO-release author outreach pipeline: after a GPAD load, email the authors
# of papers behind new gene-centric SGD GO annotations. Chain:
#
#   resolve_pmid_emails.py          PMIDs from YEAST-mod.gpad since $SINCE;
#                                   emails from ABC API -> PubMed -> PMC
#   map_emails_to_go_annotations.py join emails to annotations, split
#                                   gene-centric / pathway / non-noctua
#   send_go_annotation_emails.py    send one email per (PMID, author email);
#                                   the sent log guarantees a pair is only
#                                   ever emailed once, so re-runs are safe
#
# Called from system_config/cron/go_update.sh with --send, only when both
# load_gpad.py runs exited 0. Run manually with --dry-run (previews only,
# default) or --test (emails go to the test recipients) to inspect a release
# before a production send.
#
# SINCE = last successful run minus a buffer that covers GO's GPAD release
# lag; annotations already emailed are skipped via the sent log, so an overly
# wide window only costs redundant lookups, never duplicate emails.

set -e
cd "$(dirname "$0")"

MODE="${1:---dry-run}"
STATE_FILE=go_release_email_pipeline.state
SENT_LOG=sgd_go_email_sent_log.tsv
SINCE_DEFAULT=2026-01-01
BUFFER_DAYS=120

if [ -s "$STATE_FILE" ]; then
    SINCE=$(date -d "$(cat "$STATE_FILE") -${BUFFER_DAYS} days" +%F)
else
    SINCE=$SINCE_DEFAULT
fi
echo "mode=$MODE since=$SINCE"

# always work from the current GO release, not a cached one
rm -f data/YEAST-mod.gpad.gz data/YEAST-mod.gpi.gz

python3 resolve_pmid_emails.py --since "$SINCE" \
    -o sgd_go_release_emails.tsv -d data

python3 map_emails_to_go_annotations.py -e sgd_go_release_emails.tsv \
    -o sgd_email_pmid_go_annotations.tsv -d data

# never email an author about an annotation that load_gpad.py skipped:
# keep only (pmid, gene) pairs the SGD site actually shows, checked via the
# public backend API (no database credentials needed)
python3 verify_annotations_on_site.py \
    -i sgd_email_pmid_go_annotations_gene_centric.tsv \
    -o sgd_email_pmid_go_annotations_gene_centric_verified.tsv
SEND_INPUT=sgd_email_pmid_go_annotations_gene_centric_verified.tsv

if [ "$MODE" = "--dry-run" ]; then
    python3 send_go_annotation_emails.py -i "$SEND_INPUT" \
        --since "$SINCE" -l "$SENT_LOG" -d data
else
    python3 send_go_annotation_emails.py -i "$SEND_INPUT" \
        --since "$SINCE" -l "$SENT_LOG" -d data "$MODE"
fi

# only mark a successful production run; test/dry runs must not move the window
if [ "$MODE" = "--send" ]; then
    date +%F > "$STATE_FILE"
fi
