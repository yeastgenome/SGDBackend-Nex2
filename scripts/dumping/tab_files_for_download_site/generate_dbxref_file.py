from datetime import datetime
from src.models import LocusAlias
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

dbxrefFile = "scripts/dumping/tab_files_for_download_site/data/dbxref.tab"

    
def dump_data():

    """
    1) DBXREF ID
    2) DBXREF ID source
    3) DBXREF ID type
    4) S. cerevisiae feature name
    5) SGDID
    6) S. cerevisiae gene name (optional) 
    """

    """
    1.1.1.- IUBMB   EC number       YHR104W S000001146      GRE3
    1.1.1.- IUBMB   EC number       YPL088W S000006009      
    1.1.1.- IUBMB   EC number       YGL157W S000003125      ARI1
    """
    
    print(datetime.now())
    print("Generating dbxref file...")
    
    nex_session = get_session()
    
    fw = open(dbxrefFile, "w")

    rows = nex_session.query(LocusAlias).order_by(LocusAlias.alias_type, LocusAlias.display_name).all()
    for x in rows: 
        if x.source.display_name == 'SGD':
            continue
        gene = x.locus.gene_name if x.locus.gene_name else ""
        fw.write(str(x.display_name) + "\t" + str(x.source.display_name) + "\t" + x.alias_type + "\t" + x.locus.systematic_name + "\t" + x.locus.sgdid + "\t" + gene + "\n")
        
    nex_session.close()
    print(datetime.now())
    print("DONE!")


if __name__ == '__main__':
    
    dump_data()

    


