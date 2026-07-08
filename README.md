# SGDBackend-Nex2

[![Build Status](https://travis-ci.org/yeastgenome/SGDBackend-Nex2.svg)](https://travis-ci.org/yeastgenome/SGDBackend-Nex2) [![Coverage Status](https://coveralls.io/repos/github/yeastgenome/SGDBackend-Nex2/badge.svg?branch=qa)](https://coveralls.io/github/yeastgenome/SGDBackend-Nex2?branch=qa)

A restful web service for the Saccharomyces Genome Database (SGD) NEX 2, as well as an authenticated curation interface.

SGD API documentation can be found at https://github.com/yeastgenome/SGDBackend-Nex2/blob/master/docs/webservice.MD.

## Setup

Prerequisites: node.js 6.0.0+, Python 3 (to simplify Python setup, virtualenv is highly suggested), and redis.

Make sure you have the needed environmental variables configured in dev_variables.sh, then

    $ make build

If `npm install` fails with:

    npm ERR! ERESOLVE unable to resolve dependency tree

and your npm install is newer (this happens at least for 7.18.1) then running again with `npm install --legacy-peer-deps` should work.

Lastly, `npm run build` may emit error messages, but everything will continue fine. Ticket for existing errors here: https://redmine.yeastgenome.org/issues/6040


## Run Locally

To run locally you must have a running instance of Redis. On Ubuntu style Linux systems after installing with `apt-get install redis` a redis service should have been started.

This can be turned on and off with `$ service redis start|stop`. Running a redis instance directly is also possible by `$ redis-server` as long as the redis service is stopped first.

Ensure also that dev_variables.sh is present in the Makefile directory.

    $ make run

Running locally will start the backend web service which will point to dev databases. In order to access data in the database with some endpoints (like `/annotations` which rely on being logged in) you'll need a user in the databases.

Navigating a browser to http://localhost:6543/ will show the home login screen. If you have a database user you can then log in.

Not all endpoints require credentials, however. As a test to prove you're getting real data, you can go to http://localhost:6543/complex/CPX-863 which should display JSON.

## Run Tests

Be sure to have a test_variables.sh file to configure test environemntal variables.

    $ make tests

This command runs just the Python tests. To run just the JavaScript tests use

    $ npm test

or

    $ make npm-tests

## QA Security Upgrade Notes

On `sgd-backend-qa`, the backend has been upgraded in a parallel virtualenv to
address CVE-2026-42304 / GHSA-grgv-6hw6-v9g4 for Twisted.

The QA runtime is:

    /data/www/SGDBackend-Nex2/venv-py39/bin/python
    /data/www/SGDBackend-Nex2/venv-py39/bin/pserve development.ini

The original Python 3.8 virtualenv is still present at:

    /data/www/SGDBackend-Nex2/venv

The QA dependency changes are:

    cryptography==43.0.3
    pyOpenSSL==24.2.1
    twisted==26.4.0rc2
    pandas==1.5.3

The QA host was verified with:

    python --version
    python -c "import twisted, OpenSSL, cryptography, pandas; print(twisted.__version__, OpenSSL.__version__, cryptography.__version__, pandas.__version__)"
    pip check
    curl -sS -o /tmp/sgd-qa-root.out -w "%{http_code} %{size_download}\n" http://127.0.0.1:6543/

Expected results include Python `3.9.25`, Twisted `26.4.0rc2`,
pyOpenSSL `24.2.1`, cryptography `43.0.3`, pandas `1.5.3`, no broken
requirements, and HTTP `200` from the local backend.

QA startup files were updated to use `venv-py39`:

    start.sh
    activate_env.sh

Rollback on QA is to restore `start.sh` from:

    start.sh.bak-before-py39

Then restart the backend so it uses the original Python 3.8 virtualenv again.
Do not remove `venv` or `venv-py39` until production rollout and rollback
requirements are settled.


### Varnish Cache and Rebuilding the cache

Caching uses [varnish](https://varnish-cache.org/).  To rebuild the cache, run

    $ source /data/envs/sgd/bin/activate && source prod_variables.sh && python src/loading/scrapy/pages/spiders/pages_spider.py

using environmental variable `CACHE_URLS`, a comma-sepratated list of varshish host URLs (or a single one) such as `http://locahost:5000`.
