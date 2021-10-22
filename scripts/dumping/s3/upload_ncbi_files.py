import boto3
import os
from os import path
S3_BUCKET = os.environ['ARCHIVE_S3_BUCKET']

local_dir = "scripts/dumping/ncbi/data/"
s3_dir = "sequence/S288C_reference/NCBI_genome_source/"

session = boto3.Session()
s3 = session.resource('s3')

def upload_files():
    
    for filename in os.listdir(local_dir):
        local_file = local_dir + filename
        if filename.startswith('chr'):
            if filename.startswith('chr00') or filename.endswith('.ecn'):
                continue
            s3_file = s3_dir + filename
            print (local_file, s3_file)
            s3.meta.client.upload_file(local_file, S3_BUCKET, s3_file, ExtraArgs={'ACL': 'public-read'})
        elif filename.startswith("ncbi_") and filename.endswith(".tar.gz"):
            s3_file = s3_dir + "archive/" + filename
            print (local_file, s3_file)
            s3.meta.client.upload_file(local_file, S3_BUCKET, s3_file, ExtraArgs={'ACL': 'public-read'}) 

if __name__ == '__main__':

    upload_files()
