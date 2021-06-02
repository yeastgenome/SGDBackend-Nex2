FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt update && apt-get --yes install wget
 
RUN mkdir /tools/ && cd /tools/ && \
    wget https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/ncbi-blast-2.11.0+-x64-linux.tar.gz && \
    tar -zxvf ncbi-blast-2.11.0+-x64-linux.tar.gz && \
    ln -s ncbi-blast-2.11.0+ blast

RUN mkdir /var/www && cd /var/www && mkdir conf logs FlaskApp && cd FlaskApp && \
    mkdir FlaskApp && cd FlaskApp && mkdir venv static templates

COPY blast-sgd.json /var/www/conf
COPY blast-fungal.json /var/www/conf
COPY __init__.py /var/www/FlaskApp/FlaskApp/
COPY blast.py /var/www/FlaskApp/FlaskApp/
COPY blast_markup.py /var/www/FlaskApp/FlaskApp/
COPY flaskapp.wsgi /var/www/FlaskApp/
COPY FlaskApp.conf /etc/apache2/sites-available/

RUN mkdir /data && mkdir /data/blast/ && mkdir /data/blast/fungi

RUN apt-get install -y apache2 libapache2-mod-wsgi-py3

RUN a2enmod wsgi

RUN apt-get update -y && apt-get install -y python3-pip

RUN pip3 install virtualenv 

RUN cd /var/www/FlaskApp/FlaskApp && virtualenv venv

RUN #!/bin/bash . venv/bin/activate
   
RUN pip3 install Flask 

RUN pip3 install -U flask-cors 

RUN a2ensite FlaskApp

RUN service apache2 stop && service apache2 restart

