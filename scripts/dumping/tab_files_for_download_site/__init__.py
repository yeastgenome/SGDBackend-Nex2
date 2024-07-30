from src.models import PhenotypeannotationCond

taxon = 'TAX:559292'


def dbentity_id_feature_type_mapping(nex_session):
    
    rows = nex_session.execute("SELECT dsa.dbentity_id, s.display_name "
                               "FROM nex.dnasequenceannotation dsa, nex.so s "
                               "WHERE dsa.dna_type = 'GENOMIC' "
                               "AND dsa.so_id = s.so_id").fetchall()
    dbentity_id_to_feature_type_mapping = dict([(x['dbentity_id'], x['display_name']) for x in rows])
    return dbentity_id_to_feature_type_mapping


def get_taxonomy_id_for_S288C(nex_session):
    
    rows = nex_session.execute(f"SELECT taxonomy_id FROM nex.taxonomy WHERE taxid = '{taxon}'").fetchall()
    return rows[0]['taxonomy_id']

def get_chr_num_mapping():
    
    return {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9,
        "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16, "Mito": 17
    }


def annotation_id_to_conds_mapping(nex_session):

    rows = nex_session.query(PhenotypeannotationCond).order_by(
        PhenotypeannotationCond.annotation_id, PhenotypeannotationCond.group_id).all()

    annotation_id_to_conds = {}
    for x in rows:
        conds = []
        if x.annotation_id in annotation_id_to_conds:
            conds = annotation_id_to_conds[x.annotation_id]
        conds.append(x)
        annotation_id_to_conds[x.annotation_id] = conds
    return annotation_id_to_conds
                

def dbentity_id_to_data_mapping(nex_session):

    rows = nex_session.execute("SELECT d.sgdid, ld.* "
                               "FROM nex.dbentity d, nex.locusdbentity ld "
                               "WHERE d.subclass = 'LOCUS' "
                               "AND d.dbentity_status = 'Active' "
                               "AND d.dbentity_id = ld.dbentity_id").fetchall()
    dbentity_id_to_data = {}
    for x in rows:
        dbentity_id = x['dbentity_id']
        dbentity_id_to_data[dbentity_id] = (x['sgdid'], x['systematic_name'], x['gene_name'], x['qualifier'], x['genetic_position'], x['description'])

    return dbentity_id_to_data


def reference_id_to_data_mapping(nex_session):

    rows = nex_session.execute("SELECT d.dbentity_id, d.sgdid, rd.pmid, rd.citation "
                               "FROM nex.dbentity d, nex.referencedbentity rd "
                               "WHERE d.subclass = 'REFERENCE' "
                               "AND d.dbentity_status = 'Active' "
                               "AND d.dbentity_id = rd.dbentity_id").fetchall()
    reference_id_to_data = {}
    for x in rows:
        reference = "SGD_REF:" + x['sgdid']
        if x['pmid']:
            reference = reference + "|PMID:" + str(x['pmid'])
        reference_id_to_data[x['dbentity_id']] = (reference, x['citation'])

    return reference_id_to_data


def phenotype_id_to_phenotype_mapping(nex_session):

    rows = nex_session.execute("SELECT phenotype_id, display_name FROM nex.phenotype").fetchall()

    phenotype_id_to_phenotype = {}
    for x in rows:
        phenotype_id_to_phenotype[x['phenotype_id']] = x['display_name']
    return phenotype_id_to_phenotype

def taxonomy_id_to_strain_mapping(nex_session):

    rows = nex_session.execute("SELECT sd.taxonomy_id, d.display_name "
                               "FROM nex.straindbentity sd, nex.dbentity d "
                               "WHERE sd.dbentity_id = d.dbentity_id").fetchall()
    
    taxonomy_id_to_strain_name = {}
    for x in rows:
        taxonomy_id_to_strain_name[x['taxonomy_id']] = x['display_name']
    return taxonomy_id_to_strain_name
    


