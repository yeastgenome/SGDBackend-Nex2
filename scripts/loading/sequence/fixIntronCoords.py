import os
from datetime import datetime
import sys
from typing import List
import ast
from src.models import Locusdbentity, Dnasequenceannotation, \
     Dnasubsequence
from scripts.loading.database_session import get_session

__author__ = 'sweng66'


# coordFile = "scripts/loading/sequence/data/intron_coords_to_be_fixed_automatically.txt"
coordFile = "scripts/loading/sequence/data/intronChanges2make112224sw.txt"

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

def fix_intron_coords():

    db_session = get_session()

    strain_rows = db_session.execute("select d.display_name, sd.taxonomy_id "
                              "from nex.dbentity d, nex.straindbentity sd "
                              "where d.dbentity_id = sd.dbentity_id "
                              "and display_name in ('S288C', 'CEN.PK', 'D273-10B', 'FL100', 'JK9-3d', 'RM11-1a', 'SEY6210', 'Sigma1278b', 'SK1', 'W303', 'X2180-1A', 'Y55')").fetchall()

    strain_to_taxonomy_id = {}
    for x in strain_rows:
        strain_to_taxonomy_id[x[0]] = x[1]

    # print(strain_to_taxonomy_id)

    f = open(coordFile)

    old_coord = None
    for line in f:
        if line.strip() == '':
            old_coord = None
            continue
        pieces = line.strip().split("\t")
        if line.startswith("S288C"):
            print("S288C:", pieces[3])
            continue
        
        if old_coord is None:
            old_coord = ast.literal_eval(pieces[3])
        else:
            new_coord = ast.literal_eval(pieces[3])
            print(pieces[0], strain_to_taxonomy_id[pieces[0]], pieces[1], pieces[2], old_coord)
            print(pieces[0], strain_to_taxonomy_id[pieces[0]], pieces[1], pieces[2], new_coord)
            reversed_new_coord = new_coord[::-1]
            print(pieces[0], strain_to_taxonomy_id[pieces[0]], pieces[1], pieces[2], reversed_new_coord)
            strain = pieces[0]
            gene = pieces[1]
            dbentity_id = pieces[2]
            taxonomy_id = strain_to_taxonomy_id[strain]
            fix_subfeature_coords(db_session, gene, dbentity_id, taxonomy_id,
                                  old_coord, reversed_new_coord)

    f.close()
    
    # db_session.rollback()
    db_session.commit()
    db_session.close()
    

    
def fix_subfeature_coords(db_session, gene, dbentity_id, taxonomy_id, old_coord, reversed_new_coord):

    row = db_session.execute("SELECT annotation_id "
                             "FROM nex.dnasequenceannotation "
                             "WHERE taxonomy_id = " + str(taxonomy_id) + " "
                             "AND dna_type = 'GENOMIC' "
                             "AND dbentity_id = " + str(dbentity_id)).fetchone()
    if row is None:
        print("NO dnasequenceannotation row found for taxonomy_id=", taxonomy_id, ",  dbentity_id=",  dbentity_id)
        return
    annotation_id = row.annotation_id
    print("annotation_id=", annotation_id)

    i = 0
    for (new_display_name, new_start_index, new_stop_index) in reversed_new_coord:
        (old_display_name, old_start_index, old_stop_index) = old_coord[i]
        i += 1
        try:
            db_session.execute("UPDATE nex.dnasubsequence "
                               "set relative_start_index = " + str(new_start_index) + ", "
                               " relative_end_index = " + str(new_stop_index) + ", "
                               " display_name = '" + new_display_name + "' "
                               "WHERE annotation_id = " + str(annotation_id) + " "
                               "AND dbentity_id = " + str(dbentity_id) + " "
                               "AND display_name = '" + old_display_name + "' "
                               "AND relative_start_index = " + str(old_start_index) + " "
                               "AND relative_end_index = " + str(old_stop_index))
            print("Updating subfeature coords for " + gene)
        except Exception as e:
            print("An error occurred when updating subfeature coords for " + gene + ". ERROR=" + str(e))


        
if __name__ == '__main__':

    fix_intron_coords()
