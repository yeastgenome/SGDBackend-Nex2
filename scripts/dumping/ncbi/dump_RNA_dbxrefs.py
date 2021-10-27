from src.helpers import upload_file
from datetime import datetime
import logging
from src.models import Taxonomy, Dnasequenceannotation, Locusdbentity, LocusAlias, \
     Contig, So, Source, Edam, Filedbentity, Path, FilePath, Dbentity
from scripts.loading.database_session import get_session
import os

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

datestamp = str(datetime.now()).split(" ")[0].replace("-", "")
datafile = "scripts/dumping/ncbi/data/SGD_ncRNA_xref.txt." + datestamp 

# s3_archive_dir = "curation/chromosomal_feature/"

TAXON = "TAX:559292"
mito_accession = 'KP263414.1'


def dump_data(rna_file):

    nex_session = get_session()
    
    log.info(str(datetime.now()))
    log.info("Getting basic data from the database...")

    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()])
    edam_to_id = dict([(x.format_name, x.edam_id) for x in nex_session.query(Edam).all()])

    taxon = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxon.taxonomy_id
    so_id_to_so = dict([(x.so_id, (x.soid, x.display_name))
                        for x in nex_session.query(So).all()])
    dbentity_id_to_locus = dict([(x.dbentity_id, x)
                                 for x in nex_session.query(Locusdbentity).all()])

    contig_id_to_name = dict([(x.contig_id, x.display_name) for x in nex_session.query(
        Contig).filter_by(taxonomy_id=taxonomy_id).all()])

    num2rom = number2roman()
    chr2accession = {}
    for x in nex_session.query(LocusAlias).filter_by(alias_type = 'TPA accession ID').all():
        locus = dbentity_id_to_locus.get(x.locus_id)
        if locus and locus.systematic_name.isdigit():
            chr = num2rom[locus.systematic_name]
            chr2accession[chr] = x.display_name
    chr2accession['Mito'] = mito_accession

    sgdid2accession = {}
    
    f =	open(rna_file)
    for line in f:
        pieces = line.split("\t")
        sgdid2accession[pieces[2]] = pieces[0]
    f.close()

    log.info("Getting all features from the database...")

    fw = open(datafile, "w")
    
    data = []
    for x in nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id=taxonomy_id, dna_type='GENOMIC').order_by(Dnasequenceannotation.contig_id, Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all():
        locus = dbentity_id_to_locus.get(x.dbentity_id)
        if locus is None:
            continue

        (soid, soTerm) = so_id_to_so[x.so_id]
        if 'RNA' not in soTerm:
            continue
        if locus.dbentity_status != 'Active':
            continue
        if locus.qualifier == 'Dubious':
            continue

        name = None
        if locus.gene_name and locus.gene_name != locus.systematic_name:
            name = locus.gene_name
        else:
            name = locus.systematic_name

        chromosome = contig_id_to_name.get(x.contig_id)
        chr = None
        if chromosome:
            chr = chromosome.split(' ')[1]
        accession4chr = chr2accession[chr]
        
        sgdid = locus.sgdid
        accession = sgdid2accession.get(sgdid)
        if accession is None:
            continue
        fw.write(accession4chr + "\t" + sgdid + "\t" + name + "\t" + soTerm + "\t" + accession + "\n")
    
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

    datafile = datafile.replace("scripts/dumping/ncbi/data/", "")

    nex_session.query(Dbentity).filter(Dbentity.display_name.like('SGD_ncRNA_xref.txt%')).filter(
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
        display_name="SGD_ncRNA_xref.README", dbentity_status='Active').one_or_none()
    readme_file_id = None
    if readme is not None:
        readme_file_id = readme.dbentity_id

    upload_file(CREATED_BY, local_file,
                filename=datafile,
                file_extension='.txt',
                description='SGD RNA dbxref file',
                display_name=datafile,
                data_id=data_id,
                format_id=format_id,
                topic_id=topic_id,
                status='Active',
                readme_file_id=readme_file_id,
                is_public='1',
                is_in_spell='0',
                is_in_browser='0',
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

    
def number2roman():

    num2rom = {}
    i = 0
    for roman in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI',
                  'XII', 'XIII', 'XIV', 'XV', 'XVI', 'Mito']:
        i = i + 1
        num2rom[str(i)] = roman
    return num2rom

if __name__ == '__main__':

    # http://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/id_mapping/database_mappings/sgd.tsv
    url_path = 'http://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/id_mapping/database_mappings/'
    rna_file = 'sgd.tsv'
    
    import urllib.request

    urllib.request.urlretrieve(url_path + rna_file, rna_file)

    dump_data(rna_file)
