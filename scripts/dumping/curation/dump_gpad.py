from src.helpers import upload_file
from scripts.loading.database_session import get_session
from src.models import Dbentity, Locusdbentity, Referencedbentity, Taxonomy, \
    Go, Ro, Eco, EcoAlias, Source, Goannotation, Goextension, \
    Gosupportingevidence, LocusAlias, Edam, Path, FilePath, \
    Filedbentity, ReferenceAlias, Dnasequenceannotation, So
from urllib.request import urlretrieve
from urllib.request import urlopen
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

gpad_file = "scripts/dumping/curation/data/gpad.sgd"

# TAXON = 'NCBITaxon:559292'

def dump_data():

    nex_session = get_session()

    fw = open(gpad_file, "w")

    datestamp = str(datetime.now()).split(" ")[0].replace("-", "")

    write_header(fw, datestamp)

    log.info(str(datetime.now()))
    log.info("Getting data from the database...")

    id_to_source = dict([(x.source_id, x.display_name) for x in nex_session.query(Source).all()])
    ro_id_to_roid = dict([(x.ro_id, x.roid) for x in nex_session.query(Ro).all()])
    display_name_to_roid = dict([(x.display_name, x.roid) for x in nex_session.query(Ro).all()])
    dbentity_id_to_sgdid = dict([(x.dbentity_id, x.sgdid) for x in nex_session.query(Dbentity).filter_by(subclass='LOCUS').all()])
    reference_id_to_pmid = dict([(x.dbentity_id, x.pmid) for x in nex_session.query(Referencedbentity).all()])
    go_id_to_goid = dict([(x.go_id, (x.goid, x.go_namespace)) for x in nex_session.query(Go).all()])
    eco_id_to_ecoid = dict([(x.eco_id, x.format_name) for x in nex_session.query(Eco).all()])
    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()])
    edam_to_id = dict([(x.format_name, x.edam_id) for x in nex_session.query(Edam).all()])
    
    annotation_id_to_supportingevidencs = {}
    for x in nex_session.query(Gosupportingevidence).all():
        if x.annotation_id in annotation_id_to_supportingevidencs:
            annotation_id_to_supportingevidencs[x.annotation_id] = annotation_id_to_supportingevidencs[x.annotation_id] + "|" + x.dbxref_id
        else:
            annotation_id_to_supportingevidencs[x.annotation_id] = x.dbxref_id

    annotation_id_to_extensions = {}
    for x in nex_session.query(Goextension).all():
        if x.annotation_id in annotation_id_to_extensions:
            annotation_id_to_extensions[x.annotation_id] = annotation_id_to_extensions[x.annotation_id] + "|" + ro_id_to_roid[x.ro_id] + "(" + x.dbxref_id + ")"
        else:
            annotation_id_to_extensions[x.annotation_id] = ro_id_to_roid[x.ro_id] + "(" + x.dbxref_id + ")"

    reference_id_to_GO_REF = {}
    for x in nex_session.query(ReferenceAlias).all():
        if x.display_name.startswith('GO_REF:'):
            reference_id_to_GO_REF[x.reference_id] = x.display_name

    curator_to_orcid_mapping = get_curator_to_orcid_mapping()
    
    for x in nex_session.query(Goannotation).all():
        
        # col1: database ID
        col1 = "SGD:" + dbentity_id_to_sgdid.get(x.dbentity_id)
        
        # col2: Negation
        col2 = ''
        if x.go_qualifier == 'NOT':
            col2 = 'NOT'
        
        # col3: Relation
        (goid, aspect) = go_id_to_goid.get(x.go_id)
        go_qualifier = x.go_qualifier.replace('acts upstream of or within ', 'acts upstream of or within, ')
        if go_qualifier == 'NOT':
            if aspect == 'cellular component':
                go_qualifier = 'part of'
            elif aspect == 'biological process':
                go_qualifier = 'involved in'
            else:
                go_qualifier = 'enables'
        col3 = display_name_to_roid.get(go_qualifier)
        if col3 is None:
            log.info("Warning: NO ROID for go_qualifier: " + x.go_qualifier)
            continue

        # col4: GOID
        col4 = goid

        # col5: REFERENCE
        pmid = reference_id_to_pmid.get(x.reference_id)
        col5 = ''
        if pmid is not None:
            col5 = "PMID:" + str(pmid)
        elif x.reference_id in reference_id_to_GO_REF:
            col5 = reference_id_to_GO_REF[x.reference_id]
        else:
            ref = nex_session.query(Dbentity).filter_by(dbentity_id = x.reference_id).one_or_none()
            col5 = "REF:" + "SGD:" + ref.sgdid

        # col6: Evidence_type
        col6 = eco_id_to_ecoid.get(x.eco_id, '')
        
        # col7: With_or_From
        col7 = annotation_id_to_supportingevidencs.get(x.annotation_id, '')

        # col8: TAXON ID
        col8 = ""

        # col9: date generated
        col9 = str(x.date_created).split(' ')[0]

        # col10: source
        col10 = id_to_source.get(x.source_id, '')

        # col11: go extensions
        col11 = annotation_id_to_extensions.get(x.annotation_id, '')

        # col12: annotation properties
        created_by = curator_to_orcid_mapping.get(x.created_by)
        col12 = ''
        if created_by is None:
            col12 = 'id=' + str(x.annotation_id)
        else:
            col12 = "contributor-id=" + created_by + '|id=' + str(x.annotation_id)
        
        fw.write(col1 + "\t" + col2 + "\t" + col3 + "\t" + col4 + "\t" + col5 + "\t" + col6 + "\t" + col7 + "\t" + col8 + "\t" + col9 + "\t" + col10 + "\t" + col11 + "\t" + col12 + "\n")
        
    fw.close()
   
    log.info("Uploading GPAD file to S3...")

    update_database_load_file_to_s3(nex_session, gpad_file, source_to_id, edam_to_id, datestamp)

    nex_session.close()

    log.info(str(datetime.now()))
    log.info("Done!")

    
def write_header(fw, datestamp):

    fw.write("!gpa-version: 2.0\n")
    fw.write("!date-generated: " + datestamp + "\n")
    fw.write("!generated-by: Saccharomyces Genome Database (SGD)\n")
    fw.write("!URL: https://www.yeastgenome.org/\n")
    fw.write("!Contact Email: sgd-helpdesk@lists.stanford.edu\n")
    fw.write("!Funding: NHGRI at US NIH, grant number U41-HG001315\n")
    fw.write("!\n")

def get_curator_to_orcid_mapping():

    return { 'FISK'       : 'https://orcid.org/0000-0003-4929-9472',
             'JULIEP'     : 'GOC:jp',
             'STACIA'     : 'https://orcid.org/0000-0001-5472-917X', 
             'PLLOYD'     : 'https://orcid.org/0000-0003-3508-5553',
             'RAMA'       : 'https://orcid.org/0000-0003-2468-9933',
             'DWIGHT'     : 'https://orcid.org/0000-0002-8546-7798',
             'MAREK'      : 'https://orcid.org/0000-0001-6749-615X',
             'JDEMETER'   : 'https://orcid.org/0000-0002-7301-8055',
             'MIDORI'     : 'https://orcid.org/0000-0003-4148-4606',
             'EDITH'      : 'https://orcid.org/0000-0001-9799-5523',
             'PCNG'       : 'https://orcid.org/0000-0001-8208-652X',
             'CINDY'      : 'GOC:cjk',
             'KARA'       : 'https://orcid.org/0000-0002-7010-0264',
             'DIANE'      : 'https://orcid.org/0000-0003-3166-4638',
             'JOANNA'     : 'https://orcid.org/0000-0003-2678-2824',
             'JODI'       : 'GOC:jh',
             'SUZIA'      : 'https://orcid.org/0000-0001-6787-2901',
             'KCHRIS'     : 'https://orcid.org/0000-0001-5501-853X',
             'NASH'       : 'https://orcid.org/0000-0002-3726-7441',
             'KMACPHER'   : 'https://orcid.org/0000-0002-2657-8762',
             'MICHEAL'    : 'https://orcid.org/0000-0003-3841-4324',
             'MARIA'      : 'https://orcid.org/0000-0001-9043-693X',
             'ROSE'       : 'https://orcid.org/0000-0002-6475-3373',
             'EURIE'      : 'https://orcid.org/0000-0002-1775-4998',
             'TLJ'        : 'https://orcid.org/0000-0003-2387-6411',
             'CHANDRA'    : 'https://orcid.org/0000-0002-8379-6600',
             'ANAND'      : 'GOC:as'
    }

def update_database_load_file_to_s3(nex_session, gpad_file, source_to_id, edam_to_id, datestamp):

    gzip_file = gpad_file + "." + datestamp + ".gz"
    import gzip
    import shutil
    with open(gpad_file, 'rb') as f_in, gzip.open(gzip_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    local_file = open(gzip_file, mode='rb')

    # print ("uploading file to latest...")
    
    ### upload a current GPAD file to S3 with a static URL for Go Community ###
    # upload_file_to_s3(local_file, "latest/gpad.sgd.gz")
    ##########################################################################

    # print ("uploading file to s3 sgdid system...")
    
    import hashlib
    gpad_md5sum = hashlib.md5(gzip_file.encode()).hexdigest()
    row = nex_session.query(Filedbentity).filter_by(md5sum=gpad_md5sum).one_or_none()

    if row is not None:
        return

    gzip_file = gzip_file.replace("scripts/dumping/curation/data/", "")


    nex_session.query(Dbentity).filter(Dbentity.display_name.like('gpad.sgd%')).filter(
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
        display_name="gpad.sgd.README", dbentity_status='Active').one_or_none()
    readme_file_id = None
    if readme is not None:
        readme_file_id = readme.dbentity_id

    # path.path = /reports/function 

    upload_file(CREATED_BY, local_file,
                filename=gzip_file,
                file_extension='gz',
                description='All GO annotations for yeast genes (protein and RNA) in GPAD file format',
                display_name=gzip_file,
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
                md5sum=gpad_md5sum)

    gpad = nex_session.query(Dbentity).filter_by(
        display_name=gzip_file, dbentity_status='Active').one_or_none()
    if gpad is None:
        log.info("The " + gzip_file + " is not in the database.")
        return
    file_id = gpad.dbentity_id

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

    log.info("Done uploading " + gpad_file)

    
if __name__ == '__main__':

    dump_data()
