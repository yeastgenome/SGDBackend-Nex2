import sys
from src.models import Goslim
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

datafile = "scripts/checking/data/genome_count.txt"

def update_data():

    nex_session = get_session()

    f = open(datafile)
    
    for line in f:
        if line.startswith('#'):
            continue
        pieces = line.split('\t')
        genome_count = int(pieces[3])
        format_name = pieces[4]
        print (format_name, genome_count)
        x = nex_session.query(Goslim).filter_by(format_name=format_name).one_or_none()
        if x is None:
            print (format_name, " is not in the goslim table")
            continue
        x.genome_count = genome_count
        nex_session.add(x)
        
    # nex_session.rollback()
    nex_session.commit()
            
if __name__ == '__main__':

    update_data()
