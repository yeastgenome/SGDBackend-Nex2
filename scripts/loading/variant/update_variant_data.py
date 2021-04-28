import os
import sys
from src.models import Sequencevariant
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

CREATED_BY = os.environ['DEFAULT_USER']

dna_data_file = "scripts/loading/variant/data/dna_variant.txt"
protein_data_file = "scripts/loading/variant/data/protein_variant.txt"
intergenic_data_file = "scripts/loading/variant/data/intergenic_variant.txt"

def update_data():

    nex_session = get_session()

    # update_dna_data(nex_session)
    # update_protein_data(nex_session)
    # update_intergenic_data(nex_session)

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

    
def update_dna_data(nex_session):

    key_to_x = {}
    key_to_values = {}
    for x in nex_session.query(Sequencevariant).filter_by(seq_type = 'DNA').all():
        key = (x.locus_id, x.snp_type, x.start_index, x.end_index)
        key_to_x[key] = x
        key_to_values[key] = (x.variant_type, x.score)
    
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

        if snp_type == 'None':
            snp_type = None
            
        key = (locus_id, snp_type, start, end)
        values = (variant_type, score)
        
        if key not in key_to_x:
            print ("DNA: INSERT: ", key)
            if variant_type in ['Insertion', 'Deletion']:
                add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end)
            else:       
                add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end, snp_type)
        else:
            if values != key_to_values[key]:
                print ("DNA: UPDATE: ", key)
                x = key_to_x[key]
                ## trigger error: couldn't update score
                nex_session.delete(x)
                nex_session.commit()
                if variant_type in ['Insertion', 'Deletion']:
                    add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end)
                else:
                    add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end, snp_type)
            else:
                print ("DNA: NO CHANGE: ", key)
            del key_to_x[key]
            
        i = i + 1
        if i > 500:
            nex_session.commit()
            # nex_session.rollback()
            i = 0

    for key in key_to_x:
        print ("DNA: DELETE", key)
        x = key_to_x[key]
        nex_session.delete(x)
        i = i + 1
        if i > 500:
            nex_session.commit()
            # nex_session.rollback()
        
    nex_session.commit()
    # nex_session.rollback()

    f.close()
    
def update_protein_data(nex_session):

    key_to_x = {}
    key_to_values = {}
    for x in nex_session.query(Sequencevariant).filter_by(seq_type = 'protein').all():
        key = (x.locus_id, x.start_index, x.end_index)
        key_to_x[key] = x
        key_to_values[key] = (x.variant_type, x.score)
        
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

        key = (locus_id, start, end)
        values = (variant_type, score)
        if key not in key_to_x:
            print ("protein: INSERT: ", key)
            add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end)
        else:
            if values != key_to_values[key]:
                print ("protein: UPDATE: ", key)
                x = key_to_x[key]
                nex_session.delete(x)
                nex_session.commit()
                add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end)
            else:
                print ("protein: NO CHANGE: ", key)
            del key_to_x[key]
            
        i = i + 1
        if i > 500:
            nex_session.commit()
            # nex_session.rollback()
            i = 0

    for key in key_to_x:
        print ("protein: DELETE", key)
        x = key_to_x[key]
        nex_session.delete(x)

    nex_session.commit()
    # nex_session.rollback()

    f.close()
    
def update_intergenic_data(nex_session):

    key_to_x = {}
    key_to_values = {}
    for x in nex_session.query(Sequencevariant).filter(Sequencevariant.seq_type.like('%stream IGR')).all():
        key = (x.locus_id, x.seq_type, x.snp_type, x.start_index, x.end_index)
        key_to_x[key] = x
        key_to_values[key] = (x.variant_type, x.score)
    
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

        locus_id = None
        seq_type = None
        if name1.endswith('C'):
            locus_id = locus_id_1
            seq_type = 'upstream IGR'
        else:         
            locus_id = locus_id_1
            seq_type = 'downstream IGR'
        key = (locus_id, seq_type, snp_type, start, end)
        values = (variant_type, score)
        if key not in key_to_x:
            print ("IGR: INSERT: ", key)
            add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end, snp_type)
        else:
            if values != key_to_values[key]:
                print ("IGR: UPDATE: ", key)
                x = key_to_x[key]
                nex_session.delete(x)
                nex_session.commit()
                add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end, snp_type)
            else:
                print ("IGR: NO CHANGE: ", key)
            del key_to_x[key]
        
        if name2.endswith('C'):
            locus_id = locus_id_2
            seq_type = 'downstream IGR'    
        else:
            locus_id = locus_id_2
            seq_type = 'upstream IGR'
        key = (locus_id, seq_type, snp_type, start, end)
        values = (variant_type, score)
        if key not in key_to_x:
            print ("IGR: INSERT: ", key)
            add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end, snp_type)
        else:
            if values != key_to_values[key]:
                print ("IGR: UPDATE: ", key)
                x = key_to_x[key]
                nex_session.delete(x)
                nex_session.commit()
                add_row(nex_session, seqID, locus_id, seq_type, variant_type, score, start, end, snp_type)
            else:
                print ("IGR: NO CHANGE: ", key)
            del	key_to_x[key]
            
        i = i + 2
        if i > 500:
            nex_session.commit()
            # nex_session.rollback()
            i = 0

    for key in key_to_x:
        print ("IGR: DELETE", key)
        x = key_to_x[key]
        nex_session.delete(x)
        
    nex_session.commit()
    # nex_session.rollback()
    
    f.close()

if __name__ == "__main__":
        
    update_data()
    
        
