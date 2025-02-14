import sys
import json
from urllib import request
from scripts.loading.database_session import get_session
from scripts.loading.reference.add_abc_reference import add_paper
import json
from os import environ

__author__ = 'sweng66'

ABC_API_ROOT_URL = environ['ABC_API_ROOT_URL']
url = ABC_API_ROOT_URL + "reference/get_recently_sorted_references/SGD"
json_file = "scripts/loading/reference/data/reference_new_SGD.json"


def load_data():

    download_json_file()
    
    print("Reading ABC reference_SGD.json file...")
    
    nex_session = get_session()
    
    json_data = dict()
    with open(json_file, "r") as f:
        json_str = f.read()
        json_data = json.loads(json_str)
    
    for record in json_data['data']:
        if "cross_references" not in record:
            continue
        (sgdid, pmid, reference_id, is_obsolete_sgdid) = is_paper_in_db(nex_session, record["cross_references"])

        # print(sgdid, pmid, reference_id, is_obsolete_sgdid)
        if reference_id or is_obsolete_sgdid:
            continue
        if sgdid is None:
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


def download_json_file():

    try:
        print("Downloading " + url)
        req = request.urlopen(url)
        data = req.read()
        with open(json_file, 'wb') as fh:
            fh.write(data)
    except Exception as e:
        print("Error downloading the file: " + json_file + ". Error=" + str(e))


if __name__ == '__main__':

    load_data()
