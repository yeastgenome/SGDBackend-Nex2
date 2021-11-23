from sqlalchemy import or_
from datetime import datetime, timedelta
import sys
from src.models import Reservedname
from scripts.loading.database_session import get_session
import logging

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

TAXON = 'TAX:559292'

def check_data():

    nex_session = get_session()
    
    today = datetime.today() 

    reserved_name_list = []
    for x in nex_session.query(Reservedname).filter(Reservedname.expiration_date <= today).all():
        reserved_name_list.append(x.display_name)
            
    log.info("\n* Expired reserved gene name(s) :\n")

    if len(reserved_name_list) > 0:
        log.info("\t" + "\n\t".join([x for x in reserved_name_list]))
        
    nex_session.close()

if __name__ == '__main__':

    check_data()
