from sqlalchemy import or_
from datetime import datetime, timedelta
import sys
from src.models import Dbentity, Referencedbentity, Filedbentity
from scripts.loading.database_session import get_session
import logging

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

TAXON = 'TAX:559292'

def check_data():

    nex_session = get_session()

    dbentity_id_to_pmid = dict([(x.dbentity_id, x.pmid) for x in nex_session.query(Referencedbentity).all()])
    display_name_to_dbentity_id = dict([(x.display_name, x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='FILE').all()])
    dbentity_id_to_s3_url = dict([(x.dbentity_id, x.s3_url) for x in nex_session.query(Filedbentity).all()])
    
    seven_days_ago = datetime.today() - timedelta(days = 7)

    pmids_without_suppl_file = []
    pmids_without_file_uploaded = []

    for x in nex_session.query(Dbentity).filter_by(subclass = 'REFERENCE').filter(Dbentity.date_created >= seven_days_ago).all():
        pmid = dbentity_id_to_pmid.get(x.dbentity_id)
        if pmid is None:
            continue
        suppl_file_name = str(pmid) + ".zip"
        dbentity_id_for_suppl_file = display_name_to_dbentity_id.get(suppl_file_name)
        if dbentity_id_for_suppl_file is None:
            pmids_without_suppl_file.append(pmid)
        else:
            s3_url = dbentity_id_to_s3_url.get(dbentity_id_for_suppl_file)
            if s3_url is None:
                pmids_without_file_uploaded.append(pmid)

    log.info("\n* Papers added in the past week without a suppl file:\n")

    if len(pmids_without_suppl_file) > 0:
        log.info("\t" + "\n\t".join([str(x) for x in pmids_without_suppl_file]))

    log.info("\n* Papers added in the past week without a suppl file uploaded (but the metadata is in the database:\n")    

    if len(pmids_without_file_uploaded) > 0:
        log.info("\t" + "\n\t".join([str(x) for x in pmids_without_file_uploaded]))
        
    nex_session.close()

if __name__ == '__main__':

    check_data()
