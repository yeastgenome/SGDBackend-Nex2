import os
import sys
from src.models import Proteinsequencealignment
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

CREATED_BY = os.environ['DEFAULT_USER']

data_file = "scripts/loading/variant/data/protein_sequence_alignment.txt"

def update_data():

    nex_session = get_session()

    key_to_x = {}
    for x in nex_session.query(Proteinsequencealignment).all():
        key = (x.locus_id, x.display_name)
        key_to_x[key] = x
        
    f = open(data_file)

    i = 0
    
    for line in f:
        if line.startswith('sequence'):
            continue
        pieces = line.strip().split('\t')
        seqID = pieces[0]
        locus_id = int(pieces[1])
        aligned_seq = pieces[2]

        # print (seqID, locus_id, aligned_seq)
        key = (locus_id, seqID)
        if key in key_to_x:
            x = key_to_x[key]
            if x.aligned_sequence != aligned_seq:
                print ("UPDATE: ", locus_id, seqID)
                x.aligned_sequence = aligned_seq
                nex_session.add(x)
            else:
                print ("NO CHANGE: ", locus_id, seqID)
            del key_to_x[key]
        else:
            print ("NEW: ", locus_id, seqID)
            x = Proteinsequencealignment(locus_id = locus_id,
                                         display_name = seqID,
                                         aligned_sequence = aligned_seq,
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
        
    update_data()
    
        
