#! /bin/sh

cd /data/www/SGDBackend-Nex2
source venv/bin/activate 
source prod_variables.sh 
python scripts/loading/suppl_files/download_pubmed_PMC_files.py

