#! /bin/sh

cd /data/www/SGDBackend-NEX2/current
source /data/envs/sgd3/bin/activate 
source prod_variables.sh 
python scripts/loading/dbxref/update_dbxref.py
python scripts/loading/locus/load_RNAcentral_IDs.py

