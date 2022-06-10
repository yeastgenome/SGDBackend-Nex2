import sys
from scripts.loading.database_session import get_session
from src.models import Locusdbentity, Dnasequenceannotation, Taxonomy, Contig, So
# from scripts.dumping.sequence_update import generate_not_feature_seq_file
from scripts.loading.alt_sequence_update import generate_not_feature_seq_file, generate_dna_seq_file, \
    generate_protein_seq_file

__author__ = 'sweng66'

dataDir = "scripts/loading/alt_sequence_update/data/"

SEQ_FORMAT = 'fasta'

def dump_data():

    nex_session = get_session()

    dbentity_id_to_data = dict([(x.dbentity_id, (x.systematic_name, x.gene_name, x.sgdid, x.qualifier, x.description)) for x in nex_session.query(Locusdbentity).filter_by(dbentity_status = 'Active').all()])

    so_id_to_display_name = dict([(x.so_id, x.term_name) for x in nex_session.query(So).all()])

    contig_id_to_header = dict([(x.contig_id, x.file_header) for x in nex_session.query(Contig).all()])
    
    strain_mapping = strain_to_taxon_id_filename()
    
    for strain in strain_mapping:

        (taxon, filename_prefix) = strain_mapping[strain]
        
        taxonomy = nex_session.query(Taxonomy).filter_by(taxid=taxon).one_or_none()
        taxonomy_id = taxonomy.taxonomy_id

        not_feature_file = dataDir + filename_prefix + 'intergenic_regions.fsa'

        generate_not_feature_seq_file(nex_session, strain, taxonomy_id, dbentity_id_to_data,
                                      so_id_to_display_name, not_feature_file, SEQ_FORMAT)
        
        FILE_TYPE = 'RNA'

        rna_genomic_file = dataDir + filename_prefix + 'rna_genomic.fsa'

        generate_dna_seq_file(nex_session, strain, taxonomy_id, contig_id_to_header, dbentity_id_to_data, 
                              so_id_to_display_name, rna_genomic_file, 'GENOMIC', SEQ_FORMAT, FILE_TYPE)
        
        rna_genomic_oneKB_file = dataDir + filename_prefix + 'rna_genomic_1kb.fsa'

        generate_dna_seq_file(nex_session, strain, taxonomy_id, contig_id_to_header, dbentity_id_to_data,	
                              so_id_to_display_name, rna_genomic_oneKB_file, '1KB', SEQ_FORMAT, FILE_TYPE)

        FILE_TYPE = 'ORF'

        orf_genomic_file = dataDir + filename_prefix + 'orf_genomic.fsa'

        dbentity_id_to_defline = {}
        dbentity_id_list = []
        generate_dna_seq_file(nex_session, strain, taxonomy_id, contig_id_to_header, dbentity_id_to_data,
                              so_id_to_display_name, orf_genomic_file, 'GENOMIC', SEQ_FORMAT, FILE_TYPE,
                              dbentity_id_to_defline, dbentity_id_list)

        orf_genomic_oneKB_file = dataDir + filename_prefix + 'orf_genomic_1kb.fsa'

        generate_dna_seq_file(nex_session, strain, taxonomy_id, contig_id_to_header, dbentity_id_to_data,
                              so_id_to_display_name, orf_genomic_oneKB_file, '1KB', SEQ_FORMAT, FILE_TYPE)

        protein_file = dataDir + filename_prefix + 'pep.fsa'

        
        generate_protein_seq_file(nex_session, taxonomy_id, dbentity_id_to_defline, dbentity_id_list,
                                  protein_file, SEQ_FORMAT)
        
    nex_session.close()


def strain_to_taxon_id_filename():

    return { 'CEN.PK':     ('NTR:115', 'CEN.PK2-1Ca_JRIV01000000_SGD_'), 
             'D273-10B':   ('NTR:101', 'D273-10B_JRIY00000000_SGD_'),
             'FL100':      ('TAX:947036', 'FL100_JRIT00000000_SGD_'),
             'JK9-3d':     ('NTR:104', 'JK9-3d_JRIZ00000000_SGD_'),
             'RM11-1a':    ('TAX:285006', 'RM11-1a_JRIP00000000_SGD_'),
             'SEY6210':    ('NTR:107', 'SEY6210_JRIW00000000_SGD_'),                
             'Sigma1278b': ('TAX:658763', 'Sigma1278b-10560-6B_JRIQ00000000_SGD_'),
             'SK1':        ('TAX:580239', 'SK1_NCSL00000000_SGD_'),
             'W303':       ('TAX:580240', 'W303_JRIU00000000_SGD_'),             
             'X2180-1A':   ('NTR:108', 'X2180-1A_JRIX00000000_SGD_'),                
             'Y55':        ('NTR:112', 'Y55_JRIF00000000_SGD_')
    }
                          
             
    
if __name__ == '__main__':

    dump_data()
