#! /bin/sh

cd /data/www/SGDBackend-NEX2

# elasticsearch 7 script
source /data/www/venv/bin/activate && source prod_variables.sh && python scripts/search/index_es_7.py
