from sqlalchemy import or_
from datetime import datetime
import os
from src.models import Dnasubsequence, Dnasequenceannotation, Proteinsequenceannotation
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

infile = "scripts/loading/alt_sequence_update/data/bad_seq_rows.lst"

nex_session = get_session()

f = open(infile)

# taxonomy_id strain dbentity_id systematic_name gene_name dnasequenceannotation.annotation_ids 
# 275334 Saccharomyces cerevisiae Y55 1267376 YBR118W TEF2 1844980 1853792 1844979

bad_ids = []
for line in f:
    if line.startswith('#'):
        continue
    pieces = line.strip().split(' ')
    bad_ids = bad_ids + pieces[7:]
    
f.close()

for id in bad_ids:

    for x in nex_session.query(Dnasubsequence).filter_by(annotation_id = int(id)).all():
        nex_session.delete(x)
        
    dbentity_id = None
    taxonomy_id = None
    file_header = None
    for x in nex_session.query(Dnasequenceannotation).filter_by(annotation_id = int(id)).all(): 
        if x.dna_type == 'GENOMIC':
            dbentity_id = x.dbentity_id
            taxonomy_id = x.taxonomy_id
            header = x.file_header.split(' ')
            file_header = ' '.join(header[0:2]) + ' ' + ' '.join(header[3:])
        nex_session.delete(x)

    if dbentity_id is None:
        continue
    
    x = nex_session.query(Proteinsequenceannotation).filter_by(dbentity_id = dbentity_id, taxonomy_id = taxonomy_id, file_header = file_header).one_or_none()
    if x is None:
        continue
    print (y.annotation_id, dbentity_id, taxonomy_id, file_header)
    nex_session.delete(x)
    
nex_session.rollback()
# nex_session.commit()
nex_session.close()
