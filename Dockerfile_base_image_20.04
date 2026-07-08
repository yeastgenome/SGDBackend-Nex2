# instead of standard Ubuntu 20.04 base image (which has been EOL'd), use sgd-backend image which has most up to date Ubuntu 20.04 release

FROM public.ecr.aws/yeastgenome/sgd-backend:base-20250827

# these packages are already installed in the sgd-backend base image

#RUN DEBIAN_FRONTEND=noninteractive apt-get update \
#    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y \
#    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
#	awscli \
#	curl \
#	git \
#        make \
#	npm \
#	postfix \
#        python3-pip \
#	tzdata \
#	unzip

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -r aws awscliv2.zip \
    && DEBIAN_FRONTEND=noninteractive apt-get purge -y curl unzip

WORKDIR /data/www
RUN rm -rf SGDBackend-Nex2 \
    && git clone https://github.com/yeastgenome/SGDBackend-Nex2.git

WORKDIR /data/www/logs

WORKDIR /data/www/SGDBackend-Nex2
RUN git checkout master_docker \
    && pip3 install virtualenv \
    && virtualenv venv \
    && . venv/bin/activate \
    && pip3 install -U setuptools==57.5.0 \
    && make build \
    && chmod 755 /data/www/SGDBackend-Nex2/system_config/cron/* \
    && echo 'export $(strings /proc/1/environ | grep AWS_CONTAINER_CREDENTIALS_RELATIVE_URI)' >> /root/.profile

#CMD ["sh", "-c", ". /data/www/SGDBackend-Nex2/venv/bin/activate && pserve $INI_FILE --reload"]
CMD ["/bin/bash --reload"]
