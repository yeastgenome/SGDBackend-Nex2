from sqlalchemy import or_
import sys
from src.models import Phenotype, Phenotypeannotation, PhenotypeannotationCond
from scripts.loading.database_session import get_session
import logging

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

def check_data():

    nex_session = get_session()

    phenotypes = nex_session.query(Phenotype).all()
    
    log.info("\n* Observables for classical phenotypes are associated with a qualifier:\n")
    observables = ['viable', 'inviable', 'auxotrophy', 'sterile', 'petite']
    check_observables(nex_session, phenotypes, observables, 'classical')
    
    log.info("\n* Phenotypes are curated by using top level observables:\n")
    observables = ['metabolism and growth', 'morphology', 'development', 'cellular processes',
                   'essentiality', 'interaction with host/environment', 'fitness']
    check_observables(nex_session, phenotypes, observables, 'top')

    log.info("\n* Phenotype annotations with observables like 'chemical compound*' or 'resistance to chemicals*' have no chemical condition. Annotation_id = \n")
    check_chemical_for_observables(nex_session)

    log.info("\n* Observables in ('%protein activity%', '%protein/peptide%', '%RNA%', 'prior%') without a reporter\n")
    check_reporter_for_observables(nex_session)
        
    nex_session.close()

def check_reporter_for_observables(nex_session):

    bad_annotations = []
    for x in nex_session.query(Phenotype).filter(or_(Phenotype.display_name.like('%protein activity%'), Phenotype.display_name.like('%protein/peptide%'), Phenotype.display_name.like('%RNA%'), Phenotype.display_name.like('prior%%'))).all():
        for y in nex_session.query(Phenotypeannotation).filter_by(phenotype_id=x.phenotype_id).all():
            if y.reporter_id is None:
                bad_annotations.append(y.annotation_id)

    if len(bad_annotations) > 0:
        log.info("\t" + "\n\t".join([str(x) for x in bad_annotations]))
    

def check_chemical_for_observables(nex_session):

    annotation_id_to_condition_id = dict([(x.annotation_id, x.condition_id) for x in nex_session.query(PhenotypeannotationCond).filter_by(condition_class='chemical').all()])
    
    bad_annotations = []
    for x in nex_session.query(Phenotype).filter(or_(Phenotype.display_name.like('chemical compound%'), Phenotype.display_name.like('resistance to chemicals%'))).all():
        for y in nex_session.query(Phenotypeannotation).filter_by(phenotype_id=x.phenotype_id).all():
            if y.annotation_id not in annotation_id_to_condition_id:
                bad_annotations.append(y.annotation_id)

    if len(bad_annotations) > 0:
        log.info("\t" + "\n\t".join([str(x) for x in bad_annotations]))
        
def check_observables(nex_session, phenotypes, observables, observable_type):

    bad_phenotypes = []
    for x in phenotypes:
        pieces = x.display_name.split(': ')
        if observable_type == 'classical':
            if pieces[0] in observables and len(pieces) > 1:
                bad_phenotypes.append(x.display_name + "\t(phenotype_id = " + str(x.phenotype_id) + ")")
        else:
            if pieces[0] in observables:
                bad_phenotypes.append(x.display_name + "\t(phenotype_id = " + str(x.phenotype_id) + ")")
            
    if len(bad_phenotypes) > 0:
        log.info("\t" + "\n\t".join(bad_phenotypes))
    
if __name__ == '__main__':

    check_data()
