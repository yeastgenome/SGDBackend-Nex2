import csv
import os
import json

from loading.load_summaries_sync import load_summaries
from helpers import upload_file

# takes a TSV file and returns an array of annotations
def parse_tsv_annotations(db_session, tsv_file, filename, template_type, username):
    raw_file_content = csv.reader(tsv_file, delimiter='\t')
    annotations = load_summaries(db_session, raw_file_content, username)
    upload_file(
    	username, tsv_file,
    	filename=filename,
    	data_id=248375,
        description='summary upload',
        display_name=filename,
        format_id=248824,
        format_name='TSV',
        file_extension='tsv',
        json=json.dumps(annotations),
		topic_id=250482
    )
    return annotations
