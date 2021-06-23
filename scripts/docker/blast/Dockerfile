FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y \
    apache2 \
    libapache2-mod-wsgi-py3 \
    net-tools \
    python3-pip \
    wget
 
RUN mkdir /tools && cd /tools && \
    wget https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/ncbi-blast-2.11.0+-x64-linux.tar.gz && \
    tar -zxvf ncbi-blast-2.11.0+-x64-linux.tar.gz && \
    ln -s ncbi-blast-2.11.0+ blast && \
    rm ncbi-blast-2.11.0+-x64-linux.tar.gz

RUN cd /var/www && mkdir conf logs FlaskApp && cd FlaskApp && \
    mkdir FlaskApp && cd FlaskApp && mkdir venv static templates

RUN pip3 install Flask && pip3 install -U flask-cors 

COPY www /var/www/
COPY FlaskApp.conf /etc/apache2/sites-available/

RUN mkdir -p /data/blast/fungi

#RUN a2ensite FlaskApp

RUN a2enmod wsgi && a2ensite FlaskApp && a2dissite 000-default

RUN pip3 install virtualenv 

RUN cd /var/www/FlaskApp/FlaskApp && virtualenv venv

RUN #!/bin/bash . venv/bin/activate

CMD ["apachectl", "-D", "FOREGROUND"]
