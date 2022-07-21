from sqlalchemy import or_
import sys
from src.models import Taxonomy, Dbentity, Locusdbentity, Dnasequenceannotation,\
                       Goannotation, Go, GoRelation, Goslim, So, Source
from scripts.loading.database_session import get_session
import logging

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

TAXON = 'TAX:559292'

def check_data():

    nex_session = get_session()

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id

    locus_id_to_name = dict([(x.dbentity_id, x.systematic_name) for x in nex_session.query(Locusdbentity).all()])
    
    dbentity_id_to_contig_so_id = dict([(x.dbentity_id, (x.contig_id, x.so_id)) for x in nex_session.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC', taxonomy_id=taxonomy_id).all()])
    is_deleted = dict([(x.dbentity_id, x.display_name) for x in nex_session.query(Dbentity).filter(or_(Dbentity.dbentity_status=='Deleted', Dbentity.dbentity_status=='Merged')).all()])
    go_id_to_aspect = dict([(x.go_id, x.go_namespace) for x in nex_session.query(Go).filter_by(is_obsolete=False).all()])
    
    # log.info("\n* Deleted SGDIDs with a row in DBENTITY table:\n")
    # log.info("\n* Deleted SGDIDs used in GO annotations:\n")
    
    log.info("\n* GO: deleted/merged features with GO annotations:\n")
    check_deleted_merged_for_go(nex_session, is_deleted)
    
    log.info("\n* GO: ORF/RNA features without a positive annotation in each aspect:\n")
    # ORFs and RNA features should have at least 1 positive annotation in each 
    # aspect (P, F, or C). This is an annotation that is not associated with a 
    # NOT qualifier.    
    check_orf_rna_for_go(nex_session, is_deleted, dbentity_id_to_contig_so_id,
                         go_id_to_aspect, locus_id_to_name)
    
    log.info("\n* GO: features with an unknown annotation (annotation to the root term) and an annotation to a more granular term:\n")
    check_go_unknown_granular_terms(nex_session, go_id_to_aspect, locus_id_to_name)
    
    log.info("\n* GO: orphan GO terms (no parent and no child):\n")
    check_orphan_go_terms(nex_session)
    
    log.info("\n* GO: macromolecular complex terms: children of GO:0032991 are used to annotate SGD genes and NOT already in the goslim table:\n")
    check_macromacromolecular_complex_term(nex_session)
    
    #Features with the feature type not listed below should not have rows in GO_ANNOTATION.
    # ORF
    # ncRNA
    # not in systematic sequence of S288C
    # pseudogene
    # rRNA
    # snRNA
    # snoRNA
    # tRNA
    # transposable_element_gene
    
    nex_session.close()

                    
def get_child_ids(nex_session, parent_id, all_complex_terms):

    for x in nex_session.query(GoRelation).filter_by(parent_id=parent_id):
        if x.child_id in all_complex_terms:
            continue
        all_complex_terms[x.child_id] = (x.child.goid, x.child.display_name)
        get_child_ids(nex_session, x.child_id, all_complex_terms)
        
def check_macromacromolecular_complex_term(nex_session):
    
    # 293865    GO:0032991      protein-containing complex
    
    all_complex_terms = {}
    go = nex_session.query(Go).filter_by(goid='GO:0032991').one_or_none()
    go_id = go.go_id
    all_complex_terms[go_id] = (go.goid, go.display_name)

    src = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = src.source_id
    
    get_child_ids(nex_session, go_id, all_complex_terms)

    goslim_go_id = dict([(x.go_id, x.goslim_id) for x in nex_session.query(Goslim).filter_by(slim_name='Macromolecular complex terms').all()]) 

    not_in_goslim = []
    for x in nex_session.query(Goannotation).filter_by(source_id=source_id).filter(or_(Goannotation.annotation_type=='manually curated', Goannotation.annotation_type=='high-throughput')).all():
        if x.go_id not in all_complex_terms:
            continue
        if x.go_id not in goslim_go_id and all_complex_terms[x.go_id] not in not_in_goslim:
            not_in_goslim.append(all_complex_terms[x.go_id])

    if len(not_in_goslim) > 0:
        log.info("\t" + "\n\t".join([str(x) for x in not_in_goslim]))
    
def check_orphan_go_terms(nex_session):

    go_id_in_relation = {}
    for x in nex_session.query(GoRelation).all():
        go_id_in_relation[x.parent_id] = 0
        go_id_in_relation[x.child_id] = 0

    orphan_goid = []
    for x in nex_session.query(Go).filter_by(is_obsolete=False).all():
        if x.go_id not in go_id_in_relation:
            orphan_goid.append(x.goid)
            
    if len(orphan_goid):
        log.info("\t" + "\n\t".join(orphan_goid))
        
def check_go_unknown_granular_terms(nex_session, go_id_to_aspect, locus_id_to_name):
    
    # select * from nex.goannotation where go_id = 290848 and annotation_type != 'computational';

    # GO:0008150  biological process
    # GO:0005575  cellular component
    # GO:0003674   molecular function

    go = nex_session.query(Go).filter_by(goid='GO:0008150').one_or_none()
    process_root_go_id = go.go_id
    go = nex_session.query(Go).filter_by(goid='GO:0005575').one_or_none()
    component_root_go_id = go.go_id
    go = nex_session.query(Go).filter_by(goid='GO:0003674').one_or_none()
    function_root_go_id = go.go_id

    dbentity_id_to_root_process = {}
    dbentity_id_to_root_function = {}
    dbentity_id_to_root_component= {}

    dbentity_id_to_granular_process = {}
    dbentity_id_to_granular_function = {}
    dbentity_id_to_granular_component= {}

    for x in nex_session.query(Goannotation).filter(or_(Goannotation.annotation_type=='manually curated', Goannotation.annotation_type=='high-throughput')).all():
        if x.go_id not in go_id_to_aspect:
            continue
        if x.go_id == process_root_go_id:
            dbentity_id_to_root_process[x.dbentity_id] = 1
        elif x.go_id == function_root_go_id:
            dbentity_id_to_root_function[x.dbentity_id] = 1
        elif x.go_id == component_root_go_id:
            dbentity_id_to_root_component[x.dbentity_id] = 1
        elif go_id_to_aspect[x.go_id] == 'biological process':
            dbentity_id_to_granular_process[x.dbentity_id] = 1
        elif go_id_to_aspect[x.go_id] == 'molecular function':
            dbentity_id_to_granular_function[x.dbentity_id] = 1
        else:
            dbentity_id_to_granular_component[x.dbentity_id] = 1

    has_both_root_granular_process = []
    for dbentity_id in dbentity_id_to_root_process:
        key = locus_id_to_name[dbentity_id] + ": " + str(dbentity_id)
        if dbentity_id in dbentity_id_to_granular_process:
            has_both_root_granular_process.append(key)
    if len(has_both_root_granular_process) > 0:
        log.info("\tfollowing features have been annotated to both root PROCESS term and a more granular PROCESS term: systematic_name: dbentity_id = \n")
        log.info("\t" + "\n\t".join(has_both_root_granular_process) + "\n")
            
    has_both_root_granular_function = []
    for	dbentity_id in dbentity_id_to_root_function:
        key = locus_id_to_name[dbentity_id] + ": " + str(dbentity_id)
        if dbentity_id in dbentity_id_to_granular_function:
            has_both_root_granular_function.append(key)
    if len(has_both_root_granular_function) > 0:
        log.info("\tfollowing features have been annotated to both root FUNCTION term and a more granular FUNCTION term: systematic_name: dbentity_id = \n")
        log.info("\t" + "\n\t".join(has_both_root_granular_function) + "\n")
            
    has_both_root_granular_component= []
    for dbentity_id in dbentity_id_to_root_component:
        key = locus_id_to_name[dbentity_id] + ": " + str(dbentity_id)
        if dbentity_id in dbentity_id_to_granular_component:
            has_both_root_granular_component.append(key)
    
    if len(has_both_root_granular_component) > 0:
        log.info("\tfollowing features have been annotated to both root COMPONENT term and a more granular COMPONENT term: systematic_name: dbentity_id = \n")
        log.info("\t" + "\n\t".join(has_both_root_granular_component))

def check_orf_rna_for_go(nex_session, is_deleted, dbentity_id_to_contig_so_id, go_id_to_aspect, locus_id_to_name):

    so_term = ['ORF', 'ncRNA_gene', 'snoRNA_gene', 'snRNA_gene', 'tRNA_gene',
               'rRNA_gene', 'telomerase_RNA_gene']
    
    so_ids = []
    for x in nex_session.query(So).all():
        if x.display_name in so_term:
            so_ids.append(x.so_id)
            
    dbentity_to_component = {}
    dbentity_to_process = {}
    dbentity_to_function = {}

    for x in nex_session.query(Goannotation).filter(Goannotation.go_qualifier != 'NOT').filter(or_(Goannotation.annotation_type=='manually curated', Goannotation.annotation_type=='high-throughput')).all():
        if x.go_id not in go_id_to_aspect:
            continue
        aspect = go_id_to_aspect[x.go_id]
        if aspect == 'molecular function':
            dbentity_to_function[x.dbentity_id] = 1
        elif aspect == 'biological process':
            dbentity_to_process[x.dbentity_id] = 1
        else:
            dbentity_to_component[x.dbentity_id] = 1

    missing_function = []
    missing_process = []
    missing_component = []
    for dbentity_id in dbentity_id_to_contig_so_id:
        if dbentity_id in is_deleted:
            continue
        (contig_id, so_id) = dbentity_id_to_contig_so_id[dbentity_id]
        if so_id not in so_ids:
            continue
        key = locus_id_to_name[dbentity_id] + ": " + str(dbentity_id)
        if dbentity_id not in dbentity_to_function:
            missing_function.append(key)
        if dbentity_id not in dbentity_to_process:
            missing_process.append(key)
        if dbentity_id not in dbentity_to_component:
            missing_component.append(key)

    if len(missing_function) > 0:
        log.info("\tfeatures missing function annotation. systematic_name: dbentity_id = \n")
        log.info("\t" + "\n\t".join(missing_function) + "\n")
        
    if len(missing_process) > 0:
        log.info("\tfeatures missing process annotation. systematic_name: dbentity_id = \n")
        log.info("\t" + "\n\t".join(missing_process) + "\n")

    if len(missing_component) > 0:
        log.info("\tfeatures missing component annotation. systematic_name: dbentity_id = \n")
        log.info("\t" + "\n\t".join(missing_component))
            
def check_deleted_merged_for_go(nex_session, is_deleled):

    is_deleted = dict([(x.dbentity_id, x.display_name) for x in nex_session.query(Dbentity).filter(or_(Dbentity.dbentity_status=='Deleted', Dbentity.dbentity_status=='Merged')).all()])

    data = []
    for x in nex_session.query(Goannotation).all():
        if x.dbentity_id in is_deleted:
            key = (is_deleted[x.dbentity_id], x.dbentity_id)
            if key not in data:
                data.append(key)
    if len(data) > 0:
        log.info("\tDeleted/Merged feature name and dbentity_id:\n")
        log.info("\t" + "\n\t".join([str(x) for x in data]))
    
if __name__ == '__main__':

    check_data()
