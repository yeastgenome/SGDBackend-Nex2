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

dnaSeqAlignFile = dataDir + 'dna_sequence_alignment.txt'
proteinSeqAlignFile = dataDir + 'protein_sequence_alignment.txt'
dnaVariantFile = dataDir + 'dna_variant.txt'
proteinVariantFile = dataDir + 'protein_variant.txt'

dnaDir = dataDir + 'dna_align/'
proteinDir = dataDir + 'protein_align/'

def generate_protein_data(name_to_dbentity_id):

    fw = open(proteinSeqAlignFile, "w")
    fw2 = open(proteinVariantFile, "w")
    
    fw.write("sequence_name\tdbentity_id\taligned_sequence\n")
    fw2.write("systematic_name\tdbentity_id\tsequence_type\tscore\tvariant_type\tsnp_type\tstart\tend\n")

    for filename in os.listdir(proteinDir):
        name = filename.split('_')[0]
        (strain_to_seq, variant_data) = process_one_file(name, 'protein', proteinDir+filename, [])
        if variant_data is None:
            continue
        dbentity_id = name_to_dbentity_id.get(name)
        for strain in strain_to_seq:
            seqName = name + "_" + strain
            fw.write(seqName + "\t" + str(dbentity_id) + "\t" + strain_to_seq[strain] + "\n")
        for variant in variant_data:
            fw2.write(name + "\t" + str(dbentity_id) + "\tprotein\t" + str(variant['score']) + "\t" + variant['variant_type'] + "\t" + str(variant.get('snp_type')) + "\t" + str(variant['start']) + "\t" + str(variant['end']) + "\n")
            
    fw.close()
    fw2.close()

def generate_dna_data(name_to_dbentity_id, dbentity_id_to_name):

    fw = open(dnaSeqAlignFile, "w")
    fw2 = open(dnaVariantFile, "w")
    
    fw.write("sequence_name\tdbentity_id\taligned_sequence\tsnp_sequence\tblock_sizes\tblock_starts\n")
    fw2.write("systematic_name\tdbentity_id\tsequence_type\tscore\tvariant_type\tsnp_type\tstart\tend\n")

    name_to_introns = map_name_to_introns(dbentity_id_to_name)
    for filename in os.listdir(dnaDir):
        name = filename.split('_')[0]
        # print (name)
        introns = name_to_introns.get(name)
        if introns is None:
            introns = []
        (strain_to_seq, variant_data, snp_seqs, block_starts, block_sizes) = process_one_file(name, 'DNA', dnaDir+filename, introns)
        if variant_data is None:
            continue
        strain_to_snp_seqs = {}
        for snp in snp_seqs:
            strain = snp['name']
            strain_to_snp_seqs[strain] = snp['snp_sequence']
        dbentity_id = name_to_dbentity_id.get(name)
        for strain in strain_to_seq:
            seqName = name + "_" + strain
            if strain == 'S288C':
                fw.write(seqName + "\t" + str(dbentity_id) + "\t" + strain_to_seq[strain] + "\t" + str(strain_to_snp_seqs.get(strain)) + "\t" + ','.join(str(n) for n in block_sizes) + "\t" + ','.join(str(n) for n in block_starts) + "\n")
            else:
                fw.write(seqName + "\t" + str(dbentity_id) + "\t" + strain_to_seq[strain] + "\t" + str(strain_to_snp_seqs.get(strain)) + "\tNone\tNone\n")
        for variant in variant_data:
            fw2.write(name + "\t" + str(dbentity_id) + "\tDNA\t" + str(variant['score']) + "\t" + variant['variant_type'] + "\t" + str(variant.get('snp_type')) + "\t" + str(variant['start']) + "\t" + str(variant['end']) + "\n")
         
    fw.close()
    fw2.close()

def map_name_to_introns(dbentity_id_to_name):

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=taxon).one_or_none()    
    annotation_id_to_dbentity_id = dict([(x.annotation_id, x.dbentity_id) for x in nex_session.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC', taxonomy_id=taxonomy.taxonomy_id).all()])

    name_to_introns = {}
    for x in nex_session.query(Dnasubsequence).filter_by(display_name='intron').order_by(Dnasubsequence.annotation_id, Dnasubsequence.relative_start_index).all():
        if x.annotation_id in annotation_id_to_dbentity_id:
            name = dbentity_id_to_name[x.dbentity_id]
            introns = []
            if name in name_to_introns:
                introns = name_to_introns[name]
            introns.append({'start': x.relative_start_index,
                            'end': x.relative_end_index})
            name_to_introns[name] = introns
            
    return name_to_introns

def process_one_file(name, type, alignFile, introns):

    strain_to_seq = read_one_file(alignFile)
    if 'S288C' not in strain_to_seq:
        print ("No S288C in ", alignFile)
        if type == 'DNA':
            return (strain_to_seq, None, None, None, None)
        else:
            return (strain_to_seq, None)
    variant_data = calculate_variant_data(name, type, strain_to_seq, introns)
    if type == 'protein':
        return (strain_to_seq, variant_data)

    snp_seqs = [aligned_sequence_to_snp_sequence(strain, strain_to_id[strain], strain_to_seq[strain], variant_data) for strain in strain_to_seq]
    # print (snp_seqs)
    (block_starts, block_sizes) = calculate_block_data(strain_to_seq['S288C'], introns)
    # print (block_starts, block_sizes)
    return (strain_to_seq, variant_data, snp_seqs, block_starts, block_sizes)
    
def read_one_file(alignFile):
    
    f = open(alignFile)

    strain_to_seq = {}
    for line in f:
        if "CLUSTAL" in line or line.startswith(' '):
            continue
        pieces = line.strip().split(' ')
        if len(pieces) < 2:
            continue      
        strain = pieces[0].split('_')[1]
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

    generate_protein_data(name_to_dbentity_id)

    generate_dna_data(name_to_dbentity_id, dbentity_id_to_name)

