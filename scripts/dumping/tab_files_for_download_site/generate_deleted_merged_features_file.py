from datetime import datetime
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import dbentity_id_feature_type_mapping, \
    get_chr_num_mapping, get_taxonomy_id_for_S288C

__author__ = 'sweng66'

deletedMergedFile = "scripts/dumping/tab_files_for_download_site/data/deleted_merged_features.tab"


def dump_data():
 
    nex_session = get_session()

    """
    1.  Systematic name (not NULL)
    2.  Feature_type|qualifier (not NULL)
    3.  Chromosome (not NULL)
    4.  Start_coordinate (optional)
    5.  Stop_coordinate (optional)
    6.  Strand (optional)
    7.  Primary SGDID (not NULL)
    8.  Secondary SGDID (optional)
    9.  New systematic name (not NULL for Merged features only) 
    10. New Primary SGDID (not NULL for Merged features only) 
    11. Locus Description (not NULL)
    12. Annotation note (not NULL, multiples separated by |)
    13. Date of action (not NULL)
    """

    """
    YCR029C ORF|Deleted     3       172976  172554  C       S000000624                              Deleted ORF; does not encode a protein; included in the original annotation of Chromosome III but deleted due to sequence correction    ORF YCR029C has been deleted from the genome annotation due to sequence correction.     1998-07-24

    YCL012W ORF|Merged      3       100113  100808  W       S000000518              YCL014W S000000520      Merged open reading frame; does not encode a discrete protein; YCL012W was originally annotated as an independent ORF, but as a result of a sequence change, it was merged with an adjacent ORF into a single reading frame, designated YCL014W The stop site of ORF YCL012W was moved 137 nt downstream, lengthening the coding region from 459 nt to 696 nt. Chromosomal coordinates change from 100110-100568 to 100113-100808.        2000-09-13

    21S_rRNA_4 => 1288410 => Non-uniform
    YNCQ0006W/21S_RRNA

    
    """

    print(datetime.now())
    print("Generating deleted_merged_features.tab file...")
    
    nex_session = get_session()

    chr_to_chrnum = get_chr_num_mapping()
    dbentity_id_to_feature_type = dbentity_id_feature_type_mapping(nex_session)
    taxonomy_id = get_taxonomy_id_for_S288C(nex_session)

    fw = open(deletedMergedFile, "w")
    
    rows = get_deleted_or_merged_rows(nex_session, "Merged")

    for x in rows:
        dbentity_id = x[0]
        sgdid = x[1]
        systematic_name = x[2]
        gene_name = x[3] if x[3] else ""
        desc = x[4]
        feature_type = dbentity_id_to_feature_type.get(dbentity_id)
        if feature_type is None:
            print("Merged:", systematic_name, "missing feature type")
            continue
        secondary_sgdid = get_secondary_sgdid(nex_session, dbentity_id)
        # main_systematic_name = get_main_systematic_name(desc, systematic_name)
        # main_sgdid = get_sgdid_by_name(nex_session, main_systematic_name)
        (main_systematic_name, main_sgdid) = get_main_systematic_name(nex_session,
                                                                      desc,
                                                                      systematic_name)
        (note, action_date) = get_notes_dates(nex_session, dbentity_id)
        (chrnum, start, end, strand) = get_chr_coords(nex_session,
                                                      dbentity_id,
                                                      chr_to_chrnum,
                                                      taxonomy_id)
        fw.write(systematic_name + "\t" + feature_type + "|Merged\t" + str(chrnum) + "\t" + str(start) + "\t" + str(end) + "\t" + strand + "\t" + sgdid + "\t" + secondary_sgdid + "\t" + main_systematic_name + "\t" + main_sgdid + "\t" + desc + "\t" + note + "\t" + action_date + "\n")

    rows = get_deleted_or_merged_rows(nex_session, "Deleted")

    for x in rows:
        dbentity_id = x[0]
        sgdid = x[1]
        systematic_name = x[2]
        gene_name = x[3] if x[3] else ""
        desc = x[4]
        feature_type = dbentity_id_to_feature_type.get(dbentity_id)
        if feature_type is None:
            print("Deleted:", systematic_name, "missing feature type")
            continue
        secondary_sgdid = get_secondary_sgdid(nex_session, dbentity_id)
        (note, action_date) = get_notes_dates(nex_session, dbentity_id)
        (chrnum, start, end, strand) = get_chr_coords(nex_session,
                                                      dbentity_id,
                                                      chr_to_chrnum,
                                                      taxonomy_id)
        fw.write(systematic_name + "\t" + feature_type + "|Deleted\t" + str(chrnum) + "\t" + str(start) + "\t" + str(end) + "\t" + strand + "\t" + sgdid + "\t" + secondary_sgdid + "\t\t\t" + desc + "\t" + note + "\t" + action_date + "\n")
        
    fw.close()
    nex_session.close()
    print(datetime.now())
    print("DONE!")


def get_sgdid_by_name(nex_session, systematic_name):

    rows = nex_session.execute("SELECT d.sgdid "
                               "FROM nex.dbentity d, nex.locusdbentity ld "
                               "WHERE d.dbentity_id = ld.dbentity_id "
                               "AND ld.systematic_name = '" + systematic_name + "'").fetchall()
    if len(rows) == 0:
        return ""
    return rows[0][0]

                            
def get_deleted_or_merged_rows(nex_session, dbentity_status):

    rows = nex_session.execute("SELECT d.dbentity_id, d.sgdid, ld.systematic_name, ld.gene_name, ld.description "
                               "FROM nex.locusdbentity ld, nex.dbentity d "
                               "WHERE ld.description is not null "
                               "AND ld.dbentity_id = d.dbentity_id "
                               "AND d.subclass = 'LOCUS' "
                               "AND d.dbentity_status = '" + dbentity_status + "' "
                               "ORDER BY ld.systematic_name").fetchall()

    return rows

    
def get_secondary_sgdid(nex_session, locus_id):

    rows = nex_session.execute("SELECT display_name "
                               "FROM nex.locus_alias "
                               "WHERE alias_type = 'SGDID Secondary' "
                               "AND locus_id = " + str(locus_id)).fetchall()
    if len(rows) == 0:
        return ""
    return "|".join([x[0] for x in rows])


def get_notes_dates(nex_session, locus_id):

    rows = nex_session.execute("SELECT note, date_created "
                               "FROM nex.locusnote "
                               "WHERE note_type = 'Annotation change' "
                               "AND locus_id = " + str(locus_id)).fetchall()
    if len(rows) == 0:
        return ("", "")
    else:
        notes = []
        dates = []
        for x in rows:
            notes.append(x[0].replace("<b>Annotation change:</b>", ""))
            dates.append(str(x[1]).split(" ")[0])
        return ("|".join(notes), "|".join(dates))


def get_chr_coords(nex_session, dbentity_id, chr_to_chrnum, taxonomy_id):

    rows = nex_session.execute(
        "SELECT c.display_name, da.start_index, da.end_index, da.strand "
        "FROM nex.dnasequenceannotation da "
        "JOIN nex.contig c ON da.contig_id = c.contig_id "
        "WHERE da.dbentity_id = :dbentity_id "
        "AND da.taxonomy_id = :taxonomy_id "
        "AND da.dna_type = 'GENOMIC'",
        {'dbentity_id': dbentity_id, 'taxonomy_id': taxonomy_id}
    ).fetchall()

    if len(rows) == 0:
        return ("", "", "", "")
    
    x = rows[0]
    chr = x[0].replace("Chromosome ", "")
    chrnum = chr_to_chrnum[chr]
    start = x[1]
    end = x[2]
    strand = "W" if x[3] == '+' else "C"
    if strand == 'C':
        (start, end) = (end, start)
    return (chrnum, start, end, strand)


def get_main_systematic_name(nex_session, desc, merged_systematic_name):

    """
    desc = desc.replace("/", " ").replace(";", " ")
    desc = desc.replace(",", " ").replace(".", " ")
    words = desc.split(" ")

    for word in words:
        if word != systematic_name and systematic_name[0:3] == word[0:3]:
            return word
    return None
    """
    
    rows = nex_session.execute("SELECT ld.systematic_name, d.sgdid "
                               "FROM nex.locusdbentity ld, nex.dbentity d, nex.locus_alias la "
                               "WHERE ld.dbentity_id = d.dbentity_id "
                               "AND ld.dbentity_id = la.locus_id "
                               "AND la.display_name = '" + merged_systematic_name + "'").fetchall()
    if len(rows) == 1:
        return (rows[0][0], rows[0][1])
    desc = desc.replace("/", " ").replace(";", " ")
    desc = desc.replace(",", " ").replace(".", " ")
    words = desc.split(" ")
    for word in words:
        if word != merged_systematic_name and merged_systematic_name[0:3] == word[0:3]:
            systematic_name = word
            sgdid = get_sgdid_by_name(nex_session, systematic_name)
            return (systematic_name, sgdid)
    return (None, None)                           
                               
                               

if __name__ == '__main__':
    
    dump_data()

    


