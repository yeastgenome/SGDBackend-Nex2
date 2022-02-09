from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPOk, HTTPNotFound, HTTPFound
from sqlalchemy import create_engine, and_, or_, DateTime
from sqlalchemy.exc import IntegrityError, DataError, InternalError
from sqlalchemy.orm import scoped_session, sessionmaker, joinedload
from datetime import datetime
import transaction
import json
import pandas as pd
from .models_helpers import ModelsHelper
import logging


from src.models import DBSession, Diseaseannotation, Disease, Diseasesupportingevidence, Source, Dbentity, Locusdbentity, Referencedbentity,\
     Straindbentity, Ro, Eco
from src.curation_helpers import get_curator_session

GROUP_ID = 1
OBJ_URL = 'http://www.alliancegenome.org/gene/'
EVIDENCE_TYPE = 'with'
RO_ID = '1968075'

models_helper = ModelsHelper()

def insert_update_disease_annotations(request):
    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        source_id = 834
        annotation_id = request.params.get('annotation_id')
        dbentity_id = request.params.get('dbentity_id')
        if not dbentity_id:
            return HTTPBadRequest(body=json.dumps({'error': "gene is blank"}), content_type='text/json')

        taxonomy_id = request.params.get('taxonomy_id')
        if not taxonomy_id:
            return HTTPBadRequest(body=json.dumps({'error': "taxonomy is blank"}), content_type='text/json')

        reference_id = request.params.get('reference_id')
        if not reference_id:
            return HTTPBadRequest(body=json.dumps({'error': "reference is blank"}), content_type='text/json')

        eco_id = request.params.get('eco_id')
        if not eco_id:
            return HTTPBadRequest(body=json.dumps({'error': "eco is blank"}), content_type='text/json')
        
        disease_id = request.params.get('disease_id')
        if not disease_id:
            return HTTPBadRequest(body=json.dumps({'error': "disease_id is blank"}), content_type='text/json')       

        annotation_type = request.params.get('annotation_type')
        if not annotation_type:
            return HTTPBadRequest(body=json.dumps({'error': "annotation type is blank"}), content_type='text/json')

        with_ortholog = request.params.get('with_ortholog')
        if not with_ortholog:
            return HTTPBadRequest(body=json.dumps({'error': "with_ortholog is blank"}), content_type='text/json')
         
        try:
            dbentity_in_db = None
            dbentity_in_db = DBSession.query(Dbentity).filter(or_(Dbentity.sgdid == dbentity_id, Dbentity.format_name == dbentity_id)).filter(Dbentity.subclass == 'LOCUS').one_or_none()
            if dbentity_in_db is not None:
                dbentity_id = dbentity_in_db.dbentity_id
            else:
                return HTTPBadRequest(body=json.dumps({'error': "gene value not found in database"}), content_type='text/json')
        except Exception as e:
            print(e)
        
        dbentity_in_db = None
        pmid_in_db = None
        dbentity_in_db = DBSession.query(Dbentity).filter(and_(Dbentity.sgdid == reference_id,Dbentity.subclass == 'REFERENCE')).one_or_none()
        if dbentity_in_db is None:
            try:
                dbentity_in_db = DBSession.query(Dbentity).filter(and_(Dbentity.dbentity_id == int(reference_id), Dbentity.subclass == 'REFERENCE')).one_or_none()
            except ValueError as e:
                pass
        if dbentity_in_db is None:
            try:
                pmid_in_db = DBSession.query(Referencedbentity).filter(Referencedbentity.pmid == int(reference_id)).one_or_none()
            except ValueError as e:
                pass

        if dbentity_in_db is not None:
            reference_id = dbentity_in_db.dbentity_id
        elif (pmid_in_db is not None):
            reference_id = pmid_in_db.dbentity_id
        else:
            return HTTPBadRequest(body=json.dumps({'error': "reference value not found in database"}), content_type='text/json')
        
        isSuccess = False
        returnValue = ''
        disease_in_db = []

        if (int(annotation_id) > 0):
            
            try:
                update_disease = {'dbentity_id': dbentity_id,
                                    'source_id': source_id,
                                    'taxonomy_id': taxonomy_id,
                                    'reference_id': reference_id,
                                    'eco_id': eco_id,
                                    'association_type': int(RO_ID),
                                    'annotation_type': annotation_type,
                                    'disease_id': disease_id
                                    }
                update_dse = {'dbxref_id': with_ortholog,
                               'obj_url': OBJ_URL + with_ortholog}
                curator_session.query(Diseaseannotation).filter(Diseaseannotation.annotation_id == annotation_id).update(update_disease)
                curator_session.query(Diseasesupportingevidence).filter(Diseasesupportingevidence.annotation_id == annotation_id).update(update_dse)
                curator_session.flush()
                transaction.commit()
               
                isSuccess = True
                returnValue = 'Record updated successfully.'
                
                disease = curator_session.query(Diseaseannotation).filter(Diseaseannotation.annotation_id == annotation_id).one_or_none()
                dse = curator_session.query(Diseasesupportingevidence).filter(Diseasesupportingevidence.annotation_id == annotation_id).one_or_none()

                disease_in_db = {
                    'id': disease.annotation_id,
                    'dbentity_id': {
                        'id': disease.dbentity.format_name,
                        'display_name': disease.dbentity.display_name
                    },
                    'taxonomy_id': '',
                    'reference_id': disease.reference.pmid,
                    'eco_id': disease.eco_id,
                    'association_type': disease.association_type,
                    'source_id': disease.source_id,
                    'with_ortholog': dse.dbxref_id,
                    'annotation_type': disease.annotation_type,
                }
                if disease.eco:
                    disease_in_db['eco_id'] = str(disease.eco.eco_id)

                if disease.taxonomy:
                    disease_in_db['taxonomy_id'] = disease.taxonomy.taxonomy_id


            except IntegrityError as e:
                transaction.abort()
                if curator_session:
                    curator_session.rollback()
                isSuccess = False
                returnValue = 'Integrity Error: Update failed, record already exists' + str(e.orig.pgerror)
            except DataError as e:
                transaction.abort()
                if curator_session:
                    curator_session.rollback()
                isSuccess = False
                returnValue = 'Data Error: ' + str(e.orig.pgerror)
            except InternalError as e:
                transaction.abort()
                if curator_session:
                    curator_session.rollback()
                isSuccess = False
                error = str(e.orig).replace('_', ' ')
                error = error[0:error.index('.')]
                returnValue = 'Updated failed, ' + error
            except Exception as e:
                transaction.abort()
                if curator_session:
                    curator_session.rollback()
                isSuccess = False
                returnValue = 'Updated failed, ' + str(e)
            finally:
                if curator_session:
                    curator_session.close()

        if(int(annotation_id) == 0):
            try:
                y = None
                date_created = datetime.now()
                y = Diseaseannotation(dbentity_id = dbentity_id,
                                    source_id = source_id,
                                    taxonomy_id = taxonomy_id,
                                    reference_id = reference_id,
                                    eco_id = eco_id,
                                    disease_id = disease_id,
                                    association_type = int(RO_ID),
                                    annotation_type = annotation_type,
                                    created_by = CREATED_BY,
                                    date_assigned = date_created)
                curator_session.add(y)
                curator_session.flush()
                dse = Diseasesupportingevidence(
                                annotation_id=y.annotation_id,
                                group_id = GROUP_ID,
                                dbxref_id=with_ortholog,
                                obj_url=OBJ_URL+with_ortholog,
                                evidence_type = 'with',
                                created_by=CREATED_BY)
                curator_session.add(dse)
                update_ldb = {'has_disease': True}
                curator_session.query(Locusdbentity).filter(Locusdbentity.dbentity_id == dbentity_id).update(update_ldb)
                transaction.commit()
                isSuccess = True
                returnValue = 'Record added successfully.'
            except IntegrityError as e:
                transaction.abort()
                if curator_session:
                    curator_session.rollback()
                isSuccess = False
                returnValue = 'Integrity Error: ' + str(e.orig.pgerror)
            except DataError as e:
                transaction.abort()
                if curator_session:
                    curator_session.rollback()
                isSuccess = False
                returnValue = 'Data Error: ' + str(e.orig.pgerror)
            except Exception as e:
                transaction.abort()
                if curator_session:
                    curator_session.rollback()
                isSuccess = False
                returnValue = 'Insert failed ' +str(e)
            finally:
                if curator_session:
                    curator_session.close()

        if isSuccess:
            return HTTPOk(body=json.dumps({'success': returnValue,'disease':disease_in_db}), content_type='text/json')

        return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')

    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')

def get_diseases_by_filters(request):
    try:
        dbentity_id = str(request.params.get('dbentity_id')).strip()
        reference_id = str(request.params.get('reference_id')).strip()

        if not(dbentity_id or reference_id):
            raise Exception("Please provide input for gene, reference or combination to get the disease.")

        diseases_in_db = DBSession.query(Diseaseannotation)
        
        gene_dbentity_id,reference_dbentity_id = None,None

        if dbentity_id:
            gene_dbentity_id = DBSession.query(Dbentity).filter(or_(Dbentity.sgdid==dbentity_id, Dbentity.format_name==dbentity_id)).one_or_none()

            if not gene_dbentity_id:
                raise Exception('gene not found, please provide sgdid or systematic name')
            else:
                gene_dbentity_id = gene_dbentity_id.dbentity_id
                diseases_in_db = diseases_in_db.filter_by(dbentity_id=gene_dbentity_id)

        if reference_id:
            if reference_id.startswith('S00'):
                reference_dbentity_id = DBSession.query(Dbentity).filter(Dbentity.sgdid == reference_id).one_or_none()
            else:
                reference_dbentity_id = DBSession.query(Referencedbentity).filter(or_(Referencedbentity.pmid == int(reference_id),Referencedbentity.dbentity_id == int(reference_id))).one_or_none()
            
            if not reference_dbentity_id:
                raise Exception('Reference not found, please provide sgdid , pubmed id or reference number')
            else:
                reference_dbentity_id = reference_dbentity_id.dbentity_id
                diseases_in_db = diseases_in_db.filter_by(reference_id=reference_dbentity_id)
      
        diseases = diseases_in_db.options(joinedload(Diseaseannotation.eco), joinedload(Diseaseannotation.disease), joinedload(Diseaseannotation.taxonomy)
                                                , joinedload(Diseaseannotation.reference), joinedload(Diseaseannotation.dbentity)).order_by(Diseaseannotation.annotation_id.asc()).all()

        list_of_diseases = []
        for disease in diseases:
            dse = DBSession.query(Diseasesupportingevidence).filter(Diseasesupportingevidence.annotation_id == disease.annotation_id).one_or_none()
            dbxref_id = ''
            if dse:
                dbxref_id = dse.dbxref_id
            currentDisease = {
                'annotation_id': disease.annotation_id,
                'dbentity_id': {
                    'id': disease.dbentity.format_name,
                    'display_name': disease.dbentity.display_name
                },
                'taxonomy_id': '',
                'reference_id': disease.reference.pmid,
                'eco_id': '',
                'association_type': disease.association_type,
                'annotation_type': disease.annotation_type,
                'disease_id': disease.disease_id,
                'with_ortholog': dbxref_id
            }
            if disease.eco:
                currentDisease['eco_id'] = str(disease.eco_id)

            if disease.disease_id:
                currentDisease['disease_id'] = str(disease.disease_id)

            if disease.taxonomy:
                currentDisease['taxonomy_id'] = disease.taxonomy_id

            list_of_diseases.append(currentDisease)
        
        return HTTPOk(body=json.dumps({'success': list_of_diseases}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')

def delete_disease_annotation(request):
    try:
        id = request.matchdict['id']
        dbentity_id = request.matchdict['dbentity_id']

        if dbentity_id:
            gene_dbentity_id = DBSession.query(Dbentity).filter(or_(Dbentity.sgdid==dbentity_id, Dbentity.format_name==dbentity_id)).one_or_none()
            if not gene_dbentity_id:
                raise Exception('gene not found, please provide sgdid or systematic name')
    
        curator_session = get_curator_session(request.session['username'])
        isSuccess = False
        returnValue = ''
        disease_in_db = curator_session.query(Diseaseannotation).filter(Diseaseannotation.annotation_id == id).one_or_none()
        total_diseases_in_db = curator_session.query(Diseaseannotation).filter(Diseaseannotation.dbentity_id == gene_dbentity_id.dbentity_id).count()
        if(disease_in_db):
            try:
                curator_session.delete(disease_in_db)
                if (total_diseases_in_db == 1): #last annotation being deleted
                    update_ldb = {'has_disease': False}
                    curator_session.query(Locusdbentity).filter(Locusdbentity.dbentity_id == gene_dbentity_id.dbentity_id).update(update_ldb)
                transaction.commit()
                isSuccess = True
                returnValue = 'Diseaseannotation successfully deleted.'
            except Exception as e:
                transaction.abort()
                if curator_session:
                    curator_session.rollback()
                isSuccess = False
                returnValue = 'Error occurred deleting diseaseannotation: ' + str(e.message)
            finally:
                if curator_session:
                    curator_session.close()

            if isSuccess:
                return HTTPOk(body=json.dumps({'success': returnValue}), content_type='text/json')

            return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')

        return HTTPBadRequest(body=json.dumps({'error': 'diseaseannot not found in database.'}), content_type='text/json')

    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')


def upload_disease_file(request):

    try:
        file = request.POST['file'].file
        filename = request.POST['file'].filename
        CREATED_BY = request.session['username']
        xl = pd.ExcelFile(file)
        list_of_sheets = xl.sheet_names

        COLUMNS = {
            'taxonomy': 'Taxon',
            'gene': 'Gene',
            'disease_id': 'DOID',
            'with_ortholog':'With Ortholog',
            'eco_id': 'Evidence Code',
            'reference': 'DB:Reference',
            'created_by': 'Assigned By',    
        }

        SOURCE_ID = 834
        SEPARATOR = ','
        ANNOTATION_TYPE = 'high-throughput'

        list_of_diseases = []
        list_of_diseases_errors = []
        df = pd.read_excel(io=file, sheet_name="Sheet1")

        null_columns = df.columns[df.isnull().any()]
        for col in null_columns:
            if COLUMNS['with_ortholog'] != col and COLUMNS['evidence code'] !=col:
                rows = df[df[col].isnull()].index.tolist()
                rows = ','.join([str(r+2) for r in rows])
                list_of_diseases_errors.append('No values in column ' + col + ' rows ' + rows)
        
        if list_of_diseases_errors:
            err = [e + '\n' for e in list_of_diseases_errors]
            return HTTPBadRequest(body=json.dumps({"error": list_of_diseases_errors}), content_type='text/json')


        sgd_id_to_dbentity_id, systematic_name_to_dbentity_id = models_helper.get_dbentity_by_subclass(['LOCUS', 'REFERENCE'])
        strain_to_taxonomy_id = models_helper.get_common_strains()
        eco_displayname_to_id = models_helper.get_all_eco_mapping()
        doid_to_disease_id = models_helper.get_all_do_mapping()
        pubmed_id_to_reference, reference_to_dbentity_id = models_helper.get_references_all()

        for index_row,row in df.iterrows():
            index  = index_row + 2;
            column = ''
            try:
                disease_existing = {
                    'dbentity_id': '',
                    'source_id':SOURCE_ID,
                    'taxonomy_id': '',
                    'reference_id': '',
                    'eco': '',
                    'with_ortholog': None,
                    'disease_id': '',
                    'created_by': '',
                    'annotation_type': ANNOTATION_TYPE
                }
                disease_update = {
                    'annotation_type': ANNOTATION_TYPE
                }

                column = COLUMNS['gene']
                gene = row[column]
                gene_current = str(gene.strip())
                
                key = (gene_current,'LOCUS')
                if key in sgd_id_to_dbentity_id:
                    disease_existing['dbentity_id'] = sgd_id_to_dbentity_id[key]
                elif(key in systematic_name_to_dbentity_id):
                    disease_existing['dbentity_id'] = systematic_name_to_dbentity_id[key]
                else:
                    list_of_diseases_errors.append('Error in gene on row ' + str(index)+ ', column ' + column)
                    continue
                                       
                
                column = COLUMNS['reference']
                reference = row[column]
                reference_current = str(reference)
                key = (reference_current,'REFERENCE')
                if(key in sgd_id_to_dbentity_id):
                    disease_existing['reference_id'] = sgd_id_to_dbentity_id[key]
                elif(reference_current in pubmed_id_to_reference):
                    disease_existing['reference_id'] = pubmed_id_to_reference[reference_current]
                elif(reference_current in reference_to_dbentity_id):
                    disease_existing['reference_id'] = int(reference_current)
                else:
                    list_of_diseases_errors.append('Error in reference on row ' + str(index) + ', column ' + column)
                    continue
                 
                column = COLUMNS['taxonomy']
                taxonomy = row[column]
                taxonomy_current = str(taxonomy)
                if taxonomy_current in strain_to_taxonomy_id:
                    disease_existing['taxonomy_id'] = strain_to_taxonomy_id[taxonomy_current]
                else:
                    list_of_diseases_errors.append('Error in taxonomy on row ' + str(index) + ', column ' + column)
                    continue
                    
                column = COLUMNS['eco_id']
                eco = row[column]
                eco_current = str(eco)        

                column = COLUMNS['disease_id']
                disease_id = row[column]
                disease_id_current = str(disease_id).strip()
                if disease_id_current in doid_to_disease_id:
                    disease_existing['disease_id'] = doid_to_disease_id[disease_id_current]
                else:
                    list_of_diseases_errors.append('Error in disease_id on row ' + str(index) + ', column ' + column)
                    continue

                
                column = COLUMNS['with_ortholog']
                with_ortholog = row[column]
                with_ortholog_current = None if pd.isnull(with_ortholog) else None if not str(with_ortholog) else str(with_ortholog)
                disease_existing['with_ortholog'] = with_ortholog_current

                if not pd.isnull(with_ortholog):
                    with_ortholog_new = None if pd.isnull(with_ortholog) else None if not str(with_ortholog) else str(with_ortholog)
                    disease_existing['with_ortholog'] = with_ortholog_new

                list_of_diseases.append([disease_existing,disease_update])
            
            except Exception as e:
                list_of_diseases_errors.append('Error in on row ' + str(index) + ', column ' + column + ' ' + str(e))
        

        if list_of_diseases_errors:
            err = [e + '\n' for e in list_of_diseases_errors]
            logging.debug('Error in list_of_diseases_errors')
            return HTTPBadRequest(body=json.dumps({"error":list_of_diseases_errors}),content_type='text/json')
        
        INSERT = 0
        UPDATE = 0
        curator_session = get_curator_session(request.session['username'])
        isSuccess = False
        returnValue = ''
        
        if list_of_diseases:
            for item in list_of_diseases:
                disease, update_disease = item
                
                if (len(update_disease)>1):
                    disease_in_db = curator_session.query(Diseaseannotation).filter(and_(
                        Diseaseannotation.dbentity_id == disease['dbentity_id'],
                        Diseaseannotation.disease_id == disease['disease_id'],
                        Diseaseannotation.taxonomy_id == disease['taxonomy_id'],
                        Diseaseannotation.reference_id == disease['reference_id'],
                        Diseaseannotation.eco_id == disease['eco_id'],
                        Diseaseannotation.association_type == int(RO_ID),
                        Diseaseannotation.date_assigned == datetime.now(),
                        Diseaseannotation.created_by == disease['created_by']
                        )).one_or_none()
                    if disease_in_db is not None:
                        curator_session.query(Diseaseannotation).filter(and_(
                        Diseaseannotation.dbentity_id == disease['dbentity_id'],
                        Diseaseannotation.disease_id == disease['disease_id'],
                        Diseaseannotation.taxonomy_id == disease['taxonomy_id'],
                        Diseaseannotation.reference_id == disease['reference_id'],
                        Diseaseannotation.eco_id == disease['eco_id'],
                        Diseaseannotation.association_type == int(RO_ID),
                        Diseaseannotation.date_assigned == datetime.now(),
                        Diseaseannotation.created_by == disease['created_by']
                        )).update(update_disease)
                        curator_session.flush()
                        curator_session.query(Diseasesupportingevidence).filter(and_(
                        Diseasesupportingevidence.annotation_id == disease_in_db['annotation_id'],
                        )).update({'dbxref_id': disease['with_ortholog'], 'obj_url': OBJ_URL+disease['with_ortholog']})                      
                        UPDATE  = UPDATE + 1
                else:
                    codes = eco_current.split(';')
                    for code in codes:
                        code = code.strip()
                        if code in eco_displayname_to_id:
                            eco_id = eco_displayname_to_id[code]
                            disease['eco_id'] = eco_id
                            r = Diseaseannotation(
                                dbentity_id = disease['dbentity_id'],
                                disease_id = disease['disease_id'], 
                                source_id = SOURCE_ID,
                                taxonomy_id = disease['taxonomy_id'],
                                reference_id = disease['reference_id'], 
                                eco_id = disease['eco_id'],
                                association_type = int(RO_ID),
                                date_assigned = datetime.now(),
                                created_by = CREATED_BY,
                                annotation_type = disease['annotation_type']
                            )
                            curator_session.add(r)
                            curator_session.flush()
                            annotation_id = r.annotation_id
                            daf_evidence_row = Diseasesupportingevidence(
                                annotation_id=annotation_id,
                                group_id = GROUP_ID,
                                dbxref_id=disease['with_ortholog'],
                                obj_url=OBJ_URL+disease['with_ortholog'],
                                evidence_type = 'with',
                                created_by=CREATED_BY
                            )
                        curator_session.add(daf_evidence_row)
                        update_ldb = {'has_disease': True}
                        curator_session.query(Locusdbentity).filter(Locusdbentity.dbentity_id == disease['dbentity_id']).update(update_ldb)
                        transaction.commit()
                        curator_session.flush()
                        INSERT = INSERT + 1            
            try:
                transaction.commit()
                err = '\n'.join(list_of_diseases_errors)
                isSuccess = True    
                returnValue = 'Inserted:  ' + str(INSERT) + ' <br />Updated: ' + str(UPDATE) + '<br />Errors: ' + err
            except IntegrityError as e:
                transaction.abort()
                if curator_session:
                    curator_session.rollback()
                isSuccess = False
                returnValue = 'Integrity Error: '+str(e.orig.pgerror)
            except DataError as e:
                transaction.abort()
                if curator_session:
                    curator_session.rollback()
                isSuccess = False
                returnValue = 'Data Error: '+str(e.orig.pgerror)
            except Exception as e:
                transaction.abort()
                if curator_session:
                    curator_session.rollback()
                isSuccess = False
                returnValue = str(e)
            finally:
                if curator_session:
                    curator_session.close()
        
        if isSuccess:
            return HTTPOk(body=json.dumps({"success": returnValue}), content_type='text/json')
        
        return HTTPBadRequest(body=json.dumps({'error': returnValue}), content_type='text/json')    

    except Exception as e:
        return HTTPBadRequest(body=json.dumps({"error":str(e)}),content_type='text/json')
