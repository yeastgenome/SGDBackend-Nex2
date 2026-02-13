#! /bin/sh

cd /data/www/SGDBackend-Nex2
source /data/www/venv/bin/activate && source prod_variables.sh && CREATED_BY=fgondwe python scripts/loading/files/upload_files_fdb.py
