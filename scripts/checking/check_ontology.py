from sqlalchemy import or_
import sys
from src.models import Phenotype, PhenotypeannotationCond, Goextension, Interactor, \
                       Locusdbentity, Apo, Chebi, Disease, Ec, Eco, Edam, Go, Obi, \
                       Psimi, Psimod, So, Taxonomy, Goslim, ComplexGo, Datasetsample, \
                       ArchContig, ArchDnasequenceannotation, ArchDnasubsequence, \
                       Interactor, Dnasequenceannotation, Dnasubsequence, Alleledbentity,\
                       Referencedbentity, Referenceunlink, Bindingmotifannotation, \
                       Diseaseannotation, Diseasesubsetannotation, Enzymeannotation, \
                       Expressionannotation, Functionalcomplementannotation, \
                       Geninteractionannotation, Goannotation, Literatureannotation, \
                       Goslimannotation, Pathwayannotation, Phenotypeannotation, \
                       Physinteractionannotation, Posttranslationannotation, \
                       Proteindomainannotation, Proteinexptannotation, \
                       Proteinsequenceannotation, Proteinabundanceannotation, \
                       Regulationannotation, ArchLiteratureannotation, \
                       ArchProteinsequenceannotation, Straindbentity, Contig, \
                       Complexbindingannotation, Complexdbentity, Filedbentity
from scripts.loading.database_session import get_session
import logging

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

TAXON = 'TAX:559292'

def check_data():

    nex_session = get_session()

    log.info("\n* APO:\n")
    check_apo(nex_session)

    log.info("\n* CHEBI:\n")
    check_chebi(nex_session)   

    log.info("\n* DISEASE:\n")
    check_disease(nex_session)

    log.info("\n* EC:\n")
    check_ec(nex_session)

    log.info("\n* ECO:\n")
    check_eco(nex_session) 

    log.info("\n* EDAM:\n")
    check_edam(nex_session) 

    log.info("\n* GO:\n")
    check_go(nex_session)  

    log.info("\n* OBI:\n")
    check_obi(nex_session)
    
    log.info("\n* PSIMI:\n")
    check_psimi(nex_session)

    log.info("\n* PSIMOD:\n")
    check_psimod(nex_session)   

    log.info("\n* SO:\n")
    check_so(nex_session)

    log.info("\n* TAXONOMY:\n")
    check_taxonomy(nex_session)  
    
    ##= dict([(x.dbentity_id, (x.contig_id, x.so_id)) for x in nex_session.query(Dnasequenceannotation).filter_by(dna_type='GEN\OMIC', taxonomy_id=taxonomy_id).all()])   

def check_taxonomy(nex_session):

    for x in nex_session.query(Taxonomy).filter_by(is_obsolete=True).all():
        for tableClass in [ArchContig,
                           ArchDnasequenceannotation,
                           ArchLiteratureannotation,
                           ArchProteinsequenceannotation,
                           Bindingmotifannotation,
                           Contig,
                           Datasetsample,
                           Straindbentity,
                           Complexbindingannotation,
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
            rows = nex_session.query(tableClass).filter_by(taxonomy_id=x.taxonomy_id).all()
            if len(rows) > 0:
                etc = ''
                if len(rows) > 5:
                    rows = rows[0:5]
                    etc = ", ..."
                table = str(tableClass).split('.')[-1].replace('>', '')
                if tableClass in [ArchContig, Contig]:
                    message = "Obsolete TAXON ID: " + x.taxid+ " is used in '" + table + " table. contig_id = " + ", ".join([str(x.contig_id) for x in rows]) + etc
                elif tableClass == Datasetsample:
                    message = "Obsolete TAXON ID: " + x.taxid + " is used in '" + table + " table. datasetsample_id = " + ", ".join([str(x.datasetsample_id) for x in rows]) + etc
                elif tableClass == Straindbentity:
                    message = "Obsolete TAXON ID: " + x.taxid + " is used in '" + table + " table. dbentity_id = " + ", ".join([str(x.dbentity_id) for x in rows]) + etc
                else:
                    message = "Obsolete TAXON ID: " + x.taxid + " is used in '" + table + " table. annotation_id = " + ", ".join([str(x.annotation_id) for x in rows]) + etc
                log.info("\t" + message)
                    
def check_so(nex_session):

    for x in nex_session.query(So).filter_by(is_obsolete=True).all():
        for tableClass in [ArchContig, ArchDnasequenceannotation, ArchDnasubsequence,
                           Contig, Dnasequenceannotation, Dnasubsequence, Alleledbentity]:
            rows = nex_session.query(tableClass).filter_by(so_id=x.so_id).all()
            if len(rows) > 0:
                etc = ''
                if len(rows) > 5:
                    rows = rows[0:5]
                    etc = ", ..."
                table = str(tableClass).split('.')[-1].replace('>', '')
                if tableClass in [ArchContig, Contig]:
                    message = "Obsolete SOID: " + x.format_name + " is used in '" + table + " table. contig_id = " + ", ".join([str(x.contig_id) for x in rows]) + etc 
                elif tableClass in [ArchDnasubsequence, Dnasubsequence]:
                    message = "Obsolete SOID: " + x.format_name + " is used in '" + table + " table. dnasubsequence_id = " + ", ".join([str(x.dnasubsequence_id) for x in rows]) + etc
                elif tableClass == Alleledbentity:
                     message = "Obsolete SOID: " + x.format_name + " is used in '" + table + " table. dbentity_id = " + ", ".join([str(x.dbentity_id) for x in rows]) + etc
                else:
                    message = "Obsolete SOID: " + x.format_name + " is used in '" + table + " table. annotation_id = " + ", ".join([str(x.annotation_id) for x in rows]) + etc
                log.info("\t" + message)
                
def check_psimod(nex_session):

    for x in nex_session.query(Psimod).filter_by(is_obsolete=True).all():
        for tableClass in [Physinteractionannotation, Posttranslationannotation]:
            rows = nex_session.query(tableClass).filter_by(psimod_id=x.psimod_id).all()
            if len(rows) > 0:
                etc = ''
                if len(rows) > 5:
                    rows = rows[0:5]
                    etc = ", ..."
                table = str(tableClass).split('.')[-1].replace('>', '')
                message = "Obsolete PSIMOD ID: " + x.format_name + " is used in '" + table + " table. annotation_id = " + ", ".join([str(x.annotation_id) for x in rows]) + etc
                log.info("\t" + message)
                
def check_psimi(nex_session):
    
    for x in nex_session.query(Psimi).filter_by(is_obsolete=True).all():
        rows = nex_session.query(Interactor).filter(or_(Interactor.type_id==x.psimi_id, Interactor.role_id==x.psimi_id)).all()
        if len(rows) > 0:
            message = "Obsolete PSIMI ID " + x.format_name + " is used in 'Interactor' table. interactor_id = " + ", ".join([str(x.interactor_id) for x in rows])
            log.info("\t" + message)
            
def check_obi(nex_session):

    for x in nex_session.query(Obi).filter_by(is_obsolete=True).all():
        for tableClass in [Datasetsample, Phenotypeannotation, Proteinexptannotation]:
            rows = nex_session.query(tableClass).filter_by(assay_id=x.obi_id).all()
            if len(rows) > 0:
                etc = ''
                if len(rows) > 5:
                    rows = rows[0:5]
                    etc = ", ..."
                table = str(tableClass).split('.')[-1].replace('>', '')
                if tableClass == Datasetsample:
                    message = "Obsolete OBI ID: " + x.format_name + " is used in '" + table + " table. datasetsample_id = " + ", ".join([str(x.datasetsample_id) for x in rows]) + etc
                else:
                    message = "Obsolete OBI ID: " + x.format_name + " is used in '" + table + " table. annotation_id = " + ", ".join([str(x.annotation_id) for x in rows]) + etc
                log.info("\t" + message)
                    
def check_go(nex_session):

    for x in nex_session.query(Go).filter_by(is_obsolete=True).all():
        for tableClass in [Goannotation, Goslim, Proteinabundanceannotation, ComplexGo, Regulationannotation]:
            rows = None
            if tableClass == Proteinabundanceannotation:
                rows = nex_session.query(tableClass).filter_by(process_id=x.go_id).all()
            elif tableClass == Regulationannotation:
                rows = nex_session.query(tableClass).filter_by(happens_during=x.go_id).all()
            else:
                rows = nex_session.query(tableClass).filter_by(go_id=x.go_id).all()
            if len(rows) > 0:
                etc = ''
                if len(rows) > 5:
                    rows = rows[0:5]
                    etc = ", ..."
                table = str(tableClass).split('.')[-1].replace('>', '')
                if tableClass == ComplexGo:
                    message = "Obsolete GOID: " + x.format_name + " is used in '" + table + " table. complex_go_id = " + ", ".join([str(x.complex_go_id) for x in rows]) + etc
                elif tableClass == Goslim:
                    message = "Obsolete GOID: " + x.format_name + " is used in '" + table + " table. goslim_id = " + ", ".join([str(x.goslim_id) for x in rows]) + etc
                else:
                    message = "Obsolete GOID: " + x.format_name + " is used in '" + table + " table. annotation_id = " + ", ".join([str(x.annotation_id) for x in rows]) + etc
                log.info("\t" + message)

                
def check_edam(nex_session):

    for x in nex_session.query(Edam).filter_by(is_obsolete=True).all():
        rows = nex_session.query(Filedbentity).filter(or_(Filedbentity.topic_id==x.edam_id, Filedbentity.data_id==x.edam_id, Filedbentity.format_id==x.edam_id)).all()
        if len(rows) > 0:
            message = "Obsolete EDAM ID: " + x.format_name + " is used in 'Filedbentity' table. dbentity_id = " + ", ".join([str(x.dbentity_id) for x in rows])
            log.info(message)

def check_eco(nex_session):

    for x in nex_session.query(Eco).filter_by(is_obsolete=True).all():
        for tableClass in [Goannotation, Diseaseannotation,
                           Functionalcomplementannotation,
                           Complexdbentity, Regulationannotation,
                           Proteinabundanceannotation]:
            rows = None
            if tableClass == Proteinabundanceannotation:
                rows = nex_session.query(tableClass).filter_by(assay_id=x.eco_id).all()
            else:
                rows = nex_session.query(tableClass).filter_by(eco_id=x.eco_id).all()
            if len(rows) > 0:
                etc = ''
                if len(rows) > 5:
                    rows = rows[0:5]
                    etc = ", ..."
                table = str(tableClass).split('.')[-1].replace('>', '')
                if tableClass == Complexdbentity:
                    message = "Obsolete ECO ID: " + x.format_name + " is used in '" + table + " table. dbentity_id = " + ", ".join([str(x.dbentity_id) for x in rows]) + etc
                else:
                    message = "Obsolete ECO ID: " + x.format_name + " is used in '" + table + " table. annotation_id = " + ", ".join([str(x.annotation_id) for x in rows]) + etc
                log.info("\t" + message)

def check_ec(nex_session):
    
    for x in nex_session.query(Ec).filter_by(is_obsolete=True).all():
        for tableClass in [Pathwayannotation, Enzymeannotation]:
            rows = nex_session.query(tableClass).filter_by(ec_id=x.ec_id).all()
            if len(rows) > 0:
                table = str(tableClass).split('.')[-1].replace('>', '')
                message = "Obsolete EC number: " + x.format_name + " is used in '" + table + " table. annotation_id = " + ", ".join([str(x.annotation_id) for x in rows])
                log.info("\t" + message)
                
def check_disease(nex_session):

    for x in nex_session.query(Disease).filter_by(is_obsolete=True).all():
        rows = nex_session.query(Diseaseannotation).filter_by(disease_id=x.disease_id).all()
        if len(rows) > 0:
            message = "Obsolete DISEASE ID: " + x.format_name + " is used in 'Diseaseannotation' table. annotation_id = " + ", ".join([str(x.annotation_id) for x in rows])
            log.info("\t" + message)
    
def check_chebi(nex_session):

    validTerm = {}
    validChebi = {}
    validId = {}
    for x in nex_session.query(Chebi).filter_by(is_obsolete=False).all():
        validTerm[x.display_name] = 1
        validChebi[x.format_name] = 1
        validId[x.chebi_id] = 1

    invalidTerm = []
    for x in nex_session.query(PhenotypeannotationCond).filter_by(condition_class='chemical').all():
        if x.condition_name not in validTerm and x.condition_name not in invalidTerm:
            invalidTerm.append(x.condition_name)
    if len(invalidTerm) > 0:
        message = "\tfollowing chemical name(s) used in Phenotypeannotation_cond table is not valid 3-STAR chebi term:\n\n\t" + "\n\t".join(sorted(invalidTerm)) 
        log.info(message + "\n")

    invalidChebi = []
    for	x in nex_session.query(Goextension).filter(Goextension.dbxref_id.like('CHEBI:%')).all():
        if x.dbxref_id not in validChebi and x.dbxref_id not in invalidChebi:
            invalidChebi.append(x.dbxref_id)
    if len(invalidChebi) > 0:
        message = "\tfollowing CHEBI ID(s) used in Goextension table is not valid 3-STAR CHEBI ID:\n\n\t" + "\n\t".join(sorted(invalidChebi)) 
        log.info(message + "\n")

    invalidChebi = []
    for x in nex_session.query(Interactor).filter(Interactor.format_name.like('CHEBI:%')).all():
        if x.format_name not in validChebi and x.format_name not in invalidChebi:
            invalidChebi.append(x.format_name)
    if len(invalidChebi) > 0:
        message = "\tfollowing CHEBI ID(s) used in Interactor table is not valid 3-STAR CHEBI ID:\n\n\t" + "\n\t".join(sorted(invalidChebi))
        log.info(message + "\n")

    invalidId = []
    for x in nex_session.query(Proteinabundanceannotation).all():
        if x.process_id and x.process_id not in validId and x.process_id not in invalidId:
            invalidId.append(x.process_id)
    if len(invalidId) > 0:
        message = "\tfollowing chebi_id(s) used in Proteinabundanceannotation table is not valid 3-STAR CHEBI ID:\n\n\t" + "\n\t".join([str(x) for x in sorted(invalidId)])
        log.info(message)
    
def check_apo(nex_session):

    for x in nex_session.query(Apo).filter_by(is_obsolete=True).all():

        rows = nex_session.query(Phenotype).filter(or_(Phenotype.observable_id==x.apo_id, Phenotype.qualifier_id==x.apo_id)).all()
        if len(rows) > 0:
            message = "Obsolete APO ID: " + x.format_name + " is used in 'Phenotype' table. Phenotype_id = " + ", ".join([str(x.phenotype_id) for x in rows])
            log.info(message)

        rows = nex_session.query(Phenotypeannotation).filter(or_(Phenotypeannotation.mutant_id==x.apo_id, Phenotypeannotation.mutant_id==x.apo_id)).all()
        if len(rows) > 0:
            message = "Obsolete APO ID: " + x.format_name + " is used in 'Phenotype' table. Phenotype_id = " + ", ".join([str(x.annotation_id) for x in rows])
            log.info("\t" + message)
            
if __name__ == '__main__':

    check_data()
