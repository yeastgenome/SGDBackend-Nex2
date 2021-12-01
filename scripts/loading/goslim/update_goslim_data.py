import sys
from src.models import Goslim, Go
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

datafile = "scripts/loading/goslim/data/genome_count.txt"

def update_data():

    nex_session = get_session()

    go_id_to_term =  dict([(x.go_id, x.display_name) for x in nex_session.query(Go).all()])
    
    f = open(datafile)
    
    for line in f:
        if line.startswith('#'):
            continue
        pieces = line.split('\t')
        genome_count = int(pieces[2])
        format_name = pieces[3]
        print (format_name, genome_count)
        x = nex_session.query(Goslim).filter_by(format_name=format_name).one_or_none()
        if x is None:
            print (format_name, " is not in the goslim table")
            continue
        x.genome_count = genome_count
        display_name = go_id_to_term.get(x.go_id)
        if display_name != x.display_name and x.display_name not in ['biological_process', 'molecular_function', 'cellular_component']:
            x.display_name = display_name
        nex_session.add(x)
        
    # nex_session.rollback()
    nex_session.commit()
            
if __name__ == '__main__':

    update_data()
