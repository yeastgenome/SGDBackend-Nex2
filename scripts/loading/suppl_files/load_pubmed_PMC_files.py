from src.helpers import upload_file
from src.boto3_upload import upload_one_file_to_s3
from scripts.loading.database_session import get_session
from src.models import Dbentity, Filedbentity, Referencedbentity, Edam,\
    FilePath, Path, ReferenceFile, Source
from datetime import datetime
import logging
import os
import sys
import gzip
import logging

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

supplFileDir = "scripts/loading/suppl_files/pubmed_pmc_download/"

def load_data():
    
    nex_session = get_session()

    log.info(datetime.now())
    log.info("Getting data from database...")
    
    edam_to_id = dict([(x.format_name, x.edam_id) for x in nex_session.query(Edam).all()])
    src = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = src.source_id
    pmid_to_reference_id_year = dict([(x.pmid, (x.dbentity_id, x.year)) for x in nex_session.query(Referencedbentity).filter(Referencedbentity.pmid.isnot(None)).all()])
    filename_to_file_id = dict([(x.previous_file_name, x.dbentity_id) for x in nex_session.query(Filedbentity).filter_by(description='PubMed Central download').all()])
    
    log.info(datetime.now())
    log.info("Uploading files to s3...")

    i = 0
    for suppl_file in os.listdir(supplFileDir):
        i += 1
        pmid = int(suppl_file.replace('.tar.gz', ''))
        if pmid in pmid_to_reference_id_year:
            (reference_id, year) = pmid_to_reference_id_year[pmid]
            if suppl_file in filename_to_file_id:
                log.info(suppl_file + " is already in the database.")
            else:
                update_database_load_file_to_s3(nex_session, i, suppl_file, source_id, edam_to_id, year, reference_id)
        else:
            log.info("PMID:" + str(pmid) + " is not in the database.")

    nex_session.close()

    log.info(datetime.now())
    log.info("Done!")

    
def update_database_load_file_to_s3(nex_session, count, suppl_file_name, source_id, edam_to_id, year, reference_id):

    suppl_file_with_path = supplFileDir + suppl_file_name
    local_file = open(suppl_file_with_path, mode='rb')

    import hashlib
    md5sum = hashlib.md5(suppl_file_with_path.encode()).hexdigest()
    row = nex_session.query(Filedbentity).filter_by(md5sum=md5sum).one_or_none()

    if row is not None:
        return

    row = nex_session.query(Dbentity).filter(Dbentity.display_name == suppl_file_name).all()
    if len(row) > 0:
        return 

    data_id = edam_to_id.get('EDAM:2526')  
    topic_id = edam_to_id.get('EDAM:3070') 
    format_id = edam_to_id.get('EDAM:2330')

    from sqlalchemy import create_engine
    from src.models import DBSession
    engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
    DBSession.configure(bind=engine)
        
    upload_file(CREATED_BY, local_file,
                filename=suppl_file_name,
                file_extension='gz',
                description='PubMed Central download',
                display_name=suppl_file_name,
                year=year,
                data_id=data_id,
                format_id=format_id,
                topic_id=topic_id,
                status='Active',
                is_public=True,
                is_in_spell=False,
                is_in_browser=False,
                file_date=datetime.now(),
                source_id=source_id,
                md5sum=md5sum)

    row = nex_session.query(Dbentity).filter_by(display_name=suppl_file_name, dbentity_status='Active').one_or_none()
    if row is None:
        log.info("The " + suppl_file_name + " is not in the database.")
        return
    file_id = row.dbentity_id

    path = nex_session.query(Path).filter_by(
        path="/supplemental_data").one_or_none()
    if path is None:
        log.info("The path /supplemental_data is not in the database.")
        return
    path_id = path.path_id

    x = FilePath(file_id=file_id,
                 path_id=path_id,
                 source_id=source_id,
                 created_by=CREATED_BY)
    
    nex_session.add(x)

    x = ReferenceFile(file_id=file_id,
                      reference_id=reference_id,
                      file_type='Supplemental',
                      source_id=source_id,
                      created_by=CREATED_BY)
    nex_session.add(x)
        
    nex_session.commit()

    log.info(str(count) + " done uploading " + suppl_file_name)


if __name__ == '__main__':

    load_data()
