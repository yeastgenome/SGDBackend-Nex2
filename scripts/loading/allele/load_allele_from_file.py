import logging
import os
from datetime import datetime
import sys
from src.models import Source, So, Dbentity, Locusdbentity, Referencedbentity, Alleledbentity,\
                       AlleleReference, LocusAllele, LocusalleleReference, AlleleAlias, \
                       AllelealiasReference
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']
ALIAS_TYPE = 'Synonym'

def load_data(infile):

    nex_session = get_session()

    log.info(str(datetime.now()))
    log.info("Getting data from database...")
    
    source = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = source.source_id
    so_to_id =  dict([(x.display_name, x.so_id) for x in nex_session.query(So).all()])

    gene_to_locus_id = dict([(x.gene_name, x.dbentity_id) for x in nex_session.query(Locusdbentity).all()])
    name_to_locus_id = dict([(x.systematic_name, x.dbentity_id) for x in nex_session.query(Locusdbentity).all()])
    
    pmid_to_reference_id = dict([(x.pmid, x.dbentity_id) for x in nex_session.query(Referencedbentity).all()])

    allele_to_id = dict([(x.display_name.upper(), x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='ALLELE').all()])

    allele_reference_to_id = dict([((x.allele_id, x.reference_id), x.allele_reference_id) for x in nex_session.query(AlleleReference).all()])

    locus_allele_to_id = dict([((x.locus_id, x.allele_id), x.locus_allele_id) for x in nex_session.query(LocusAllele).all()])

    locus_allele_reference_to_id = dict([((x.locus_allele_id, x.reference_id), x.locusallele_reference_id) for x in nex_session.query(LocusalleleReference).all()])

    allele_alias_to_id = dict([((x.allele_id, x.display_name.upper()), x.allele_alias_id) for x in nex_session.query(AlleleAlias).all()])

    allele_alias_reference_to_id = dict([((x.allele_alias_id, x.reference_id), x.allelealias_reference_id) for x in nex_session.query(AllelealiasReference).all()])
    
    f = open(infile)
    
    count = 0
    
    for line in f:
        pieces = line.strip().split("\t")
        if pieces[0] in ['PMID', 'pmid']:
            continue
        if pieces[0] == '':
            log.info("Missing PMID for line: " + line)
            continue
        reference_id = pmid_to_reference_id.get(int(pieces[0]))
        if reference_id is None:
            log.info("The PMID: " + pieces[0] + " is not in the database")
            continue
        locus_id = gene_to_locus_id.get(pieces[1])
        if locus_id is None:
            locus_id = name_to_locus_id.get(pieces[1])
            if locus_id is None:
                log.info("The gene: " + pieces[1] + " is not in the database")
                continue
        allele_name = pieces[2].replace('"', '')
        if allele_name == '':
            log.info("Missing allele name for line: " + line)
            continue
        allele_desc = pieces[3].replace('"', '')
        so_id = so_to_id.get(pieces[4].replace("_", " "))
        if so_id is None:
            log.info("The so term: " + pieces[4].replace("_", " ") + " is not in the database")
            continue
        alias = pieces[5]
        created_by = pieces[6]
        if created_by == '':
            log.info("Missing created_by for line: " + line)
            continue

        count = count + 1
        
        allele_id = allele_to_id.get(allele_name.upper())

        if allele_id is None:
            log.info("loading data into dbentity/alleledbentity table...")
            allele_id = insert_alleledbentity(nex_session, allele_name.replace(" ", "_"), allele_name, allele_desc,
                                              source_id, so_id, created_by)

        if (allele_id, reference_id) not in allele_reference_to_id:
            log.info("loading data into allele_reference table...")
            insert_allele_reference(nex_session, allele_id, reference_id, source_id, created_by)
            
        locus_allele_id = locus_allele_to_id.get((locus_id, allele_id))
        
        if locus_allele_id is None:
            log.info("loading data into locus_allele table...")
            locus_allele_id = insert_locus_allele(nex_session, locus_id, allele_id, source_id, created_by)

        if (locus_allele_id, reference_id) not in locus_allele_reference_to_id:
            log.info("loading data into locusallele_reference table...")
            insert_locusallele_reference(nex_session, reference_id, locus_allele_id, source_id, created_by)

        if alias:
            allele_alias_id = allele_alias_to_id.get((allele_id, alias.upper()))
            if allele_alias_id is None:
                log.info("loading data into allele_alias table...")
                allele_alias_id = insert_allele_alias(nex_session, allele_id, alias, source_id, created_by)

            if (allele_alias_id, reference_id) not in allele_alias_reference_to_id:
                log.info("loading data into allelealias_reference table...")
                insert_allelealias_reference(nex_session, reference_id, allele_alias_id, source_id, created_by)
            
        if count >= 300:
            # nex_session.rollback()  
            nex_session.commit()
            count = 0
                        
    # nex_session.rollback()
    nex_session.commit()
        
    nex_session.close()
    log.info("Done!")
    log.info(str(datetime.now()))


def insert_allele_reference(nex_session, allele_id, reference_id, source_id, created_by):

    x = AlleleReference(allele_id = allele_id,
                        reference_id = reference_id,
                        source_id = source_id,
                        created_by = created_by)
    nex_session.add(x)

def insert_locus_allele(nex_session, locus_id, allele_id, source_id, created_by):

    x = LocusAllele(locus_id = locus_id,
                    allele_id = allele_id,
                    source_id = source_id,
                    created_by = created_by)
    
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)
    return x.locus_allele_id

def insert_locusallele_reference(nex_session, reference_id, locus_allele_id, source_id, created_by):

    x = LocusalleleReference(reference_id = reference_id,
                             locus_allele_id = locus_allele_id,
                             source_id = source_id,
                             created_by = created_by)
    nex_session.add(x)

def insert_allele_alias(nex_session, allele_id, alias, source_id, created_by):

    x = AlleleAlias(allele_id = allele_id,
                    display_name = alias,
                    alias_type = ALIAS_TYPE,
                    source_id = source_id,
                    created_by = created_by)

    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)
    return x.allele_alias_id

def insert_allelealias_reference(nex_session, reference_id, allele_alias_id, source_id, created_by):

    x = AllelealiasReference(reference_id = reference_id,
                             allele_alias_id = allele_alias_id,
                             source_id = source_id,
                             created_by = created_by)
    nex_session.add(x)

def insert_alleledbentity(nex_session, format_name, display_name, desc, source_id, so_id, created_by):
    
    x = Alleledbentity(format_name= format_name,
                       display_name = display_name,
                       source_id = source_id,
                       subclass = 'ALLELE',
                       dbentity_status = 'Active',
                       created_by = created_by,
                       description = desc,
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
        print("Usage:         python scripts/loading/allele/load_allele_from_file.py allele_file_name")
        print("Usage example: python scripts/loading/allele/load_allele_from_file.py scripts/loading/allele/data/alleles4Shuai2load062920.tsv")
        exit()

    load_data(infile)
