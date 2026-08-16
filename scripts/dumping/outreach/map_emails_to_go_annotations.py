"""Map author email addresses to the GO annotations of their papers, for
GO-outreach emails to authors whose publications produced new annotations.

Input: a tab-delimited email file with a header line and columns
    reference_curie  pmid  source  email  has_email_in_abc
as produced by the ABC's retrieve_emails_from_pubmed_pmc.py (one row per
paper/source/email; extra columns are ignored).

Annotation source: YEAST-mod.gpad.gz from current.geneontology.org -- the
same file scripts/loading/go/load_gpad.py loads. The old separate
noctua_sgd.gpad no longer exists; GO-CAM/noctua annotations are folded into
this file and identified by a noctua-model-id property (column 12). A model
id of the form gomodel:SGD_<sgdid> is the gene's own gene-centric model
(routine curation); a hex id (e.g. gomodel:5fce9b7300001215) is a hand-built
GO-CAM pathway model worth showcasing in an outreach email; a blank means the
annotation is third-party assigned (IntAct, UniProt, ...), not SGD-curated.

Output: one row per (email, GO annotation) for every PMID present in both
inputs, with gene symbol (from YEAST-mod.gpi.gz) and GO term name/aspect
(from go-basic.obo) resolved:
    email  pmid  reference_curie  has_email_in_abc  email_source  gene_sgdid
    gene_symbol  qualifier  go_id  go_term  go_aspect  go_evidence
    assigned_by  annotation_date  gocam_model
"""
import argparse
import gzip
import re
import urllib.request
from collections import defaultdict
from os import makedirs, path

GPAD_URL = "http://current.geneontology.org/annotations/gpad/YEAST-mod.gpad.gz"
GPI_URL = "http://current.geneontology.org/annotations/gpi/YEAST-mod.gpi.gz"
OBO_URL = "http://purl.obolibrary.org/obo/go/go-basic.obo"

DEFAULT_EMAIL_FILE = "sgd_emails_from_pubmed_pmc.tsv"
DEFAULT_OUTPUT_FILE = "sgd_email_pmid_go_annotations.tsv"
DEFAULT_DATA_DIR = "scripts/dumping/outreach/data"

# GPAD 2.0 relation (col 3) -> GO qualifier label
RO_TO_QUALIFIER = {
    "RO:0002327": "enables",
    "RO:0002331": "involved in",
    "RO:0001025": "located in",
    "RO:0002432": "is active in",
    "RO:0002325": "colocalizes with",
    "RO:0002326": "contributes to",
    "RO:0002263": "acts upstream of",
    "RO:0002264": "acts upstream of or within",
    "RO:0004032": "acts upstream of or within, positive effect",
    "RO:0004033": "acts upstream of or within, negative effect",
    "RO:0004034": "acts upstream of, positive effect",
    "RO:0004035": "acts upstream of, negative effect",
    "BFO:0000050": "part of",
}

ASPECT = {"biological_process": "P", "molecular_function": "F",
          "cellular_component": "C"}


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


def open_maybe_gz(filename):
    return gzip.open(filename, "rt") if filename.endswith(".gz") else open(filename)


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


def read_gene_symbols(gpi_file):
    """SGD:<sgdid> -> gene symbol, from the GPI (col 1 id, col 2 symbol)."""
    sgdid_to_symbol = {}
    with open_maybe_gz(gpi_file) as f:
        for line in f:
            if line.startswith("!"):
                continue
            field = line.rstrip("\n").split("\t")
            if len(field) >= 2 and field[0].startswith("SGD:"):
                sgdid_to_symbol.setdefault(field[0], field[1])
    return sgdid_to_symbol


def read_go_terms(obo_file):
    """GO id -> (term name, aspect P/F/C), from go-basic.obo."""
    go_name = {}
    go_aspect = {}
    term_id = None
    with open(obo_file) as f:
        for line in f:
            line = line.rstrip("\n")
            if line == "[Term]":
                term_id = None
            elif line.startswith("id: GO:"):
                term_id = line[4:]
            elif term_id and line.startswith("name: "):
                go_name[term_id] = line[6:]
            elif term_id and line.startswith("namespace: "):
                go_aspect[term_id] = ASPECT.get(line[11:], "")
    return (go_name, go_aspect)


def dump_data(email_file, output_file, data_dir):

    emails_by_pmid = read_emails_by_pmid(email_file)
    print(str(sum(len(v) for v in emails_by_pmid.values())) +
          " distinct (pmid, email) pairs on " + str(len(emails_by_pmid)) + " papers")

    sgdid_to_symbol = read_gene_symbols(download(GPI_URL, data_dir, "YEAST-mod.gpi.gz"))
    (go_name, go_aspect) = read_go_terms(download(OBO_URL, data_dir, "go-basic.obo"))
    gpad_file = download(GPAD_URL, data_dir, "YEAST-mod.gpad.gz")

    gocam_re = re.compile(r"noctua-model-id=([^|]+)")
    evidence_re = re.compile(r"comment=go_evidence:([A-Z]+)")

    rows = []
    annotated_pmids = set()
    seen_lines = set()
    with open_maybe_gz(gpad_file) as f:
        for line in f:
            if line.startswith("!") or line in seen_lines:
                continue
            seen_lines.add(line)
            field = line.rstrip("\n").split("\t")
            if len(field) < 12 or not field[0].startswith("SGD:"):
                continue
            reference = field[4]
            if not reference.startswith("PMID:"):
                continue
            pmid = reference.split(":")[1]
            if pmid not in emails_by_pmid:
                continue
            annotated_pmids.add(pmid)
            qualifier = RO_TO_QUALIFIER.get(field[2], field[2])
            if field[1].strip() == "NOT":
                qualifier = "NOT|" + qualifier
            goid = field[3]
            evidence_m = evidence_re.search(field[11])
            gocam_m = gocam_re.search(field[11])
            for email, (curie, has_abc, sources) in sorted(emails_by_pmid[pmid].items()):
                rows.append((email, pmid, curie, has_abc,
                             "|".join(sorted(sources)),
                             field[0], sgdid_to_symbol.get(field[0], ""),
                             qualifier, goid, go_name.get(goid, ""),
                             go_aspect.get(goid, ""),
                             evidence_m.group(1) if evidence_m else "",
                             field[9], field[8],
                             gocam_m.group(1).strip() if gocam_m else ""))

    ## GPAD lines can differ only in columns not carried into the output
    ## (with/from, annotation extensions) -- collapse those to one row.
    rows = sorted(set(rows))

    fw = open(output_file, "w")
    fw.write("email\tpmid\treference_curie\thas_email_in_abc\temail_source\t"
             "gene_sgdid\tgene_symbol\tqualifier\tgo_id\tgo_term\tgo_aspect\t"
             "go_evidence\tassigned_by\tannotation_date\tgocam_model\n")
    for row in rows:
        fw.write("\t".join(row) + "\n")
    fw.close()

    pairs = set([(r[0], r[1]) for r in rows])
    gocam_rows = sum(1 for r in rows if r[14])
    print("email papers with GO annotations: " +
          str(len(annotated_pmids)) + "/" + str(len(emails_by_pmid)))
    print("(email, pmid) pairs mapped: " + str(len(pairs)))
    print("rows written: " + str(len(rows)) + " (" + str(gocam_rows) +
          " from GO-CAM/noctua models) -> " + output_file)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Map author emails to the GO annotations of their papers "
                    "(from YEAST-mod.gpad), for GO outreach")
    parser.add_argument("-e", "--email-file", default=DEFAULT_EMAIL_FILE,
                        help="email tsv from retrieve_emails_from_pubmed_pmc.py "
                             "(default: " + DEFAULT_EMAIL_FILE + ")")
    parser.add_argument("-o", "--output-file", default=DEFAULT_OUTPUT_FILE,
                        help="output tsv (default: " + DEFAULT_OUTPUT_FILE + ")")
    parser.add_argument("-d", "--data-dir", default=DEFAULT_DATA_DIR,
                        help="directory for the downloaded GPAD/GPI/OBO files; "
                             "delete its files to force a fresh download "
                             "(default: " + DEFAULT_DATA_DIR + ")")
    args = parser.parse_args()

    dump_data(args.email_file, args.output_file, args.data_dir)
