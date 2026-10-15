import gzip
import json
import logging
import os
import sys
from threading import Thread
import time
import traceback

import boto3
from sqlalchemy import create_engine
from src.models import Base, DBSession, Dnasequenceannotation, Locusdbentity

__author__ = 'tshepp'

'''
    For a set of loci, get expression details, make a JSON string and upload to sgd-prod-expression-details bucket with name [SGDID].json.

    Files are stored gzipped (Content-Encoding: gzip) as application/json with a
    1-day browser cache, so pages download ~10x less and repeat visits skip S3.
    Re-run after loading expression data (load_expression_data.py) or editing
    dataset metadata shown on expression pages.

    usage:
        python scripts/loading/dataset/upload_expression_details.py               # all loci with expression
        python scripts/loading/dataset/upload_expression_details.py S000001855 ... # just these SGDIDs
'''

engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600, pool_size=20)
DBSession.configure(bind=engine)
Base.metadata.bind = engine

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

DEBUG_SIZE = 5
S3_BUCKET = os.environ['EXPRESSION_S3_BUCKET']
S3_ACCESS_KEY = os.environ['S3_ACCESS_KEY']
S3_SECRET_KEY = os.environ['S3_SECRET_KEY']
S3_REGION = 'us-west-2'
CACHE_CONTROL = 'public, max-age=86400'

# boto3 clients are thread-safe; one is shared by the upload threads
s3_client = boto3.client('s3', region_name=S3_REGION, aws_access_key_id=S3_ACCESS_KEY,
                         aws_secret_access_key=S3_SECRET_KEY)

def get_all_genes(limit, offset):
    # stable order so the LIMIT/OFFSET chunks don't overlap or skip loci
    return DBSession.query(Locusdbentity).filter(Locusdbentity.has_expression == True).order_by(
        Locusdbentity.dbentity_id).limit(limit).offset(offset).all()

def upload_gene(gene):
    try:
        expression_details_json = json.dumps(gene.expression_to_dict())
        s3_client.put_object(Bucket=S3_BUCKET,
                             Key=gene.sgdid + '.json',
                             Body=gzip.compress(expression_details_json.encode('utf-8')),
                             ContentType='application/json',
                             ContentEncoding='gzip',
                             CacheControl=CACHE_CONTROL,
                             ACL='public-read')
        return True
    except:
        log.error('Error uploading ' + gene.sgdid)
        traceback.print_exc()
        return False

def upload_test_gene():
    start = time.time()
    gene = DBSession.query(Locusdbentity).filter(Locusdbentity.dbentity_id == 1268789).one_or_none()
    upload_gene(gene)
    end = time.time()
    elapsed = end - start
    log.info('RAD54 done in ' + str(elapsed) + ' seconds')

def upload_gene_list(genes, list_name):
    list_start = time.time()
    start = time.time()
    temp_success_list = []
    # every DEBUG_SIZE genes print some debug
    for i, gene in enumerate(genes):
        success = upload_gene(gene)
        if success:
            temp_success_list.append(gene.sgdid)
        if i > 0 and i % DEBUG_SIZE == 0:
            end = time.time()
            elapsed = round(end - start)
            list_elapsed_hours = round(end - list_start) / 3600
            log.info(str(temp_success_list) + ' done in ' + str(elapsed) + ' seconds. ' + str(i) + '/' + str(len(genes)) + ' of total list in ' + str(list_elapsed_hours) + ' hours. List ' + list_name)
            start = time.time()
            temp_success_list = []
    log.info('Finished with list ' + list_name)

CHUNK_SIZE = 1100
FINAL_EXTRA_CHUNK_SIZE = 2000
# methods for 6 gene subsets to allow 6 threads
def upload_genes_a():
    genes = get_all_genes(CHUNK_SIZE, 0 * CHUNK_SIZE)
    upload_gene_list(genes, 'a')
def upload_genes_b():
    genes = get_all_genes(CHUNK_SIZE, 1 * CHUNK_SIZE)
    upload_gene_list(genes, 'b')
def upload_genes_c():
    genes = get_all_genes(CHUNK_SIZE, 2 * CHUNK_SIZE)
    upload_gene_list(genes, 'c')
def upload_genes_d():
    genes = get_all_genes(CHUNK_SIZE, 3 * CHUNK_SIZE)
    upload_gene_list(genes, 'd' )
def upload_genes_e():
    genes = get_all_genes(CHUNK_SIZE, 4 * CHUNK_SIZE)
    upload_gene_list(genes, 'e' )
def upload_genes_f():
    genes = get_all_genes(CHUNK_SIZE + FINAL_EXTRA_CHUNK_SIZE, 5 * CHUNK_SIZE)
    upload_gene_list(genes, 'f' )
    
def upload_sgdids(sgdids):
    genes = DBSession.query(Locusdbentity).filter(Locusdbentity.sgdid.in_(sgdids)).all()
    missing = set(sgdids) - set(gene.sgdid for gene in genes)
    if missing:
        log.error('Not in the database: ' + ', '.join(sorted(missing)))
    for gene in genes:
        start = time.time()
        if upload_gene(gene):
            log.info(gene.sgdid + ' uploaded in ' + str(round(time.time() - start, 1)) + ' seconds')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        upload_sgdids(sys.argv[1:])
        sys.exit(0)
    log.info('Starting expression upload.')
    t1 = Thread(target=upload_genes_a)
    t2 = Thread(target=upload_genes_b)
    t3 = Thread(target=upload_genes_c)
    t4 = Thread(target=upload_genes_d)
    t5 = Thread(target=upload_genes_e)
    t6 = Thread(target=upload_genes_f)
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()
    t6.start()
