import sys
import json
import json
from os import environ
from urllib import request
from scripts.loading.database_session import get_session
from scripts.loading.reference.add_abc_reference import email_id_to_dbuser_mapping
from src.models import Referencedbentity, CuratorActivity, ReferenceFile, Referenceunlink, \
    Referencetype, Referencedocument, Referenceauthor, ReferenceUrl, ReferenceAlias, \
    StrainsummaryReference, Reservedname, PathwaysummaryReference, LocussummaryReference, \
    LocusRelationReference, LocusnoteReference, LocusAliasReferences, LocusReferences, \
    DatasetReference, CurationReference, ColleagueReference, Physinteractionannotation, \
    Goannotation, Geninteractionannotation, Literatureannotation, Referencedeleted, \
    AlleleReference, LocusalleleReference, Phenotypeannotation, Posttranslationannotation, \
    ReferenceRelation, Regulationannotation

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

    records = json_data['data']
    for record in records:
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
            # db.execute("UPDATE nex.dbentity SET dbentity_status = 'Deleted' WHERE dbentity_id = " + str(reference_id))
            print("PMID:" + str(pmid) + ": Deleting from dbentity/referencedbentity and other ref related tables:", email, created_by)
            delete_reference(db, reference_id, pmid, created_by)
        else:
            print("PMID:" + str(pmid) + ": Inserting into referencedeleted table:", email, created_by)
            x = Referencedeleted(pmid=pmid,
                                 reason_deleted='This paper was deleted because the content is not relevant to S. cerevisiae.',
                                 created_by=created_by)
            db.add(x)
            db.commit()
            
    db.close()
    print("DONE!")
    

def delete_helper(db, reference_id, table, table_name):
    count = db.query(table).filter_by(reference_id = reference_id).count()
    if count > 0:
        db.query(table).filter_by(reference_id = reference_id).delete()
        print('{} records being deleted from {} for reference_id = {}'.format(count, table_name, reference_id))


def delete_reference(db, reference_id, pmid, created_by):

    try:
        delete_helper(db, reference_id, Literatureannotation, 'Literatureannotation')
        delete_helper(db, reference_id, Phenotypeannotation, 'Phenotypeannotation')
        delete_helper(db, reference_id, Regulationannotation, 'Regulationannotation')
        delete_helper(db, reference_id, Posttranslationannotation, 'Posttranslationannotation')
        delete_helper(db, reference_id, Geninteractionannotation, 'Geninteractionannotation')
        delete_helper(db, reference_id, Goannotation, 'Goannotation')
        delete_helper(db, reference_id, Physinteractionannotation, 'Physinteractionannotation')
        delete_helper(db, reference_id, AlleleReference, 'AlleleReference')
        delete_helper(db, reference_id, LocusalleleReference, 'LocusalleleReference')
        delete_helper(db, reference_id, ColleagueReference, 'ColleagueReference')
        delete_helper(db, reference_id, CurationReference, 'CurationReference')
        delete_helper(db, reference_id, DatasetReference, 'DatasetReference')
        delete_helper(db, reference_id, DatasetReference, 'DatasetReference')
        delete_helper(db, reference_id, LocusReferences, 'LocusReferences')
        delete_helper(db, reference_id, LocusAliasReferences, 'LocusAliasReferences')
        delete_helper(db, reference_id,	LocusnoteReference, 'LocusnoteReference')
        delete_helper(db, reference_id, LocusRelationReference, 'LocusRelationReference')
        delete_helper(db, reference_id,	LocussummaryReference, 'LocussummaryReference')
        delete_helper(db, reference_id,	PathwaysummaryReference, 'PathwaysummaryReference')
        delete_helper(db, reference_id,	Reservedname, 'Reservedname')
        delete_helper(db, reference_id, StrainsummaryReference, 'StrainsummaryReference')
        delete_helper(db, reference_id, ReferenceAlias, 'ReferenceAlias')
        delete_helper(db, reference_id,	ReferenceUrl, 'ReferenceUrl')
        delete_helper(db, reference_id, Referenceauthor, 'Referenceauthor')
        delete_helper(db, reference_id, Referencedocument, 'Referencedocument')
        delete_helper(db, reference_id,	Referencetype, 'Referencetype')
        delete_helper(db, reference_id, Referenceunlink, 'Referenceunlink')
        delete_helper(db, reference_id,	ReferenceFile, 'ReferenceFile')
        ### delete rows in CuratorActivity if there are any
        count = db.query(CuratorActivity).filter_by(dbentity_id = reference_id).count()
        if count > 0:
            db.query(CuratorActivity).filter_by(dbentity_id = reference_id).delete()
            print('{} records being deleted from {} for reference_id = {}'.format(count, "CuratorActivity", reference_id))
        count = db.query(ReferenceRelation).filter_by(child_id = reference_id).count()
        if count > 0:
            db.query(ReferenceRelation).filter_by(child_id = reference_id).delete()
        count =	db.query(ReferenceRelation).filter_by(parent_id = reference_id).count()
        if count > 0:
            db.query(ReferenceRelation).filter_by(parent_id = reference_id).delete()
        reference = db.query(Referencedbentity).filter_by(dbentity_id=reference_id).one_or_none()
        db.delete(reference)
        print('{} records being deleted from {} for reference_id = {}'.format(count, "Dbentity/Referencedbentity", reference_id))
        db.commit()
        x = Referencedeleted(pmid=pmid,
                             reason_deleted='This paper was deleted by ' + created_by,
                             created_by=created_by)
        db.add(x)
        db.commit()
    except Exception as e:
        print("Error deleting PMID:" + str(pmid) + ": " + str(e))


def download_json_file():
    
    try:
        print("Downloading " + url)
        req = request.urlopen(url)
        data = req.read()
        with open(json_file, 'wb') as fh:
            fh.write(data)
    except Exception as e:
        print("Error downloading the fil. Error=" + str(e))
        

if __name__ == '__main__':

    load_data()
