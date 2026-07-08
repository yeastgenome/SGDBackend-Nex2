import sys
from src.models import Referencedbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

outfile = 'scripts/dumping/paper/data/pmcid_2021.txt'


def dump_data():

    nex_session = get_session()

    fw = open(outfile, "w")

    all = nex_session.query(Referencedbentity).order_by(Referencedbentity.year, Referencedbentity.pmid).all()
    for x in all:
        if x.year < 2021:
            continue
        if x.pmcid is None:
            continue
        if x.fulltext_status == 'N':
            fw.write(str(x.pmid) + "\t" + x.pmcid + "\t" + str(x.year) + "\t" + x.fulltext_status + "\n")

    fw.close()
    nex_session.close()
    
if __name__ == '__main__':

    dump_data()
