#! /bin/sh

cd /data/www/SGDBackend-Nex2
source venv/bin/activate 
source prod_variables.sh

export PYTHONPATH=/data/www/SGDBackend-Nex2

LOG=/data/www/logs/reference_update.log

python scripts/loading/reference/reference_update_from_abc.py > "$LOG" 2>&1
# python scripts/loading/reference/reference_update_non_pubmed_from_abc.py >> "$LOG" 2>&1
python scripts/loading/reference/reference_display_name_update.py >> "$LOG" 2>&1
python scripts/dumping/ncbi/dump_gene_pmid_pair.py >> "$LOG" 2>&1


