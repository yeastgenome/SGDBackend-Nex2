#!/bin/sh
# Nightly GO enrichment cache pre-warm. Pass BACKEND_URLS / PASSES through
# from the crontab line when warming remote nodes via the LB, e.g.
#   30 10 * * * BACKEND_URLS="https://backend.yeastgenome.org" PASSES=4 \
#       /bin/bash /data/www/SGDBackend-Nex2/system_config/cron/prewarm_enrichment_cache.sh

cd /data/www/SGDBackend-Nex2
if [ -f ./activate_env.sh ]; then
    . ./activate_env.sh
fi
if [ -f ./qa.sh ]; then
    . ./qa.sh
elif [ -f ./prod_variables.sh ]; then
    . ./prod_variables.sh
else
    . ./prod.sh
fi
bash scripts/prewarm_enrichment_cache.sh > /data/www/logs/prewarm_enrichment.log 2>&1
