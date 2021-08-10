import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Locusdbentity, LocusUrl, Source
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

new_features = ['YLR379W-A', 'YMR008C-A', 'YJR107C-A', 'YKL104W-A', 'YGR227C-A', 'YHR052C-B', 'YHR054C-B', 'RE301', 'YELWdelta27', 'YNCP0002W', 'YNCM0001W', 'YNCB0008W', 'YNCH0011W', 'YNCB0014W']

def update_data():

    nex_session = get_session()

    src = nex_session.query(Source).filter_by(display_name = 'NCBI').one_or_none()
    source_id = src.source_id

    for name in new_features:
        locus = nex_session.query(Locusdbentity).filter_by(systematic_name=name).one_or_none()
        if locus is None:
            print ("The ORF: ", name, " is not in the database.")
            continue
        obj_url = "https://www.ncbi.nlm.nih.gov/search/all/?term=" + name
        insert_locus_url(nex_session, obj_url, source_id, locus.dbentity_id)
        
    # nex_session.rollback()
    nex_session.commit()

    nex_session.close()

    
def insert_locus_url(nex_session, obj_url, source_id, locus_id):

    x = LocusUrl(display_name = 'Search all NCBI',
                 obj_url = obj_url,
                 source_id = source_id,
                 locus_id = locus_id,
                 url_type = 'Systematic name',
                 placement = 'LOCUS_LSP_RESOURCES',
                 created_by = 'OTTO')
    nex_session.add(x)
    
if __name__ == '__main__':

    update_data()
