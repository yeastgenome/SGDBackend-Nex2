from datetime import datetime
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import dbentity_id_to_data_mapping

__author__ = 'sweng66'

regulationFile = "scripts/dumping/tab_files_for_download_site/data/regulation.tab"

    
def dump_data():

    """
    Regulator standard_name
    Regulator systematic_name
    Target standard_name
    Target systematic_name
    Assay (eco.display_name)
    Regulator_type
    Regulation_type
    Direction
    Happens during (go.display_name)
    Strain background
    PMID
    """
    
    print(datetime.now())
    print("Generating regulation.tab file...")
    
    nex_session = get_session()

    locus_id_to_data = dbentity_id_to_data_mapping(nex_session)

    
    rows = nex_session.execute("SELECT d.dbentity_id, cd.systematic_name, d.display_name "
                               "FROM nex.complexdbentity cd, nex.dbentity d "
                               "WHERE cd.dbentity_id = d.dbentity_id").fetchall()
    complex_id_to_names = {}
    for x in rows:
        complex_id_to_names[x[0]] = (x[1], x[2])


    rows = nex_session.execute("SELECT go_id, display_name "
                               "FROM nex.go").fetchall()
    go_id_to_term = {}
    for x in rows:
        go_id_to_term[x[0]] = x[1]

    
    fw = open(regulationFile, "w")

    rows = nex_session.execute("SELECT ra.regulator_id, ra.target_id, e.display_name, ra.regulator_type, "
                               "       ra.regulation_type, ra.direction, ra.happens_during, "
                               "       d.display_name, rd.pmid, ra.annotation_id "
                               "FROM nex.eco e, nex.regulationannotation ra, nex.referencedbentity rd, "
                               "     nex.straindbentity sd, nex.dbentity d "
                               "WHERE ra.eco_id = e.eco_id "
                               "AND ra.taxonomy_id = sd.taxonomy_id "
                               "AND sd.dbentity_id = d.dbentity_id "
                               "AND ra.reference_id = rd.dbentity_id").fetchall()

    found = set()

    for x in rows:
        
        if x[9] in found:
            continue
        found.add(x[9])
        
        regulator_id = x[0]
        target_id = x[1]
        regulator_systematic_name = ""
        regulator_standard_name = ""
        target_systematic_name = ""
        target_standard_name = ""
        if regulator_id in locus_id_to_data:
            (sgdid, systematic_name, gene_name, qualifier, genetic_position, desc) = locus_id_to_data[regulator_id]
            regulator_systematic_name = systematic_name
            regulator_standard_name = gene_name if gene_name else ""
        elif regulator_id in complex_id_to_names:
            (regulator_systematic_name, regulator_standard_name) = complex_id_to_names[regulator_id]
        else:
            print("The regulator_id =", regulator_id, "is not in locusdbentity table or in complexdbentity table")
            print("The regulator_id:", get_entity_name(nex_session, regulator_id))
            continue

        if target_id in locus_id_to_data:
            (sgdid, systematic_name, gene_name, qualifier, genetic_position, desc) = locus_id_to_data[target_id]
            target_systematic_name = systematic_name
            target_standard_name = gene_name if gene_name else ""
        elif target_id in complex_id_to_names:
            (target_systematic_name, target_standard_name) = complex_id_to_names[target_id]
        else:
            print("The target_id =", target_id, "is not in locusdbentity table or in complexdbentity table")
            print("The target_id:", get_entity_name(nex_session, target_id))
            continue
        assay = x[2]
        regulator_type = x[3]
        regulation_type = x[4]
        direction = x[5] if x[5] else ""
        happens_during = go_id_to_term.get(x[6], "") if x[6] else ""
        strain = x[7]
        pmid = "PMID:" + str(x[8]) if x[8] else ""
        fw.write(regulator_standard_name + "\t" + regulator_systematic_name + "\t" + target_standard_name + "\t")
        fw.write(target_systematic_name + "\t" + assay + "\t" + regulator_type + "\t" + regulation_type + "\t")
        fw.write(direction + "\t" + happens_during + "\t" + strain + "\t" + pmid + "\n")

    fw.close()
    nex_session.close()
    print(datetime.now())
    print("DONE!")


def get_entity_name(nex_session, dbentity_id):

    row = nex_session.execute("SELECT display_name, subclass, dbentity_status "
                              "FROM nex.dbentity WHERE dbentity_id = " + str(dbentity_id)).fetchone()
    if row is None:
        return "Not found in DBENTITY table"
    return row[0] + " (" + row[1] + ", " + row[2] + ")"
                                            

if __name__ == '__main__':
    
    dump_data()

    


