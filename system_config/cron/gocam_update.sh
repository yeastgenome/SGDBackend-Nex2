#! /bin/sh

cd /data/www/SGDBackend-Nex2
source venv-py39/bin/activate
source prod_variables.sh
python -m scripts.loading.pathway.load_gocam_url
python -m scripts.loading.pathway.load_complex_gocam_url
