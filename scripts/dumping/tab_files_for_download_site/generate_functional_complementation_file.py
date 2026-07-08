from datetime import datetime
import gzip
import urllib.request, urllib.parse, urllib.error
from src.models import Functionalcomplementannotation
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import dbentity_id_to_data_mapping
 
__author__ = 'sweng66'

funcComplFile = "scripts/dumping/tab_files_for_download_site/data/functional_complementation.tab"


def dump_data():

    """
    1) Systematic name (mandatory)                  - systematic name of the yeast gene
    2) Gene name (optional)                         - genetic name of the yeast gene, for named genes
    3) HGNC approved symbol (mandatory)             - name of the human gene 
    4) HGNC ID (mandatory)                          - identifier for the human gene
    5) direction of complementation (mandatory)     - denotes whether the human gene complements the
                                                      yeast mutation or vice versa
    6) PMID (mandatory)                             - the PubMed identifier for the reference supporting
                                                      complementation
    7) Source (mandatory)                           - project that performed the curation (SGD or P-POD)
    8) Note (optional)                              - free-text note explaining any details
    """

    """
    Systematic name Gene name       HGNC approved symbol    HGNC ID Direction of complementation    PMID    Source  Note
    YLR304C ACO1    ACO2    HGNC:118        human gene complements S. cerevisiae mutation   15263083        P-POD   
    YLR304C ACO1    ACO2    HGNC:118        human gene complements S. cerevisiae mutation   25351951        SGD     
    YLR359W ADE13   ADSL    HGNC:291        human gene complements S. cerevisiae mutation   25999509        SGD     Human gene allows growth of the yeast haploid null mutant after sporulation of a hete/rozygous diploid.
    """

    print(datetime.now())
    print("Generating functional_complementation.tab file...")
    
    nex_session = get_session()
    
    fw = open(funcComplFile, "w")

    hgnc_to_symbol = get_HGNC_to_symbol_mapping()
    dbentity_id_to_data = dbentity_id_to_data_mapping(nex_session)

    fw.write("Systematic name\tGene name\tHGNC approved symbol\tHGNC ID\tDirection of complementation\tPMID\tSource\tNote\n")

    for x in nex_session.query(Functionalcomplementannotation).all():
        (sgdid, systematic_name, gene_name, qualifier, genetic_position, desc) = dbentity_id_to_data[x.dbentity_id]
        hgnc_symbol = hgnc_to_symbol.get(x.dbxref_id, "")
        gene_name = gene_name if gene_name else ""
        note = x.curator_comment if x.curator_comment else ""
        ref = "PMID:" + str(x.reference.pmid) if x.reference.pmid else x.reference.sgdid
        fw.write(systematic_name + "\t" + gene_name + "\t" + hgnc_symbol + "\t" + x.dbxref_id + "\t" + x.direction + "\t" + ref + "\t" + x.source.display_name + "\t" + note + "\n")


    nex_session.close()
    fw.close()
    print(datetime.now())
    print("DONE!")


def get_HGNC_to_symbol_mapping():

    url_path = "https://fms.alliancegenome.org/download/"
    mappingfile = "GENE-DESCRIPTION-TXT_HUMAN.txt.gz"
    urllib.request.urlretrieve(url_path + mappingfile, mappingfile)
    urllib.request.urlcleanup()

    f = gzip.open(mappingfile, 'rt')
    HGNC_to_symbol_mapping = {}
    for line in f:
        if line.startswith("HGNC:"):
            [hgnc, symbol] = line.strip().split("\t")
            HGNC_to_symbol_mapping[hgnc] = symbol
    f.close()
    return HGNC_to_symbol_mapping

    
if __name__ == '__main__':
    
    dump_data()

    


