import logging
import os
from datetime import datetime
import sys
from src.models import Source, So, Dbentity, Alleledbentity, So
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

generic_so_term = 'structural_variant'

def load_data(infile):

    nex_session = get_session()

    log.info(str(datetime.now()))
    log.info("Getting data from database...")
    
    so_to_id =  dict([(x.term_name, x.so_id) for x in nex_session.query(So).all()])
    
    allele_to_id = dict([(x.display_name.upper(), x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='ALLELE').all()])
    
    f = open(infile)
    
    count = 0

    allele_id_to_so_id_desc = {}
    allele_id_to_so_id_desc = {}
    for line in f:
        pieces = line.strip().split("\t")
        allele_name = pieces[0]
        allele_id = allele_to_id.get(allele_name.upper())
        if allele_id is None:
            log.info("The allele = " + allele_name + " is not in the database.")
            continue
        so_term = pieces[1]
        so_id = so_to_id.get(so_term)
        if so_id is None:
            log.info("The so term = " + so_term + " is not in the database.")
            continue
        allele_desc = pieces[2]
        allele_id_to_so_id_desc[allele_id] = (so_id, allele_desc)

    ## update allele types here
    so_id = so_to_id.get(generic_so_term)
    
    if so_id is None:
        log.info("The so term: " + generic_so_term + " is not in the database.")
        return

    all = nex_session.query(Alleledbentity).filter_by(so_id=so_id).all()

    count = 0
    for x in all:
        if x.dbentity_id not in allele_id_to_so_id_desc:
            log.info("The allele_id: " + str(x.dbentity_id) + " is not in the mapping file.")
            continue
        (so_id, desc) = allele_id_to_so_id_desc[x.dbentity_id]
        updated = 0
        if x.so_id != so_id:
            x.so_id = so_id
            updated = 1
        if x.description != desc:
            x.description = desc
            updated = 1
        if updated == 1:
            nex_session.add(x)
            count = count + 1
        if count > 300:
            # nex_session.rollback()
            nex_session.commit()
            count = 0

    # nex_session.rollback()
    nex_session.commit()
    
    nex_session.close()
    
    log.info("Done!")
    log.info(str(datetime.now()))

if __name__ == "__main__":
    
    infile = None
    if len(sys.argv) >= 2:
        infile = sys.argv[1]
    else:
        print("Usage:         python scripts/loading/allele/update_allele_type.py allele_to_so_mapping_file_name")
        print("Usage example: python scripts/loading/allele/update_allele_type.py scripts/loading/allele/data/allele_to_so_desc_mapping.txt")
        exit()

    load_data(infile)
