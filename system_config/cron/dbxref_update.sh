#! /bin/sh

cd /data/www/SGDBackend-Nex2
source venv/bin/activate 
source prod_variables.sh 
python scripts/loading/dbxref/update_dbxref.py
python scripts/loading/locus/load_RNAcentral_IDs.py

