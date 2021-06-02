FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt update && apt-get --yes install wget

RUN mkdir /var/www && mkdir /var/www/bin && mkdir /var/www/conf

COPY scan_for_matches /var/www/bin
COPY nrgrep_coords /var/www/bin
COPY generate_sequence_index.pl /var/www/bin
COPY patmatch_to_nrgrep.pl /var/www/bin

COPY patmatch.json var/www/conf

RUN mkdir /data && mkdir /data/patmatch && mkdir /data/restriction_mapper

RUN cd /var/www && mkdir logs FlaskApp && cd FlaskApp && \
    mkdir FlaskApp && cd FlaskApp && \
    mkdir venv static templates

RUN apt-get install -y apache2 libapache2-mod-wsgi-py3

RUN a2enmod wsgi

RUN apt-get update -y && apt-get install -y python3-pip

RUN pip3 install virtualenv 

RUN cd /var/www/FlaskApp/FlaskApp && virtualenv venv

RUN #!/bin/bash . venv/bin/activate
   
RUN pip3 install Flask 

RUN pip3 install -U flask-cors 

COPY __init__.py /var/www/FlaskApp/FlaskApp/
COPY patmatch.py /var/www/FlaskApp/FlaskApp/
COPY restrictionmapper.py /var/www/FlaskApp/FlaskApp/
COPY flaskapp.wsgi /var/www/FlaskApp/
COPY FlaskApp.conf /etc/apache2/sites-available/

RUN a2ensite FlaskApp

RUN service apache2 stop && service apache2 restart

