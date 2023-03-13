#! /bin/sh

echo "index_disambiguation.sh start:  `/bin/date`"

cd /data/www/SGDBackend-Nex2
. venv/bin/activate && python scripts/disambiguation/index_disambiguation.py

echo "index_disambiguation.sh end:  `/bin/date`"
