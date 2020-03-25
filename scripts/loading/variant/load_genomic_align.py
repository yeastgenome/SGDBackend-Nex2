import os
import sys
from src.models import Dnasequencealignment
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

CREATED_BY = os.environ['DEFAULT_USER']

mapping_file = "scripts/loading/variant/data/name_to_contig_mapping.txt"
data_file = "scripts/loading/variant/data/dna_sequence_alignment.txt"

def load_data():

    nex_session = get_session()

    name_to_contig_mapping = {}
    
    f = open(mapping_file)
    for line in f:
        if line.startswith('sequence'):
            continue
        pieces = line.strip().split('\t')
        name_to_contig_mapping[pieces[0]] = (pieces[1], pieces[2], pieces[3])
    f.close()

    f = open(data_file)

    i = 0
    
    for line in f:
        if line.startswith('sequence'):
            continue
        pieces = line.strip().split('\t')
        seqID = pieces[0]
        locus_id = int(pieces[1])
        aligned_seq = pieces[2]
        snp_seq = pieces[3]
        block_sizes = pieces[4]
        block_starts = pieces[5]
        (contig_id, start, end) = name_to_contig_mapping[seqID]

        print (seqID, locus_id, contig_id, block_sizes, block_starts, start, end, snp_seq, aligned_seq)
        
        if 'S288C' in seqID:
            x = Dnasequencealignment(locus_id = locus_id,
                                     contig_id = int(contig_id),
                                     display_name = seqID,
                                     dna_type = 'genomic',
                                     block_sizes = block_sizes,
                                     block_starts = block_starts,
                                     contig_start_index = int(start),
                                     contig_end_index = int(end),
                                     aligned_sequence = aligned_seq,
                                     snp_sequence = snp_seq,
                                     created_by = CREATED_BY)
            nex_session.add(x)
        else:
            x = Dnasequencealignment(locus_id = locus_id,
                                     contig_id = int(contig_id),
                                     display_name = seqID,
                                     dna_type = 'genomic',
                                     contig_start_index = int(start),
                                     contig_end_index = int(end),
                                     aligned_sequence = aligned_seq,
                                     snp_sequence = snp_seq,
                                     created_by = CREATED_BY)
            nex_session.add(x)
            
        i = i + 1
        if i > 500:
            nex_session.commit()
            # nex_session.rollback()
            i = 0
        
    nex_session.commit()
    # nex_session.rollback()

if __name__ == "__main__":
        
    load_data()
    
        
