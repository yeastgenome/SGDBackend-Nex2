from datetime import datetime
import json
import logging
import csv
import sys
import transaction
import os
from sqlalchemy import create_engine, and_
from src.models import DBSession, Locussummary, LocussummaryReference, Locusdbentity, Referencedbentity, Source
                             
__author__ = 'tshepp'

'''
* validate file
* Read in the summary text for each gene from the upload file and compare the 
  text with the info in the memory.
  * The summary for this gene for the given type (eg, Regulation or Phenotype) 
    is not in the database,
       * insert the summay text into the LOCUSSUMMARY table
       * insert any associated reference(s) into LOCUSSUMMARY_REFERENCE table 
         (eg, for regulation summaries)
  * The summary for this gene for the given type is in the database.
       * if the summary text is updated, update the LOCUSSUMMARY.text/html; 
         otherwise noneed todo anything to theLOCUSSUMMARY table
       * check to see if there is any referenceupdate, if yes, updatethe 
         LOCUSSUMMARY_REFERENCE table
'''
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
# has correct columns in header
# checks IDs to make sure real IDs
def validate_file_content(file_content, nex_session):
    header_literal = ['# Feature', 'Summary Type (phenotype, regulation, protein, or sequence)', 'Summary', 'PMIDs']
    file_gene_ids = []
    copied = []
    for i, val in enumerate(file_content):
        # match header
        if i is 0:
            is_header_match = header_literal == val
            if not is_header_match:
                raise ValueError('File header does not match expected format.') 
        else:
            file_gene_ids.append(val[0])
        # match length of each row
        if len(val) != len(header_literal):
            raise ValueError('Row has incorrect number of columns.')
        copied.append(val)
    # check that gene names are valid
    matching_genes = nex_session.query(Locusdbentity).filter(Locusdbentity.format_name.in_(file_gene_ids)).count()
    is_correct_match_num = matching_genes == len(file_gene_ids)
    if not is_correct_match_num:
        raise ValueError('Invalid gene identifier in ', str(file_gene_ids))
    # update 
    for i, val in enumerate(copied):
        if i != 0:
            file_id = val[0]
            gene = nex_session.query(Locusdbentity).filter(Locusdbentity.format_name.match(file_id)).all()[0]
            summaries = DBSession.query(Locussummary.summary_id, Locussummary.html, Locussummary.date_created).filter_by(locus_id=gene.dbentity_id, summary_type='Gene').all()
            new_summary_val = val[2]
            # update
            if len(summaries):
                summary = summaries[0]
                nex_session.query(Locussummary).filter_by(summary_id=summary.summary_id).update({ 'text': new_summary_val, 'html': new_summary_val })
                # nex_session.query(summary.update({ 'text': new_summary_val, 'html': new_summary_val }))
            # TODO create
            # else:

def load_summaries(nex_session, file_content, username, summary_type=None):
    print str(enumerate(file_content))
    # print val
    # # update each gene summary
    # file_id = val[0]
    # gene = nex_session.query(Locusdbentity).filter(Locusdbentity.format_name.match(file_id))
    # print gene
    # summary = DBSession.query(Locussummary.summary_id, Locussummary.html, Locussummary.date_created).filter_by(locus_id=self.dbentity_id, summary_type="Gene").all()

    # nex_session.query(Locussummary).filter_by(summary_id=key_to_summary[key].summary_id).update({'text': x['text'], 'html': x['html']})
    annotation_summary = []
    return annotation_summary

if __name__ == '__main__':
    engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
    DBSession.configure(bind=engine)
    with open('test/example_files/example_summary_upload.tsv') as tsvfile:
        tsvreader = csv.reader(tsvfile, delimiter="\t")
        validate_file_content(tsvreader, DBSession)
