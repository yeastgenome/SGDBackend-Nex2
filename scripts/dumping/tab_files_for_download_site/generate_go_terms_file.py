from datetime import datetime
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

goTermFile = "scripts/dumping/tab_files_for_download_site/data/go_terms.tab"

    
def dump_data():

    """
    1) GOID (mandatory)       - the unique numerical identifer of the GO term
    2) eGO_wTerm (mandatory)     - the name of the GO term
    3) GO_Asrpect (mandatory)    - which ontology: P=Process, F=Function, C=Component
    4) GO_Term_Definition (optinal)      - the full definition of the GO term
    """
    """
    3  reproduction  P  The production of new individuals that contain some portion...
    """

    print(datetime.now())
    print("Generating go_terms.tab file...")
    
    nex_session = get_session()
    
    fw = open(goTermFile, "w")

    rows = nex_session.execute("SELECT goid, display_name, go_namespace, description "
                               "FROM nex.go "
                               "WHERE is_obsolete is False").fetchall()
    for x in rows:
        goAspect = x['go_namespace'].split(' ')[1][0].upper()
        desc = x['description'] if x['description'] else ''
        fw.write(x['goid'] + "\t" + x['display_name'] + "\t" + goAspect + "\t" + desc + "\n")

    fw.close()
    nex_session.close()
    print(datetime.now())
    print("DONE!")


if __name__ == '__main__':
    
    dump_data()

    


