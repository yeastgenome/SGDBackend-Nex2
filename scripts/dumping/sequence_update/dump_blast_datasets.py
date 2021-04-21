import sys
from scripts.loading.database_session import get_session
from src.models import Locusdbentity, Dnasequenceannotation, Taxonomy, Contig, So,\
                       Proteinsequenceannotation
from scripts.dumping.sequence_update import generate_not_feature_seq_file, generate_dna_seq_file,\
     generate_protein_seq_file

__author__ = 'sweng66'

notFeatFile = "scripts/dumping/sequence_update/data/blast/NotFeature.fsa"
codingFile = "scripts/dumping/sequence_update/data/blast/YeastORF.fsa"
genomicFile = "scripts/dumping/sequence_update/data/blast/YeastORF-Genomic.fsa"
oneKBFile = "scripts/dumping/sequence_update/data/blast/YeastORF-Genomic-1K.fsa"
proteinFile = "scripts/dumping/sequence_update/data/blast/YeastORF.pep"

rnaCodingFile = "scripts/dumping/sequence_update/data/blast/YeastRNA-coding.fsa"	
rnaGenomicFile = "scripts/dumping/sequence_update/data/blast/YeastRNA-genomic.fsa"
rnaGenomic1KFile = "scripts/dumping/sequence_update/data/blast/YeastRNA-genomic-1K.fsa"

TAXON = "TAX:559292"
SEQ_FORMAT = 'fasta'

def dump_data():

    nex_session = get_session()

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id

    dbentity_id_to_data = dict([(x.dbentity_id, (x.systematic_name, x.gene_name, x.sgdid, x.qualifier, x.description)) for x in nex_session.query(Locusdbentity).filter_by(dbentity_status = 'Active').all()])

    so_id_to_display_name = dict([(x.so_id, x.term_name) for x in nex_session.query(So).all()])
    
    contig_id_to_chr = dict([(x.contig_id, x.display_name) for x in nex_session.query(Contig).filter(Contig.display_name.like('Chromosome %')).all()])

    ### dump out DNA and protein sequences

    FILE_TYPE = 'ORF'
    
    generate_not_feature_seq_file(nex_session, taxonomy_id, dbentity_id_to_data,
                                  so_id_to_display_name, notFeatFile, SEQ_FORMAT)
    
    dbentity_id_to_defline = {}
    dbentity_id_list = []
    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, codingFile, 'CODING', SEQ_FORMAT, FILE_TYPE,
                          dbentity_id_to_defline, dbentity_id_list)
    
    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, genomicFile, 'GENOMIC', SEQ_FORMAT, FILE_TYPE)

    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, oneKBFile, '1KB', SEQ_FORMAT, FILE_TYPE)

    generate_protein_seq_file(nex_session, taxonomy_id, dbentity_id_to_defline, dbentity_id_list,
                              proteinFile, SEQ_FORMAT)

    ### dump out RNA sequences

    FILE_TYPE = 'RNA'
    
    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, rnaCodingFile, 'CODING', SEQ_FORMAT, FILE_TYPE)


    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, rnaGenomicFile, 'GENOMIC', SEQ_FORMAT, FILE_TYPE)


    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, rnaGenomic1KFile, '1KB', SEQ_FORMAT, FILE_TYPE)
        
    nex_session.close()

    
if __name__ == '__main__':

    dump_data()
