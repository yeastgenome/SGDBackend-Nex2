#!/bin/sh

cd /data/www/SGDBackend-NEX2/current
source /data/envs/sgd3/bin/activate 
source prod_variables.sh 
python scripts/checking/check_feature.py
python scripts/checking/check_go.py
python scripts/checking/check_reference.py
python scripts/checking/check_phenotype.py
python scripts/checking/check_paragraph_etc.py
python scripts/checking/check_ontology.py
python scripts/checking/check_NTR.py
python scripts/checking/check_suppl_files.py
python scripts/checking/check_gene_name_reservation.py
