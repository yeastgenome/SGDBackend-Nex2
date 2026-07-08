from src.helpers import upload_file
from datetime import datetime
import logging
## import tarfile
import os
import sys
import json
from src.models import Referencedbentity, Locusdbentity, Literatureannotation, Source, Edam,\
     Filedbentity, Path, FilePath, Dbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

# Handlers need to be reset for use under Fargate. See
# https://stackoverflow.com/questions/37703609/using-python-logging-with-aws-lambda/56579088#56579088
# for details.  Applies to Fargate in addition to Lambda.

log = logging.getLogger()
if log.handlers:
    for handler in log.handlers:
        log.removeHandler(handler)

logging.basicConfig(
    format='%(message)s',
    handlers=[
        logging.FileHandler(os.environ['LOG_FILE']),
        logging.StreamHandler(sys.stderr)
    ],
    level=logging.INFO
)

CREATED_BY = os.environ['DEFAULT_USER']

datestamp = str(datetime.now()).split(" ")[0].replace("-", "")
datafile = "scripts/dumping/ncbi/data/gene2pmid.tab." + datestamp

obsolete_pmids = [25423496, 27651461, 28068213, 31088842]

def dump_data():

    nex_session = get_session()

    log.info(str(datetime.now()))
    log.info("Getting basic data from the database...")

    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()])
    edam_to_id = dict([(x.format_name, x.edam_id) for x in nex_session.query(Edam).all()])
    
    dbentity_id_to_gene = dict([(x.dbentity_id, x.systematic_name)
                                 for x in nex_session.query(Locusdbentity).all()])
    reference_id_to_pmid = dict([(x.dbentity_id, x.pmid)
                                 for x in nex_session.query(Referencedbentity).all()])

    fw = open(datafile, "w")

    gene_to_pmid_list = {}
    for x in nex_session.query(Literatureannotation).filter_by(topic='Primary Literature').order_by(Literatureannotation.dbentity_id, Literatureannotation.reference_id).all():
        if x.dbentity_id not in dbentity_id_to_gene:
            continue
        if x.reference_id not in reference_id_to_pmid or reference_id_to_pmid[x.reference_id] in obsolete_pmids:
            continue
        pmid = reference_id_to_pmid[x.reference_id]
        if pmid	is None:
            continue
        gene = dbentity_id_to_gene[x.dbentity_id]
        pmid_list = []
        if gene in gene_to_pmid_list:
            pmid_list = gene_to_pmid_list[gene]
        
        if pmid not in pmid_list:
            pmid_list.append(pmid)
            gene_to_pmid_list[gene] = pmid_list
        
    for gene in sorted (gene_to_pmid_list.keys()):
        pmids = gene_to_pmid_list[gene]
        pmids.sort()
        for pmid in pmids:
            fw.write(gene + "\t" + str(pmid) + "\t" + x.topic + "\n")
    fw.close()

    update_database_load_file_to_s3(nex_session, datafile, source_to_id, edam_to_id)

    nex_session.close()

    log.info(str(datetime.now()))
    log.info("Done!")

def update_database_load_file_to_s3(nex_session, datafile, source_to_id, edam_to_id):

    local_file = open(datafile, mode='rb')

    import hashlib
    md5sum = hashlib.md5(datafile.encode()).hexdigest()
    row = nex_session.query(Filedbentity).filter_by(md5sum=md5sum).one_or_none()

    if row is not None:
        return

    datafile = datafile.replace("scripts/dumping/ncbi/data/", "")

    nex_session.query(Dbentity).filter(Dbentity.display_name.like('gene2pmid.tab%')).filter(
        Dbentity.dbentity_status == 'Active').update({"dbentity_status": 'Archived'}, synchronize_session='fetch')
    nex_session.commit()

    data_id = edam_to_id.get('EDAM:2048')  # data:2048 Report
    topic_id = edam_to_id.get('EDAM:0085')  # topic:0085 Functional genomics
    format_id = edam_to_id.get('EDAM:3475')  # format:3475 TSV 

    from sqlalchemy import create_engine
    from src.models import DBSession
    engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
    DBSession.configure(bind=engine)

    readme = nex_session.query(Dbentity).filter_by(
        display_name="gene2pmid.README", dbentity_status='Active').one_or_none()
    readme_file_id = None
    if readme is not None:
        readme_file_id = readme.dbentity_id

    upload_file(CREATED_BY, local_file,
                filename=datafile,
                file_extension='.tab',
                description='mapping of all yeast genes to pubmed IDs.',
                display_name=datafile,
                data_id=data_id,
                format_id=format_id,
                topic_id=topic_id,
                status='Active',
                readme_file_id=readme_file_id,
                is_public=True,
                is_in_spell=False,
                is_in_browser=False,
                file_date=datetime.now(),
                source_id=source_to_id['SGD'],
                md5sum=md5sum)

    row = nex_session.query(Dbentity).filter_by(display_name=datafile, dbentity_status='Active').one_or_none()
    if row is None:
        log.info("The " + datafile + " is not in the database.")
        return
    file_id = row.dbentity_id

    path = nex_session.query(Path).filter_by(
        path="/reports/function").one_or_none()
    if path is None:
        log.info("The path /reports/function is not in the database.")
        return
    path_id = path.path_id

    x = FilePath(file_id=file_id,
                 path_id=path_id,
                 source_id=source_to_id['SGD'],
                 created_by=CREATED_BY)

    nex_session.add(x)
    nex_session.commit()

    log.info("Done uploading " + datafile)
            
if __name__ == '__main__':

    dump_data()
