#! /bin/sh
cd /data/www/SGDBackend-Nex2
source /data/www/venv/bin/activate 
source prod_variables.sh 

python scripts/loading/goslim/generate_goslimannotation_data.py yeast
python scripts/loading/goslim/generate_goslimannotation_data.py generic
python scripts/loading/goslim/generate_goslimannotation_data.py complex
python scripts/loading/goslim/process_goslimannotation_data.py
/usr/bin/sort scripts/loading/goslim/data/goslimannotation_data_all.txt > scripts/loading/goslim/data/goslimannotation_data_all_sorted.txt
python scripts/loading/goslim/update_goslimannotation_data.py

python scripts/loading/goslim/generate_genome_count.py
python scripts/loading/goslim/update_goslim_data.py
python scripts/dumping/curation/dump_goslim_mapping.py

