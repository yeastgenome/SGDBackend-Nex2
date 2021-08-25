from sqlalchemy import func, distinct
import os
import sys
from src.models import Go, Goannotation, GoRelation, Goslim
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

CREATED_BY = os.environ['DEFAULT_USER']

def load_data():

    nex_session = get_session()

    goid_to_go_id = dict([(x.goid, x.go_id) for x in nex_session.query(Go).all()])

    complex_terms = go_complex_terms()

    for goid in complex_terms:
        if goid not in goid_to_go_id:
            continue
        go_id = goid_to_go_id[goid]
        all_go_ids = [go_id]
        get_child_ids(nex_session, go_id, all_go_ids)
        genome_count = get_count(nex_session, all_go_ids)
        format_name = 'Macromolecular_complex_terms_' + goid  
        display_name = complex_terms[goid]
        obj_url = '/go/' + goid
        source_id = 834
        slim_name = 'Macromolecular complex terms'
        insert_goslim(nex_session, format_name, display_name, obj_url, go_id,
                      genome_count, slim_name, source_id) 

    # nex_session.rollback()
    nex_session.commit()
        
def insert_goslim(nex_session, format_name, display_name, obj_url, go_id, genome_count, slim_name, source_id):

    print (format_name, display_name, obj_url, go_id, genome_count, slim_name, source_id)
    
    x = Goslim(format_name = format_name,
               display_name = display_name,
               obj_url = obj_url,
               go_id = go_id,
               genome_count = genome_count,
               slim_name = slim_name,
               source_id = source_id,
               created_by = CREATED_BY)
    
    nex_session.add(x)
        
def get_child_ids(nex_session, parent_id, all_go_ids):

    for x in nex_session.query(GoRelation).filter_by(parent_id=parent_id):
        if x.child_id in all_go_ids:
            continue
        all_go_ids.append(x.child_id)
        get_child_ids(nex_session, x.child_id, all_go_ids)

def get_count(nex_session, go_ids):

    annotations = nex_session.query(Goannotation.dbentity_id, func.count(distinct(Goannotation.dbentity_id))).filter(Goannotation.go_id.in_(go_ids)).group_by(Goannotation.dbentity_id).count()

    return annotations    
    
def go_complex_terms():

    return {  'GO:0071010': 'prespliceosome',
              'GO:0000131': 'incipient cellular bud site',
              'GO:0043596': 'nuclear replication fork',
              'GO:0034993': 'meiotic nuclear membrane microtubule tethering complex',
              'GO:0017056': 'structural constituent of nuclear pore',
              'GO:0000940': 'outer kinetochore',
              'GO:0000786': 'nucleosome',
              'GO:1990904': 'ribonucleoprotein complex',
              'GO:0098745': 'Dcp1-Dcp2 complex',
              'GO:0099128': 'mitochondrial iron-sulfur cluster assembly complex',
              'GO:0042564': 'NLS-dependent protein nuclear import complex',
              'GO:0043601': 'nuclear replisome',
              'GO:0106143': 'tRNA (m7G46) methyltransferase complex',
              'GO:0071986': 'Ragulator complex',
              'GO:0030685': 'nucleolar preribosome',
              'GO:0062128': 'MutSgamma complex',
              'GO:0031680': 'G-protein beta/gamma-subunit complex',
              'GO:0000796': 'condensin complex',
              'GO:0110131': 'Aim21-Tda2 complex',
              'GO:0120155': 'MIH complex',
              'GO:1990964': 'actin cytoskeleton-regulatory complex',
              'GO:0034973': 'Sid2-Mob1 complex',
              'GO:1990303': 'UBR1-RAD6 ubiquitin ligase complex',
              'GO:0071162': 'CMG complex',
              'GO:0008275': 'gamma-tubulin small complex',
              'GO:0097361': 'CIA complex',
              'GO:0120171': 'Cdc24p-Far1p-Gbetagamma complex',
              'GO:0062092': 'Yae1-Lto1 complex',
              'GO:0035808': 'meiotic recombination initiation complex',
              'GO:0140224': 'SLAC complex',
              'GO:0101031': 'chaperone complex',
              'GO:0030894': 'replisome' }
    
if __name__ == '__main__':

    load_data()
