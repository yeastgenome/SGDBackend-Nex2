import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Locusdbentity, LocusUrl
from scripts.loading.database_session import get_session

__author__ = 'sweng66'


def update_data():

    nex_session = get_session()

    locus_id_to_name = dict([(x.dbentity_id, x.systematic_name) for x in nex_session.query(Locusdbentity).all()])

    all = nex_session.query(LocusUrl).filter_by(display_name='Search all NCBI').all()

    i = 0
    j = 0
    for x in all:
        name = locus_id_to_name[x.locus_id]
        url = "https://www.ncbi.nlm.nih.gov/search/all/?term=" + name
        x.obj_url = url
        nex_session.add(x)
        i = i + 1
        if i > 300:
            i = 0
            # nex_session.rollback()
            nex_session.commit()
        j = j + 1
        print (j, i, url)
        
    # nex_session.rollback()
    nex_session.commit() 
    nex_session.close()
    
if __name__ == '__main__':

    update_data()
