#! /bin/sh

cd /data/www/SGDBackend-NEX2/current
source /data/envs/sgd3/bin/activate 
source prod_variables.sh 
python scripts/dumping/alliance/affectedGeneModel.py
python scripts/dumping/alliance/affectedGeneModelPersistent.py
python scripts/dumping/alliance/alleles.py
python scripts/dumping/alliance/allelesPersistent.py
python scripts/dumping/alliance/basic_gene_information.py
python scripts/dumping/alliance/bgiPersistent.py
python scripts/dumping/alliance/disease.py
python scripts/dumping/alliance/disease_persistent.py
python scripts/dumping/alliance/expression.py
python scripts/dumping/alliance/htp_datasamples.py
python scripts/dumping/alliance/htp_datasets.py
python scripts/dumping/alliance/phenotype.py
