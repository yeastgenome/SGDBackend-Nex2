#! /bin/sh

cd /data/www/SGDBackend-NEX2
source /data/www/venv/bin/activate 
source prod_variables.sh 
python scripts/loading/dbxref/update_dbxref.py

