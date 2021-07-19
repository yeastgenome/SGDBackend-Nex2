from sqlalchemy import or_
import sys
from src.models import Taxonomy, Dbentity, Locusdbentity, So, Sgdid, Dnasequenceannotation
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
    
    locusData = nex_session.query(Locusdbentity).all()
    dbentity_id_to_contig_so_id = dict([(x.dbentity_id, (x.contig_id, x.so_id)) for x in nex_session.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC', taxonomy_id=taxonomy_id).all()])

    ###### features
    
    log.info("\n* Features with not unique gene name:\n")
    check_unique_gene_name(nex_session, locusData)

    log.info("\n* Features with genetic position information not associated with a chromosome:\n")
    check_genetic_mapped_genes(nex_session, locusData, dbentity_id_to_contig_so_id)

    log.info("\n* Features with qualifier not associated with ORF:\n")
    check_orf_features(nex_session, locusData, dbentity_id_to_contig_so_id)

    log.info("\n* Features ('Active') with 'Deleted' SGDIDs:\n")
    # check_sgdid_status_for_active_dbentity_rows(nex_session)
    
    nex_session.close()
    
def check_sgdid_status_for_active_dbentity_rows(nex_session):

    # select * from nex.dbentity where dbentity_status = 'Active' and sgdid in 
    # (select display_name from nex.sgdid where sgdid_status = 'Deleted'); 
    sgdid_to_status= dict([(x.display_name, x.sgdid_status) for x in nex_session.query(Sgdid).all()])

    for subclass in ['LOCUS', 'REFERENCE', 'ALLELE', 'STRAIN', 'COMPLEX', 'FILE', 'PATHWAY', 'TRANSCRIPT']:
        for x in nex_session.query(Dbentity).filter_by(subclass=subclass).all():
            if x.sgdid not in sgdid_to_status:
                log.info("\tSGDID: " + x.sgdid + " is not in sgdid table.")
                continue
            if sgdid_to_status[x.sgdid] == 'Deleted':
                log.info("\t" + x.subclass + ": " + x.display_name)
                           
                        
def check_orf_features(nex_session, locusData, dbentity_id_to_contig_so_id):

    ## STA1
    
    so = nex_session.query(So).filter_by(display_name='ORF').one_or_none()

    for x in locusData:
        if x.dbentity_status != 'Active':
            continue
        if x.qualifier:
            if x.dbentity_id not in dbentity_id_to_contig_so_id:
                log.info("\t" + x.systematic_name)
                continue
            (contig_id, so_id) = dbentity_id_to_contig_so_id[x.dbentity_id]
            if so_id != so_id:
                log.info("\t" + x.systematic_name)
                
def check_genetic_mapped_genes(nex_session, locusData, dbentity_id_to_contig_so_id):

    for x in locusData:
        if x.genetic_position is None:
            continue
        if x.dbentity_id not in dbentity_id_to_contig_so_id:
            name = x.systematic_name
            if x.gene_name and x.gene_name != name:
                name = x.gene_name + "/" + name
            log.info("\t" + name) 
    
def check_unique_gene_name(nex_session, locusData):
    
    # update nex.locusdbentity set gene_name = 'ACT1' where systematic_name = 'YDL041W';

    gene2systematicNm = {}
    for x in locusData:
        if x.gene_name is None:
            continue
        if x.gene_name in gene2systematicNm:
            log.info("\t" + x.gene_name + ": associated with " + gene2systematicNm[x.gene_name] + " and " + x.systematic_name)
            continue
        gene2systematicNm[x.gene_name] = x.systematic_name
        

if __name__ == '__main__':

    check_data()
