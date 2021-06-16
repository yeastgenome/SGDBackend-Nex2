FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y \
    apache2 \
    libapache2-mod-wsgi-py3 \
    net-tools \
    python3-pip \
    wget \
    gcc \
    make \
    build-essential \
    graphviz \
    libgd-perl 
   
RUN pip3 install Flask && pip3 install -U flask-cors 

RUN wget https://cpan.metacpan.org/authors/id/T/TO/TODDR/IPC-Run-20200505.0.tar.gz && \
    tar xvfz IPC-Run-20200505.0.tar.gz && \
    cd IPC-Run-20200505.0 && \
    perl Makefile.PL && \
    make && \
    make install

RUN wget https://cpan.metacpan.org/authors/id/P/PL/PLICEASE/File-Which-1.24.tar.gz && \
    tar xvfz File-Which-1.24.tar.gz && \
    cd File-Which-1.24 && \
    perl Makefile.PL && \
    make && \
    make install

RUN wget https://cpan.metacpan.org/authors/id/C/CM/CMUNGALL/go-perl-0.15.tar.gz && \
    tar xvfz go-perl-0.15.tar.gz && \
    cd go-perl-0.15 && \
    perl Makefile.PL && \
    make && \
    make install

RUN wget https://cpan.metacpan.org/authors/id/G/GA/GAAS/IO-String-1.08.tar.gz && \
    tar xvfz IO-String-1.08.tar.gz && \
    cd IO-String-1.08 && \
    perl Makefile.PL && \
    make && \
    make install

RUN wget https://cpan.metacpan.org/authors/id/C/CM/CMUNGALL/Data-Stag-0.14.tar.gz && \
    tar xvfz Data-Stag-0.14.tar.gz && \
    cd Data-Stag-0.14 && \
    perl Makefile.PL && \
    make && \
    make install

RUN wget https://cpan.metacpan.org/authors/id/R/RS/RSAVAGE/GraphViz-2.24.tgz && \
    tar xvfz GraphViz-2.24.tgz && \
    cd GraphViz-2.24 && \
    perl Makefile.PL && \
    make && \
    make install

RUN wget https://cpan.metacpan.org/authors/id/S/SH/SHERLOCK/GO-TermFinder-0.86.tar.gz && \
    tar xvfz GO-TermFinder-0.86.tar.gz && \
    cd GO-TermFinder-0.86 && \
    perl Makefile.PL && \
    make && \
    make install

RUN cd /var/www && mkdir bin data lib logs tmp FlaskApp && cd FlaskApp && \
    mkdir FlaskApp && cd FlaskApp && mkdir venv static templates && \
    cd /var/www/data && mkdir new

COPY www /var/www/
COPY FlaskApp.conf /etc/apache2/sites-available/

RUN a2enmod wsgi && a2ensite FlaskApp && a2dissite 000-default

RUN pip3 install virtualenv 

RUN cd /var/www/FlaskApp/FlaskApp && virtualenv venv

RUN #!/bin/bash . venv/bin/activate

CMD ["apachectl", "-D", "FOREGROUND"]
