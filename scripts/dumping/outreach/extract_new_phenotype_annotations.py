"""List the (paper, gene) pairs behind phenotype annotations added since a date.

First step of the weekly phenotype outreach pipeline
(phenotype_weekly_email_pipeline.sh). Reads the SGD database directly
(NEX2_URI), because the public phenotype_data.tab carries no annotation
dates and "added since the last email" needs nex.phenotypeannotation's
date_created.

Rules (per SGD curators, Oct 2026):
- only annotations with date_created >= --since
- only papers with a PMID (the PMID itself may be from any year)
- only active genes and references, so every link in the email resolves

Output, one row per (pmid, gene), sorted by pmid then gene:
    pmid  gene_sgdid  gene_symbol  systematic_name  annotation_date  annotation_count
annotation_date is the earliest date_created of the pair's annotations in
the window; annotation_count is how many annotations the pair has there.
"""
import argparse
import os

from sqlalchemy import create_engine, text

DEFAULT_SINCE = "2026-01-01"
DEFAULT_OUTPUT_FILE = "sgd_phenotype_new_annotations.tsv"

COLUMNS = ["pmid", "gene_sgdid", "gene_symbol", "systematic_name",
           "annotation_date", "annotation_count"]

QUERY = text("""
    SELECT r.pmid,
           d.sgdid,
           COALESCE(NULLIF(l.gene_name, ''), l.systematic_name),
           l.systematic_name,
           MIN(pa.date_created)::date,
           COUNT(*)
    FROM nex.phenotypeannotation pa
    JOIN nex.referencedbentity r ON r.dbentity_id = pa.reference_id
    JOIN nex.dbentity rd ON rd.dbentity_id = pa.reference_id
    JOIN nex.locusdbentity l ON l.dbentity_id = pa.dbentity_id
    JOIN nex.dbentity d ON d.dbentity_id = pa.dbentity_id
    WHERE pa.date_created >= :since
      AND r.pmid IS NOT NULL
      AND d.dbentity_status = 'Active'
      AND rd.dbentity_status = 'Active'
    GROUP BY r.pmid, d.sgdid, l.gene_name, l.systematic_name
    ORDER BY r.pmid, 3
""")


def extract(since, output_file):

    engine = create_engine(os.environ["NEX2_URI"])
    with engine.connect() as connection:
        rows = connection.execute(QUERY, {"since": since}).fetchall()

    with open(output_file, "w") as fw:
        fw.write("\t".join(COLUMNS) + "\n")
        for row in rows:
            fw.write("\t".join(str(value) for value in row) + "\n")

    papers = {row[0] for row in rows}
    annotations = sum(row[5] for row in rows)
    print(str(annotations) + " phenotype annotations since " + since + " on " +
          str(len(papers)) + " papers with a PMID (" + str(len(rows)) +
          " paper-gene pairs) -> " + output_file)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="List (pmid, gene) pairs of phenotype annotations added since a date")
    parser.add_argument("-s", "--since", default=DEFAULT_SINCE,
                        help="only annotations with date_created >= this "
                             "(default: " + DEFAULT_SINCE + ")")
    parser.add_argument("-o", "--output-file", default=DEFAULT_OUTPUT_FILE,
                        help="output tsv (default: " + DEFAULT_OUTPUT_FILE + ")")
    args = parser.parse_args()

    extract(args.since, args.output_file)
