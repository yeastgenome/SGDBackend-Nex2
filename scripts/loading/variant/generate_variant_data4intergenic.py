import os
from os import path
from src.models import Locusdbentity, Dnasubsequence, Dnasequenceannotation, Taxonomy
from scripts.loading.database_session import get_session
from scripts.loading.variant import calculate_variant_data, aligned_sequence_to_snp_sequence, \
     strain_to_id, calculate_block_data
from scripts.loading.util import get_strain_taxid_mapping

nex_session = get_session()
strain_to_taxid = get_strain_taxid_mapping()
strain_to_id = strain_to_id()
taxon = strain_to_taxid['S288C']

dataDir = 'scripts/loading/variant/data/'

seqAlignFile = dataDir + 'intergenic_sequence_alignment.txt'
variantFile = dataDir + 'intergenic_variant.txt'

dnaDir = dataDir + 'not_feature_align/'

def generate_dna_data(name_to_dbentity_id, dbentity_id_to_name):

    fw = open(seqAlignFile, "w")
    fw2 = open(variantFile, "w")
    
    fw.write("intergenic_sequence_name\tdbentity_id_1\tdbentity_id_2\taligned_sequence\tsnp_sequence\tblock_size\n")
    fw2.write("intergenic_sequence_name\tdbentity_id_1\tdbentity_id_2\tsequence_type\tscore\tvariant_type\tsnp_type\tstart\tend\n")

    for filename in os.listdir(dnaDir):
        name = filename.replace(".align", "")
        (strain_to_seq, variant_data, snp_seqs, block_sizes) = process_one_file(name, dnaDir+filename)
        
        if variant_data is None:
            continue
        strain_to_snp_seqs = {}
        for snp in snp_seqs:
            strain = snp['name']
            strain_to_snp_seqs[strain] = snp['snp_sequence']
        [name1, name2] = name.split("_")
        dbentity_id_1 = name_to_dbentity_id.get(name1)
        dbentity_id_2 = name_to_dbentity_id.get(name2)
        for strain in strain_to_seq:
            seqName = name + "_" + strain
            if strain == 'S288C':
                fw.write(seqName + "\t" + str(dbentity_id_1) + "\t" + str(dbentity_id_2) + "\t" + strain_to_seq[strain] + "\t" + str(strain_to_snp_seqs.get(strain)) + "\t" + str(block_sizes) + "\n")
            else:
                fw.write(seqName + "\t" + str(dbentity_id_1) + "\t" + str(dbentity_id_2) + "\t" + strain_to_seq[strain] + "\t" + str(strain_to_snp_seqs.get(strain)) + "\tNone\n")
        for variant in variant_data:
            fw2.write(name + "\t" + str(dbentity_id_1) + "\t" + str(dbentity_id_2) + "\tDNA\t" + str(variant['score']) + "\t" + variant['variant_type'] + "\t" + str(variant.get('snp_type')) + "\t" + str(variant['start']) + "\t" + str(variant['end']) + "\n")
         
    fw.close()
    fw2.close()

    
def process_one_file(name, alignFile):

    strain_to_seq = read_one_file(alignFile)
    if 'S288C' not in strain_to_seq:
        print ("No S288C in ", alignFile)
        return (strain_to_seq, None, None, None)

    introns = []
    variant_data = calculate_variant_data(name, 'intergenic', strain_to_seq, introns)
    
    snp_seqs = [aligned_sequence_to_snp_sequence(strain, strain_to_id[strain], strain_to_seq[strain], variant_data) for strain in strain_to_seq]
    # print (snp_seqs)
    block_sizes = len(strain_to_seq['S288C'].replace('-', ''))
    return (strain_to_seq, variant_data, snp_seqs, block_sizes)
    
def read_one_file(alignFile):
    
    f = open(alignFile)

    strain_to_seq = {}
    for line in f:
        if "CLUSTAL" in line or line.startswith(' '):
            continue
        pieces = line.strip().split(' ')
        if len(pieces) < 2:
            continue      
        strain = pieces[0].split('_')[2]
        if strain not in strain_to_id:
            continue
        seq = ''
        if strain in strain_to_seq:
            seq = strain_to_seq[strain]
        strain_to_seq[strain] = seq + pieces[-1] 
        
    return strain_to_seq     

if __name__ == '__main__':

    dbentity_id_to_name = {}
    name_to_dbentity_id = {}
    for x in nex_session.query(Locusdbentity).all():
        dbentity_id_to_name[x.dbentity_id] = x.systematic_name
        name_to_dbentity_id[x.systematic_name] = x.dbentity_id

    generate_dna_data(name_to_dbentity_id, dbentity_id_to_name)

