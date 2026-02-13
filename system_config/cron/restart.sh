#! /bin/sh

cd /data/www/SGDBackend-Nex2
source /data/www/venv/bin/activate
. prod_variables.sh
/usr/bin/make stop-prod >/dev/null
/usr/bin/make run-prod >/dev/null
