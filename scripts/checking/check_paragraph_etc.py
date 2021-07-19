from sqlalchemy import or_
import sys
from src.models import Dbentity, Locusdbentity, Locussummary, Referencedbentity, \
                       Go, Reservedname, Colleague
from scripts.loading.database_session import get_session
import logging

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

def check_data():

    nex_session = get_session()
    
    ###### paragraphs, colleaguess
    
    (locus_id_to_bad_goids, locus_id_to_bad_ref_sgdids, locus_id_to_bad_gene_sgdids) = retrieve_ids_from_paragraphs(nex_session)

    log.info("\n* SGDIDs for Genes in paragraphs are not Primary SGDID:\n")
    check_sgdids_for_gene_in_paragraphs(nex_session, locus_id_to_bad_gene_sgdids)

    log.info("\n* SGDIDs for References in paragraphs are not Primary SGDID:\n")
    check_sgdids_for_ref_in_paragraphs(nex_session, locus_id_to_bad_ref_sgdids)
    
    log.info("\n* GOIDs in paragraphs are not in GO table or is an obsolete GOID:\n")
    check_goids_in_paragraphs(nex_session, locus_id_to_bad_goids)
    
    log.info("\n* Collegues in RESERVEDNAME table have no email address:\n")
    check_colleagues(nex_session)

    nex_session.close()

def check_colleagues(nex_session):

    colleagues = []
    for x in nex_session.query(Reservedname).all(): 
        coll = nex_session.query(Colleague).filter_by(colleague_id=x.colleague_id).one_or_none()
        if coll.email is None and x.colleague_id not in colleagues:
            colleagues.append(x.colleague_id)

    if len(colleagues):
        log.info("\t" + "\n\t".join([str(x) for x in colleagues]))    
        
def check_goids_in_paragraphs(nex_session, locus_id_to_bad_goids):

    for locus_id in locus_id_to_bad_goids:
        x = nex_session.query(Locusdbentity).filter_by(dbentity_id=locus_id).one_or_none()
        log.info("\t" + x.systematic_name + ": " + ", ".join(locus_id_to_bad_goids[locus_id]))
    
def check_sgdids_for_ref_in_paragraphs(nex_session, locus_id_to_bad_ref_sgdids):

    for locus_id in locus_id_to_bad_ref_sgdids:
        x = nex_session.query(Locusdbentity).filter_by(dbentity_id=locus_id).one_or_none()
        log.info("\t" + x.systematic_name + ": " + ", ".join(locus_id_to_bad_ref_sgdids[locus_id]) + "\n")
    
def check_sgdids_for_gene_in_paragraphs(nex_session, locus_id_to_bad_gene_sgdids):

    for locus_id in locus_id_to_bad_gene_sgdids:
        x = nex_session.query(Locusdbentity).filter_by(dbentity_id=locus_id).one_or_none()
        log.info("\t" + x.systematic_name + ": " + ", ".join(locus_id_to_bad_gene_sgdids[locus_id]) + "\n")
                 
def compose_goid(goid):

    stop = 7 - len(goid)
    for i in range(stop):
        goid = '0' + goid
    return "GO:" + goid

def retrieve_ids_from_paragraphs(nex_session):

    ## <a href="/locus/S000001855">ACT1</a> encodes the single essential gene for actin (<reference:S000073423>, <reference:S000073427>, <reference:S000057332>). Actin is a ubiquitous, conserved cytoskeletal element critical for many cellular processes. The large collection of <a href="/locus/S000001855">act1</a> ... <a href="/go/32432"> actin cables</a>, an actin-myosin <a href="/go/142"> contractile ring</a>, and <a href="/go/30479"> a

    # GO:0032991 
    goid_to_go_id = dict([(x.goid, x.go_id) for x in nex_session.query(Go).filter_by(is_obsolete=False).all()])
    ref_sgdid_to_ref_id = dict([(x.sgdid, x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='REFERENCE').all()])
    locus_sgdid_to_locus_id = dict([(x.sgdid, x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='LOCUS').all()])
    
    locus_id_to_bad_goids = {}
    locus_id_to_bad_ref_sgdids = {}
    locus_id_to_bad_gene_sgdids = {}
    for x in nex_session.query(Locussummary).filter_by(summary_type='Gene').all():        
        for word in x.html.split(' '):
            if '"/locus/S' in word:
                word = word.replace('"', '')
                sgdid = word.split(">")[0].split('/')[-1]
                if sgdid.startswith('S00') and sgdid not in locus_sgdid_to_locus_id:
                    sgdid_list = [] 
                    if x.locus_id in locus_id_to_bad_gene_sgdids:
                        sgdid_list = locus_id_to_bad_gene_sgdids[x.locus_id]
                    if sgdid not in sgdid_list:
                        sgdid_list.append(sgdid)
                    locus_id_to_bad_gene_sgdids[x.locus_id] = sgdid_list
            if '<reference:S00' in word:
                try:
                    sgdid = word.split('>')[0].split(':')[1]
                except:
                    continue
                if sgdid.startswith('S00') and sgdid not in ref_sgdid_to_ref_id:
                    sgdid_list = []
                    if x.locus_id in locus_id_to_bad_ref_sgdids:
                        sgdid_list = locus_id_to_bad_ref_sgdids[x.locus_id]
                    if sgdid not in sgdid_list:
                        sgdid_list.append(sgdid)
                    locus_id_to_bad_ref_sgdids[x.locus_id] = sgdid_list
            if '"/go/' in word:
                word = word.replace('"', '')
                goid = word.split(">")[0].split('/')[-1]
                goid = compose_goid(goid)
                if goid not in goid_to_go_id:
                    goid_list = []
                    if x.locus_id in locus_id_to_bad_goids:
                        sgdid_list = locus_id_to_bad_goids[x.locus_id]
                    if goid not in goid_list:
                        goid_list.append(goid)
                    locus_id_to_bad_goids[x.locus_id] = goid_list

    return (locus_id_to_bad_goids, locus_id_to_bad_ref_sgdids, locus_id_to_bad_gene_sgdids)


if __name__ == '__main__':

    check_data()
