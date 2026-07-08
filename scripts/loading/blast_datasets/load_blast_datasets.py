from src.helpers import upload_file
from src.boto3_upload import upload_one_file_to_s3
from scripts.loading.database_session import get_session
from src.models import Dbentity, Source, Edam, Filedbentity, Path, FilePath
from datetime import datetime
import os
import sys
import gzip

__author__ = 'sweng66'

infile = "scripts/loading/blast_datasets/data/blast_database_metadata.txt"
dataDir = "scripts/loading/blast_datasets/data/blast_datasets_for_alliance/"

CREATED_BY = os.environ['DEFAULT_USER']

def load_data():

    nex_session = get_session()

    datestamp = str(datetime.now()).split(" ")[0].replace("-", "")
    
    source = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = source.source_id
    
    edam_to_id = dict([(x.format_name, x.edam_id)
                       for x in nex_session.query(Edam).all()])

    f = open(infile)
    for line in f:
        pieces = line.strip().split('\t')
        print ("uploading pieces[0] to s3")
        update_database_load_file_to_s3(nex_session, pieces[0], pieces[1], source_id, edam_to_id, datestamp)
        
    nex_session.close()

    
def update_database_load_file_to_s3(nex_session, dataset_filename, desc, source_id, edam_to_id, datestamp):

    desc = "BLAST: " + desc
    
    dataset_file = dataDir + dataset_filename
    gzip_file = dataset_file + "." + datestamp + ".gz"
    import gzip
    import shutil
    with open(dataset_file, 'rb') as f_in, gzip.open(gzip_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    local_file = open(gzip_file, mode='rb')

    import hashlib
    md5sum = hashlib.md5(gzip_file.encode()).hexdigest()
    row = nex_session.query(Filedbentity).filter_by(md5sum=md5sum).one_or_none()

    if row is not None:
        return

    gzip_file = dataset_filename + "." + datestamp + ".gz"

    nex_session.query(Dbentity).filter(Dbentity.display_name.like(dataset_filename+'%')).filter(Dbentity.dbentity_status == 'Active').update({"dbentity_status": 'Archived'}, synchronize_session='fetch')
    nex_session.commit()

    data_id = edam_to_id.get('EDAM:0849')  # data:0849 Sequence record
    topic_id = edam_to_id.get('EDAM:0160')  # topic:0160 Sequence sites, features and motifs
    format_id = edam_to_id.get('EDAM:1332')  # format:1332 FASTA search results format

    from sqlalchemy import create_engine
    from src.models import DBSession
    engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
    DBSession.configure(bind=engine)

    upload_file(CREATED_BY, local_file,
                filename=dataset_filename + ".gz",
                file_extension='gz',
                description=desc,
                display_name=gzip_file,
                data_id=data_id,
                format_id=format_id,
                topic_id=topic_id,
                status='Active',
                readme_file_id=None,
                is_public=True,
                is_in_spell=False,
                is_in_browser=False,
                file_date=datetime.now(),
                source_id=source_id,
                md5sum=md5sum)

    row = nex_session.query(Dbentity).filter_by(
        display_name=gzip_file, dbentity_status='Active').one_or_none()
    if row is None:
        log.info("The " + gzip_file + " is not in the database.")
        return
    file_id = row.dbentity_id

    path = nex_session.query(Path).filter_by(
        path="/datasets").one_or_none()
    if path is None:
        log.info("The path datasets is not in the database.")
        return
    path_id = path.path_id

    x = FilePath(file_id=file_id,
                 path_id=path_id,
                 source_id=source_id,
                 created_by=CREATED_BY)

    nex_session.add(x)
    nex_session.commit()

    print ("Done uploading " + dataset_filename)


if __name__ == "__main__":
        
    load_data()
