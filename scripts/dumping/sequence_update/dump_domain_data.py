import sys
from scripts.loading.database_session import get_session
from src.models import Locusdbentity, Proteindomain, Proteindomainannotation, \
                       Proteinsequenceannotation, ProteinsequenceDetail, \
                       Taxonomy, Source 
from scripts.dumping.sequence_update import get_sorted_dbentity_ids

__author__ = 'sweng66'

datafile = "scripts/dumping/sequence_update/data/protein/domains.tab"

TAXON = "TAX:559292"

# strains = [ 'S288C', 'CEN.PK', 'D273-10B', 'FL100', 'JK9-3d', 'RM11-1a',
#            'SEY6210', 'Sigma1278b', 'SK1', 'W303', 'X2180-1A', 'Y55' ]

def dump_data():

    nex_session = get_session()

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id

    dbentity_id_to_systematic_name = dict([(x.dbentity_id, x.systematic_name) for x in nex_session.query(Locusdbentity).filter_by(dbentity_status = 'Active').all()])
    
    domain_id_to_data = dict([(x.proteindomain_id, x) for x in nex_session.query(Proteindomain).all()])

    dbentity_id_to_annotation_id = dict([(x.dbentity_id, x.annotation_id) for x in nex_session.query(Proteinsequenceannotation).filter_by(taxonomy_id=taxonomy_id).all()])

    annotation_id_to_protein_length = dict([(x.annotation_id, x.protein_length) for x in nex_session.query(ProteinsequenceDetail).all()])

    source_id_to_display_name = dict([(x.source_id, x.display_name) for x in nex_session.query(Source).all()])
    
    key_to_data = {}
    for x in nex_session.query(Proteindomainannotation).filter_by(taxonomy_id=taxonomy_id).all():

        if x.proteindomain_id not in domain_id_to_data:
            continue
        domain = domain_id_to_data[x.proteindomain_id]
        if domain.source_id not in source_id_to_display_name:
            continue
        source = source_id_to_display_name[domain.source_id]
        if x.dbentity_id not in dbentity_id_to_systematic_name:
            continue
        systematic_name = dbentity_id_to_systematic_name[x.dbentity_id]
        if x.dbentity_id not in dbentity_id_to_annotation_id:
            continue
        annotation_id = dbentity_id_to_annotation_id[x.dbentity_id]
        if annotation_id not in annotation_id_to_protein_length:
            continue
        protein_length = annotation_id_to_protein_length[annotation_id]
        data = []
        if x.dbentity_id in key_to_data:
            data = key_to_data[x.dbentity_id]
        data.append(systematic_name + "\t" + str(protein_length) + "\t" + source + "\t" + domain.display_name + "\t" + domain.description + "\t" + str(x.start_index) + "\t" + str(x.end_index) + "\t" + str(x.date_of_run).split(' ')[0] + "\t" + domain.interpro_id)
        key_to_data[x.dbentity_id] = data

    all_dbentity_ids = get_sorted_dbentity_ids(nex_session, taxonomy_id)
    
    fw = open(datafile, "w")

    fw.write("systematic_name\tprotein_length\tdomain_source\tdomain_name\tdomain_description\tstart_index\tend_index\tdate_of_run\tinterpro_id\n")
    
    for dbentity_id in all_dbentity_ids:
        if dbentity_id in key_to_data:
            data = key_to_data[dbentity_id]
            for row in data:
                fw.write(row + "\n")
        
    nex_session.close()
    fw.close()

if __name__ == '__main__':

    dump_data()
