import sys
import json
import gzip
import requests
from urllib import request
from os import environ, makedirs, path
from scripts.loading.database_session import get_session
import logging

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

ABC_API_ROOT_URL = environ.get('ABC_API_ROOT_URL', 'https://literature-rest.alliancegenome.org/')
FMS_GAF_API_URL = "https://fms.alliancegenome.org/api/datafile/by/GAF?latest=true"
FMS_INTERACTION_DOWNLOAD_URL = "https://fms.alliancegenome.org/download/"

DATA_DIR = "scripts/checking/data/"
REFERENCE_JSON_FILE = DATA_DIR + "reference_new_SGD.json"


def check_data():

    # Create data directory if it doesn't exist
    makedirs(DATA_DIR, exist_ok=True)

    nex_session = get_session()

    # Download reference_new_SGD.json from ABC API
    download_reference_json()

    # Parse JSON and extract PMIDs with Gaf or Interaction mod_corpus_sort_source
    gaf_pmids, interaction_pmids = extract_gaf_interaction_pmids()

    # Get PMIDs that are in the SGD database
    pmid_to_ref_id = get_pmids_in_db(nex_session)

    # Filter to only PMIDs in the database
    gaf_pmids_in_db = set()
    for pmid in gaf_pmids:
        if pmid in pmid_to_ref_id:
            gaf_pmids_in_db.add(pmid)

    interaction_pmids_in_db = set()
    for pmid in interaction_pmids:
        if pmid in pmid_to_ref_id:
            interaction_pmids_in_db.add(pmid)

    # Get sources from GAF file for GAF PMIDs
    gaf_pmid_sources = {}
    if gaf_pmids_in_db:
        gaf_pmid_sources = get_sources_from_gaf_file(gaf_pmids_in_db)

    # Get sources from interaction files for interaction PMIDs
    interaction_pmid_sources = {}
    if interaction_pmids_in_db:
        interaction_pmid_sources = get_sources_from_interaction_files(interaction_pmids_in_db)

    # Print report
    print_report(gaf_pmids_in_db, gaf_pmid_sources,
                 interaction_pmids_in_db, interaction_pmid_sources)

    nex_session.close()


def download_reference_json():
    """Download reference_new_SGD.json from ABC API."""
    url = ABC_API_ROOT_URL + "reference/get_recently_sorted_references/SGD"
    try:
        req = request.urlopen(url)
        data = req.read()
        with open(REFERENCE_JSON_FILE, 'wb') as fh:
            fh.write(data)
    except Exception as e:
        log.error("Error downloading the file: " + REFERENCE_JSON_FILE + ". Error=" + str(e))
        sys.exit(1)


def extract_gaf_interaction_pmids():
    """
    Parse reference_new_SGD.json and extract PMIDs for records with
    mod_corpus_sort_source = 'Gaf' or 'Interaction' in SGD mod_corpus_associations.
    """
    gaf_pmids = set()
    interaction_pmids = set()

    with open(REFERENCE_JSON_FILE, "r") as f:
        json_data = json.load(f)

    for record in json_data.get('data', []):
        # Get PMID from cross_references
        pmid = None
        for xref in record.get('cross_references', []):
            if xref.get('curie', '').startswith('PMID') and xref.get('is_obsolete') is False:
                pmid = xref['curie'].replace('PMID:', '')
                break

        if not pmid:
            continue

        # Convert to integer for comparison with database
        try:
            pmid_int = int(pmid)
        except ValueError:
            continue

        # Check mod_corpus_associations for SGD with Gaf or Interaction source
        for mca in record.get('mod_corpus_associations', []):
            if mca.get('mod_abbreviation') != 'SGD':
                continue
            sort_source = mca.get('mod_corpus_sort_source', '')
            if sort_source == 'Gaf':
                gaf_pmids.add(pmid_int)
            elif sort_source == 'Interaction':
                interaction_pmids.add(pmid_int)

    return gaf_pmids, interaction_pmids


def get_pmids_in_db(nex_session):
    """Get all PMIDs that are in the SGD database."""
    pmid_to_ref_id = {}
    rows = nex_session.execute(
        "SELECT pmid, dbentity_id FROM nex.referencedbentity WHERE pmid IS NOT NULL"
    ).fetchall()
    for row in rows:
        pmid_to_ref_id[int(row[0])] = row[1]
    return pmid_to_ref_id


def get_sources_from_gaf_file(pmids_to_check):
    """
    Download SGD GAF file and extract sources for the given PMIDs.
    Returns dict mapping PMID to set of sources.
    """
    pmid_sources = {}

    # Fetch GAF file list from FMS API
    try:
        response = requests.get(FMS_GAF_API_URL, timeout=60)
        response.raise_for_status()
        gaf_files = response.json()
    except requests.RequestException as e:
        log.error(f"Error fetching GAF file list: {e}")
        return pmid_sources

    # Find SGD GAF file
    sgd_gaf_url = None
    for gaf_file in gaf_files:
        data_sub_type = gaf_file.get("dataSubType", {}).get("name", "")
        if data_sub_type == "SGD":
            sgd_gaf_url = gaf_file.get("s3Url")
            break

    if not sgd_gaf_url:
        log.error("SGD GAF file not found in FMS API response")
        return pmid_sources

    # Download GAF file
    file_name = sgd_gaf_url.split("/")[-1]
    file_with_path = DATA_DIR + file_name
    try:
        response = requests.get(sgd_gaf_url, timeout=300, stream=True)
        response.raise_for_status()
        with open(file_with_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    except requests.RequestException as e:
        log.error(f"Failed to download SGD GAF file: {e}")
        return pmid_sources

    # Convert pmids_to_check to strings for comparison
    pmids_to_check_str = {str(pmid) for pmid in pmids_to_check}

    # Parse GAF file and extract sources for PMIDs we're looking for
    try:
        if file_with_path.endswith('.gz'):
            f = gzip.open(file_with_path, "rt")
        else:
            f = open(file_with_path, "r")

        with f:
            for line in f:
                if line.startswith("!"):
                    continue

                parts = line.strip().split("\t")
                if len(parts) < 15:
                    continue

                # Column 6 (index 5) contains DB:Reference field
                # Column 15 (index 14) contains assigned_by field
                ref_col = parts[5]
                source = parts[14] if len(parts) > 14 else "Unknown"
                refs = ref_col.split("|")

                for ref in refs:
                    ref = ref.strip()
                    if ref.startswith("PMID:"):
                        pmid = ref.replace("PMID:", "")
                        if pmid in pmids_to_check_str:
                            if pmid not in pmid_sources:
                                pmid_sources[pmid] = set()
                            pmid_sources[pmid].add(source)
    except Exception as e:
        log.error(f"Error reading GAF file: {e}")

    return pmid_sources


def get_sources_from_interaction_files(pmids_to_check):
    """
    Download SGD interaction files and extract sources for the given PMIDs.
    Returns dict mapping PMID to set of sources.
    """
    pmid_sources = {}

    # Convert pmids_to_check to strings for comparison
    pmids_to_check_str = {str(pmid) for pmid in pmids_to_check}

    # SGD has both GEN and MOL interaction files
    interaction_types = ["GEN", "MOL"]

    for int_type in interaction_types:
        file_name = f"INTERACTION-{int_type}_SGD.tsv.gz"
        url = FMS_INTERACTION_DOWNLOAD_URL + file_name
        file_with_path = DATA_DIR + file_name

        try:
            response = requests.get(url, timeout=300, stream=True)
            response.raise_for_status()
            with open(file_with_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.RequestException as e:
            continue

        # Parse interaction file
        try:
            with gzip.open(file_with_path, "rt") as f:
                for line in f:
                    if line.startswith("#"):
                        continue
                    items = line.split("\t")
                    if len(items) < 9:
                        continue

                    pub_ids = items[8].split("|")
                    pmid = None
                    for pub_id in pub_ids:
                        if pub_id.isdigit():
                            pmid = pub_id
                        elif pub_id.startswith("pubmed:"):
                            pmid = pub_id.replace("pubmed:", "")

                    if pmid and pmid in pmids_to_check_str:
                        source = "Unknown"
                        if len(items) > 12:
                            # Extract source from column 13 (e.g., "psi-mi:MI:0469(IntAct)")
                            source_field = items[12]
                            if "(" in source_field and ")" in source_field:
                                source = source_field.split("(")[1].replace(")", "")
                        if pmid not in pmid_sources:
                            pmid_sources[pmid] = set()
                        pmid_sources[pmid].add(source)
        except Exception as e:
            pass

    return pmid_sources


def print_report(gaf_pmids, gaf_pmid_sources, interaction_pmids, interaction_pmid_sources):
    """Print the final report."""

    print("\nPMIDs added from the SGD GAF file in the past week:")
    if gaf_pmids:
        for pmid in sorted(gaf_pmids):
            sources = gaf_pmid_sources.get(str(pmid), set())
            if sources:
                sources_str = ", ".join(sorted(sources))
                print(f"PMID:{pmid} [{sources_str}]")
            else:
                print(f"PMID:{pmid}")
    else:
        print("None")

    print("\nPMIDs added from the SGD Interaction datasets in the past week:")
    if interaction_pmids:
        for pmid in sorted(interaction_pmids):
            sources = interaction_pmid_sources.get(str(pmid), set())
            if sources:
                sources_str = ", ".join(sorted(sources))
                print(f"PMID:{pmid} [{sources_str}]")
            else:
                print(f"PMID:{pmid}")
    else:
        print("None")


if __name__ == '__main__':

    check_data()
