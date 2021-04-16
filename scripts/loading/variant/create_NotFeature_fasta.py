import sys
from src.models import Locusdbentity, Dnasequenceannotation, Taxonomy, Contig, So
from scripts.loading.database_session import get_session
from scripts.loading.util import get_strain_taxid_mapping

dataDir = "scripts/loading/variant/data/"
refFile = dataDir + "not_feature_fasta/not_feature_S288C.fsa"

mapping_file =dataDir + "name_to_contig4intergenic_mapping.txt"
fw_mapping = open(mapping_file, "a")

def create_seqs(strain):

    nex_session = get_session()
    strain_to_taxid = get_strain_taxid_mapping()
    taxon = strain_to_taxid.get(strain)
    if taxon is None:
        print ("The strain=", strain, " is not in the mapping.")
        return

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=taxon).one_or_none()
    if taxonomy is None:
        print ("The taxon ID=", taxon, " is not in the database.")
        return
    taxonomy_id = taxonomy.taxonomy_id

    dbentity_id_to_name = dict([(x.dbentity_id, (x.systematic_name, x.dbentity_status)) for x in nex_session.query(Locusdbentity).all()])
    so_id_to_display_name = dict([(x.so_id, x.display_name) for x in nex_session.query(So).all()])
    
    outfile = dataDir + "not_feature_" + strain + ".fsa"

    featureOrder = []
    if strain != 'S288C':
        f = open(refFile)
        for line in f:
            if line.startswith(">"):
                seqID = line.replace(">", "").split(' ')[0]
                [name1, name2, RefStrain] = seqID.split('|')
                featureOrder.append((name1, name2))
        f.close()

    fw = open(outfile, "w")

    found = {}
    prevRow = None
    prevContigId = None
    contig_id_to_seq = {}
    contig_id_to_display_name = {}
    defline_to_seq = {}
    for x in nex_session.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC', taxonomy_id=taxonomy_id).order_by(Dnasequenceannotation.contig_id, Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all():
        if x.dbentity_id not in dbentity_id_to_name:
            continue
        (name, status) = dbentity_id_to_name[x.dbentity_id]
        if status in ['Deleted', 'Merged']:
            continue
        type = so_id_to_display_name.get(x.so_id)
        if type not in ['ORF', 'ncRNA gene', 'snoRNA gene', 'snRNA gene', 'tRNA gene', 'rRNA gene', 'telomerase RNA gene']:
            continue
        if prevContigId is None or prevContigId != x.contig_id:
            prevRow = (name, x.start_index, x.end_index)
            prevContigId = x.contig_id
            continue

        (prevName, prevStart, prevEnd) = prevRow
        
        if x.start_index >= prevStart and x.end_index <= prevEnd:
            continue

        start = prevEnd + 1
        end = x.start_index - 1
        
        if end <= start:
            prevRow = (name, x.start_index, x.end_index)
            prevContigId = x.contig_id
            continue

        #if prevName[0:2] == name[0:2] and prevName[2] != name[2]:
        #    print (name, prevName)
        #    # eg YAL002W and YAR002W
        #    prevRow = (name, x.start_index, x.end_index)
        #    prevContigId = x.contig_id
        #    continue
    
        if x.contig_id not in contig_id_to_seq:
            contig = nex_session.query(Contig).filter_by(contig_id=x.contig_id).one_or_none()
            if contig is None:
                print ("The contig_id=", x.contig_id, " is not in the database.")
                exit() 
            contig_id_to_seq[x.contig_id] = contig.residues;
            contig_id_to_display_name[x.contig_id] = contig.display_name;
        seq = contig_id_to_seq[x.contig_id][start-1:end]
        seqID = prevName + "|" + name + "|" + strain
        
        if (prevName, name) not in featureOrder and (name, prevName) in featureOrder:
            seqID = name + "|" + prevName + "|" + strain
            (start, end) = (end, start)
            seq = reverse_complement(seq)
            
        if seqID in found:
            print ("The seqID is already in the file.", seqID)
            continue
        found[seqID] = 1
        defline = ">"+seqID + " " + contig_id_to_display_name[x.contig_id] + " " + "from " + str(start) + "-" + str(end)

        fw_mapping.write(seqID + "\t" + str(x.contig_id) + "\t" + str(start) + "\t" + str(end) + "\n")

        if strain == 'S288C':
            defline = defline + ", Genome Release 64-2-1,"
        defline = defline + " between " + seqID.split('|')[0] + " and " + seqID.split('|')[1]    
        if strain == 'S288C':
            fw.write(defline + "\n")
            fw.write(seq + "\n")
        else:
            defline_to_seq[defline] = seq

        prevRow = (name, x.start_index, x.end_index)
        prevContigId = x.contig_id

    if strain != 'S288C':
        for defline in sorted(defline_to_seq.keys()):
            fw.write(defline + "\n")
            fw.write(defline_to_seq[defline] + "\n")

    fw.close()
    fw_mapping.close()

def reverse_complement(seq):

    complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
    bases = list(seq)
    bases = reversed([complement.get(base,base) for base in bases])
    bases = ''.join(bases)
    return bases

if __name__ == '__main__':

    if len(sys.argv) >= 2:
        strain = sys.argv[1]
        create_seqs(strain)
    else:
        print("Usage:         python create_NotFeature_seqs.py REF_strain_or_alt_strain_name\n");
        print("Usage example: python create_NotFeature_seqs.py S288C\n");
        print("Usage example: python create_NotFeature_seqs.py W303\n");
        print("Usage example: python create_NotFeature_seqs.py CEN.PK\n");
        exit()
