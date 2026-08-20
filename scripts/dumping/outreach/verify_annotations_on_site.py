"""Keep only outreach rows whose GO annotation is actually live on the SGD site.

The outreach pipeline derives its annotations from YEAST-mod.gpad (the GO
release file), but load_gpad.py can legitimately skip GPAD rows (unknown
gene, obsolete GO term, filtering rules) — and the outreach email links the
author straight to the paper page and the gene's GO tab. This step checks
each (pmid, gene) pair against the public SGD backend API
(/backend/reference/<pmid>/go_details, one call per paper) and drops rows
the site does not show, so an email is only ever sent for annotations an
author can really see. No database credentials needed.

Failure mode is conservative: a paper whose API lookup fails (404 or
repeated errors) has ALL its rows dropped; the sent-log dedupe means the
pair is simply retried on the next pipeline run.

Input/output: the gene-centric TSV format of map_emails_to_go_annotations.py
(pmid and gene_sgdid columns are used for the check).
"""
import argparse
import http.client
import json
import sys
import time
import urllib.error
import urllib.request

BACKEND_URL = "https://www.yeastgenome.org/backend"
REQUEST_RETRIES = 3
RETRY_BACKOFF_SECONDS = 10
REQUEST_INTERVAL = 0.2


def fetch_go_details(backend_url, pmid):
    """Return the list of GO annotations SGD shows for this paper, or None
    when the paper itself is unknown to the site (404) or unreachable."""
    url = backend_url + "/reference/" + pmid + "/go_details"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            print("WARNING: " + url + " HTTP " + str(e.code) +
                  " attempt " + str(attempt) + "/" + str(REQUEST_RETRIES))
        except (urllib.error.URLError, http.client.HTTPException,
                json.JSONDecodeError, OSError) as e:
            print("WARNING: " + url + " attempt " + str(attempt) + "/" +
                  str(REQUEST_RETRIES) + " failed: " + str(e))
        if attempt < REQUEST_RETRIES:
            time.sleep(RETRY_BACKOFF_SECONDS)
    return None


def annotated_sgdids_by_pmid(backend_url, pmids):
    """pmid -> set of gene sgdids the SGD site shows GO annotations for."""
    sgdids_by_pmid = {}
    for (count, pmid) in enumerate(pmids, 1):
        details = fetch_go_details(backend_url, pmid)
        if details is None:
            print("no go_details on the site for PMID " + pmid +
                  " -- its rows will be dropped")
            continue
        sgdids = set()
        for annotation in details:
            link = (annotation.get("locus") or {}).get("link") or ""
            if link.startswith("/locus/"):
                sgdids.add(link.split("/")[2])
        sgdids_by_pmid[pmid] = sgdids
        if count % 25 == 0:
            print("checked " + str(count) + "/" + str(len(pmids)) + " papers")
        time.sleep(REQUEST_INTERVAL)
    return sgdids_by_pmid


def verify(input_file, output_file, backend_url):

    with open(input_file) as fh:
        header = fh.readline().rstrip("\n").split("\t")
        col = {name: idx for idx, name in enumerate(header)}
        rows = [line.rstrip("\n").split("\t") for line in fh]

    pmids = sorted({row[col["pmid"]] for row in rows if row[col["pmid"]].isdigit()})
    print("verifying " + str(len(rows)) + " rows / " + str(len(pmids)) +
          " papers against " + backend_url)
    sgdids_by_pmid = annotated_sgdids_by_pmid(backend_url, pmids)

    kept = []
    dropped = []
    for row in rows:
        sgdid = row[col["gene_sgdid"]].replace("SGD:", "")
        on_site = sgdid in sgdids_by_pmid.get(row[col["pmid"]], set())
        (kept if on_site else dropped).append(row)

    with open(output_file, "w") as fw:
        fw.write("\t".join(header) + "\n")
        for row in kept:
            fw.write("\t".join(row) + "\n")

    print("site verification: " + str(len(kept)) + "/" + str(len(rows)) +
          " rows confirmed live -> " + output_file)
    if dropped:
        print("dropped " + str(len(dropped)) + " rows not (yet) on the site:")
        for row in dropped:
            print("  pmid " + row[col["pmid"]] + " " + row[col["gene_sgdid"]] +
                  " " + row[col["go_id"]])


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Drop outreach rows whose (pmid, gene) GO annotation the "
                    "SGD site does not show")
    parser.add_argument("-i", "--input", required=True,
                        help="gene-centric TSV from map_emails_to_go_annotations.py")
    parser.add_argument("-o", "--output", required=True,
                        help="filtered TSV (same format, verified rows only)")
    parser.add_argument("--backend-url", default=BACKEND_URL,
                        help="SGD backend API base url (default: " + BACKEND_URL + ")")
    args = parser.parse_args()

    verify(args.input, args.output, args.backend_url)
    sys.exit(0)
