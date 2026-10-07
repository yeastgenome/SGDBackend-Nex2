#! /bin/sh
# Weekly phenotype author outreach emails, Mondays 8 PM Pacific; see
# scripts/dumping/outreach/phenotype_weekly_email_pipeline.sh
#
# The host clock is UTC and cron cannot follow daylight saving time, so the
# crontab fires this at both 03:00 and 04:00 UTC on Tuesday:
#   0 3 * * 2 /bin/bash .../system_config/cron/phenotype_outreach_email.sh
#   0 4 * * 2 /bin/bash .../system_config/cron/phenotype_outreach_email.sh
# and only the run that lands on Monday 20:00 in Los Angeles proceeds (the
# other exits silently, so cron mails nothing for it).
if [ "$(TZ=America/Los_Angeles date +%u%H)" != "120" ]; then
    exit 0
fi

cd /data/www/SGDBackend-Nex2
source venv/bin/activate
source prod_variables.sh

# MUST only run on sgd-curate: it holds the one canonical sent log, and its
# postfix relays through SES -- running elsewhere would double-email authors.
if [ "$(hostname)" != "ip-172-31-48-169" ]; then
    echo "not sgd-curate; skipping phenotype outreach emails"
    exit 0
fi
sh scripts/dumping/outreach/phenotype_weekly_email_pipeline.sh --send
