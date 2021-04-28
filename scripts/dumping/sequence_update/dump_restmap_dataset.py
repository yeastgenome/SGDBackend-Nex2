import sys
from scripts.loading.database_session import get_session
from src.models import Locusdbentity, Dnasequenceannotation, Taxonomy, Contig, So,\
                       Proteinsequenceannotation
from scripts.dumping.sequence_update import generate_dna_seq_file

__author__ = 'sweng66'

genomicFile = "scripts/dumping/sequence_update/data/restrictionMapper/orf_genomic.seq"

TAXON = "TAX:559292"
SEQ_FORMAT = 'plain'
FILE_TYPE = 'ALL'

def dump_data():

    nex_session = get_session()

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id

    dbentity_id_to_data = dict([(x.dbentity_id, (x.systematic_name, x.gene_name, x.sgdid, x.qualifier, x.description)) for x in nex_session.query(Locusdbentity).filter_by(dbentity_status = 'Active').all()])

    so_id_to_display_name = dict([(x.so_id, x.term_name) for x in nex_session.query(So).all()])
    
    contig_id_to_chr = dict([(x.contig_id, x.display_name) for x in nex_session.query(Contig).filter(Contig.display_name.like('Chromosome %')).all()])
        
    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, genomicFile, 'GENOMIC', SEQ_FORMAT, FILE_TYPE)

    nex_session.close()

if __name__ == '__main__':

    dump_data()
    
