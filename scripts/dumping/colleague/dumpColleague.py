"""
Dump SGD colleague data to a single JSON file for loading into the ABC
(agr_literature_service) literature database.

Captures everything the ABC loader needs in one self-contained file:
  * nex.colleague                      -> one record per colleague
  * nex.colleague_url                  -> research_summary_urls / lab_urls (embedded)
  * nex.colleague_keyword + keyword    -> keywords (embedded)
  * nex.colleague_relation 'Head of Lab' -> lab_relations (PI <-> member edges)
Counts of the data that has no ABC target (Associate relations, colleague_locus)
are recorded in the metadata block so the loader can report them without
re-querying SGD.

Companion loader (reads the JSON written here, via its --datafile argument):
  agr_literature_service/lit_processing/oneoff_scripts/load_sgd_colleagues.py

Usage:
  set -a; source .env_cc; set +a            # provides NEX2_URI
  python scripts/dumping/colleague/dumpColleague.py
  python scripts/dumping/colleague/dumpColleague.py --outfile /tmp/colleague.json
"""
import argparse
import json
from os import makedirs, path

from sqlalchemy import text

from scripts.loading.database_session import get_session

__author__ = 'sweng66'

DEFAULT_OUTFILE = "scripts/dumping/colleague/data/colleague.json"

COLLEAGUE_SQL = """
    SELECT colleague_id, display_name, obj_url, orcid,
           first_name, middle_name, last_name, other_last_name, suffix,
           job_title, institution,
           address1, address2, address3, city, state, country, postal_code,
           email, display_email, research_interest, colleague_note
    FROM nex.colleague
    ORDER BY colleague_id
"""

URL_SQL = """
    SELECT colleague_id, url_type, obj_url
    FROM nex.colleague_url
    WHERE coalesce(trim(obj_url), '') <> ''
    ORDER BY colleague_id, url_id
"""

KEYWORD_SQL = """
    SELECT ck.colleague_id, k.display_name
    FROM nex.colleague_keyword ck
    JOIN nex.keyword k ON ck.keyword_id = k.keyword_id
    ORDER BY ck.colleague_id
"""

RELATION_SQL = """
    SELECT colleague_id AS member_id, associate_id AS pi_id
    FROM nex.colleague_relation
    WHERE association_type = 'Head of Lab'
"""


def dump_data(outfile):
    nex_session = get_session()
    try:
        colleagues = {}
        for row in nex_session.execute(text(COLLEAGUE_SQL)).mappings():
            col = dict(row)
            col["research_summary_urls"] = []
            col["lab_urls"] = []
            col["keywords"] = []
            colleagues[col["colleague_id"]] = col

        for row in nex_session.execute(text(URL_SQL)).mappings():
            cid = row["colleague_id"]
            if cid not in colleagues:
                continue
            key = ("research_summary_urls"
                   if row["url_type"] == "Research summary" else "lab_urls")
            colleagues[cid][key].append(row["obj_url"].strip())

        for row in nex_session.execute(text(KEYWORD_SQL)).mappings():
            cid = row["colleague_id"]
            keyword = (row["display_name"] or "").strip()
            if cid in colleagues and keyword:
                colleagues[cid]["keywords"].append(keyword)

        lab_relations = [
            {"pi_colleague_id": row["pi_id"],
             "member_colleague_id": row["member_id"]}
            for row in nex_session.execute(text(RELATION_SQL)).mappings()
        ]

        associate_count = nex_session.execute(text(
            "SELECT count(*) FROM nex.colleague_relation "
            "WHERE association_type = 'Associate'"
        )).scalar()
        locus_count = nex_session.execute(text(
            "SELECT count(*) FROM nex.colleague_locus"
        )).scalar()
    finally:
        nex_session.close()

    payload = {
        "metadata": {
            "source": "SGD nex.colleague",
            "colleague_count": len(colleagues),
            "head_of_lab_pairs": len(lab_relations),
            "skipped_associate_relations": associate_count,
            "skipped_colleague_locus": locus_count,
        },
        "colleagues": list(colleagues.values()),
        "lab_relations": lab_relations,
    }

    outdir = path.dirname(outfile)
    if outdir:
        makedirs(outdir, exist_ok=True)
    with open(outfile, "w") as fw:
        # default=str guards against any unexpected non-JSON types
        json.dump(payload, fw, indent=2, default=str)

    print("Wrote {} colleagues, {} Head-of-Lab relations -> {}".format(
        len(colleagues), len(lab_relations), outfile))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outfile", default=DEFAULT_OUTFILE,
                        help="output JSON path (default: %(default)s)")
    args = parser.parse_args()
    dump_data(args.outfile)


if __name__ == '__main__':
    main()
