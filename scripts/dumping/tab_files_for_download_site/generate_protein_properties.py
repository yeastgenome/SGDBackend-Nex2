from datetime import datetime
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import get_taxonomy_id_for_S288C

__author__ = 'sweng66'

proteinPropFile = "scripts/dumping/tab_files_for_download_site/data/protein_properties.tab"


def dump_data():

    """
    ORF (Systematic Name)
    Mw (Molecular Weight)
    PI (Isoelectric Point)
    Protein Length
    N_term_seq
    C_term_seq
    GRAVY Score (Hydropathicity of Protein)
    Aromaticity Score (Frequency of aromatic amino acids: Phe, Tyr, Trp)
    CAI (Codon Adaptation Index)
    Codon Bias
    FOP Score (Frequency of Optimal Codons)>
    Ala
    Cys
    Asp
    Glu
    Phe
    Gly
    His
    Ile
    Lys
    Leu
    Met
    Asn
    Pro
    Gln
    Arg
    Ser
    Thr
    Val
    Trp
    Tyr
    CARBON
    HYDROGEN
    NITROGEN
    OXYGEN
    SULPHUR
    INSTABILITY INDEX (II)
    ASSUMING ALL CYS RESIDUES APPEAR AS HALF CYSTINES
    ASSUMING NO CYS RESIDUES APPEAR AS HALF CYSTINES
    ALIPHATIC INDEX
    """

    print(datetime.now())
    print("Generating protein_properties.tab file...") 
    nex_session = get_session()

    taxonomy_id = get_taxonomy_id_for_S288C(nex_session)

    rows = nex_session.execute("SELECT ld.systematic_name, psd.* "
                               "FROM nex.locusdbentity ld, nex.proteinsequenceannotation psa, nex.proteinsequence_detail psd "
                               "WHERE ld.dbentity_id = psa.dbentity_id "
                               "AND psa.taxonomy_id = " + str(taxonomy_id) + " "
                               "AND psa.annotation_id = psd.annotation_id").fetchall()
                               
    fw = open(proteinPropFile, "w")
    fw.write("ORF\tMw\tPI\tProtein Length\tN_term_seq\tC_term_seq\t")
    fw.write("GRAVY Score\tAromaticity Score\tCAI\tCodon Bias\tFOP Score\t")
    fw.write("Ala\tCys\tAsp\tGlu\tPhe\tGly\tHis\tIle\tLys\tLeu\tMet\tAsn\tPro\tGln\t")
    fw.write("Arg\tSer\tThr\tVal\tTrp\tTyr\tCARBON\tHYDROGEN\tNITROGEN\tOXYGEN\tSULPHUR\tINSTABILITY INDEX (II)\t")
    fw.write("ASSUMING ALL CYS RESIDUES APPEAR AS HALF CYSTINES\tASSUMING NO CYS RESIDUES APPEAR AS HALF CYSTINES\t")
    fw.write("ALIPHATIC INDEX\n")
    for x in rows:
        fw.write(x['systematic_name'] + "\t" + str(x['molecular_weight']) + "\t" + str(x['pi']) + "\t" + str(x['protein_length']) + "\t")
        fw.write(x['n_term_seq'] + "\t" + x['c_term_seq'] + "\t" + str(x['gravy_score']) + "\t" + str(x['aromaticity_score']) + "\t")
        fw.write(str(x['cai']) + "\t" + str(x['codon_bias']) + "\t" + str(x['fop_score']) + "\t" + str(x['ala']) + "\t")
        fw.write(str(x['cys']) + "\t" + str(x['asp']) + "\t" + str(x['glu']) + "\t" + str(x['phe']) + "\t")
        fw.write(str(x['gly']) + "\t" + str(x['his']) + "\t" + str(x['ile']) + "\t" + str(x['lys']) + "\t")
        fw.write(str(x['leu']) + "\t" + str(x['met']) + "\t" + str(x['asn']) + "\t" + str(x['pro']) + "\t")
        fw.write(str(x['gln']) + "\t" + str(x['arg']) + "\t" + str(x['ser']) + "\t" + str(x['thr']) + "\t")
        fw.write(str(x['val']) + "\t" + str(x['trp']) + "\t" + str(x['tyr']) + "\t" + str(x['carbon']) + "\t")
        fw.write(str(x['hydrogen']) + "\t" + str(x['nitrogen']) + "\t" + str(x['oxygen']) + "\t" + str(x['sulfur']) + "\t")
        fw.write(str(x['instability_index']) + "\t" + str(x['all_cys_ext_coeff']) + "\t" + str(x['no_cys_ext_coeff']) + "\t")
        fw.write(str(x['aliphatic_index']) + "\n")
    
    fw.close()
    nex_session.close()
    print(datetime.now())
    print("DONE!")
    
    
if __name__ == '__main__':
    
    dump_data()

    


