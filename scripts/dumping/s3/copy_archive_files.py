import boto3
import os
S3_BUCKET = os.environ['S3_BUCKET']
S3_BUCKET2 = os.environ['ARCHIVE_S3_BUCKET']
from src.boto3_upload import boto3_copy_file
from src.models import Filedbentity
from scripts.loading.database_session import get_session

def copy_files():
   
    nex_session = get_session()

    ## comment out the following since this is one time thing and it is done!!
    # copy_gff(nex_session)
    # copy_gaf(nex_session)
    # copy_gpad(nex_session)
    # copy_gpi(nex_session)
    # copy_noctua_gpad(nex_session) 

def copy_noctua_gpad(nex_session):

    dstDir = "curation/literature/archive/"
    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('noctua_sgd.gpad_%.gz')).all():
        if x.s3_url is not None:
            urlParam = x.s3_url.split('/')
            srcFile = urlParam[3] + '/' + urlParam[4].split('?')[0]
            dstFile = dstDir + urlParam[4].split('?')[0]
            print (x.dbentity_status, srcFile, dstFile)
            boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

def copy_gpi(nex_session):

    dstDir = "curation/literature/archive/"
    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('gp_information.559292_sgd_%.gz')).all():
        if x.s3_url is not None:
            urlParam = x.s3_url.split('/')
            srcFile = urlParam[3] + '/' + urlParam[4].split('?')[0]
            dstFile = dstDir + urlParam[4].split('?')[0]
            print (x.dbentity_status, srcFile, dstFile)
            boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)


def copy_gpad(nex_session):

    dstDir = "curation/literature/archive/"
    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('gp_association.559292_sgd_%.gz')).all():
        if x.s3_url is not None:
            urlParam = x.s3_url.split('/')
            srcFile = urlParam[3] + '/' + urlParam[4].split('?')[0]
            dstFile = dstDir + urlParam[4].split('?')[0]
            print (x.dbentity_status, srcFile, dstFile)
            boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)


def copy_gaf(nex_session):

    dstDir = "curation/literature/archive/"
    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('gene_association.sgd.%.gz')).all():
        if x.s3_url is not None:
            urlParam = x.s3_url.split('/')
            srcFile = urlParam[3] + '/' + urlParam[4].split('?')[0]
            dstFile = dstDir + urlParam[4].split('?')[0]
            print (x.dbentity_status, srcFile, dstFile)
            boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

def copy_gff(nex_session):

    dstDir = "curation/chromosomal_feature/archive/"
    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('saccharomyces_cerevisiae.%.gff.gz')).all():
        if '.2019' in x.s3_url or '.2020' in x.s3_url:
            urlParam = x.s3_url.split('/')
            srcFile = urlParam[3] + '/' + urlParam[4].split('?')[0]
            dstFile = dstDir + urlParam[4].split('?')[0]
            print (x.dbentity_status, srcFile, dstFile)
            boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

if __name__ == '__main__':

    copy_files()
