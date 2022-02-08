from src.helpers import upload_file
from scripts.loading.database_session import get_session
from src.models import Locusdbentity, Dnasequenceannotation, Source, Edam, So, Go, Goslim,\
     Goslimannotation, Taxonomy, Filedbentity, Path, FilePath, Dbentity, Complexdbentity
from datetime import datetime
import logging
import os
import sys
import gzip
import importlib

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

datestamp = str(datetime.now()).split(" ")[0].replace("-", "")
datafile = "scripts/dumping/curation/data/go_slim_mapping.tab." + datestamp

TAXID = 'TAX:559292'

def dump_data():

    nex_session = get_session()
    
    log.info(str(datetime.now()))
    log.info("Getting data from the database...")

    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()])
    edam_to_id = dict([(x.format_name, x.edam_id) for x in nex_session.query(Edam).all()])

    dbentity_id_to_names = dict([(x.dbentity_id, (x.systematic_name, x.gene_name, x.sgdid, x.qualifier)) for x in nex_session.query(Locusdbentity).all()])
    dbentity_id_to_complex = dict([(x.dbentity_id, (x.format_name, x.display_name, x.sgdid)) for x in nex_session.query(Complexdbentity).all()])
    so_id_to_term_name = dict([(x.so_id, x.term_name) for x in nex_session.query(So).all()])
    taxonomy = nex_session.query(Taxonomy).filter_by(taxid = TAXID).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    dbentity_id_to_so_id = dict([(x.dbentity_id, x.so_id) for x in nex_session.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC', taxonomy_id=taxonomy_id).all()])
    goslim_id_to_go_id = dict([(x.goslim_id, x.go_id) for x in nex_session.query(Goslim).all()])
    go_id_to_term_goid_aspect = dict([(x.go_id, (x.display_name, x.goid, x.go_namespace)) for x in nex_session.query(Go).all()])

    data = []
    for x in nex_session.query(Goslimannotation).all():
        go_id = goslim_id_to_go_id[x.goslim_id]
        (go_term, goid, go_aspect) = go_id_to_term_goid_aspect[go_id]
        if go_aspect.endswith('function'):
            go_aspect = 'F'
        elif go_aspect.endswith('process'):
            go_aspect =     'P'
        else:
            go_aspect =     'C'
        if x.dbentity_id in dbentity_id_to_names:
            (systematic_name, gene_name, sgdid, qualifier) = dbentity_id_to_names.get(x.dbentity_id)
            so_id = dbentity_id_to_so_id.get(x.dbentity_id)
            if so_id is None:
                continue
            so_term = so_id_to_term_name[so_id]
            type = so_term
            if qualifier:
                type = so_term + "|" + qualifier
            if gene_name is None:
                gene_name = ''
            data.append(systematic_name + "\t" + gene_name + "\t" + sgdid + "\t" + go_aspect + "\t" + go_term + "\t" + goid + "\t" + type)
        elif x.dbentity_id in dbentity_id_to_complex:
            (complex_acc, complex_name, sgdid) = dbentity_id_to_complex.get(x.dbentity_id)
            type = 'protein complex'
            data.append(complex_acc + "\t" + complex_name + "\t" + sgdid + "\t" + go_aspect + "\t" + go_term + "\t" + goid + "\t" + type)
            
    data.sort()
    
    fw = open(datafile, 'w')    
    for line in data:
        fw.write(line + "\n")
    fw.close()

    log.info("Uploading go_slim_mapping to S3...")

    update_database_load_file_to_s3(nex_session, datafile, source_to_id, edam_to_id, datestamp)

    nex_session.close()

    log.info(str(datetime.now()))
    log.info("Done!")

def update_database_load_file_to_s3(nex_session, datafile, source_to_id, edam_to_id, datestamp):
    
    local_file = open(datafile, mode='rb')
        
    import hashlib
    md5sum = hashlib.md5(datafile.encode()).hexdigest()
    row = nex_session.query(Filedbentity).filter_by(md5sum=md5sum).one_or_none()

    if row is not None:
        return

    datafile = datafile.replace("scripts/dumping/curation/data/", "")

    nex_session.query(Dbentity).filter(Dbentity.display_name.like('go_slim_mapping.tab%')).filter(
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
        display_name="go_slim_mapping.README", dbentity_status='Active').one_or_none()
    readme_file_id = None
    if readme is not None:
        readme_file_id = readme.dbentity_id

    # path.path = /reports/function

    upload_file(CREATED_BY, local_file,
                filename=datafile,
                file_extension='.tab',
                description='mapping of all yeast gene products (protein or RNA) to a GO-Slim term.',
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
