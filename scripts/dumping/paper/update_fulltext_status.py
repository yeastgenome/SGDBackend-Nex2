from src.models import Referencedbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

pmid_list = 'scripts/dumping/paper/data/pmid_for_new_pdf_2021-06-23.lst'

def update_data():

    nex_session = get_session()

    f = open(pmid_list)
    to_be_changed_pmid = {}
    for line in f:
        pmid = int(line.strip())
        to_be_changed_pmid[pmid] = 1
    f.close()
    
    all = nex_session.query(Referencedbentity).filter(Referencedbentity.fulltext_status!='YT').all()

    i = 0
    for x in all:
        if x.pmid not in to_be_changed_pmid:
            continue
        
        x.fulltext_status = 'YT'
        nex_session.add(x)
        i = i + 1
        print (i, x.pmid)
        
        if i > 300:        
            # nex_session.rollback()
            nex_session.commit()
            i = 0
   
    # nex_session.rollback()
    nex_session.commit()
    
    nex_session.close()

    print ("DONE!")
        
if __name__ == "__main__":

    update_data()


    
        
