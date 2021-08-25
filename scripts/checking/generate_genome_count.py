from sqlalchemy import func, distinct
import sys
from src.models import Go, Goannotation, GoRelation, Goslim
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

def generate_genome_count():

    nex_session = get_session()

    all = nex_session.query(Goslim).all()
    for x in all:
        
        direct_count = get_count(nex_session, [x.go_id])

        ## get direct and indirect 
        all_go_ids = [x.go_id]
        get_child_ids(nex_session, x.go_id, all_go_ids)
        total_count = get_count(nex_session, all_go_ids)
        
        print (str(x.go_id) + "\t" + str(x.genome_count) + "\t" + str(direct_count) + "\t" + str(total_count) + "\t" + x.format_name + "\t" + x.display_name )
        
        nex_session.close()

def get_child_ids(nex_session, parent_id, all_go_ids):

    for x in nex_session.query(GoRelation).filter_by(parent_id=parent_id):
        if x.child_id in all_go_ids:
            continue
        all_go_ids.append(x.child_id)
        get_child_ids(nex_session, x.child_id, all_go_ids)

def get_count(nex_session, go_ids):
    
    annotations = nex_session.query(Goannotation.dbentity_id, func.count(distinct(Goannotation.dbentity_id))).filter(Goannotation.go_id.in_(go_ids)).group_by(Goannotation.dbentity_id).count()
    
    return annotations

if __name__ == '__main__':

    generate_genome_count()
