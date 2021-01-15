import csv
import os
import logging
from src.models import DBSession, Locusdbentity, Functionalcomplementannotation, Eco, Ro, Referencedbentity, Source, Taxonomy
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, scoped_session
from scripts.loading.reference.promote_reference_triage import add_paper
from zope.sqlalchemy import ZopeTransactionExtension

import transaction
import traceback
import sys

'''
    Process a TSV file of disease annotation
    example
        $ source dev_variables.sh && CREATED_BY=KKARRA INPUT_FILE_NAME=/System/Volumes/Data/Users/data/intermine/yeast_complementation/functional_complementation.tab.entrez  python scripts/loading/funccomp/load_funccomp.py
'''

INPUT_FILE_NAME = os.environ.get('INPUT_FILE_NAME')
NEX2_URI = os.environ.get('NEX2_URI')
CREATED_BY = os.environ.get('CREATED_BY')
OBJ_URL = 'https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id'
TAXON_ID = 'TAX:559292'
ECO_ID = 'ECO:0007584'
RO_ID = 'RO:HOM0000065'

logging.basicConfig(level=logging.INFO)


def upload_db(obj, row_num):

    try:
        temp_engine = create_engine(NEX2_URI)
        session_factory = sessionmaker(bind=temp_engine, extension=ZopeTransactionExtension(), expire_on_commit=False)
        db_session = scoped_session(session_factory)
        dbentity_id = db_session.query(Locusdbentity.dbentity_id).filter(Locusdbentity.systematic_name == obj['systematic_name']).one_or_none()[0]
        if dbentity_id:
            try:
                tax_id = db_session.query(Taxonomy.taxonomy_id).filter(Taxonomy.taxid==TAXON_ID).one_or_none()[0]
                ref_id = db_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == obj['pmid']).one_or_none()
                print(ref_id)
                if ref_id is None:
                    ref = add_paper(obj['pmid'], CREATED_BY)
                    ref_id = ref[0]
                    logging.info('PMID added' + obj['pmid'])
                ro_id = db_session.query(Ro.ro_id).filter(Ro.format_name == RO_ID).one_or_none()[0]
                eco_id = db_session.query(Eco.eco_id).filter(Eco.format_name == ECO_ID).one_or_none()[0]
                source_id = db_session.query(Source.source_id).filter(Source.format_name == obj['source']).one_or_none()[0]
            except TypeError:
                logging.error('invalid ids ' + str(row_num) +  ' ' + str(dbentity_id) + ' ' + str(tax_id) + '  '+ str(ref_id) +'  '+ str(eco_id))
                return
            #annotation_id = db_session.query(Functionalcomplementannotation.annotation_id).filter(and_(Functionalcomplementannotation.eco_id == eco_id,
            #Functionalcomplementannotation.reference_id == ref_id, Functionalcomplementannotation.dbentity_id == dbentity_id)).one_or_none()          
            #print (annotation_id[0])
            #if not annotation_id[0] :
            new_daf_row = Functionalcomplementannotation(
                dbentity_id=dbentity_id,
                source_id=source_id,
                taxonomy_id=tax_id,
                reference_id=ref_id,
                eco_id=eco_id,
                obj_url=OBJ_URL + "/" + obj['hgnc'],
                dbxref_id=obj['hgnc'],
                ro_id=ro_id,
                created_by=CREATED_BY,
                curator_comment=obj['note'],
                direction=obj['direction']
                )
            db_session.add(new_daf_row)
            transaction.commit()
            db_session.flush()
            logging.info('finished ' + obj['systematic_name'] + ', line ' + str(row_num) +  ' ' + obj['pmid']+  ' ' + obj['hgnc'])
    except:
        logging.error('error with ' + obj['systematic_name']+ ' in row ' + str(row_num) +  ' ' + obj['pmid'] +  ' ' + obj['hgnc'])
        traceback.print_exc()
        db_session.rollback()
        db_session.close()
        sys.exit()

def load_csv_funccomp_dbentities():
    engine = create_engine(NEX2_URI, pool_recycle=3600)
    DBSession.configure(bind=engine)

    o = open(INPUT_FILE_NAME,'rU')
    reader = csv.reader(o, delimiter='\t')
    for i, val in enumerate(reader):
        if i >= 0:
            if val[0] == '':
                logging.info('Found a blank value, DONE!')
                return
            obj = {
                'systematic_name': val[1].strip(),
                'hgnc': val[4].strip(),
                'direction': val[5],
                'pmid': val[6].strip(),
                'source': val[7],
                'note': val[8]
            }
            upload_db(obj, i)

if __name__ == '__main__':
    load_csv_funccomp_dbentities()
