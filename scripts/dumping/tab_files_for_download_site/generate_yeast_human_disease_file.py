from datetime import datetime
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

diseaseFile = "scripts/dumping/tab_files_for_download_site/data/yeastHumanDisease.tab"

    
def dump_data():

    """
    SGDID
    Systematic_name
    Standard_name
    DOID
    DO Term Name
    evidence code
    With
    PMID
    """

    print(datetime.now())
    print("Generating yeastHumanDisease.tab file...")
    
    nex_session = get_session()
    
    fw = open(diseaseFile, "w")

    rows = nex_session.execute("SELECT annotation_id, dbxref_id "
                               "FROM nex.diseasesupportingevidence").fetchall()

    annotation_id_dbxref_id = {}
    for x in rows:
        annotation_id_dbxref_id[x[0]] = x[1]

    rows = nex_session.execute("SELECT d.sgdid, ld.systematic_name, ld.gene_name, "
                               "       dis.doid, dis.display_name, e.ecoid, "
                               "       rd.pmid, da.annotation_id "
                               "FROM nex.diseaseannotation da, nex.locusdbentity ld, "
                               "     nex.dbentity d, nex.disease dis, nex.eco e, "
                               "     nex.referencedbentity rd "
                               "WHERE d.dbentity_id = ld.dbentity_id "
                               "AND ld.dbentity_id = da.dbentity_id "
                               "AND da.disease_id = dis.disease_id "
                               "AND da.reference_id = rd.dbentity_id "
                               "AND da.eco_id = e.eco_id").fetchall()
    for x in rows:
        sgdid = x[0]
        systematic_name = x[1]
        gene_name = x[2] if x[2] else ""
        doid = x[3]
        do_term = x[4]
        evidence_code = x[5]
        pmid = "PMID:" + str(x[6]) if x[6] else ""
        dbxref_id = annotation_id_dbxref_id.get(x[7], "")
        
        fw.write(sgdid + "\t" + systematic_name + "\t" + gene_name + "\t")
        fw.write(doid + "\t" + do_term + "\t" + evidence_code + "\t")
        fw.write(dbxref_id + "\t" + pmid + "\n")

    fw.close()
    nex_session.close()
    print(datetime.now())
    print("DONE!")


if __name__ == '__main__':
    
    dump_data()

    


