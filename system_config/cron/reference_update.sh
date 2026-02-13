#!/bin/sh
set -e

cd /data/www/SGDBackend-NEX2
. venv/bin/activate
. ./prod_variables.sh

# set credentials to access ABC
export AWS_ACCESS_KEY_ID=$ABC_AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$ABC_AWS_SECRET_ACCESS_KEY

export PYTHONPATH=/data/www/SGDBackend-NEX2

LOG=/data/www/logs/reference_update.log

python /data/www/SGDBackend-Nex2/scripts/loading/reference/reference_update_from_abc.py > "$LOG" 2>&1
# python /data/www/SGDBackend-Nex2/scripts/loading/reference/reference_update_non_pubmed_from_abc.py >> "$LOG" 2>&1

unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY

python /data/www/SGDBackend-Nex2/scripts/loading/reference/reference_display_name_update.py >> "$LOG" 2>&1
python /data/www/SGDBackend-Nex2/scripts/dumping/ncbi/dump_gene_pmid_pair.py >> "$LOG" 2>&1

