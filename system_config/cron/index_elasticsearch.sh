#!/bin/sh

OUTPUT_FILE=/tmp/index_elasticsearch.out

echo "index_elasticsearch.sh start:  `/bin/date`" | /bin/tee $OUTPUt_FILE

cd /data/www/SGDBackend-Nex2

# elasticsearch 7 script
. venv/bin/activate && \
    python scripts/search/index_es_7.py | /bin/tee -a $OUTPUt_FILE

echo "index_elasticsearch.sh end:  `/bin/date`" | /bin/tee -a $OUTPUt_FILE

/bin/mail -s "index_elasticsearch.sh: `/bin/date`" $CRON_EMAIL < $OUTPUT_FILE
