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

PMID = 25721128

def update_data():

    nex_session = get_session()

    log.info(str(datetime.now()))
    log.info("Getting data from database...")

    ref = nex_session.query(Referencedbentity).filter_by(pmid=PMID).one_or_none()
    reference_id = ref.dbentity_id

    locus_allele_ids = nex_session.query(LocusalleleReference.locus_allele_id).filter_by(reference_id=reference_id).all()

    allele_ids = nex_session.query(LocusAllele.allele_id).filter(LocusAllele.locus_allele_id.in_(locus_allele_ids)).all()

    all = nex_session.query(Dbentity).filter(Dbentity.dbentity_id.in_(allele_ids)).filter(Dbentity.display_name.like('%-delta%')).all()

    for x in all:
        print (x.display_name)
        allele_name = x.display_name.replace("-delta", "-Δ")
        x.display_name = allele_name
        nex_session.add(x)
        
    # nex_session.rollback()
    nex_session.commit()
    nex_session.close()

    
if __name__ == "__main__":
    
    update_data()
