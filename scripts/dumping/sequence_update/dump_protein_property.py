import sys
from scripts.loading.database_session import get_session
from src.models import Locusdbentity, ProteinsequenceDetail, Proteinsequenceannotation,\
                       Taxonomy
from scripts.dumping.sequence_update import get_sorted_dbentity_ids

__author__ = 'sweng66'

datafile = "scripts/dumping/sequence_update/data/protein/protein_properties.tab"

TAXON = "TAX:559292"

# strains = [ 'S288C', 'CEN.PK', 'D273-10B', 'FL100', 'JK9-3d', 'RM11-1a',
#            'SEY6210', 'Sigma1278b', 'SK1', 'W303', 'X2180-1A', 'Y55' ]

def dump_data():

    nex_session = get_session()

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id

    dbentity_id_to_systematic_name = dict([(x.dbentity_id, x.systematic_name) for x in nex_session.query(Locusdbentity).filter_by(dbentity_status = 'Active').all()])
    
    annotation_id_to_dbentity_id = dict([(x.annotation_id, x.dbentity_id) for x in nex_session.query(Proteinsequenceannotation).filter_by(taxonomy_id=taxonomy_id).all()])

    key_to_data = {}
    for x in nex_session.query(ProteinsequenceDetail).all():
        
        if x.annotation_id not in annotation_id_to_dbentity_id:
            continue
        dbentity_id = annotation_id_to_dbentity_id[x.annotation_id]

        systematic_name = dbentity_id_to_systematic_name.get(dbentity_id)
        if systematic_name is None:
            continue

        data = systematic_name + "\t" + str(x.molecular_weight) + "\t" + str(x.pi) + "\t" + str(x.protein_length) + "\t" + x.n_term_seq + "\t" + x.c_term_seq + "\t" + str(x.gravy_score) + "\t" + str(x.aromaticity_score) + "\t" + str(x.cai) + "\t" + str(x.codon_bias) + "\t" + str(x.fop_score) + "\t" + str(x.ala) + "\t" + str(x.cys) + "\t" + str(x.asp) + "\t" + str(x.glu) + "\t" + str(x.phe) + "\t" + str(x.gly) + "\t" + str(x.his) + "\t" + str(x.ile) + "\t" + str(x.lys) + "\t" + str(x.leu) + "\t" + str(x.met) + "\t" + str(x.asn) + "\t" + str(x.pro) + "\t" + str(x.gln) + "\t" + str(x.arg) + "\t" + str(x.ser) + "\t" + str(x.thr) + "\t" + str(x.val) + "\t" + str(x.trp) + "\t" + str(x.tyr) + "\t" + str(x.carbon) + "\t" + str(x.hydrogen) + "\t" + str(x.nitrogen) + "\t" + str(x.oxygen) + "\t" + str(x.sulfur) + "\t" + str(x.instability_index) + "\t" + str(x.all_cys_ext_coeff) + "\t" + str(x.no_cys_ext_coeff) + "\t" + str(x.aliphatic_index)

        key_to_data[dbentity_id] = data

    all_dbentity_ids = get_sorted_dbentity_ids(nex_session, taxonomy_id)
    
    fw = open(datafile, "w")

    fw.write("ORF\tMw\tPI\tProtein Length\tN_term_seq\tC_term_seq\tGRAVY Score\tAromaticity Score\tCAI\tCodon Bias\tFOP Score\tAla\tCys\tAsp\tGlu\tPhe\tGly\tHis\tIle\tLys\tLeu\tMet\tAsn\tPro\tGln\tArg\tSer\tThr\tVal\tTrp\tTyr\tCARBON\tHYDROGEN\tNITROGEN\tOXYGEN\tSULPHUR\tINSTABILITY INDEX (II)\tASSUMING ALL CYS RESIDUES APPEAR AS HALF CYSTINES\tASSUMING NO CYS RESIDUES APPEAR AS HALF CYSTINES\tALIPHATIC INDEX\n")

    for dbentity_id in all_dbentity_ids:
        if dbentity_id in key_to_data:
            data = key_to_data[dbentity_id]
            fw.write(data + "\n")
        
    nex_session.close()
    fw.close()

if __name__ == '__main__':

    dump_data()
