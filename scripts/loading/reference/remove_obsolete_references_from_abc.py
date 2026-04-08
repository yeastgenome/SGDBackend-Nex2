import json
from os import environ
from urllib import request
from scripts.loading.database_session import get_session
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
url = ABC_API_ROOT_URL + "reference/obsolete_mod_curies/SGD"
json_file = "scripts/loading/reference/data/references_obsolete_SGD.json"
CREATED_BY = 'OTTO'


def load_data():

    download_json_file()

    print("Reading ABC references_obsolete_SGD.json file...")

    db = get_session()

    json_data = []
    with open(json_file, "r") as f:
        json_str = f.read()
        json_data = json.loads(json_str)

    # Build lookup of format_name -> (dbentity_id, pmid) for references
    format_name_to_ref = {}
    rows = db.execute(
        "SELECT d.format_name, d.dbentity_id, r.pmid "
        "FROM nex.dbentity d "
        "JOIN nex.referencedbentity r ON d.dbentity_id = r.dbentity_id "
        "WHERE d.subclass = 'REFERENCE'"
    ).fetchall()
    for x in rows:
        format_name_to_ref[x[0]] = (x[1], x[2])

    deleted_count = 0
    not_found_count = 0

    for sgdid_with_prefix in json_data:
        # Remove "SGD:" prefix to get format_name (e.g., "SGD:S000001234" -> "S000001234")
        format_name = sgdid_with_prefix.replace("SGD:", "")

        if format_name in format_name_to_ref:
            reference_id, pmid = format_name_to_ref[format_name]
            print(f"SGDID:{sgdid_with_prefix}: Deleting reference_id={reference_id}, pmid={pmid}")
            delete_reference(db, reference_id, pmid, CREATED_BY)
            deleted_count += 1
        else:
            print(f"SGDID:{sgdid_with_prefix}: Not found in database, skipping")
            not_found_count += 1

    db.close()
    print(f"\nDONE! Deleted: {deleted_count}, Not found: {not_found_count}")


def delete_helper(db, reference_id, table, table_name):
    count = db.query(table).filter_by(reference_id=reference_id).count()
    if count > 0:
        db.query(table).filter_by(reference_id=reference_id).delete()
        print(f'  {count} records deleted from {table_name}')


def delete_reference(db, reference_id, pmid, created_by):

    try:
        # Delete from annotation tables
        delete_helper(db, reference_id, Literatureannotation, 'Literatureannotation')
        delete_helper(db, reference_id, Phenotypeannotation, 'Phenotypeannotation')
        delete_helper(db, reference_id, Regulationannotation, 'Regulationannotation')
        delete_helper(db, reference_id, Posttranslationannotation, 'Posttranslationannotation')
        delete_helper(db, reference_id, Geninteractionannotation, 'Geninteractionannotation')
        delete_helper(db, reference_id, Goannotation, 'Goannotation')
        delete_helper(db, reference_id, Physinteractionannotation, 'Physinteractionannotation')

        # Delete from reference association tables
        delete_helper(db, reference_id, AlleleReference, 'AlleleReference')
        delete_helper(db, reference_id, LocusalleleReference, 'LocusalleleReference')
        delete_helper(db, reference_id, ColleagueReference, 'ColleagueReference')
        delete_helper(db, reference_id, CurationReference, 'CurationReference')
        delete_helper(db, reference_id, DatasetReference, 'DatasetReference')
        delete_helper(db, reference_id, LocusReferences, 'LocusReferences')
        delete_helper(db, reference_id, LocusAliasReferences, 'LocusAliasReferences')
        delete_helper(db, reference_id, LocusnoteReference, 'LocusnoteReference')
        delete_helper(db, reference_id, LocusRelationReference, 'LocusRelationReference')
        delete_helper(db, reference_id, LocussummaryReference, 'LocussummaryReference')
        delete_helper(db, reference_id, PathwaysummaryReference, 'PathwaysummaryReference')
        delete_helper(db, reference_id, Reservedname, 'Reservedname')
        delete_helper(db, reference_id, StrainsummaryReference, 'StrainsummaryReference')

        # Delete reference metadata
        delete_helper(db, reference_id, ReferenceAlias, 'ReferenceAlias')
        delete_helper(db, reference_id, ReferenceUrl, 'ReferenceUrl')
        delete_helper(db, reference_id, Referenceauthor, 'Referenceauthor')
        delete_helper(db, reference_id, Referencedocument, 'Referencedocument')
        delete_helper(db, reference_id, Referencetype, 'Referencetype')
        delete_helper(db, reference_id, Referenceunlink, 'Referenceunlink')
        delete_helper(db, reference_id, ReferenceFile, 'ReferenceFile')

        # Delete CuratorActivity records
        count = db.query(CuratorActivity).filter_by(dbentity_id=reference_id).count()
        if count > 0:
            db.query(CuratorActivity).filter_by(dbentity_id=reference_id).delete()
            print(f'  {count} records deleted from CuratorActivity')

        # Delete ReferenceRelation (both child and parent relationships)
        count = db.query(ReferenceRelation).filter_by(child_id=reference_id).count()
        if count > 0:
            db.query(ReferenceRelation).filter_by(child_id=reference_id).delete()
            print(f'  {count} records deleted from ReferenceRelation (child)')
        count = db.query(ReferenceRelation).filter_by(parent_id=reference_id).count()
        if count > 0:
            db.query(ReferenceRelation).filter_by(parent_id=reference_id).delete()
            print(f'  {count} records deleted from ReferenceRelation (parent)')

        # Delete the reference itself
        reference = db.query(Referencedbentity).filter_by(dbentity_id=reference_id).one_or_none()
        if reference:
            db.delete(reference)
            print(f'  Deleted from Referencedbentity/Dbentity')
        db.commit()

        # Record deletion in referencedeleted table (only if pmid exists)
        if pmid:
            x = Referencedeleted(
                pmid=pmid,
                reason_deleted='This paper was deleted because the SGDID became obsolete in ABC.',
                created_by=created_by
            )
            db.add(x)
            db.commit()

    except Exception as e:
        db.rollback()
        print(f"  Error deleting reference_id={reference_id}: {str(e)}")


def download_json_file():

    try:
        print("Downloading " + url)
        req = request.urlopen(url)
        data = req.read()
        with open(json_file, 'wb') as fh:
            fh.write(data)
    except Exception as e:
        print("Error downloading the file. Error=" + str(e))


if __name__ == '__main__':

    load_data()
