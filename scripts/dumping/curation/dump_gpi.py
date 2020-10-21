from src.helpers import upload_file
from scripts.loading.database_session import get_session
from src.models import Dbentity, Locusdbentity, LocusAlias, So, Dnasequenceannotation, Locussummary, Goannotation, \
                       Source, Complexdbentity, Complexbindingannotation, Interactor, Taxonomy
from urllib.request import urlretrieve
from urllib.request import urlopen
import transaction
from boto.s3.key import Key
import boto
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

S3_ACCESS_KEY = os.environ['S3_ACCESS_KEY']
S3_SECRET_KEY = os.environ['S3_SECRET_KEY']
S3_BUCKET = os.environ['S3_BUCKET']

CREATED_BY = os.environ['DEFAULT_USER']

gpi_file = "scripts/dumping/curation/data/gpi.sgd"

TAXON = 'NCBITaxon:559292'

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
    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXID).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    so_id_to_soid = dict([(x.so_id, x.soid) for x in nex_session.query(So).all()])
    dbentity_id_to_sgdid = dict([(x.dbentity_id, x.sgdid) for x in nex_session.query(Dbentity).filter_by(subclass='LOCUS').all()])
    dbentity_id_to_locus = dict([(x.dbentity_id, (x.systematic_name, x.gene_name)) for x in nex_session.query(Locusdbentity).all()])
    dbentity_id_to_function = dict([(x.locus_id, x.text) for x in nex_session.query(Locussummary).filter_by(summary_type='Function').all()])
    complex_id_to_complex_accession = dict([(x.dbentity_id, x.complex_accession) for x in nex_session.query(Complexdbentity).all()])
    
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
            dbentity_id_to_uniprot[x.locus_id] = x.display_name
        elif x.alias_type == 'RefSeq nucleotide version ID':
            refseq_ids = []
            if x.locus_id in dbentity_id_to_refseq_ids:
                refseq_ids = dbentity_id_to_refseq_ids[x.locus_id]
            refseq_ids.append(x.display_name)
            dbentity_id_to_refseq_ids[x.locus_id] = refseq_ids

    dbentity_id_to_date_assigned = {}
    for x in nex_session.query(Goannotation).filter_by(source_id=source_id, annotation_type='manually curated').all():
        dbentity_id_to_date_assigned[x.dbentity_id] = str(x.date_assigned).split(' ')[0].replace('-', '')
        
    ## complex_id_to_complex_accession  
    interactor_id_to_complexes = {}
    for x in nex_session.query(Complexbindingannotation).all():
        ## interactor_id
        complexes = []
        if x.interactor_id in interactor_id_to_complexes:
            complexes = interactor_id_to_complexes[x.interactor_id]
        complex_accession = complex_id_to_complex_accession[x.complex_id]
        if complex_accession not in complexes:
            complexes.append(complex_accession)
        interactor_id_to_complexes[x.interactor_id] = complexes
        ## binding_interactor_id
        complexes = []
        if x.binding_interactor_id in interactor_id_to_complexes:
            complexes =	interactor_id_to_complexes[x.binding_interactor_id]
        complex_accession = complex_id_to_complex_accession[x.complex_id]
        if complex_accession not in complexes:
            complexes.append(complex_accession)
        interactor_id_to_complexes[x.binding_interactor_id] = complexes
                                   
    dbentity_id_to_complexes = {}
    for x in nex_session.query(Interactor).all():
        if x.locus_id is None:
            continue
        complexes = []
        if x.locus_id in dbentity_id_to_complexes:
            complexes = dbentity_id_to_complexes[x.locus_id]
        for complex_accession in interactor_id_to_complexes.get(x.interactor_id, []):
            if complex_accession not in complexes:
                complexes.append(complex_accession)
        dbentity_id_to_complexes[x.locus_id] = complexes
        
    for x in nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id=taxonomy_id, dna_type='GENOMIC').all():
        if x.dbentity_id not in dbentity_id_to_date_assigned:
            continue

        # col1: database ID
        col1 = "SGD:" + dbentity_id_to_sgdid.get(x.dbentity_id)
        
        # col2: gene name
        (systematic_name, gene_name) = dbentity_id_to_locus.get(x.dbentity_id)
        col2 = gene_name
        if gene_name is None:
            col2 = systematic_name
        
        # col3: gene product
        col3 = ''
        if x.dbentity_id in dbentity_id_to_ncbi_protein_name:
            col3 = dbentity_id_to_ncbi_protein_name[x.dbentity_id]

        # col4: gene name/aliases/ORFname
        aliases = dbentity_id_to_alias_names.get(x.dbentity_id, [])
        if gene_name is not None:
            aliases = [gene_name] + aliases
        aliases = aliases + [systematic_name]
        col4 = '|'.join(aliases)
        
        # col5: soid
        col5 = so_id_to_soid.get(x.so_id)
        
        # col6: taxon
        col6 = TAXON

        # col7: Encoded_By
        col7 = ''

        # col8: Parent protein
        col8 = ''

        # col9: Protein_Containing_Complex_Members
        col9 = ''
        if x.dbentity_id in dbentity_id_to_complexes:
            col9 = '|'.join(dbentity_id_to_complexes[x.dbentity_id])

        # col10: DB_Xrefs
        dbxrefs = dbentity_id_to_refseq_ids.get(x.dbentity_id, [])
        if x.dbentity_id in dbentity_id_to_uniprot:
            dbxrefs = [dbentity_id_to_uniprot[x.dbentity_id]] + dbxrefs
        col10 = ''
        if len(dbxrefs) > 0:
            col10 = '|'.join(dbxrefs)

        # col11: Gene_Product_Properties
        col11 = "db_subset=Swiss-Prot|go_annotation_complete=" + dbentity_id_to_date_assigned[x.dbentity_id]
        if x.dbentity_id in dbentity_id_to_function:
            col11 = col11 + "|go_annotation_summary=" + dbentity_id_to_function[x.dbentity_id]
        if x.dbentity_id in dbentity_id_to_uniprot:
            col11 = col11 + "|uniprot_proteome=" + dbentity_id_to_uniprot[x.dbentity_id]
        
        fw.write(col1 + "\t" + col2 + "\t" + col3 + "\t" + col4 + "\t" + col5 + "\t" + col6 + "\t" + col7 + "\t" + col8 + "\t" + col9 + "\t" + col10 + "\t" + col11 + "\n")
        
    fw.close()
   
    log.info("Uploading GPI file to S3...")

    # update_database_load_file_to_s3(nex_session, gpi_file, source_to_id, edam_to_id, datestamp)

    
    nex_session.close()

    log.info(str(datetime.now()))
    log.info("Done!")

    
def write_header(fw, datestamp):

    fw.write("!gpi-version: 2.0\n")
    fw.write("!date-generated: " + datestamp + "\n")
    fw.write("!generated-by: Saccharomyces Genome Database (SGD)\n")
    fw.write("!URL: https://www.yeastgenome.org/\n")
    fw.write("!Contact Email: sgd-helpdesk@lists.stanford.edu\n")
    fw.write("!Funding: NHGRI at US NIH, grant number U41-HG001315\n")
    fw.write("!\n")

def update_database_load_file_to_s3(nex_session, gpi_file, source_to_id, edam_to_id, datestamp):

    # gene_association.sgd.20171204.gaf.gz
    # gene_association.sgd-yeastmine.20171204.gaf.gz

    # datestamp = str(datetime.now()).split(" ")[0].replace("-", "")
    gzip_file = gpi_file + "." + datestamp + ".gaf.gz"
    import gzip
    import shutil
    with open(gpi_file, 'rb') as f_in, gzip.open(gzip_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    local_file = open(gzip_file, mode='rb')

    ### upload a current GAF file to S3 with a static URL for Go Community ###
    # if is_public == '1':
    #    upload_gpi_to_s3(local_file, "latest/gpi.sgd.gz")
    ##########################################################################

    import hashlib
    gpad_md5sum = hashlib.md5(gzip_file.encode()).hexdigest()
    row = nex_session.query(Filedbentity).filter_by(
        md5sum=gpad_md5sum).one_or_none()

    if row is not None:
        return

    gzip_file = gzip_file.replace("scripts/dumping/curation/data/", "")


    nex_session.query(Dbentity).filter(Dbentity.display_name.like('gpi.sgd%')).filter(
        Dbentity.dbentity_status == 'Active').update({"dbentity_status": 'Archived'}, synchronize_session='fetch')
    nex_session.commit()

    data_id = edam_to_id.get('EDAM:2048')  # data:2048 Report
    topic_id = edam_to_id.get('EDAM:0085')  # topic:0085 Functional genomics
    format_id = edam_to_id.get('EDAM:3475')  # format:3475 TSV

    readme = nex_session.query(Dbentity).filter_by(
        display_name="gpi.README", dbentity_status='Active').one_or_none()
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
                is_public=is_public,
                is_in_spell='0',
                is_in_browser='0',
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
