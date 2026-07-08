import logging
import os
import datetime
from sqlalchemy import or_
from pyramid.httpexceptions import HTTPBadRequest, HTTPOk
from sqlalchemy.exc import IntegrityError, DataError
import transaction
import json
from src.models import DBSession, Dbentity, Filedbentity, Referencedbentity, FilePath, \
                       Path, FileKeyword, Keyword, ReferenceFile, Dataset, DatasetFile,\
                       DatasetKeyword, Source
from src.aws_helpers import get_checksum
from src.helpers import upload_file
from src.aws_helpers import upload_file_to_s3
from src.curation_helpers import get_curator_session

# PREVIEW_URL = os.environ['PREVIEW_URL']

log = logging.getLogger('curation')

def get_metadata_for_one_file(request):

    try:
        
        data = {}
        
        sgdid = str(request.matchdict['sgdid'])
    
        x = DBSession.query(Filedbentity).filter_by(sgdid=sgdid).one_or_none()
        
        if x is None:
            return HTTPBadRequest(body=json.dumps({'error': "The file sgdid " + sgdid + " is not in the database."}))
        
        data['display_name'] = x.display_name
        data['previous_file_name'] = x.previous_file_name
        data['sgdid'] = x.sgdid
        data['dbentity_status'] = x.dbentity_status
        data['file_extension'] = x.file_extension
        data['file_date'] = str(x.file_date).split(' ')[0]
        data['is_public'] = x.is_public
        data['is_in_spell'] = x.is_in_spell
        data['is_in_browser'] = x.is_in_browser
        data['md5sum'] = x.md5sum
        data['readme_file_id'] = x.readme_file_id
        data['s3_url'] = x.s3_url
        data['description'] = x.description
        data['year'] = x.year
        data['file_size'] = x.file_size
        data['topic_id'] = x.topic_id
        data['data_id'] = x.data_id
        data['format_id'] = x.format_id

        all_kw = DBSession.query(FileKeyword).filter_by(file_id=x.dbentity_id).all()
        keywords = []
        for kw in all_kw:
            keywords.append(kw.keyword.display_name)
        data['keywords'] = '|'.join(keywords)

        fp = DBSession.query(FilePath).filter_by(file_id=x.dbentity_id).one_or_none()
        if fp is not None:
            data['path_id'] = fp.path_id
        else:
            data['path_id'] = ''

        all_refs = DBSession.query(ReferenceFile).filter_by(file_id=x.dbentity_id).all()
        pmids = ''
        for ref in all_refs:
            if pmids != '':
                pmids = pmids + "|"
            pmids = pmids + ref.file_type + ":" + str(ref.reference.pmid)
        data['pmids'] = pmids
            
        return HTTPOk(body=json.dumps(data),content_type='text/json')
    except Exception as e:
        log.error(e)
        return HTTPBadRequest(body=json.dumps({'error': str(e)}))
    finally:
        if DBSession:
            DBSession.remove()

            
def get_list_of_file_metadata(request):

    try:
        query = str(request.matchdict['query'])
        data = []

        ## search by PMID:
        rows_by_pmid = []
        if query.isdigit():
            pmid = int(query)
            ref = DBSession.query(Referencedbentity).filter_by(pmid=pmid).one_or_none()
            if ref is not None:
                all_refFiles = DBSession.query(ReferenceFile).filter_by(reference_id=ref.dbentity_id).all()
                for x in all_refFiles:
                    rows_by_pmid.append(x.file)

        ## search by GEO/SRA/ArrayExpress ID:
        rows_by_GEO = []
        all_datasets = DBSession.query(Dataset).filter(Dataset.format_name.ilike('%'+query+'%')).all()
        for x in all_datasets:
            all_df = DBSession.query(DatasetFile).filter_by(dataset_id=x.dataset_id).all()
            for y in all_df:
                rows_by_GEO.append(y.file)

        ## search by file name:
        rows_by_filename = DBSession.query(Filedbentity).filter(or_(Filedbentity.display_name.ilike('%'+query+'%'), Filedbentity.previous_file_name.ilike('%'+query+'%'))).order_by(Filedbentity.display_name).all()

        foundSGDID = {}
        for x in rows_by_pmid + rows_by_GEO + rows_by_filename:
            if x.sgdid in foundSGDID:
                continue
            foundSGDID[x.sgdid] = 1
            data.append({ 'display_name': x.display_name,
                          'previous_file_name': x.previous_file_name,
                          'sgdid': x.sgdid,
                          'is_in_browser': x.is_in_browser,
                          'is_in_spell': x.is_in_spell,
                          'is_public': x.is_public,
                          'year': x.year,
                          's3_url': x.s3_url,
                          'description': x.description })
        return HTTPOk(body=json.dumps(data),content_type='text/json')
    except Exception as e:
        log.error(e)
        return HTTPBadRequest(body=json.dumps({'error': str(e)}))
    finally:
        if DBSession:
            DBSession.remove()    

def insert_reference_file(curator_session, CREATED_BY, source_id, file_id, reference_id, file_type):

    try:
        x = ReferenceFile(file_id = file_id,
                          reference_id = reference_id,
                          file_type = file_type,
                          source_id = source_id,
                          created_by = CREATED_BY)
        curator_session.add(x)
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()

def insert_file_path(curator_session, CREATED_BY, source_id, file_id, path_id):

    try:
        x = FilePath(file_id = file_id,
                     path_id = path_id,
                     source_id = source_id,
                     created_by = CREATED_BY)
        curator_session.add(x)
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()

def insert_dataset_keyword(curator_session, CREATED_BY, source_id, dataset_id, keyword_id):

    try:
        x = DatasetKeyword(dataset_id = dataset_id,
                           keyword_id = keyword_id,
                           source_id = source_id,
                           created_by = CREATED_BY)
        curator_session.add(x)
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
            
def insert_file_keyword(curator_session, CREATED_BY, source_id, file_id, keyword_id):

    try:
        x = FileKeyword(file_id = file_id,
                        keyword_id = keyword_id,
                        source_id = source_id,
                        created_by = CREATED_BY)
        curator_session.add(x)
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
            
def insert_keyword(curator_session, CREATED_BY, source_id, keyword):

    kw = curator_session.query(Keyword).filter(Keyword.display_name.ilike(keyword)).one_or_none()
    if kw:
        return kw.keyword_id
    else:
        return "The keyword: " + keyword + " is not in the database."

    ## DON'T WANT TO ADD NEW KEYWORDS through interfaces at this moment
    keyword_id = None
    returnValue = None
    keyword_id = None
    try:
        format_name = keyword.replace(' ', '_').replace('/', '_')
        obj_url = '/keyword/' + format_name
        x = Keyword(format_name = format_name,
                    display_name = keyword,
                    obj_url = obj_url,
                    source_id = source_id,
                    is_obsolete = False,
                    created_by = CREATED_BY)
        curator_session.add(x)
        transaction.commit()
        keyword_id = x.keyword_id
    except Exception as e:
        transaction.abort()
        if curator_session:
            curator_session.rollback()
        returnValue = 'Insert Keyword failed: ' + str(e)
    if keyword_id:
        return keyword_id 
    else:
        return returnValue
    
def add_metadata(request, curator_session, CREATED_BY, source_id, old_file_id, file, filename, md5sum):

    try:
        success_message = ''
        display_name = request.params.get('display_name')
        if display_name == '':
            return HTTPBadRequest(body=json.dumps({'error': "File display_name field is blank"}), content_type='text/json')

        dbentity_status = request.params.get('dbentity_status', None)
        if dbentity_status is None or dbentity_status == '':
            return HTTPBadRequest(body=json.dumps({'error': "dbentity_status field is blank"}), content_type='text/json')
        if dbentity_status not in ['Active', 'Archived']:
            return HTTPBadRequest(body=json.dumps({'error': "dbentity_status must be 'Active' or 'Archived'."}), content_type='text/json')

        previous_file_name = request.params.get('previous_file_name', '')

        description = request.params.get('description', '')
    
        year = request.params.get('year')
        if year is None or year == '':
            return HTTPBadRequest(body=json.dumps({'error': "year field is blank"}), content_type='text/json')
        year = int(year)
    
        file_size = request.params.get('file_size')
        if file_size is None or file_size == '':
            return HTTPBadRequest(body=json.dumps({'error': "file_size field is blank"}), content_type='text/json')
        file_size = int(file_size)

        file_extension = request.params.get('file_extension')
        if file_extension is None:
            return HTTPBadRequest(body=json.dumps({'error': "file_extension field is blank"}), content_type='text/json')

        topic_id = request.params.get('topic_id')
        topic_id = int(topic_id)

        data_id = request.params.get('data_id')
        data_id = int(data_id)

        format_id = request.params.get('format_id')
        format_id = int(format_id)

        is_public = request.params.get('is_public', '')
        if is_public == '':
            return HTTPBadRequest(body=json.dumps({'error': "is_public field is blank"}), content_type='text/json')

        is_in_spell = request.params.get('is_in_spell', '')
        if is_in_spell == '':
            return HTTPBadRequest(body=json.dumps({'error': "is_in_spell field is blank"}), content_type='text/json')

        is_in_browser = request.params.get('is_in_browser', '')
        if is_in_browser == '':
            return HTTPBadRequest(body=json.dumps({'error': "is_in_browser field is blank"}), content_type='text/json')

        file_date = request.params.get('file_date', '')
        if file_date == '':
            return HTTPBadRequest(body=json.dumps({'error': "file_date field is blank"}), content_type='text/json')
        if '-' not in file_date:
            return HTTPBadRequest(body=json.dumps({'error': "file_date format: yyyy-mm-dd"}), content_type='text/json')
    
        readme_file_id = request.params.get('readme_file_id')
        if str(readme_file_id).isdigit():
            readme_file_id = int(readme_file_id)
        else:
            readme_file_id = None
        
        #### add metadata to database
        file_date=datetime.datetime.strptime(file_date, '%Y-%m-%d'),
        fd = Filedbentity(created_by=CREATED_BY,
                          display_name=display_name,
                          format_name=display_name,
                          subclass='FILE',
                          previous_file_name=filename,
                          file_extension=file_extension,
                          file_size=file_size,
                          json=None,
                          s3_url=None,
                          dbentity_status='Active',
                          year=year,
                          file_date=file_date,
                          description=description,
                          data_id=data_id,
                          format_id=format_id,
                          topic_id=topic_id,
                          is_public=is_public,
                          is_in_spell=is_in_spell,
                          is_in_browser=is_in_browser,
                          readme_file_id=readme_file_id,
                          source_id=source_id,
                          md5sum=md5sum)
        curator_session.add(fd)
        curator_session.flush()
        file_id = fd.dbentity_id
        transaction.commit()
        curator_session.flush()

        fd = curator_session.query(Filedbentity).filter_by(dbentity_id=file_id).one_or_none()
                
        #### upload file to s3
        s3_url = upload_file_to_s3(file, fd.sgdid + "/" + filename)
        fd.s3_url = s3_url
        curator_session.add(fd)
        transaction.commit()
        success_message = success_message + "<br>The metadata for this new version has been added into database and the file is up in s3 now."

        #### add path_id and newly created file_id to file_path table
        path_id = request.params.get('path_id')
        if str(path_id).isdigit():
            insert_file_path(curator_session, CREATED_BY, source_id, file_id, int(path_id))
            success_message = success_message + "<br>path_id has been added for this file."

        #### add paper(s) and newly created file_id to reference_file table
        pmids = request.params.get('pmids', '')
        pmid_list = pmids.split('|')
        for type_pmid in pmid_list:
            type_pmid = type_pmid.replace(' ', '')
            if type_pmid == '':
                continue
            [file_type, pmid] = type_pmid.split(':') 
            ref = curator_session.query(Referencedbentity).filter_by(pmid=int(pmid)).one_or_none()
            if ref is None:
                return HTTPBadRequest(body=json.dumps({'error': "The PMID: " + pmid + " is not in the database."}), content_type='text/json')
            reference_id = ref.dbentity_id
            insert_reference_file(curator_session, CREATED_BY, source_id, file_id,
                                  reference_id, file_type)
            
        ### add keywords to file_keyword table
        keywords = request.params.get('keywords', '')
        kw_list = keywords.split('|')
        all_new_keyword_id = {}
        for kw in kw_list:
            kw = kw.strip()
            if kw == '':
                continue
            keyword_id = insert_keyword(curator_session, CREATED_BY, source_id, kw)
            if str(keyword_id).isdigit():
                all_new_keyword_id[keyword_id] = kw
                success_message = success_message + "<br>keyword '" + kw + "' has been added for this file."
                insert_file_keyword(curator_session, CREATED_BY, source_id, file_id, keyword_id)
            else:
                err_msg = keyword_id
                return HTTPBadRequest(body=json.dumps({'error': err_msg}), content_type='text/json')

        ### update dataset_keyword table
        all_df = curator_session.query(DatasetFile).filter_by(file_id=old_file_id).all()
        for x in all_df:
            already_in_db = {}
            all_dk = curator_session.query(DatasetKeyword).filter_by(dataset_id=x.dataset_id).all()
            for kw in all_dk:
                if kw.keyword.keyword_id in all_new_keyword_id:
                    already_in_db[kw.keyword.keyword_id] = 1
                    continue
                curator_session.delete(kw)
            for keyword_id in all_new_keyword_id:
                if keyword_id in already_in_db:
                    continue
                success_message = success_message + "<br>keyword '" + all_new_keyword_id[keyword_id] + "' has been added for the associated dataset."
                insert_dataset_keyword(curator_session, CREATED_BY, source_id, x.dataset_id, keyword_id)
                
        ### set dbentity_status = 'Archived' for the old_file_id
        curator_session.query(Dbentity).filter_by(dbentity_id=old_file_id).filter_by(dbentity_status='Active').update({"dbentity_status": 'Archived'}, synchronize_session='fetch')
        success_message = success_message + "<br>The dbentity_status has been set to 'Archived' for old version."

        ### update dataset_file table to point to new file_id
        curator_session.query(DatasetFile).filter_by(file_id=old_file_id).update({"file_id": file_id}, synchronize_session='fetch')

        ### delete paper associated with old file 
        all_old_refs = curator_session.query(ReferenceFile).filter_by(file_id=old_file_id).all()
        for x in all_old_refs:
            curator_session.delete(x)
            
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'metadata': "METADATA"}), content_type='text/json')
    except Exception as e:
        log.exception('ADD metadata ERROR')
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()
        
def update_metadata(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        sgd = DBSession.query(Source).filter_by(display_name='SGD').one_or_none()
        source_id = sgd.source_id
        
        sgdid = request.params.get('sgdid')
        if sgdid == '':
            return HTTPBadRequest(body=json.dumps({'error': "No SGDID is passed in."}), content_type='text/json')
    
        d = curator_session.query(Filedbentity).filter_by(sgdid=sgdid).one_or_none()

        if d is None:
            return HTTPBadRequest(body=json.dumps({'error': "The SGDID " + sgdid + " is not in the database."}), content_type='text/json')

        file_id = d.dbentity_id

        ## check to see if there is a file passed in and if yes, if its md5sum is
        ## the same as the one in the database, ignore it; otherwise upload 
        ## the new file to s3, insert metadata, set status = 'Active', mark the 
        ## old version as 'Archived'
    
        fileObj = request.params.get('file')
    
        file = None
        filename = None
        if fileObj != '':
            file = fileObj.file
            filename = fileObj.filename
            

        ## for small file:
        # file = <_io.BytesIO object at 0x7f668c41c468>
        
        ## for BIG file
        # fileObj = FieldStorage('file', 'pone.0000217.e011.jpg')
        # file = file <_io.BufferedRandom name=23>
        # filename = pone.0000217.e011.jpg
        ## this name=23 will cause issue
        
        if filename:
            md5sum = get_checksum(file)
            if md5sum != d.md5sum:
                message = add_metadata(request, curator_session, CREATED_BY, source_id,
                                       file_id, file, filename, md5sum)
                return message
            
        success_message = ""
        
        ## update file display_name
        display_name = request.params.get('display_name')
        if display_name == '':
            return HTTPBadRequest(body=json.dumps({'error': "File display_name field is blank"}), content_type='text/json')
        if display_name != d.display_name:
            success_message = "display_name has been updated from '" + d.display_name + "' to '" + display_name + "'."
            d.display_name = display_name
            curator_session.add(d)
            
        ## update dbentity_status
        dbentity_status = request.params.get('dbentity_status', None)
        if dbentity_status is None:
            return HTTPBadRequest(body=json.dumps({'error': "dbentity_status field is blank"}), content_type='text/json')
        if dbentity_status not in ['Active', 'Archived']:
            return HTTPBadRequest(body=json.dumps({'error': "dbentity_status must be 'Active' or 'Archived'."}), content_type='text/json')
        if dbentity_status != d.dbentity_status:
            success_message = success_message + "<br>dbentity_status has been updated from '" + d.dbentity_status + "' to '" + dbentity_status + "'."
            d.dbentity_status = dbentity_status
            curator_session.add(d)

        ## update previous file names
        previous_file_name = request.params.get('previous_file_name', '')
        if (previous_file_name or d.previous_file_name) and previous_file_name != d.previous_file_name:
            success_message = success_message + "<br>previous_file_name has been updated from '" + str(d.previous_file_name) + "' to '" + previous_file_name + "'."
            d.previous_file_name = previous_file_name
            curator_session.add(d)

        ## update description
        description = request.params.get('description', '')
        if description != d.description:
            success_message = success_message + "<br>description has been updated from '" + str(d.description) + "' to '" + description + "'."
            d.description = description
            curator_session.add(d)

        ## update year                                                                              
        year = request.params.get('year')
        if year is None:
            return HTTPBadRequest(body=json.dumps({'error': "year field is blank"}), content_type='text/json')
        year = int(year)
        if year != d.year:
            success_message = success_message + "<br>year has been updated from '" + str(d.year) + "' to '" + str(year) + "'."
            d.year = year
            curator_session.add(d)    

        ## update file_size 
        file_size = request.params.get('file_size')
        if file_size is None:
            return HTTPBadRequest(body=json.dumps({'error': "file_size field is blank"}), content_type='text/json')
        file_size = int(file_size)
        if file_size != d.file_size:
            success_message = success_message + "<br>file_size has been updated from '" + str(d.file_size) + "' to '" + str(file_size) + "'."
            d.file_size = file_size
            curator_session.add(d)

        ## update file_extension
        file_extension = request.params.get('file_extension')
        if file_extension is None:
            return HTTPBadRequest(body=json.dumps({'error': "file_extension field is blank"}), content_type='text/json')
        if file_extension != d.file_extension:
            success_message = success_message + "<br>file_extension has been updated from '" + str(d.file_extension) + "' to '" + file_extension + "'."
            d.file_extension = file_extension
            curator_session.add(d)

        ## update topic_id (required field)
        topic_id = request.params.get('topic_id')
        topic_id = int(topic_id)
        if topic_id != d.topic_id:
            success_message = success_message + "<br>topic_id has been updated from '" + str(d.topic_id) + "' to '" + str(topic_id) + "'."
            d.topic_id = topic_id
            
        ## update data_id (required field)
        data_id = request.params.get('data_id')
        data_id = int(data_id)
        if data_id != d.data_id:
            success_message = success_message + "<br>data_id has been updated from '" + str(d.data_id) + "' to '" + str(data_id) + "'."
            d.data_id = data_id
            
        ## update format_id (required field)
        format_id = request.params.get('format_id')
        format_id = int(format_id)
        if format_id != d.format_id:
            success_message = success_message + "<br>format_id has been updated from '" + str(d.format_id) + "' to '" + str(format_id) + "'."
            d.format_id = format_id
            
        ## update is_public (required field)
        is_public = request.params.get('is_public', '')
        if is_public == '':
            return HTTPBadRequest(body=json.dumps({'error': "is_public field is blank"}), content_type='text/json')
        is_public = True if is_public == 'true' else False
        if is_public != d.is_public:
            success_message = success_message + "<br>is_public has been updated from '" + str(d.is_public) + "' to '" + str(is_public) + "'."
            d.is_public = is_public
            
        ## update is_in_spell (required field)
        is_in_spell = request.params.get('is_in_spell', '')
        if is_in_spell == '':
            return HTTPBadRequest(body=json.dumps({'error': "is_in_spell field is blank"}), content_type='text/json')
        is_in_spell = True if is_in_spell == 'true' else False
        if is_in_spell != d.is_in_spell:
            success_message = success_message + "<br>is_in_spell has been updated from '" + str(d.is_in_spell) + "' to '" + str(is_in_spell) + "'."
            d.is_in_spell = is_in_spell

        ## update is_in_browser (required field)
        is_in_browser = request.params.get('is_in_browser', '')
        if is_in_browser == '':
            return HTTPBadRequest(body=json.dumps({'error': "is_in_browser field is blank"}), content_type='text/json')
        is_in_browser = True if is_in_browser == 'true' else False
        if is_in_browser != d.is_in_browser:
            success_message = success_message + "<br>is_in_browser has been updated from '" + str(d.is_in_browser) + "' to '" + str(is_in_browser) + "'."
            d.is_in_browser = is_in_browser
        
        ## update file_date (required field)  
        file_date = request.params.get('file_date', '')
        if file_date == '':
            return HTTPBadRequest(body=json.dumps({'error': "file_date field is blank"}), content_type='text/json')
        if '-' not in file_date:
            return HTTPBadRequest(body=json.dumps({'error': "file_date format: yyyy-mm-dd"}), content_type='text/json')
        file_date_db = str(d.file_date).split(' ')[0]
        if file_date != file_date_db:    
            success_message = success_message + "<br>file_date has been updated from '" + file_date_db + "' to '" + file_date + "'."
            d.file_date = file_date
            
        ## update readme_file_id (optional field)
        readme_file_id = request.params.get('readme_file_id')
        if str(readme_file_id).isdigit():
            if str(readme_file_id) != str(d.readme_file_id):
                d.readme_file_id = int(readme_file_id)
                curator_session.add(d)
                success_message = success_message + "<br>readme_file_id has been set to " + str(readme_file_id) + " for this file."
        else:
            if d.readme_file_id:
                d.readme_file_id = None
                curator_session.add(d)
                success_message = success_message + "<br>readme_file_id has been removed from this file."
                
        ## update path_id (path) (optional field)
        path_id = request.params.get('path_id')
        fp = curator_session.query(FilePath).filter_by(file_id=file_id).one_or_none()
        if str(path_id).isdigit():
            if fp is None:
                insert_file_path(curator_session, CREATED_BY, source_id, file_id, int(path_id))
                success_message = success_message + "<br>path_id has been added for this file."
            elif fp.path_id != int(path_id):
                success_message = success_message + "<br>path_id has been updated from '" + str(fp.path_id) + "' to '" + str(path_id) + "'."
                fp.path_id = int(path_id)
                curator_session.add(fp)
        elif fp is not None:
            success_message = success_message + "<br>path_id has been removed from this file."
            curator_session.delete(fp)

        ## update reference(s)
        all_refs = curator_session.query(ReferenceFile).filter_by(file_id=file_id).all()
        references_db = {}
        for ref in all_refs:
            references_db[ref.file_type + ":" + str(ref.reference.pmid)] = ref.reference.dbentity_id
            
        pmids =	request.params.get('pmids', '')
        pmid_list = pmids.split('|')
        for type_pmid in pmid_list:
            type_pmid = type_pmid.replace(' ', '')
            if type_pmid == '':
                continue
            [file_type, pmid] = type_pmid.split(':')
            if type_pmid in references_db:
                del references_db[type_pmid]
                continue
            ref = curator_session.query(Referencedbentity).filter_by(pmid=int(pmid)).one_or_none()
            if ref is None:
                return HTTPBadRequest(body=json.dumps({'error': "The PMID: " + pmid + " is not in th\
e database."}), content_type='text/json')
            reference_id = ref.dbentity_id
            insert_reference_file(curator_session, CREATED_BY, source_id, file_id,
                                  reference_id, file_type)
            success_message = success_message + "<br>PMID '" + pmid + "' has been added to this file."
            
        for type_pmid in references_db:
            reference_id = references_db[type_pmid]
            [file_type, pmid] = type_pmid.split(':')
            rf = curator_session.query(ReferenceFile).filter_by(file_id=file_id, reference_id=reference_id, file_type=file_type).one_or_none()
            if rf:
                success_message = success_message + "<br>PMID '" + str(pmid) + "' has been removed from this file."
                curator_session.delete(rf)

        
        ## update keyword(s) for file_keyword table
        all_file_kw = curator_session.query(FileKeyword).filter_by(file_id=file_id).all()
        keywords_file_db = {}
        for kw in all_file_kw:
            keywords_file_db[kw.keyword.display_name.upper()] = kw.keyword_id
        keywords = request.params.get('keywords', '')
        kw_list = keywords.split('|')
        for kw in kw_list:
            kw = kw.strip()
            if kw == '':
                continue
            if kw.upper() in keywords_file_db:
                del keywords_file_db[kw.upper()]
                continue
            keyword_id = insert_keyword(curator_session, CREATED_BY, source_id, kw)
            if str(keyword_id).isdigit():
                success_message = success_message + "<br>keyword '" + kw + "' has been added for this file."
                insert_file_keyword(curator_session, CREATED_BY, source_id, file_id, keyword_id)
            else:
                err_msg = keyword_id 
                return HTTPBadRequest(body=json.dumps({'error': err_msg}), content_type='text/json')
    
        for kw in keywords_file_db:
            keyword_id = keywords_file_db[kw]
            fk = curator_session.query(FileKeyword).filter_by(file_id=file_id, keyword_id=keyword_id).one_or_none()
            if fk:
                success_message = success_message + "<br>keyword '" + kw + "' has been removed from this file."
                curator_session.delete(fk)

        ## update keyword(s) for dataset_keyword table
        all_df = curator_session.query(DatasetFile).filter_by(file_id=file_id).all()
        for x in all_df:
            all_dataset_kw = curator_session.query(DatasetKeyword).filter_by(dataset_id=x.dataset_id).all()
            keywords_dataset_db = {}
            for kw in all_dataset_kw:
                keywords_dataset_db[kw.keyword.display_name.upper()] = kw.keyword_id
            for kw in kw_list:
                kw = kw.strip()
                if kw == '':
                    continue
                if kw.upper() in keywords_dataset_db:
                    del keywords_dataset_db[kw.upper()]
                    continue
                keyword_id = insert_keyword(curator_session, CREATED_BY, source_id, kw)
                if str(keyword_id).isdigit():
                    success_message = success_message + "<br>keyword '" + kw + "' has been added for the associated dataset."
                    insert_dataset_keyword(curator_session, CREATED_BY, source_id, x.dataset_id, keyword_id)
                else:
                    err_msg = keyword_id
                    return HTTPBadRequest(body=json.dumps({'error': err_msg}), content_type='text/json')

            for kw in keywords_dataset_db:
                keyword_id = keywords_dataset_db[kw]
                fk = curator_session.query(DatasetKeyword).filter_by(dataset_id=x.dataset_id, keyword_id=keyword_id).one_or_none()
                if fk:
                    success_message = success_message + "<br>keyword '" + kw + "' has been removed from the associated dataset."
                    curator_session.delete(fk)

                    
        if success_message == '':
            success_message = "Nothing changed"
            
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'metadata': "METADATA"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()

def delete_metadata(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])

        sgdid = request.params.get('sgdid')
        if sgdid == '':
            return HTTPBadRequest(body=json.dumps({'error': "No SGDID is passed in."}), content_type='text/json')

        d = curator_session.query(Filedbentity).filter_by(sgdid=sgdid).one_or_none()

        if d is None:
            return HTTPBadRequest(body=json.dumps({'error': "The SGDID " + sgdid + " is not in the database."}), content_type='text/json')

        file_id = d.dbentity_id

        ## reference_file
        refFiles = curator_session.query(ReferenceFile).filter_by(file_id=file_id).all()
        for x in refFiles:
            curator_session.delete(x)
            
        ## dataset_file
        dsFiles = curator_session.query(DatasetFile).filter_by(file_id=file_id).all() 
        for x in dsFiles:
            curator_session.delete(x)
            
        ## file_path
        fpaths = curator_session.query(FilePath).filter_by(file_id=file_id).all()
        for x in fpaths:
            curator_session.delete(x)
        
        ## file_keyword
        fkws = curator_session.query(FileKeyword).filter_by(file_id=file_id).all()
        for x in fkws:
            curator_session.delete(x)
            
        ## filedbentity
        fd = curator_session.query(Filedbentity).filter_by(dbentity_id=file_id).one_or_none()
        if fd is not None:
            curator_session.delete(fd)
            
        ## dbentity
        d = curator_session.query(Dbentity).filter_by(dbentity_id=file_id).one_or_none()
        if d is not None:
            curator_session.delete(d)

        success_message = "The file along with the metadata has been deleted from database." 
            
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'metadata': "METADATA"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()

        
    
    
