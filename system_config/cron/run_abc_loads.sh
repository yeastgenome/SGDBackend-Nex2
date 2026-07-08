#! /bin/sh

cd /data/www/SGDBackend-Nex2
source venv/bin/activate
source prod_variables.sh

export PYTHONPATH=/data/www/SGDBackend-Nex2

python scripts/loading/reference/load_new_references_from_abc.py
python scripts/loading/reference/load_tet_from_abc.py

