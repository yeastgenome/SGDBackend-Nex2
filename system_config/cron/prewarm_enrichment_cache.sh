#!/bin/sh

cd /data/www/SGDBackend-Nex2
if [ -f ./qa.sh ]; then
    . ./qa.sh
else
    . ./prod_variables.sh
fi
bash scripts/prewarm_enrichment_cache.sh > /data/www/logs/prewarm_enrichment.log 2>&1
