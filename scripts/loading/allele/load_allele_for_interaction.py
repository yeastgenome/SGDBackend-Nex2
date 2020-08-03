import logging
import os
from datetime import datetime
import sys
from src.models import Source, So, Dbentity, Locusdbentity, Referencedbentity, Alleledbentity,\
                       AlleleReference, LocusAllele, LocusalleleReference, AlleleAlias, \
                       AllelealiasReference, AlleleGeninteraction
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']
ALIAS_TYPE = 'Synonym'
SO_TERM = "feature_variant"

def load_data(infile):

    nex_session = get_session()

    log.info(str(datetime.now()))
    log.info("Getting data from database...")
    
    source = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = source.source_id
    # so_to_id =  dict([(x.display_name, x.so_id) for x in nex_session.query(So).all()])
    so = nex_session.query(So).filter_by(term_name=SO_TERM).one_or_none()
    so_id = so.so_id
    
    gene_to_locus_id = dict([(x.systematic_name, x.dbentity_id) for x in nex_session.query(Locusdbentity).all()])

    pmid_to_reference_id = dict([(x.pmid, x.dbentity_id) for x in nex_session.query(Referencedbentity).all()])

    allele_to_id = dict([(x.display_name.upper(), x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='ALLELE').all()])

    # allele_reference_to_id = dict([((x.allele_id, x.reference_id), x.allele_reference_id) for x in nex_session.query(AlleleReference).all()])

    locus_allele_to_id = dict([((x.locus_id, x.allele_id), x.locus_allele_id) for x in nex_session.query(LocusAllele).all()])

    locus_allele_reference_to_id = dict([((x.locus_allele_id, x.reference_id), x.locusallele_reference_id) for x in nex_session.query(LocusalleleReference).all()])

    allele_interaction_to_id = dict([((x.allele_id, x.interaction_id), x.allele_geninteraction_id) for x in nex_session.query(AlleleGeninteraction).all()])

    # allele_alias_to_id = dict([((x.allele_id, x.display_name.upper()), x.allele_alias_id) for x in nex_session.query(AlleleAlias).all()])

    # allele_alias_reference_to_id = dict([((x.allele_alias_id, x.reference_id), x.allelealias_reference_id) for x in nex_session.query(AllelealiasReference).all()])
    
    f = open(infile)
    
    count = 0

    allele_loaded = {}
    locus_allele_loaded = {}
    ref_loaded = {}
    for line in f:
        pieces = line.strip().split("\t")
        reference_id = pmid_to_reference_id.get(int(pieces[5]))
        if reference_id is None:
            log.info("The PMID: " + pieces[5] + " is not in the database")
            continue
        gene = pieces[1]
        [gene1, name1] = pieces[3].split('/')
        [gene2, name2] = pieces[4].split('/')
        
        locus_id = None
        if gene in [gene1, name1]:
            locus_id = gene_to_locus_id.get(name1)
        elif gene in [gene2, name2]:
            locus_id = gene_to_locus_id.get(name2)
        if locus_id is None:
            log.info("The gene: " + gene + " is not in the database")
            continue
        allele_name = pieces[0]
        if allele_name == '':
            log.info("Missing allele name for line: " + line)
            continue

        interaction_id = int(pieces[2]) 
        
        date_created = pieces[7]

        count = count + 1
        
        allele_id = allele_to_id.get(allele_name.upper())
        if allele_id is None:
            allele_id = allele_loaded.get(allele_name)
        if allele_id is None:
            log.info("loading data into dbentity/alleledbentity table...")
            allele_id = insert_alleledbentity(nex_session, allele_name.replace(" ", "_"), allele_name, 
                                              source_id, so_id, date_created)
            allele_loaded[allele_name] = allele_id
            
        locus_allele_id = locus_allele_to_id.get((locus_id, allele_id))
        if locus_allele_id is None:
            locus_allele_id = locus_allele_loaded.get((locus_id, allele_id))
            
        if locus_allele_id is None:
            log.info("loading data into locus_allele table...")
            locus_allele_id = insert_locus_allele(nex_session, locus_id, allele_id, source_id, date_created)
            locus_allele_loaded[(locus_id, allele_id)] = locus_allele_id
            
        if (locus_allele_id, reference_id) not in locus_allele_reference_to_id and (locus_allele_id, reference_id) not in ref_loaded:
            log.info("loading data into locusallele_reference table...")
            insert_locusallele_reference(nex_session, reference_id, locus_allele_id, source_id, date_created)
            ref_loaded[(locus_allele_id, reference_id)] = 1

        if (allele_id, interaction_id) not in allele_interaction_to_id:
            log.info("loading data into allele_geninteraction table...")
            insert_allele_geninteraction(nex_session, allele_id, interaction_id, source_id, date_created)
            
        if count >= 300:
            # nex_session.rollback()  
            nex_session.commit()
            count = 0
                        
    # nex_session.rollback()
    nex_session.commit()
        
    nex_session.close()
    log.info("Done!")
    log.info(str(datetime.now()))

def insert_allele_geninteraction(nex_session, allele_id, interaction_id, source_id, date_created):

    x = AlleleGeninteraction(allele_id = allele_id,
                             interaction_id = interaction_id,
                             source_id = source_id,
                             date_created = date_created,
                             created_by = CREATED_BY)
    nex_session.add(x)
    
def insert_locus_allele(nex_session, locus_id, allele_id, source_id, date_created):

    x = LocusAllele(locus_id = locus_id,
                    allele_id = allele_id,
                    source_id = source_id,
                    date_created = date_created,
                    created_by = CREATED_BY)
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)
    return x.locus_allele_id

def insert_locusallele_reference(nex_session, reference_id, locus_allele_id, source_id, date_created):

    x = LocusalleleReference(reference_id = reference_id,
                             locus_allele_id = locus_allele_id,
                             source_id = source_id,
                             date_created = date_created,
                             created_by = CREATED_BY)
    nex_session.add(x)

def insert_alleledbentity(nex_session, format_name, display_name, source_id, so_id, date_created):
    
    x = Alleledbentity(format_name= format_name,
                       display_name = display_name,
                       source_id = source_id,
                       subclass = 'ALLELE',
                       dbentity_status = 'Active',
                       created_by = CREATED_BY,
                       date_created = date_created,
                       so_id = so_id)
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)
    return x.dbentity_id

if __name__ == "__main__":

    infile = None
    if len(sys.argv) >= 2:
        infile = sys.argv[1]
    else:
        print("Usage:         python scripts/loading/allele/load_allele_for_interaction.py allele_file_name")
        print("Usage example: python scripts/loading/allele/load_allele_for_interaction.py scripts/loading/allele/data/allele_to_interaction_mapping_to_load.txt")
        exit()

    load_data(infile)
