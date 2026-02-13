#! /bin/sh

cd /data/www/SGDBackend-Nex2
source /data/www/venv/bin/activate && source prod_variables.sh && python scripts/loading/load_reference_triage.py &>> /data/www/logs/triage_worker.log
