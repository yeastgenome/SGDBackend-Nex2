import csv
import os
import json
from sqlalchemy.exc import IntegrityError
import traceback

from loading.load_summaries_sync import load_summaries, validate_file_content_and_process
from helpers import upload_file, file_upload_to_dict


# takes a TSV file and returns an array of annotations
def parse_tsv_annotations(db_session, file_upload, filename, template_type, username):
    db_session.execute('SET LOCAL ROLE ' + username)
    file_extension = ''
    try:
        if(filename.endswith('.tsv')):
            raw_file_content = csv.reader(file_upload, delimiter='\t', dialect=csv.excel_tab)
            file_extension = 'tsv'
        elif(filename.endswith('.txt')):
            raw_file_content = csv.reader(file_upload, delimiter='\t', dialect=csv.excel_tab)
            file_extension = 'txt'
        else:
            raise ValueError('File format not accepted. Please upload a valid TSV or Text file.')

        file_upload.seek(0)
    except:
        traceback.print_exc()
        db_session.close()
        raise ValueError('File format not accepted. Please upload a valid TSV or Text file.')

    try:
        upload_file(
                username, file_upload,
                filename=filename,
                data_id=248375,
                description='summary upload',
                display_name=filename,
                format_id=248824,
                format_name=file_extension.upper(),
                file_extension=file_extension,
                topic_id=250482)
    except IntegrityError:
        db_session.rollback()
        db_session.close()
        raise ValueError('That file has already been uploaded and cannot be reused. Please change the file contents and try again.')

    file_upload.seek(0)
    file_dict = file_upload_to_dict(file_upload)
    annotations = validate_file_content_and_process(file_dict, db_session, username)
    db_session.close()
    return annotations
