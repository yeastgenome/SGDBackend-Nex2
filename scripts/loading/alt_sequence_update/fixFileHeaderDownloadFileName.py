from sqlalchemy import or_
from datetime import datetime
from src.models import Locusdbentity, Dnasequenceannotation, Proteinsequenceannotation,\
                       Dnasubsequence
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

# taxid = "TAX:559292"

print (datetime.now())

nex_session = get_session()

dbentity_id_to_names = dict([(x.dbentity_id, (x.systematic_name, x.gene_name)) for x in nex_session.query(Locusdbentity).all()])

## switch to update one of the tables
all_rows = nex_session.query(Dnasequenceannotation).all()
# all_rows = nex_session.query(Proteinsequenceannotation).all()
# all_rows = nex_session.query(Dnasubsequence).all()

i = 0
j = 0
for x in all_rows:
    if x.dbentity_id not in dbentity_id_to_names:
        continue
    if x.file_header == 'N/A' or x.download_filename == 'N/A':
        continue
    (systematic_name, gene_name) = dbentity_id_to_names[x.dbentity_id]
    if gene_name is None:
        gene_name = systematic_name
    file_header = x.file_header[1:].split(' ')
    if len(file_header) < 2:
        continue
    if file_header[0] == systematic_name and file_header[1] == gene_name and x.download_filename.startswith(systematic_name):
        continue
    i = i + 1
    j = j + 1
    if file_header[0] != systematic_name or file_header[1] != gene_name:
        print (j, (systematic_name, gene_name), x.file_header)
        file_header[0] = systematic_name
        file_header[1] = gene_name
        x.file_header = '>' + ' '.join(file_header)
    if not x.download_filename.startswith(systematic_name):
        print (j, (systematic_name, gene_name), x.download_filename)
        file_name = x.download_filename.split('_')
        file_name[0] = systematic_name
        x.download_filename = '_'.join(file_name)
    nex_session.add(x)
    if i >= 300:
        nex_session.commit()
        # nex_session.rollback()
        i = 0

nex_session.commit()
# nex_session.rollback()
nex_session.close()

print (datetime.now())

exit
