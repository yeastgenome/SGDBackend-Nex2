from datetime import datetime
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import dbentity_id_to_data_mapping

__author__ = 'sweng66'

complexFile = "scripts/dumping/tab_files_for_download_site/data/molecularComplexes.tab"

    
def dump_data():

    """
    EBI complex ID
    Complex Portal ID (CPX ID)
    Complex name
    Complex Aliases
    Complex Function summary
    Complex Properties summary
    Complex PubMed ID
    Interactors Biological Role
    Interactor Stoichiometry
    Interactor Type
    Interactor Secondary Id (systematic name)
    Participant standard name (Standard Name)
    Participant name
    Participant SGDID
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
        aliases.append(x[1])
        complex_id_to_aliases[x[0]] = aliases
    
    rows = nex_session.execute("SELECT cr.complex_id, rd.pmid "
                               "FROM nex.complex_reference cr, nex.referencedbentity rd "
                               "WHERE cr.reference_id = rd.dbentity_id").fetchall()
    complex_id_to_pmids = {}
    for x in rows:
        pmids = complex_id_to_pmids.get(x[0], [])
        pmid = "PMID:" + str(x[1]) if x[1] else ""
        if pmid:
            pmids.append(pmid)
            complex_id_to_pmids[x[0]] = pmids

    rows = nex_session.execute("SELECT cg.complex_id, g.display_name "
                               "FROM nex.complex_go cg, nex.go g "
                               "WHERE cg.go_id = g.go_id "
                               "AND g.go_namespace = 'molecular function' "
                               "ORDER BY 1, 2").fetchall()
    complex_id_to_functions = {}
    for x in rows:
        functions = complex_id_to_functions.get(x[0], [])
        functions.append(x[1])
        complex_id_to_functions[x[0]] = functions
    
    rows = nex_session.execute("SELECT cba.complex_id, cba.stoichiometry, i.format_name, i.display_name, "
                               "       i.locus_id, pt.display_name, pr.display_name "  
                               "FROM nex.complexbindingannotation cba, nex.interactor i, "
                               "     nex.psimi pt, nex.psimi pr "
                               "WHERE cba.interactor_id = i.interactor_id "
                               "AND i.type_id = pt.psimi_id "
                               "AND i.role_id = pr.psimi_id").fetchall()

    complex_id_to_interactors = {}
    for x in rows:
        complex_id = x[0]
        stoichiometry = x[1] if x[1] else ""
        format_name = x[2]
        display_name = x[3]
        locus_id = x[4]
        type = x[5]
        role = x[6]
        sgdid = ""
        systematic_name = ""
        if locus_id and locus_id in locus_id_to_data:
            (sgdid, systematic_name, gene_name, qualifier, genetic_position, desc) = locus_id_to_data[locus_id]
        interactor = (stoichiometry, format_name, display_name, type, role, sgdid, systematic_name)
        interactors = complex_id_to_interactors.get(complex_id, [])
        interactors.append(interactor)
        complex_id_to_interactors[complex_id] = interactors
        
    
    rows = nex_session.execute("SELECT cd.intact_id, cd.complex_accession, d.display_name, cd.description, d.dbentity_id " 
                               "FROM nex.complexdbentity cd, nex.dbentity d "
                               "WHERE cd.dbentity_id = d.dbentity_id "
                               "ORDER BY 3").fetchall()

    for x in rows:
        ebi_complex_id = x[0]
        cpx_id = x[1]
        complexNm = x[2]
        desc = x[3]
        complex_id = x[4]
        aliases = "|".join(complex_id_to_aliases.get(complex_id, []))
        functions = "|".join(complex_id_to_functions.get(complex_id, []))
        pmids = "|".join(complex_id_to_pmids.get(complex_id, []))
        interactors = complex_id_to_interactors.get(complex_id, [])
        for interactor in interactors:
            (stoichiometry, format_name, display_name, type, role, sgdid, systematic_name) = interactor
            fw.write(ebi_complex_id + "\t" + cpx_id + "\t" + complexNm + "\t")
            fw.write(aliases + "\t" + functions + "\t" + desc + "\t")
            fw.write(pmids + "\t" + role + "\t" + str(stoichiometry) + "\t" + type + "\t")
            fw.write(format_name + "\t" + display_name + "\t" + systematic_name + "\t")
            fw.write(sgdid + "\n")
        
    fw.close()
    nex_session.close()
    print(datetime.now())
    print("DONE!")


if __name__ == '__main__':
    
    dump_data()

    

