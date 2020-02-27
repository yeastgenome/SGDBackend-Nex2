from datetime import datetime
import sys
import os
from src.models import Dbentity, Pathwaydbentity, PathwayUrl, PathwayAlias, Pathwaysummary,\
                       PathwaysummaryReference, Pathwayannotation, Referencedbentity, \
                       Locusdbentity, LocusAlias, Taxonomy, Source 
from scripts.loading.reference.promote_reference_triage import add_paper
from scripts.loading.database_session import get_session
                             
__author__ = 'sweng66'

log_file = "scripts/loading/pathway/logs/load_pathway.log"
data_file = "scripts/loading/pathway/data/processed_pathways.txt"

summary_type = "Metabolic"

CREATED_BY = os.environ['DEFAULT_USER']
max_to_commit = 25

def load_pathway():

    nex_session = get_session()

    # print (datetime.now(), flush=True)
    print (datetime.now())
    print ("quering data from database...")

    biocyc_id_to_dbentity_id = dict([(x.biocyc_id, x.dbentity_id) for x in nex_session.query(Pathwaydbentity).all()])    

    pathway_name_to_dbentity_id = dict([(x.display_name, x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='PATHWAY').all()])

    pathway_id_to_pathwaysummary = dict([(x.pathway_id, x) for x in nex_session.query(Pathwaysummary).all()])    
    source_to_id = dict([(x.format_name, x.source_id) for x in nex_session.query(Source).all()])
    taxonomy = nex_session.query(Taxonomy).filter_by(taxid='TAX:4932').one_or_none()
    taxonomy_id = taxonomy.taxonomy_id

    # pmid_to_reference_id = dict([(x.pmid, x.dbentity_id) for x in nex_session.query(Referencedbentity).all()])

    print (datetime.now())
    print ("quering Locusdbentity table from database again...")

    gene_to_locus_id = {}
    for x in nex_session.query(Locusdbentity).all():
        gene_to_locus_id[x.systematic_name] = x.dbentity_id
        if x.gene_name:
            gene_to_locus_id[x.gene_name] = x.dbentity_id

    print (datetime.now())
    print ("quering PathwayAlias table from database again...")

    pathway_id_to_alias_list = {}
    for x in nex_session.query(PathwayAlias).all():
        alias_list = []
        if x.pathway_id in pathway_id_to_alias_list:
            alias_list = pathway_id_to_alias_list[x.pathway_id]
        alias_list.append(x.display_name)
        pathway_id_to_alias_list[x.pathway_id] = alias_list
    
    print (datetime.now())
    print ("quering PathwaysummaryReference table from database again...")

    summary_id_to_reference_id_list = {}
    for x in nex_session.query(PathwaysummaryReference).all():
        reference_id_list = []
        if x.summary_id in summary_id_to_reference_id_list:
            reference_id_list = summary_id_to_reference_id_list[x.summary_id]
        reference_id_list.append((x.reference_id, x.reference_order))
        summary_id_to_reference_id_list[x.summary_id] = reference_id_list

    print (datetime.now())
    print ("quering LocusAlias table from database again...")

    biocycID_to_locus_id_list = {}
    for x in nex_session.query(LocusAlias).filter_by(alias_type='Pathway ID').all():
        locus_id_list = []
        if x.display_name in biocycID_to_locus_id_list:
            locus_id_list = biocycID_to_locus_id_list[x.display_name]
        locus_id_list.append(x.locus_id)
        biocycID_to_locus_id_list[x.display_name] = locus_id_list

    print (datetime.now())
    print ("quering Pathwayannotation table from database again...")

    key_to_annotation = {}
    for x in nex_session.query(Pathwayannotation).all():
        key_to_annotation[(x.pathway_id, x.dbentity_id, x.reference_id)] = 1

    f = open(data_file)
    fw = open(log_file, "w")

    biocycIdList = []

    print (datetime.now())
    print ("reading data from datafile...")

    count = 0

    for line in f:
        if line.startswith('pathwayID'):
            continue
        pieces = line.strip().split("\t")
        biocycID = pieces[0]
        biocycIdList.append(biocycID)
        pathway_id = biocyc_id_to_dbentity_id.get(biocycID)
        display_name = pieces[1].replace("<i>", "").replace("</i>", "")
        genes = pieces[2].split('|')
        pmids = pieces[3].split('|')
        summary = pieces[4]
        pmids4summary = pieces[5].split('|')
        synonyms = pieces[6].split('|')
        created_by = pieces[7] 
        if created_by is None:
            created_by = CREATED_BY
        if pathway_id is None:
            pathway_id = pathway_name_to_dbentity_id.get(display_name)
            if pathway_id:
                update_pathwaydbentity(nex_session, fw, pathway_id, biocycID)

        if pathway_id is None:
            
            print (datetime.now())
            print ("adding new pathway: " + biocycID)

            add_pathway(nex_session, fw, taxonomy_id, source_to_id, biocycID, 
                            display_name, genes, pmids, summary, pmids4summary, 
                            synonyms, created_by, gene_to_locus_id)
        else:

            print (datetime.now())
            print ("updating data for pathway: " + biocycID)

            update_pathway(nex_session, fw, taxonomy_id, biocycID, pathway_id, display_name, genes, 
                           pmids, summary, pmids4summary, synonyms, created_by, source_to_id, 
                           pathway_id_to_alias_list, summary_id_to_reference_id_list, 
                           biocycID_to_locus_id_list, gene_to_locus_id, key_to_annotation)
        count = count + 1

        if count == max_to_commit:
            nex_session.commit()
            nex_session.close()
            nex_session = get_session()
            count = 0
            print ("Just committed " + str(max_to_commit) + "rows.")
            
    f.close()
    
    # nex_session.rollback()
    nex_session.commit()

    ## some biocyc_ids have been updated so have to retrieve data from database
    biocyc_id_to_dbentity_id = dict([(x.biocyc_id, x.dbentity_id) for x in nex_session.query(Pathwaydbentity).all()])

    for biocycId in biocyc_id_to_dbentity_id:
        if biocycId not in biocycIdList:
            print (biocycId + " is not in the new pathway file.")
            pathwayId = biocyc_id_to_dbentity_id[biocycId]
            delete_obsolete_biocyc_id(nex_session, fw, biocycId, pathwayId)

    # nex_session.rollback()
    nex_session.commit()

    fw.close()

def delete_obsolete_biocyc_id(nex_session, fw, biocycId, pathwayId):
    
    ## delete from locus_alias 
    nex_session.query(LocusAlias).filter_by(alias_type='Pathway ID', display_name=biocycId).delete()

    ## delete from pathway_alias
    nex_session.query(PathwayAlias).filter_by(pathway_id=pathwayId).delete()

    ## delete from pathway_url                                                                                       
    nex_session.query(PathwayUrl).filter_by(pathway_id=pathwayId).delete()

    ## delete from pathwayannotation
    nex_session.query(Pathwayannotation).filter_by(pathway_id=pathwayId).delete()

    ## delete from pathwaysummary + pathwaysummary_reference
    summary_ids = nex_session.query(Pathwaysummary.summary_id).filter_by(pathway_id=pathwayId).all()
    # nex_session.query(PathwaysummaryReference).filter(PathwaysummaryReference.summary_id.in_(summary_ids)).delete()
    for summary_id in summary_ids:
        nex_session.query(PathwaysummaryReference).filter_by(summary_id=summary_id).delete() 

    nex_session.query(Pathwaysummary).filter_by(pathway_id=pathwayId).delete()

    ## delete from pathwaydbentity
    nex_session.query(Pathwaydbentity).filter_by(dbentity_id=pathwayId).delete()

    ## delete from dbentity
    nex_session.query(Dbentity).filter_by(dbentity_id=pathwayId).delete()

    fw.write("The biocyc_id=" + biocycId + " has been deleted from database.")

def update_pathwaydbentity(nex_session, fw, pathway_id, biocycID):

    nex_session.query(Pathwaydbentity).filter_by(dbentity_id=pathway_id).update({'biocyc_id': biocycID})
    
    fw.write("The biocyc_id has been updated to " + biocycID + " for pathway_id=" + str(pathway_id) + ".") 
    
def update_pathway(nex_session, fw, taxonomy_id, biocycID, pathway_id, display_name, genes, pmids, summary, pmids4summary, synonyms, created_by, source_to_id, pathway_id_to_alias_list, summary_id_to_reference_id_list, biocycID_to_locus_id_list, gene_to_locus_id, key_to_annotationDB):    
    
    ## dbentity 
    x = nex_session.query(Dbentity).filter_by(dbentity_id=pathway_id).one_or_none()
    if display_name != x.display_name:
        x.display_name = display_name
        nex_session.add(x)
        nex_session.flush()
        nex_session.refresh(x)

    ## pathwaydbentity: nothing to update

    ## pathway_alias
    synonymsDB = pathway_id_to_alias_list.get(pathway_id, [])
    for synonym in synonyms:
        if synonym not in synonymsDB:
            insert_pathway_alias(nex_session, fw, pathway_id, synonym, source_to_id['SGD'], 
                                 created_by)
    for synonym in synonymsDB:
        if synonym not in synonyms:
            x = nex_session.query(PathwayAlias).filter_by(pathway_id=pathway_id, display_name=synonym).one_or_none()
            nex_session.delete(x)

    ## pathway_url: nothing to update 

    ## pathwaysummary
    x = nex_session.query(Pathwaysummary).filter_by(pathway_id=pathway_id).one_or_none()
    summary_id = None
    if x is None:
        summary_id = insert_pathwaysummary(nex_session, fw, pathway_id, source_to_id['SGD'], 
                                           summary)
    else:
        summary_id = x.summary_id
        if summary != x.text:
            nex_session.query(Pathwaysummary).filter_by(pathway_id=pathway_id).update({'text': summary, 'html': summary})

    ## pathwaysummary_reference
    reference_id_listDB = summary_id_to_reference_id_list.get(summary_id, [])
    reference_id_to_orderDB = {}
    for (reference_id, order) in reference_id_listDB:
        reference_id_to_orderDB[reference_id] = order
    reference_id_to_order = {}
    order = 0
    found = {}
    for pmid in pmids4summary:

        if pmid in found:
            continue
        found[pmid] = 1

        reference_id = None
        if pmid.isdigit():
            reference_id = get_reference_id_from_db(nex_session, int(pmid))
        else:
            continue
        if reference_id is None:
            (reference_id, sgdid) = add_paper(pmid, created_by)
            if reference_id is None:
                print ("The pmid = " + pmid + " is not in the database and couldn't be added into the database.")
                continue
        order = order + 1
        reference_id_to_order[reference_id] = order
        if reference_id not in reference_id_to_orderDB:
            insert_pathwaysummary_reference(nex_session, fw, summary_id, reference_id, order,
                                            source_to_id['SGD'], created_by)
        elif order != reference_id_to_orderDB[reference_id]:
            nex_session.query(PathwaysummaryReference).filter_by(summary_id=summary_id, reference_id=reference_id).update({'reference_order': order})

    for reference_id in reference_id_to_orderDB:
        if reference_id not in reference_id_to_order:
            nex_session.query(PathwaysummaryReference).filter_by(summary_id=summary_id, reference_id=reference_id).delete()

    ## pathwayannotation & locus_alias
    locus_id_listDB = biocycID_to_locus_id_list.get(biocycID, [])
    locus_id_list = []
    key_to_annotation = {}
    for gene in genes:
        locus_id = gene_to_locus_id.get(gene)
        if locus_id is None:
            print ("The gene name = " + gene + " is not in the database.")
            continue
        locus_id_list.append(locus_id)
        if locus_id not in locus_id_listDB:
            insert_locus_alias(nex_session, fw, source_to_id['MetaCyc'], locus_id, biocycID, created_by)

        has_pmids = 0
        for pmid in pmids:
            reference_id = None
            if pmid.isdigit():
                reference_id = get_reference_id_from_db(nex_session, int(pmid))
            else:
                continue
            if reference_id is None:
                (reference_id, sgdid) = add_paper(pmid, created_by)
                if reference_id is None:
                    print ("The pmid = " + pmid + " is not in the database and couldn't be added into the database.")
                    continue
            has_pmids = 1
            key_to_annotation[(pathway_id, locus_id, reference_id)] = 1
            if (pathway_id, locus_id, reference_id) not in key_to_annotationDB:
                insert_pathwayannotation(nex_session, fw, source_to_id['SGD'], taxonomy_id,
                                         locus_id, reference_id, pathway_id, created_by)
        if has_pmids == 0:
            insert_pathwayannotation(nex_session, fw, source_to_id['SGD'], taxonomy_id,
                                     locus_id, None, pathway_id, created_by)

    for locus_id in locus_id_listDB:
        if locus_id not in locus_id_list:
            nex_session.query(LocusAlias).filter_by(locus_id=locus_id, display_name=biocycID, alias_type='Pathway ID').delete()

    for (pathway_id, locus_id, reference_id) in key_to_annotationDB:
        if (pathway_id, locus_id, reference_id) not in key_to_annotation:
            nex_session.query(Pathwayannotation).filter_by(pathway_id=pathway_id, dbentity_id=locus_id, reference_id=reference_id).delete()

def add_pathway(nex_session, fw, taxonomy_id, source_to_id, biocycID, display_name, genes, pmids, summary,  pmids4summary, synonyms, created_by, gene_to_locus_id):

    ## dbentity & pathwaydbentity 
    pathway_id = insert_pathway_dbentity(nex_session, fw, biocycID, display_name, source_to_id['SGD'], 
                                         created_by)
        
    ## pathway_alias
    for synonym in synonyms:
        insert_pathway_alias(nex_session, fw, pathway_id, synonym, source_to_id['SGD'], created_by)

    ## pathway_url
    insert_pathway_url(nex_session, fw, pathway_id, 'BioCyc', source_to_id['BioCyc'], created_by,
                       'http://www.biocyc.org/YEAST/NEW-IMAGE?type=PATHWAY&object=' + biocycID)
    insert_pathway_url(nex_session, fw, pathway_id, 'YeastPathways', source_to_id['SGD'], created_by,
                       'http://pathway.yeastgenome.org/YEAST/new-image?type=PATHWAY&object=' + biocycID + '&detail-level=2')

    ## pathwaysummary 
    summary_id = insert_pathwaysummary(nex_session, fw, pathway_id, source_to_id['SGD'], summary, created_by)
                                                                                                
    ## pathwaysummary_reference
    order = 0
    found = {}
    for pmid in pmids4summary:
        
        if pmid in found:
            continue
        found[pmid] = 1

        reference_id = None
        if pmid.isdigit():
            reference_id = get_reference_id_from_db(nex_session, int(pmid))
        else:
            continue
        if reference_id is None:
            (reference_id, sgdid) = add_paper(pmid, created_by)
            if reference_id is None:
                print ("The pmid = " + pmid + " is not in the database and couldn't be added into the database.")
                continue

        order = order + 1
        insert_pathwaysummary_reference(nex_session, fw, summary_id, reference_id, order, 
                                        source_to_id['SGD'], created_by) 
        
    ## pathwayannotation & locus_alias
    for gene in genes:    
        locus_id = gene_to_locus_id.get(gene)
        if locus_id is None:
            print ("The gene name = " + gene + " is not in the database.")
            continue

        has_pmids = 0
        for pmid in pmids:
            reference_id = None
            if pmid.isdigit():
                reference_id = get_reference_id_from_db(nex_session, int(pmid))
            else:
                continue
            if reference_id is None:
                (reference_id, sgdid) = add_paper(pmid, created_by)
                if reference_id is None:
                    print ("The pmid = " + pmid + " is not in the database and couldn't be added into the database.")
                    continue

            has_pmids = 1
                
            insert_pathwayannotation(nex_session, fw, source_to_id['SGD'], taxonomy_id, 
                                     locus_id, reference_id, pathway_id, created_by)
        if has_pmids == 0:
            insert_pathwayannotation(nex_session, fw, source_to_id['SGD'], taxonomy_id,
                                     locus_id, None, pathway_id, created_by)

        insert_locus_alias(nex_session, fw, source_to_id['MetaCyc'], locus_id, biocycID, created_by)

def get_reference_id_from_db(nex_session, pmid):

    x = nex_session.query(Referencedbentity).filter_by(pmid=pmid).one_or_none()
    if x is None:
        return None
    else:
        return x.dbentity_id

def insert_locus_alias(nex_session, fw, source_id, locus_id, biocycID, created_by):

    x = nex_session.query(LocusAlias).filter_by(locus_id=locus_id, display_name=biocycID, alias_type='Pathway ID').one_or_none()
    if x is not None:
        return 

    x = LocusAlias(locus_id = locus_id,
                   display_name = biocycID,
                   obj_url = 'http://pathway.yeastgenome.org/YEAST/new-image?type=PATHWAY&object=' + biocycID + '&detail-level=2',
                   source_id = source_id,
                   has_external_id_section = '1',
                   alias_type = 'Pathway ID',
                   created_by = created_by)

    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    fw.write("insert new locus_alias: locus_id=" + str(locus_id) + ", biocyc_id=" + biocycID + "\n")

def insert_pathwayannotation(nex_session, fw, source_id, taxonomy_id, locus_id, reference_id, pathway_id, created_by):

    x = None
    if reference_id is None:
        x = Pathwayannotation(dbentity_id = locus_id,
                              source_id = source_id,
                              taxonomy_id = taxonomy_id,
                              pathway_id = pathway_id,
                              created_by = created_by)
    else:
        x = Pathwayannotation(dbentity_id = locus_id,
                              source_id = source_id,
                              taxonomy_id = taxonomy_id,
                              reference_id = reference_id,
                              pathway_id = pathway_id,
                              created_by = created_by)

    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    fw.write("insert new pathwayannotation: pathway_id=" + str(pathway_id) + ", reference_id=" + str(reference_id) + ", dbentity_id=" + str(locus_id) + "\n")


def insert_pathwaysummary_reference(nex_session, fw, summary_id, reference_id, order, source_id, created_by):
    
    x = PathwaysummaryReference(summary_id = summary_id,
                                reference_id = reference_id,
                                reference_order = order,
                                source_id = source_id,
                                created_by = created_by)
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    fw.write("insert new pathwaysummary_reference: reference_id=" + str(reference_id) + ", summary_id=" + str(summary_id) + "\n")

def insert_pathwaysummary(nex_session, fw, pathway_id, source_id, summary, created_by):

    x = Pathwaysummary(source_id = source_id,
                       pathway_id = pathway_id,
                       summary_type = 'Metabolic',
                       text = summary,
                       html = summary,
                       created_by = created_by)
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    fw.write("insert new pathwaysummary: " + summary + "\n")                   
    
    return x.summary_id

def insert_pathway_url(nex_session, fw, pathway_id, url_type, source_id, created_by, url):

    x = PathwayUrl(display_name = url_type,
                   obj_url = url,
                   source_id = source_id,
                   pathway_id = pathway_id,
                   url_type = url_type,
                   created_by = created_by)

    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    fw.write("insert new pathway_url: " + url + "\n")


def insert_pathway_alias(nex_session, fw, pathway_id, synonym, source_id, created_by):

    if synonym == '':
        return

    x = PathwayAlias(display_name = synonym,
                     source_id = source_id,
                     pathway_id = pathway_id,
                     alias_type = 'Synonym',
                     created_by = created_by)

    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    fw.write("insert new pathway_alias: pathway=" + str(pathway_id) + ", synonym=" + synonym + "\n")


def insert_pathway_dbentity(nex_session, fw, biocycID, display_name, source_id, created_by):

    format_name = display_name.replace(" ", "_")
    x = Pathwaydbentity(format_name = format_name,
                        display_name =display_name,
                        source_id = source_id,
                        subclass = 'PATHWAY',
                        dbentity_status = 'Active',
                        biocyc_id = biocycID,
                        created_by = created_by)

    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    fw.write("insert new dbentity/pathwaydbentity: " + biocycID + "\n")

    return x.dbentity_id


if __name__ == "__main__":
        
    load_pathway()
    
