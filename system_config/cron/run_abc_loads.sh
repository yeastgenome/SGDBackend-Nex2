#! /bin/sh
set -e

cd /data/www/SGDBackend-NEX2/current
. /data/envs/sgd3/bin/activate
. ./prod_variables.sh

export PYTHONPATH=/data/www/SGDBackend-NEX2/current

LOG=/data/www/logs/abc_loads.log
echo "===== $(date): Starting ABC loads =====" >> "$LOG"

python scripts/loading/reference/load_new_references_from_abc.py >> "$LOG" 2>&1
python scripts/loading/reference/load_tet_from_abc.py          >> "$LOG" 2>&1

echo "===== $(date): ABC loads finished =====" >> "$LOG"
