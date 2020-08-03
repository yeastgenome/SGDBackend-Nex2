import logging
import os
from datetime import datetime
import sys
from src.models import Allele, Phenotypeannotation
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

def dump_data():

    nex_session = get_session()

    allele_id_to_name = dict([(x.allele_id, x.display_name) for x in nex_session.query(Allele).all()])
    
    allPheno = nex_session.query(Phenotypeannotation).all()
    for x in allPheno:
        if x.allele_id:
            print (str(x.annotation_id) + "\t" + allele_id_to_name[x.allele_id])
        
    nex_session.close()
    
if __name__ == "__main__":

    dump_data()
