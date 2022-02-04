#! /bin/sh


cd /data/www/SGDBackend-NEX2
source /data/www/venv/bin/activate 
source prod_variables.sh 
python scripts/loading/reference/reference_update.py
python scripts/loading/reference/reference_display_name_update.py
python scripts/dumping/ncbi/dump_gene_pmid_pair.py
