import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Locusdbentity, LocusReferences, Referencedbentity, \
                       Source
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

datafile = 'scripts/loading/sequence/data/newFeatureQualifierDesc.tsv'

def update_data():

    nex_session = get_session()

    src = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = src.source_id
    pmid_to_reference_id = dict([(x.pmid, x.dbentity_id) for x in nex_session.query(Referencedbentity).all()])
    
    f = open(datafile)
    
    for line in f:
        pieces = line.strip().split('\t')
        name = pieces[0].replace('N/A', '').replace('[null]', '')
        qualifier = pieces[1].replace('N/A', '').replace('[null]', '')
        description = pieces[2].strip().replace('N/A', '').replace('[null]', '')
        desc_pmids = pieces[3].replace('N/A', '').replace('[null]', '').split('|')       
        name_description = pieces[4].strip().replace('N/A', '').replace('[null]', '')
        name_desc_pmids = pieces[5].replace('N/A', '').replace('[null]', '').split('|')
        ld = nex_session.query(Locusdbentity).filter_by(systematic_name=name).one_or_none()
        if ld is None:
            print ("The systematic_name", name, " is not in the database.")
            continue
        locus_id = ld.dbentity_id
        if qualifier != '':
            ld.qualifier = qualifier
        if description != '':
            ld.description = description
        if name_description != '':
            ld.name_description = name_description
        nex_session.add(ld)
        for pmid in desc_pmids:
            if pmid == '':
                continue
            reference_id = pmid_to_reference_id.get(int(pmid))
            if reference_id is None:
                print ("The pmid:", pmid, " is not in the database.")
                continue
            insert_locus_reference(nex_session, source_id, 'description',
                                   locus_id, reference_id)

        for pmid in name_desc_pmids:
            if pmid == '':
                continue
            reference_id = pmid_to_reference_id.get(int(pmid))
            if reference_id is None:
                print ("The pmid:", pmid, " is not in the database.")
                continue
            insert_locus_reference(nex_session, source_id,
                                   'name_description',
                                   locus_id, reference_id)
            
    f.close()
    # nex_session.rollback()
    nex_session.commit()

def insert_locus_reference(nex_session, source_id, reference_class, locus_id, reference_id):

    print (reference_class, locus_id, reference_id)
    
    x = LocusReferences(locus_id = locus_id,
                        reference_id = reference_id,
                        reference_class = reference_class,
                        source_id = source_id,
                        created_by = 'OTTO')
    nex_session.add(x)
    
    
if __name__ == '__main__':
    
    update_data()
