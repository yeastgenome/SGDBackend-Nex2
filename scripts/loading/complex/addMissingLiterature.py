import os
from datetime import datetime
import sys
from src.models import ComplexReference, Goannotation, Literatureannotation
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

## THIS IS ONE-OFF SCRIPT TO ADD MISSING PAPERS TO LITERATUREANNOTATION TABLE
source_id = 834
taxonomy_id = 274803
topic = 'Primary Literature'
created_by = 'OTTO'

def add_annotations():

    nex_session = get_session()

    key_to_topic = dict([((x.dbentity_id, x.reference_id), x.topic) for x in nex_session.query(Literatureannotation).all()])
    
    added = {}
    for x in nex_session.query(ComplexReference).all():
        if (x.complex_id, x.reference_id) in key_to_topic:
            continue
        insert_literatureannotation(nex_session, x.complex_id, x.reference_id)
        added[(x.complex_id, x.reference_id)] = 1

    for x in nex_session.query(Goannotation).all():
        if x.annotation_type == 'computational':
            continue
        # if x.dbentity.subclass != 'COMPLEX':
        #    continue
        if (x.dbentity_id, x.reference_id) in key_to_topic:
            continue
        if (x.dbentity_id, x.reference_id) in added:
            continue
        if x.reference.sgdid in ['S000246339', 'S000069584']:
            continue
        insert_literatureannotation(nex_session, x.dbentity_id, x.reference_id)
        added[(x.dbentity_id, x.reference_id)] = 1
    # nex_session.rollback()
    nex_session.commit()

def insert_literatureannotation(nex_session, dbentity_id, reference_id):

    print (dbentity_id, reference_id)

    x = Literatureannotation(dbentity_id = dbentity_id,
                             reference_id = reference_id,
                             taxonomy_id = taxonomy_id,
                             topic = topic,
                             source_id = source_id,
                             created_by = created_by)
    nex_session.add(x)
    
if __name__ == '__main__':
    
    add_annotations()
                                                  
