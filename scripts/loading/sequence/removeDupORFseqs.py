import os
from datetime import datetime
import sys
from src.models import Locusdbentity, Taxonomy, Dnasequenceannotation, \
     Dnasubsequence, Proteinsequenceannotation
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

datafile = "scripts/loading/sequence/data/dupORFsOtherStrainsFixed060323.tsv"
logfile = "scripts/loading/sequence/logs/removeDupORFseqs.log"


def remove_seq_rows():

    db_session = get_session()

    # so_to_id = dict([(x.display_name, x.so_id) for x in nex_session.query(So).all()])
    
    f = open(datafile)
    fw = open(logfile, "w")

    i = 0
    for line in f:
        if line.startswith('taxonomy_id'):
            continue
        i += 1
        if i % 100 == 0:
            # db_session.rollback()
            db_session.commit()
        pieces = line.strip().split("\t")
        taxonomy_id = int(pieces[0])
        dbentity_id = int(pieces[2])
        systematic_name = pieces[3]
        annotation_ids = pieces[5:]
        for annotation_id in annotation_ids:
            annotation_id = int(annotation_id)
            print(taxonomy_id, dbentity_id, systematic_name, annotation_id)

            # no protein data for these features since we only store protein sequences
            # for the genes that are in reference S288C or in one of the alternative strains

            # check if there is anything in dnasubsequence table using annotation_id
            rows = db_session.execute(f"SELECT download_filename "
                                      f"FROM nex.dnasubsequence "
                                      f"WHERE annotation_id = {annotation_id}").fetchall()
            for x in rows:
                print(x[0])


            if len(rows) > 0:
                db_session.execute(f"DELETE FROM nex.dnasubsequence "
                                   f"WHERE annotation_id = {annotation_id}")
            
                fw.write("DELETE FROM nex.dnasubsequence WHERE annotation_id = " + str(annotation_id) + "\n")
            
            
            # check the genomic seq from dnasequenceannotation table by using annotation_id 
            row = db_session.execute(f"SELECT download_filename, so_id, start_index, end_index, contig_id "
                                     f"FROM nex.dnasequenceannotation "
                                     f"WHERE annotation_id = {annotation_id}").first()
            if row is None:
                print("annotation_id=", annotation_id, "is not in the database for line:", line)
                continue
            so_id = int(row[1])
            start_index = int(row[2])
            end_index = int(row[3])
            contig_id = int(row[4])
            filename = row[0]
            print(f"filename={filename} so_id={so_id} taxonomy_id={taxonomy_id} start_index={start_index} end_index={end_index}")



            
            db_session.execute(f"DELETE FROM nex.dnasequenceannotation "
                               f"WHERE annotation_id = {annotation_id}") 

            fw.write("DELETE FROM nex.dnasequenceannotation WHERE annotation_id =" +  str(annotation_id) + "\n")
            
            
            # check to get the corresponding 1KB rows and delete them
            annotation_id_for_1kb = annotation_id + 1
            row = db_session.execute(f"SELECT annotation_id, download_filename, start_index, end_index "
                                     f"FROM nex.dnasequenceannotation "
                                     f"WHERE taxonomy_id = {taxonomy_id} "
                                     f"AND dbentity_id = {dbentity_id} "
                                     f"AND so_id = {so_id} "
                                     f"AND contig_id = {contig_id} "
                                     f"AND dna_type = '1KB' "
                                     f"AND annotation_id = {annotation_id_for_1kb}").first()
            
            if row is None:
                print(f"BAD: not found 1KB for taxonomy_id = {taxonomy_id} dbentity_id = {dbentity_id} so_id = {so_id}")
                continue
            elif int(row[2]) != start_index - 1000 and int(row[3]) != end_index + 1000:
                contig_length = get_contig_length(db_session, contig_id)
                if row[3] == contig_length:
                    print("GOOD!: short contig:", start_index, "to", end_index, "1KB:", row[2], "to", row[3])
                else:
                    print("BAD coords?:", start_index, "to", end_index, "1KB:", row[2], "to", row[3], "contig_length=", contig_length)
                    continue
            else:
                print("GOOD!:", row[1], row[0], row[2], row[3])



                
            db_session.execute(f"DELETE FROM nex.dnasequenceannotation "
                               f"WHERE annotation_id = {annotation_id_for_1kb}")

            fw.write("DELETE FROM nex.dnasequenceannotation WHERE annotation_id =" +  str(annotation_id_for_1kb) + "\n")
            
            
    # db_session.rollback()
    db_session.commit()
    f.close()
    fw.close()


def get_contig_length(db_session, contig_id):

    row = db_session.execute(f"SELECT residues from nex.contig WHERE contig_id = {contig_id}").first()
    return len(row[0])

    
if __name__ == '__main__':

    remove_seq_rows()
