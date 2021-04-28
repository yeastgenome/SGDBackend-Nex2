import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Locusdbentity, Source, LocusAlias
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

datafile = 'scripts/loading/sequence/data/ncRNAsNewSystematicNamesRevised031821.tsv'

def update_data():

    nex_session = get_session()

    src = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = src.source_id
    
    f = open(datafile)

    isNewName = []

    for line in f:
        if line.startswith('Chromosome'):
            continue
        line = line.replace('"', '')
        pieces = line.strip().split("\t")
        isNewName.append(pieces[7])

    f.close()
    
    for x in nex_session.query(Locusdbentity).all():
        if x.systematic_name in isNewName:
            display_name = x.systematic_name
            if x.gene_name:
                display_name = x.gene_name
            x.display_name = display_name
            print (x.systematic_name, x.gene_name, display_name)
            nex_session.add(x)
            
    # nex_session.rollback()
    nex_session.commit()
    nex_session.close()

if __name__ == '__main__':

    update_data()
