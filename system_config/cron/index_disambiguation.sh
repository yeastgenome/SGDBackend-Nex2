#!/bin/sh

cd /data/www/SGDBackend-Nex2
source venv/bin/activate && source prod_variables.sh && python scripts/disambiguation/index_disambiguation.py
