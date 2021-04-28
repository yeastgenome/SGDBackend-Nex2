import sys
from scripts.loading.database_session import get_session
from src.models import Locusdbentity, Dnasequenceannotation, Taxonomy, Contig, So,\
                       Proteinsequenceannotation
from scripts.dumping.sequence_update import generate_not_feature_seq_file, \
     generate_dna_seq_file, generate_protein_seq_file

__author__ = 'sweng66'

notFeatFile = "scripts/dumping/sequence_update/data/sequence_for_download/NotFeature.fasta"

allCodingFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_coding_all.fasta"
codingFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_coding.fasta"
dubiousCodingFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_coding_dubious.fasta"

allGenomicFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_genomic_all.fasta"
genomicFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_genomic.fasta"
dubiousGenomicFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_genomic_dubious.fasta"

allGenomic1KFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_genomic_1000_all.fasta"
genomic1KFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_genomic_1000.fasta"
dubiousGenomic1KFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_genomic_1000_dubious.fasta"

allProteinFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_trans_all.fasta"
proteinFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_trans.fasta"
dubiousProteinFile = "scripts/dumping/sequence_update/data/sequence_for_download/orf_trans_dubious.fasta"

rnaCodingFile = "scripts/dumping/sequence_update/data/sequence_for_download/rna_coding.fasta"	
rnaGenomicFile = "scripts/dumping/sequence_update/data/sequence_for_download/rna_genomic.fasta"
rnaGenomic1KFile = "scripts/dumping/sequence_update/data/sequence_for_download/rna_genomic_1000.fasta"

otherGenomicFile = "scripts/dumping/sequence_update/data/sequence_for_download/other_features_genomic.fasta"
otherGenomic1KFile = "scripts/dumping/sequence_update/data/sequence_for_download/other_features_genomic_1000.fasta"

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
                          so_id_to_display_name, allCodingFile, 'CODING', SEQ_FORMAT, FILE_TYPE,
                          dbentity_id_to_defline, dbentity_id_list)

    generate_dubious_none_dubious_files(allCodingFile, codingFile, dubiousCodingFile)
    
    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, allGenomicFile, 'GENOMIC', SEQ_FORMAT, FILE_TYPE)

    generate_dubious_none_dubious_files(allGenomicFile, genomicFile, dubiousGenomicFile)
    
    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, allGenomic1KFile, '1KB', SEQ_FORMAT, FILE_TYPE)

    generate_dubious_none_dubious_files(allGenomic1KFile, genomic1KFile, dubiousGenomic1KFile)

    generate_protein_seq_file(nex_session, taxonomy_id, dbentity_id_to_defline, dbentity_id_list,
                              allProteinFile, SEQ_FORMAT)

    generate_dubious_none_dubious_files(allProteinFile, proteinFile, dubiousProteinFile)

    
    ### dump out RNA sequences

    FILE_TYPE = 'RNA'
    
    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, rnaCodingFile, 'CODING', SEQ_FORMAT, FILE_TYPE)


    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, rnaGenomicFile, 'GENOMIC', SEQ_FORMAT, FILE_TYPE)


    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                          so_id_to_display_name, rnaGenomic1KFile, '1KB', SEQ_FORMAT, FILE_TYPE)


    ### dump sequences for other features

    FILE_TYPE = 'other'
    
    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                                    so_id_to_display_name, otherGenomicFile, 'GENOMIC', SEQ_FORMAT, FILE_TYPE)

    generate_dna_seq_file(nex_session, taxonomy_id, dbentity_id_to_data, contig_id_to_chr,
                                    so_id_to_display_name, otherGenomic1KFile, '1KB', SEQ_FORMAT, FILE_TYPE)

    
    nex_session.close()

def generate_dubious_none_dubious_files(allSeqFile, seqFile, dubiousSeqFile):

    f = open(allSeqFile)
    fw = open(seqFile, "w")
    fw2 = open(dubiousSeqFile, "w")

    isDubious = 0
    for line in f:
        if line.startswith('>'):
            if ', Dubious ORF, ' in line:
                fw2.write(line)
                isDubious = 1
            else:
                fw.write(line)
                isDubious = 0
        else:
            if isDubious == 1:
                fw2.write(line)
            else:
                fw.write(line)
    f.close()
    fw.close()
    fw2.close()
    
    
if __name__ == '__main__':

    dump_data()
