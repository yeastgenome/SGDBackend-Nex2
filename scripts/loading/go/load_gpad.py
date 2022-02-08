from sqlalchemy import or_
import urllib.request, urllib.parse, urllib.error
import gzip
import shutil
import logging
import os
from datetime import datetime
import sys
import importlib
importlib.reload(sys)  # Reload does the trick!
from src.models import Go, Taxonomy, Source, Goannotation, Gosupportingevidence, \
                       Goextension, EcoAlias, Edam, Dbentity, Filedbentity
from scripts.loading.database_session import get_session
from src.helpers import upload_file
from scripts.loading.util import get_relation_to_ro_id, read_gpi_file, \
                                 read_gpad_file, read_noctua_gpad_file, \
                                 read_complex_gpad_file, get_go_extension_link

__author__ = 'sweng66'

## Created on April 2017
## This script is used to load the go annotation (gpad) file into NEX2.

TAXON_ID = 'TAX:4932'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

def load_go_annotations(gpad_file, noctua_gpad_file, complex_gpad_file, gpi_file, annotation_type, log_file):

    nex_session = get_session()

    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()])
    edam_to_id = dict([(x.format_name, x.edam_id) for x in nex_session.query(Edam).all()])
    go_id_to_aspect =  dict([(x.go_id, x.go_namespace) for x in nex_session.query(Go).all()])
    
    deleted_merged_dbentity_ids = []
    for x in nex_session.query(Dbentity).filter_by(subclass='LOCUS').filter(or_(Dbentity.dbentity_status=='Deleted', Dbentity.dbentity_status=='Merged')).all():
        deleted_merged_dbentity_ids.append(x.dbentity_id)

    log.info("GPAD Loading Report for "+ annotation_type + " annotations\n") 
    
    fw = open(log_file, "w")
    
    fw.write(str(datetime.now()) + "\n")
    taxid_to_taxonomy_id =  dict([(x.taxid, x.taxonomy_id) for x in nex_session.query(Taxonomy).all()])
    taxonomy_id = taxid_to_taxonomy_id.get(TAXON_ID)
    if taxonomy_id is None:
        fw.write("The Taxon_id = " + TAXON_ID + " is not in the database\n")
        return

    log.info(str(datetime.now()))
    log.info("Getting Go annotations from database...")
    
    fw.write(str(datetime.now()) + "\n")
    fw.write("getting old annotations from database...\n")
    key_to_annotation = all_go_annotations(nex_session, annotation_type)

    log.info(str(datetime.now()))
    log.info("Getting Go extensions from database...")

    fw.write(str(datetime.now()) + "\n")
    fw.write("getting old go extensions from database...\n")
    annotation_id_to_extensions = all_go_extensions(nex_session)

    log.info(str(datetime.now()))
    log.info("Getting Go supporting evidences from database...")

    fw.write(str(datetime.now()) + "\n")
    fw.write("getting old go supporting evidences from database...\n")
    annotation_id_to_support_evidences = all_go_support_evidences(nex_session)

    log.info(str(datetime.now()))
    log.info("Reading GPI file...")

    fw.write(str(datetime.now()) + "\n")
    fw.write("reading gpi file...\n")
    [uniprot_to_date_assigned, uniprot_to_sgdid_list] = read_gpi_file(gpi_file)

    log.info(str(datetime.now()))
    log.info("Reading GPAD file...")

    fw.write(str(datetime.now()) + "\n")
    fw.write("reading gpad file...\n")
    yes_goextension = 1
    yes_gosupport = 1
    new_pmids = []
    dbentity_id_with_new_pmid = {}
    dbentity_id_with_uniprot = {}
    bad_ref = []
    foundAnnotation = {}
    data = read_gpad_file(gpad_file, nex_session, uniprot_to_date_assigned, 
    	   	          uniprot_to_sgdid_list, foundAnnotation, 
                          yes_goextension, yes_gosupport, 
			  new_pmids, dbentity_id_with_new_pmid, 
                          dbentity_id_with_uniprot, bad_ref)

    noctua_data = []
    complex_data = []
    if annotation_type == 'manually curated':
        log.info(str(datetime.now()))
        log.info("Reading noctua GPAD file...")

        fw.write(str(datetime.now()) + "\n")
        fw.write("reading noctua gpad file...\n")

        sgdid_to_date_assigned = {}
        for uniprot in uniprot_to_date_assigned:
            date_assigned = uniprot_to_date_assigned[uniprot]
            sgdid_list = uniprot_to_sgdid_list.get(uniprot, [])
            for sgdid in sgdid_list:
                sgdid_to_date_assigned[sgdid] = date_assigned

        noctua_data = read_noctua_gpad_file(noctua_gpad_file, nex_session, 
                                            sgdid_to_date_assigned, foundAnnotation,
                                            yes_goextension, yes_gosupport, new_pmids, 
                                            dbentity_id_with_new_pmid, bad_ref)
        log.info(str(datetime.now()))
        log.info("Reading complex portal GPAD file...")

        fw.write(str(datetime.now()) + "\n")
        fw.write("reading complex portal gpad file...\n")

        complex_data = read_complex_gpad_file(complex_gpad_file, nex_session,
                                              foundAnnotation, yes_goextension,
                                              yes_gosupport, new_pmids, bad_ref)
        
        
    nex_session.close()

    log.info(str(datetime.now()))
    log.info("Loading the new data into database...")

    # load the new data into the database
    fw.write(str(datetime.now()) + "\n")
    fw.write("loading the new data into the database...\n")
    [hasGoodAnnot, annotation_update_log] = load_new_data(data, noctua_data, complex_data,
                                                          source_to_id, annotation_type,
                                                          key_to_annotation, 
                                                          annotation_id_to_extensions, 
                                                          annotation_id_to_support_evidences, 
                                                          taxonomy_id, go_id_to_aspect,
                                                          deleted_merged_dbentity_ids, fw)
    
    log.info(str(datetime.now()))
    log.info("Deleting obsolete Go annotation entries...")

    ## uncomment out the following when it is ready
    fw.write(str(datetime.now()) + "\n")
    fw.write("deleting obsolete go_annotation entries...\n") 
    delete_obsolete_annotations(key_to_annotation, 
                                hasGoodAnnot, 
                                go_id_to_aspect,
                                annotation_update_log, 
                                source_to_id,
                                dbentity_id_with_new_pmid,
                                dbentity_id_with_uniprot,
                                fw)

    if annotation_type == 'manually curated':

        log.info(str(datetime.now()))
        log.info("Uploading GPAD/GPI files to AWS...")

        ENGINE_CREATED = 1
        update_database_load_file_to_s3(nex_session, gpad_file, source_to_id, 
                                        edam_to_id, ENGINE_CREATED)
        ENGINE_CREATED = 1
        update_database_load_file_to_s3(nex_session, gpi_file, source_to_id,
                                        edam_to_id, ENGINE_CREATED)
        ENGINE_CREATED = 1
        update_database_load_file_to_s3(nex_session, noctua_gpad_file, source_to_id, 
                                        edam_to_id, ENGINE_CREATED)

    log.info(str(datetime.now()))
    log.info("Writing summary...")

    fw.write(str(datetime.now()) + "\n") 
    fw.write("writing summary and sending an email to curator about new pmids...\n")
    write_summary_and_send_email(annotation_update_log, new_pmids, bad_ref, fw, annotation_type)
    
    fw.close()

    log.info(str(datetime.now()))
    log.info("Done!\n\n")


def load_new_data(data, noctua_data, complex_data, source_to_id, annotation_type, key_to_annotation, annotation_id_to_extensions, annotation_id_to_support_evidences, taxonomy_id, go_id_to_aspect, deleted_merged_dbentity_ids, fw):

    annotation_update_log = {}
    for count_name in ['annotation_updated', 'annotation_added', 'annotation_deleted',
                       'extension_added', 'extension_deleted', 'supportevidence_added',
                       'supportevidence_deleted']:
        annotation_update_log[('manually curated', count_name)] = 0
        annotation_update_log[('computational', count_name)] = 0
        annotation_update_log[('high-throughput', count_name)] = 0

    hasGoodAnnot = {}

    allowed_types = [annotation_type]
    if annotation_type == 'manually curated':
        allowed_types.append('high-throughput')

    nex_session = get_session()

    i = 0

    seen = {}
    key_to_annotation_id = {}
    annotation_id_to_extension = {}
    annotation_id_to_support = {}
    for x in data + noctua_data + complex_data:
        if x['annotation_type'] not in allowed_types:
            continue
        if x['dbentity_id'] in deleted_merged_dbentity_ids:
            continue
        source_id = source_to_id.get(x['source'])
        if x['source'] == 'EnsemblPlants' or x['source'] == 'AgBase':
            continue
        if source_id is None:
            print("The source: ", x['source'], " is not in the SOURCE table.")
            continue

        i = i + 1
        if i > 1000:
            nex_session.close()
            nex_session = get_session()
            i = 0

        try:
            # nex_session = get_session()

            dbentity_id = x['dbentity_id']
            go_id = x['go_id']

            key = (dbentity_id, go_id, x['eco_id'], x['reference_id'], x['annotation_type'],
                   x['source'], x['go_qualifier'], taxonomy_id)

            if key in seen:
                if str(x) == str(seen[key]):
                    continue                
                annotation_id = key_to_annotation_id[key]
                if x.get('goextension') is not None:
                    if annotation_id in annotation_id_to_extension:
                        (goextension, date_created, created_by, annotation_type) = annotation_id_to_extension[annotation_id]
                        goextension = goextension + "|" + x['goextension']
                    else:
                        goextension = x['goextension']
                    annotation_id_to_extension[annotation_id] = (goextension, x['date_created'], x['created_by'], x['annotation_type'])
                if x.get('gosupport') is not None:
                    if annotation_id in annotation_id_to_support:
                        (gosupport, date_created, created_by, annotation_type) = annotation_id_to_support[annotation_id]
                        gosupport = gosupport + "|" + x['gosupport']
                    else:
                        gosupport = x['gosupport']
                    annotation_id_to_support[annotation_id] = (gosupport, x['date_created'], x['created_by'], x['annotation_type'])
                continue

            seen[key] = x

            annotation_id = None
    
            if key in key_to_annotation:
            
                # remove the new key from the dictionary
                # and the rest can be deleted later
                thisAnnot = key_to_annotation.pop(key)
                annotation_id = thisAnnot.annotation_id
                ## this annotation is in the database, so update  
                ## the date_assigned if it is changed
                ## but no need to update created_by and date_created
                #####  date_assigned_in_db = str(getattr(thisAnnot, 'date_assigned'))
                date_assigned_in_db = thisAnnot.date_assigned
                date_assigned_db = str(date_assigned_in_db).split(" ")[0]

                if x['date_assigned'] is None:
                    fw.write("No date_assigned for key=" + str(key) + "\n")
                    continue

                if date_assigned_db != str(x['date_assigned']):
                    fw.write("UPDATE GOANNOTATION: key=" + str(key) + " OLD date_assigned=" + date_assigned_db + ", NEW date_assigned=" + str(x['date_assigned']) + "\n")
                    # nex_session.query(Goannotation).filter_by(id=thisAnnot.annotation_id).update({"date_assigned": x['date_assigned']})
                    thisAnnot.date_assigned = x['date_assigned']
                    nex_session.add(thisAnnot)
                    nex_session.flush()
                    count_key = (x['annotation_type'], 'annotation_updated')
                    annotation_update_log[count_key] = annotation_update_log[count_key] + 1
            else:

                if x['date_assigned'] is None:
                    fw.write("No date_assigned for key=" + str(key) + "\n")
                    continue

                # print "KEY=", str(key), " is a NEW ENTRY"

                fw.write("NEW GOANNOTATION: key=" + str(key) + "\n")

                created_by = x['created_by']
                if created_by == '<NULL>' or created_by is None or created_by == 'NULL':
                    created_by = CREATED_BY

                thisAnnot = Goannotation(dbentity_id = dbentity_id, 
                                         source_id = source_id, 
                                         taxonomy_id = taxonomy_id, 
                                         reference_id = x['reference_id'], 
                                         go_id = go_id, 
                                         eco_id = x['eco_id'], 
                                         annotation_type = x['annotation_type'], 
                                         go_qualifier = x['go_qualifier'], 
                                         date_assigned = x['date_assigned'], 
                                         date_created = x['date_created'], 
                                         created_by = created_by)
                nex_session.add(thisAnnot)
                nex_session.flush()
                annotation_id = thisAnnot.annotation_id
                count_key= (x['annotation_type'], 'annotation_added')
                annotation_update_log[count_key] = annotation_update_log[count_key] + 1

            # nex_session.commit()
            
            created_by = x['created_by']
            if created_by == '<NULL>' or created_by is None or created_by == 'NULL':
                created_by = CREATED_BY
            
            key_to_annotation_id[key] = annotation_id
            if x.get('goextension') is not None:
                annotation_id_to_extension[annotation_id] = (x['goextension'], x['date_created'], created_by, x['annotation_type'])
            if x.get('gosupport') is not None:
                annotation_id_to_support[annotation_id] = (x['gosupport'], x['date_created'], created_by, x['annotation_type'])

            hasGoodAnnot[(dbentity_id, go_id_to_aspect[go_id])] = 1
        
        finally:
            nex_session.commit()

    nex_session.close()
    ## update goextension table

    # print "Upadting GO extension data..."

    nex_session = get_session()

    for annotation_id in annotation_id_to_extension:
        (goextension, date_created, created_by, annotation_type) = annotation_id_to_extension[annotation_id]
        update_goextension(nex_session, annotation_id, goextension, annotation_id_to_extensions, 
                           date_created, created_by, annotation_type, 
                           annotation_update_log, fw)

    nex_session.close()

    ## update gosupportingevidence table

    # print "Updating GO supporting evidence data..."

    nex_session = get_session()

    for annotation_id in annotation_id_to_support:
        (gosupport, date_created, created_by, annotation_type) = annotation_id_to_support[annotation_id]
        update_gosupportevidence(nex_session, annotation_id, gosupport, annotation_id_to_support_evidences, 
                                 date_created, created_by, annotation_type, 
                                 annotation_update_log, fw)

    nex_session.close()

    return [hasGoodAnnot, annotation_update_log]


def update_goextension(nex_session, annotation_id, goextension, annotation_id_to_extensions, date_created, created_by, annotation_type, annotation_update_log, fw):

    if created_by == '<NULL>' or created_by is None or created_by == 'NULL':
        created_by = CREATED_BY

    key_to_extension = {}
    if annotation_id in annotation_id_to_extensions:
        key_to_extension = annotation_id_to_extensions[annotation_id]
   
    groups = goextension.split('|')
    seen_this_group = {}
    group_id = 0
    for group in groups:
        if group in seen_this_group:
            continue
        seen_this_group[group] = 1
        members = group.split(',')
        group_id = group_id + 1
        seen_this_member = {}
        for member in members:
            if member in seen_this_member:
                continue
            seen_this_member[member] = 1
            pieces = member.split('(')
            role = pieces[0].replace('_', ' ')
            ro_id = get_relation_to_ro_id(role)
            if ro_id is None:
                print(role, " is not in RO table.")
                continue
            
            dbxref_id = pieces[1][:-1]
            if dbxref_id.startswith('EcoGene:') or dbxref_id.startswith('UniPathway:'):
                continue
            link = get_go_extension_link(dbxref_id)
            if link.startswith('Unknown'):
                if dbxref_id.startswith('IntAct:'):
                    continue
                else:
                    print("Unknown ID: ", dbxref_id)
                    continue

            key = (group_id, ro_id, dbxref_id)
            if key in key_to_extension:
                # print "GO extension ", key, " is in the database."
                x = key_to_extension.pop(key)
                if x.obj_url != link:
                    x.obj_url = link
                    nex_session.add(x)
                    nex_session.flush()
            else:

                # print "NEW GO extension ", key
                
                thisExtension = Goextension(annotation_id = annotation_id,
                                            group_id = group_id,
                                            dbxref_id = dbxref_id,
                                            obj_url = link,
                                            ro_id = ro_id,
                                            date_created = date_created,
                                            created_by = created_by)
                fw.write("NEW GOEXTENSION: key=" + str(key) + "\n")
                nex_session.add(thisExtension)
                key= (annotation_type, 'extension_added')
                annotation_update_log[key] = annotation_update_log[key] + 1
    to_be_deleted = list(key_to_extension.values())
    
    for row in to_be_deleted:

        # print "DELETE GO extension: ", row.annotation_id, row.group_id, row.ro_id, row.dbxref_id  

        fw.write("DELETE GOEXTENSION: row=" + str(row) + "\n")
        nex_session.delete(row)
        key= (annotation_type, 'extension_deleted')
        annotation_update_log[key] = annotation_update_log[key] + 1
    nex_session.commit()    
    
def update_gosupportevidence(nex_session, annotation_id, gosupport, annotation_id_to_support_evidences, date_created, created_by, annotation_type, annotation_update_log, fw):

    if created_by == '<NULL>' or created_by is None or created_by == 'NULL':
        created_by = CREATED_BY
        
    key_to_support = {}
    if annotation_id in annotation_id_to_support_evidences:
        key_to_support = annotation_id_to_support_evidences[annotation_id]

    groups = gosupport.split('|')
    seen_this_group = {}
    group_id = 0
    for group in groups:
        if group in seen_this_group:
            continue
        seen_this_group[group] = 1
        if group.startswith('With:Not_supplied'):
            break
        dbxref_ids = group.split(',')
        group_id = group_id + 1
        seen_this_id = {}
        for dbxref_id in dbxref_ids:
            if dbxref_id in seen_this_id:
                continue
            seen_this_id[dbxref_id] = 1
            if dbxref_id.startswith('EcoGene:') or dbxref_id.startswith('UniPathway:'):
                continue
            link = get_go_extension_link(dbxref_id)
            if link.startswith('Unknown'):
                print("Unknown ID: ", dbxref_id)
                continue
            evidence_type = 'with'
            if dbxref_id.startswith('GO:'):
                evidence_type = 'from'
                        
            key = (group_id, evidence_type, dbxref_id)
    
            if key in key_to_support:
                # print "GO supporting evidence ", key, " is in the database"
                x = key_to_support.pop(key)
                if x.obj_url != link:
                    x.obj_url = link
                    nex_session.add(x)
                    nex_session.flush()
            else:
                # print "NEW GO supporting evidence ", key
                thisSupport = Gosupportingevidence(annotation_id = annotation_id,
                                                   group_id = group_id,
                                                   dbxref_id = dbxref_id,
                                                   obj_url = link,
                                                   evidence_type = evidence_type,
                                                   date_created = date_created,
                                                   created_by = created_by)

                fw.write("NEW GOSUPPORTINGEVIDENCE: key=" + str(key) + "\n")
                nex_session.add(thisSupport)
                key= (annotation_type, 'supportevidence_added')
                annotation_update_log[key] = annotation_update_log[key] + 1

    to_be_deleted = list(key_to_support.values())

    for row in to_be_deleted:

        # print "DELETE GO supporting evidence ", row.annotation_id, row.group_id, row.evidence_type, row.dbxref_id

        fw.write("DELETE GOSUPPORTINGEVIDENCE: row=" + str(row) +"\n")
        nex_session.delete(row)
        key= (annotation_type, 'supportevidence_deleted')
        annotation_update_log[key] = annotation_update_log[key] + 1
    nex_session.commit()

def all_go_extensions(nex_session):
    
    annotation_id_to_extensions = {}

    for x in nex_session.query(Goextension).all():
        key_to_extension = {}
        if x.annotation_id in annotation_id_to_extensions:
            key_to_extension = annotation_id_to_extensions[x.annotation_id]
        key = (x.group_id, x.ro_id, x.dbxref_id) 
        key_to_extension[key] = x
        annotation_id_to_extensions[x.annotation_id] = key_to_extension
        
    return annotation_id_to_extensions


def all_go_support_evidences(nex_session):

    annotation_id_to_support_evidences = {}

    for x in nex_session.query(Gosupportingevidence).all():
        key_to_support_evidence = {}
        if x.annotation_id in annotation_id_to_support_evidences:
            key_to_support_evidence = annotation_id_to_support_evidences[x.annotation_id]
        key = (x.group_id, x.evidence_type, x.dbxref_id)
        key_to_support_evidence[key] =x
        annotation_id_to_support_evidences[x.annotation_id] = key_to_support_evidence

    return annotation_id_to_support_evidences


def all_go_annotations(nex_session, annotation_type):
        
    key_to_annotation = {}
    for x in nex_session.query(Goannotation).all():
        if (x.source.display_name in ['SGD', 'GO_Central', 'ComplexPortal'] and x.annotation_type in ['manually curated', 'high-throughput'] and annotation_type == 'manually curated') or (annotation_type == 'computational' and x.annotation_type=='computational'):
            key = (x.dbentity_id, x.go_id, x.eco_id, x.reference_id, x.annotation_type, x.source.display_name, x.go_qualifier, x.taxonomy_id)
            key_to_annotation[key] = x

    return key_to_annotation 


def delete_obsolete_annotations(key_to_annotation, hasGoodAnnot, go_id_to_aspect, annotation_update_log, source_to_id, dbentity_id_with_new_pmid, dbentity_id_with_uniprot, fw):

    nex_session = get_session()
    
    evidence_to_eco_id = dict([(x.display_name, x.eco_id) for x in nex_session.query(EcoAlias).all()])

    src_id = source_to_id['SGD']

    to_be_deleted = list(key_to_annotation.values())

    try:

        ## add check to see if there are any valid htp annotations..                                         
        # for x in nex_session.query(Goannotation).filter_by(source_id=src_id).filter_by(annotation_type='high-throughput').all():
        #    hasGoodAnnot[(x.dbentity_id, go_id_to_aspect[x.go_id])] = 1

        ## delete the old ones -                                                                            

        for x in to_be_deleted:

            ## don't delete the annotations for the features with a pmid not in db yet 
            ## (so keep the old annotations for now) 
            if dbentity_id_with_new_pmid.get(x.dbentity_id) is not None:
                continue

            ## ## don't delete PAINT annotations (they are not in GPAD files yet)                              
            ## if x.source_id == source_to_id['GO_Central']:
            ##    continue

            # aspect = go_id_to_aspect[x.go_id]
            # if x.eco_id == evidence_to_eco_id['ND'] and hasGoodAnnot.get((x.dbentity_id, aspect)) is None:
            #    ## still keep the ND annotation if there is no good annotation available yet 
            #    continue
            if dbentity_id_with_uniprot.get(x.dbentity_id):
                ## don't want to delete the annotations that are not in GPAD file yet
                ## do we still have any annotations that are not in GPAD? but just in case
                delete_extensions_evidences(nex_session, x.annotation_id)
                nex_session.delete(x)
                nex_session.commit()
                fw.write("DELETE GOANNOTATION: row=" + str(x) + "\n")
                key = (x.annotation_type, 'annotation_deleted')
                annotation_update_log[key] = annotation_update_log[key] + 1
    finally:
        nex_session.close()
    
def delete_extensions_evidences(nex_session, annotation_id):

    to_delete_list = nex_session.query(Goextension).filter_by(annotation_id=annotation_id).all()
    for x in to_delete_list:
        nex_session.delete(x)
        
    to_delete_list = nex_session.query(Gosupportingevidence).filter_by(annotation_id=annotation_id).all()
    for x in to_delete_list:
        nex_session.delete(x)

def update_database_load_file_to_s3(nex_session, go_file, source_to_id, edam_to_id, ENGINE_CREATED):

    import hashlib

    desc = "Gene Product Association Data (GPAD)"
    if "gp_information" in go_file:
        desc = "Gene Product Information (GPI)"

    go_local_file = open(go_file, mode='rb')
   
    go_md5sum = hashlib.md5(go_file.encode()).hexdigest()
    
    go_row = nex_session.query(Filedbentity).filter_by(md5sum = go_md5sum).one_or_none()
    
    if go_row is not None:
        log.info("The current version of " + go_file + " is already in the database.\n")
        return
    
    log.info("Adding " + go_file + " to the database.\n")

    if "gp_association" in go_file:
        nex_session.query(Dbentity).filter(Dbentity.display_name.like('gp_association.559292_sgd%')).filter(Dbentity.dbentity_status=='Active').update({"dbentity_status":'Archived'}, synchronize_session='fetch')
    elif "gp_information" in go_file:
        nex_session.query(Dbentity).filter(Dbentity.display_name.like('gp_information.559292_sgd%')).filter(Dbentity.dbentity_status=='Active').update({"dbentity_status":'Archived'}, synchronize_session='fetch')
    elif "noctua_sgd.gpad" in go_file:
        nex_session.query(Dbentity).filter(Dbentity.display_name.like('noctua_sgd.gpad%')).filter(Dbentity.dbentity_status=='Active').update({"dbentity_status":'Archived'}, synchronize_session='fetch')
    nex_session.commit()

    data_id = edam_to_id.get('EDAM:2353')   ## data:2353 Ontology data
    topic_id = edam_to_id.get('EDAM:0089')  ## topic:0089 Ontology and terminology
    format_id = edam_to_id.get('EDAM:3475') ## format:3475 TSV

    # if ENGINE_CREATED == 0:
    from sqlalchemy import create_engine
    from src.models import DBSession
    engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
    DBSession.configure(bind=engine)
        
    if go_row is None:
        upload_file(CREATED_BY, go_local_file,
                    filename=go_file,
                    file_extension='.gz',
                    description=desc,
                    display_name=go_file,
                    data_id=data_id,
                    format_id=format_id,
                    topic_id=topic_id,
                    status='Active',
                    is_public=True,
                    is_in_spell=False,
                    is_in_browser=False,
                    file_date=datetime.now(),
                    source_id=source_to_id['SGD'],
                    md5sum=go_md5sum)


def write_summary_and_send_email(annotation_update_log, new_pmids, bad_ref, fw, annot_type):

    summary = ''
    
    if len(new_pmids) > 0:
        summary = "The following Pubmed ID(s) are not in the oracle database. Please add them into the database so the missing annotations can be added @next run." + "\n" + ", ".join(new_pmids) + "\n\n"

    if len(bad_ref) > 0:
        summary = summary + "The following new GO_Reference(s) don't have a corresponding SGDID yet." + "\n" + ', '.join(bad_ref) + "\n"

    count_names = ['annotation_added', 'annotation_updated', 'annotation_deleted', 'extension_added', 'extension_deleted', 'supportevidence_added', 'supportevidence_deleted']

    for annotation_type in ['manually curated', 'computational']:
        if annotation_type != annot_type:
            continue
        header = annotation_type.title()
        summary = summary + "\n" + header + " annotations: \n\n"
        for count_name in count_names:
            key = (annotation_type, count_name)
            if annotation_update_log.get(key) is not None:
                if count_name.endswith('updated'):
                    words = count_name.replace('_', ' entries with date_assigned ')
                else:
                    words = count_name.replace('_', ' entries ')
                summary = summary + "In total " + str(annotation_update_log[key]) + " " + words + "\n"
            
    fw.write(summary)

    log.info(summary)


if __name__ == "__main__":
        
    # ftp://ftp.ebi.ac.uk/pub/contrib/goa/gp_association.559292_sgd.gz
    # ftp://ftp.ebi.ac.uk/pub/contrib/goa/gp_information.559292_sgd.gz
    # http://current.geneontology.org/products/annotations/noctua_sgd.gpad.gz

    datestamp = str(datetime.now()).split(" ")[0].replace("-", "")

    url_path = 'ftp://ftp.ebi.ac.uk/pub/contrib/goa/'
    gpad_file = 'gp_association.559292_sgd.gz'
    dated_gpad_file = 'gp_association.559292_sgd_' + datestamp + '.gpad.gz' 
    gpi_file = 'gp_information.559292_sgd.gz'
    dated_gpi_file = 'gp_information.559292_sgd_' + datestamp + '.gpi.gz'
    urllib.request.urlretrieve(url_path + gpad_file, dated_gpad_file)
    urllib.request.urlcleanup()
    urllib.request.urlretrieve(url_path + gpi_file, dated_gpi_file)

    # noctua_path = 'http://current.geneontology.org/products/annotations/'
    noctua_path = 'http://snapshot.geneontology.org/products/annotations/'
    noctua_gpad_file = 'noctua_sgd.gpad.gz'
    dated_noctua_gpad_file = 'noctua_sgd.gpad_' + datestamp + '.gz'
    urllib.request.urlcleanup()
    urllib.request.urlretrieve(noctua_path + noctua_gpad_file, dated_noctua_gpad_file)

    # complex_path = 'http://ftp.ebi.ac.uk/pub/databases/intact/complex/current/go/' 
    complex_path = 'http://ftp.ebi.ac.uk/pub/databases/intact/complex/current/go/'
    complex_gpad_file = 'complex_portal.v2.gpad'
    dated_complex_gpad_file = 'complex_portal.v2.gpad_' + datestamp 
    urllib.request.urlcleanup()
    urllib.request.urlretrieve(complex_path + complex_gpad_file, dated_complex_gpad_file)

    gpadFileInfo = os.stat(dated_gpad_file)
    gpiFileInfo = os.stat(dated_gpi_file)
    gpadFile4noctua = os.stat(dated_noctua_gpad_file)
    gpadFile4complex = os.stat(dated_complex_gpad_file)
    
    if gpadFileInfo.st_size < 1900000:
        print("This week's GPAD file size is too small, please check: ftp://ftp.ebi.ac.uk/pub/contrib/goa/gp_association.559292_sgd.gz")  
        exit()

    if gpiFileInfo.st_size < 370000:
        print("This week's GPI file size is too small, please check: ftp://ftp.ebi.ac.uk/pub/contrib/goa/gp_information.559292_sgd.gz")
        exit()

    if gpadFile4noctua.st_size < 14000:
        print("This week's noctua GPAD file size is too small, please check: http://snapshot.geneontology.org/products/annotations/noctua_sgd.gpad.gz")
        exit()

    if gpadFile4complex.st_size < 2000000:
        print("This week's complex portal GPAD file size is too small, please check: http://ftp.ebi.ac.uk/pub/databases/intact/complex/current/go/complex_portal.v2.gpad")
        exit()

    if len(sys.argv) >= 2:
        annotation_type = sys.argv[1]
    else:
        # annotation_type = "manually curated"
        print("Usage:         python load_gpad.py annotation_type[manually curated|computational]")
        print("Usage example: python load_gpad.py 'manually curated'")
        print("Usage example: python load_gpad.py computational")
        exit()
    
    log_file = "scripts/loading/go/logs/GPAD_loading_" + annotation_type.replace(" ", "-") + ".log"

    load_go_annotations(dated_gpad_file, dated_noctua_gpad_file, dated_complex_gpad_file,
                        dated_gpi_file, annotation_type, log_file)


    
        
