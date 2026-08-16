"""Map author email addresses to the phenotype annotations of their papers,
for outreach emails to authors whose publications produced new annotations.

Input: a tab-delimited email file with a header line and columns
    reference_curie  pmid  source  email  has_email_in_abc
as produced by the ABC's retrieve_emails_from_pubmed_pmc.py (one row per
paper/source/email; extra columns are ignored).

Annotation source: phenotype_data.tab from sgd-archive, regenerated weekly by
scripts/dumping/tab_files_for_download_site/generate_phenotype_file.py. Its
column 5 carries the reference as 'SGD_REF:<sgdid>|PMID:<pmid>', which is
joined against the email file's PMIDs.

Output: one row per (email, phenotype annotation row) for every PMID present
in both inputs -- the email/ABC columns first, then the phenotype file's own
columns (minus its reference column, folded into the pmid):
    email  pmid  reference_curie  has_email_in_abc  email_source
    feature_name  feature_type  gene_name  sgdid  experiment_type
    mutant_type  allele  strain_background  phenotype  chemical  condition
    details  reporter
"""
import argparse
import urllib.request
from collections import defaultdict
from os import makedirs, path

PHENOTYPE_URL = "http://sgd-archive.yeastgenome.org/curation/literature/phenotype_data.tab"

DEFAULT_EMAIL_FILE = "sgd_emails_from_pubmed_pmc.tsv"
DEFAULT_OUTPUT_FILE = "sgd_email_pmid_phenotype_annotations.tsv"
DEFAULT_DATA_DIR = "scripts/dumping/outreach/data"

## phenotype_data.tab columns (no header line; see phenotype_data.README)
PHENOTYPE_COLUMNS = ["feature_name", "feature_type", "gene_name", "sgdid",
                     "reference", "experiment_type", "mutant_type", "allele",
                     "strain_background", "phenotype", "chemical", "condition",
                     "details", "reporter"]
REFERENCE_COLUMN = PHENOTYPE_COLUMNS.index("reference")


def download(url, data_dir, filename):
    makedirs(data_dir, exist_ok=True)
    out = path.join(data_dir, filename)
    if path.exists(out) and path.getsize(out) > 0:
        print("already downloaded: " + out)
        return out
    print("downloading " + url)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; SGD-loader/1.0)", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(out, "wb") as fw:
        while True:
            chunk = resp.read(1024 * 64)
            if not chunk:
                break
            fw.write(chunk)
    print("  -> " + str(path.getsize(out)) + " bytes")
    return out


def read_emails_by_pmid(email_file):
    """pmid -> {email: [reference_curie, has_email_in_abc, set(sources)]}"""
    emails_by_pmid = defaultdict(dict)
    with open(email_file) as f:
        f.readline()
        for line in f:
            pieces = line.rstrip("\n").split("\t")
            if len(pieces) < 5:
                continue
            (curie, pmid, source, email, has_abc) = pieces[:5]
            entry = emails_by_pmid[pmid].setdefault(email, [curie, has_abc, set()])
            entry[2].add(source)
    return emails_by_pmid


def dump_data(email_file, output_file, data_dir):

    emails_by_pmid = read_emails_by_pmid(email_file)
    print(str(sum(len(v) for v in emails_by_pmid.values())) +
          " distinct (pmid, email) pairs on " + str(len(emails_by_pmid)) + " papers")

    phenotype_file = download(PHENOTYPE_URL, data_dir, "phenotype_data.tab")

    rows = []
    annotated_pmids = set()
    with open(phenotype_file) as f:
        for line in f:
            fields = line.rstrip("\n").split("\t")
            if len(fields) != len(PHENOTYPE_COLUMNS):
                continue
            reference = fields[REFERENCE_COLUMN]
            pmid = ""
            for piece in reference.split("|"):
                if piece.startswith("PMID:"):
                    pmid = piece[5:]
                    break
            if not pmid or pmid not in emails_by_pmid:
                continue
            annotated_pmids.add(pmid)
            annotation = fields[:REFERENCE_COLUMN] + fields[REFERENCE_COLUMN + 1:]
            for email, (curie, has_abc, sources) in sorted(emails_by_pmid[pmid].items()):
                rows.append([email, pmid, curie, has_abc,
                             "|".join(sorted(sources))] + annotation)

    rows.sort()
    header = (["email", "pmid", "reference_curie", "has_email_in_abc", "email_source"] +
              [c for c in PHENOTYPE_COLUMNS if c != "reference"])
    fw = open(output_file, "w")
    fw.write("\t".join(header) + "\n")
    for row in rows:
        fw.write("\t".join(row) + "\n")
    fw.close()

    pairs = set([(r[0], r[1]) for r in rows])
    print("email papers with phenotype annotations: " +
          str(len(annotated_pmids)) + "/" + str(len(emails_by_pmid)))
    print("(email, pmid) pairs mapped: " + str(len(pairs)))
    print("rows written: " + str(len(rows)) + " -> " + output_file)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Map author emails to the phenotype annotations of their papers "
                    "(from phenotype_data.tab), for outreach")
    parser.add_argument("-e", "--email-file", default=DEFAULT_EMAIL_FILE,
                        help="email tsv from retrieve_emails_from_pubmed_pmc.py "
                             "(default: " + DEFAULT_EMAIL_FILE + ")")
    parser.add_argument("-o", "--output-file", default=DEFAULT_OUTPUT_FILE,
                        help="output tsv (default: " + DEFAULT_OUTPUT_FILE + ")")
    parser.add_argument("-d", "--data-dir", default=DEFAULT_DATA_DIR,
                        help="directory for the downloaded phenotype_data.tab; "
                             "delete the file to force a fresh weekly copy "
                             "(default: " + DEFAULT_DATA_DIR + ")")
    args = parser.parse_args()

    dump_data(args.email_file, args.output_file, args.data_dir)
