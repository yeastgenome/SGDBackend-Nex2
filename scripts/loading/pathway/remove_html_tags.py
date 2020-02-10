from src.models import Dbentity
from scripts.loading.database_session import get_session
                             
__author__ = 'sweng66'

nex_session = get_session()

all_pathways = nex_session.query(Dbentity).filter_by(subclass='PATHWAY').all()

for x in all_pathways:

    if ">" in x.display_name or "<" in x.display_name:
        display_name = x.display_name.replace("<i>", "").replace("</i>", "")
        # print (x.dbentity_id, x.display_name, display_name)
        nex_session.query(Dbentity).filter_by(dbentity_id=x.dbentity_id).update({ 'display_name': display_name })

nex_session.commit()
nex_session.close()
