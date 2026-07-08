import logging
import os
from datetime import datetime
from sqlalchemy import or_
from pyramid.httpexceptions import HTTPBadRequest, HTTPOk
from sqlalchemy.exc import IntegrityError, DataError
import transaction
import pandas as pd
import json
import math
import mimetypes
from src.models import DBSession, Dataset, Datasetsample, Datasettrack, Datasetlab, DatasetFile, \
                       DatasetKeyword, DatasetReference, DatasetUrl, Referencedbentity, Source,\
                       Filedbentity, FileKeyword, Colleague, Keyword, Expressionannotation, Obi,\
                       Taxonomy
from src.curation_helpers import get_curator_session
from src.metadata_helpers import insert_file_keyword, insert_dataset_keyword
from src.helpers import check_for_non_ascii_characters

log = logging.getLogger('curation')

DBXREF_URL = 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc='

def insert_dataset_file(curator_session, CREATED_BY, source_id, dataset_id, file_id):

    try:
        x = DatasetFile(dataset_id = dataset_id,
                        file_id = file_id,
                        source_id = source_id,
                        created_by = CREATED_BY)
        curator_session.add(x)
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()

def insert_dataset_url(curator_session, CREATED_BY, source_id, dataset_id, display_name, url):

    try:
        x = DatasetUrl(dataset_id = dataset_id,
                       display_name = display_name,
                       obj_url = url,
                       url_type = display_name,
                       source_id = source_id,
                       created_by = CREATED_BY)
        curator_session.add(x)
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()

def insert_datasetlab(curator_session, CREATED_BY, source_id, dataset_id, lab_name, lab_location, colleague_id):
    
    try:
        x = Datasetlab(dataset_id = dataset_id,
                       lab_name = lab_name,
                       lab_location = lab_location,
                       colleague_id = colleague_id,
                       source_id = source_id,
                       created_by = CREATED_BY)
        curator_session.add(x)
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        
def insert_dataset_reference(curator_session, CREATED_BY, source_id, dataset_id, reference_id):

    try:
        x = DatasetReference(dataset_id = dataset_id,
                             reference_id = reference_id,
                             source_id = source_id,
                             created_by = CREATED_BY)
        curator_session.add(x)
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()


def insert_dataset(curator_session, CREATED_BY, x):

    try:
        x = Dataset(format_name = x['format_name'],
                    display_name = x['display_name'],
                    obj_url = x['obj_url'],
                    source_id = x['source_id'],
                    dbxref_id = x['dbxref_id'],
                    dbxref_type = x['dbxref_type'],
                    date_public = x['date_public'],
                    parent_dataset_id = x['parent_dataset_id'],
                    channel_count = x['channel_count'],
                    sample_count = x['sample_count'],
                    is_in_spell = x['is_in_spell'],
                    is_in_browser = x['is_in_browser'],
                    description = x['description'],
                    created_by = CREATED_BY)
        curator_session.add(x)
        transaction.commit()
        return x.dataset_id
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        # return -1
        return str(e)
    
def get_pmids(dataset_id):
    
    pmids = ''
    all_dsRefs = DBSession.query(DatasetReference).filter_by(dataset_id=dataset_id).all()
    for dsR in all_dsRefs:
        if pmids != '':
            pmids = pmids + '|'
        pmids = pmids + str(dsR.reference.pmid)
    return pmids

def get_keywords(dataset_id):
    
    keywords = ''
    all_kws = DBSession.query(DatasetKeyword).filter_by(dataset_id=dataset_id).all()
    for kw in all_kws:
        if keywords != '':
            keywords = keywords + '|'
        keywords = keywords + kw.keyword.display_name
    return keywords

def get_lab(dataset_id):
                                                                                            
    all_labInfo = DBSession.query(Datasetlab).filter_by(dataset_id=dataset_id).all()
    lab1 = ''
    lab2 = ''
    for labInfo in all_labInfo:
        lab = "lab_name: " + labInfo.lab_name + " | lab_location: " + labInfo.lab_location + " | colleague_format_name: "
        if labInfo.colleague_id:
            lab = lab + labInfo.colleague.format_name
        if lab1 == '':
            lab1 = lab
        else:
            lab2 = lab
    return (lab1, lab2)

def get_list_of_dataset(request):

    try:
        query = str(request.matchdict['query'])
        data = []

        ## search by PMID:
        rows_by_pmid = []
        if query.isdigit():
            pmid = int(query)
            ref = DBSession.query(Referencedbentity).filter_by(pmid=pmid).one_or_none()
            if ref is not None:
                all_dsRefs = DBSession.query(DatasetReference).filter_by(reference_id=ref.dbentity_id).all()
                for x in all_dsRefs:
                    rows_by_pmid.append(x.dataset)

        ## search by GEO/SRA/ArrayExpress ID:
        rows_by_GEO = DBSession.query(Dataset).filter(Dataset.format_name.ilike('%'+query+'%')).all()

        ## search by file name:
        rows_by_filename = []
        all_fileRows = DBSession.query(Filedbentity).filter(or_(Filedbentity.display_name.ilike('%'+query+'%'), Filedbentity.previous_file_name.ilike('%'+query+'%'))).order_by(Filedbentity.display_name).all()
        for x in all_fileRows:
            all_dsFiles = DBSession.query(DatasetFile).filter_by(file_id=x.dbentity_id).all()
            for y in all_dsFiles:
                rows_by_filename.append(y.dataset)
        
        foundDataset = {}    
        for x in rows_by_pmid + rows_by_GEO + rows_by_filename:
            if x.format_name in foundDataset:
                continue
            foundDataset[x.format_name] = 1
            pmids = get_pmids(x.dataset_id)
            keywords = get_keywords(x.dataset_id)
            (lab1, lab2) = get_lab(x.dataset_id)
            data.append({ 'format_name': x.format_name,
                          'display_name': x.display_name,
                          'dbxref_id': x.dbxref_id,
                          'dbxref_type': x.dbxref_type,
                          'date_public': str(x.date_public),
                          'pmids': pmids,
                          'keywords': keywords,
                          'lab': lab1 })
        return HTTPOk(body=json.dumps(data),content_type='text/json')
    except Exception as e:
        log.error(e)
        return HTTPBadRequest(body=json.dumps({'error': str(e)}))
    finally:
        if DBSession:
            DBSession.remove()
            
def get_one_dataset(request):

    try:
        data = {}
        format_name = str(request.matchdict['format_name'])
        x = DBSession.query(Dataset).filter_by(format_name=format_name).one_or_none()
        if x is None:
            return HTTPBadRequest(body=json.dumps({'error': "The dataset format_name " + format_name + " is not in the database."}))
        data['dataset_id'] = x.dataset_id
        data['format_name'] = x.format_name
        data['display_name'] = x.display_name
        data['dbxref_id'] = x.dbxref_id
        data['dbxref_type'] = x.dbxref_type
        data['date_public'] = str(x.date_public).split(' ')[0]
        data['parent_dataset_id'] = x.parent_dataset_id
        data['channel_count'] = x.channel_count
        data['sample_count'] = x.sample_count
        data['is_in_spell'] = x.is_in_spell
        data['is_in_browser'] = x.is_in_browser
        data['description'] = x.description
    
        ## file names
        files = ''
        all_dfs = DBSession.query(DatasetFile).filter_by(dataset_id=x.dataset_id).all() 
        for df in all_dfs:
            if df.file.dbentity_status == 'Active':
                if files != '':
                    files = files + '|'
                files = files + df.file.display_name 
        data['filenames'] = files

        ## pmids, keywords, lab
        data['pmids'] = get_pmids(x.dataset_id)
        data['keywords'] = get_keywords(x.dataset_id)
        (data['lab1'], data['lab2']) = get_lab(x.dataset_id)
        
        ## urls
        # urls = []
        all_dsUrls = DBSession.query(DatasetUrl).filter_by(dataset_id=x.dataset_id).all()
        i = 1
        for dsUrl in all_dsUrls:
            data['url' + str(i)] = dsUrl.display_name + ' | ' + dsUrl.obj_url
            i = i + 1
        # data['urls'] = urls
    
        ## samples
        samples = []
        all_samples = DBSession.query(Datasetsample).filter_by(dataset_id=x.dataset_id).order_by(Datasetsample.sample_order).all()
        for s in all_samples:
            samples.append({ 'datasetsample_id': s.datasetsample_id,
                             'format_name': s.format_name,
                             'display_name': s.display_name,
                             'obj_url': s.obj_url,
                             'taxonomy_id': s.taxonomy_id,
                             'sample_order': s.sample_order,
                             'dbxref_id': s.dbxref_id,
                             'assay_id': s.assay_id,
                             'dbxref_type': s.dbxref_type,
                             'biosample': s.biosample,
                             'strain_name': s.strain_name,
                             'description': s.description,
                             'dbxref_url': s.dbxref_url })
        data['samples'] = samples
 
        ## tracks
        tracks = []
        all_tracks = DBSession.query(Datasettrack).filter_by(dataset_id=x.dataset_id).order_by(Datasettrack.track_order).all()
        for t in all_tracks:
            tracks.append({ 'datasettrack_id': t.datasettrack_id,
                            'format_name': t.format_name,
                            'display_name': t.display_name,
                            'obj_url': t.obj_url,
                            'track_order': t.track_order })
        data['tracks'] = tracks

        return HTTPOk(body=json.dumps(data),content_type='text/json')
    except Exception as e:
        log.error(e)
        return HTTPBadRequest(body=json.dumps({'error': str(e)}))
    finally:
        if DBSession:
            DBSession.remove()
            
def read_dataset_data_from_file(file):

    try:
        
        dataset_to_id = dict([(x.display_name, x.dataset_id) for x in DBSession.query(Dataset).all()])
        format_name_to_id = dict([(x.format_name, x.dataset_id) for x in DBSession.query(Dataset).all()])
        file_to_id = dict([(x.display_name, x.dbentity_id) for x in DBSession.query(Filedbentity).all()])
        source_to_id = dict([(x.display_name, x.source_id) for x in DBSession.query(Source).all()])
        pmid_to_reference_id = dict([(x.pmid, x.dbentity_id) for x in DBSession.query(Referencedbentity).all()])
        keyword_to_id = dict([(x.display_name, x.keyword_id) for x in DBSession.query(Keyword).all()])
        coll_name_institution_to_id = dict([((x.display_name, x.institution), x.colleague_id) for x in DBSession.query(Colleague).all()])
        coll_name_to_id = dict([(x.display_name, x.colleague_id) for x in DBSession.query(Colleague).all()])
    
        error_message = ''
        
        df = pd.read_csv(file, sep='\t')
    
        # old_datasets = []
        found = {}
        data = []        
        for index, row in df.iterrows(): 
                   
            format_name = row.iat[0].strip()
            
            # if index == 0 and format_name.lower().startswith('dataset'):
            #     continue
        
            if format_name in found:
                # error_message = error_message + "<br>" + format_name + " is in the file already.")
                continue
            found[format_name] = 1
            
            if format_name in dataset_to_id:
                # error_message = error_message + "<br>" + format_name + " is in the database already.")
                continue
            if format_name in format_name_to_id:
                # old_datasets.append(format_name)
                continue
            
            dbxref_id = row.iat[3]
            if dbxref_id != format_name and len(dbxref_id) > 40:
                dbxref_id = format_name

            url = row.iat[18]
            url_type = row.iat[19]

            display_name = row.iat[1]
            source = row.iat[2]
            if source == 'lab website':
                source = 'Lab website'
            if source not in ['GEO', 'ArrayExpress', 'Lab website']:
                source = 'Publication'
            source_id = source_to_id.get(source)
            if source_id is None:
                error_message = error_message + "<br>source=" + source + " is not in the database."
                continue

            if str(row.iat[9]) == 'nan' or str(row.iat[10]) == 'nan' or str(row.iat[11]) == 'nan':
                error_message = error_message + "<br>MISSING sample_count or is_in_spell or is_in_browser data for the following line:<br>" + line
                continue

            sample_count = int(row.iat[9])
            is_in_spell = row.iat[10]
            is_in_browser = row.iat[11]
            
            if is_in_spell and int(is_in_spell) >= 1:
                is_in_spell = True
            else:
                is_in_spell = False
            if is_in_browser and int(is_in_browser) >= 1:
                is_in_browser = True
            else:
                is_in_browser = False
            date_public = row.iat[5]
            if str(date_public) == 'nan':
                # no date provided
                date_public = str(datetime.now()).split(" ")[0]
            channel_count = None
            if str(row.iat[8]) != 'nan':
                channel_count = int(row.iat[8])

            file_id = None
            if str(row.iat[17]) != 'nan':
                file_id = file_to_id.get(row.iat[17])
                if file_id is None:
                    error_message = error_message + "<br>The file display_name: " + str(row.iat[17]) + " is not in the database"
                    continue

            description = str(row.iat[12])
            if description == 'nan':
                description = ''
            elif len(description) > 4000:
                error_message = error_message + "<br>The desc is too long. length=" + str(len(description)) + " for " + format_name  
                continue

            reference_ids = []
            pmids = str(row.iat[16]).replace(' ', '').split('|')
            for pmid in pmids:
                if pmid == '':
                    continue
                pmid = pmid.split('.')[0]
                if str(pmid).isdigit():
                    reference_id = pmid_to_reference_id.get(int(pmid))
                    if reference_id is None:
                        error_message = error_message + "<br>The PMID: " + str(pmid) + " is not in the database."
                        continue
                    reference_ids.append(reference_id)            
                    
            keywords = str(row.iat[15]).replace('"', '').split('|')
            keyword_ids = []
            for keyword in keywords:
                keyword = keyword.strip()
                if str(keyword) == 'nan' or keyword == '':
                    continue
                keyword_id = keyword_to_id.get(keyword)
                if keyword_id is None:
                    error_message = error_message + "<br>The keyword: '" + keyword + "' is not in the database."
                    continue
                keyword_ids.append(keyword_id)
            
            coll_institution = str(row.iat[14]).replace('"', '')
            if coll_institution == 'nan':
                coll_institution = ''
            if len(coll_institution) > 100:
                coll_institution = coll_institution.replace("National Institute of Environmental Health Sciences", "NIEHS")
                if coll_institution.startswith('Department'):
                    items = coll_institution.split(', ')
                    items.pop(0)
                    coll_institution = ', '.join(items)

            lab_name = str(row.iat[13]).replace('"', '')
            if lab_name == 'nan':
                lab_name = ''
            coll_display_name = lab_name
            name = lab_name.split(' ')
            lab_name = name[0]
            if len(name) > 1:
                first_name = str(name[1]).replace(', ', '')
                lab_name = lab_name + ' ' + first_name
            colleague_id = coll_name_institution_to_id.get((coll_display_name, coll_institution))
            if colleague_id is None:
                colleague_id = coll_name_to_id.get(coll_display_name)
                
            parent_dataset_id = None
            if str(row.iat[6]) != 'nan' and str(row.iat[6]).isdigit():
                parent_dataset_id = int(row.iat[6])

            dbxref_type = row.iat[4]

            for x in [format_name, display_name, dbxref_type, description, lab_name, coll_institution]:
                if type(x) == str:
                    continue
                try:
                    x = x.decode('utf-8')
                except UnicodeDecodeError:
                    pass
            
            entry = { "source_id": source_id,
                      "format_name": format_name, 
                      "display_name": str(display_name).replace('"', ''),
                      "obj_url": "/dataset/" + format_name,
                      "sample_count": sample_count,
                      "is_in_spell": is_in_spell,
                      "is_in_browser": is_in_browser,
                      "dbxref_id": dbxref_id,
                      "dbxref_type": dbxref_type,
                      "date_public": date_public,
                      "channel_count": channel_count,
                      "description": str(description).replace('"', ''),
                      "lab_name": lab_name,
                      "lab_location": coll_institution,
                      "colleague_id": colleague_id,
                      "keyword_ids": keyword_ids,
                      "reference_ids": reference_ids,
                      "file_id": file_id,
                      "url": url,
                      "url_type": url_type,
                      "parent_dataset_id": parent_dataset_id }
            data.append(entry)
        
        return [data, error_message]
            
    except Exception as e:
        return [[], str(e)]
        

def insert_datasets(curator_session, CREATED_BY, data):

    dataset_added = 0
    for x in data:
    
        # dataset table
        check_code = insert_dataset(curator_session, CREATED_BY, x)

        dataset_id = None
        if str(check_code).isdigit():
            dataset_id = check_code
        else:
            if dataset_added > 0:
                return "Total " + str(dataset_added) + " dataset rows has been added into database. Now an error occurred. See below" + check_code
            else:
                return check_code
        
        dataset_added = dataset_added + 1
        
        # dataset_file
        if x.get('file_id'):
            insert_dataset_file(curator_session, CREATED_BY, x['source_id'], dataset_id, x['file_id'])
            
        # dataset_keyword
        for keyword_id in x['keyword_ids']:
            insert_dataset_keyword(curator_session, CREATED_BY, x['source_id'], dataset_id, keyword_id)

        # dataset_reference
        for reference_id in x['reference_ids']:
            insert_dataset_reference(curator_session, CREATED_BY, x['source_id'], dataset_id, reference_id)
            
        # dataset_url
        if x.get('url') and x.get('url_type'):
            urls = x.get('url').split('|')
            # only one url_type is provided...                                                                                      
            type = x.get('url_type')
            for url in urls:
                insert_dataset_url(curator_session, CREATED_BY, x['source_id'], dataset_id, type, url)

        # datasetlab
        if x['lab_name'] or x['lab_location']:
            if x['lab_name'] == '' or  x['lab_name'] is None:
                 x['lab_name'] = 'Unknown'
            if x['lab_location'] == '' or x['lab_location'] is None:
                x['lab_location'] = 'Unknown'
            insert_datasetlab(curator_session, CREATED_BY, x['source_id'], dataset_id,
                              x['lab_name'], x['lab_location'], x['colleague_id'])

    return dataset_added

def load_dataset(request):
    
    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        sgd = DBSession.query(Source).filter_by(display_name='SGD').one_or_none()
        source_id = sgd.source_id

        fileObj = request.params.get('file')
        file = None
        filename = None
        if fileObj != '':
            file = fileObj.file
            filename = fileObj.filename
            
        if file is None or filename is None:
            return HTTPBadRequest(body=json.dumps({'error': "No dataset file is passed in."}), content_type='text/json')

        #error_message = check_non_ascii_characters(file)
        #if error_message:
        #    return HTTPBadRequest(body=json.dumps({'error': error_message}), content_type='text/json')
        #file.seek(0)
        
        [data, error_message] = read_dataset_data_from_file(file)    
        if error_message != '':
            return HTTPBadRequest(body=json.dumps({'error': error_message}), content_type='text/json') 
        
        # return HTTPBadRequest(body=json.dumps({'error': str(data)}), content_type='text/json')

        dataset_added = insert_datasets(curator_session, CREATED_BY, data)

        success_message = ''
        if str(dataset_added).isdigit():
            success_message = "Total " + str(dataset_added) + " row(s) from " + filename + " have been added into dataset and its related tables." 
        else:
            return HTTPBadRequest(body=json.dumps({'error': str(dataset_added)}), content_type='text/json')
        
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'dataset': "DATASET"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()


def read_dataset_sample_data_from_file(file):

    try:
        format_name_to_dataset_id_src = dict([(x.format_name, (x.dataset_id, x.source_id)) for x in DBSession.query(Dataset).all()])
        taxid_to_taxonomy_id = dict([(x.taxid, x.taxonomy_id) for x in DBSession.query(Taxonomy).all()])
        format_name_to_datasetsample_id = dict([(x.format_name, x.datasetsample_id) for x in DBSession.query(Datasetsample).all()])
        obi_name_to_id = dict([(x.format_name, x.obi_id) for x in DBSession.query(Obi).all()])
        
        format_name2display_name = {}
        dataset2index = {}
    
        data = []
        error_message = ''
        found_missing_dataset = {}
        
        df = pd.read_csv(file, sep='\t')
        
        for i, row in df.iterrows():
            
            dataset_format_name = row.iat[0]
            
            if dataset_format_name not in found_missing_dataset and dataset_format_name not in format_name_to_dataset_id_src:
                found_missing_dataset[dataset_format_name] = 1
                error_message = error_message + "<br>The dataset: " + dataset_format_name + " is not in DATASET table."
                continue
            elif dataset_format_name not in format_name_to_dataset_id_src:
                continue
            
            ## the following is the problematic line
            dataset_id = None
            source_id = None
            if dataset_format_name in format_name_to_dataset_id_src:
                (dataset_id, source_id) = format_name_to_dataset_id_src[dataset_format_name]
            else:
                error_message = error_message + "<br>The dataset format_name = " + dataset_format_name + " and source_id is not in DATASET table."

            display_name = str(row.iat[1]).replace('"', '')
            
            sample_order = row.iat[10]
            if str(sample_order) == 'nan':
                error_message = error_message + "<br>Missing sample order for one of the sample for dataset: " + dataset_format_name 
                continue
            sample_order = int(sample_order)

            assay_id = obi_name_to_id.get(str(row.iat[8]).split('|')[0])
            if assay_id is None:
                error_message = error_message + "<br>The OBI format_name: " + str(row.iat[8]) + " is not in the database."
                continue
            
            description = ""
            if str(row.iat[2]) != 'nan':
                description = row.iat[2]
                if len(description) > 500:
                    description = display_name
            entry = { "source_id": source_id,
                      "dataset_id": dataset_id,
                      "display_name": display_name,
                      "sample_order": sample_order,
                      "description": description,
                      "assay_id": assay_id }        
            
            if str(row.iat[5]) != 'nan':
                entry['biosample'] = row.iat[5]
            if str(row.iat[9]) != 'nan':
                entry['strain_name'] = row.iat[9]
            if len(df.columns) == 12 and str(row.iat[11]) != 'nan':
                taxonomy_id = taxid_to_taxonomy_id.get("TAX:"+row.iat[11])
                if taxonomy_id is None:
                    error_message = error_message + "<br>The taxid = " + str(row.iat[11]) + " for: " + dataset_format_name + " is not in TAXONOMY table."
                else:
                    entry['taxonomy_id'] = taxonomy_id
            GSM = str(row.iat[3])
            if GSM == 'nan':
                index = dataset2index.get(dataset_format_name, 0) + 1
                entry['format_name'] = dataset_format_name + "_sample_" + str(index)
                if entry['format_name'] in format_name_to_datasetsample_id:
                    error_message = error_message + "<br>format_name for Non GSM row: " + entry['format_name'] + " is used."
                    continue
                dataset2index[dataset_format_name] = index
                entry['obj_url'] = "/datasetsample/" + entry['format_name']
            else:
                entry['dbxref_type'] = str(row.iat[4])
                if format_name2display_name.get(GSM):
                    error_message = error_message + "<br>The format_name: " + GSM + " has been used for other sample " + format_name2display_name.get(GSM)
                    continue
                format_name2display_name[GSM] = display_name
                entry['format_name'] = dataset_format_name + "_" + GSM
                if entry['format_name'] in format_name_to_datasetsample_id:
                    error_message = error_message + "<br>format_name for GSM row: " + entry['format_name'] + " is used."
                    continue
                entry['obj_url'] = "/datasetsample/" + entry['format_name']
                entry['dbxref_id'] = GSM

            for x in [entry['format_name'], entry['display_name'], entry['dbxref_type'], entry['description']]:
                if type(x) == str:
                    continue
                try:
                    x = x.decode('utf-8')
                except UnicodeDecodeError:
                    pass
                      
            data.append(entry)
        return [data, error_message]
    except Exception as e:
        return [[], str(e)]

def insert_dataset_samples(curator_session, CREATED_BY, data):
        
    for x in data:
        dbxref_url = ''
        if x.get('dbxref_id'):
            dbxref_url = DBXREF_URL + x['dbxref_id']
        y = Datasetsample(format_name = x['format_name'],
                          display_name = x['display_name'],
                          obj_url = x['obj_url'],
                          source_id = x['source_id'],
                          dataset_id = x['dataset_id'],
                          sample_order = x['sample_order'],
                          description = x.get('description'),
                          biosample = x.get('biosample'),
                          assay_id = x['assay_id'],
                          strain_name = x.get('strain_name'),
                          taxonomy_id = x.get('taxonomy_id'),
                          dbxref_type = x.get('dbxref_type'),
                          dbxref_id = x.get('dbxref_id'),
                          dbxref_url = dbxref_url,
                          created_by = CREATED_BY)
        
        curator_session.add(y)
    
def load_datasetsample(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        sgd = DBSession.query(Source).filter_by(display_name='SGD').one_or_none()
        source_id = sgd.source_id

        fileObj = request.params.get('file')
        file = None
        filename = None
        if fileObj != '':
            file = fileObj.file
            filename = fileObj.filename

        fileObj = request.params.get('file')

        if file is None or filename is None:
            return HTTPBadRequest(body=json.dumps({'error': "No dataset sample file is passed in."}), content_type='text/json')

        #error_message = check_non_ascii_characters(file)
        #if error_message:
        #    return HTTPBadRequest(body=json.dumps({'error': error_message}), content_type='text/json')
        #file.seek(0)
        
        [data, error_message] = read_dataset_sample_data_from_file(file)
        if error_message != '':
            return HTTPBadRequest(body=json.dumps({'error': error_message}), content_type='text/json')

        insert_dataset_samples(curator_session, CREATED_BY, data)

        sample_added = len(data)
        
        success_message = "Total " + str(sample_added) + " row(s) from " + filename + " have been added into datasetsample table."
        
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'dataset_sample': "DATASET_SAMPLE"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()
            
def update_dataset(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        sgd = DBSession.query(Source).filter_by(display_name='SGD').one_or_none()
        source_id = sgd.source_id

        dataset_id = request.params.get('dataset_id', '')
        if dataset_id == '':
            return HTTPBadRequest(body=json.dumps({'error': "No dataset_id is passed in."}), content_type='text/json')
        
        # dataset_format_name = request.params.get('dataset_format_name', '')      
        d = curator_session.query(Dataset).filter_by(dataset_id=int(dataset_id)).one_or_none()
        if d is None:
            return HTTPBadRequest(body=json.dumps({'error': "The dataset_id = " + dataset_id + " is not in the database."}), content_type='text/json')

        dataset_id = d.dataset_id
        
        ## dataset

        update = 0
        format_name = request.params.get('format_name', '')
        if format_name == '':
            return HTTPBadRequest(body=json.dumps({'error': "format_name is required."}), content_type='text/json')
        if format_name != d.format_name:
            d.format_name = format_name
            update = 1
        
        display_name = request.params.get('display_name', '')
        if display_name == '':
            return HTTPBadRequest(body=json.dumps({'error': "display_name is required."}), content_type='text/json')
        if display_name != d.display_name:
            d.display_name = display_name
            update = 1

        dbxref_id = request.params.get('dbxref_id', '')
        if dbxref_id != d.dbxref_id:
            d.dbxref_id = dbxref_id
            update = 1

        dbxref_type = request.params.get('dbxref_type', '')
        if dbxref_type != d.dbxref_type:
            d.dbxref_type = dbxref_type
            update = 1

        date_public = request.params.get('date_public', '')
        if date_public != str(d.date_public).split(' ')[0]:
            d.date_public = date_public
            update = 1
            
        parent_dataset_id = request.params.get('parent_dataset_id', None)
        if str(parent_dataset_id).isdigit():
            parent_dataset_id = int(parent_dataset_id)
            if parent_dataset_id != d.parent_dataset_id:
                d.parent_dataset_id = parent_dataset_id
                update = 1
        elif d.parent_dataset_id:
            d.parent_dataset_id = None
            update = 1

        channel_count = request.params.get('channel_count', None)
        if str(channel_count).isdigit():
            channel_count = int(channel_count)
        if channel_count != d.channel_count:
            d.channel_count = channel_count
            update = 1
    
        # required
        sample_count = request.params.get('sample_count', None)
        if sample_count is None:
            return HTTPBadRequest(body=json.dumps({'error': "sample_count is required."}), content_type='text/json')
        if str(sample_count).isdigit():
            sample_count = int(sample_count)
        if sample_count != d.sample_count:
            d.sample_count = sample_count
            update = 1
    
        is_in_spell = request.params.get('is_in_spell')
        is_in_spell = True if is_in_spell == 'true' else False
        if is_in_spell != d.is_in_spell:
            d.is_in_spell = is_in_spell
            update = 1

        is_in_browser = request.params.get('is_in_browser')
        is_in_browser = True if is_in_browser == 'true' else False
        if is_in_browser != d.is_in_browser:
            d.is_in_browser = is_in_browser
            update = 1

        description = request.params.get('description', '')
        if description != d.description:
            d.description = description
            update = 1

        success_message = ''
        if update == 1:
            success_message = 'The dataset table has been successfully updated'

        # return HTTPBadRequest(body=json.dumps({'error': "dataset table"}), content_type='text/json')
    
        ## dataset_file
        
        all_dFile = curator_session.query(DatasetFile).filter_by(dataset_id=dataset_id).all()
        all_file_ids_DB = {}
        for x in all_dFile:
            all_file_ids_DB[x.file_id] = x
            
        filenames = request.params.get('filenames', '')
        files = filenames.split('|')

        all_file_ids_NEW = {}
        for file in files:
            if file == '':
                continue
            fd = curator_session.query(Filedbentity).filter_by(display_name=file, subclass='FILE', dbentity_status='Active').one_or_none()
            if fd is None:
                return HTTPBadRequest(body=json.dumps({'error': "file = " + file + " is not in the database."}), content_type='text/json')
            all_file_ids_NEW[fd.dbentity_id] = fd
            if fd.dbentity_id not in all_file_ids_DB:
                insert_dataset_file(curator_session, CREATED_BY, source_id, dataset_id, fd.dbentity_id)
                success_message = success_message + "<br>file '" + fd.display_name + "' has been added for this dataset."
        for file_id in all_file_ids_DB:
            if file_id not in all_file_ids_NEW:
                x = all_file_ids_DB[file_id]
                success_message = success_message + "<br>file '" + fd.display_name + "' has been added for this dataset."
                curator_session.delete(x)

        # return HTTPBadRequest(body=json.dumps({'error': "dataset_file table"}), content_type='text/json')
    
        ## dataset_keyword
        
        all_Kw = curator_session.query(DatasetKeyword).filter_by(dataset_id=dataset_id).all()
        all_keyword_ids_DB = {}
        for x in all_Kw:
            all_keyword_ids_DB[x.keyword_id] = x

        keywords = request.params.get('keywords', '')
        kws = keywords.split('|')

        all_keyword_ids_NEW = {}
        keyword_to_id = {}
        for kw in kws:
            kw = kw.strip()
            if kw == '':
                continue
            k = curator_session.query(Keyword).filter_by(display_name=kw).one_or_none()
            if k is None:
                return HTTPBadRequest(body=json.dumps({'error': "The keyword: "+kw + " is not in the database."}), content_type='text/json')
            keyword_id = k.keyword_id
            keyword_to_id[kw] = keyword_id
            all_keyword_ids_NEW[keyword_id] = 1
            if keyword_id not in all_keyword_ids_DB:
                insert_dataset_keyword(curator_session, CREATED_BY, source_id, dataset_id, keyword_id)
                success_message = success_message + "<br>keyword '" + kw + "' has been added for this dataset."

        for keyword_id in all_keyword_ids_DB:
            if keyword_id not in all_keyword_ids_NEW:
                x = all_keyword_ids_DB[keyword_id]
                success_message = success_message + "<br>keyword '" + x.keyword.display_name + "' has been removed from this dataset."
                curator_session.delete(x)

            
        # return HTTPBadRequest(body=json.dumps({'error': "dataset_keyword table"}), content_type='text/json')

        ## file_keyword
        # keywords = request.params.get('keywords', '')
        # kws = keywords.split('|')
        
        for file_id in all_file_ids_NEW:
            all_file_kw = curator_session.query(FileKeyword).filter_by(file_id=file_id).all()
            keywords_file_db = {}
            for kw in all_file_kw:
                keywords_file_db[kw.keyword.display_name.upper()] = kw.keyword_id
            for kw in kws:
                if kw == '':
                    continue
                if kw.upper() in keywords_file_db:
                    del keywords_file_db[kw.upper()]
                    continue
                keyword_id = keyword_to_id[kw]
                insert_file_keyword(curator_session, CREATED_BY, source_id, file_id, keyword_id)
                success_message = success_message + "<br>keyword '" + kw + "' has been added for the associated file."
                
            for kw in keywords_file_db:
                keyword_id = keywords_file_db[kw]
                fk = curator_session.query(FileKeyword).filter_by(file_id=file_id, keyword_id=keyword_id).one_or_none()
                if fk:
                    success_message = success_message + "<br>keyword '" + kw + "' has been removed from the associated file."
                    curator_session.delete(fk)

        ## dataset_reference

        all_refs = curator_session.query(DatasetReference).filter_by(dataset_id=dataset_id).all()

        all_ref_ids_DB = {}
        for x in all_refs:
            all_ref_ids_DB[x.reference.dbentity_id] = x

        pmids = request.params.get('pmids', '')
        pmid_list = pmids.split('|')

        all_ref_ids_NEW = {}
        for pmid in pmid_list:
            if pmid == '':
                continue
            if str(pmid).isdigit():
                ref = curator_session.query(Referencedbentity).filter_by(pmid=int(pmid)).one_or_none()
                if ref is None:
                    return HTTPBadRequest(body=json.dumps({'error': 'pmid = ' + pmid + ' is not in the database.'}), content_type='text/json')
                reference_id = ref.dbentity_id
                if reference_id not in all_ref_ids_DB:
                    insert_dataset_reference(curator_session, CREATED_BY, source_id, dataset_id, reference_id)
                    success_message = success_message + "<br>pmid '" + pmid + "' has been added for this dataset."
                all_ref_ids_NEW[reference_id] = 1
            else:
                return HTTPBadRequest(body=json.dumps({'error': 'pmid = ' + pmid + ' is not valid.'}), content_type='text/json')
                
        for reference_id in all_ref_ids_DB:
            if reference_id not in all_ref_ids_NEW:
                x = all_ref_ids_DB[reference_id]
                success_message = success_message + "<br>pmid '" + pmid + "' has been removed for this dataset."
                curator_session.delete(x)
    
        ## dataset_url

        all_urls = curator_session.query(DatasetUrl).filter_by(dataset_id=dataset_id).all()
        
        all_urls_DB = {}
        for x in all_urls:
            all_urls_DB[x.display_name + '|' + x.obj_url] = x

        url1 = request.params.get('url1', '').replace('| ', '|').replace(' |', '|')
        url2 = request.params.get('url2', '').replace('| ', '|').replace(' |', '|')
        url3 = request.params.get('url3', '').replace('| ', '|').replace(' |', '|')
        for url_set in [url1, url2, url3]:
            if url_set == '':
                continue
            if url_set not in all_urls_DB:
                [u_display_name, url] = url_set.split('|')
                insert_dataset_url(curator_session, CREATED_BY, source_id, dataset_id, u_display_name, url)
                success_message = success_message + "<br>URL '" + url_set + "' has been added for this dataset."
        for url_set in all_urls_DB:
            if url_set not in [url1, url2, url3]:
                x = all_urls_DB[url_set]
                success_message = success_message + "<br>URL '" + url_set + "' has been removed for this dataset."
                curator_session.delete(x)

        # return HTTPBadRequest(body=json.dumps({'error': "dataset_url table"}), content_type='text/json')

    
        ## datasetlab
        
        all_labs = curator_session.query(Datasetlab).filter_by(dataset_id=dataset_id).all()
        labs_db = {}
        for lab in all_labs:
            colleague_id = None
            if lab.colleague_id:
                colleague_id = lab.colleague_id
            key = (lab.lab_name, lab.lab_location, colleague_id)
            labs_db[key] = lab

        lab1 = request.params.get('lab1', '').replace(' |', '|').replace('| ', '|')
        lab2 = request.params.get('lab2', '').replace(' |', '|').replace('| ', '|')    
        
        for labNew in [lab1, lab2]:
            if labNew is None or labNew == '':
                continue
            [lab_name, lab_location, colleague_format_name] = labNew.split('|')
            lab_name = lab_name.replace('lab_name: ', '').replace('Unknown', '')
            lab_location = lab_location.replace('lab_location: ', '').replace('Unknown', '')
            if lab_name == '' and lab_location == '':
                continue
            if lab_name == '':
                lab_name = 'Unknown'
            if lab_location == '':
                lab_location = 'Unknown'
            colleague_format_name = colleague_format_name.replace('colleague_format_name: ', '')
            coll = curator_session.query(Colleague).filter_by(format_name=colleague_format_name).one_or_none()
            colleague_id = None
            if coll:
                colleague_id = coll.colleague_id
            key = (lab_name, lab_location, colleague_id)
            if key in labs_db:
                del labs_db[key]
                continue
            insert_datasetlab(curator_session, CREATED_BY, source_id, dataset_id, lab_name, lab_location, colleague_id)
            success_message = success_message + "<br>lab '" + labNew + "' has been added for this dataset."

        for key in labs_db:
            success_message = success_message + "<br>lab '" + lab.lab_name + '|' + lab.lab_location + "' has been removed for this dataset."
            lab = labs_db[key]
            curator_session.delete(lab)
            
        # return HTTPBadRequest(body=json.dumps({'error': "datasetlab table"}), content_type='text/json') 
            
            
        if success_message == '':
            success_message = 'Nothing is changed'
        
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'dataset': "DATASET"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()

def delete_dataset(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])

        dataset_id = request.params.get('dataset_id', '')
        if dataset_id == '':
            return HTTPBadRequest(body=json.dumps({'error': "No dataset_id is passed in."}), content_type='text/json')
        d = curator_session.query(Dataset).filter_by(dataset_id=int(dataset_id)).one_or_none()
        if d is None:
            return HTTPBadRequest(body=json.dumps({'error': "The dataset_id = " + dataset_id + " is not in the database."}), content_type='text/json')
        
        dataset_id = d.dataset_id

        ## check to see if this dataset associated datasetsample IDs are in the
        ## expressionannotation table. 
        found = 0
        all_dSample = curator_session.query(Datasetsample).filter_by(dataset_id=dataset_id).all()
        for x in all_dSample:
            all_exp = curator_session.query(Expressionannotation).filter_by(datasetsample_id=x.datasetsample_id).all()
            if len(all_exp) > 0:
                found = 1
                break
        if found == 1:
            return HTTPBadRequest(body=json.dumps({'error': "The associated datasetsample is used in Expressionannotation table."}), content_type='text/json')
        
        ## dataset_file
        all_dFile = curator_session.query(DatasetFile).filter_by(dataset_id=dataset_id).all()
                    
        ## dataset_keyword
        all_dKw = curator_session.query(DatasetKeyword).filter_by(dataset_id=dataset_id).all()
                    
        ## dataset_reference
        all_dRef = curator_session.query(DatasetReference).filter_by(dataset_id=dataset_id).all()
                    
        ## dataset_url
        all_dUrl = curator_session.query(DatasetUrl).filter_by(dataset_id=dataset_id).all()
                    
        ## datasetlab
        all_dLab = curator_session.query(Datasetlab).filter_by(dataset_id=dataset_id).all()
        
        ## datasetsample
        # see above all_dSample

        ## datasettrack
        all_dTrack = curator_session.query(Datasettrack).filter_by(dataset_id=dataset_id).all()

        for x in all_dFile + all_dKw + all_dRef + all_dUrl + all_dLab + all_dSample + all_dTrack:
            curator_session.delete (x)

        curator_session.delete(d)

        success_message = 'The dataset row along with its associated File/Keyword/URL/Lab/Sample/Track has been successfully deleted.'	

        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'dataset': "DATASET"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()

def update_datasetsample(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        sgd = DBSession.query(Source).filter_by(display_name='SGD').one_or_none()
        source_id = sgd.source_id

        datasetsample_id = request.params.get('datasetsample_id', '')
        if datasetsample_id == '':
            return HTTPBadRequest(body=json.dumps({'error': "No datasetsample_id is passed in."}), content_type='text/json')
        d = curator_session.query(Datasetsample).filter_by(datasetsample_id=int(datasetsample_id)).one_or_none()

        if d is None:
            return HTTPBadRequest(body=json.dumps({'error': "The datasetsample_id = " + datasetsample_id + " is not in the database."}), content_type='text/json')

        format_name = request.params.get('format_name', '')
        display_name = request.params.get('display_name', '')
        dbxref_id = request.params.get('dbxref_id', '')
        dbxref_type = request.params.get('dbxref_type', '')
        dbxref_url = request.params.get('dbxref_url', '')
        strain_name = request.params.get('strain_name', '')
        biosample = request.params.get('biosample', '')
        assay_id = request.params.get('assay_id', '')
        sample_order = request.params.get('sample_order', '') 
        description = request.params.get('description', '')
        
        if format_name == '' or display_name == '' or sample_order == '' or assay_id == '':
            return HTTPBadRequest(body=json.dumps({'error': "format_name, display_name, sample_order, and assay_id are required fields."}), content_type='text/json')
        update = 0
        if format_name != d.format_name:
            d.format_name = format_name
            update = 1
        if display_name != d.display_name:
            d.display_name = display_name
            update = 1
        if dbxref_id != d.dbxref_id:
            d.dbxref_id = dbxref_id
            update = 1
        if dbxref_type != d.dbxref_type:
            d.dbxref_type = dbxref_type
            update = 1
        if dbxref_url != d.dbxref_url:
            d.dbxref_url = dbxref_url
            update = 1
        if strain_name != d.strain_name:
            d.strain_name = strain_name
            update = 1
        if biosample != d.biosample:
            d.biosample = biosample
            update = 1
        if int(sample_order) != d.sample_order:
            d.sample_order = int(sample_order)
            update = 1
        if description != d.description:
            d.description = description
            update = 1

        if int(assay_id) != d.assay_id:
            d.assay_id = int(assay_id)
            update = 1

        success_message = ''
        if update == 1:
            curator_session.add(d)
            success_message = 'The datasetsample row has been successfully updated'
        else:
            success_message = 'Nothing is changed'
            
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'dataset': "DATASET"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()

def delete_datasetsample(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])

        datasetsample_id = request.params.get('datasetsample_id', '')
        if datasetsample_id == '':
            return HTTPBadRequest(body=json.dumps({'error': "No datasetsample_id is passed in."}), content_type='text/json')
        d = curator_session.query(Datasetsample).filter_by(datasetsample_id=int(datasetsample_id)).one_or_none()

        if d is None:
            return HTTPBadRequest(body=json.dumps({'error': "The datasetsample_id " + datasettrack_id + " is not in the database."}), content_type='text/json')

        all_exp = curator_session.query(Expressionannotation).filter_by(datasetsample_id=datasetsample_id).all()
        if len(all_exp) > 0:
            return HTTPBadRequest(body=json.dumps({'error': "This datasetsample_id is in Expressionannotation table."}), content_type='text/json')
        
        curator_session.delete(d)

        success_message = 'The datasetsample row has been successfully deleted.'
        
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'dataset': "DATASET"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()
            
def update_datasettrack(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        sgd = DBSession.query(Source).filter_by(display_name='SGD').one_or_none()
        source_id = sgd.source_id

        datasettrack_id = request.params.get('datasettrack_id', '')
        if datasettrack_id == '':
            return HTTPBadRequest(body=json.dumps({'error': "No datasettrack_id is passed in."}), content_type='text/json')
        d = curator_session.query(Datasettrack).filter_by(datasettrack_id=int(datasettrack_id)).one_or_none()

        if d is None:
            return HTTPBadRequest(body=json.dumps({'error': "The datasettrack_id " + datasettrack_id + " is not in the database."}), content_type='text/json')
        
        format_name = request.params.get('format_name', '')
        display_name = request.params.get('display_name', '')
        obj_url = request.params.get('obj_url', '')
        track_order = request.params.get('track_order', '')

        if format_name == '' or display_name == '' or obj_url == '' or track_order == '':
            return HTTPBadRequest(body=json.dumps({'error': "All four fields are required."}), content_type='text/json')
        
        update = 0
        if format_name != d.format_name:
            d.format_name = format_name
            update = 1
        if display_name != d.display_name:
            d.display_name = display_name
            update = 1
        if obj_url != d.obj_url:
            d.obj_url = obj_url
            update = 1
        if track_order != d.track_order:
            d.track_order = track_order
            update = 1
            
        success_message = ''
        if update == 1:
            curator_session.add(d)
            success_message = 'The datasettrack row has been successfully updated.'
        else:
            success_message = 'Nothing is changed'
            
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'dataset': "DATASET"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()

def delete_datasettrack(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        
        datasettrack_id = request.params.get('datasettrack_id', '')
        if datasettrack_id == '':
            return HTTPBadRequest(body=json.dumps({'error': "No datasettrack_id is passed in."}), content_type='text/json')
        d = curator_session.query(Datasettrack).filter_by(datasettrack_id=int(datasettrack_id)).one_or_none()

        if d is None:
            return HTTPBadRequest(body=json.dumps({'error': "The datasettrack_id " + datasettrack_id + " is not in the database."}), content_type='text/json')

        curator_session.delete(d)

        success_message = 'The datasettrack row has been successfully deleted.'
        
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'dataset': "DATASET"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()
