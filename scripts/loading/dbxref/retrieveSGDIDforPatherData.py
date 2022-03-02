from scripts.loading.database_session import get_session
from src.models import Dnasequenceannotation, Taxonomy 

TAXON = 'TAX:559292'

nex_session = get_session()

taxonomy = nex_session.query(Taxonomy).filter_by(taxid = TAXON).one_or_none()

for x in nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id=taxonomy.taxonomy_id, dna_type='GENOMIC').all():

    if x.dbentity.dbentity_status == 'Active':
        print (x.dbentity.sgdid)

nex_session.close()

