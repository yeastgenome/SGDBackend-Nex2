import boto3
import os
S3_BUCKET = os.environ['S3_BUCKET']
S3_BUCKET2 = os.environ['ARCHIVE_S3_BUCKET']
from src.boto3_upload import boto3_copy_file
from src.models import Filedbentity, Dbentity
from scripts.loading.database_session import get_session

def copy_files():
   
    nex_session = get_session()

    copy_utr_files(nex_session)


def copy_utr_files(nex_session):

    dstDir = "sequence/S288C_reference/"
    
    utr_files = ['SGD_all_ORFs_5prime_UTRs.fsa.zip', 'SGD_all_ORFs_5prime_UTRs.README',
                 'SGD_all_ORFs_3prime_UTRs.fsa.zip', 'SGD_all_ORFs_3prime_UTRs.README']

    for utr_file in utr_files: 
        x = nex_session.query(Filedbentity).filter_by(previous_file_name=utr_file).filter(Filedbentity.dbentity_status=='Active').one_or_none()
        if x is None:
            print ("Error finding a single Active ", utr_file, " in the database") 
            continue
        if x.s3_url is None:
            continue
        urlParam = x.s3_url.split('/')
        filename = urlParam[4].split('?')[0]
        srcFile = urlParam[3] + '/' + filename

        ## copy to current directory
        dstFile = dstDir + utr_file
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)
        
if __name__ == '__main__':

    copy_files()
