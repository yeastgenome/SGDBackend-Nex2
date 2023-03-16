from src.helpers import upload_file
from scripts.loading.database_session import get_session
from src.models import Dbentity, Locusdbentity, LocusAlias, Locussummary, \
                       Goannotation, Source, FilePath, Path, Complexdbentity,\
                       Taxonomy, Edam, Filedbentity, So, Dnasequenceannotation
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

gpi_file = "scripts/dumping/curation/data/gpi.sgd"

TAXON = 'taxon:559292'

TAXID = 'TAX:559292'

def dump_data():

    nex_session = get_session()

    fw = open(gpi_file, "w")

    datestamp = str(datetime.now()).split(" ")[0].replace("-", "")

    write_header(fw, datestamp)

    log.info(str(datetime.now()))
    log.info("Getting data from the database...")

    source = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = source.source_id
    dbentity_id_to_function = dict([(x.locus_id, x.text.replace("\n", ' ').strip()) for x in nex_session.query(Locussummary).filter_by(summary_type='Function').all()])
    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()])
    edam_to_id = dict([(x.format_name, x.edam_id) for x in nex_session.query(Edam).all()])
    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXID).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    so_id_to_type = dict([(x.so_id, x.display_name) for x in nex_session.query(So).all()])
    dbentity_id_to_alias_names = {}
    dbentity_id_to_ncbi_protein_name = {}
    dbentity_id_to_uniprot = {}
    dbentity_id_to_refseq_ids = {}
    for x in nex_session.query(LocusAlias).all():
        if x.alias_type == 'Uniform':
            alias_names = []
            if x.locus_id in dbentity_id_to_alias_names:
                alias_names = dbentity_id_to_alias_names[x.locus_id]
            alias_names.append(x.display_name)
            dbentity_id_to_alias_names[x.locus_id] = alias_names
        elif x.alias_type == 'NCBI protein name':
            dbentity_id_to_ncbi_protein_name[x.locus_id] = x.display_name
        elif x.alias_type == 'UniProtKB ID':
            dbentity_id_to_uniprot[x.locus_id] = "UniProtKB:" + x.display_name
        elif x.alias_type == 'RefSeq nucleotide version ID':
            refseq_ids = []
            if x.locus_id in dbentity_id_to_refseq_ids:
                refseq_ids = dbentity_id_to_refseq_ids[x.locus_id]
            refseq_ids.append("RefSeq:" + x.display_name)
            dbentity_id_to_refseq_ids[x.locus_id] = refseq_ids

    dbentity_id_to_date_assigned = {}
    for x in nex_session.query(Goannotation).filter_by(source_id=source_id, annotation_type='manually curated').all():
        dbentity_id_to_date_assigned[x.dbentity_id] = str(x.date_assigned).split(' ')[0].replace('-', '')

    dbentity_id_to_so_id = {}
    i = 0
    for x in nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id=taxonomy_id, dna_type='GENOMIC').all():
        dbentity_id_to_so_id[x.dbentity_id] = x.so_id
        
    ## dumping genes
    
    type_to_col6 = type_mapping()
    
    for x in nex_session.query(Locusdbentity).filter_by(has_go=True).all():
        
        # col1: DB
        col1 = 'SGD'
        
        # col2: database ID
        col2 = x.sgdid
        
        # col3: gene name
        col3 = x.display_name
                
        # col4: gene product
        col4 = ''
        if x.dbentity_id in dbentity_id_to_ncbi_protein_name:
            col4 = dbentity_id_to_ncbi_protein_name[x.dbentity_id]

        # col5: gene name/aliases/ORFname
        aliases = dbentity_id_to_alias_names.get(x.dbentity_id, [])
        if x.gene_name is not None:
            aliases = [x.gene_name] + aliases
        aliases = aliases + [x.systematic_name]
        col5 = '|'.join(aliases)

        # col6: object type
        so_id = dbentity_id_to_so_id.get(x.dbentity_id)
        ## NISS genes
        if so_id is None:
            for y in nex_session.query(Dnasequenceannotation).filter_by(dbentity_id=x.dbentity_id, dna_type='GENOMIC').all():
                so_id = y.so_id 
                break
            
        if so_id:
            type = so_id_to_type.get(so_id)
            if type is None:
                continue
            col6 = type_to_col6.get(type)
            if col6 is None:
                continue
        else:
            col6 = 'gene'
        
        # col7: taxon
        col7 = TAXON

        # col8: Parent protein
        col8 = ''

        # col9: DB_Xrefs
        dbxrefs = dbentity_id_to_refseq_ids.get(x.dbentity_id, [])
        if x.dbentity_id in dbentity_id_to_uniprot:
            dbxrefs = [dbentity_id_to_uniprot[x.dbentity_id]] + dbxrefs
        col9 = ''
        if len(dbxrefs) > 0:
            col9 = '|'.join(dbxrefs)

        # col10: Gene_Product_Properties
        col10 = "db_subset=Swiss-Prot|go_annotation_complete=" + dbentity_id_to_date_assigned.get(x.dbentity_id, '')
        if x.dbentity_id in dbentity_id_to_function:
            col10 = col10 + "|go_annotation_summary=" + dbentity_id_to_function[x.dbentity_id]
        if x.dbentity_id in dbentity_id_to_uniprot:
            col10 = col10 + "|uniprot_proteome=" + dbentity_id_to_uniprot[x.dbentity_id]

        fw.write(col1 + "\t" + col2 + "\t" + col3 + "\t" + col4 + "\t" + col5 + "\t" + col6 + "\t" + col7 + "\t" + col8 + "\t" + col9 + "\t" + col10 + "\n")
        
    ## dumping complexes

    for x in nex_session.query(Complexdbentity).all():

        col1 = 'SGD'
        col2 = x.sgdid
        col3 = x.complex_accession
        col4 = x.display_name
        col5 = x.systematic_name + '|' + x.intact_id + '|' + x.display_name 
        col6 = 'protein_complex'
        col7 = TAXON
        col9 = "ComplexPortal:" + x.complex_accession
        
        fw.write(col1 + "\t" + col2 + "\t" + col3 + "\t" + col4 + "\t" + col5 + "\t" + col6 + "\t" + col7 + "\t\t" + col9 + "\t\n") 

    fw.close()
   
    log.info("Uploading GPI file to S3...")

    update_database_load_file_to_s3(nex_session, gpi_file, source_to_id, edam_to_id, datestamp)

    nex_session.close()

    log.info(str(datetime.now()))
    log.info("Done!")

def type_mapping():

    return { 'ORF': 'protein',
             'transposable element gene': 'protein',
             'blocked reading frame': 'gene',
             'ncRNA gene': 'ncRNA',
             'snoRNA gene': 'snoRNA',
             'snRNA gene': 'snRNA',
             'tRNA gene': 'tRNA',
             'rRNA gene': 'rRNA',
             'telomerase RNA gene': 'telomerase_RNA',
             'disabled reading frame': 'gene' }
             
def write_header(fw, datestamp):

    fw.write("!gpi-version: 1.2\n")
    fw.write("!date-generated: " + datestamp + "\n")
    fw.write("!generated-by: Saccharomyces Genome Database (SGD)\n")
    fw.write("!URL: https://www.yeastgenome.org/\n")
    fw.write("!Contact Email: sgd-helpdesk@lists.stanford.edu\n")
    fw.write("!Funding: NHGRI at US NIH, grant number U41-HG001315\n")
    fw.write("!\n")

# def upload_file_to_s3(file, filename):

#    s3 = boto3.client('s3')
#    s3.upload_fileobj(file, S3_BUCKET, filename, ExtraArgs={'ACL': 'public-read'})

def update_database_load_file_to_s3(nex_session, gpi_file, source_to_id, edam_to_id, datestamp):

    gzip_file = gpi_file + "." + datestamp + ".gz"
    import gzip
    import shutil
    with open(gpi_file, 'rb') as f_in, gzip.open(gzip_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    local_file = open(gzip_file, mode='rb')

    # print ("uploading to latest...")
    
    ### upload a current GPI file to S3 with a static URL for Go Community ###
    # upload_file_to_s3(local_file, "latest/gpi.sgd.gz")
    ##########################################################################

    # print ("uploading to s3 sgdid system...")
    
    import hashlib
    gpad_md5sum = hashlib.md5(gzip_file.encode()).hexdigest()
    row = nex_session.query(Filedbentity).filter_by(
        md5sum=gpad_md5sum).one_or_none()

    if row is not None:
        return

    # file_size = os.path.getsize(gzip_file)
    
    gzip_file = gzip_file.replace("scripts/dumping/curation/data/", "")


    nex_session.query(Dbentity).filter(Dbentity.display_name.like('gpi.sgd%')).filter(
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
        display_name="gpi.sgd.README", dbentity_status='Active').one_or_none()
    readme_file_id = None
    if readme is not None:
        readme_file_id = readme.dbentity_id

    # path.path = /reports/function

    upload_file(CREATED_BY, local_file,
                filename=gzip_file,
                file_extension='gz',
                description='All GO annotations for yeast genes (protein and RNA) in GPI file format',
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
                # file_size=file_size)

    
    gpi = nex_session.query(Dbentity).filter_by(
        display_name=gzip_file, dbentity_status='Active').one_or_none()
    if gpi is None:
        log.info("The " + gzip_file + " is not in the database.")
        return
    file_id = gpi.dbentity_id

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

    log.info("Done uploading " + gpi_file)

    
if __name__ == '__main__':

    dump_data()
