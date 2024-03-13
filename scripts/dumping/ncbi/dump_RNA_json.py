from datetime import datetime
import logging
import tarfile
import os
import sys
import json
import boto3
import gzip
import shutil
from src.models import Taxonomy, Source, Edam, Path, Filedbentity, FilePath, So, Dbentity,\
    Dnasequenceannotation, Locusdbentity, LocusAlias, Referencedbentity,\
    Literatureannotation, Contig
from scripts.loading.database_session import get_session
from src.helpers import upload_file

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

S3_BUCKET = os.environ['S3_BUCKET']
S3_BUCKET2 = os.environ['ARCHIVE_S3_BUCKET']

CREATED_BY = os.environ['DEFAULT_USER']

data_file = "scripts/dumping/ncbi/data/RNAcentral.json"

s3_archive_dir = "curation/chromosomal_feature/"

taxonId = "NCBITaxon:559292"
TAXON = "TAX:559292"
assembly = "R64-4-1"

obsolete_pmids = ['PMID:25423496', 'PMID:27651461',
                  'PMID:28068213', 'PMID:31088842']


def dump_data():

    nex_session = get_session()

    # datestamp = str(datetime.now()).split(" ")[0]
    datestamp = str(datetime.today().strftime("%Y-%m-%dT%H:%M:%S%z")) + ".458526-07:00"
    
    
    log.info(str(datetime.now()))
    log.info("Getting basic data from the database...")

    source_to_id = dict([(x.display_name, x.source_id)
                         for x in nex_session.query(Source).all()])
    edam_to_id = dict([(x.format_name, x.edam_id)
                       for x in nex_session.query(Edam).all()])

    taxon = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxon.taxonomy_id
    so_id_to_so = dict([(x.so_id, (x.soid, x.display_name))
                        for x in nex_session.query(So).all()])
    dbentity_id_to_locus = dict([(x.dbentity_id, x)
                                 for x in nex_session.query(Locusdbentity).all()])
    reference_id_to_pmid = dict([(x.dbentity_id, x.pmid)
                                 for x in nex_session.query(Referencedbentity).all()])
    dbentity_id_to_sgdid = dict([(x.dbentity_id, x.sgdid) for x in nex_session.query(
        Dbentity).filter_by(subclass='LOCUS').all()])
    dbentity_id_to_status = dict([(x.dbentity_id, x.dbentity_status)
                                  for x in nex_session.query(Dbentity).filter_by(subclass='LOCUS').all()])
    contig_id_to_name = dict([(x.contig_id, x.display_name) for x in nex_session.query(
        Contig).filter_by(taxonomy_id=taxonomy_id).all()])

    log.info(str(datetime.now()))
    log.info("Getting aliases from the database...")

    locus_id_to_alias_names = {}
    locus_id_to_ncbi_protein_name = {}

    for x in nex_session.query(LocusAlias).filter(LocusAlias.alias_type.in_(['Uniform', 'Non-uniform', 'NCBI protein name'])).all():

        if x.alias_type in ['Uniform', 'Non-uniform']:
            alias_names = []
            if x.locus_id in locus_id_to_alias_names:
                alias_names = locus_id_to_alias_names[x.locus_id]
            alias_names.append(x.display_name)
            locus_id_to_alias_names[x.locus_id] = alias_names
        elif x.alias_type == 'NCBI protein name':
            locus_id_to_ncbi_protein_name[x.locus_id] = x.display_name

    dbentity_id_to_pmid_list = {}
    for x in nex_session.query(Literatureannotation).all():
        pmid_list = []
        if x.dbentity_id in dbentity_id_to_pmid_list:
            pmid_list = dbentity_id_to_pmid_list[x.dbentity_id]
        pmid = reference_id_to_pmid[x.reference_id]
        if pmid:
            pmidStr = "PMID:"+str(pmid)
            if pmidStr not in pmid_list and pmidStr not in obsolete_pmids:
                pmid_list.append(pmidStr)
        dbentity_id_to_pmid_list[x.dbentity_id] = pmid_list

    log.info("Getting all features from the database...")

    metaData = {"dateProduced": datestamp,
                "dataProvider": 'SGD',
                "release": datestamp,
                "schemaVersion": "0.4.0",
                "publications": [
                    "PMID:22110037"
                ]}

    data = []
    ## get all features with 'GENOMIC' sequence in S288C
    for x in nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id=taxonomy_id, dna_type='GENOMIC').order_by(Dnasequenceannotation.contig_id, Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all():
        locus = dbentity_id_to_locus.get(x.dbentity_id)
        if locus is None:
            continue

        (soid, soTerm) = so_id_to_so[x.so_id]
        if 'RNA' not in soTerm:
            continue
        if dbentity_id_to_status[x.dbentity_id] != 'Active':
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

        sgdid = dbentity_id_to_sgdid[x.dbentity_id]

        row = {"primaryId": "SGD:" + sgdid,
               "taxonId": taxonId,
               "symbol": name}

        if x.dbentity_id in locus_id_to_alias_names:
            row["symbolSynonyms"] = locus_id_to_alias_names[x.dbentity_id]

        row["soTermId"] = soid
        row["sequence"] = x.residues
        row["genomeLocations"] = [{"assembly": assembly,
                                   "exons": [{"chromosome": chr,
                                              "strand": x.strand,
                                              "startPosition": x.start_index,
                                              "endPosition": x.end_index}]
                                   }]
        if x.dbentity_id in locus_id_to_ncbi_protein_name:
            row["name"] = locus_id_to_ncbi_protein_name[x.dbentity_id]
        elif locus.name_description:
            row["name"] = locus.name_description
        elif locus.headline:
            row["name"] = locus.headline
        else:
            row["name"] = None

        row["url"] = "https://www.yeastgenome.org/locus/" + sgdid
        if x.dbentity_id in dbentity_id_to_pmid_list:
            row["publications"] = dbentity_id_to_pmid_list[x.dbentity_id]
        data.append(row)

    jsonData = {"data": data,
                "metaData": metaData}

    f = open(data_file, "w")
    f.write(json.dumps(jsonData, indent=4, sort_keys=True))
    f.close()

    datestamp = str(datetime.now()).split(" ")[0].replace("-", "")

    gzip_file = data_file.replace('.json', '') + '.' + datestamp + ".json.gz"

    with open(data_file, 'rb') as f_in, gzip.open(gzip_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    upload_file_to_latest_archive(data_file, gzip_file)

    update_database_load_file_to_s3(
        nex_session, data_file, gzip_file, source_to_id, edam_to_id)


def upload_file_to_latest_archive(data_file, gzip_file):

    session = boto3.Session()
    s3 = session.resource('s3')

    ## to latest:
    filename = data_file.split('/')[-1]
    s3.meta.client.upload_file(
        data_file, S3_BUCKET, "latest/" + filename, ExtraArgs={'ACL': 'public-read'})
    
    ## to current directoty under sgd-archive.yeastgenome.org bucket
    s3.meta.client.upload_file(
        data_file, S3_BUCKET2, s3_archive_dir + filename, ExtraArgs={'ACL': 'public-read'})

    ## to archive directory under sgd-archive.yeastgenome.org bucket
    gzip_filename = gzip_file.split('/')[-1]
    s3.meta.client.upload_file(gzip_file, S3_BUCKET2, s3_archive_dir +
                               "archive/" + gzip_filename, ExtraArgs={'ACL': 'public-read'})


def update_database_load_file_to_s3(nex_session, data_file, gzip_file, source_to_id, edam_to_id):

    local_file = open(gzip_file, mode='rb')

    import hashlib
    gff_md5sum = hashlib.md5(gzip_file.encode()).hexdigest()
    row = nex_session.query(Filedbentity).filter_by(
        md5sum=gff_md5sum).one_or_none()

    if row is not None:
        return

    gzip_file = gzip_file.replace("scripts/dumping/ncbi/data/", "")

    nex_session.query(Dbentity).filter(Dbentity.display_name.like('RNAcentral.%.json.gz')).filter(
        Dbentity.dbentity_status == 'Active').update({"dbentity_status": 'Archived'}, synchronize_session='fetch')
    nex_session.commit()

    data_id = edam_to_id.get('EDAM:3495')  # data:3495    RNA sequence
    topic_id = edam_to_id.get('EDAM:0099')  # topic:0099   RNA
    format_id = edam_to_id.get('EDAM:3464')  # format:3464  JSON format

    from sqlalchemy import create_engine
    from src.models import DBSession
    engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
    DBSession.configure(bind=engine)

    upload_file(CREATED_BY, local_file,
                filename=gzip_file,
                file_extension='gz',
                description='JSON file for yeast RNA genes',
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
                source_id=source_to_id['SGD'],
                md5sum=gff_md5sum)

    rnaFile = nex_session.query(Dbentity).filter_by(
        display_name=gzip_file, dbentity_status='Active').one_or_none()

    if rnaFile is None:
        log.info("The " + gzip_file + " is not in the database.")
        return

    file_id = rnaFile.dbentity_id

    path = nex_session.query(Path).filter_by(
        path="/reports/chromosomal-features").one_or_none()
    if path is None:
        log.info("The path: /reports/chromosomal-features is not in the database.")
        return
    path_id = path.path_id

    x = FilePath(file_id=file_id,
                 path_id=path_id,
                 source_id=source_to_id['SGD'],
                 created_by=CREATED_BY)

    nex_session.add(x)
    nex_session.commit()

    log.info("Done uploading " + data_file)


if __name__ == '__main__':

    dump_data()
