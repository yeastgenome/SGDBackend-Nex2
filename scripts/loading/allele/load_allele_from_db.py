import logging
import os
from datetime import datetime
import sys
from src.models import Source, So, Allele, Dbentity, Alleledbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

def load_data():

    nex_session = get_session()

    log.info(str(datetime.now()))
    log.info("Getting data from database...")

    allele_to_dbentity_id = dict([(x.display_name.upper(), x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='ALLELE').all()])

    source = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = source.source_id
    so = nex_session.query(So).filter_by(display_name='structural variant').one_or_none()
    so_id = so.so_id
    
    count = 0

    allAllele = nex_session.query(Allele).all()
    for x in allAllele:
        if x.display_name.upper() in allele_to_dbentity_id:
            continue
        log.info("adding alleledbentiy: " + x.display_name + "...")
        insert_alleledbentity(nex_session, x.format_name, x.display_name, x.description,
                              source_id, so_id, x.date_created, x.created_by)
        count = count + 1
        if count >= 300:
            # nex_session.rollback()  
            nex_session.commit()
            count = 0
                        
    # nex_session.rollback()
    nex_session.commit()
        
    nex_session.close()
    log.info("Done!")
    log.info(str(datetime.now()))

def insert_alleledbentity(nex_session, format_name, display_name, desc, source_id, so_id, date_created, created_by):
    
    x = Alleledbentity(format_name= format_name,
                       display_name = display_name,
                       source_id = source_id,
                       subclass = 'ALLELE',
                       dbentity_status = 'Active',
                       created_by = created_by,
                       date_created = date_created,
                       description = desc,
                       so_id = so_id)
    
    nex_session.add(x)
    # nex_session.flush()
    # nex_session.refresh(x)
    # return x.dbentity_id

if __name__ == "__main__":

    load_data()
