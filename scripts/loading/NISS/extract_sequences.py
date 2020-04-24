import sys
from src.models import Contig, Locusdbentity
from scripts.loading.database_session import get_session
from scripts.loading.util import get_strain_taxid_mapping

__author__ = 'sweng66'

data_file = "scripts/loading/NISS/data/NISSpilotSet102119.txt"
genomic_seq_file = "scripts/loading/NISS/data/NISSpilotSet102119_genomic.fsa"
kb_seq_file = "scripts/loading/NISS/data/NISSpilotSet102119_1KB.fsa"
locus_file = "scripts/loading/NISS/data/niss_genes.txt"
   
def extract_data():
    
    nex_session = get_session()

    name_to_dbentity_id =  dict([(x.systematic_name, x.dbentity_id) for x in nex_session.query(Locusdbentity).all()])
    
    header = []
    f = open(data_file)
    fw = open(genomic_seq_file, "w")
    fw2 = open(kb_seq_file , "w")
    fw3 = open(locus_file, "w")

    for line in f:
        
        pieces = line.strip().split("\t")
        
        if line.startswith('gene_name'):
            header = pieces[4:]
            continue
        if len(pieces) < 5:
            continue
        gene = pieces[0]
        name = pieces[2]
        dbentity_id = name_to_dbentity_id[name]
        genBankID = pieces[3].replace("GenBank: ", "")

        fw3.write(name + "\t" + genBankID  + "\n")

        i = 0
        for data in pieces[4:]:
            if data:
                strain = header[i]
                [contig, coords] = data.split(':')
                [start_index, end_index] = coords.split('..')
                strand = '+'
                if int(start_index) > int(end_index):
                    strand = '-'
                    [start_index, end_index] = [end_index, start_index]
                # print (name, dbentity_id, genBankID, strain, contig, start_index, end_index, strand)
                [genomic, kb] = get_sequences_from_contig(nex_session, name, contig, int(start_index), int(end_index), strand)
                if genomic == '':
                    continue
                fw.write(">" + name + " " + gene + " " + strain + " " + contig + " " + start_index + " " + end_index + " " + strand + " " + genBankID + "\n")
                fw.write(genomic+"\n")
                fw2.write(">" + name + " " + gene + " " + strain + " " + contig + " " + start_index + " " + end_index + " " + strand + " " + genBankID + "\n")
                fw2.write(kb+"\n")

            i = i + 1

    f.close()
    fw.close()
    fw2.close()
    fw3.close()

def get_sequences_from_contig(nex_session, name, contig, start, end, strand):
    
    seqLen = end - start + 1
    if seqLen%3 != 0:
        print (name, ": seqLen cannot be divided by 3. ", start, end)
        return ['', '']
    contigRow = nex_session.query(Contig).filter_by(format_name = contig).one_or_none()

    if contigRow is None:
        print (contig, ": is not in the Contig table.")
        return ['', '']
    else:
        contig_seq = contigRow.residues
        genomic_seq = contig_seq[start-1:end]
        kb_seq = ''
        if strand == '-':
            genomic_seq = reverse_complement(genomic_seq)

        if len(genomic_seq)%3 != 0:
            print (name, ": genomic seq length cannot be divided by 3. ", start, end)
            return ['', '']
        if genomic_seq.startswith('ATG'):
            start_kb = start - 1000
            end_kb = end + 1000
            if start_kb < 0:
                start_kb = 1
            if end_kb > len(contig_seq):
                end_kb = len(contig_seq)
            kb_seq = contig_seq[start_kb-1:end_kb]
            if strand == '-':
                kb_seq = reverse_complement(kb_seq)
        else:
            return ['', '']
        return [genomic_seq, kb_seq]

def reverse_complement(seq):

    complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
    bases = list(seq)
    bases = reversed([complement.get(base,base) for base in bases])
    bases = ''.join(bases)
    return bases

if __name__ == "__main__":

    extract_data()
    
