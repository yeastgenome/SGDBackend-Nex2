from scripts.loading.database_session import get_session
from src.models import Filedbentity
import os
from pathlib import Path
import hashlib
import urllib

__author__ = 'sweng66'

dataDir = "scripts/loading/blast_datasets/data/new_blast_datasets/"

db_session = get_session()

for x in db_session.query(Filedbentity).filter(Filedbentity.description.like('BLAST: %')).order_by(Filedbentity.dbentity_id).all():
    # print (x.previous_file_name, x.s3_url)
    file = dataDir + x.previous_file_name
    urllib.request.urlretrieve(x.s3_url, file)
    fasta_file = Path(str(file))
    md5sum = None
    with fasta_file.open(mode="rb") as fh:
        md5sum = hashlib.md5(fh.read()).hexdigest()
    # print (x.previous_file_name, md5sum)
    x.md5sum = md5sum
    db_session.add(x)
    db_session.commit()

db_session.close()


    
