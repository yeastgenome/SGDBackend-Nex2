import sys
from scripts.loading.database_session import get_session
from src.models import Locusdbentity, Dnasequenceannotation, Taxonomy, Contig, So,\
                       Proteinsequenceannotation
from scripts.dumping.sequence_update import generate_not_feature_seq_file, generate_dna_seq_file,\
     generate_protein_seq_file

__author__ = 'sweng66'

locusFile = "scripts/dumping/sequence_update/data/patmatch/locus.txt"
notFeatFile = "scripts/dumping/sequence_update/data/patmatch/NotFeature.dna.seq"
codingFile = "scripts/dumping/sequence_update/data/patmatch/orf_dna.seq"
genomicFile = "scripts/dumping/sequence_update/data/patmatch/orf_genomic.seq"
oneKBFile = "scripts/dumping/sequence_update/data/patmatch/orf_genomic_1000.seq"
proteinFile = "scripts/dumping/sequence_update/data/patmatch/orf_pep.seq"

TAXON = "TAX:559292"
SEQ_FORMAT = 'plain'
FILE_TYPE = 'ORF'

def dump_data():

    nex_session = get_session()

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id

    dbentity_id_to_data = dict([(x.dbentity_id, (x.systematic_name, x.gene_name, x.sgdid, x.qualifier, x.description)) for x in nex_session.query(Locusdbentity).filter_by(dbentity_status = 'Active').all()])

    so_id_to_display_name = dict([(x.so_id, x.term_name) for x in nex_session.query(So).all()])
    
    contig_id_to_chr = dict([(x.contig_id, x.display_name) for x in nex_session.query(Contig).filter(Contig.display_name.like('Chromosome %')).all()])
    
    generate_locus_file(nex_session, taxonomy_id, dbentity_id_to_data)

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

    nex_session.close()

    
def generate_locus_file(nex_session, taxonomy_id, dbentity_id_to_data):

    fw = open(locusFile, "w")

    for x in nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id = taxonomy_id, dna_type='GENOMIC').all():
        if x.dbentity_id not in dbentity_id_to_data:
            continue
        (systematic_name, gene_name, sgdid, qualifier, desc) = dbentity_id_to_data[x.dbentity_id]
        if gene_name is None:
            gene_name = ''
        headline = ''
        if desc is not None:
            headline = desc.split(";")[0]
        fw.write(systematic_name + "\t" + gene_name + "\t" + sgdid + "\t" + headline + "\n")

    fw.close()

if __name__ == '__main__':

    dump_data()
