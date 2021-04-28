import os
import sys
from src.models import Dnasequencealignment
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

CREATED_BY = os.environ['DEFAULT_USER']

mapping_file = "scripts/loading/variant/data/name_to_contig4intergenic_mapping.txt"
data_file = "scripts/loading/variant/data/intergenic_sequence_alignment.txt"

def update_data():

    nex_session = get_session()

    key_to_values = {}
    key_to_x = {}
    for x in nex_session.query(Dnasequencealignment).filter(Dnasequencealignment.dna_type != 'genomic').all():
        key = (x.locus_id, x.display_name, x.dna_type)
        key_to_values[key] = (x.contig_id, x.block_sizes, x.contig_start_index, x.contig_end_index, x.aligned_sequence, x.snp_sequence)
        key_to_x[key] = x

    name_to_contig_mapping = {}

    f = open(mapping_file)
    for line in f:
        if line.startswith('sequence'):
            continue
        pieces = line.strip().split('\t')
        names = pieces[0].split('|')
        seqID = names[0] + "_" + names[1] + "_" + names[2]
        name_to_contig_mapping[seqID] = (pieces[1], pieces[2], pieces[3])
    f.close()

    f = open(data_file)

    i = 0
    
    for line in f:
        if line.startswith('intergenic_sequence'):
            continue
        pieces = line.strip().split('\t')
        seqID = pieces[0]
        locus_id_1 = int(pieces[1])
        locus_id_2 = int(pieces[2]) 
        aligned_seq = pieces[3]
        snp_seq = pieces[4]
        block_sizes = pieces[5]
        if block_sizes == 'None':
            block_sizes = None
        
        
        (contig_id, start, end) = name_to_contig_mapping[seqID]
        contig_id = int(contig_id)
        start = int(start)
        end = int(end)
        
        [name1, name2, strain] = seqID.split('_')
        name1 = name1.split('-')[0]
        name2 =	name2.split('-')[0]

        ## YFL040W_YFL039C        <=   YFL039C          <=   YFL039C_YFL038C
        ## (downstream)                                      (upstream)

        ## YOR028C_YOR029W         => YOR029W           =>   YOR029W_YOR030W
        ## (upstream)                                        (downstream)

        if name1.endswith('C'):
            locus_id = locus_id_1
            dna_type = 'upstream IGR'

            key = (locus_id, seqID, dna_type)
            if key in key_to_values:
                values = (contig_id, block_sizes, start, end, aligned_seq, snp_seq)
                if values != key_to_values[key]:
                    print ("UPDATE: ", key)
                    ### trigger error: couldn't update contig_end_index so have to
                    ### change it to drop/reload for the updated rows
                    x = key_to_x[key]
                    nex_session.delete(x)
                    nex_session.commit()
                    add_row(nex_session, locus_id, contig_id, seqID, dna_type, start, end, aligned_seq, snp_seq, block_sizes)
                else:
                    print ("NO CHANGE: ", key)
                del key_to_values[key]
            else:
                print ("INSERT: ", key)
                add_row(nex_session, locus_id, contig_id, seqID, dna_type, start, end, aligned_seq, snp_seq, block_sizes)
        else:
            locus_id = locus_id_1
            dna_type = 'downstream IGR'

            key = (locus_id, seqID, dna_type)
            if key in key_to_values:
                values = (contig_id, block_sizes, start, end, aligned_seq, snp_seq)
                if values != key_to_values[key]:
                    print ("UPDATE: ", key)
                    x = key_to_x[key]
                    nex_session.delete(x)
                    nex_session.commit()  
                    add_row(nex_session, locus_id, contig_id, seqID, dna_type, start, end, aligned_seq, snp_seq, block_sizes)
                else:
                    print ("NO CHANGE: ", key)
                del key_to_values[key]
            else:
                print ("INSERT: ", key)
                add_row(nex_session, locus_id, contig_id, seqID, dna_type, start, end, aligned_seq, snp_seq, block_sizes)
        
        if name2.endswith('C'):
            locus_id = locus_id_2
            dna_type = 'downstream IGR'

            key = (locus_id, seqID, dna_type)
            if key in key_to_values:
                values = (contig_id, block_sizes, start, end, aligned_seq, snp_seq)
                if values != key_to_values[key]:
                    print ("UPDATE: ", key)
                    x = key_to_x[key]
                    nex_session.delete(x)
                    nex_session.commit()  
                    add_row(nex_session, locus_id, contig_id, seqID, dna_type, start, end, aligned_seq, snp_seq, block_sizes)
                else:
                    print ("NO CHANGE: ", key)
                del key_to_values[key]
            else:
                print ("INSERT: ", key)
                add_row(nex_session, locus_id, contig_id, seqID, dna_type, start, end, aligned_seq, snp_seq, block_sizes)
        else:
            locus_id = locus_id_2
            dna_type = 'upstream IGR'
            
            key = (locus_id, seqID, dna_type)
            if key in key_to_values:
                values = (contig_id, block_sizes, start, end, aligned_seq, snp_seq)
                if values != key_to_values[key]:
                    print ("UPDATE: ", key)
                    x = key_to_x[key]
                    nex_session.delete(x)
                    nex_session.commit()  
                    add_row(nex_session, locus_id, contig_id, seqID, dna_type, start, end, aligned_seq, snp_seq, block_sizes)
                else:
                    print ("NO CHANGE: ", key)
                del key_to_values[key]
            else:
                print ("INSERT: ", key)
                add_row(nex_session, locus_id, contig_id, seqID, dna_type, start, end, aligned_seq, snp_seq, block_sizes)
        	
        i = i + 1
        if i > 500:
            nex_session.commit()
            # nex_session.rollback()
            i = 0

    #########################
    for key in key_to_values:
        print ("DELETE: ", key)
        x = key_to_x[key]
        nex_session.delete(x)
            
    nex_session.commit()   
    # nex_session.rollback()


def add_row(nex_session, locus_id, contig_id, seqID, dna_type, start, end, aligned_seq, snp_seq, block_sizes):

    x = None
    if 'S288C' in seqID:
        x = Dnasequencealignment(locus_id = locus_id,
                                 contig_id = contig_id,
                                 display_name = seqID,
                                 dna_type = dna_type,
                                 block_sizes = block_sizes,
                                 contig_start_index = start,
                                 contig_end_index = end,
                                 aligned_sequence = aligned_seq,
                                 snp_sequence = snp_seq,
                                 created_by = CREATED_BY)
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
    
        
