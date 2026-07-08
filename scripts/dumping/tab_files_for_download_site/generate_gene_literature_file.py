from datetime import datetime
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

geneLitFile = "scripts/dumping/tab_files_for_download_site/data/gene_literature.tab"

    
def dump_data():

    """
    1) PubMed ID (optional)         - the unique PubMed identifer for a reference
    2) citation (mandatory)         - the citation for the publication, as stored in SGD
    3) gene name (optional)         - Gene name, if one exists
    4) feature (optional)           - Systematic name, if one exists
    5) literature_topic (mandatory) - all associated Literature Topics of the SGD Literature Guide
                                      relevant to this gene/feature within this paper
                                      Multiple literature topics are separated by a '|' character.
    6) SGDID (mandatory)            - the SGDID, unique database identifier, for the gene/feature
    """

    """
    5666    Ishiguro J (1976) Study on proteins from yeast cytoplasmic ribosomes by two-dimensional gel electrophoresis. Mol Gen Genet 145(1):73-9  RPS12   YOR369C Protein Physical Properties|Additional Literature|Cellular Location     S000005896
    """
    
    print(datetime.now())
    print("Generating gene_literature.tab file...")
    
    nex_session = get_session()

    fw = open(geneLitFile, "w")

    rows = nex_session.execute("SELECT ld.systematic_name, ld.gene_name, d.sgdid, rd.pmid, "
                               "       rd.citation, la.topic "
                               "FROM nex.literatureannotation la, nex.locusdbentity ld, "
                               "     nex.referencedbentity rd, nex.dbentity d "
                               "WHERE la.dbentity_id is not null "
                               "AND la.dbentity_id = ld.dbentity_id "
                               "AND ld.dbentity_id = d.dbentity_id "
                               "AND la.reference_id = rd.dbentity_id "
                               "ORDER BY rd.pmid, ld.systematic_name, la.topic").fetchall()
    key_to_topics = {}
    for x in rows:
        systematic_name = x['systematic_name']
        gene_name = x['gene_name'] if x['gene_name'] else ""
        sgdid = "SGD:" + x['sgdid']
        pmid = "PMID:" + str(x['pmid']) if x['pmid'] else ""
        citation = x['citation'] if x['citation'] else ""
        topic = x['topic']
        key = (pmid, citation, systematic_name, gene_name, sgdid)        
        topics = key_to_topics.get(key, [])
        topics.append(topic)
        key_to_topics[key] = topics
    sorted_keys = sorted(key_to_topics.keys(), key=lambda k: int(k[0].split(":")[1]) if k[0].startswith("PMID:") else float('inf'))
    for key in sorted_keys:
        (pmid, citation, systematic_name, gene_name, sgdid) = key
        topic_list = "|".join(key_to_topics[key])
        fw.write(pmid + "\t" + citation + "\t" + gene_name + "\t" + systematic_name + "\t" + topic_list + "\t" + sgdid + "\n") 
        
    nex_session.close()
    fw.close()
    print(datetime.now())
    print("DONE!")


if __name__ == '__main__':
    
    dump_data()

    


