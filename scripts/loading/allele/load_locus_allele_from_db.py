import logging
import os
import sys
from src.models import Source, So, Phenotypeannotation, LocusAllele, LocusalleleReference
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

def load_data():

    nex_session = get_session()

    log.info("Getting data from database...")
    
    source = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = source.source_id
    locus_allele_to_id = dict([((x.locus_id, x.allele_id), x.locus_allele_id) for x in nex_session.query(LocusAllele).all()])
    locus_allele_reference_to_id = dict([((x.locus_allele_id, x.reference_id), x.locusallele_reference_id) for x in nex_session.query(LocusalleleReference).all()])
    
    count = 0

    loaded = {}
    ref_loaded = {}
    allPhenos = nex_session.query(Phenotypeannotation).all()
    for x in allPhenos:
        if x.allele_id is None:
            continue
        locus_allele_id = locus_allele_to_id.get((x.dbentity_id, x.allele_id))
        if locus_allele_id is None:
            locus_allele_id = loaded.get((x.dbentity_id, x.allele_id))
        if locus_allele_id is None:
            log.info("adding locus_allele: " + str(x.dbentity_id) + " and " + str(x.allele_id))
            locus_allele_id = insert_locus_allele(nex_session, x.dbentity_id, x.allele_id, source_id,
                                                  x.date_created, x.created_by)
            loaded[(x.dbentity_id, x.allele_id)] = locus_allele_id

        if (locus_allele_id, x.reference_id) not in locus_allele_reference_to_id and (locus_allele_id, x.reference_id) not in ref_loaded:
            log.info("adding locusallele_reference: " + str(locus_allele_id) + " and " + str(x.reference_id))
            insert_locusallele_reference(nex_session, locus_allele_id, x.reference_id, source_id, x.date_created, x.created_by)
            ref_loaded[(locus_allele_id, x.reference_id)] = 1

        count = count + 1

        if count >= 300:
            log.info("commiting data...")
            # nex_session.rollback()
            nex_session.commit()
            count = 0
                        
    # nex_session.rollback()
    nex_session.commit()
        
    nex_session.close()
    log.info("Done!")

def insert_locusallele_reference(nex_session, locus_allele_id, reference_id, source_id, date_created, created_by):

    x = LocusalleleReference(locus_allele_id = locus_allele_id,
                             reference_id = reference_id,
                             source_id = source_id,
                             created_by = created_by,
                             date_created = date_created)
    nex_session.add(x)
    
    
def insert_locus_allele(nex_session, locus_id, allele_id, source_id, date_created, created_by):
    
    x = LocusAllele(locus_id = locus_id,
                    allele_id = allele_id,
                    source_id = source_id,
                    created_by = created_by,
                    date_created = date_created)
        
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)
    return x.locus_allele_id

    
if __name__ == "__main__":

    load_data()
