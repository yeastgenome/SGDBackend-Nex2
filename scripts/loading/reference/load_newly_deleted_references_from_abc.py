import sys
import json
from urllib import request
from scripts.loading.database_session import get_session
from scripts.loading.reference.load_tet_from_abc import download_json_file
from scripts.loading.reference.add_abc_reference import email_id_to_dbuser_mapping
import json
from os import environ

__author__ = 'sweng66'

ABC_API_ROOT_URL = environ['ABC_API_ROOT_URL']
url = ABC_API_ROOT_URL + "reference/get_recently_deleted_references/SGD"
json_file = "scripts/loading/reference/data/references_deleted_SGD.json"
CREATED_BY = 'OTTO'


def load_data():

    download_json_file()
    
    print("Reading ABC references_deleted_SGD.json file...")
    
    db = get_session()
    
    json_data = dict()
    with open(json_file, "r") as f:
        json_str = f.read()
        json_data = json.loads(json_str)

    deleted_pmids_in_db = set()
    rows = db.execute("SELECT pmid from nex.referencedeleted").fetchall()
    for x in rows:
        deleted_pmids_in_db.add(x[0])
    good_pmids_in_db = {}
    rows = db.execute("SELECT dbentity_id, pmid from nex.referencedbentity WHERE pmid is not null").fetchall()
    for	x in rows:
        good_pmids_in_db[x[1]] = x[0]

    email_id_to_created_by = email_id_to_dbuser_mapping()
    
    for record in json_data['data']:
        pmid = int(record['pmid'].replace("PMID:", ""))
        email = record['updated_by_email']
        created_by = None
        if email and "@" in email:
            created_by = email_id_to_created_by.get(email.split('@')[0])
        if created_by is None:
            created_by = CREATED_BY
            
        updated_by = record['updated_by_okta_id']
        if pmid in deleted_pmids_in_db:
            continue
        elif pmid in good_pmids_in_db:
            reference_id = good_pmids_in_db[pmid]
            # set it to 'Deleted' for now?
            db.execute("UPDATE nex.dbentity SET dbentity_status = 'Deleted' WHERE dbentity_id = " + str(reference_id))
            print("PMID:" + str(pmid) + ": Deleting from dbentity/referencedbentity and other ref related tables:", email, created_by)
            db.rollback()
        else:
            db.execute("INSERT INTO nex.referencedeleted (pmid, reason_deleted, created_by) "
                       "VALUES (" + str(pmid) + ", 'This paper was deleted because the content is not relevant to S. cerevisiae.', '" + created_by + "')")
            db.commit()
            print("PMID:" + str(pmid) + ": Inserting into referencedeleted table:", email, created_by)
            
    db.close()
    print("DONE!")
    

if __name__ == '__main__':

    load_data()
