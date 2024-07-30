from datetime import datetime
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import dbentity_id_to_data_mapping, \
    dbentity_id_feature_type_mapping

__author__ = 'sweng66'

goProteinComplexSlimFile = "scripts/dumping/tab_files_for_download_site/data/go_protein_complex_slim.tab"

    
def dump_data():

    """
    1) Ontology: GO Term/GOID (mandatory)   
    2) /gene (optional)/ORF/SGDID/feature type/
    """

    """
    Component: 1,3-beta-D-glucan synthase complex/148       /GSC2/YGR032W/S000003264/ORF|Verified/|/FKS1/YLR342W/S000004334/ORF|Verified/|/RHO1/YPR165W/S000006369/ORF|Verified/
    Component: 6-phosphofructokinase complex/5945   /PFK1/YGR240C/S000003472/ORF|Verified/|/PFK2/YMR205C/S000004818/ORF|Verified/
    """

    """
    select goslim_id, format_name, display_name
    from nex.goslim
    where slim_name = 'Macromolecular complex terms';

    format_name: Macromolecular_complex_terms_GO:0070762
    display_name: nuclear pore transmembrane ring
    """

    print(datetime.now())
    print("Generating go_protein_complex_slim.tab file...")
    
    nex_session = get_session()
    
    dbentity_id_to_data = dbentity_id_to_data_mapping(nex_session)
    dbentity_id_to_feature_type = dbentity_id_feature_type_mapping(nex_session)
    
    rows = nex_session.execute("SELECT  gs.format_name, gs.display_name, gsa.dbentity_id "
                               "FROM nex.goslim gs, nex.goslimannotation gsa "
                               "WHERE gs.slim_name = 'Macromolecular complex terms' "
                               "AND gs.goslim_id = gsa.goslim_id").fetchall()

    complex_to_genes = {}
    for x in rows:
        if x['dbentity_id'] not in dbentity_id_to_data:
            continue
        (sgdid, systematic_name, gene_name, qualifier, genetic_position, desc) = dbentity_id_to_data[x['dbentity_id']]
        complexComponent = x['display_name'] + "/GO:" + x['format_name'].split("_GO:")[1]
        genes = []
        if complexComponent in complex_to_genes:
            genes = complex_to_genes[complexComponent]
        if gene_name is None:
            gene_name = ""
        feature_type = dbentity_id_to_feature_type.get(x['dbentity_id'], '')
        if qualifier is None:
            qualifier = ""
        genes.append("/" + gene_name + "/" + systematic_name + "/" + sgdid + "/" + feature_type + "/" + qualifier + "/")
        complex_to_genes[complexComponent] = genes
        
        fw = open(goProteinComplexSlimFile, "w")
    for complexComponent in complex_to_genes:
        fw.write("Component: " + complexComponent + "\t" + "|".join(complex_to_genes[complexComponent]) + "\n")
    fw.close()
    nex_session.close()
    print(datetime.now())
    print('DONE!')
    
    
if __name__ == '__main__':
    
    dump_data()

    


