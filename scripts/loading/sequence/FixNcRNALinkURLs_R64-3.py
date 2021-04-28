import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Locusdbentity, LocusUrl
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

datafile = 'scripts/loading/sequence/data/ncRNAsNewSystematicNamesRevised031821.tsv'

def update_data():

    nex_session = get_session()
    
    f = open(datafile)
    
    for line in f:
        if line.startswith('Chromosome'):
            continue
        line = line.replace('"', '')
        pieces = line.strip().split("\t")
        old_name = pieces[2]
        new_name = pieces[7]
        locus = nex_session.query(Locusdbentity).filter_by(systematic_name = new_name).one_or_none()
        if locus is None:
            print (new_name, " is not in DB.")
            continue
        all_urls = nex_session.query(LocusUrl).filter_by(locus_id = locus.dbentity_id, url_type='Systematic name').all()
        for u in all_urls:
            if old_name in u.obj_url:
                url = u.obj_url.replace(old_name, new_name)
                u.obj_url = url
                print (url)
                nex_session.add(u)
                
    f.close()
                
    # nex_session.rollback()
    nex_session.commit()
    nex_session.close()

if __name__ == '__main__':

    update_data()
