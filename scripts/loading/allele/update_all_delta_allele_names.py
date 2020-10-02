import logging
import os
from datetime import datetime
import sys
from src.models import Dbentity, Referencedbentity, LocusAllele, LocusalleleReference
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

def update_data():

    nex_session = get_session()

    log.info(str(datetime.now()))
    log.info("Getting data from database...")

    all = nex_session.query(Dbentity).filter_by(subclass='ALLELE').filter(Dbentity.display_name.like('%delta%')).all()

    for x in all:
        allele_name = x.display_name.replace("delta", "Δ")
        print (x.display_name, allele_name)
        x.display_name = allele_name
        nex_session.add(x)
        
    # nex_session.rollback()
    nex_session.commit()
    nex_session.close()

    
if __name__ == "__main__":
    
    update_data()
