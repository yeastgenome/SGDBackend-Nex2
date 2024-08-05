from scripts.loading.database_session import get_session
from src.models import Dbentity, Source, Edam, Filedbentity, Path, FilePath
from datetime import datetime
import transaction
import os
import sys

__author__ = 'sweng66'

infile = "scripts/dumping/tab_files_for_download_site/data/download_file_metadata.txt"
dataDir = "scripts/dumping/tab_files_for_download_site/data/"
s3_download_root_url = "https://sgd-prod-upload.s3.amazonaws.com/latest/"

CREATED_BY = os.environ['DEFAULT_USER']

def load_metadata():

    nex_session = get_session()
    
    source = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = source.source_id
    
    edam_to_id = dict([(x.format_name, x.edam_id)
                       for x in nex_session.query(Edam).all()])

    f = open(infile)
    for line in f:
        if line.startswith('File'):
            continue
        pieces = line.strip().split('\t')
        print("Loading metadata for file:", pieces[0])
        load_one_file_metadata(nex_session, pieces[0], pieces[1], pieces[3], pieces[5], source_id, edam_to_id)
    f.close()
    
    nex_session.close()

    
def load_one_file_metadata(nex_session, filename, topic_edam_id, data_edam_id, format_edam_id, source_id, edam_to_id):

    filename_with_path = dataDir + filename
    if not os.path.exists(filename_with_path):
        return
    
    data_id = edam_to_id.get(data_edam_id)
    topic_id = edam_to_id.get(topic_edam_id)
    format_id = edam_to_id.get(format_edam_id)

    if data_id is None or topic_id is None or format_id is None:
        print("Edam ID not found:", filename, data_edam_id, data_id, topic_edam_id, topic_id, format_edam_id, format_id)
        return

    s3_url = s3_download_root_url + filename
    
    import hashlib
    md5sum = hashlib.md5(filename_with_path.encode()).hexdigest()
    
    row = nex_session.query(Filedbentity).filter_by(md5sum=md5sum).one_or_none()

    if row is not None:
        print("The file:", filename, "is already in the database")
        return

    nex_session.query(Dbentity).filter(Dbentity.display_name.like(filename+'%')).filter(Dbentity.dbentity_status == 'Active').update({"dbentity_status": 'Archived'}, synchronize_session='fetch')
    nex_session.commit()

    """
    from sqlalchemy import create_engine
    from src.models import DBSession
    engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
    DBSession.configure(bind=engine)
    """
    
    file_extension = filename.split('.')[-1]
    file_size = os.path.getsize(filename_with_path)
    file_date = datetime.now()
    year = file_date.year
    
    try:
        fdb = Filedbentity(
            md5sum=md5sum,
            previous_file_name=filename,
            data_id=data_id,
            topic_id=topic_id,
            format_id=format_id,
            file_date=file_date,
            year=year,
            is_public=True,
            is_in_spell=False,
            is_in_browser=False,
            source_id=source_id,
            file_extension=file_extension,
            format_name=filename,
            display_name=filename,
            s3_url=s3_url,
            dbentity_status='Active',
            readme_file_id=None,
            subclass='FILE',
            created_by=CREATED_BY,
            file_size=file_size)
        nex_session.add(fdb)
        nex_session.flush()
        file_id = fdb.dbentity_id
        transaction.commit()
        nex_session.flush()

        path = nex_session.query(Path).filter_by(
            path="/reports").one_or_none()
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

        print("Done loading " + filename + " metadata.")
    except Exception as e:
        print("Loading " + filename + " metadata error: " + str(e))

    
if __name__ == "__main__":
        
    load_metadata()
