#! /bin/sh

cd /data/www/SGDBackend-NEX2
source /data/www/venv/bin/activate 
source prod_variables.sh 
python scripts/dumping/s3/copy_active_files.py
