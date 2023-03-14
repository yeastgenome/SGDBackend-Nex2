#! /bin/sh

cd /data/www/SGDBackend-Nex2

# elasticsearch 7 script
. venv/bin/activate && python scripts/search/index_es_7.py
