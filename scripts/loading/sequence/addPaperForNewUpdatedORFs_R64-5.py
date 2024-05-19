import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Locusdbentity, Referencedbentity, Literatureannotation, LocusReferences, \
    Source, Taxonomy
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

TAXON = 'TAX:559292'
datafile = 'scripts/loading/sequence/data/R64-5genomeUpdate050724.tsv'


def add_data():

    nex_session = get_session()

    src = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = src.source_id
    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id

    f = open(datafile)

    pmid_to_reference_id = {}
    for line in f:
        if line.startswith('gene'):
            continue
        pieces = line.strip().split("\t")
        systematic_name = pieces[1].strip()
        note = pieces[4].replace('"', "")
        pmids = pieces[7].split("|")        
        if 'new ORF' in note or "move start" in note.lower():
            locus = nex_session.query(Locusdbentity).filter_by(systematic_name=systematic_name).one_or_none()
            if locus is None:
                print("ORF: " + systematic_name + " is not in the database.")
                continue
            dbentity_id = locus.dbentity_id
            for pmid in pmids:
                reference_id = pmid_to_reference_id.get(pmid)
                if reference_id is None:
                    x = nex_session.query(Referencedbentity).filter_by(pmid=int(pmid)).one_or_none()
                    if x:
                        reference_id = x.dbentity_id
                    else:
                        print("PMID:" + str(pmid) + " is not in the database.")
                        continue
                pmid_to_reference_id[pmid] = reference_id
                insert_into_literatureannotation_table(nex_session, source_id, taxonomy_id, dbentity_id,
                                                       reference_id, systematic_name, pmid)
                if 'new ORF' in note:
                    insert_into_locus_reference_table(nex_session, source_id, dbentity_id, reference_id, "systematic_name")
                    insert_into_locus_reference_table(nex_session, source_id, dbentity_id, reference_id, "qualifier")
                
        
    # nex_session.rollback()
    nex_session.commit()
    

def insert_into_locus_reference_table(nex_session, source_id, dbentity_id, reference_id, reference_class):

    x = LocusReferences(locus_id = dbentity_id,
                        source_id = source_id,
                        reference_id = reference_id,
                        reference_class = reference_class,
                        created_by = 'OTTO')

    nex_session.add(x)

    
def insert_into_literatureannotation_table(nex_session, source_id, taxonomy_id, dbentity_id, reference_id, systematic_name, pmid):
    topic = "Primary Literature"
    x = nex_session.query(Literatureannotation).filter_by(dbentity_id = dbentity_id,
                                                          reference_id = reference_id,
                                                          topic = topic).one_or_none()
    if x:
        print("Literatureannotation: existing entry for ", systematic_name, "PMID:" + pmid)
        return
    x = Literatureannotation(dbentity_id = dbentity_id,
                             source_id = source_id,
                             taxonomy_id = taxonomy_id,
                             reference_id = reference_id,
                             topic = topic,
                             created_by = 'OTTO')
    
    nex_session.add(x)
    

if __name__ == '__main__':

    add_data()
