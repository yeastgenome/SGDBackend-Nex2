"""
Download PMC Open Access packages from AWS S3 bucket pmc-oa-opendata.

As of August 2026, PMC FTP service is deprecated in favor of AWS S3.
See: https://ncbiinsights.ncbi.nlm.nih.gov/2026/02/12/pmc-article-dataset-distribution-services/
"""
import gzip
import json
import shutil
import time
import logging
from os import path, makedirs, listdir
from os.path import join as path_join, basename
from typing import Dict, List, Optional

import boto3
import requests
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError

from src.models import Referencedbentity, ReferenceFile, Filedbentity
from scripts.loading.database_session import get_session
from scripts.loading.suppl_files.load_pubmed_PMC_files import load_data
from src.helpers import upload_file

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

# AWS S3 PMC Open Access bucket (anonymous access)
PMC_OA_S3_BUCKET = "pmc-oa-opendata"

# Directories
dataDir = 'scripts/loading/suppl_files/data/'
pmcFileDir = 'scripts/loading/suppl_files/pubmed_pmc_download/'

# EuroPMC API settings
EUROPEPMC_API_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPEPMC_BATCH_SIZE = 100
EUROPEPMC_MAX_PAGE_SIZE = 1000
OA_CACHE_FILE = dataDir + "europepmc_oa_cache.json"
OA_CACHE_TTL_DAYS = 30

# Cached S3 client for PMC OA bucket
_pmc_oa_s3_client = None


def get_pmc_oa_s3_client():
    """Get an S3 client configured for anonymous access to the PMC Open Access bucket."""
    global _pmc_oa_s3_client
    if _pmc_oa_s3_client is None:
        _pmc_oa_s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    return _pmc_oa_s3_client


def get_latest_pmc_version(pmcid: str) -> Optional[str]:
    """Get the latest version prefix for a PMC package."""
    if not pmcid.startswith('PMC'):
        pmcid = f'PMC{pmcid}'

    s3_client = get_pmc_oa_s3_client()

    try:
        response = s3_client.list_objects_v2(
            Bucket=PMC_OA_S3_BUCKET,
            Prefix=f"{pmcid}.",
            Delimiter='/'
        )
        prefixes = [p['Prefix'] for p in response.get('CommonPrefixes', [])]
        if prefixes:
            return sorted(prefixes)[-1].rstrip('/')
        return None
    except ClientError as e:
        log.error(f"Error listing PMC package versions for {pmcid}: {e}")
        return None


def list_pmc_package_files(pmcid: str, version: str = None) -> list:
    """List all files in a PMC package."""
    if not pmcid.startswith('PMC'):
        pmcid = f'PMC{pmcid}'

    if version:
        prefix = f"{pmcid}.{version}/"
    else:
        latest = get_latest_pmc_version(pmcid)
        if not latest:
            return []
        prefix = f"{latest}/"

    s3_client = get_pmc_oa_s3_client()

    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=PMC_OA_S3_BUCKET, Prefix=prefix)
        files = []
        for page in pages:
            for obj in page.get('Contents', []):
                files.append(obj['Key'])
        return files
    except ClientError as e:
        log.error(f"Error listing PMC package files for {pmcid}: {e}")
        return []


def download_pmc_package_from_s3(pmcid: str, dest_dir: str) -> bool:
    """Download all files from a PMC package to a local directory."""
    if not pmcid.startswith('PMC'):
        pmcid = f'PMC{pmcid}'

    if not get_latest_pmc_version(pmcid):
        log.warning(f"No PMC package found for {pmcid}")
        return False

    s3_client = get_pmc_oa_s3_client()
    files = list_pmc_package_files(pmcid)

    if not files:
        log.warning(f"No files found for {pmcid}")
        return False

    package_dir = path_join(dest_dir, pmcid)
    makedirs(package_dir, exist_ok=True)

    try:
        for file_key in files:
            file_name = basename(file_key)
            local_path = path_join(package_dir, file_name)
            log.info(f"Downloading {file_key} to {local_path}")
            s3_client.download_file(PMC_OA_S3_BUCKET, file_key, local_path)
        return True
    except ClientError as e:
        log.error(f"Error downloading PMC package {pmcid}: {e}")
        return False


# EuroPMC OA Status Functions
def load_oa_cache(cache_path: str) -> Dict[str, dict]:
    """Load OA metadata cache from JSON file."""
    if not path.exists(cache_path):
        return {}
    try:
        with open(cache_path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_oa_cache(cache_path: str, cache: Dict[str, dict]) -> None:
    """Save OA metadata cache to JSON file."""
    makedirs(path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2, sort_keys=True)


def normalize_pmcid(pmcid: str) -> str:
    """Normalize 'PMCID:PMC123' or 'PMC123' to 'PMC123' (uppercase)."""
    s = pmcid.strip().upper()
    if s.startswith("PMCID:"):
        s = s.split(":", 1)[1]
    if not s.startswith("PMC"):
        s = f"PMC{s}"
    return s


def fetch_oa_metadata_batch(pmcids: List[str], session: requests.Session,
                            timeout: int = 60) -> Dict[str, dict]:
    """Fetch OA metadata from EuroPMC API for a batch of PMCIDs."""
    if not pmcids:
        return {}

    effective_page_size = min(len(pmcids), EUROPEPMC_MAX_PAGE_SIZE)
    or_query = " OR ".join([f"PMCID:{p}" for p in pmcids])
    query = f"({or_query})"

    params = {
        "query": query,
        "resultType": "core",
        "format": "json",
        "pageSize": effective_page_size
    }

    try:
        r = session.get(EUROPEPMC_API_URL, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()

        result_list = data.get("resultList", {})
        results = result_list.get("result", []) if result_list else []

        out: Dict[str, dict] = {}
        cached_at = time.time()
        for res in results:
            if not isinstance(res, dict):
                continue
            pmcid = (res.get("pmcid") or "").upper()
            if not pmcid:
                continue

            out[pmcid] = {
                "hit": True,
                "is_open_access": res.get("isOpenAccess") == "Y",
                "has_pdf": res.get("hasPDF") == "Y",
                "license": res.get("license"),
                "cached_at": cached_at,
            }

        return out

    except Exception as e:
        log.warning(f"EuroPMC API batch fetch failed: {type(e).__name__}: {e}")
        return {}


def _is_cache_entry_stale(entry: dict) -> bool:
    """Check if a cache entry is older than TTL."""
    cached_at = entry.get("cached_at")
    if cached_at is None:
        return True
    age_days = (time.time() - cached_at) / (60 * 60 * 24)
    return age_days > OA_CACHE_TTL_DAYS


def fetch_oa_status_for_pmcids(pmcids: List[str], cache: Dict[str, dict]) -> Dict[str, dict]:
    """Fetch OA status for list of PMCIDs using EuroPMC API."""
    unique_pmcids = set(normalize_pmcid(p) for p in pmcids)

    missing = []
    stale = 0
    for p in unique_pmcids:
        if p not in cache:
            missing.append(p)
        elif _is_cache_entry_stale(cache[p]):
            missing.append(p)
            stale += 1

    if not missing:
        log.info(f"OA cache hit: all {len(unique_pmcids)} PMCIDs found in cache")
        return cache

    if stale > 0:
        log.info(f"OA cache: {len(unique_pmcids)} unique PMCIDs, {len(missing)} to fetch ({stale} stale)")
    else:
        log.info(f"OA cache: {len(unique_pmcids)} unique PMCIDs, {len(missing)} missing, fetching from EuroPMC...")

    session = requests.Session()
    session.headers.update({"User-Agent": "sgd-pmc-download/1.0"})

    fetched = 0
    cached_at = time.time()
    for i in range(0, len(missing), EUROPEPMC_BATCH_SIZE):
        batch = missing[i:i + EUROPEPMC_BATCH_SIZE]
        batch_meta = fetch_oa_metadata_batch(batch, session)

        for pmcid, meta in batch_meta.items():
            cache[pmcid] = meta

        for pmcid in batch:
            if pmcid not in batch_meta:
                cache[pmcid] = {
                    "hit": False,
                    "is_open_access": False,
                    "has_pdf": False,
                    "license": None,
                    "cached_at": cached_at,
                }

        fetched += len(batch)
        if fetched % 500 == 0 or fetched == len(missing):
            log.info(f"Fetched OA metadata: {fetched}/{len(missing)}")

        time.sleep(0.1)

    return cache


def is_open_access(cache: Dict[str, dict], pmcid: str) -> bool:
    """Check if a PMCID is Open Access."""
    pmcid = normalize_pmcid(pmcid)
    entry = cache.get(pmcid, {})
    return entry.get("is_open_access", False)


def gzip_file(file_with_path: str) -> Optional[str]:
    """Gzip a file and return the path to the gzipped file."""
    try:
        gzip_file_with_path = file_with_path + ".gz"
        with open(file_with_path, 'rb') as f_in, gzip.open(gzip_file_with_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        return gzip_file_with_path
    except Exception as e:
        log.error(f"Error gzipping file {file_with_path}: {e}")
        return None


def gzip_and_upload_files(pmid: int, pmcid: str, pmid_dir: str) -> bool:
    """
    Gzip all files for a paper and upload to SGD S3.

    Args:
        pmid: PubMed ID
        pmcid: PMC ID
        pmid_dir: Directory containing downloaded PMC files

    Returns:
        True if successful, False otherwise
    """
    pmcid_dir = path_join(pmid_dir, pmcid)
    if not path.exists(pmcid_dir):
        log.warning(f"PMCID directory not found: {pmcid_dir}")
        return False

    files = listdir(pmcid_dir)
    if not files:
        log.warning(f"No files found in {pmcid_dir}")
        return False

    success_count = 0
    for file_name in files:
        file_path = path_join(pmcid_dir, file_name)
        if not path.isfile(file_path):
            continue

        # Skip already gzipped files
        if file_path.endswith('.gz'):
            gzip_path = file_path
        else:
            gzip_path = gzip_file(file_path)
            if gzip_path is None:
                continue

        try:
            # Upload to SGD S3
            s3_path = f"suppl_files/{pmid}/{pmcid}/{basename(gzip_path)}"
            status = upload_file(gzip_path, s3_path)
            if status:
                success_count += 1
                log.info(f"Uploaded {gzip_path} to S3: {s3_path}")
            else:
                log.error(f"Failed to upload {gzip_path} to S3")
        except Exception as e:
            log.error(f"Error uploading {gzip_path}: {e}")

    return success_count > 0


def download_files():
    """Download PMC Open Access packages from AWS S3 for SGD references."""

    nex_session = get_session()

    # Get references that already have supplemental files
    reference_id_to_file_id = dict([
        (x.reference_id, x.file_id)
        for x in nex_session.query(ReferenceFile).filter_by(file_type='Supplemental').all()
    ])

    file_id_to_s3_url = dict([
        (x.dbentity_id, x.s3_url)
        for x in nex_session.query(Filedbentity).filter_by(description='PubMed Central download').all()
    ])

    # Get all references with PMIDs that need PMC files
    pmid_to_pmcid = {}
    references_to_process = []

    for x in nex_session.query(Referencedbentity).filter(Referencedbentity.pmid.isnot(None)).all():
        file_id = reference_id_to_file_id.get(x.dbentity_id)
        if file_id is None or file_id not in file_id_to_s3_url:
            if x.pmcid:
                pmid_to_pmcid[x.pmid] = x.pmcid
                references_to_process.append(x)

    if not pmid_to_pmcid:
        log.info("No references need PMC package downloads.")
        nex_session.close()
        return

    log.info(f"Found {len(pmid_to_pmcid)} references to check for PMC packages")

    # Check OA status via EuroPMC API
    makedirs(dataDir, exist_ok=True)
    oa_cache = load_oa_cache(OA_CACHE_FILE)
    oa_cache = fetch_oa_status_for_pmcids(list(pmid_to_pmcid.values()), oa_cache)
    save_oa_cache(OA_CACHE_FILE, oa_cache)

    # Filter to only Open Access papers
    oa_references = []
    non_oa_count = 0
    for ref in references_to_process:
        if is_open_access(oa_cache, ref.pmcid):
            oa_references.append(ref)
        else:
            non_oa_count += 1

    log.info(f"OA filter: {len(oa_references)} Open Access papers, {non_oa_count} non-OA skipped")
    log.info(f"Total papers to download from S3: {len(oa_references)}")

    if not oa_references:
        log.info("No Open Access papers to download.")
        nex_session.close()
        return

    # Download packages from S3
    download_count = 0
    error_count = 0
    total = len(oa_references)

    for idx, ref in enumerate(oa_references, 1):
        pmid = ref.pmid
        pmcid = ref.pmcid

        pmid_dir = path_join(pmcFileDir, str(pmid))
        if path.exists(pmid_dir) and listdir(pmid_dir):
            log.info(f"[{idx}/{total}] PMID:{pmid} - Already downloaded, skipping")
            continue

        try:
            log.info(f"[{idx}/{total}] PMID:{pmid} PMCID:{pmcid} - Downloading from S3...")
            makedirs(pmid_dir, exist_ok=True)

            success = download_pmc_package_from_s3(pmcid, pmid_dir)

            if success:
                download_count += 1
                log.info(f"[{idx}/{total}] PMID:{pmid} PMCID:{pmcid} - Download successful")

                # Gzip and upload to SGD S3
                gzip_and_upload_files(pmid, pmcid, pmid_dir)
            else:
                log.warning(f"[{idx}/{total}] PMID:{pmid} PMCID:{pmcid} - Not found in S3")
                if path.exists(pmid_dir) and not listdir(pmid_dir):
                    shutil.rmtree(pmid_dir)

        except Exception as e:
            error_count += 1
            log.error(f"[{idx}/{total}] PMID:{pmid} PMCID:{pmcid} - Error: {type(e).__name__}: {e}")
            if path.exists(pmid_dir) and not listdir(pmid_dir):
                shutil.rmtree(pmid_dir)
            continue

        if idx % 100 == 0:
            log.info(f"Progress: {idx}/{total} processed, {download_count} downloaded, {error_count} errors")

    log.info(f"Download summary: {download_count} downloaded, {error_count} errors")

    nex_session.close()


if __name__ == "__main__":

    if path.exists(pmcFileDir):
        shutil.rmtree(pmcFileDir)
    makedirs(pmcFileDir)

    makedirs(dataDir, exist_ok=True)

    download_files()
    load_data()
