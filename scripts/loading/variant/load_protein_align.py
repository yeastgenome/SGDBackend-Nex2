import os
import sys
from src.models import Proteinsequencealignment
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

CREATED_BY = os.environ['DEFAULT_USER']

data_file = "scripts/loading/variant/data/protein_sequence_alignment.txt"

def load_data():

    nex_session = get_session()

    f = open(data_file)

    i = 0
    
    for line in f:
        if line.startswith('sequence'):
            continue
        pieces = line.strip().split('\t')
        seqID = pieces[0]
        locus_id = int(pieces[1])
        aligned_seq = pieces[2]

        print (seqID, locus_id, aligned_seq)
        
        x = Proteinsequencealignment(locus_id = locus_id,
                                     display_name = seqID,
                                     aligned_sequence = aligned_seq,
                                     created_by = CREATED_BY)
        nex_session.add(x)
                    
        i = i + 1
        if i > 500:
            # nex_session.commit()
            nex_session.rollback()
            i = 0
        
    # nex_session.commit()
    nex_session.rollback()

if __name__ == "__main__":
        
    load_data()
    
        
