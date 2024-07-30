from datetime import datetime
from src.models import Pathwayannotation, LocusAlias, Ec, Dbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

pathwayFile = "scripts/dumping/tab_files_for_download_site/data/biochemical_pathways.tab"

    
def dump_data():

    """
    1) biochemical pathway common name      - name of the biochemical pathway, as
                                              stored in SGD (mandatory)
    2) enzyme name (optional)               - name of a specific enzyme (may be
                                              single or multi subunit)
    3) E.C number of reaction (optional)    - Enzyme Commission identifier of the reaction,
                                              e.g. EC:1.1.1.1
    4) gene name (optional)                 - Gene name for the enzyme catalyzing the
                                              reaction, if identified
    5) reference (optional)                 - if the pathway has been curated from the literature,
                                              the SGDID of the reference (prefaced by SGD_REF:)
                                              or the Pubmed ID of the reference (prefaced by PMID:)
                                              will be listed
    """

    """
    acetate utilization     Acetate--CoA ligase     6.2.1.1 ACS1    
    acetate utilization     Acetate--CoA ligase     6.2.1.1 ACS2    
    acetoin biosynthesis    acetoin dehydrogenase   1.1.1.5 BDH1    PMID:16535224|PMID:10938079
    acetoin biosynthesis    Acetolactate synthase   2.2.1.6 ILV2    PMID:16535224|PMID:10938079
    acetoin biosynthesis    Acetolactate synthase   2.2.1.6 ILV6    PMID:16535224|PMID:10938079
    acetoin biosynthesis II         4.1.1.1 PDC1    PMID:16535224|PMID:2404950|PMID:6383467
    acetoin biosynthesis II         4.1.1.1 PDC5    PMID:16535224|PMID:2404950|PMID:6383467
    """

    print(datetime.now())
    print("Generating biochemical_pathways.tab file...")

    nex_session = get_session()

    rows = nex_session.query(Pathwayannotation).all()
    pathway_id_to_gene_refs = {}
    gene_to_locus_id = {}
    for x in rows:
        gene_refs = []
        if x.pathway_id in pathway_id_to_gene_refs:
            gene_refs = pathway_id_to_gene_refs[x.pathway_id]
        gene = x.dbentity.display_name
        gene_to_locus_id[gene] = x.dbentity_id
        ref = ''
        if x.reference:
            if x.reference.pmid:
                ref = "PMID:" + str(x.reference.pmid)
            else:
                ref = "SGD_REF:" + x.sgdid
        gene_refs.append((gene, ref))
        pathway_id_to_gene_refs[x.pathway_id] = gene_refs
    
    locus_id_to_ecnumbers = {}
    for x in nex_session.query(LocusAlias).filter_by(alias_type='EC number').all():
        ecnumbers = []
        if x.locus_id in locus_id_to_ecnumbers:
            ecnumbers = locus_id_to_ecnumbers[x.locus_id]
        ecnumbers.append(x.display_name)
        locus_id_to_ecnumbers[x.locus_id] = ecnumbers

    ecnumber_to_name = {}
    for x in nex_session.query(Ec).all():
         ecnumber_to_name[x.display_name.replace("EC:", "")] = x.description

    key_to_refs = {}
    for x in nex_session.query(Dbentity).filter_by(subclass='PATHWAY').order_by(Dbentity.display_name).all():
        pathway_id = x.dbentity_id
        if pathway_id not in pathway_id_to_gene_refs:
            # fw.write(x.display_name + "\t\t\t\t\n")
            key = (x.display_name, "", "", "")
            key_to_refs[key] = []
        else:
            for (gene, ref) in pathway_id_to_gene_refs[pathway_id]:
                locus_id = gene_to_locus_id[gene]
                ecnumbers = locus_id_to_ecnumbers.get(locus_id, [])
                for ecnumber in ecnumbers:
                    enzyme_name = ecnumber_to_name.get(ecnumber, "")
                    key = (x.display_name, enzyme_name, ecnumber, gene)
                    refs = []
                    if key in key_to_refs:
                        refs = key_to_refs[key]
                    refs.append(ref)
                    key_to_refs[key] = refs
                    # fw.write(x.display_name + "\t" + enzyme_name + "\t" + ecnumber + "\t" + gene + "\t" + ref + "\n")

    fw = open(pathwayFile, "w")
    for key in key_to_refs:
        (display_name, enzyme_name, ecnumber, gene) = key
        refs = "|".join(key_to_refs[key])
        fw.write(display_name + "\t" + enzyme_name + "\t" + ecnumber + "\t" + gene + "\t" + refs + "\n") 
    fw.close()
    nex_session.close()
    print(datetime.now())
    print('DONE!')


if __name__ == '__main__':
    
    dump_data()

    


