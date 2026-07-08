#! /bin/sh

cd /data/www/SGDBackend-Nex2
source /data/www/venv/bin/activate && source prod_variables.sh && python src/loading/scrapy/pages/spiders/pages_spider.py
