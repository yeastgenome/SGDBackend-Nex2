import sys
from scripts.loading.database_session import get_session
from src.models import Genomerelease

__author__ = 'sweng66'

datafile = "scripts/dumping/sequence_update/data/dates_of_genome_releases.tab"

def dump_data():

    nex_session = get_session()

    fw = open(datafile, "w")
    
    for x in nex_session.query(Genomerelease).all():
        fw.write("R" + x.display_name + "\t" + str(x.release_date).split(' ')[0] + "\n")

    fw.close()

    nex_session.close()

if __name__ == '__main__':

    dump_data()
