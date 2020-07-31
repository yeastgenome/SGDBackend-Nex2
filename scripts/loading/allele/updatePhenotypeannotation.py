import logging
import os
from datetime import datetime
import sys
from src.models import Dbentity, Phenotypeannotation
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

mapping_file = "scripts/loading/allele/data/phenotypeannotation_id_to_allele_mapping.txt"

def update_data():

    nex_session = get_session()

    allele_to_id = dict([(x.display_name, x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='ALLELE').all()])

    f = open(mapping_file)
    annotation_id_to_allele = {}
    for line in f:
        pieces = line.strip().split('\t')
        annotation_id_to_allele[int(pieces[0])] = pieces[1]
             
    allPheno = nex_session.query(Phenotypeannotation).all()

    count = 0
    for x in allPheno:
        if x.annotation_id in annotation_id_to_allele:
            allele = annotation_id_to_allele[x.annotation_id]
            allele_id = allele_to_id.get(allele)
            if allele_id is None:
                print ("The allele: " + allele + " is not in the database")
                continue
            if allele_id == x.allele_id:
                continue
            print (count, x.annotation_id, allele_id)
            x.allele_id = allele_id
            nex_session.add(x)
            count = count + 1
            if count > 300:
                # nex_session.rollback()
                nex_session.commit() 
                count = 0
                
    # nex_session.rollback()
    nex_session.commit() 
    nex_session.close()
    
if __name__ == "__main__":

    update_data()
