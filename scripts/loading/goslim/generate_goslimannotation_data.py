from sqlalchemy import func, distinct, or_
import sys
from src.models import Go, Goannotation, GoRelation, Goslim, Complexdbentity, Locusdbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

defaultGoSlim = 'yeast'
# defaultGoSlim = 'generic'
# defaultGoSlim = 'complex'

goSlimDir = 'scripts/loading/goslim/data/'

def generate_data(goSlim):

    goSlimFile = goSlimDir + goSlim + 'GoSlimAnnot.txt'
    
    nex_session = get_session()

    dbentity_id_to_name =  dict([(x.dbentity_id, x.systematic_name) for x in nex_session.query(Locusdbentity).all()])
    dbentity_id_to_complexAcc = dict([(x.dbentity_id, x.complex_accession) for x in nex_session.query(Complexdbentity).all()])
    
    go_id_to_go = dict([(x.go_id, (x.goid, x.display_name)) for x in nex_session.query(Go).all()])
    
    go_id_to_dbentity_ids = {}
    for x in nex_session.query(Goannotation).filter(or_(Goannotation.annotation_type == 'manually curated', Goannotation.annotation_type== 'high-throughput')).all():
        dbentity_ids = []
        if x.go_id in go_id_to_dbentity_ids:
            dbentity_ids = go_id_to_dbentity_ids[x.go_id]
        if x.dbentity_id not in dbentity_ids:
            dbentity_ids.append(x.dbentity_id)
        go_id_to_dbentity_ids[x.go_id] = dbentity_ids
    
    all = nex_session.query(Goslim).all()

    nex_session.close()

    fw= open(goSlimFile, 'w')

    nex_session = get_session()

    foundGoid = {}
    foundSlimGoidGenePair = {}
    
    for x in all:

        if goSlim not in x.slim_name.lower():
            continue
        
        if x.go_id in foundGoid:
            continue
        foundGoid[x.go_id] = 1
        
        ## get direct and indirect 
        all_go_ids = [x.go_id]
        get_child_ids(nex_session, x.go_id, all_go_ids)

        for go_id in all_go_ids:
            if go_id not in go_id_to_dbentity_ids:
                continue
            dbentity_ids = go_id_to_dbentity_ids[go_id]
            for dbentity_id in dbentity_ids:
                key = (x.go_id, dbentity_id)
                if key in foundSlimGoidGenePair:
                    continue
                foundSlimGoidGenePair[key] = 1
                name = None
                if dbentity_id in dbentity_id_to_name:
                    name = dbentity_id_to_name[dbentity_id]
                elif dbentity_id in dbentity_id_to_complexAcc:
                    name = dbentity_id_to_complexAcc[dbentity_id]
                if name:
                    fw.write(name + "\t" + str(dbentity_id) + "\t" + str(x.goslim_id) + "\t" + x.format_name + "\t" + x.display_name + "\n")
                
    fw.close()
    nex_session.close()

def get_child_ids(nex_session, parent_id, all_go_ids):

    for x in nex_session.query(GoRelation).filter_by(parent_id=parent_id):
        if x.child_id in all_go_ids:
            continue
        all_go_ids.append(x.child_id)
        get_child_ids(nex_session, x.child_id, all_go_ids)

if __name__ == '__main__':

    goSlim = defaultGoSlim
    if len(sys.argv) >= 2:
        goSlim = sys.argv[1]
        
    generate_data(goSlim)
