#! /bin/sh
# Weekly S3 backup of the author outreach email sent logs and pipeline state.
#
# The sent logs are what stop the GO and phenotype outreach pipelines from
# emailing the same author twice; they are gitignored (author emails), so
# without this copy a lost checkout would re-send every past email.
#
# Runs Wednesday 12:00 UTC, after the phenotype (Tue 03:00/04:00 UTC) and GO
# (go_update.sh, Tue/Wed 03:30 UTC) runs:
#   0 12 * * 3 /bin/bash /data/www/SGDBackend-Nex2/system_config/cron/backup_outreach_logs.sh
#
# Each file goes to latest/ (overwritten) and to a dated folder. The bucket
# blocks public access and is versioned, so earlier copies stay recoverable.
# Restore: aws s3 cp s3://sgd-prod-server-data/outreach/latest/<file> .

# the canonical logs live on sgd-curate only
if [ "$(hostname)" != "ip-172-31-48-169" ]; then
    echo "not sgd-curate; skipping outreach log backup"
    exit 0
fi

cd /data/www/SGDBackend-Nex2
. ./prod_variables.sh > /dev/null 2>&1

OUTREACH_DIR=scripts/dumping/outreach
S3_PREFIX=s3://sgd-prod-server-data/outreach
TODAY=$(date -u +%Y-%m-%d)
FILES="sgd_go_email_sent_log.tsv
sgd_phenotype_email_sent_log.tsv
go_release_email_pipeline.state
phenotype_weekly_email_pipeline.state"

status=0
for f in $FILES; do
    if [ ! -s "$OUTREACH_DIR/$f" ]; then
        echo "WARNING: $OUTREACH_DIR/$f is missing or empty; not backed up"
        status=1
        continue
    fi
    for dest in "$S3_PREFIX/latest/$f" "$S3_PREFIX/$TODAY/$f"; do
        if ! aws s3 cp --only-show-errors --sse AES256 "$OUTREACH_DIR/$f" "$dest"; then
            echo "ERROR: upload of $f to $dest failed"
            status=1
        fi
    done
done
exit $status
