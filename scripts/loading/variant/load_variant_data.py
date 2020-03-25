import os
import sys
from src.models import Sequencevariant
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

CREATED_BY = os.environ['DEFAULT_USER']

dna_data_file = "scripts/loading/variant/data/dna_variant.txt"
protein_data_file = "scripts/loading/variant/data/protein_variant.txt"
intergenic_data_file = "scripts/loading/variant/data/intergenic_variant.txt"

def load_data():

    nex_session = get_session()

    load_dna_data(nex_session)
    load_protein_data(nex_session)
    load_intergenic_data(nex_session)

def add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start_index, end_index, snp_type=None):

    print (seqID, locus_id, seq_type, variant_type, score, start_index, end_index, snp_type)

    x = None
    if snp_type is None:        
        x = Sequencevariant(locus_id = locus_id,
                            seq_type = seq_type,
                            variant_type = variant_type,
                            score = score,
                            start_index = start_index,
                            end_index = end_index,
                            created_by = CREATED_BY)
    else:
        x = Sequencevariant(locus_id = locus_id,
                            seq_type = seq_type,
                            variant_type = variant_type,
                            score = score,
                            snp_type = snp_type,
                            start_index = start_index,
                            end_index = end_index,
                            created_by = CREATED_BY)
    nex_session.add(x)

    
def load_dna_data(nex_session):
    
    f = open(dna_data_file)

    i = 0
    
    for line in f:
        if line.startswith('systematic_name'):
            continue
        pieces = line.strip().split('\t')
        seqID = pieces[0]
        locus_id = int(pieces[1])
        seq_type = pieces[2]
        score = int(pieces[3])
        variant_type = pieces[4]
        snp_type = pieces[5].lower()
        start = int(pieces[6])
        end = int(pieces[7])

        if variant_type in ['Insertion', 'Deletion']:
            add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end)
        else:       
            add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end, snp_type)
                          
        i = i + 1
        if i > 500:
            nex_session.commit()
            # nex_session.rollback()
            i = 0
        
    nex_session.commit()
    # nex_session.rollback()

    f.close()
    
def load_protein_data(nex_session):

    f = open(protein_data_file)

    i = 0

    for line in f:
        if line.startswith('systematic_name'):
            continue
        pieces = line.strip().split('\t')
        seqID = pieces[0]
        locus_id = int(pieces[1])
        seq_type = pieces[2]
        score = int(pieces[3])
        variant_type = pieces[4]
        start = int(pieces[6])
        end = int(pieces[7])

        add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end)
        
        i = i + 1
        if i > 500:
            nex_session.commit()
            # nex_session.rollback()
            i = 0

    nex_session.commit()
    # nex_session.rollback()

    f.close()
    
def load_intergenic_data(nex_session):

    f = open(intergenic_data_file)

    i = 0

    for line in f:
        if line.startswith('intergenic'):
            continue
        pieces = line.strip().split('\t')
        seqID = pieces[0]
        locus_id_1 = int(pieces[1])
        locus_id_2 = int(pieces[2])
        score = int(pieces[4])
        variant_type = pieces[5]
        start = int(pieces[7])
        end = int(pieces[8])
    
        ## YFL040W_YFL039C        <=   YFL039C          <=   YFL039C_YFL038C
        ## (downstream)                                      (upstream)
        
        ## YOR028C_YOR029W         => YOR029W           =>   YOR029W_YOR030W
        ## (upstream)                                        (downstream)

        [name1, name2] = seqID.split('_')
        name1 = name1.split('-')[0]
        name2 = name2.split('-')[0]

        snp_type = 'intergenic'
        if variant_type in ['Insertion', 'Deletion']:
            snp_type = None
        
        if name1.endswith('C'):
            locus_id = locus_id_1
            seq_type = 'upstream IGR'
            add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end, snp_type)
        else:         
            locus_id = locus_id_1
            seq_type = 'downstream IGR'
            add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end, snp_type)
            
        if name2.endswith('C'):
            locus_id = locus_id_2
            seq_type = 'downstream IGR'
            add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end, snp_type)
        else:
            locus_id = locus_id_2
            seq_type = 'upstream IGR'
            add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end, snp_type)
       
        i = i + 2
        if i > 500:
            nex_session.commit()
            # nex_session.rollback()
            i = 0

    nex_session.commit()
    # nex_session.rollback()
    
    f.close()

if __name__ == "__main__":
        
    load_data()
    
        
