FROM ubuntu:20.04

RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
        awscli \
	git \
        make \
	npm \
	postfix \
        python3-pip \
	tzdata

WORKDIR /data/www
RUN git clone https://github.com/yeastgenome/SGDBackend-Nex2.git

WORKDIR /data/www/logs

WORKDIR /data/www/SGDBackend-Nex2
RUN git checkout master_docker \
    && pip3 install virtualenv \
    && virtualenv venv \
    && . venv/bin/activate \
    && pip3 install -U setuptools==57.5.0 \
    && make build \
    && chmod 755 /data/www/SGDBackend-Nex2/system_config/cron/*

CMD ["sh", "-c", ". /data/www/SGDBackend-Nex2/venv/bin/activate && pserve $INI_FILE --reload"]
