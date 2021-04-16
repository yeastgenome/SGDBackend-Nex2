import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Locusdbentity, Referencedbentity, Source, Locusnote, LocusnoteReference
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

datafile = 'scripts/loading/sequence/data/locusNotes-Table_1.tsv'

def update_data():

    nex_session = get_session()

    src = nex_session.query(Source).filter_by(display_name = 'SGD').one_or_none()
    source_id = src.source_id
    
    f = open(datafile)

    for line in f:
        if line.startswith('Chromosome'):
            continue
        line = line.replace('"', '')
        pieces = line.strip().split("\t")
        systematic_name = pieces[2].strip()
        locus = nex_session.query(Locusdbentity).filter_by(systematic_name=systematic_name).one_or_none()
        if locus is None:
            print ("The systematic_name ", systematic_name, " is not in the database.")
            continue
        locus_id = locus.dbentity_id
        note = pieces[5]
        note_type = pieces[6]
        note_class = pieces[7]
        note_id = insert_locusnote(nex_session, source_id, locus_id, note,
                                   note_class, note_type)

        pmids = pieces[8].strip().replace(' ', '')
        if note_id and pmids:
            pmid_list = pmids.split('|')
            for pmid in pmid_list:
                ref = nex_session.query(Referencedbentity).filter_by(pmid=int(pmid)).one_or_none()
                if ref is None:
                    print ("The PMID ", pmid, " is not in the database.")
                    continue
                reference_id = ref.dbentity_id
                insert_locusnote_reference(nex_session, source_id, note_id, reference_id)
                
    f.close()
            
    # nex_session.rollback()
    nex_session.commit()
    nex_session.close()

def insert_locusnote(nex_session, source_id, locus_id, note, note_class, note_type):

    x = Locusnote(source_id = source_id,
                  locus_id = locus_id,
                  note = note,
                  note_class = note_class,
                  note_type = note_type,
                  created_by = 'OTTO')
    
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    return x.note_id


def insert_locusnote_reference(nex_session, source_id, note_id, reference_id):

    x = LocusnoteReference(source_id = source_id,
                           note_id = note_id,
                           reference_id = reference_id,
                           created_by = 'OTTO')
    nex_session.add(x)
    
    
if __name__ == '__main__':

    update_data()
