from datetime import datetime
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import dbentity_id_to_data_mapping, \
    get_taxonomy_id_for_S288C, get_chr_num_mapping

__author__ = 'sweng66'

sgdFeatureFile = "scripts/dumping/tab_files_for_download_site/data/SGD_features.tab"


def dump_data():

    """
    1.   Primary SGDID (mandatory)
    2.   Feature type (mandatory)
    3.   Feature qualifier (optional)
    4.   Feature name (optional)
    5.   Standard gene name (optional)
    6.   Alias (optional, multiples separated by |) (eg, actin|ABY1|END7)
    7.   Parent feature name (optional)  (eg.  "chromosome 6", "YFL039C"
    8.   Secondary SGDID (optional, multiples separated by |)
    9.   Chromosome (optional) (eg, 6)
    10.  Start_coordinate (optional)
    11.  Stop_coordinate (optional)
    12.  Strand (optional)
    13.  Genetic position (optional)
    14.  Coordinate version (optional)
    15.  Sequence version (optional)
    16.  Description (optional)
    """

    print(datetime.now())
    print("Generating SGD_features.tab file...")
    nex_session = get_session()
    
    dbentity_id_to_data = dbentity_id_to_data_mapping(nex_session)
    taxonomy_id = get_taxonomy_id_for_S288C(nex_session)
    chr_to_chrnum = get_chr_num_mapping()

    # "WHERE alias_type in ('Uniform', 'NCBI protein name', 'SGDID Secondary') "
    rows = nex_session.execute("SELECT locus_id, display_name, alias_type "
                               "FROM nex.locus_alias "
                               "WHERE alias_type in ('Uniform', 'Non-uniform', 'Retired nameetired name', 'NCBI protein name', 'SGDID Secondary') "
                               "ORDER by 1, 2").fetchall()
    dbentity_id_to_aliases = {}
    dbentity_id_to_secondary_sgdids = {}
    for x in rows:
        locus_id = x['locus_id']
        aliases = dbentity_id_to_aliases.get(locus_id, [])
        sgdids = dbentity_id_to_secondary_sgdids.get(locus_id, [])
        if x['alias_type'] == 'SGDID Secondary':
            sgdids.append(x['display_name'])
            dbentity_id_to_secondary_sgdids[locus_id] = sgdids
        else:
            aliases.append(x['display_name'])
            dbentity_id_to_aliases[locus_id] = aliases
        
    rows = nex_session.execute("SELECT so_id, display_name "
                               "FROM nex.so").fetchall()
    so_id_to_display_name = {}
    for x in rows:
        so_id_to_display_name[x['so_id']] = x['display_name']

    rows = nex_session.execute("SELECT contig_id, display_name "
                               "FROM nex.contig "
                               "WHERE display_name like 'Chromosome%'").fetchall()
    contig_id_to_chromosome = {}
    contig_id_to_chrnum = {}
    for x in rows:
        chr = x['display_name'].replace("Chromosome ", "")
        chrnum = chr_to_chrnum[chr]
        contig_id_to_chromosome[x['contig_id']] = "chromosome " + str(chrnum)
        contig_id_to_chrnum[x['contig_id']] = chrnum

    rows = nex_session.execute("SELECT annotation_id, display_name, contig_start_index, "
                               "       contig_end_index, coord_version, seq_version "
                               "FROM nex.dnasubsequence "
                               "ORDER BY 1, 2").fetchall()
    annotation_id_to_subfeatures = {}
    for x in rows:
        data = (x['display_name'], x['contig_start_index'], x['contig_end_index'], str(x['coord_version']).split(' ')[0], str(x['seq_version']).split(' ')[0])
        if x['annotation_id'] in annotation_id_to_subfeatures:
            annotation_id_to_subfeatures[x['annotation_id']].append(data)
        else:
            annotation_id_to_subfeatures[x['annotation_id']] = [data]
            
    rows = nex_session.execute(f"SELECT dbentity_id, annotation_id, contig_id, so_id, strand, start_index, "
                               f"       end_index, coord_version, seq_version "
                               f"FROM nex.dnasequenceannotation "
                               f"WHERE taxonomy_id = {taxonomy_id} "
                               f"AND dna_type = 'GENOMIC'").fetchall()

    fw = open(sgdFeatureFile, "w")
    
    for x in rows:
        if x['dbentity_id'] not in dbentity_id_to_data:
            continue
        dbentity_id = x['dbentity_id']
        annotation_id = x['annotation_id']
        (sgdid, systematic_name, gene_name, qualifier, genetic_position, desc) = dbentity_id_to_data[dbentity_id]    
        feature_type = so_id_to_display_name[x['so_id']]
        if dbentity_id_to_aliases.get(dbentity_id):
            aliases = "|".join(dbentity_id_to_aliases[dbentity_id])
        else:
            aliases = ""
        if dbentity_id_to_secondary_sgdids.get(dbentity_id):
            secondarySGDIDs = "|".join(dbentity_id_to_secondary_sgdids[dbentity_id])
        else:
            secondarySGDIDs = ""
        start = x['start_index']
        end = x['end_index']
        if x['strand'] == '-':
            strand = 'C'
            (start, end) = (end, start)
        else:
            strand = 'W'
        chrnum = contig_id_to_chrnum.get(x['contig_id'])
        if chrnum is None:
            continue
        if qualifier is None:
            qualifier = ""
        if gene_name is None:
            gene_name = ""
        if genetic_position is None:
            genetic_position = ""
        fw.write(sgdid + "\t" + feature_type + "\t" + qualifier + "\t" + systematic_name + "\t" + gene_name + "\t" + aliases + "\t" + contig_id_to_chromosome[x['contig_id']] + "\t" + secondarySGDIDs + "\t" + str(chrnum) + "\t" + str(start) + "\t" + str(end) + "\t" + strand + "\t" + str(genetic_position) + "\t" + str(x['coord_version']).split(' ')[0] + "\t" + str(x['seq_version']).split(' ')[0] + "\t" + desc + "\n")
        subfeatures = annotation_id_to_subfeatures.get(x['annotation_id'])
        if subfeatures is None:
            continue
        for (display_name, start4subfeat, end4subfeat, coordVersion4subfeat, seqVersion4subfeat) in subfeatures:
            if strand == 'C':
                (start4subfeat, end4subfeat) = (end4subfeat, start4subfeat)
            fw.write(sgdid + "\t" + display_name + "\t\t\t\t\t" + systematic_name + "\t\t" + str(chrnum) + "\t" + str(start4subfeat) + "\t" + str(end4subfeat) + "\t" + strand + "\t\t" + coordVersion4subfeat + "\t" + seqVersion4subfeat + "\t\n")

    fw.close()
    nex_session.close()
    print(datetime.now())
    print("DONE!")


if __name__ == '__main__':
    
    dump_data()

    


