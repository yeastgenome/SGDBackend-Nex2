"""Resolve author emails for the papers behind a GO release's annotations.

Reads YEAST-mod.gpad.gz (downloaded to --data-dir if absent), collects the
PMIDs of SGD-assigned gene-centric annotations (noctua-model-id of the form
gomodel:SGD_<sgdid>) with annotation_date >= --since, and resolves author
emails for each PMID, cheapest source first:

  1. ABC (Alliance literature service) reference_email rows via its REST API.
     Works without authentication only from IP-allowlisted hosts (sgd-curate,
     sgd-backend-qa). Tries /reference/PMID:<pmid>/emails directly (needs the
     ABC ref_email branch deployed); until then falls back to resolving the
     PMID through /cross_reference/PMID:<pmid> -> reference_curie.
  2. PubMed efetch: emails in AffiliationInfo strings (recent papers).
  3. PMC full-text JATS XML <corresp> (papers with a PMCID that tier 2
     missed), with a front//contrib-group//email fallback.

Tiers 2 and 3 are a standalone port of the ABC's
retrieve_emails_from_pubmed_pmc.py + extract_emails.py validation (same
EMAIL_RE incl. the sentence-ending-dot guard, same role-account keyword
suppression), so the pipeline accepts the same addresses as the ABC.

Output (input format of map_emails_to_go_annotations.py), one row per
(paper, source), multiple emails joined by ' | ':
    reference_curie  pmid  source(abc|pubmed_metadata|pmc_corresp)  email  has_email_in_abc(Y|N)

Part of the per-GO-release outreach pipeline (go_release_email_pipeline.sh):
resolve_pmid_emails.py -> map_emails_to_go_annotations.py ->
send_go_annotation_emails.py
"""

import argparse
import gzip
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from os import environ, makedirs, path
from xml.etree import ElementTree

GPAD_URL = "http://current.geneontology.org/annotations/gpad/YEAST-mod.gpad.gz"
ABC_API_URL = "https://literature-rest.alliancegenome.org"
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

DEFAULT_SINCE = "2026-01-01"
DEFAULT_OUTPUT_FILE = "sgd_go_release_emails.tsv"
DEFAULT_DATA_DIR = "scripts/dumping/outreach/data"

SOURCE_ABC = "abc"
SOURCE_PUBMED = "pubmed_metadata"
SOURCE_PMC = "pmc_corresp"

NCBI_API_KEY = environ.get("NCBI_API_KEY", "")
REQUEST_TIMEOUT = 300
REQUEST_RETRIES = 3
RETRY_BACKOFF_SECONDS = 10
# NCBI allows 3 requests/s without an API key, 10/s with one.
NCBI_REQUEST_INTERVAL = 0.11 if NCBI_API_KEY else 0.34
ABC_REQUEST_INTERVAL = 0.2

EFETCH_PUBMED_CHUNK = 200
ELINK_CHUNK = 200
# PMC efetch returns the FULL JATS document per article, so keep chunks small.
EFETCH_PMC_CHUNK = 50

# Same acceptance rules as the ABC's extract_emails.py: the trailing guard
# rejects a truncated domain but still accepts a sentence-ending '.' right
# after the address ("... or markg@fhcrc.org.").
EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])"
    r"([A-Za-z0-9][A-Za-z0-9._%+-]{0,63}"
    r"@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,63})"
    r"(?![A-Za-z0-9_%+-])(?!\.[A-Za-z0-9])",
    re.IGNORECASE,
)

BLOCKED_LOCAL_KEYWORDS = {
    "reprint", "reprints", "permission", "permissions", "copyright",
    "editor", "editors", "support", "helpdesk", "help", "contact", "info",
    "admin", "webmaster", "data_request", "datarequest", "noreply",
    "no-reply", "do-not-reply", "postmaster", "mailer-daemon",
    "correspondence", "journal", "journals", "reviewer",
}

_last_ncbi_request_time = 0.0


def normalize_email(raw):
    raw = (raw or "").strip().strip(" \t\r\n<>()[]{}'\"")
    raw = raw.rstrip(".,;:!?)")
    # Elsevier AffiliationInfo style: "... Electronic address: x@y.z."
    raw = re.sub(r"\s*@\s*", "@", raw)
    return raw.lower()


def is_acceptable_email(email):
    if "@" not in email:
        return False
    try:
        email.encode("ascii")
    except UnicodeEncodeError:
        return False
    (local, _at, domain) = email.rpartition("@")
    if not local or "." not in domain:
        return False
    for keyword in BLOCKED_LOCAL_KEYWORDS:
        if keyword in local:
            return False
    # very long local part with no separators is glue-text garbage
    if len(local) > 30 and not any(sep in local for sep in "._-"):
        return False
    return True


def emails_from_text(content):
    emails = []
    for match in EMAIL_RE.finditer(content or ""):
        email = normalize_email(match.group(1))
        if is_acceptable_email(email) and email not in emails:
            emails.append(email)
    return emails


def download(url, data_dir, filename):
    makedirs(data_dir, exist_ok=True)
    out = path.join(data_dir, filename)
    if path.exists(out) and path.getsize(out) > 0:
        print("already downloaded: " + out)
        return out
    print("downloading " + url)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; SGD-loader/1.0)", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp, open(out, "wb") as fw:
        while True:
            chunk = resp.read(1024 * 64)
            if not chunk:
                break
            fw.write(chunk)
    print("  -> " + str(path.getsize(out)) + " bytes")
    return out


def gene_centric_pmids(gpad_file, since):
    """PMIDs of SGD-assigned gene-centric (gomodel:SGD_*) GPAD annotations
    with annotation_date >= since."""
    pmids = set()
    with gzip.open(gpad_file, "rt") as f:
        for line in f:
            if line.startswith("!"):
                continue
            field = line.rstrip("\n").split("\t")
            if len(field) < 12 or not field[0].startswith("SGD:"):
                continue
            if not field[4].startswith("PMID:") or field[9] != "SGD":
                continue
            if field[8] < since:
                continue
            if "noctua-model-id=gomodel:SGD_" not in field[11]:
                continue
            pmids.add(field[4].split(":")[1])
    return sorted(pmids)


def http_get_json(url):
    """GET a JSON resource; returns (status_code, parsed_json_or_None).
    Retries transient failures (dropped chunked reads, timeouts)."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return (resp.status, json.load(resp))
        except urllib.error.HTTPError as e:
            return (e.code, None)
        except (urllib.error.URLError, http.client.HTTPException,
                json.JSONDecodeError, OSError) as e:
            print("WARNING: " + url + " attempt " + str(attempt) + "/" +
                  str(REQUEST_RETRIES) + " failed: " + str(e))
            if attempt < REQUEST_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS)
    return (0, None)


def fetch_abc_emails(pmids, abc_api_url):
    """Tier 1: reference_email rows from the ABC REST API (unauthenticated;
    only works from IP-allowlisted hosts). Returns pmid -> [emails]."""
    emails_by_pmid = {}
    direct_pmid_supported = True
    for (count, pmid) in enumerate(pmids, 1):
        rows = None
        if direct_pmid_supported:
            (code, rows) = http_get_json(abc_api_url + "/reference/PMID:" + pmid + "/emails")
            if code == 404 and rows is None:
                # either the ref is not in ABC or the deployed API predates
                # PMID support on this endpoint; resolve via cross_reference
                # to tell the two apart (and to keep working either way)
                rows = None
        if rows is None:
            (code, xref) = http_get_json(abc_api_url + "/cross_reference/PMID:" + pmid)
            reference_curie = (xref or {}).get("reference_curie")
            if reference_curie:
                (code, rows) = http_get_json(abc_api_url + "/reference/" + reference_curie + "/emails")
        emails = []
        for row in rows or []:
            email = normalize_email(row.get("email_address", ""))
            if is_acceptable_email(email) and email not in emails:
                emails.append(email)
        if emails:
            emails_by_pmid[pmid] = emails
        if count % 50 == 0:
            print("ABC: checked " + str(count) + "/" + str(len(pmids)) +
                  " PMIDs (" + str(len(emails_by_pmid)) + " with emails)")
        time.sleep(ABC_REQUEST_INTERVAL)
    return emails_by_pmid


def eutils_post(endpoint, params, ids):
    """POST an E-utilities request with one id parameter per identifier
    (required for per-id elink results). Throttled and retried with backoff;
    returns None when all attempts fail."""
    global _last_ncbi_request_time
    url = EUTILS_BASE_URL + "/" + endpoint + ".fcgi"
    data = list(params.items())
    if NCBI_API_KEY:
        data.append(("api_key", NCBI_API_KEY))
    data.extend(("id", one_id) for one_id in ids)
    body = urllib.parse.urlencode(data, doseq=False).encode()
    for attempt in range(1, REQUEST_RETRIES + 1):
        wait = NCBI_REQUEST_INTERVAL - (time.monotonic() - _last_ncbi_request_time)
        if wait > 0:
            time.sleep(wait)
        _last_ncbi_request_time = time.monotonic()
        try:
            req = urllib.request.Request(url, data=body)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return resp.read()
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            print("WARNING: " + endpoint + " attempt " + str(attempt) + "/" +
                  str(REQUEST_RETRIES) + " failed (" + str(len(ids)) + " ids): " + str(e))
            if attempt < REQUEST_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    return None


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def fetch_pubmed_emails(pmids):
    """Tier 2: efetch PubMed records and extract emails from AffiliationInfo
    strings. Returns pmid -> [emails] (only PMIDs with at least one email)."""
    emails_by_pmid = {}
    for chunk in chunks(pmids, EFETCH_PUBMED_CHUNK):
        content = eutils_post("efetch", {"db": "pubmed", "retmode": "xml"}, chunk)
        if content is None:
            print("WARNING: skipping a PubMed chunk of " + str(len(chunk)) + " PMIDs")
            continue
        root = ElementTree.fromstring(content)
        for article in root.findall(".//PubmedArticle"):
            # direct child lookup: .//PMID would also match the PMIDs of
            # comments/corrections and erratum links
            pmid = article.findtext("MedlineCitation/PMID") or ""
            affiliations = " ".join(
                aff.text or "" for aff in article.findall(".//AffiliationInfo/Affiliation"))
            emails = emails_from_text(affiliations)
            if pmid and emails:
                emails_by_pmid[pmid] = emails
    return emails_by_pmid


def map_pmids_to_pmcids(pmids):
    """Map PMIDs to PMC ids via elink. Each PMID is sent as its own id
    parameter so NCBI returns one LinkSet per input; filter on the
    pubmed_pmc linkname (pubmed_pmc_refs = citing articles, not the paper)."""
    pmid_to_pmcid = {}
    for chunk in chunks(pmids, ELINK_CHUNK):
        content = eutils_post(
            "elink", {"dbfrom": "pubmed", "db": "pmc", "linkname": "pubmed_pmc"}, chunk)
        if content is None:
            print("WARNING: skipping an elink chunk of " + str(len(chunk)) + " PMIDs")
            continue
        root = ElementTree.fromstring(content)
        for linkset in root.findall(".//LinkSet"):
            pmid = linkset.findtext("IdList/Id")
            pmcid = linkset.findtext(".//LinkSetDb/Link/Id")
            if pmid and pmcid:
                pmid_to_pmcid[pmid] = pmcid
    return pmid_to_pmcid


def fetch_pmc_emails(pmid_to_pmcid):
    """Tier 3: efetch PMC JATS XML and extract emails from front-matter
    <corresp> elements, falling back to <contrib-group>//<email>. Returns
    pmid -> [emails]."""
    emails_by_pmid = {}
    pmcid_to_pmid = {pmcid: pmid for (pmid, pmcid) in pmid_to_pmcid.items()}
    pmcids = sorted(pmid_to_pmcid.values())
    for chunk in chunks(pmcids, EFETCH_PMC_CHUNK):
        content = eutils_post("efetch", {"db": "pmc", "retmode": "xml"}, chunk)
        if content is None:
            print("WARNING: skipping a PMC chunk of " + str(len(chunk)) + " articles")
            continue
        root = ElementTree.fromstring(content)
        for article in root.findall(".//article"):
            ids = {aid.get("pub-id-type"): (aid.text or "").strip()
                   for aid in article.findall("front/article-meta/article-id")}
            pmid = ids.get("pmid") or pmcid_to_pmid.get(ids.get("pmc", ""), "")
            corresp_text = " ".join(
                "".join(corresp.itertext()) for corresp in article.findall("front//corresp"))
            emails = emails_from_text(corresp_text)
            if not emails:
                contrib_text = " ".join(
                    "".join(email_el.itertext())
                    for email_el in article.findall("front//contrib-group//email"))
                emails = emails_from_text(contrib_text)
            if pmid and emails:
                emails_by_pmid[pmid] = emails
    return emails_by_pmid


def resolve(since, output_file, data_dir, abc_api_url, gpad_file):

    if not gpad_file:
        gpad_file = download(GPAD_URL, data_dir, "YEAST-mod.gpad.gz")
    pmids = gene_centric_pmids(gpad_file, since)
    print(str(len(pmids)) + " PMIDs on gene-centric SGD annotations since " + since)
    if not pmids:
        with open(output_file, "w") as fw:
            fw.write("reference_curie\tpmid\tsource\temail\thas_email_in_abc\n")
        return

    abc_emails = fetch_abc_emails(pmids, abc_api_url)
    print("Tier 1 (ABC): emails for " + str(len(abc_emails)) + "/" + str(len(pmids)) + " papers")

    missing = [p for p in pmids if p not in abc_emails]
    pubmed_emails = fetch_pubmed_emails(missing)
    print("Tier 2 (PubMed metadata): emails for " + str(len(pubmed_emails)) +
          "/" + str(len(missing)) + " remaining papers")

    still_missing = [p for p in missing if p not in pubmed_emails]
    pmid_to_pmcid = map_pmids_to_pmcids(still_missing)
    pmc_emails = fetch_pmc_emails(pmid_to_pmcid)
    print("Tier 3 (PMC <corresp>): emails for " + str(len(pmc_emails)) +
          "/" + str(len(still_missing)) + " remaining papers")

    with open(output_file, "w") as fw:
        fw.write("reference_curie\tpmid\tsource\temail\thas_email_in_abc\n")
        row_count = 0
        for pmid in pmids:
            for (source, emails_by_pmid, in_abc) in ((SOURCE_ABC, abc_emails, "Y"),
                                                     (SOURCE_PUBMED, pubmed_emails, "N"),
                                                     (SOURCE_PMC, pmc_emails, "N")):
                emails = emails_by_pmid.get(pmid, [])
                if emails:
                    fw.write("PMID:" + pmid + "\t" + pmid + "\t" + source + "\t" +
                             " | ".join(emails) + "\t" + in_abc + "\n")
                    row_count += 1

    covered = set(abc_emails) | set(pubmed_emails) | set(pmc_emails)
    print("Done: emails for " + str(len(covered)) + "/" + str(len(pmids)) +
          " papers; " + str(row_count) + " rows -> " + output_file)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Resolve author emails (ABC -> PubMed -> PMC) for PMIDs on "
                    "gene-centric SGD GO annotations in the current GO release")
    parser.add_argument("-s", "--since", default=DEFAULT_SINCE,
                        help="only annotations with annotation_date >= this "
                             "(default: " + DEFAULT_SINCE + ")")
    parser.add_argument("-o", "--output-file", default=DEFAULT_OUTPUT_FILE,
                        help="output tsv (default: " + DEFAULT_OUTPUT_FILE + ")")
    parser.add_argument("-d", "--data-dir", default=DEFAULT_DATA_DIR,
                        help="directory for the downloaded GPAD; delete the file "
                             "there to force a fresh download "
                             "(default: " + DEFAULT_DATA_DIR + ")")
    parser.add_argument("--abc-api", default=ABC_API_URL,
                        help="ABC REST API base url (default: " + ABC_API_URL + ")")
    parser.add_argument("--gpad-file", default=None,
                        help="use this GPAD file instead of downloading")
    args = parser.parse_args()

    resolve(args.since, args.output_file, args.data_dir, args.abc_api, args.gpad_file)
