from sqlalchemy import or_
import logging
import os
from datetime import datetime
import sys
from src.models import Source, So, Dbentity, Locusdbentity, Referencedbentity, Alleledbentity,\
                       AlleleReference, LocusAllele, LocusalleleReference, AlleleAlias, \
                       AllelealiasReference, AlleleGeninteraction, Literatureannotation, \
                       Phenotypeannotation
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
    so = nex_session.query(So).filter_by(term_name=SO_TERM).one_or_none()
    so_id = so.so_id
    
    gene_to_locus_id = dict([(x.systematic_name, x.dbentity_id) for x in nex_session.query(Locusdbentity).all()])

    allele_to_id = dict([(x.display_name.upper(), x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='ALLELE').all()])

    locus_allele_to_id = dict([((x.locus_id, x.allele_id), x.locus_allele_id) for x in nex_session.query(LocusAllele).all()])

    locus_allele_reference_to_id = dict([((x.locus_allele_id, x.reference_id), x.locusallele_reference_id) for x in nex_session.query(LocusalleleReference).all()])

    dbentity_id_to_topic = dict([(x.dbentity_id, x.topic) for x in nex_session.query(Literatureannotation).all()])

    ## 1.  retrieve all allele ids for interactions from database
    ## 2.  retrieve all (allele1_id, allele2_id, interaction_id) from from database
    ## 3.  read all alleles for interactions from the flat file
    ## 4.  read all (allele1_id, allele2_id, interaction_id) from the flat file  
    ## 5.  insert all new alleles that are not in the database into database and all related tables
    ## 6.  if allele is in the db, but the paper is different, update the reference linking table
    ## 7.  if allele is in the db, but the sga/scrore is different, update allele_geninteraction table
    ## 8.  if the allele_ids in #1 are not in allele list from #2, delete these alleles in all related tables 
    ## 9.  if (allele1_id, allele2_id, interaction_id) in #2 are not in list in #4, delete these
    ##     (allele1_id, allele2_id, interaction_id) from database
    
    ## 1.  retrieve all allele ids for interactions from database
    ## 2.  retrieve all (allele1_id, allele2_id, interaction_id) from from database
    
    all_allele_ids_for_interaction_in_db = []
    allele_interaction_to_score = {}
    for x in nex_session.query(AlleleGeninteraction).all():
        if x.allele1_id not in all_allele_ids_for_interaction_in_db:
            all_allele_ids_for_interaction_in_db.append(x.allele1_id)
        allele2_id = None
        if x.allele2_id:
            allele2_id = x.allele2_id
            if allele2_id not in all_allele_ids_for_interaction_in_db:
                all_allele_ids_for_interaction_in_db.append(allele2_id)
        allele_interaction_to_score[(x.allele1_id, allele2_id, x.interaction_id)] = (x.sga_score, x.pvalue)


    ## 3.  read all alleles for interactions from the flat file
    ## 4.  read all (allele1_id, allele2_id, interaction_id) from the flat file 
    ## 5.  insert all new alleles that are not in the database into database and all related tables
    ## 6.  if allele is in the db, but the paper is different, update the reference linking table                                     
    ## 7.  if allele is in the db, but the sga/scrore is different, update allele_geninteraction table
    
    f = open(infile)
    
    count = 0
    
    allele_loaded = {}
    locus_allele_loaded = {}
    ref_loaded = {}
    allele_interaction_loaded = {}
    all_allele_ids_in_flat_file = []
    for line in f:
        pieces = line.strip().split("\t")
        reference_id = int(pieces[5])
        interaction_id = int(pieces[2])
        score = float(pieces[7])
        pvalue = float(pieces[8])
        date_created = pieces[11]
        
        [gene1, name1] = pieces[3].split('/')
        [gene2, name2] = pieces[4].split('/')

        allele1_name = pieces[0].replace("-delta", "-Δ")
        allele2_name = pieces[1].replace("-delta", "-Δ")

        allele1_id = insert_allele_etc(nex_session, allele1_name, gene1, name1, gene2, name2,
                                       reference_id, source_id, so_id, date_created,
                                       allele_loaded, gene_to_locus_id, allele_to_id,
                                       locus_allele_to_id, locus_allele_loaded,
                                       locus_allele_reference_to_id, ref_loaded)
        
        allele2_id = insert_allele_etc(nex_session, allele2_name, gene1, name1, gene2, name2,
                                       reference_id, source_id, so_id, date_created,
                                       allele_loaded, gene_to_locus_id, allele_to_id,
                                       locus_allele_to_id, locus_allele_loaded,
                                       locus_allele_reference_to_id, ref_loaded)
        
        
        # if allele1_id is None and allele2_id is None:
        #    continue        
        if allele1_id is None and allele2_id is not None:
            (allele1_id, allele2_id) = (allele2_id, allele1_id)

            
        ## adding alleles to all_allele_ids_in_flat_file list    
        if allele1_id not in all_allele_ids_in_flat_file:
            all_allele_ids_in_flat_file.append(allele1_id)
        if allele2_id is not None and allele2_id not in all_allele_ids_in_flat_file:
            all_allele_ids_in_flat_file.append(allele2_id)

            
        if (allele1_id, allele2_id, interaction_id) not in allele_interaction_to_score and (allele1_id, allele2_id, interaction_id) not in allele_interaction_loaded:
            log.info("loading data " + str((allele1_id, allele2_id, interaction_id)) + "into allele_geninteraction table...")
            insert_allele_geninteraction(nex_session, allele1_id, allele2_id, interaction_id, score, pvalue, source_id, date_created)
            # allele_interaction_loaded[(allele1_id, allele2_id, interaction_id)] = 1
        count = count + 1

        if (allele1_id, allele2_id, interaction_id) not in allele_interaction_loaded and (allele1_id, allele2_id, interaction_id) in allele_interaction_to_score:
            (sga_score_db, pvalue_db) = allele_interaction_to_score[(allele1_id, allele2_id, interaction_id)]
            if float(sga_score_db) != float(score) or float(pvalue_db) != float(pvalue):
                
                log.info("updating data " + str((allele1_id, allele2_id, interaction_id)) + " in the allele_geninteraction table. sga_score_db="+str(sga_score_db) + ", sga_score="+str(score) + ", pvalue_db="+str(pvalue_db) + ", pvalue="+str(pvalue))
                
                update_allele_geninteraction(nex_session, allele1_id, allele2_id, interaction_id, score, pvalue)
            # allele_interaction_loaded[(allele1_id, allele2_id, interaction_id)] = 1

        allele_interaction_loaded[(allele1_id, allele2_id, interaction_id)] = 1
            
        if count >= 300:
            # nex_session.rollback()
            nex_session.commit()
            count = 0

    # nex_session.rollback()
    nex_session.commit()

    ## 8.  if the allele_ids in #1 are not in allele list from #2, delete these alleles in all related tables 
    for allele_id in all_allele_ids_for_interaction_in_db: 
        if allele_id not in all_allele_ids_in_flat_file:
            log.info("Deleting AlleleGeninteraction rows for allele_id = " + str(allele_id))
            delete_allele_geninteraction(nex_session, allele_id)

    ## 9.  if (allele1_id, allele2_id, interaction_id) in #2 are not in list in #4, delete these
    ##     (allele1_id, allele2_id, interaction_id) from database
    for key in allele_interaction_to_score:
        if key not in allele_interaction_loaded:
            (allele1_id, allele2_id, interaction_id) = key
            log.info("Deleting AlleleGeninteraction row for allele1_id = " + str(allele1_id) + ", allele2_id = " + str(allele2_id))
            delete_allele_geninteraction_by_key(nex_session, allele1_id, allele2_id, interaction_id)
    
    # nex_session.rollback()
    nex_session.commit()
    
    nex_session.close()
    log.info("Done!")
    log.info(str(datetime.now()))

def delete_allele_geninteraction_by_key(nex_session, allele1_id, allele2_id, interaction_id):

    x = nex_session.query(AlleleGeninteraction).filter_by(allele1_id=allele1_id, allele2_id=allele2_id, interaction_id=interaction_id).one_or_none()
    if x is None:
        return
    nex_session.delete(x)
    
def delete_allele_geninteraction(nex_session, allele_id):

    ## delete from allele_geninteraction table
    all_agi = nex_session.query(AlleleGeninteraction).filter(or_(AlleleGeninteraction.allele1_id==allele_id, AlleleGeninteraction.allele2_id==allele_id)).all()
    for x in all_agi:
        log.info("Deleting one of alleleGeninteraction rows for allele_id = " + str(allele_id))
        nex_session.delete(x)
    
def update_allele_geninteraction(nex_session, allele1_id, allele2_id, interaction_id, score, pvalue):

    x = nex_session.query(AlleleGeninteraction).filter_by(allele1_id=allele1_id, allele2_id=allele2_id, interaction_id=interaction_id).one_or_none()
    if x is not None:
        x.sga_score = score
        x.pvalue = pvalue
        nex_session.add(x)

def insert_allele_etc(nex_session, allele_name, gene1, name1, gene2, name2, reference_id, source_id, so_id, date_created, allele_loaded, gene_to_locus_id, allele_to_id, locus_allele_to_id, locus_allele_loaded, locus_allele_reference_to_id, ref_loaded):
        
    if allele_name == 'None' or allele_name is None:
        return None

    gene = None
    if allele_name == 'smt3aiir':
        gene = 'SMT3'
    elif allele_name.startswith('ygr146c-a-'):
        gene = 'YGR146C-A'
    else:
        pieces = allele_name.split('-')    
        if len(pieces) == 1:
            log.info("Warning: bad allele_name: " + allele_name)
            return None
        if allele_name.endswith('-Δ'):
            gene = allele_name.replace('-Δ', '')
        else:
            gene = pieces[0]
        
    locus_id = None
    if gene.upper() == gene1.upper() or gene.upper() == name1.upper():
        locus_id = gene_to_locus_id.get(name1)
    elif gene.upper() == gene2.upper() or gene.upper() == name2.upper():
        locus_id = gene_to_locus_id.get(name2)
    if locus_id is None:
        log.info("Warning: allele_name: " +  allele_name + " doesn't match " + gene1 + ", " + name1 + ", " + gene2 + ", " + name2)
        return None
    
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

    return allele_id

def insert_allele_geninteraction(nex_session, allele1_id, allele2_id, interaction_id, score, pvalue, source_id, date_created):

    x = AlleleGeninteraction(allele1_id = allele1_id,
                             allele2_id = allele2_id,
                             interaction_id = interaction_id,
                             sga_score = score,
                             pvalue = pvalue,
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
        print("Usage example: python scripts/loading/biogrid/load_allele_for_interaction.py scripts/loading/biogrid/data/allele_interaction_score_to_load.txt")
        exit()

    load_data(infile)
