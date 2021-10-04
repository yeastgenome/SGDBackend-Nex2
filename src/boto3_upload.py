import threading
import boto3
import os
import sys
import logging
from boto3.s3.transfer import TransferConfig

S3_BUCKET = os.environ['S3_BUCKET']

session = boto3.Session()

boto3.set_stream_logger('boto3.resources', logging.INFO)
s3 = session.resource('s3')

def upload_one_file_to_s3(file, filename):

    s3 = boto3.client('s3')
    file.seek(0)
    s3.upload_fileobj(file, S3_BUCKET, filename, ExtraArgs={'ACL': 'public-read'})
    return "https://" + S3_BUCKET + ".s3.amazonaws.com/" + filename

def boto3_copy_file(srcBucket, srcFile, dstBucket, dstFile):

    copy_source = { 'Bucket': srcBucket,
                    'Key':    srcFile }
    s3.meta.client.copy(copy_source, dstBucket, dstFile, ExtraArgs={'ACL': 'public-read'})

def boto3_multi_upload(file_path, s3_path):
    config = TransferConfig(multipart_threshold=1024 * 25, max_concurrency=10, multipart_chunksize=1024 * 25, use_threads=True)
    s3.meta.client.upload_file(file_path, S3_BUCKET, s3_path,
                               ExtraArgs={'ACL': 'public-read', }, Config=config, Callback=ProgressPercentage(file_path))
    
class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
            # To simplify we'll assume this is hooked up
            # to a single filename.
            with self._lock:
                self._seen_so_far += bytes_amount
                percentage = (self._seen_so_far / self._size) * 100
                sys.stdout.write(
                    "\r%s  %s / %s  (%.2f%%)" % (
                        self._filename, self._seen_so_far, self._size,
                        percentage))
                sys.stdout.flush()
