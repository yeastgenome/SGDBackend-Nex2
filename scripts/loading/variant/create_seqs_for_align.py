from os import path, remove
from src.models import Locusdbentity, Dnasequenceannotation, Proteinsequenceannotation, Taxonomy, So
from scripts.loading.database_session import get_session
from scripts.loading.util import get_strain_taxid_mapping
from scripts.loading.variant import strain_to_id

dataDir = "scripts/loading/variant/data/"
dnaDir = dataDir + "dna_seq/"
proteinDir = dataDir + "protein_seq/"

nex_session = get_session()
strain_to_taxid = get_strain_taxid_mapping()
strain_to_id = strain_to_id()

dbentity_id_to_name = dict([(x.dbentity_id, x.systematic_name) for x in nex_session.query(Locusdbentity).all()])
taxon_to_taxonomy_id = dict([(x.taxid, x.taxonomy_id) for x in nex_session.query(Taxonomy).all()])    
so_id_to_type = dict([(x.so_id, x.display_name) for x in nex_session.query(So).all()])

taxonomy_id_list = []
taxonomy_id_to_strain = {}

mapping_file = dataDir + 'name_to_contig_mapping.txt'

fw_mapping = open(mapping_file, "w")
fw_mapping.write("sequence_name\tcontig_id\tstart_index\tend_index\n")

for strain in strain_to_id:
    taxon = strain_to_taxid[strain]
    taxonomy_id_list.append(taxon_to_taxonomy_id[taxon])
    taxonomy_id_to_strain[taxon_to_taxonomy_id[taxon]] = strain

filename_to_written_sequences = {}

def write_sequence(filename, seqID, sequence):
    if filename not in filename_to_written_sequences:
        filename_to_written_sequences[filename] = set()
    if seqID not in filename_to_written_sequences[filename]:
        with open(filename, "a" if path.exists(filename) else "w") as fw:
            fw.write(">" + seqID + "\n")
            fw.write(sequence + "\n")
        filename_to_written_sequences[filename].add(seqID)


found_dna_sequences = set()
for x in nex_session.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC').filter(Dnasequenceannotation.taxonomy_id.in_(taxonomy_id_list)).all():
    if x.dbentity_id not in dbentity_id_to_name:
        continue
    name = dbentity_id_to_name[x.dbentity_id]
    if name.startswith('Y') or name.startswith('Q'):
        seqID = name + "_" + taxonomy_id_to_strain[x.taxonomy_id]
        if seqID in found_dna_sequences:
            continue
        found_dna_sequences.add(seqID)
        filename = dnaDir + name + "_dna.seq"
        write_sequence(filename, seqID, x.residues)
        fw_mapping.write(seqID + "\t" + str(x.contig_id) + "\t" + str(x.start_index) + "\t" + str(x.end_index) + "\n")

fw_mapping.close()

# Clean up files with only one sequence
for filename, sequences in filename_to_written_sequences.items():
    if len(sequences) == 1:
        remove(filename)

filename_to_written_sequences = {}

found_protein_sequences = set()
for x in nex_session.query(Proteinsequenceannotation).filter(Proteinsequenceannotation.taxonomy_id.in_(taxonomy_id_list)).all():
    name = dbentity_id_to_name[x.dbentity_id]
    seqID = name + "_" + taxonomy_id_to_strain[x.taxonomy_id]
    if seqID in found_protein_sequences:
        continue
    found_protein_sequences.add(seqID)
    filename = proteinDir + name + "_protein.seq"
    write_sequence(filename, seqID, x.residues)

# Clean up files with only one sequence
for filename, sequences in filename_to_written_sequences.items():
    if len(sequences) == 1:
        remove(filename)
