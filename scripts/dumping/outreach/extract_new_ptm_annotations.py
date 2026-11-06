"""List the (paper, gene) pairs behind post-translational modification (PTM)
annotations added since a date.

First step of the weekly PTM outreach pipeline
(ptm_weekly_email_pipeline.sh). Reads the SGD database directly
(NEX2_URI), because "added since the last email" needs
nex.posttranslationannotation's date_created. Each annotation is one modified
site (residue, position, PSI-MOD term) of the gene's protein.

Rules (per SGD curators, Nov 2026):
- only annotations with date_created >= --since
- only papers with a PMID (the PMID itself may be from any year)
- only active genes and references, so every link in the email resolves

Output, one row per (pmid, gene), sorted by pmid then gene:
    pmid  gene_sgdid  gene_symbol  systematic_name  annotation_date
    annotation_count  paper_annotation_count
annotation_date is the earliest date_created of the gene's annotations on
the paper in the window; annotation_count is how many of them there are;
paper_annotation_count is how many annotations the paper has there.
"""
import argparse
import os

from sqlalchemy import create_engine, text

DEFAULT_SINCE = "2026-01-01"
DEFAULT_OUTPUT_FILE = "sgd_ptm_new_annotations.tsv"

COLUMNS = ["pmid", "gene_sgdid", "gene_symbol", "systematic_name",
           "annotation_date", "annotation_count", "paper_annotation_count"]

QUERY = text("""
    WITH new_annotations AS (
        SELECT pa.annotation_id, r.pmid, pa.dbentity_id, pa.date_created
        FROM nex.posttranslationannotation pa
        JOIN nex.referencedbentity r ON r.dbentity_id = pa.reference_id
        JOIN nex.dbentity rd ON rd.dbentity_id = pa.reference_id
        JOIN nex.dbentity gd ON gd.dbentity_id = pa.dbentity_id
        WHERE pa.date_created >= :since
          AND r.pmid IS NOT NULL
          AND rd.dbentity_status = 'Active'
          AND gd.dbentity_status = 'Active'
    ),
    paper_counts AS (
        SELECT pmid, COUNT(*) AS paper_annotation_count
        FROM new_annotations
        GROUP BY pmid
    )
    SELECT a.pmid,
           d.sgdid,
           COALESCE(NULLIF(l.gene_name, ''), l.systematic_name),
           l.systematic_name,
           MIN(a.date_created)::date,
           COUNT(*),
           p.paper_annotation_count
    FROM new_annotations a
    JOIN nex.locusdbentity l ON l.dbentity_id = a.dbentity_id
    JOIN nex.dbentity d ON d.dbentity_id = a.dbentity_id
    JOIN paper_counts p ON p.pmid = a.pmid
    GROUP BY a.pmid, d.sgdid, l.gene_name, l.systematic_name, p.paper_annotation_count
    ORDER BY a.pmid, 3
""")


def extract(since, output_file):

    engine = create_engine(os.environ["NEX2_URI"])
    with engine.connect() as connection:
        rows = connection.execute(QUERY, {"since": since}).fetchall()

    with open(output_file, "w") as fw:
        fw.write("\t".join(COLUMNS) + "\n")
        for row in rows:
            fw.write("\t".join(str(value) for value in row) + "\n")

    annotations_by_paper = {row[0]: row[6] for row in rows}
    print(str(sum(annotations_by_paper.values())) + " PTM annotations since " + since +
          " on " + str(len(annotations_by_paper)) + " papers with a PMID (" + str(len(rows)) +
          " paper-gene pairs) -> " + output_file)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="List (pmid, gene) pairs of PTM annotations added since a date")
    parser.add_argument("-s", "--since", default=DEFAULT_SINCE,
                        help="only annotations with date_created >= this "
                             "(default: " + DEFAULT_SINCE + ")")
    parser.add_argument("-o", "--output-file", default=DEFAULT_OUTPUT_FILE,
                        help="output tsv (default: " + DEFAULT_OUTPUT_FILE + ")")
    args = parser.parse_args()

    extract(args.since, args.output_file)
