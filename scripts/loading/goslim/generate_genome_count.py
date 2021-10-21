from sqlalchemy import func, distinct, or_
import sys
from src.models import Go, Goannotation, GoRelation, Goslim
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

datafile = "scripts/loading/goslim/data/genome_count.txt"

def generate_genome_count():

    nex_session = get_session()

    fw = open(datafile, 'w')

    go_id_to_dbentity_ids = {}
    for x in nex_session.query(Goannotation).filter(or_(Goannotation.annotation_type == 'manually curated', Goannotation.annotation_type== 'high-throughput')).all():
        dbentity_ids = []
        if x.go_id in go_id_to_dbentity_ids:
            dbentity_ids = go_id_to_dbentity_ids[x.go_id]
        if x.dbentity_id not in dbentity_ids:
            dbentity_ids.append(x.dbentity_id)
        go_id_to_dbentity_ids[x.go_id] = dbentity_ids
    
    all = nex_session.query(Goslim).all()
    slim_go_id_to_count = {}
    for x in all:

        total_count = None
        if x.go_id in slim_go_id_to_count:
            total_count = slim_go_id_to_count[x.go_id]
        else:
            ## get direct and indirect go ids
            all_go_ids = [x.go_id]
            get_child_ids(nex_session, x.go_id, all_go_ids)
            all_dbentity_ids = []
            for go_id in all_go_ids:
                if go_id in go_id_to_dbentity_ids:
                    for dbentity_id in go_id_to_dbentity_ids[go_id]:
                        if dbentity_id not in all_dbentity_ids:
                            all_dbentity_ids.append(dbentity_id)
            total_count = len(all_dbentity_ids)
        fw.write(str(x.go_id) + "\t" + str(x.genome_count) + "\t" + str(total_count) + "\t" + x.format_name + "\t" + x.display_name + "\n")
        
        nex_session.close()

    fw.close()
    
def get_child_ids(nex_session, parent_id, all_go_ids):

    for x in nex_session.query(GoRelation).filter_by(parent_id=parent_id):
        if x.child_id in all_go_ids:
            continue
        all_go_ids.append(x.child_id)
        get_child_ids(nex_session, x.child_id, all_go_ids)

if __name__ == '__main__':

    generate_genome_count()
