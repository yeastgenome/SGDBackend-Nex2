.PHONY: test lib config build prod-build run restart start stop status logs

SHELL := /bin/bash

# Canonical runtime: the systemd service $(SERVICE) runs ./start.sh, which execs
# pserve from the Python 3.9 venv below. Python deps MUST go into this venv or
# the service crash-loops (installed pkg vs shared egg-info mismatch). Override
# with e.g. `make VENV=venv prod-build`.
VENV    ?= venv-py39
SERVICE ?= sgd-backend.service

build:
	npm install
	npm run build
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/pip install -e . --no-deps

prod-build:
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/pip install -e . --no-deps

run:
	source dev_variables.sh && $(VENV)/bin/pserve development.ini --reload

# --- service control (systemd; the canonical QA/runtime mechanism) -----------
restart:
	sudo systemctl restart $(SERVICE)
	@sleep 4 && systemctl is-active $(SERVICE)

start:
	sudo systemctl start $(SERVICE)

stop:
	sudo systemctl stop $(SERVICE)

status:
	systemctl status $(SERVICE) --no-pager

logs:
	sudo tail -n 100 -f /var/log/sgd-backend/error.log

NOSEOPTS ?=

tests:
	source test_variables.sh && nosetests -s $(NOSEOPTS)

npm-tests:
	npm test

# LEGACY (Capistrano): the `cap ... deploy` targets below predate the systemd +
# start.sh + venv-py39 setup and are no longer the canonical QA deploy path.
qa-index-redis:
	source dev_variables.sh && NEX2_URI=$$QA_NEX2_URI && cap qa deploy:redis

qa-deploy:
	source dev_variables.sh && NEX2_URI=$$QA_NEX2_URI && cap qa deploy

qa-restart:
	source dev_variables.sh && NEX2_URI=$$QA_NEX2_URI && cap qa deploy:restart

curate-deploy:
	npm run build:dev && source dev_variables.sh && NEX2_URI=$$CURATE_NEX2_URI && cap curate_dev deploy

preview-deploy:
	source dev_variables.sh && NEX2_URI=$$CURATE_NEX2_URI && cap preview deploy

deploy:
	npm run build && source dev_variables.sh && cap dev deploy

staging-deploy:
	source prod_variables.sh && cap staging deploy

curate-staging-deploy:
	npm run build && source prod_variables.sh && NEX2_URI=$$CURATE_NEX2_URI && CACHE_URLS=$$STAGING_CACHE_URLS && cap curate_staging deploy

curate-prod-deploy:
	npm run build && source prod_variables.sh && NEX2_URI=$$CURATE_NEX2_URI && cap curate_prod deploy

prod-deploy:
	npm run build && source prod_variables.sh && cap prod deploy

# LEGACY (pre-systemd): direct pserve daemon. Superseded by the systemd service
# ($(SERVICE)) via start.sh -> venv-py39. Kept for reference / non-QA hosts.
run-prod:
	$(VENV)/bin/pserve production.ini --daemon --pid-file=/var/run/pyramid/backend.pid

stop-prod:
	-$(VENV)/bin/pserve production.ini --stop-daemon --pid-file=/var/run/pyramid/backend.pid

lint:
	eslint src/client/js/

refresh-cache:
	source dev_variables.sh && python src/loading/scrapy/pages/spiders/pages_spider.py

index-es:
	source dev_variables.sh && python scripts/search/index_elastic_search.py

index-es7:
	source dev_variables.sh && python scripts/search/index_es_7.py

index-es-prod:
	source prod_variables.sh && python scripts/search/index_elastic_search.py

index-redis:
	source dev_variables.sh && python scripts/disambiguation/index_disambiguation.py


bgi-dev:
	source dev_variables.sh && python scripts/bgi_json/bgi.py
bgi-prod:
	source prod_variables.sh && python scripts/bgi_json/bgi.py

upload-expression-details:
	source dev_variables.sh && python scripts/loading/upload_expression_details.py

load-triage:
	source dev_variables.sh && python scripts/loading/load_reference_triage.py

crawl-site:
	source prod_variables.sh && python src/loading/scrapy/pages/spiders/pages_spider.py

load-files:
	source dev_variables.sh && CREATED_BY=fgondwe python scripts/loading/files/upload_files_fdb.py

tests-dev:
	source dev_variables.sh && python test/test_dev.py


# docker commands
# run local elasticsarch service
es-up:
	docker-compose up -d

es-down:
	docker-compose down
