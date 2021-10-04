from datetime import datetime
import logging
## import tarfile
import os
import sys
import json
from src.models import Referencedbentity, Locusdbentity, Literatureannotation
from scripts.loading.database_session import get_session
from src.boto3_upload import upload_one_file_to_s3

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

S3_BUCKET = os.environ['S3_BUCKET']
S3_BUCKET2 = os.environ['ARCHIVE_S3_BUCKET']

CREATED_BY = os.environ['DEFAULT_USER']

datafile = "scripts/dumping/ncbi/data/gene2pmid.tab"

s3_archive_dir = "curation/literature/"

obsolete_pmids = [25423496, 27651461, 28068213, 31088842]

def dump_data():

    nex_session = get_session()

    datestamp = str(datetime.now()).split(" ")[0]

    log.info(str(datetime.now()))
    log.info("Getting basic data from the database...")
    
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

    upload_file_to_latest(datafile)
    
def upload_file_to_latest(datafile):

    file = open(datafile, "rb")
    filename = "latest/" + datafile.split('/')[-1]
    upload_one_file_to_s3(file, filename)
        
if __name__ == '__main__':

    dump_data()
