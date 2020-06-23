from src.models import Source, Chebi, ChebiAlia
from scripts.loading.database_session import get_session

datafile = 'scripts/loading/chemical/data/pathway_to_chebi_mapping.txt'

DB = 'SGD'
type = 'YeastPathway ID'

nex_session = get_session()

src = nex_session.query(Source).filter_by(display_name=DB).one_or_none()
source_id = src.source_id

chebiid_to_chebi_id =  dict([(x.chebiid, x.chebi_id) for x in nex_session.query(Chebi).all()])

f = open(datafile)

for line in f:
    pieces = line.strip().split('\t')
    pathwayID = pieces[0]
    pathwayName = pieces[1]
    for chebi in pieces[2:]:
        chebiid = "CHEBI:" + chebi
        chebi_id = chebiid_to_chebi_id.get(chebiid)
        if chebi_id is None:
            continue
        x = ChebiAlia(display_name = pathwayID,
                      alias_type = type,
                      source_id = source_id,
                      chebi_id = chebi_id,
                      created_by = 'OTTO')
        nex_session.add(x)
        nex_session.flush()
        print (chebiid, chebi_id, pathwayID)
# nex_session.rollback()
nex_session.commit()

f.close()


