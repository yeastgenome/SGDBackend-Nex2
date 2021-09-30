from sqlalchemy import func, distinct
import sys
from src.models import Taxonomy, Source, Goslimannotation, Goslim
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

datafile = "scripts/loading/goslim/data/goslimannotation_data_all_sorted.txt"

TAXID = 'TAX:4932'

def update_data():

    nex_session = get_session()

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid = TAXID).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    src = nex_session.query(Source).filter_by(display_name = 'SGD').one_or_none()
    source_id = src.source_id

    goslim_id_to_name =  dict([(x.goslim_id, x.display_name) for x in nex_session.query(Goslim).all()])
    
    dbentity_id_to_goslim_ids_db = {}
    for x in nex_session.query(Goslimannotation).all():
        goslim_ids = []
        if x.dbentity_id in dbentity_id_to_goslim_ids_db:
            goslim_ids = dbentity_id_to_goslim_ids_db[x.dbentity_id]
        goslim_ids.append(x.goslim_id)
        dbentity_id_to_goslim_ids_db[x.dbentity_id] = goslim_ids
    
    dbentity_id_to_goslim_ids = {}
    f =	open(datafile)
    for line in f:
        pieces = line.split("\t")
        dbentity_id = int(pieces[1])
        goslim_id = int(pieces[2])
        if goslim_id not in goslim_id_to_name:
            continue
        goslim_ids = []
        if dbentity_id in dbentity_id_to_goslim_ids:
            goslim_ids = dbentity_id_to_goslim_ids[dbentity_id]
        goslim_ids.append(goslim_id)
        dbentity_id_to_goslim_ids[dbentity_id] = goslim_ids

    i = 0
    for dbentity_id in dbentity_id_to_goslim_ids:

        goslim_ids_db = []
        if dbentity_id in dbentity_id_to_goslim_ids_db:
            goslim_ids_db = dbentity_id_to_goslim_ids_db[dbentity_id]

        goslim_ids = dbentity_id_to_goslim_ids[dbentity_id]
        for goslim_id in goslim_ids:
            if goslim_id in goslim_ids_db:
                continue
            else:
                insert_row(nex_session, source_id, taxonomy_id, dbentity_id, goslim_id)
                i = i + 1
        for goslim_id in goslim_ids_db:
            if goslim_id not in goslim_ids:
                delete_row(nex_session, dbentity_id, goslim_id) 
                i = i + 1
        if i > 300:
            # nex_session.rollback()
            nex_session.commit()
            i = 0
            
    # nex_session.rollback()
    nex_session.commit()
    
    nex_session.close()

def insert_row(nex_session, source_id, taxonomy_id, dbentity_id, goslim_id):

    print ("Insert: ", source_id, taxonomy_id, dbentity_id, goslim_id)
    
    x = Goslimannotation(source_id = source_id,
                         taxonomy_id = taxonomy_id,
                         dbentity_id = dbentity_id,
                         goslim_id = goslim_id,
                         created_by = 'OTTO')

    nex_session.add(x)
    
def delete_row(nex_session, dbentity_id, goslim_id):

    print ("Delete: ", dbentity_id, goslim_id)
    
    x = nex_session.query(Goslimannotation).filter_by(dbentity_id=dbentity_id, goslim_id=goslim_id).one_or_none()
    if x:
        nex_session.delete(x)

if __name__ == '__main__':

    update_data()
