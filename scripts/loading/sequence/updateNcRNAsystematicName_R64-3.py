import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Locusdbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

datafile = 'scripts/loading/sequence/data/ncRNAsNewSystematicNamesRevised031821.tsv'

def update_data():

    nex_session = get_session()
    
    f = open(datafile)

    oldName2newName = {}

    for line in f:
        if line.startswith('Chromosome'):
            continue
        line = line.replace('"', '')
        pieces = line.strip().split("\t")
        old_name = pieces[2]
        new_name = pieces[7]
        oldName2newName[old_name] = new_name

    f.close()
    
    for x in nex_session.query(Locusdbentity).all():
        if x.systematic_name in oldName2newName:
            old_name = x.systematic_name
            new_name = oldName2newName[old_name]
            x.systematic_name = new_name
            print (old_name, new_name, x.systematic_name) 
            nex_session.add(x)
            
    nex_session.rollback()
    # nex_session.commit()
    nex_session.close()
        
if __name__ == '__main__':

    update_data()
