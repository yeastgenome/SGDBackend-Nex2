"""List the (paper, gene) pairs behind regulation annotations added since a date.

First step of the weekly regulation outreach pipeline
(regulation_weekly_email_pipeline.sh). Reads the SGD database directly
(NEX2_URI), because "added since the last email" needs
nex.regulationannotation's date_created.

A regulation annotation links a regulator gene to a target gene, so both
genes of every annotation are listed (role says which; a gene that is a
regulator in one annotation and a target in another is 'regulator,target').

Rules (per SGD curators, Oct 2026):
- only annotations with date_created >= --since
- only papers with a PMID (the PMID itself may be from any year)
- only active genes and references, so every link in the email resolves

Output, one row per (pmid, gene), sorted by pmid then gene:
    pmid  gene_sgdid  gene_symbol  systematic_name  role  annotation_date
    annotation_count  paper_annotation_count
annotation_date is the earliest date_created of the gene's annotations on
the paper in the window; annotation_count is how many of them the gene is
in; paper_annotation_count is how many annotations the paper has there
(an annotation counts once even though it names two genes).
"""
import argparse
import os

from sqlalchemy import create_engine, text

DEFAULT_SINCE = "2026-01-01"
DEFAULT_OUTPUT_FILE = "sgd_regulation_new_annotations.tsv"

COLUMNS = ["pmid", "gene_sgdid", "gene_symbol", "systematic_name", "role",
           "annotation_date", "annotation_count", "paper_annotation_count"]

QUERY = text("""
    WITH new_annotations AS (
        SELECT ra.annotation_id, r.pmid, ra.regulator_id, ra.target_id, ra.date_created
        FROM nex.regulationannotation ra
        JOIN nex.referencedbentity r ON r.dbentity_id = ra.reference_id
        JOIN nex.dbentity rd ON rd.dbentity_id = ra.reference_id
        JOIN nex.dbentity reg ON reg.dbentity_id = ra.regulator_id
        JOIN nex.dbentity tgt ON tgt.dbentity_id = ra.target_id
        WHERE ra.date_created >= :since
          AND r.pmid IS NOT NULL
          AND rd.dbentity_status = 'Active'
          AND reg.dbentity_status = 'Active'
          AND tgt.dbentity_status = 'Active'
    ),
    gene_roles AS (
        SELECT annotation_id, pmid, regulator_id AS gene_id, 'regulator' AS role, date_created
        FROM new_annotations
        UNION ALL
        SELECT annotation_id, pmid, target_id, 'target', date_created
        FROM new_annotations
    ),
    paper_counts AS (
        SELECT pmid, COUNT(*) AS paper_annotation_count
        FROM new_annotations
        GROUP BY pmid
    )
    SELECT g.pmid,
           d.sgdid,
           COALESCE(NULLIF(l.gene_name, ''), l.systematic_name),
           l.systematic_name,
           STRING_AGG(DISTINCT g.role, ',' ORDER BY g.role),
           MIN(g.date_created)::date,
           COUNT(DISTINCT g.annotation_id),
           p.paper_annotation_count
    FROM gene_roles g
    JOIN nex.locusdbentity l ON l.dbentity_id = g.gene_id
    JOIN nex.dbentity d ON d.dbentity_id = g.gene_id
    JOIN paper_counts p ON p.pmid = g.pmid
    GROUP BY g.pmid, d.sgdid, l.gene_name, l.systematic_name, p.paper_annotation_count
    ORDER BY g.pmid, 3
""")


def extract(since, output_file):

    engine = create_engine(os.environ["NEX2_URI"])
    with engine.connect() as connection:
        rows = connection.execute(QUERY, {"since": since}).fetchall()

    with open(output_file, "w") as fw:
        fw.write("\t".join(COLUMNS) + "\n")
        for row in rows:
            fw.write("\t".join(str(value) for value in row) + "\n")

    annotations_by_paper = {row[0]: row[7] for row in rows}
    print(str(sum(annotations_by_paper.values())) + " regulation annotations since " + since +
          " on " + str(len(annotations_by_paper)) + " papers with a PMID (" + str(len(rows)) +
          " paper-gene pairs) -> " + output_file)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="List (pmid, gene) pairs of regulation annotations added since a date")
    parser.add_argument("-s", "--since", default=DEFAULT_SINCE,
                        help="only annotations with date_created >= this "
                             "(default: " + DEFAULT_SINCE + ")")
    parser.add_argument("-o", "--output-file", default=DEFAULT_OUTPUT_FILE,
                        help="output tsv (default: " + DEFAULT_OUTPUT_FILE + ")")
    args = parser.parse_args()

    extract(args.since, args.output_file)
