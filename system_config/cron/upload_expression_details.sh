#! /bin/sh

cd /data/www/SGDBackend-Nex2
source venv/bin/activate && source prod_variables.sh && python scripts/loading/upload_expression_details.py &>> /data/www/logs/expression_worker.log
