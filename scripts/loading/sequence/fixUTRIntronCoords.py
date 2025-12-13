from scripts.loading.database_session import get_session

__author__ = 'sweng66'


def get_cds_coords(db, annotation_id):

    sql = """
        SELECT contig_start_index, contig_end_index
        FROM nex.dnasubsequence
        WHERE display_name = 'CDS'
          AND annotation_id = :annotation_id
    """
    row = db.execute("SELECT contig_start_index, contig_end_index "
                     "FROM nex.dnasubsequence "
                     "WHERE display_name = 'CDS' "
                     "AND annotation_id = " + str(annotation_id)).fetchall()
    return row


def main():

    db = get_session()
    rows = db.execute("SELECT dnasubsequence_id, annotation_id, relative_start_index, "
                      " relative_end_index, contig_start_index, contig_end_index, download_filename "
                      "FROM nex.dnasubsequence "
                      "WHERE display_name = 'five_prime_UTR_intron' "
                      "AND download_filename NOT LIKE '%W%'").fetchall()

    for x in rows:
        dnasubsequence_id = x[0]
        annotation_id = x[1]
        UTR_relative_start_index = x[2]
        UTR_relative_end_index = x[3]
        OLD_UTR_contig_start_index = x[4]
        OLD_UTR_contig_end_index = x[5]
        download_filename = x[6]
        cds_rows = get_cds_coords(db, annotation_id)
        if len(cds_rows) > 1:
            print("Multiple CDS for ", download_filename)
        else:
            cds_row = cds_rows[0]
            CDS_contig_start_index = cds_row[0]
            CDS_contig_end_index = cds_row[1]
            UTR_contig_start_index = CDS_contig_end_index - UTR_relative_end_index + 1
            UTR_contig_end_index = CDS_contig_end_index - UTR_relative_start_index + 1
            print(download_filename, OLD_UTR_contig_start_index, OLD_UTR_contig_end_index, UTR_contig_start_index, UTR_contig_end_index)
            db.execute("UPDATE nex.dnasubsequence SET contig_start_index = " + str(UTR_contig_start_index) + ", contig_end_index = " + str(UTR_contig_end_index) + " WHERE dnasubsequence_id = " + str(dnasubsequence_id))
            db.commit()

if __name__ == "__main__":
    main()
