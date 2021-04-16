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
        if x.format_name in oldName2newName:
            old_name = x.format_name
            new_name = oldName2newName[old_name]
            x.format_name = new_name
            print (old_name, new_name, x.systematic_name)
            nex_session.add(x)
            insert_locus_alias(nex_session, source_id, x.dbentity_id, old_name)
            
    # nex_session.rollback()
    nex_session.commit()
    nex_session.close()

def insert_locus_alias(nex_session, source_id, locus_id, alias):

    x = LocusAlias(display_name = alias,
                   source_id = source_id,
                   locus_id = locus_id,
                   has_external_id_section = '0',
                   alias_type = 'Uniform',
                   created_by = 'OTTO')

    nex_session.add(x)

if __name__ == '__main__':

    update_data()
