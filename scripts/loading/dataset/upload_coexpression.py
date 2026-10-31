"""Upload the co-expression JSON files written by compute_coexpression.py to S3.

Each <SGDID>.json in --in-dir is gzipped and stored as
s3://<bucket>/coexpression/<SGDID>.json (public-read, one-day Cache-Control),
next to the expression details JSON that the locus expression page already
reads from the same bucket.

Credentials: S3_ACCESS_KEY / S3_SECRET_KEY if set (as on the servers),
otherwise the default AWS credential chain (e.g. AWS_PROFILE).

Usage:
    python scripts/loading/dataset/upload_coexpression.py --in-dir data/coexpression
    python scripts/loading/dataset/upload_coexpression.py --in-dir data/coexpression --only S000001855
"""
import argparse
import gzip
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import boto3

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
log = logging.getLogger('upload_coexpression')

S3_BUCKET = os.environ.get('EXPRESSION_S3_BUCKET', 'sgd-prod-expression-details')
S3_REGION = 'us-west-2'
S3_PREFIX = 'coexpression/'
CACHE_CONTROL = 'public, max-age=86400'


def s3_client():
    if os.environ.get('S3_ACCESS_KEY') and os.environ.get('S3_SECRET_KEY'):
        return boto3.client('s3', region_name=S3_REGION, aws_access_key_id=os.environ['S3_ACCESS_KEY'],
                            aws_secret_access_key=os.environ['S3_SECRET_KEY'])
    return boto3.client('s3', region_name=S3_REGION)


def upload(client, path):
    with open(path, 'rb') as f:
        body = gzip.compress(f.read())
    client.put_object(Bucket=S3_BUCKET, Key=S3_PREFIX + os.path.basename(path), Body=body,
                      ContentType='application/json', ContentEncoding='gzip',
                      CacheControl=CACHE_CONTROL, ACL='public-read')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--in-dir', required=True)
    parser.add_argument('--only', nargs='+', metavar='SGDID', help='upload just these genes')
    parser.add_argument('--threads', type=int, default=8)
    args = parser.parse_args()

    names = sorted(n for n in os.listdir(args.in_dir) if n.endswith('.json'))
    if args.only:
        names = [n for n in names if n[:-5] in set(args.only)]
    client = s3_client()
    failed = []

    def task(name):
        try:
            upload(client, os.path.join(args.in_dir, name))
        except Exception as e:
            log.error('%s: %s', name, e)
            failed.append(name)

    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        for n, _ in enumerate(pool.map(task, names), 1):
            if n % 500 == 0:
                log.info('%d/%d uploaded', n, len(names))
    log.info('done: %d uploaded to s3://%s/%s, %d failed', len(names) - len(failed), S3_BUCKET, S3_PREFIX,
             len(failed))


if __name__ == '__main__':
    main()
