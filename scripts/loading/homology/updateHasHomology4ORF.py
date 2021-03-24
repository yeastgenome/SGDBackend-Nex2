import sys
from src.models import So, Taxonomy, Dnasequenceannotation, Locusdbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

TAXON = 'TAX:559292'

def update_data():
    
    nex_session = get_session()

    so = nex_session.query(So).filter_by(display_name='ORF').one_or_none()
    so_id = so.so_id
    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    all = nex_session.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC', so_id=so_id, taxonomy_id=taxonomy_id).all()

    i = 0
    for x in all:
        print (x.taxonomy_id, x.dbentity_id)
        locus = nex_session.query(Locusdbentity).filter_by(dbentity_id=x.dbentity_id).one_or_none()
        locus.has_homology = '1'
        nex_session.add(locus)
        i = i + 1
        if i > 300:
            nex_session.commit()
            i = 0
        
    # nex_session.rollback()
    nex_session.commit()
    
if __name__ == "__main__":

    update_data()
    
