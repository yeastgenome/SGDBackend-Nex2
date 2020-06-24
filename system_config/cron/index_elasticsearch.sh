#! /bin/sh

cd /data/www/SGDBackend-NEX2/current
# elasticsearch 2.4 script
#source /data/envs/sgd3/bin/activate && source prod_variables.sh && python scripts/search/index_elastic_search.py

# elasticsearch 7 script
source /data/envs/sgd3/bin/activate && source prod_variables.sh && python scripts/search/index_es_7.py
