import logging
import os
import datetime
from sqlalchemy import or_
from pyramid.httpexceptions import HTTPBadRequest, HTTPOk
from sqlalchemy.exc import IntegrityError, DataError
import transaction
import json
from src.models import DBSession, Dbentity, Filedbentity, Referencedbentity, FilePath, \
                       Path, ReferenceFile, Source, Edam
from src.aws_helpers import get_checksum
from src.aws_helpers import upload_file_to_s3
from src.curation_helpers import get_curator_session

# PREVIEW_URL = os.environ['PREVIEW_URL']

log = logging.getLogger('curation')

FILE_TYPE = 'Supplemental'
DESC = 'Supplemental Materials'
PATH = '/supplemental_data'
FILE_EXTENSION = 'zip'
DBENTITY_STATUS = 'Active'
IS_PUBLIC = True
IS_IN_SPELL = False
IS_IN_BROWSER = False


def insert_reference_file(curator_session, CREATED_BY, source_id, file_id, reference_id):

    try:
        x = ReferenceFile(file_id = file_id,
                          reference_id = reference_id,
                          file_type = FILE_TYPE,
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

                
def upload_one_file(request, curator_session, CREATED_BY, source_id, file, filename, md5sum, file_date, topic_id, data_id, format_id, reference_id, year):

    try:
        #### add metadata to database
        log.debug('before fd assignment')
        fd = Filedbentity(created_by=CREATED_BY,
                          display_name=filename,
                          format_name=filename,
                          subclass='FILE',
                          previous_file_name=filename,
                          file_extension=FILE_EXTENSION,
                          json=None,
                          s3_url=None,
                          dbentity_status=DBENTITY_STATUS,
                          year=year,
                          file_date=file_date,
                          description=DESC,
                          data_id=data_id,
                          format_id=format_id,
                          topic_id=topic_id,
                          is_public=IS_PUBLIC,
                          is_in_spell=IS_IN_SPELL,
                          is_in_browser=IS_IN_BROWSER,
                          readme_file_id=None,
                          source_id=source_id,
                          md5sum=md5sum)
        log.debug('after fd assignment; before add')
        curator_session.add(fd)
        log.debug('after add; before flush')
        curator_session.flush()
        log.debug('after flush; before file_id')
        file_id = fd.dbentity_id
        log.debug('after file_id; before commit')
        transaction.commit()
        log.debug('after commit; before flush')
        curator_session.flush()
        log.debug('after flush')

        log.debug('before fd')
        fd = curator_session.query(Filedbentity).filter_by(dbentity_id=file_id).one_or_none()
        log.debug('after fd')
                
        #### upload file to s3
        s3_url = upload_file_to_s3(file, fd.sgdid + "/" + filename)
        log.debug('after s3_url; before fd.s3_url')
        fd.s3_url = s3_url
        log.debug('after fd.s3_url; before add')
        curator_session.add(fd)
        log.debug('after add; before commit')
        transaction.commit()
        log.debug('after commit')
        
        #### add path_id and newly created file_id to file_path table
        log.debug('before path')
        path = curator_session.query(Path).filter_by(path=PATH).one_or_none()
        log.debug('path is ' + str(path))
        if path is None:
            return "Path = " + PATH + " is not in the database"
        log.debug('after path check; path is not None; before insert_file_path')
        insert_file_path(curator_session, CREATED_BY, source_id, file_id, path.path_id)
        log.debug('after insert_file_path')
            
        #### add reference_id to this file
        log.debug('before insert_reference_file')
        insert_reference_file(curator_session, CREATED_BY, source_id, file_id, reference_id)
        log.debug('after insert_reference_file')
        
        log,debug('before commit')
        transaction.commit()
        log.debug('after commit')
        
        log.debug('before return')
        return "loaded"
    
    except Exception as e:
        log.exception('Upload supplemental file ERROR')
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()
        
def add_metadata_upload_file(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        sgd = DBSession.query(Source).filter_by(display_name='SGD').one_or_none()
        source_id = sgd.source_id
       
        from datetime import datetime
        date = str(datetime.now()).split(' ')[0]
    
        topic = DBSession.query(Edam).filter_by(display_name='Biology').one_or_none()
        if topic is None:
            return HTTPBadRequest(body=json.dumps({'error': "EDAM term: 'Biology' is not in the database."}), content_type='text/json')
        topic_id = topic.edam_id
        data = DBSession.query(Edam).filter_by(display_name='Text data').one_or_none()
        if data is None:
            return HTTPBadRequest(body=json.dumps({'error': "EDAM term: 'Text data' is not in the database."}), content_type='text/json')
        data_id = data.edam_id
        format = DBSession.query(Edam).filter_by(display_name='Textual format').one_or_none()
        if format is None:
            return HTTPBadRequest(body=json.dumps({'error': "EDAM term: 'Textual format' is not in the database."}), content_type='text/json')
        format_id = format.edam_id

        fileObj = request.params.get('file')
            
        file = None
        filename = None
        if fileObj != '':
            file = fileObj.file
            filename = fileObj.filename

        success_message = ""
        if filename:                
            md5sum = get_checksum(file)
            fd = DBSession.query(Filedbentity).filter_by(md5sum=md5sum).one_or_none()
            if fd is not None:
                success_message = success_message + "<br>"+ filename + " is already in the database"
            else:
                old_files = curator_session.query(Dbentity).filter_by(subclass='FILE', display_name=filename).all()

                ## a new version of the file   
                for old_file in old_files:

                    ## update dbentity_status to 'Archived' for old version
                    old_file.dbentity_status = 'Archived'
                    curator_session.add(old_file)

                    ## unlink old version with paper
                    all_rf = curator_session.query(ReferenceFile).filter_by(file_id=old_file.dbentity_id).all()
                    for x in all_rf:
                        curator_session.delete(x)
                    
                pmid = int(filename.replace('.zip', ''))

                ref = curator_session.query(Referencedbentity).filter_by(pmid=pmid).one_or_none()
                if ref is None:
                    success_message = success_message + "<br>" + filename + " is skipped since PMID = " + str(pmid) + " is not in the database"
                else:
                    reference_id = ref.dbentity_id
                    year = ref.year
                    if year is None:
                        success_message = success_message +	"<br>" + filename + " is skipped since no year found in the database for PMID = " + str(pmid) + "."
                    else:
                        msg = upload_one_file(request, curator_session, CREATED_BY, source_id, file,
                                              filename, md5sum, date, topic_id, data_id, format_id,
                                              reference_id, year)
                        if msg == "loaded":
                            if len(old_files) > 0:
                                success_message = success_message + "<br>" + filename + " is updated in s3."
                            else:
                                success_message = success_message + "<br>" + filename + " is uploaded to s3."
                        else:
                            return msg
                
        if success_message == '':
            success_message = "No file loaded"

        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'supplemental_files': "SUPPLEMENTAL_FILE"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type='text/json')
    finally:
        if curator_session:
            curator_session.remove()
