#! /bin/sh
# Weekly disease author outreach emails, Mondays 6 PM Pacific -- an hour
# before the regulation run (7 PM), two before phenotype (8 PM) and ahead of
# the GO run at the end of go_update.sh (Tue 03:30 UTC), so they never share
# the email-resolver cache at once;
# see scripts/dumping/outreach/disease_weekly_email_pipeline.sh
#
# The host clock is UTC and cron cannot follow daylight saving time, so the
# crontab fires this at both 01:00 and 02:00 UTC on Tuesday:
#   0 1 * * 2 /bin/bash .../system_config/cron/disease_outreach_email.sh
#   0 2 * * 2 /bin/bash .../system_config/cron/disease_outreach_email.sh
# and only the run that lands on Monday 18:00 in Los Angeles proceeds (the
# other exits silently, so cron mails nothing for it).
if [ "$(TZ=America/Los_Angeles date +%u%H)" != "118" ]; then
    exit 0
fi

cd /data/www/SGDBackend-Nex2
source venv/bin/activate
source prod_variables.sh

# MUST only run on sgd-curate: it holds the one canonical sent log, and its
# postfix relays through SES -- running elsewhere would double-email authors.
if [ "$(hostname)" != "ip-172-31-48-169" ]; then
    echo "not sgd-curate; skipping disease outreach emails"
    exit 0
fi
sh scripts/dumping/outreach/disease_weekly_email_pipeline.sh --send
