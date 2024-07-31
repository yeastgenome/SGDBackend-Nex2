from datetime import datetime
from scripts.loading.database_session import get_session

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

    rows = nex_session.execute("SELECT go_id, display_name "
                               "FROM nex.go").fetchall()
    
    go_id_to_term = {}
    for x in rows:
        go_id_to_term[x[0]] = x[1]

    fw = open(regulationFile, "w")

    rows = nex_session.execute("SELECT ld1.systematic_name, ld1.gene_name, ld2.systematic_name, "
                               "       ld2.gene_name, e.display_name, ra.regulator_type, "
                               "       ra.regulation_type, ra.direction, ra.happens_during, "
                               "       d.display_name, rd.pmid, ra.annotation_id "
                               "FROM nex.locusdbentity ld1, nex.locusdbentity ld2, nex.eco e, "
                               "     nex.regulationannotation ra, nex.referencedbentity rd, "
                               "     nex.straindbentity sd, nex.dbentity d "
                               "WHERE ra.regulator_id = ld1.dbentity_id "
                               "AND ra.target_id = ld2.dbentity_id "
                               "AND ra.eco_id = e.eco_id "
                               "AND ra.taxonomy_id = sd.taxonomy_id "
                               "AND sd.dbentity_id = d.dbentity_id "
                               "AND ra.reference_id = rd.dbentity_id "
                               "ORDER BY ld1.systematic_name, ld2.systematic_name").fetchall()

    found = set()

    for x in rows:
        
        if x[11] in found:
            continue
        found.add(x[11])

        regulator_systematic_name = x[0]
        regulator_standard_name = x[1] if x[1] else ""
        target_systematic_name = x[2]
        target_standard_name = x[3] if x[3] else ""
        assay = x[4]
        regulator_type = x[5]
        regulation_type = x[6]
        direction = x[7] if x[7] else ""
        happens_during = go_id_to_term.get(x[8], "") if x[8] else ""
        strain = x[9]
        pmid = "PMID:" + str(x[10]) if x[10] else ""
        fw.write(regulator_standard_name + "\t" + regulator_systematic_name + "\t" + target_standard_name + "\t")
        fw.write(target_systematic_name + "\t" + assay + "\t" + regulator_type + "t" + regulation_type + "\t")
        fw.write(direction + "\t" + happens_during + "\t" + strain + "\t" + pmid + "\n")

    fw.close()
    nex_session.close()
    print(datetime.now())
    print("DONE!")

   
if __name__ == '__main__':
    
    dump_data()

    


