#!/bin/bash
cd /data/www/SGDBackend-Nex2
. /data/www/SGDBackend-Nex2/qa.sh
exec /data/www/SGDBackend-Nex2/venv-py39/bin/pserve development.ini
