from datetime import datetime
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import dbentity_id_to_data_mapping, \
    reference_id_to_data_mapping, phenotype_id_to_phenotype_mapping

__author__ = 'sweng66'

interactionFile = "scripts/dumping/tab_files_for_download_site/data/interaction_data.tab"

    
def dump_data():

    """
    1) Feature Name (Bait) (Required)               - The feature name of the gene used as the bait
    2) Standard Gene Name (Bait) (Optional)         - The standard gene name of the gene used as the bait
    3) Feature Name (Hit) (Required)                - The feature name of the gene that interacts with the bait
    4) Standard Gene Name (Hit) (Optional)          - The standard gene name of the gene that interacts with the bait
    5) Experiment Type (Required)                   - A description of the experimental used to identify the interaction
    6) Genetic or Physical Interaction (Required)   - Indicates whether the experimental method is a genetic
                                                      or physical interaction
    7) Source (Required)                            - Lists the database source for the interaction
    8) Manually curated or High-throughput (Required) - Lists whether the interaction was manually curated from a
                                                      publication or added as part of a high-throughput dataset
    9) Notes (Optional)                             - Free text field that contains additional information
                                                      about the interaction
    10) Phenotype (Optional)                        - Contains the phenotype of the interaction
    11) Reference (Required)                        - Lists the identifiers for the reference as an SGDID (SGD_REF:)
                                                      or a PubMed ID (PMID:)
    12) Citation (Required)                         - Lists the citation for the reference
    """

    """
    example:

    YCR059C YIH1    YFL039C ACT1    Affinity Capture-MS     physical interactions   BioGRID manually curated                        SGD_REF:S000076888|PMID:15126500     Sattlegger E, et al. (2004) YIH1 is an actin-binding protein that inhibits protein kinase GCN2 and impairs general amino acid control when overexpressed. J Biol Chem 279(29):29952-62

    YFL039C	ACT1	YPR181C	SEC23	Synthetic Rescue	genetic interactions	BioGRID	high-throughput		vegetative growth:normal	SGD_REF:S000132969|PMID:20101242	He X, et al. (2010) Prevalent positive epistasis in Escherichia coli and Saccharomyces cerevisiae metabolic networks. Nat Genet 42(3):272-6
    """

    print(datetime.now())
    print("Generating interaction_data.tab file...")

    nex_session = get_session()

    dbentity_id_to_data = dbentity_id_to_data_mapping(nex_session)
    reference_id_to_data = reference_id_to_data_mapping(nex_session)
    phenotype_id_to_phenotype = phenotype_id_to_phenotype_mapping(nex_session)
    # taxonomy_id_to_strain_name = taxonomy_id_to_strain_mapping(nex_session)
    
    fw = open(interactionFile, "w")
    
    rows = nex_session.execute("SELECT * FROM nex.physinteractionannotation").fetchall()
    count = 0
    for x in rows:
        if x['dbentity1_id'] not in dbentity_id_to_data or x['dbentity2_id'] not in dbentity_id_to_data:
            if x['dbentity1_id'] not in dbentity_id_to_data:
                print("dbentity1_id =", x['dbentity1_id'], "is not an active dbentity_id")
            if x['dbentity2_id'] not in dbentity_id_to_data:
                print("dbentity2_id =", x['dbentity2_id'], "is not an active dbentity_id")
            continue
        dbentity1_id = x['dbentity1_id']
        dbentity2_id = x['dbentity2_id']
        if x['bait_hit'] == 'Hit-Bait':
            (dbentity1_id, dbentity2_id) = (dbentity2_id, dbentity1_id)
        (sgdid, systematic_name, gene_name, qualifier, geneticPos, desc) = dbentity_id_to_data[dbentity1_id]
        (sgdid2, systematic_name2, gene_name2, qualifier2, geneticPos2, desc2) = dbentity_id_to_data[dbentity2_id]
        if gene_name is None:
            gene_name = ""
        if gene_name2 is None:
            gene_name2 = ""
        note = x['description'] if x['description'] else ""
        if x['reference_id'] not in reference_id_to_data:
            print("reference_id =", x['reference_id'], "is not an active dbentity_id")
            continue
        (reference, citation) = reference_id_to_data[x['reference_id']]
        if citation is None:
            citation = ""
        count += 1
        if count % 1000 == 0:
            print(str(count) + ": generating physical interaction data")
        fw.write(systematic_name + "\t" + gene_name + "\t" + systematic_name2 + "\t" + gene_name2 + "\t" + x['biogrid_experimental_system'] + "\tphysical interactions\tBioGRID" + "\t" + x['annotation_type'] + "\t" + note + "\t\t" + reference + "\t" + citation + "\n")

    rows = nex_session.execute("SELECT * FROM nex.geninteractionannotation").fetchall()
    count = 0
    for x in rows:
        if x['dbentity1_id'] not in dbentity_id_to_data or x['dbentity2_id'] not in dbentity_id_to_data:
            if x['dbentity1_id'] not in dbentity_id_to_data:
                print("dbentity1_id =", x['dbentity1_id'], "is not an active dbentity_id")
            if x['dbentity2_id'] not in dbentity_id_to_data:
                print("dbentity2_id =", x['dbentity2_id'], "is not an active dbentity_id")
            continue
        dbentity1_id = x['dbentity1_id']
        dbentity2_id = x['dbentity2_id']
        if x['bait_hit'] == 'Hit-Bait':
            (dbentity1_id, dbentity2_id) = (dbentity2_id, dbentity1_id)
        (sgdid, systematic_name, gene_name, qualifier, geneticPos, desc) = dbentity_id_to_data[dbentity1_id]
        (sgdid2, systematic_name2, gene_name2, qualifier2, geneticPos2, desc2) = dbentity_id_to_data[dbentity2_id]
        if gene_name is None:
            gene_name = ""
        if gene_name2 is None:
            gene_name2 = ""
        note = x['description'] if x['description'] else ""
        if x['reference_id'] not in reference_id_to_data:
            print("reference_id =", x['reference_id'], "is not an active dbentity_id")
            continue
        (reference, citation) = reference_id_to_data[x['reference_id']]
        if citation is None:
            citation = ""
        phenotype = phenotype_id_to_phenotype.get(x['phenotype_id'], "")
        count += 1
        if count % 1000 == 0:
            print(str(count) + ": generating genetic interaction data")
        fw.write(systematic_name + "\t" + gene_name + "\t" + systematic_name2 + "\t" + gene_name2 + "\t" + x['biogrid_experimental_system'] + "\tgenetic interactions\tBioGRID" + "\t" + x['annotation_type'] + "\t" + note + "\t" + phenotype + "\t" + reference + "\t" + citation + "\n")

    fw.close()
    nex_session.close()
    print(datetime.now())
    print("DONE!")


if __name__ == '__main__':
    
    dump_data()

    


