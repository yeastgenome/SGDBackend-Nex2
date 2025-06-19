from datetime import datetime
from src.models import Posttranslationannotation, Dbentity, Psimod
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import dbentity_id_to_data_mapping
 
__author__ = 'sweng66'

ptmFile = "scripts/dumping/tab_files_for_download_site/data/posttranslational_modifications.tab"


def dump_data():

    """
    1) SGDID
    2) Systematic name (mandatory)                  - systematic name of the yeast gene
    3) Gene name (optional)                         - genetic name of the yeast gene, for named genes
    4) residue
    5) coordinate
    6) modification (nex.psimod.display_name)
    7) PSI-MOD ID (nex.psimod.psimodid)
    8) modifier systematic_name (if complex, use complex accession ex. CPX-1717)
    9) modifier gene_name (if complex, use nex.complex_alias.display_name ex. TORC2 complex)
    10) strain background
    11) reference
    """

    # dbentity.format_name =  CPX-1717
    # nex.complex_alias.display_nam = TORC2 complex
    
    print(datetime.now())
    print("Generating posttranslational_modification.tab file...")
    
    nex_session = get_session()
    
    fw = open(ptmFile, "w")

    dbentity_id_to_data = dbentity_id_to_data_mapping(nex_session)
    psimod_id_to_obj = dict([(x.psimod_id, x) for x in nex_session.query(Psimod).all()])
    complex_id_to_accession = dict([(x.dbentity_id, x.format_name) for x in nex_session.query(Dbentity).filter_by(subclass='COMPLEX').all()])
    
    rows = nex_session.execute(
        """
        SELECT sd.taxonomy_id, d.display_name
        FROM nex.straindbentity sd
        JOIN nex.dbentity d USING (dbentity_id)
        """
    ).fetchall()

    taxonomy_id_to_strain_name = {}
    for x in rows:
        taxonomy_id_to_strain_name[x[0]] = x[1]
        # print("TAXONOMY MAPPING:", x[0], x[1])

    rows = nex_session.execute(
        """
        SELECT complex_id, display_name
        FROM nex.complex_alias
        """
    ).fetchall()
    
    complex_id_to_display_names = {}
    for x in rows:
        # print("COMPLEX MAPPING:", x[0], x[1])
        display_names = complex_id_to_display_names.get(x[0], [])
        display_names.append(x[1])
        complex_id_to_display_names[x[0]] = display_names
        
    fw.write("SGDID\tSystematic name\tGene name\tResidue\tCoordinate\tModification\tPSI-MOD ID\tModifier Systematic name\tModifier gene name\tStrain background\tPMID\n")

    for x in nex_session.query(Posttranslationannotation).all():
        if x.dbentity_id not in dbentity_id_to_data:
            print("dbentity_id =", x.dbentity_id, "is not in dbentity_id_to_data")
            continue
        (sgdid, systematic_name, gene_name, qualifier, genetic_position, desc) = dbentity_id_to_data[x.dbentity_id]
        gene_name = gene_name if gene_name else ""
        residue = x.site_residue
        coord = x.site_index
        psimod_obj = psimod_id_to_obj.get(x.psimod_id)
        if not psimod_obj:
            print("psimod_id=", x.psimod_id, "is not in psimod table")
            continue
        modification = psimod_obj.display_name
        psimodID = psimod_obj.psimodid
        strain_name = taxonomy_id_to_strain_name.get(x.taxonomy_id, '')
        m_systematic_name = ''
        m_gene_name = ''
        if x.modifier_id:
            if x.modifier_id in dbentity_id_to_data:
                (m_sgdid, m_systematic_name, m_gene_name, m_qualifier, m_genetic_position, m_desc) = dbentity_id_to_data[x.modifier_id]
            elif x.modifier_id in complex_id_to_accession:
                m_systematic_name = complex_id_to_accession[x.modifier_id]
                if x.modifier_id in complex_id_to_display_names:
                    m_gene_name = "|".join(complex_id_to_display_names[x.modifier_id])
        ref = "PMID:" + str(x.reference.pmid) if x.reference.pmid else x.reference.sgdid
        fw.write(sgdid + "\t" + systematic_name + "\t" + gene_name + "\t" + residue + "\t" + str(coord) + "\t" + modification + "\t" + psimodID + "\t" + m_systematic_name + "\t" + m_gene_name + "\t" + strain_name + "\t" + ref +  "\n")

    nex_session.close()
    fw.close()
    print(datetime.now())
    print("DONE!")

    
if __name__ == '__main__':
    
    dump_data()

    


