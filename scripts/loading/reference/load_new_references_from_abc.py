import sys
from scripts.loading.database_session import get_session
from scripts.loading.reference.add_abc_reference import add_paper
import json
from os import environ
import boto3
from botocore.exceptions import ClientError
import gzip
import os

__author__ = 'sweng66'

AWS_REGION = 'us-east-1'

json_file = 'reference_new_SGD.json.gz'
bucketname = 'agr-literature'
## change to 'prod/reference/dumps/latest/' + json_file' when it is ready
s3_file_location = 'develop/reference/dumps/latest/' + json_file


def load_data():

    print("Downloading ABC reference_new_SGD.json file...")
    
    download_reference_json_file_from_alliance_s3()

    print("Reading ABC reference_SGD.json file...")
    
    nex_session = get_session()
    
    json_data = dict()
    with gzip.open(json_file, 'rb') as f:
        json_str = f.read()
        json_data = json.loads(json_str)
    
    for record in json_data['data']:
        if "cross_references" not in record:
            continue
        (sgdid, pmid, reference_id, is_obsolete_sgdid) = is_paper_in_db(nex_session, record["cross_references"])

        # print(sgdid, pmid, reference_id, is_obsolete_sgdid)
        if reference_id or is_obsolete_sgdid:
            continue
        print("\nAdding paper for SGD:" + sgdid + "\n")
        add_paper(record, nex_session)

    nex_session.close()
    print("DONE!")
    

def is_paper_in_db(nex_session, cross_references):

    sgdid = None
    pmid = None
    is_obsolete_sgdid = False
    for x in cross_references:
        if x['curie'].startswith('SGD:S1'):
            if x['is_obsolete']:
                is_obsolete_sgdid = x['is_obsolete']
            sgdid = x['curie'].replace('SGD:', '')
        elif x['curie'].startswith('PMID'):
            pmid = x['curie'].replace('PMID:', '')
    if sgdid is None or is_obsolete_sgdid:
        return (sgdid, pmid, None, is_obsolete_sgdid)
    rows = nex_session.execute("SELECT dbentity_id from nex.dbentity WHERE sgdid = '" + sgdid + "'").fetchall()
    if len(rows) == 0:
        return (sgdid, pmid, None, is_obsolete_sgdid)
    dbentity_id = rows[0][0]
    rows = nex_session.execute("SELECT pmid from nex.referencedbentity WHERE dbentity_id = " + str(dbentity_id)).fetchall()
    if len(rows) == 0:
        return (sgdid, pmid, None, is_obsolete_sgdid)
    return (sgdid, pmid, dbentity_id, is_obsolete_sgdid)


def download_reference_json_file_from_alliance_s3():
    
    s3_client = boto3.client('s3',
                             region_name=AWS_REGION,
                             aws_access_key_id=environ['ABC_AWS_ACCESS_KEY_ID'],
                             aws_secret_access_key=environ['ABC_AWS_SECRET_ACCESS_KEY'])
    try:
        response = s3_client.download_file(bucketname, s3_file_location, json_file)
        if response is not None:
            logger.info("boto3 downloaded response: %s", response)
    except ClientError as e:
        logging.error(e)
        return False


if __name__ == '__main__':

    load_data()
