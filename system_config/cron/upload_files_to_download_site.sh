#! /bin/sh

cd /data/www/SGDBackend-Nex2/current/
source /data/envs/sgd3/bin/activate 
source prod_variables.sh

python scripts/dumping/tab_files_for_download_site/generate_allele_file.py
python scripts/dumping/tab_files_for_download_site/generate_dbxref_file.py
python scripts/dumping/tab_files_for_download_site/generate_deleted_merged_features_file.py
python scripts/dumping/tab_files_for_download_site/generate_functional_complementation_file.py
python scripts/dumping/tab_files_for_download_site/generate_gene_literature_file.py
python scripts/dumping/tab_files_for_download_site/generate_go_protein_complex_file.py
python scripts/dumping/tab_files_for_download_site/generate_go_terms_file.py
python scripts/dumping/tab_files_for_download_site/generate_interaction_file.py
python scripts/dumping/tab_files_for_download_site/generate_molecular_complex_file.py
python scripts/dumping/tab_files_for_download_site/generate_pathway_file.py
python scripts/dumping/tab_files_for_download_site/generate_phenotype_file.py
python scripts/dumping/tab_files_for_download_site/generate_protein_properties.py
python scripts/dumping/tab_files_for_download_site/generate_regulation_file.py
python scripts/dumping/tab_files_for_download_site/generate_sgd_features.py
python scripts/dumping/tab_files_for_download_site/generate_yeast_human_disease_file.py
python scripts/dumping/s3/upload_files_for_download_site.py
