import logging
import urllib
import os
from datetime import datetime
import sys
from src.models import Dbentity, LocusAlias
from scripts.loading.database_session import get_session

__author__ = 'sweng66'


logging.basicConfig(format='%(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']
ALIAS_TYPE = 'RNAcentral ID'
OBJ_ROOT_URL = 'http://rnacentral.org/rna/'


def load_ids(mapping_file):

    nex_session = get_session()

    sgdid_to_locus_id = dict([(x.sgdid, x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(
        subclass='LOCUS').all()])

    rna_id_to_locus_ids_db = {}
    source_id = None
    for x in nex_session.query(LocusAlias).filter_by(alias_type='RNAcentral ID').all():
        if not source_id:
            source_id = x.source_id
        locus_ids = rna_id_to_locus_ids_db.get(x.display_name, [])
        locus_ids.append(x.locus_id)
        rna_id_to_locus_ids_db[x.display_name] = locus_ids

    f = open(mapping_file)
    rna_id_to_locus_ids_ebi = {}
    for line in f:
        pieces = line.split('\t')
        rna_id = pieces[0] + "_" + pieces[3]
        locus_id = sgdid_to_locus_id.get(pieces[2])
        if locus_id is None:
            continue
        locus_ids = rna_id_to_locus_ids_ebi.get(rna_id, [])
        locus_ids.append(locus_id)
        rna_id_to_locus_ids_ebi[rna_id] = locus_ids
    f.close()

    for rna_id in rna_id_to_locus_ids_ebi:
        locus_ids_db = rna_id_to_locus_ids_db.get(rna_id, [])
        locus_ids_ebi = rna_id_to_locus_ids_ebi[rna_id]
        for locus_id in locus_ids_ebi:
            if locus_id not in locus_ids_db:
                # print("TO ADD: ", rna_id, locus_id)
                insert_locus_alias(nex_session, source_id, locus_id, rna_id)
        for locus_id in	locus_ids_db:
            if locus_id	not in locus_ids_ebi:
                # print("TO DELETE: ", rna_id, locus_id)
                delete_locus_alias(nex_session, locus_id, rna_id)
        
    for rna_id in rna_id_to_locus_ids_db:
        if rna_id in rna_id_to_locus_ids_ebi:
            continue
        for locus_id in rna_id_to_locus_ids_db[rna_id]:
            # print ("TO DELETE: ", rna_id, locus_id)
            delete_locus_alias(nex_session, locus_id, rna_id)


    # nex_session.rollback()
    nex_session.commit()
    nex_session.close()


def delete_locus_alias(nex_session, locus_id, rna_id):

    x = nex_session.query(LocusAlias).filter_by(locus_id=locus_id, display_name=rna_id, alias_type=ALIAS_TYPE).one_or_none()
    if x:
        try:
            nex_session.delete(x)
            logger.info(f"Deleting RNAcentral ID: {rna_id} from database for locus_id = {locus_id}")
        except Exception as e:
            logger.info(f"Error deleting RNAcentral ID: {rna_id} from database for locus_id = {locus_id}: {e}")


def insert_locus_alias(nex_session, source_id, locus_id, rna_id):

    try:
        x = LocusAlias(source_id=source_id,
                       locus_id=locus_id,
                       display_name=rna_id,
                       obj_url=OBJ_ROOT_URL + rna_id,
                       has_external_id_section=True,
                       alias_type=ALIAS_TYPE,
                       created_by=CREATED_BY);
        nex_session.add(x)
        logger.info(f"Adding RNAcentral ID: {rna_id} into database for locus_id = {locus_id}")
    except Exception as e:
        logger.info(f"Error adding RNAcentral ID: {rna_id} into database for locus_id = {locus_id}: {e}")


if __name__ == "__main__":

    url_path = 'https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/id_mapping/database_mappings/'
    mapping_file = 'sgd.tsv'
    urllib.request.urlretrieve(url_path + mapping_file, mapping_file)
    urllib.request.urlcleanup()

    load_ids(mapping_file)


    
        
