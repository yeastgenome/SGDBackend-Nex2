import os
from datetime import datetime
import sys
from src.models import Locusdbentity, Dnasequenceannotation, \
     Dnasubsequence
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logfileFull = "scripts/loading/sequence/logs/intron_coords_to_be_checked_full.txt"
logfileAuto = "scripts/loading/sequence/logs/intron_coords_to_be_fixed_automatically.txt"
logfileManual = "scripts/loading/sequence/logs/intron_coords_to_be_checked_manually.txt"

"""
D273-10B         275315
FL100            274944
JK9-3d           275321
RM11-1a          274425
S288C            274901
W303             274910
X2180-1A         275329
SEY6210          275326
Y55              275334
SK1              274909
Sigma1278b       274916
CEN.PK           275338
"""

def check_intron_coords():

    db_session = get_session()

    strain_rows = db_session.execute("select d.display_name, sd.taxonomy_id "
                              "from nex.dbentity d, nex.straindbentity sd "
                              "where d.dbentity_id = sd.dbentity_id "
                              "and display_name in ('S288C', 'CEN.PK', 'D273-10B', 'FL100', 'JK9-3d', 'RM11-1a', 'SEY6210', 'Sigma1278b', 'SK1', 'W303', 'X2180-1A', 'Y55')").fetchall()

    strain_to_genes_with_intron = {}
    strain_to_taxonomy_id = {}
    for x in strain_rows:
        strain = x[0]
        taxonomy_id = x[1]
        strain_to_taxonomy_id[strain] = taxonomy_id
        
        intron_rows = db_session.execute("select dsa.dbentity_id, ld.systematic_name "
                                         "from nex.dnasubsequence dss, nex.dnasequenceannotation dsa, nex.locusdbentity ld "
                                         "where dsa.taxonomy_id = " + str(taxonomy_id) + " "
                                         "and dsa.dna_type = 'GENOMIC' "
                                         "and dsa.dbentity_id = ld.dbentity_id "
                                         "and dsa.annotation_id = dss.annotation_id "
                                         "and dss.display_name = 'intron'").fetchall()
        for y in intron_rows:
            dbentity_id = y[0]
            gene = y[1]
            genes_with_intron = strain_to_genes_with_intron.get(strain, [])
            genes_with_intron.append((gene, dbentity_id))
            strain_to_genes_with_intron[strain] = genes_with_intron

    
    S288C_genes_to_subfeatures = get_all_subfeatures(db_session, strain_to_taxonomy_id['S288C'],
                                                     strain_to_genes_with_intron['S288C'])
    db_session.close()

    fw_full = open(logfileFull, "w")
    fw_auto = open(logfileAuto, "w")
    fw_manual = open(logfileManual, "w")
    
    for strain in strain_to_genes_with_intron:

        db_session = get_session()
        
        genes_to_subfeatures = get_all_subfeatures(db_session, strain_to_taxonomy_id[strain],
                                                   strain_to_genes_with_intron[strain])

        for (gene, dbentity_id) in genes_to_subfeatures:
            S288C_gene_subfeatures = S288C_genes_to_subfeatures.get((gene, dbentity_id), [])
            this_strain_genes_subfeatures = genes_to_subfeatures[(gene, dbentity_id)]
            if S288C_gene_subfeatures == this_strain_genes_subfeatures:
                continue
            reversed_strain_genes_subfeatures = reverse_coords(this_strain_genes_subfeatures)
            fw_full.write("S288C  " + "\t" + gene + "\t" + str(dbentity_id) + "\t" + str(S288C_gene_subfeatures) + "\n")
            fw_full.write(strain + "\t" + gene + "\t" + str(dbentity_id) + "\t" + str(this_strain_genes_subfeatures) + "\n\n")

            if reversed_strain_genes_subfeatures == S288C_gene_subfeatures:
                fw_auto.write("S288C  " + "\t" + gene + "\t" + str(dbentity_id) + "\t" + str(S288C_gene_subfeatures) + "\n")
                fw_auto.write(strain + "\t" + gene + "\t" + str(dbentity_id) + "\t" + str(this_strain_genes_subfeatures) + "\n")
                fw_auto.write(strain + "\t" + gene + "\t" + str(dbentity_id) + "\t" + str(reversed_strain_genes_subfeatures) + "\tauto reversed\n\n")
            elif len(S288C_gene_subfeatures) > 0:
                fw_manual.write("S288C  " + "\t" + gene + "\t" + str(dbentity_id) + "\t" + str(S288C_gene_subfeatures) + "\n")
                fw_manual.write(strain + "\t" + gene + "\t" + str(dbentity_id) + "\t" + str(this_strain_genes_subfeatures) + "\n")
                fw_manual.write(strain + "\t" + gene + "\t" + str(dbentity_id) + "\t" + str(reversed_strain_genes_subfeatures) + "\treversed coords - need manually check\n\n")
        db_session.close()
    
    fw_full.close()
    fw_auto.close()
    fw_manual.close()
    

def reverse_coords(this_strain_genes_subfeatures):
    lastCDS = this_strain_genes_subfeatures[-1]
    (subfeature, last_cds_start, last_cds_end) = lastCDS
    new_coords = []
    for (name, start, end) in this_strain_genes_subfeatures:
        newEnd = last_cds_end - start + 1
        newStart = last_cds_end - end + 1
        new_coords.append((name, newStart, newEnd))
    new_coords.reverse() 
    return new_coords


def get_all_subfeatures(db_session, taxonomy_id, genes_with_intron):

    gene_to_subfeatures = {}
    for (gene, dbentity_id) in genes_with_intron:
        
        rows = db_session.execute("select dss.display_name, dss.relative_start_index, dss.relative_end_index "
                                  "from nex.dnasubsequence dss, nex.dnasequenceannotation dsa "
                                  "where dsa.taxonomy_id = " + str(taxonomy_id) + " "
                                  "and dsa.dna_type = 'GENOMIC' "
                                  "and dsa.dbentity_id = " + str(dbentity_id) + " "
                                  "and dsa.annotation_id = dss.annotation_id "
                                  "order by 2, 3").fetchall()
        subfeatures = []
        for x in rows:
            subfeatures.append((x[0], x[1], x[2]))
        gene_to_subfeatures[(gene, dbentity_id)] = subfeatures
    return gene_to_subfeatures

        
if __name__ == '__main__':

    check_intron_coords()
