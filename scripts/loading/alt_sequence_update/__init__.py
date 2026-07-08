from src.models import Dnasequenceannotation, Proteinsequenceannotation, Contig
from scripts.dumping.sequence_update import format_fasta, clean_up_description

__author__ = 'sweng66'


orf_features = ['ORF', 'transposable_element_gene', 'pseudogene', 'blocked_reading_frame']
rna_features = ['ncRNA_gene', 'snoRNA_gene', 'snRNA_gene', 'tRNA_gene', 'rRNA_gene',
                'telomerase_RNA_gene']


def generate_protein_seq_file(nex_session, taxonomy_id, dbentity_id_to_defline, dbentity_id_list, seqFile, seq_format):

    fw = open(seqFile, "w")

    dbentity_id_to_seq = {}
    for x in nex_session.query(Proteinsequenceannotation).filter_by(taxonomy_id=taxonomy_id).all():
        dbentity_id_to_seq[x.dbentity_id] = x.residues

    for dbentity_id in dbentity_id_list:
        if dbentity_id not in dbentity_id_to_defline:
            continue
        if dbentity_id not in dbentity_id_to_seq:
            continue
        fw.write(dbentity_id_to_defline[dbentity_id] + "\n")
        seq = dbentity_id_to_seq[dbentity_id]
        if seq_format == 'fasta':
            fw.write(format_fasta(seq) + "\n")
        else:
            fw.write(seq + "\n")

    fw.close
    

def generate_dna_seq_file(nex_session, strain, taxonomy_id, contig_id_to_header, dbentity_id_to_data, so_id_to_display_name, seqFile, dna_type, seq_format, file_type, dbentity_id_to_defline=None, dbentity_id_list=None):

    fw = open(seqFile, "w")

    for x in nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id=taxonomy_id, dna_type=dna_type).order_by(Dnasequenceannotation.contig_id, Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all():

        if x.dbentity_id not in dbentity_id_to_data:
            continue
        #######                                                                                                    
        if file_type == 'other' and x.residues == 'No sequence available.':
            continue
        type = so_id_to_display_name[x.so_id]
        if file_type == 'other' and (type in orf_features or type in rna_features):
            continue
        elif file_type in ['rna', 'RNA'] and type not in rna_features:
            continue
        elif file_type in ['orf', 'ORF'] and type not in orf_features:
            continue
        #######                                                                                                    
        (systematic_name, gene_name, sgdid, qualifier, desc) = dbentity_id_to_data[x.dbentity_id]
        desc = clean_up_description(desc)

        if gene_name is None:
            gene_name = ' '
        start_index = x.start_index
        end_index = x.end_index
        if x.strand == '-':
            (start_index, end_index) = (end_index, start_index)
        coords = str(start_index) + "-" + str(end_index)
        if dna_type == 'CODING':
            coords = x.file_header.split(' ')[3].split(':')[1].replace('..', '-')

        contig_identifier = contig_id_to_header[x.contig_id].split(' ')[0].replace('>', '')
        
        defline = ">" + systematic_name + "_" + strain + " " + gene_name + " " + contig_identifier + " " + coords + " " + type 
        if qualifier is not None:
            defline = defline + " " + qualifier 
        if desc is not None:
            defline = defline + ' "' + desc + '"'
        if dbentity_id_to_defline is not None:
            dbentity_id_to_defline[x.dbentity_id] = defline
        if dbentity_id_list is not None:
            dbentity_id_list.append(x.dbentity_id)
        fw.write(defline + "\n")
        if seq_format == 'fasta':
            fw.write(format_fasta(x.residues) + "\n")
        else:
            fw.write(x.residues + "\n")

    fw.close()
           
    
def generate_not_feature_seq_file(nex_session, strain, taxonomy_id, dbentity_id_to_data, so_id_to_display_name, seqFile, seq_format):

    fw = open(seqFile, "w")
     
    found = {}
    prevRow = None
    prevContigId = None
    contig_id_to_seq = {}
    contig_id_to_display_name = {}
    defline_to_seq = {}
    
    for x in nex_session.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC', taxonomy_id=taxonomy_id).order_by(Dnasequenceannotation.contig_id, Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all():
        if x.dbentity_id not in dbentity_id_to_data:
            continue
        type = so_id_to_display_name.get(x.so_id)
 
        (name, gene_name, sgdid, qualifier, desc) = dbentity_id_to_data[x.dbentity_id]
        
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
        
        if x.contig_id not in contig_id_to_seq:
            contig = nex_session.query(Contig).filter_by(contig_id=x.contig_id).one_or_none()
            if contig is None:
                print ("The contig_id=", x.contig_id, " is not in the database.")
                exit()
            contig_id_to_seq[x.contig_id] = contig.residues;
            contig_id_to_display_name[x.contig_id] = contig.display_name;

        (prevName, prevStart, prevEnd) = prevRow
        
        seqID =	prevName + "|" + name + "|" + strain

        seq = contig_id_to_seq[x.contig_id][start-1:end]
        
        if seqID in found:
            print ("The seqID is already in the file.", seqID)
            continue
        found[seqID] = 1

        defline = ">" + seqID + " " + contig_id_to_display_name[x.contig_id] + " from " + str(start) + "-" + str(end) + " between " + prevName + " and " + name

        
        fw.write(defline + "\n")
        if seq_format == 'fasta':
            fw.write(format_fasta(seq) + "\n")
        else:
            fw.write(seq + "\n")

        prevRow = (name, x.start_index, x.end_index)
        prevContigId = x.contig_id

    fw.close()

    
