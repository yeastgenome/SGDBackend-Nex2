FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y apache2 libapache2-mod-wsgi-py3 python3-pip 
    
RUN cd /var/www && mkdir bin conf logs FlaskApp && cd FlaskApp && \
    mkdir FlaskApp && cd FlaskApp && mkdir venv static templates

RUN pip3 install virtualenv
RUN cd /var/www/FlaskApp/FlaskApp && virtualenv venv
RUN #!/bin/bash . venv/bin/activate

RUN pip3 install Flask && pip3 install -U flask-cors

COPY www /var/www
COPY FlaskApp.conf /etc/apache2/sites-available/

RUN mkdir /data && cd /data && mkdir patmatch restriction_mapper

RUN a2enmod wsgi && a2ensite FlaskApp && a2dissite 000-default

CMD ["apachectl", "-D", "FOREGROUND"]


