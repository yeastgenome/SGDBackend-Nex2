from sqlalchemy import or_
import sys
from src.models import Taxonomy, Dbentity, Locusdbentity, So, Sgdid, Dnasequenceannotation,\
                       Referencedbentity, Referenceunlink, Bindingmotifannotation, \
                       Diseaseannotation, Diseasesubsetannotation, Enzymeannotation, \
                       Expressionannotation, Functionalcomplementannotation, \
                       Geninteractionannotation, Goannotation, Literatureannotation, \
                       Goslimannotation, Pathwayannotation, Phenotypeannotation, \
                       Physinteractionannotation, Posttranslationannotation, \
                       Proteindomainannotation, Proteinexptannotation, \
                       Proteinsequenceannotation, Proteinabundanceannotation, \
                       Regulationannotation, Referencedeleted, Journal, \
                       CurationReference
from scripts.loading.database_session import get_session
import logging

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

def check_data():

    nex_session = get_session()

    ###### references
    
    log.info("\n* References with not unique DOI:\n")
    check_doi(nex_session)
    
    ##### log.info("\n* References in Referenceunlink associated with same locus in one of annotations:\n")
    ##### check_referenceunlink(nex_session)
    
    log.info("\n* References in Referencedeleted also in Referencedbentity or Referenceunlink:\n")
    check_referencedeleted(nex_session) 

    log.info("\n* References ('Published) with an ISSN number journal do not have a page number:\n")
    # check_reference_page_number(nex_session)

    log.info("\n* References with manual GO, classical phenotypes or headlines do not have 'Primary Literature' topic:\n")
    check_primary_literature(nex_session)
    
    nex_session.close()
    
def check_primary_literature(nex_session):

    ref_id_locus_id_pair = dict([((x.reference_id, x.dbentity_id), x.annotation_id) for x in nex_session.query(Literatureannotation).filter_by(topic='Primary Literature').all()])

    no_primary_list = {}
    found = {}
    for x in nex_session.query(CurationReference).all():
        if x.curation_tag not in ['Headline information', 'GO information', 'Classical phenotype information']:
            continue
        key = (x.reference_id, x.dbentity_id)
        if key not in found:
            continue
        found[key] = 1
        if key not in ref_id_locus_id_pair:
            no_primary_list.append(key)
            
    if len(no_primary_list) > 0:
        log.info("\t(reference_id, dbentity_id):\n")
        log.info("t" + "\n\t".join([str(x) for x in no_primary_list]))
        
def check_reference_page_number(nex_session):

    journal_id_to_issn = dict([(x.journal_id, x.issn_print) for x in nex_session.query(Journal).all()])

    pmids_with_no_page = []
    for x in nex_session.query(Referencedbentity).filter_by(publication_status='Published').all():
        if x.journal_id is None:
            continue
        if x.journal_id in journal_id_to_issn and journal_id_to_issn[x.journal_id]:
            if x.pmid and x.page is None:
                pmids_with_no_page.append("PMID:" + str(x.pmid))

    if len(pmids_with_no_page) > 0:
        log.info("\t" + "\n\t".join(pmids_with_no_page))
    
    
def check_referencedeleted(nex_session):

    deletedPMID = dict([(x.pmid, x.referencedeleted_id) for x in nex_session.query(Referencedeleted).all()])

    ref_id_to_pmid = {}
    deletedPMID_in_reference = []
    for x in nex_session.query(Referencedbentity).all():
        if x.pmid is None:
            continue
        if x.pmid in deletedPMID: 
            deletedPMID_in_reference.append("PMID:" + str(x.pmid))
        ref_id_to_pmid[x.dbentity_id] = x.pmid 

    found = {}
    deletedPMID_in_referenceunlink = []
    for x in nex_session.query(Referenceunlink).all():
        if x.reference_id in found:
            continue
        found[x.reference_id] = 1
        if x.reference_id not in ref_id_to_pmid:
            continue
        pmid = ref_id_to_pmid[x.reference_id]
        if pmid in deletedPMID:
            deletedPMID_in_referenceunlink.append(("PMID:"+str(pmid), "REFERENCE_ID:"+str(x.reference_id))) 

    if len(deletedPMID_in_reference) > 0:
        log.info("\tThe following deleted PMIDs still in use (REFERENCEDBENTITY):\n")
        log.info("\t" + "\n\t".join(deletedPMID_in_reference))

    if len(deletedPMID_in_referenceunlink) > 0:
        log.info("\tThe following deleted PMIDs still in use (REFERENCEUNLINK):\n")
        log.info("\t" + "\n\t".join([str(x) for x in deletedPMID_in_referenceunlink]))
        
def check_referenceunlink(nex_session):

    ref_locus_pair = dict([((x.reference_id, x.dbentity_id), x.referenceunlink_id) for x in nex_session.query(Referenceunlink).all()])
    
    for tableClass in [Bindingmotifannotation,
                       Diseaseannotation,
                       Diseasesubsetannotation,
                       Dnasequenceannotation,
                       Enzymeannotation,
                       Expressionannotation,
                       Functionalcomplementannotation,
                       Geninteractionannotation,
                       Goannotation,
                       Goslimannotation,
                       Literatureannotation,
                       Pathwayannotation,
                       Phenotypeannotation,
                       Physinteractionannotation,
                       Posttranslationannotation,
                       Proteindomainannotation,
                       Proteinexptannotation,
                       Proteinsequenceannotation,
                       Proteinabundanceannotation,
                       Regulationannotation]:
        for x in nex_session.query(tableClass).all():
            if (x.reference_id, x.dbentity_id) in ref_locus_pair:
                table = str(tableClass).split('.')[-1].replace('>', '')
                message = "Obsolete TAXON ID '" + x.taxid + "' is used in '" + table + "' table. annotation_id = " + ", ".join([str(x.annotation_id) for x in annotations])
                log.info("\t" + message)


                
def check_doi(nex_session):

    doi_to_pmid = {}
    for x in nex_session.query(Referencedbentity).all():
        if x.doi:
            if x.doi in doi_to_pmid:
                log.info("\tDOI: " + x.doi + " PMID: " + str(doi_to_pmid[x.doi]) + ", " + str(x.pmid))
            doi_to_pmid[x.doi] = x.pmid
    
if __name__ == '__main__':

    check_data()
