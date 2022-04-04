from sqlalchemy import or_
from datetime import datetime
import os
from src.models import Dnasequenceannotation, Source
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

infile = "scripts/loading/alt_sequence_update/data/altRefGenomeUpdate040222_with_seq.data"

genomic_dna_type = 'GENOMIC'
oneKB_dna_type = '1KB'
created_by = os.environ['DEFAULT_USER']

def load_seq():
    
    f = open(infile)

    print (datetime.now())
    
    nex_session = get_session()

    source = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = source.source_id
    
    key_to_annotation_id = dict([((x.dna_type, x.dbentity_id, x.so_id, x.contig_id, x.taxonomy_id), x.annotation_id) for x in nex_session.query(Dnasequenceannotation).all()])
        
    i = 0
    j = 0
    for line in f:
        if 'systematic_name' in line:
            continue
        pieces = line.strip().split('\t')
        if len(pieces) < 16:
            continue
        systematic_name = pieces[0]
        dbentity_id = int(pieces[1])
        so_id = int(pieces[2])
        contig_id = int(pieces[3])
        taxonomy_id = int(pieces[4])
        strand = pieces[5]
        genomic_start_index = int(pieces[6])
        genomic_end_index = int(pieces[7])
        genomic_file_header = pieces[8]
        genomic_download_filename = pieces[9]
        genomic_seq = pieces[10]
        oneKB_start_index = int(pieces[11])
        oneKB_end_index = int(pieces[12])
        oneKB_file_header = pieces[13]
        oneKB_download_filename = pieces[14]
        oneKB_seq = pieces[15]

        genomic_key = (genomic_dna_type, dbentity_id, so_id, contig_id, taxonomy_id)
        oneKB_key = (oneKB_dna_type, dbentity_id, so_id, contig_id, taxonomy_id)

        if genomic_key not in key_to_annotation_id:
            insert_dnasequenceannotation(nex_session, genomic_dna_type, source_id, dbentity_id,
                                         so_id, contig_id, taxonomy_id, strand, genomic_start_index,
                                         genomic_end_index, genomic_file_header,
                                         genomic_download_filename, genomic_seq)
            i = i + 1
            j = j + 1

            print (j, systematic_name, genomic_dna_type)
                
        if oneKB_key not in key_to_annotation_id:
            insert_dnasequenceannotation(nex_session, oneKB_dna_type, source_id, dbentity_id,
                                         so_id, contig_id, taxonomy_id, strand, oneKB_start_index,
                                         oneKB_end_index, oneKB_file_header,
                                         oneKB_download_filename, oneKB_seq)
            i =	i + 1
            j =	j + 1

            print (j, systematic_name, oneKB_dna_type)
            
        if i > 300:
            i = 0
            # nex_session.rollback()
            nex_session.commit()
            
    f.close()
    
    # nex_session.rollback()
    nex_session.commit()
    nex_session.close()
    print (datetime.now())
    

def insert_dnasequenceannotation(nex_session, dna_type, source_id, dbentity_id, so_id, contig_id, taxonomy_id, strand, start_index, end_index, file_header, download_filename, seq):

    x = Dnasequenceannotation(dna_type = dna_type,
                              dbentity_id = dbentity_id,
                              so_id = so_id,
                              source_id = source_id,
                              contig_id = contig_id,
                              taxonomy_id = taxonomy_id,
                              strand = strand,
                              start_index = start_index,
                              end_index = end_index,
                              file_header = file_header,
                              download_filename = download_filename,
                              residues = seq,
                              created_by = created_by)

    nex_session.add(x)
        
if __name__ == "__main__":

    load_seq()
