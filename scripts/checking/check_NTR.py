from sqlalchemy import or_
import sys
from src.models import Chebi, Edam, Obi, Psimod
from scripts.loading.database_session import get_session
import logging

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

TAXON = 'TAX:559292'

def check_data():

    nex_session = get_session()

    log.info("\n* CHEBI:\n")
    check_chebi(nex_session)   

    log.info("\n* EDAM:\n")
    check_edam(nex_session) 

    log.info("\n* OBI:\n")
    check_obi(nex_session)

    log.info("\n* PSIMOD:\n")
    check_psimod(nex_session)   

def check_psimod(nex_session):

    for x in nex_session.query(Psimod).filter(Psimod.format_name.like('NTR:%')).all():
        for y in nex_session.query(Psimod).filter(Psimod.format_name.like('MOD:%')).filter(Psimod.display_name.like( x.display_name )).all():
            log.info("\t" + x.format_name + " '" + x.display_name + "' is already in PSIMOD: " + y.format_name + " : '" + y.display_name + "'")

def check_obi(nex_session):    

    for x in nex_session.query(Obi).filter(Obi.format_name.like('NTR:%')).all():
        for y in nex_session.query(Obi).filter(Obi.display_name.like( x.display_name )).all():
            if y.format_name.startswith('NTR:'):
                continue
            log.info("\t" + x.format_name + " '" + x.display_name + "' is already in OBI: " + y.format_name + " : '" + y.display_name + "'")


def check_edam(nex_session):

    for x in nex_session.query(Edam).filter(Edam.format_name.like('NTR:%')).all():
        for y in nex_session.query(Edam).filter(Edam.format_name.like('EDAM:%')).filter(Edam.display_name.like( x.display_name )).all():
            log.info("\t" + x.format_name + " '" + x.display_name + "' is already in EDAM: " + y.format_name + " : '" + y.display_name + "'")
    
def check_chebi(nex_session):

    for x in nex_session.query(Chebi).filter(Chebi.format_name.like('NTR:%')).all():
        for y in nex_session.query(Chebi).filter(Chebi.format_name.like('CHEBI:%')).filter(Chebi.display_name.like( x.display_name )).all():
            log.info("\t" + x.format_name + " '" + x.display_name + "' is already in CHEBI: " + y.format_name + " : '" + y.display_name + "'") 
        
    
if __name__ == '__main__':

    check_data()
