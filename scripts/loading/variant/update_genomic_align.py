import os
import sys
from src.models import Dnasequencealignment
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

CREATED_BY = os.environ['DEFAULT_USER']

mapping_file = "scripts/loading/variant/data/name_to_contig_mapping.txt"
data_file = "scripts/loading/variant/data/dna_sequence_alignment.txt"

dna_type = 'genomic'

def update_data():

    nex_session = get_session()

    key_to_values = {}
    key_to_x = {}
    for x in nex_session.query(Dnasequencealignment).filter_by(dna_type=dna_type).all():
        key = (x.locus_id, x.display_name)
        key_to_values[key] = (x.contig_id, x.block_sizes, x.block_starts, x.contig_start_index, x.contig_end_index, x.aligned_sequence, x.snp_sequence)
        key_to_x[key] = x
        
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
    found_key = {}
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
        if block_sizes == 'None':
            block_sizes = None
        if block_starts == 'None':
            block_starts = None
        (contig_id, start, end) = name_to_contig_mapping[seqID]
        contig_id = int(contig_id)
        start = int(start)
        end = int(end)
        
        key = (locus_id, seqID)
        if key in found_key:
            continue
        found_key[key] = 1
        
        values = (contig_id, block_sizes, block_starts, start, end, aligned_seq, snp_seq)
        
        if key in key_to_values:
            if values != key_to_values[key]:
                print ("UPDATE: ", key)
                print ("   OLD: ", key_to_values[key])
                print ("   NEW: ", values)
                # update_dnasequencealignment(nex_session, key_to_x[key], locus_id,
                #                            contig_id, seqID, block_sizes, block_starts,
                #                            start, end, aligned_seq, snp_seq)
                ## trigger error when updating contig_end_index so change to drop/reload for updated row
                x = key_to_x[key]
                nex_session.delete(x)
                nex_session.commit()
                insert_dnasequencealignment(nex_session, locus_id, contig_id, seqID, block_sizes,
                                            block_starts, start, end, aligned_seq, snp_seq)
            else:
                print ("NO CHANGE: ", key)
            del key_to_values[key]
        else:
            print ("INSERT: ", key)
            insert_dnasequencealignment(nex_session, locus_id, contig_id, seqID, block_sizes,
                                        block_starts, start, end, aligned_seq, snp_seq)
    
        i = i + 1
        if i > 500:
            nex_session.commit()
            # nex_session.rollback()
            i = 0
            
    # for key in key_to_values:
    #    x = key_to_x[key]
    #    print ("DELETE: ", key)
    #    nex_session.delete(x)
        
    nex_session.commit()
    # nex_session.rollback()
    
def insert_dnasequencealignment(nex_session, locus_id, contig_id, seqID, block_sizes, block_starts, start, end, aligned_seq, snp_seq):
           
    if 'S288C' in seqID:
        x = Dnasequencealignment(locus_id = locus_id,
                                 contig_id = contig_id,
                                 display_name = seqID,
                                 dna_type = dna_type,
                                 block_sizes = block_sizes,
                                 block_starts = block_starts,
                                 contig_start_index = start,
                                 contig_end_index = end,
                                 aligned_sequence = aligned_seq,
                                 snp_sequence = snp_seq,
                                 created_by = CREATED_BY)
        nex_session.add(x)
    else:
        x = Dnasequencealignment(locus_id = locus_id,
                                 contig_id = contig_id,
                                 display_name = seqID,
                                 dna_type = dna_type,
                                 contig_start_index = start,
                                 contig_end_index = end,
                                 aligned_sequence = aligned_seq,
                                 snp_sequence = snp_seq,
                                 created_by = CREATED_BY)
        nex_session.add(x)

        
if __name__ == "__main__":
        
    update_data()
    
        
