from sqlalchemy import or_
from datetime import datetime
import os
from src.models import Dnasequenceannotation, Proteinsequenceannotation
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

infile = "scripts/loading/alt_sequence_update/data/bad_seq_rows.lst"

nex_session = get_session()

f = open(infile)

# taxonomy_id strain dbentity_id systematic_name gene_name dnasequenceannotation.annotation_ids 
# 275334 Saccharomyces cerevisiae Y55 1267376 YBR118W TEF2 1844980 1853792 1844979

data = []
print ("annotation_id\tsystematic_name\tgene_name\tdna_type\ttaxonomy_id\tdbentity_id\tstart_index\tend_index\tbad_file_header\tfixed_file_header")
for line in f:
    if line.startswith('#'):
        continue
    pieces = line.strip().split(' ')
    taxonomy_id = int(pieces[0])
    dbentity_id = int(pieces[4])
    systematic_name = pieces[5]
    gene_name = pieces[6]
    strain = pieces[3]
    for x in nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id = taxonomy_id, dbentity_id = dbentity_id).all():
        if ',' in x.file_header:
            # Y55 YBR118W TEF2 CODING 275334 1267376 127464 128840 >YBR118W TEF2 Y55 JRIF01000118.1:113423..114496,127464..128840 intron sequence removed
            # print (strain, systematic_name, gene_name, x.dna_type, taxonomy_id, dbentity_id, x.start_index, x.end_index, x.file_header)
            coords = str(x.start_index) + '..' + str(x.end_index)
            file_header = x.file_header.split(':')[0] + ':' + coords
            print (str(x.annotation_id) + "\t" + systematic_name + "\t" + gene_name + "\t" + x.dna_type + "\t" + str(taxonomy_id) + "\t" + str(dbentity_id) + "\t" + str(x.start_index) + "\t" + str(x.end_index) +  '\t"' + x.file_header + '"\t"' + file_header + '"')
            x.file_header = file_header
            nex_session.add(x)

f.close()
# nex_session.rollback()
nex_session.commit()

    
        
