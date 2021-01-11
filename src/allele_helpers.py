import logging
import os
from sqlalchemy import or_
from pyramid.httpexceptions import HTTPBadRequest, HTTPOk
from sqlalchemy.exc import IntegrityError, DataError
import transaction
import json
from src.models import DBSession, So, SoRelation, Dbentity, Alleledbentity, AlleleReference,\
                       Literatureannotation, AlleleAlias, AllelealiasReference, LocusAllele,\
                       LocusalleleReference, Referencedbentity, Locusdbentity, Taxonomy, Source,\
                       Phenotypeannotation, AlleleGeninteraction
from src.curation_helpers import get_curator_session

PREVIEW_URL = os.environ['PREVIEW_URL']

PARENT_SO_TERM = 'structural variant'
TAXON = 'TAX:4932'

log = logging.getLogger('curation')

def insert_locusallele_reference(curator_session, CREATED_BY, source_id, locus_allele_id, reference_id):

    x = None
    try:
        x = LocusalleleReference(locus_allele_id = locus_allele_id,
                                 reference_id = reference_id,
                                 source_id = source_id,
                                 created_by = CREATED_BY)
        curator_session.add(x)
        # transaction.commit()
        return 1
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        return str(e)

def insert_allelealias_reference(curator_session, CREATED_BY, source_id, allele_alias_id, reference_id):

    x = None
    try:
        x = AllelealiasReference(allele_alias_id = allele_alias_id,
                                 reference_id = reference_id,
                                 source_id = source_id,
                                 created_by = CREATED_BY)
        curator_session.add(x)
        # transaction.commit()
        return 1
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        return str(e)

def insert_allele_reference(curator_session, CREATED_BY, source_id, allele_id, reference_id, reference_class):

    x = None
    try:
        if reference_class is None:
            x = AlleleReference(allele_id = allele_id,
                                reference_id = reference_id,
                                source_id = source_id,
                                created_by = CREATED_BY)
        else:
            x = AlleleReference(allele_id = allele_id,
                                reference_id = reference_id,
                                reference_class = reference_class,
                                source_id = source_id,
                                created_by = CREATED_BY)
        curator_session.add(x)
        # transaction.commit()
        return 1
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        return str(e)
    
def insert_allele_alias(curator_session, CREATED_BY, source_id, allele_id, alias_name):

    x = None
    try:
        x = AlleleAlias(allele_id = allele_id,
                        display_name = alias_name,
                        source_id = source_id,
                        alias_type = 'Synonym',
                        created_by = CREATED_BY)
        curator_session.add(x)
        # transaction.commit()
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        return str(e)
    finally:
        curator_session.flush()
        curator_session.refresh(x)
        return x.allele_alias_id

    
def insert_locus_allele(curator_session, CREATED_BY, source_id, allele_id, locus_id):

    x = None
    try:
        x = LocusAllele(allele_id = allele_id,
                        locus_id = locus_id,
                        source_id = source_id,
                        created_by = CREATED_BY)
        curator_session.add(x)
        # transaction.commit()    
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        return str(e)
    finally:
        curator_session.flush()
        curator_session.refresh(x)
        return x.locus_allele_id

def insert_allele(curator_session, CREATED_BY, source_id, allele_name, so_id, desc):

    a = curator_session.query(Alleledbentity).filter_by(display_name=allele_name).one_or_none()
    if a is not None:
        return a.dbentity_id

    isSuccess = False
    returnValue = ""
    allele_id = None

    x = None
    try:
        format_name = allele_name.replace(" ", "_")
        x = Alleledbentity(format_name = format_name,
                           display_name = allele_name,
                           source_id = source_id,
                           subclass = 'ALLELE',
                           dbentity_status = 'Active',
                           so_id = so_id,
                           description = desc,
                           created_by = CREATED_BY)
        curator_session.add(x)
        # transaction.commit()
        isSuccess = True
        returnValue = "Allele: '" + allele_name + "' added successfully."
    except IntegrityError as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        isSuccess = False
        returnValue = 'Insert allele failed: ' + str(e.orig.pgerror)
    except DataError as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        isSuccess = False
        returnValue = 'Insert allele failed: ' + str(e.orig.pgerror)
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        isSuccess = False
        returnValue = 'Insert allele failed' + ' ' + str(e.orig.pgerror)
    finally:
        curator_session.flush()
        curator_session.refresh(x)
        allele_id = x.dbentity_id

    if isSuccess:
        return allele_id
    else:
        return returnValue

def insert_literatureannotation(curator_session, CREATED_BY, source_id, allele_id, reference_id, topic, taxonomy_id):

    all = curator_session.query(Literatureannotation).filter_by(dbentity_id=allele_id, reference_id=reference_id).all()
    found = 0
    for x in all:
        if x.topic in ['Additional Literature', 'Primary Literature']:
            found = 1
    if found == 1:
        return 1
        
    x = None
    try:
        x = Literatureannotation(dbentity_id = allele_id,
                                 reference_id = reference_id,
                                 topic = topic,
                                 taxonomy_id = taxonomy_id,
                                 source_id = source_id,
                                 created_by = CREATED_BY)
        curator_session.add(x)
        # transaction.commit()
        return 1
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        return str(e)
        
def get_all_allele_types(request):

    try:        
        parent_id_to_child_ids = {}
        for x in DBSession.query(SoRelation).all():
            child_ids = []
            if x.parent_id in parent_id_to_child_ids:
                child_ids = parent_id_to_child_ids[x.parent_id]
            child_ids.append(x.child_id)
            parent_id_to_child_ids[x.parent_id] = child_ids
        
        s = DBSession.query(So).filter_by(display_name=PARENT_SO_TERM).one_or_none()
        so_id_list = [s.so_id]
        for so_id in so_id_list:
            child_ids = parent_id_to_child_ids.get(so_id, [])
            for child_id in child_ids:
                if child_id is not so_id_list:
                    so_id_list.append(child_id)
        
        data = []
        so_id_to_so = dict([(x.so_id, x) for x in DBSession.query(So).all()])
        found = {}
        for so_id in so_id_list:
            so = so_id_to_so[so_id]
            if so_id in found:
                continue
            found[so_id] = 1
            data.append( { 'so_id': so_id,
                           'format_name': so.term_name,
                           'display_name': so.display_name } )
            
        return HTTPOk(body=json.dumps(data), content_type='text/json')
        
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}))
    finally:
        if DBSession:
            DBSession.remove()

        
def get_one_allele(request):

    try:
        
        data = {}
        
        allele_format_name = str(request.matchdict['allele_format_name'])
    
        a = DBSession.query(Alleledbentity).filter_by(format_name=allele_format_name).one_or_none()
        
        if a is None:
            return HTTPBadRequest(body=json.dumps({'error': "The allele format_name " + allele_format_name + " is not in the database."}))
        data['allele_name'] = a.display_name
        data['format_name'] = a.format_name
        data['sgdid'] = a.sgdid
        data['so_id'] = a.so.so_id
        data['allele_type'] = a.so.display_name
        data['description'] = a.description
        
        ## get pmids from allele_reference
        allele_name_pmids = []
        description_pmids = []
        allele_type_pmids = []
        for x in DBSession.query(AlleleReference).filter_by(allele_id=a.dbentity_id).all():        
            if x.reference_class == 'allele_name':
                allele_name_pmids.append(x.reference.pmid)
            elif x.reference_class == 'allele_description':
                description_pmids.append(x.reference.pmid)
            elif x.reference_class == 'so_term':
                allele_type_pmids.append(x.reference.pmid)
        data['allele_name_pmids'] = allele_name_pmids
        data['description_pmids'] = description_pmids
        data['allele_type_pmids'] = allele_type_pmids
        
        ## get affected_gene and pmids from locus_allele & locusallele_reference
        x = DBSession.query(LocusAllele).filter_by(allele_id=a.dbentity_id).one_or_none()
        pmids = []
        for y in DBSession.query(LocusalleleReference).filter_by(locus_allele_id=x.locus_allele_id).all():
            pmids.append(y.reference.pmid)

        data['affected_gene'] = { 'display_name': x.locus.systematic_name,
                                  'sgdid': x.locus.sgdid,
                                  'pmids': pmids } 
   
        ## get aliases and pmids from allele_alias & allelealias_reference
        aliases = []
        for x in DBSession.query(AlleleAlias).filter_by(allele_id=a.dbentity_id).order_by(AlleleAlias.display_name).all():
            pmids = []
            for y in DBSession.query(AllelealiasReference).filter_by(allele_alias_id=x.allele_alias_id).all(): 
                pmids.append(y.reference.pmid)
            aliases.append( { 'display_name': x.display_name,
                              'pmids': pmids } )
        data['aliases'] = aliases
        
        return HTTPOk(body=json.dumps(data),content_type='text/json')
    except Exception as e:
        log.error(e)
        return HTTPBadRequest(body=json.dumps({'error': str(e)}))
    finally:
        if DBSession:
            DBSession.remove()

            
def get_list_of_alleles(request):

    try:
        allele_query = str(request.matchdict['allele_query'])
        data = []
        for x in DBSession.query(Alleledbentity).filter(Alleledbentity.display_name.ilike('%'+allele_query+'%')).order_by(Alleledbentity.display_name).all():
            data.append({ 'allele_name': x.display_name,
                          'format_name': x.format_name,
                          'sgdid': x.sgdid,
                          'allele_type': x.so.display_name,
                          'description': x.description })
        return HTTPOk(body=json.dumps(data),content_type='text/json')
    except Exception as e:
        log.error(e)
        return HTTPBadRequest(body=json.dumps({'error': str(e)}))
    finally:
        if DBSession:
            DBSession.remove()    

def get_reference_id_by_pmid(pmid):

    ref = DBSession.query(Referencedbentity).filter_by(pmid=pmid).one_or_none()

    if ref:
        return ref.dbentity_id
    return None

def check_pmids(pmids, pmid_to_reference_id):

    reference_ids = []
    bad_pmids = []
    for pmid in pmids.split(' '):
        if pmid == '':
            continue
        reference_id = pmid_to_reference_id.get(int(pmid))
        if reference_id is None:
            reference_id = get_reference_id_by_pmid(int(pmid))
        if reference_id is None:
            if pmid not in bad_pmids:
                bad_pmids.append(pmid)
            continue
        else:
            pmid_to_reference_id[int(pmid)] = reference_id
        if (reference_id, pmid) not in reference_ids:
            reference_ids.append((reference_id, pmid))
    err_message = ''
    if len(bad_pmids) > 0:
        err_message = "The PMID(s):" + ', '.join(bad_pmids) + " are not in the database"
    return (reference_ids, err_message)

def add_allele_data(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        sgd = DBSession.query(Source).filter_by(display_name='SGD').one_or_none()
        source_id = sgd.source_id

        ## allele name & references
        
        allele_name = request.params.get('allele_name')
        if allele_name == '':
            return HTTPBadRequest(body=json.dumps({'error': "Allele name field is blank"}), content_type='text/json')

        d = DBSession.query(Dbentity).filter_by(subclass='ALLELE').filter(Dbentity.display_name.ilike(allele_name)).one_or_none()
        if d is not None:
            return HTTPBadRequest(body=json.dumps({'error': "The allele name " + allele_name + " is already in the database."}), content_type='text/json')
        
        so_id = request.params.get('so_id')
        if so_id and str(so_id).isdigit():
            so_id = int(so_id)
        else:
            return HTTPBadRequest(body=json.dumps({'error': "Allele type field is blank"}), content_type='text/json')

        desc = request.params.get('description')

        # return HTTPBadRequest(body=json.dumps({'error': "ALLELE_NAME"}), content_type='text/json')
        
        returnValue = insert_allele(curator_session, CREATED_BY, source_id, allele_name, so_id, desc)
        allele_id = None
        success_message = ""
        if str(returnValue).isdigit():
            allele_id = returnValue
            success_message = success_message + "<br>" + "The new allele '" + allele_name + "' has been added into DBENTITY/ALLELEDBENTITY tables. "
        else:
            return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')

        
        # return HTTPBadRequest(body=json.dumps({'error': "allele_id="+str(allele_id)}), content_type='text/json')
    
        
        allele_name_pmids = request.params.get('allele_name_pmids')

        
        # return HTTPBadRequest(body=json.dumps({'error': "allele_name_pmids="+str(allele_name_pmids)}), content_type='text/json')

        all_reference_id = []
        
        pmid_to_reference_id = {}

        (reference_ids, err_message) = check_pmids(allele_name_pmids, pmid_to_reference_id)

        if err_message != '':
            return HTTPBadRequest(body=json.dumps({'error': err_message}), content_type='text/json')

        for (reference_id, pmid) in reference_ids:
            if reference_id not in all_reference_id:
                all_reference_id.append(reference_id)
            returnValue = insert_allele_reference(curator_session, CREATED_BY, source_id,
                                                  allele_id, reference_id, "allele_name")
            if returnValue != 1:
                return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')
            success_message = success_message + "<br>" + "The paper for PMID= " + pmid + " has been added into ALLELE_REFERENCE table for 'allele_name'. "

        # return HTTPBadRequest(body=json.dumps({'error': "allele_name reference_ids="+str(reference_ids)}), content_type='text/json')

        ## affected gene & reference(s)
        
        affected_gene = request.params.get('affected_gene')
        affected_gene = affected_gene.replace("SGD:", '')
        
        locus = DBSession.query(Locusdbentity).filter(or_(Locusdbentity.systematic_name.ilike(affected_gene), Locusdbentity.sgdid.ilike(affected_gene))).one_or_none()
        if locus is None:
            return HTTPBadRequest(body=json.dumps({'error': "The affected gene " + affected_gene + " is not in the database. Please enter an ORF name or a SGDID."}), content_type='text/json')

        affected_gene = locus.display_name
        
        if allele_name.upper().startswith(affected_gene.upper()):
            locus_id = locus.dbentity_id
            returnValue = insert_locus_allele(curator_session, CREATED_BY, source_id, allele_id, locus_id)
            locus_allele_id = None
            if str(returnValue).isdigit():
                locus_allele_id = returnValue
                success_message = success_message + "<br>" + "The affected gene '" + affected_gene + "' has been added into LOCUS_ALLELE table. "
            else:
                return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')


            # return HTTPBadRequest(body=json.dumps({'error': "locus_id="+str(locus_id)}), content_type='text/json')

            
            affected_gene_pmids = request.params.get('affected_gene_pmids')

            # return HTTPBadRequest(body=json.dumps({'error': "affected_gene_pmids="+affected_gene_pmids}), content_type='text/json')
                
            (reference_ids, err_message) = check_pmids(affected_gene_pmids, pmid_to_reference_id)

            
            # return HTTPBadRequest(body=json.dumps({'error': "reference_ids="+str(reference_ids)}), content_type='text/json')

            
            if err_message != '':
                return HTTPBadRequest(body=json.dumps({'error': err_message}), content_type='text/json')
            
            for (reference_id, pmid) in reference_ids:
                if reference_id not in all_reference_id:
                    all_reference_id.append(reference_id)
                returnValue = insert_locusallele_reference(curator_session, CREATED_BY, source_id,
                                                           locus_allele_id, reference_id)
                if returnValue != 1:
                    return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')
                success_message = success_message + "<br>" + "The paper for PMID= " + pmid + " has been added into LOCUSALLELE_REFERENCE table. "
                
            # return HTTPBadRequest(body=json.dumps({'error': "reference_ids="+str(reference_ids)}), content_type='text/json')
  
        else:
            return HTTPBadRequest(body=json.dumps({'error': "The affected gene name " + affected_gene + " doesn't match allele_name " + allele_name + "."}), content_type='text/json')

        
        ## allele type & reference(s)
        
        allele_type_pmids = request.params.get('allele_type_pmids')
        (reference_ids, err_message) = check_pmids(allele_type_pmids, pmid_to_reference_id)

        # return HTTPBadRequest(body=json.dumps({'error': "allele_type reference_ids="+str(reference_ids)}), content_type='text/json')   
    
        if err_message != '':
            return HTTPBadRequest(body=json.dumps({'error': err_message}), content_type='text/json')

        for (reference_id, pmid) in reference_ids:
            if reference_id not in all_reference_id:
                all_reference_id.append(reference_id)
            returnValue = insert_allele_reference(curator_session, CREATED_BY, source_id,
                                                  allele_id, reference_id, "so_term")
            if returnValue != 1:
                return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')
            success_message = success_message + "<br>" + "The paper for PMID= " + pmid + " has been added into ALLELE_REFERENCE table for 'so_term'. "
            
        ## references for description
        if desc:
            desc_pmids = request.params.get('description_pmids')

            (reference_ids, err_message) = check_pmids(desc_pmids, pmid_to_reference_id)

            # return HTTPBadRequest(body=json.dumps({'error': "description reference_ids="+str(reference_ids)}), content_type='text/json')
                
            if err_message != '':
                return HTTPBadRequest(body=json.dumps({'error': err_message}), content_type='text/json')

            for (reference_id, pmid) in reference_ids:
                if reference_id not in all_reference_id:
                    all_reference_id.append(reference_id)
                returnValue = insert_allele_reference(curator_session, CREATED_BY, source_id,
                                                      allele_id, reference_id, "allele_description")
                if returnValue != 1:
                    return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')
                success_message = success_message + "<br>" + "The paper for PMID= " + pmid + " has been added into ALLELE_REFERENCE table for 'allele_description'. "
    
        ## aliases & reference(s)
        
        alias_list = request.params.get('aliases', '')
        alias_pmid_list = request.params.get('alias_pmids', '')

        aliases = alias_list.strip().split('|')
        alias_pmids = alias_pmid_list.strip().split('|')
                    
        if len(aliases) != len(alias_pmids):
            return HTTPBadRequest(body=json.dumps({'error': "Provide same number of PMID sets for alias(es)"}), content_type='text/json')
        
        i = 0
        for alias_name in aliases:
            alias_name = alias_name.strip()
            if alias_name == '':
                i = i + 1
                continue       
            (reference_ids, err_message) = check_pmids(alias_pmids[i], pmid_to_reference_id)
            if err_message != '':
                return HTTPBadRequest(body=json.dumps({'error': err_message}), content_type='text/json')
            returnValue = insert_allele_alias(curator_session, CREATED_BY, source_id,
                                              allele_id, alias_name)
            i = i + 1
            allele_alias_id = None
            if str(returnValue).isdigit():
                allele_alias_id = returnValue
                success_message = success_message + "<br>" + "The new alias " + alias_name + " has been added into ALLELE_ALIAS table. "
            else:
                return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')


            
            # return HTTPBadRequest(body=json.dumps({'error': "allele_alias_id="+str(allele_alias_id) + ", reference_ids="+str(reference_ids)}), content_type='text/json')

        
    
            for (reference_id, pmid) in reference_ids:
                if reference_id not in all_reference_id:
                    all_reference_id.append(reference_id)
                returnValue = insert_allelealias_reference(curator_session, CREATED_BY, source_id,
                                                           allele_alias_id, reference_id)
                if returnValue != 1:
                    return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')
                success_message = success_message + "<br>" + "The paper for PMID= " + pmid + " has been added into ALLELEALIAS_REFERENCE table for alias " + alias_name + ". "

        taxonomy = DBSession.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
        taxonomy_id = taxonomy.taxonomy_id
        
        ## add all papers to Literatureannotation table
        for reference_id in all_reference_id:
            returnValue = insert_literatureannotation(curator_session, CREATED_BY, source_id, allele_id, reference_id, 'Additional Literature', taxonomy_id)
            if returnValue != 1:
                return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')
        if len(all_reference_id) > 0:
            success_message = success_message + "<br>" + "All paper(s) have been added into LITERATUREANNOTATION table. "
            
        preview_url = PREVIEW_URL + 'allele/' + allele_name.replace(' ', '_')
        update_url = "/#/curate/allele/" + allele_name.replace(' ', '_')
        
        success_message = "<a href=" + preview_url + " target='new'>Preview this Allele page</a><br><a href=" + update_url + " target='new'>Update this Allele</a><br>" + success_message
        
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'allele': "ALLELE"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()

def check_old_new_references(old_ref_ids, new_references):

    ref_ids = []
    ref_ids_to_insert = []
    ref_ids_to_delete = []
    for (reference_id, pmid) in new_references:
        ref_ids.append(reference_id)
        if reference_id in old_ref_ids:
            continue
        ref_ids_to_insert.append((reference_id, pmid))

    for reference_id in old_ref_ids:
        if reference_id in ref_ids:
            continue
        ref_ids_to_delete.append(reference_id)

    return (ref_ids_to_insert, ref_ids_to_delete)

def insert_delete_allelealias_reference_rows(curator_session, CREATED_BY, ref_ids_to_insert, ref_ids_to_delete, source_id, allele_alias_id, all_reference_id):

    success_message = ""
    ## insert
    for (reference_id, pmid) in ref_ids_to_insert:
        if reference_id not in all_reference_id:
            all_reference_id.append(reference_id)
        returnValue = insert_allelealias_reference(curator_session, CREATED_BY, source_id,
                                                   allele_alias_id, reference_id)
        if returnValue != 1:
            return ('', returnValue)
        success_message = success_message + "<br>" + "The paper for PMID= " + pmid + " has been added into ALLELEALIAS_REFERENCE table. "

    ## delete
    for reference_id in ref_ids_to_delete:
        aar = curator_session.query(AllelealiasReference).filter_by(allele_alias_id=allele_alias_id, reference_id=reference_id).one_or_none()
        if aar is not None:
            curator_session.delete(aar)
            success_message = success_message + "<br>" + "The paper for reference_id=" + str(reference_id) + " has been deleted from ALLELEALIAS_REFERENCE table. "

    return (success_message, '')


def insert_delete_locusallele_reference_rows(curator_session, CREATED_BY, ref_ids_to_insert, ref_ids_to_delete, source_id, locus_allele_id, all_reference_id):

    success_message = ""
    ## insert
    for (reference_id, pmid) in ref_ids_to_insert:
        if reference_id not in all_reference_id:
            all_reference_id.append(reference_id)
        returnValue = insert_locusallele_reference(curator_session, CREATED_BY, source_id,
                                                   locus_allele_id, reference_id)
        if returnValue != 1:
            return ('', returnValue)
        success_message = success_message + "<br>" + "The paper for PMID= " + pmid + " has been added into LOCUSALLELE_REFERENCE table. "

    ## delete
    for reference_id in ref_ids_to_delete:
        lar = curator_session.query(LocusalleleReference).filter_by(locus_allele_id=locus_allele_id, reference_id=reference_id).one_or_none()
        if lar is not None:
            curator_session.delete(lar)
            success_message = success_message + "<br>" + "The paper for reference_id=" + str(reference_id) + " has been deleted from LOCUSALLELE_REFERENCE table. "

    return (success_message, '')
                                        
def insert_delete_allele_reference_rows(curator_session, CREATED_BY, ref_ids_to_insert, ref_ids_to_delete, source_id, allele_id, reference_class, all_reference_id):

    success_message = ""
    ## insert
    for (reference_id, pmid) in ref_ids_to_insert:
        if reference_id not in all_reference_id:
            all_reference_id.append(reference_id)
        returnValue = insert_allele_reference(curator_session, CREATED_BY, source_id,
                                              allele_id, reference_id, reference_class)
        if returnValue != 1:
            return ('', returnValue)
        success_message = success_message + "<br>" + "The paper for PMID= " + pmid + " has been added into ALLELE_REFERENCE table for reference_class='" + str(reference_class) + "'. "

    ## delete
    for reference_id in ref_ids_to_delete:
        ar = curator_session.query(AlleleReference).filter_by(allele_id=allele_id, reference_id=reference_id, reference_class=reference_class).one_or_none()
        if ar is not None:
            curator_session.delete(ar)
            success_message = success_message + "<br>" + "The paper for reference_id=" + str(reference_id) + " has been deleted from ALLELE_REFERENCE table for 'allele_name'. "

    return (success_message, '')


def update_allele_data(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        sgd = DBSession.query(Source).filter_by(display_name='SGD').one_or_none()
        source_id = sgd.source_id

        ## allele name & references

        sgdid = request.params.get('sgdid')
        if sgdid == '':
            return HTTPBadRequest(body=json.dumps({'error': "No SGDID is passed in."}), content_type='text/json')
    
        d = curator_session.query(Dbentity).filter_by(subclass='ALLELE', sgdid=sgdid).one_or_none()

        if d is None:
            return HTTPBadRequest(body=json.dumps({'error': "The SGDID " + sgdid + " is not in the database."}), content_type='text/json')

        allele_id = d.dbentity_id

        ## update allele_name
        
        allele_name = request.params.get('allele_name')
        if allele_name == '':
            return HTTPBadRequest(body=json.dumps({'error': "Allele name field is blank"}), content_type='text/json')

        success_message = ""
        if allele_name != d.display_name:
            success_message = "The allele name has been updated from '" + d.display_name + "' to '" + allele_name + "'."
            d.display_name = allele_name
            d.format_name = allele_name.replace(' ', '_').replace('/', '_')
            curator_session.add(d)

        ## update so_id
        
        a = curator_session.query(Alleledbentity).filter_by(dbentity_id=allele_id).one_or_none()
        old_so_id = a.so_id
        old_desc = a.description
        
        so_id = request.params.get('so_id')
        if so_id and str(so_id).isdigit():
            so_id = int(so_id)
        else:
            return HTTPBadRequest(body=json.dumps({'error': "Allele type field is blank"}), content_type='text/json')

        allele_update = 0
        if so_id != old_so_id:
            success_message = "The so_id has been updated from " + str(old_so_id) + " to " + str(so_id) + "."
            a.so_id = so_id
            allele_update = 1
            
        ## update description
        desc = request.params.get('description')
        if desc != old_desc:
            success_message = "The description has been updated from '" + str(old_desc) + "' to '" + str(desc) + "'."
            a.description = desc
            allele_update = 1
            
        if allele_update > 0:
            curator_session.add(a)
 
        ## get all allele_reference rows
        
        old_allele_name_ref_ids = []
        old_allele_type_ref_ids = []
        old_desc_ref_ids = []
        old_other_ref_ids = []
        
        all_allele_refs = curator_session.query(AlleleReference).filter_by(allele_id=allele_id).all()
        for ar in all_allele_refs:
            if ar.reference_class == 'allele_name':
                old_allele_name_ref_ids.append(ar.reference_id)
            elif ar.reference_class == 'allele_description':
                old_desc_ref_ids.append(ar.reference_id)
            elif ar.reference_class == 'so_term':
                old_allele_type_ref_ids.append(ar.reference_id)
            else:
                old_other_ref_ids.append(ar.reference_id)

        ##############################
        pmid_to_reference_id = {}
        ##############################
        
        ## update papers for allele name
        
        allele_name_pmids = request.params.get('allele_name_pmids')
        (reference_ids, err_message) = check_pmids(allele_name_pmids, pmid_to_reference_id)    
        if err_message != '':
            return HTTPBadRequest(body=json.dumps({'error': err_message}), content_type='text/json')

        (ref_ids_to_insert, ref_ids_to_delete) = check_old_new_references(old_allele_name_ref_ids, reference_ids)

        
        all_reference_id = []

        
        reference_class = 'allele_name'
        (message, error) = insert_delete_allele_reference_rows(curator_session, CREATED_BY,
                                                               ref_ids_to_insert, ref_ids_to_delete,
                                                               source_id, allele_id, reference_class,
                                                               all_reference_id )
        if error != '':
            return HTTPBadRequest(body=json.dumps({'error': error}), content_type='text/json')
        if message != '':
            success_message = success_message + message
    
        ## update papers for allele_type (so term)
        
        allele_type_pmids = request.params.get('allele_type_pmids')
        (reference_ids, err_message) = check_pmids(allele_type_pmids, pmid_to_reference_id)
        if err_message != '':
            return HTTPBadRequest(body=json.dumps({'error': err_message}), content_type='text/json')
        (ref_ids_to_insert, ref_ids_to_delete) = check_old_new_references(old_allele_type_ref_ids, reference_ids)

        reference_class = 'so_term'
        (message, error) = insert_delete_allele_reference_rows(curator_session, CREATED_BY,
                                                               ref_ids_to_insert,
                                                               ref_ids_to_delete,
                                                               source_id, allele_id,
                                                               reference_class,
                                                               all_reference_id)
        if error != '':
            return HTTPBadRequest(body=json.dumps({'error': error}), content_type='text/json')
        if message != '':
            success_message = success_message + message
            
        ## update papers for description

        desc_pmids = request.params.get('description_pmids')
        (reference_ids, err_message) = check_pmids(desc_pmids, pmid_to_reference_id)
        if err_message != '':
            return HTTPBadRequest(body=json.dumps({'error': err_message}), content_type='text/json')
        (ref_ids_to_insert, ref_ids_to_delete) = check_old_new_references(old_desc_ref_ids, reference_ids)

        reference_class = 'allele_description'
        (message, error) = insert_delete_allele_reference_rows(curator_session,
                                                               CREATED_BY,
                                                               ref_ids_to_insert,
                                                               ref_ids_to_delete,
                                                               source_id, allele_id,
                                                               reference_class,
                                                               all_reference_id)
        if error != '':
            return HTTPBadRequest(body=json.dumps({'error': error}), content_type='text/json')
        if message != '':
            success_message = success_message + message
                      
        ## update papers for affected gene

        affected_gene = request.params.get('affected_gene')
        affected_gene = affected_gene.replace("SGD:", '')
        locus = DBSession.query(Locusdbentity).filter(or_(Locusdbentity.systematic_name.ilike(affected_gene), Locusdbentity.sgdid.ilike(affected_gene))).one_or_none()
        if locus is None:
            return HTTPBadRequest(body=json.dumps({'error': "The affected gene " + affected_gene + " is not in the database. Please enter an ORF name or a SGDID."}), content_type='text/json')

        affected_gene = locus.display_name

        if allele_name.upper().startswith(affected_gene.upper()):
            la = curator_session.query(LocusAllele).filter_by(allele_id=allele_id).one_or_none()
            locus_allele_id = None
            if la is None:
                locus_id = locus.dbentity_id
                returnValue = insert_locus_allele(curator_session, CREATED_BY, source_id, allele_id, locus_id)
                if str(returnValue).isdigit():
                    locus_allele_id = returnValue
                    success_message = success_message + "<br>" + "The affected gene '" + affected_gene + "' has been added into LOCUS_ALLELE table. "
                else:
                    return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')
            else:
                locus_allele_id = la.locus_allele_id
                
            affected_gene_pmids = request.params.get('affected_gene_pmids')
            (reference_ids, err_message) = check_pmids(affected_gene_pmids, pmid_to_reference_id)
            if err_message != '':
                return HTTPBadRequest(body=json.dumps({'error': err_message}), content_type='text/json')

            old_ref_ids = []
            for x in DBSession.query(LocusalleleReference).filter_by(locus_allele_id=locus_allele_id).all():
                old_ref_ids.append(x.reference_id)
            
            (ref_ids_to_insert, ref_ids_to_delete) = check_old_new_references(old_ref_ids, reference_ids)

            (message, error) = insert_delete_locusallele_reference_rows(curator_session, CREATED_BY,
                                                                        ref_ids_to_insert,
                                                                        ref_ids_to_delete,
                                                                        source_id,
                                                                        locus_allele_id,
                                                                        all_reference_id)
            if error != '':
                return HTTPBadRequest(body=json.dumps({'error': error}), content_type='text/json')
            if message != '':
                success_message = success_message + message
        else:
            return HTTPBadRequest(body=json.dumps({'error': "The affected gene name " + affected_gene + " doesn't match allele_name " + allele_name + "."}), content_type='text/json')

               
        ## update aliases & references
        
        old_alias_to_allele_alias_ref = {}
        for x in DBSession.query(AlleleAlias).filter_by(allele_id=allele_id).all():
            ref_ids = []
            all_aar = DBSession.query(AllelealiasReference).filter_by(allele_alias_id=x.allele_alias_id).all()
            for aar in all_aar:
                ref_ids.append(aar.reference_id)
            old_alias_to_allele_alias_ref[x.display_name.upper()] = (x.allele_alias_id, ref_ids)
            
        alias_list = request.params.get('aliases', '')
        alias_pmid_list = request.params.get('alias_pmids', '')

        aliases = alias_list.strip().split('|')
        alias_pmids = alias_pmid_list.strip().split('|')

        if len(aliases) != len(alias_pmids):
            return HTTPBadRequest(body=json.dumps({'error': "Provide same number of PMID sets for alias(es)"}), content_type='text/json')

        i = 0
        new_aliases = []
        for alias_name in aliases:
            alias_name = alias_name.strip()
            if alias_name == '':
                i = i + 1
                continue
            new_aliases.append(alias_name.upper())
            
            (reference_ids, err_message) = check_pmids(alias_pmids[i], pmid_to_reference_id)
            if err_message != '':
                return HTTPBadRequest(body=json.dumps({'error': err_message}), content_type='text/json')
            
            i = i + 1
            
            if alias_name.upper() in old_alias_to_allele_alias_ref:
                ## update references for given alias
                (this_allele_alias_id, old_ref_ids) = old_alias_to_allele_alias_ref[alias_name.upper()]
                (ref_ids_to_insert, ref_ids_to_delete) = check_old_new_references(old_ref_ids, reference_ids)
                (message, error) = insert_delete_allelealias_reference_rows(curator_session,
                                                                            CREATED_BY,
                                                                            ref_ids_to_insert,
                                                                            ref_ids_to_delete,
                                                                            source_id,
                                                                            this_allele_alias_id,
                                                                            all_reference_id)
                if error != '':
                    return HTTPBadRequest(body=json.dumps({'error': error}), content_type='text/json')
                if message != '':
                    success_message = success_message + message
            else:
                returnValue = insert_allele_alias(curator_session, CREATED_BY, source_id,
                                                  allele_id, alias_name)
                allele_alias_id = None
                if str(returnValue).isdigit():
                    allele_alias_id = returnValue
                    success_message = success_message + "<br>" + "The new alias " + alias_name + " has been added into ALLELE_ALIAS table. "
                else:
                    return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')


                for (reference_id, pmid) in reference_ids:
                    returnValue = insert_allelealias_reference(curator_session, CREATED_BY, source_id,
                                                               allele_alias_id, reference_id)
                    if returnValue != 1:
                        return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')
                    success_message = success_message + "<br>" + "The paper for PMID= " + pmid + " has been added into ALLELEALIAS_REFERENCE table for alias " + alias_name + ". "

        for alias_name in old_alias_to_allele_alias_ref:
            if alias_name in new_aliases:
                continue
            (allele_alias_id, ref_ids) = old_alias_to_allele_alias_ref[alias_name]
            all_aar = curator_session.query(AllelealiasReference).filter_by(allele_alias_id=allele_alias_id).all()
            for aar in all_aar:
                curator_session.delete(aar)
            aa = curator_session.query(AlleleAlias).filter_by(allele_alias_id=allele_alias_id).one_or_none()
            curator_session.delete(aa)
            success_message = success_message + "<br>" + "The alias " + alias_name + " has been deleted from ALLELE_ALIAS table. "

        taxonomy = DBSession.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
        taxonomy_id = taxonomy.taxonomy_id

        ## add all papers to Literatureannotation table                                                                   
        for reference_id in all_reference_id:
            returnValue = insert_literatureannotation(curator_session, CREATED_BY, source_id, allele_id, reference_id, 'Additional Literature', taxonomy_id)
            if returnValue != 1:
                return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')
        if len(all_reference_id) > 0:
            success_message = success_message + "<br>" + "All paper(s) have been added into LITERATUREANNOTATION table. "


            
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'allele': "ALLELE"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()

            
def delete_allele_data(request):

    try:
        curator_session = get_curator_session(request.session['username'])

        sgdid = request.params.get('sgdid')
        if sgdid == '':
            return HTTPBadRequest(body=json.dumps({'error': "No SGDID is passed in."}), content_type='text/json')

        d = curator_session.query(Dbentity).filter_by(subclass='ALLELE', sgdid=sgdid).one_or_none()

        if d is None:
            return HTTPBadRequest(body=json.dumps({'error': "The SGDID " + sgdid + " is not in the database."}), content_type='text/jseon')
        
        allele_id = d.dbentity_id

        success_message = ''
        
        ## delete any locusallele_reference & locus_allele
        
        la = curator_session.query(LocusAllele).filter_by(allele_id=allele_id).one_or_none()
        if la is not None:
            all_lar = curator_session.query(LocusalleleReference).filter_by(locus_allele_id=la.locus_allele_id).all()
            for lar in all_lar:
                curator_session.delete(lar)
            curator_session.delete(la)
            success_message = "The locus_allele row has been deleted. "
    
        ## delete allelealias_reference & allele_alias

        all_aa = curator_session.query(AlleleAlias).filter_by(allele_id=allele_id).all()
        deleted = 0
        for aa in all_aa:
            all_aar = curator_session.query(AllelealiasReference).filter_by(allele_alias_id=aa.allele_alias_id).all()
            for aar in all_aar:
                curator_session.delete(aar)
            curator_session.delete(aa)
            deleted = 1
        if deleted == 1:
            success_message = success_message + "<br>" + "The locus_alias row(s) have been deleted. "
            
        ## delete allele_reference
        
        all_ar = curator_session.query(AlleleReference).filter_by(allele_id=allele_id).all()
        deleted = 0
        for ar in all_ar:
            curator_session.delete(ar)
            deleted = 1
        if deleted == 1:
            success_message = success_message + "<br>" + "The allele_reference row(s) have been deleted. "
            
        ## delete literatureannotation
        
        all_la = curator_session.query(Literatureannotation).filter_by(dbentity_id=allele_id).all()
        deleted = 0
        for la in all_la:
            curator_session.delete(la)
            deleted = 1
        if deleted == 1:
            success_message = success_message + "<br>" + "The literatureannotation row(s) have been deleted. "
    
        ## update phenotypeannotation and set allele_id to null

        all_pa = curator_session.query(Phenotypeannotation).filter_by(allele_id=allele_id).all()
        updated = 0
        for pa in all_pa:
            pa.allele_id = None
            curator_session.add(pa)
            updated = 1
        if updated == 1:
            success_message = success_message + "<br>" + "The allele_id for phenotypeannotation row(s) have been set to null. "
    
        ## delete allele_geninteraction

        all_ai = curator_session.query(AlleleGeninteraction).filter(or_(AlleleGeninteraction.allele1_id==allele_id, AlleleGeninteraction.allele2_id==allele_id)).all()

        deleted = 0
        for ai in all_ai:
            curator_session.delete(ai)
            deleted = 1
        if deleted == 1:
            success_message = success_message + "<br>" + "The allele_geninteraction row(s) have been deleted. "
        
        ## delete alleledbentity & dbentity 

        curator_session.query(Alleledbentity).filter_by(dbentity_id=allele_id).delete()
        curator_session.query(Dbentity).filter_by(dbentity_id=allele_id).delete()
        
        success_message = success_message + "<br>" + "The alleledbentity/dbentity rows have been deleted."
        
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'allele': "ALLELE"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()

            


    
    
