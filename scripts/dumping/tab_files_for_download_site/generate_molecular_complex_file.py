from datetime import datetime
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import dbentity_id_to_data_mapping

__author__ = 'sweng66'

complexFile = "scripts/dumping/tab_files_for_download_site/data/molecularComplexes.tab"

    
def dump_data():

    """
    specs: one complex per row
    
    EBI complex ID
    Complex Portal ID (CPX ID)
    Complex name
    Complex systematic_name
    Complex SGDID
    Complex Aliases - pipe-separated list
    Complex Description
    Complex subunits - pipe-separated list alphabetical (use gene_name, if no gene_name use systematic_name
    Subunit stoichiometry - pipe-separated list to match order of 'Complex subunits' row
    Complex PubMed ID - pipe-separated list
    """

    print(datetime.now())
    print("Generating molecularComplexes.tab file...")
    
    nex_session = get_session()
    
    fw = open(complexFile, "w")

    locus_id_to_data = dbentity_id_to_data_mapping(nex_session)
    
    rows = nex_session.execute("SELECT complex_id, display_name "
                               "FROM nex.complex_alias").fetchall()
    complex_id_to_aliases = {}
    for x in rows:
        aliases = complex_id_to_aliases.get(x[0], [])
        if x[1] not in aliases:
            aliases.append(x[1])
            complex_id_to_aliases[x[0]] = aliases
    
    rows = nex_session.execute("SELECT cr.complex_id, rd.pmid "
                               "FROM nex.complex_reference cr, nex.referencedbentity rd "
                               "WHERE cr.reference_id = rd.dbentity_id").fetchall()
    complex_id_to_pmids = {}
    for x in rows:
        pmids = complex_id_to_pmids.get(x[0], [])
        pmid = "PMID:" + str(x[1]) if x[1] else ""
        if pmid and pmid not in pmids:
            pmids.append(pmid)
            complex_id_to_pmids[x[0]] = pmids
                               
    rows = nex_session.execute("SELECT cba.complex_id, cba.stoichiometry, i.format_name, i.display_name "  
                               "FROM nex.complexbindingannotation cba, nex.interactor i "
                               "WHERE cba.interactor_id = i.interactor_id").fetchall()

    complex_id_to_stoichiometry_list = {}
    complex_id_to_subunit_list = {}
    for x in rows:
        complex_id = x[0]
        stoichiometry = x[1] if x[1] else ""
        subunit = x[3] if x[3] else x[2]
        
        """
        if locus_id and locus_id in locus_id_to_data:
            (sgdid, systematic_name, gene_name, qualifier, genetic_position, desc) = locus_id_to_data[locus_id]
        """
        subunit_list = complex_id_to_subunit_list.get(complex_id, [])
        stoichiometry_list = complex_id_to_stoichiometry_list.get(complex_id, [])
        if subunit not in subunit_list:
            subunit_list.append(subunit)
            stoichiometry_list.append(str(stoichiometry))
            complex_id_to_subunit_list[complex_id] = subunit_list
            complex_id_to_stoichiometry_list[complex_id] = stoichiometry_list

    rows = nex_session.execute("SELECT cd.intact_id, cd.complex_accession, cd.systematic_name, "
                               "       d.display_name, d.sgdid, cd.description, d.dbentity_id " 
                               "FROM nex.complexdbentity cd, nex.dbentity d "
                               "WHERE cd.dbentity_id = d.dbentity_id "
                               "ORDER BY 3").fetchall()

    for x in rows:
        ebi_complex_id = x[0]
        cpx_id = x[1]
        systematicNm = x[2]
        complexNm = x[3]
        sgdid = x[4]
        desc = x[5]
        complex_id = x[6]
        aliases = "|".join(complex_id_to_aliases.get(complex_id, []))
        subunit_list = "|".join(complex_id_to_subunit_list.get(complex_id, []))
        stoichiometry_list = "|".join(complex_id_to_stoichiometry_list.get(complex_id, []))
        pmids = "|".join(complex_id_to_pmids.get(complex_id, []))
        
        fw.write(ebi_complex_id + "\t" + cpx_id + "\t" + complexNm + "\t")
        fw.write(systematicNm + "\t" + sgdid + "\t" + aliases + "\t" + desc + "\t")
        fw.write(subunit_list + "\t" + stoichiometry_list + "\t" + pmids + "\n")
        
    fw.close()
    nex_session.close()
    print(datetime.now())
    print("DONE!")


if __name__ == '__main__':
    
    dump_data()

    

