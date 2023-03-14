#! /bin/sh

echo "index_elasticsearch.sh start:  `/bin/date`"

cd /data/www/SGDBackend-Nex2

echo "index_elasticsearch.sh start:  `/bin/date`"

# elasticsearch 7 script
. venv/bin/activate && python scripts/search/index_es_7.py

echo "index_elasticsearch.sh end:  `/bin/date`"
