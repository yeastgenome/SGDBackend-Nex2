#! /bin/sh

cd /data/www/SGDBackend-Nex2
. /data/www/venv/bin/activate && . prod_local_variables.sh && python scripts/disambiguation/index_disambiguation.py
