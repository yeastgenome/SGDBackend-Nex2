from datetime import datetime
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

alleleFile = "scripts/dumping/tab_files_for_download_site/data/alleles.tab"

    
def dump_data():

    """
    Gene SGDID (dbentity.sgdid)
    Gene systematic_name (locusdbentity.systematic_name)
    Gene standard_name (locusdbentity.gene_name)
    Allele SGDID (dbentity.sgdid)
    Allele name (dbentity.display_name)
    Allele class (so.display_name where so.so_id = alleledbentity.so_id)
    Allele description (alleledbentity.description)
    Allele Alias (allele_alias.display_name)
    """
    
    print(datetime.now())
    print("Generating alleles.tab file...")
    
    nex_session = get_session()

    rows = nex_session.execute("SELECT allele_id, display_name "
                               "FROM nex.allele_alias "
                               "ORDER BY allele_id, display_name").fetchall()
    allele_id_to_aliases = {}
    for x in rows:
        if x['display_name'].startswith("S000"):
            continue
        aliases = allele_id_to_aliases.get(x['allele_id'], [])
        aliases.append(x['display_name'])
        allele_id_to_aliases[x['allele_id']] = aliases

    fw = open(alleleFile, "w")

    rows = nex_session.execute("SELECT d1.sgdid, ld.systematic_name, ld.gene_name, d2.sgdid, "
                               "       d2.display_name, s.display_name, ad.description, "
                               "       ad.dbentity_id "
                               "FROM nex.locusdbentity ld, nex.dbentity d1, nex.alleledbentity ad, "
                               "     nex.dbentity d2, nex.so s, nex.locus_allele la "
                               "WHERE la.locus_id = ld.dbentity_id "
                               "AND ld.dbentity_id = d1.dbentity_id "
                               "AND la.allele_id = ad.dbentity_id "
                               "AND ad.dbentity_id = d2.dbentity_id "
                               "AND ad.so_id = s.so_id "
                               "ORDER BY ld.systematic_name, d2.display_name").fetchall()
    for x in rows:
        gene_sgdid = x[0]
        gene_systematic_name = x[1]
        gene_standard_name = x[2] if x[2] else ""
        allele_sgdid = x[3]
        allele_name = x[4]
        allele_class = x[5]
        allele_desc = x[6] if x[6] else ""
        allele_id = x[7]
        aliases = "|".join(allele_id_to_aliases.get(allele_id, []))
        
        fw.write(gene_sgdid + "\t" + gene_systematic_name + "\t" + gene_standard_name + "\t" + allele_sgdid + "\t" + allele_name + "\t" + allele_class + "\t" + allele_desc + "\t" + aliases + "\n")

    fw.close()
    nex_session.close()
    print(datetime.now())
    print("DONE!")


if __name__ == '__main__':
    
    dump_data()

    


