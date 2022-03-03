import os
import logging
from datetime import datetime
from scripts.loading.database_session import get_session
from src.models import Locusdbentity, LocusAlias, Source

pantherGeneFile = 'scripts/loading/dbxref/data/pantherGeneList.txt'

__author__ = 'sagarjha'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)
log_file = "scripts/loading/dbxref/logs/update_pantherids.log"

ALIAS_TYPE = 'PANTHER ID'
SRC = "PANTHER"
OBJ_URL = 'http://www.pantherdb.org/panther/family.do?clsAccession='
CREATED_BY = os.environ['DEFAULT_USER']
alias_type_src_list = [(ALIAS_TYPE, SRC)]

ADDED = 0
DELETED = 0
UPDATED = 0


def update_data():
    nex_session = get_session()
    fw = open(log_file,"w")

    id_to_source = {}
    source_to_id = {}

    log.info(str(datetime.now()))
    log.info("Getting data from the database...")

    for x in nex_session.query(Source).all():
        id_to_source[x.source_id] = x.display_name
        source_to_id[x.display_name] = x.source_id
    
    locus_id_to_ORF = {}
    ORF_to_locus_id = {}

    for x in nex_session.query(Locusdbentity).all():
        locus_id_to_ORF[x.dbentity_id] = x.systematic_name
        ORF_to_locus_id[x.systematic_name] = x.dbentity_id
    
    log.info("Reading data from panther gene list file...")

    # [ORF_to_panther_id,panther_id_to_ORF,key_to_ids] = read_panther_gene_list_file(source_to_id)
    [ORF_to_panther_id,key_to_ids] = read_panther_gene_list_file(source_to_id)

    all_aliases = nex_session.query(LocusAlias).filter_by(alias_type = ALIAS_TYPE)
    
    nex_session.close()
    nex_session = get_session()

    key_to_ids_DB = {}
    
    log.info("Updating the data in the database...")

    for x in all_aliases:
        this_key = (x.alias_type, id_to_source[x.source_id])
        if this_key not in alias_type_src_list:
            continue
        
        ORF = locus_id_to_ORF[x.locus_id]
        panther_id = ORF_to_panther_id.get(ORF)
        if panther_id is None:
            continue
        
        # if x.alias_type == ALIAS_TYPE:
        #     if x.display_name != panther_id:
        #         #change in panther id for the ORF
        #         update_panther_id(nex_session,fw,x.locus_id,panther_id)
        #     continue
            

        key = (ORF,x.alias_type,x.source_id)
        
        panther_id_list_DB = []
        if key in key_to_ids_DB:
            panther_id_list_DB = key_to_ids_DB[key]
        panther_id_list_DB.append(x.display_name)       
        key_to_ids_DB[key] = panther_id_list_DB
    
    for key in key_to_ids:
        if key in key_to_ids_DB:
            update_aliases(nex_session,fw,key,key_to_ids[key],key_to_ids_DB[key],ORF_to_locus_id,id_to_source)
            del key_to_ids_DB[key]
        else:
            insert_aliases(nex_session,fw,key,key_to_ids[key],ORF_to_locus_id)
    
    for key in key_to_ids_DB:
        delete_aliases(nex_session,fw,key,ORF_to_locus_id)

    # nex_session.rollback()
    nex_session.commit()

    # ## Upload file to s3 ??

    log.info("Loading summary:")
    log.info("\tAdded: " + str(ADDED))
    log.info("\tUpdated: " + str(UPDATED))
    log.info("\tDeleted: " + str(DELETED))
    log.info(str(datetime.now()))
    log.info("Done!")

def read_panther_gene_list_file(source_to_id):
    ORF_to_panther_id = {}
    # panther_id_to_ORF = {}
    key_to_ids = {}
    with open(pantherGeneFile,'r') as file:
        lines = file.readlines()
        for line in lines:
            
            pieces = line.split("\t")

            ORF_list = pieces[1].split(",")

            # print ("orf=", ORF_list)
            
            words = pieces[3].split(' ')
            
            pantherid = words[-1]
            if(pantherid.startswith('(PTHR')):
                pantherid = pantherid[1:-1]

                # print ("pantherid=", pantherid)
                
                for ORF in ORF_list:
                    ORF_to_panther_id[ORF] = pantherid
                    # panther_id_to_ORF[pantherid]= ORF
                    key = (ORF,ALIAS_TYPE,source_to_id.get(SRC))
                    pantherid_list = []
                    if key in key_to_ids:
                        pantherid_list = key_to_ids[key]
                    if pantherid not in pantherid_list:
                        pantherid_list.append(pantherid)
                    key_to_ids[key] = pantherid_list
    
    return [ORF_to_panther_id,key_to_ids]

def get_locus_id(ORF,ORF_to_locus_id):
    # ORF = panther_id_to_ORF.get(panther_id)

    if ORF is None:
        return None
    
    locus_id = ORF_to_locus_id.get(ORF)
    if locus_id is None:
        log.info("The ORF: " + ORF + " is not in the database.")
        return None

    return locus_id

def update_aliases(nex_session,fw,key,ids,ids_DB,ORF_to_locus_id,id_to_source):
    if set(ids_DB) == set(ids):
        return
    
    (ORF,alias_type,source_id) = key
    locus_id = get_locus_id(ORF,ORF_to_locus_id)
    
    if locus_id is None:
        return
    
    for ID in ids:
        if ID in ids_DB:
            ids_DB.remove(ID)
            continue
        insert_alias(nex_session,fw,locus_id,source_id,ID)
        global ADDED
        ADDED = ADDED + 1
    
    for ID in ids_DB:
        delete_alias(nex_session,fw,locus_id,ID)
        global DELETED
        DELETED = DELETED + 1

# def update_panther_id(nex_session,fw,locus_id,panther_id):
    
#     obj_url = OBJ_URL + panther_id
#     nex_session.query(LocusAlias).filter_by(locus_id=locus_id, alias_type=ALIAS_TYPE).update({"display_name":panther_id,"obj_url":obj_url})
    
#     fw.write("Update "+ALIAS_TYPE+" to "+panther_id+" for locus_id="+str(locus_id)+"\n")
#     global UPDATED
#     UPDATED = UPDATED + 1


def insert_aliases(nex_session,fw,key,ids,ORF_to_locus_id):

    # (panther_id,alias_type,source_id,ORF) = key
    (ORF,alias_type,source_id) = key
    # locus_id = get_locus_id(panther_id,panther_id_to_ORF,ORF_to_locus_id,ORF)
    locus_id = get_locus_id(ORF,ORF_to_locus_id)

    if locus_id is None:
        return
    for id in ids:
        insert_alias(nex_session,fw,locus_id,source_id,id)
        global ADDED
        ADDED = ADDED + 1

def insert_alias(nex_session,fw,locus_id,source_id,panther_id):
    
    obj_url = OBJ_URL + panther_id
    
    x = LocusAlias(
        display_name=panther_id,
        obj_url=obj_url,
        source_id=source_id,
        locus_id=locus_id,
        has_external_id_section="1",
        alias_type=ALIAS_TYPE,
        created_by = CREATED_BY)
    
    nex_session.add(x)

    fw.write("Insert a new " + ALIAS_TYPE + ": " + panther_id + "\n")

def delete_aliases(nex_session,fw,key,ORF_to_locus_id):
    
    (ORF,alias_type,source_id) = key
    locus_id = get_locus_id(ORF,ORF_to_locus_id)
    if locus_id is None:
        return

    nex_session.query(LocusAlias).filter_by(locus_id=locus_id,alias_type=ALIAS_TYPE,source_id=source_id).delete()
    global DELETED
    DELETED = DELETED + 1

def delete_alias(nex_session,fw,locus_id,panther_id):  
    
    nex_session.query(LocusAlias).filter_by(locus_id=locus_id,alias_type=ALIAS_TYPE,display_name=panther_id).delete()
    fw.write("Delete " + ALIAS_TYPE + " " + panther_id + "\n")


if __name__ == '__main__':
    update_data()
