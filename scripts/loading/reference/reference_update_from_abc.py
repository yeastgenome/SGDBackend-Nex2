#!/usr/bin/env python3
"""
Update SGD reference data from ABC (Alliance) JSON dump.

Fixes the "Killed" (OOM) issue by:
1) NOT loading the entire gz JSON into memory (no f.read() + ujson.loads()).
2) Building an on-disk SQLite index (PMID -> JSON) using streaming JSON parsing (ijson).
3) NOT preloading huge DB tables into Python dicts; instead fetch authors/types/urls/abstracts per batch.

Dependencies:
  pip install ijson

Notes:
- This keeps your overall logic/behavior the same, but makes memory usage stable.
- The first run will build the SQLite index (can take a bit), subsequent runs reuse it.
"""

import sys
import logging
import gzip
import sqlite3
from datetime import datetime
from os import environ
from os.path import exists, getmtime
from typing import Dict, List, Tuple, Optional

import boto3
from botocore.exceptions import ClientError
import ujson
import ijson
from bs4 import BeautifulSoup

from sqlalchemy import text

from src.models import (
    Referencedbentity, Referenceauthor, ReferenceUrl, Referencetype,
    Journal, Source, Referencedocument, ReferenceRelation
)
from scripts.loading.database_session import get_session
from scripts.loading.reference.pubmed import set_cite
from scripts.loading.util import link_gene_names

__author__ = 'sweng66'

CREATED_BY = 'OTTO'
SRC = 'NCBI'
AUTHOR_TYPE = 'Author'
PMC_URL_TYPE = 'PMC full text'
DOI_URL_TYPE = 'DOI full text'
PMC_ROOT = 'http://www.ncbi.nlm.nih.gov/pmc/articles/'
DOI_ROOT = 'http://dx.doi.org/'
AWS_REGION = 'us-east-1'

# Batch processing parameters (DB refs)
limit = 2500
loop_count = 60
max_session = 10000
max_commit = 100

json_file = 'reference_SGD.json.gz'
bucketname = 'agr-literature'
s3_file_location = 'prod/reference/dumps/latest/' + json_file

# log_file is your output "change log"
log_file = "scripts/loading/reference/logs/reference_update_from_abc.log"

# SQLite index for ABC data (PMID -> JSON)
abc_sqlite = "reference_SGD_abc_pmid_index.sqlite3"

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)

# Prefer LOG_FILE env var if present, otherwise fall back to log_file
_log_path = environ.get('LOG_FILE', log_file)

logging.basicConfig(
    format='%(message)s',
    handlers=[
        logging.FileHandler(_log_path),
        logging.StreamHandler(sys.stderr)
    ],
    level=logging.INFO
)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def update_data():
    logger.info("Downloading ABC reference_SGD.json file...")
    logger.info(datetime.now())
    download_reference_json_file_from_alliance_s3()

    logger.info("Ensuring ABC PMID index exists (SQLite)...")
    logger.info(datetime.now())
    ensure_abc_sqlite_index()

    nex_session = get_session()

    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()])
    source_id = source_to_id[SRC]

    logger.info("Loading journal lookup tables...")
    logger.info(datetime.now())
    journal_abbr_to_journal_id = dict([(x.med_abbr, x.journal_id) for x in nex_session.query(Journal).all()])
    journal_name_to_journal_id = dict([(x.display_name, x.journal_id) for x in nex_session.query(Journal).all()])

    # Cache for PMID -> dbentity_id to support comment/corrections lookups
    pmid_to_reference_id_cache: Dict[int, int] = {}

    # Open SQLite once
    abc_conn = open_abc_sqlite()

    fw = open(log_file, "w")

    i = 0
    for index in range(loop_count):
        offset = index * limit

        if i != 0 and i % max_session == 0:
            nex_session.commit()
            nex_session.close()
            nex_session = get_session()

        rows = (nex_session.query(Referencedbentity)
                .filter(Referencedbentity.pmid.isnot(None))
                .order_by(Referencedbentity.dbentity_id)
                .offset(offset)
                .limit(limit)
                .all())

        if len(rows) == 0:
            break

        ref_ids = [r.dbentity_id for r in rows]
        # Per-batch DB lookups (memory-safe)
        reference_id_to_authors = retrieve_author_data_for_refs(nex_session, ref_ids)
        reference_id_to_types = retrieve_pubmed_types_for_refs(nex_session, ref_ids)
        reference_id_to_urls = retrieve_urls_for_refs(nex_session, ref_ids)
        reference_id_to_abstract = retrieve_abstracts_for_refs(nex_session, ref_ids)

        # Batch-level PMID->dbentity_id cache for quick comment/corrections mapping
        for r in rows:
            if r.pmid is not None:
                pmid_to_reference_id_cache[int(r.pmid)] = int(r.dbentity_id)

        for x in rows:
            if i != 0 and i % max_commit == 0:
                nex_session.commit()
            i += 1

            logger.info("processing ref: {}: PMID:{}".format(i, x.pmid))

            abc_json_data = get_abc_json_by_pmid(abc_conn, int(x.pmid))
            if not abc_json_data:
                logger.info("PubMed paper in SGD: PMID:{} not in ABC".format(x.pmid))
                continue

            try:
                (titleABC, yearABC, volumeABC, issueABC, pageABC, doiABC, pmcidABC, pubStatusABC,
                 citationABC, journalIdABC, authorsABC, pubmedTypesABC, abstractABC,
                 commentCorrectionsABC) = parse_process_json_data(
                    abc_json_data,
                    int(x.pmid),
                    pmid_to_reference_id_cache,
                    nex_session,
                    x.journal_id,
                    journal_abbr_to_journal_id,
                    journal_name_to_journal_id
                )
            except Exception as e:
                logger.info("Error parsing json data for PMID:{}. See details: {}".format(x.pmid, e))
                continue

            try:
                update_reference_table(
                    nex_session, fw, x, titleABC, yearABC, volumeABC,
                    issueABC, pageABC, doiABC, pmcidABC, pubStatusABC,
                    citationABC, journalIdABC
                )

                update_authors(
                    nex_session, fw, x.pmid, x.dbentity_id,
                    reference_id_to_authors.get(x.dbentity_id, []),
                    authorsABC, source_id
                )

                update_pubmedTypes(
                    nex_session, fw, x.pmid, x.dbentity_id,
                    reference_id_to_types.get(x.dbentity_id, []),
                    pubmedTypesABC, source_id
                )

                update_abstract(
                    nex_session, fw, x.pmid, x.dbentity_id,
                    reference_id_to_abstract.get(x.dbentity_id, ''),
                    abstractABC, source_id
                )

                update_urls(
                    nex_session, fw, x.pmid, x.dbentity_id, doiABC, pmcidABC,
                    reference_id_to_urls.get(x.dbentity_id, []),
                    source_id
                )

                update_comments_corrections(
                    nex_session, fw, int(x.pmid), source_id, commentCorrectionsABC
                )

            except Exception as e:
                logger.info("Error updating data for PMID:{}. See details: {}".format(x.pmid, e))
                # keep going
                pass

    nex_session.commit()
    nex_session.close()
    fw.close()

    try:
        abc_conn.close()
    except Exception:
        pass

    logger.info("DONE!")
    logger.info(datetime.now())


# -----------------------------------------------------------------------------
# S3 download
# -----------------------------------------------------------------------------
def download_reference_json_file_from_alliance_s3():
    s3_client = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=environ['ABC_AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=environ['ABC_AWS_SECRET_ACCESS_KEY']
    )
    try:
        response = s3_client.download_file(bucketname, s3_file_location, json_file)
        if response is not None:
            logger.info("boto3 downloaded response: %s", response)
    except ClientError as e:
        logging.error(e)
        return False


# -----------------------------------------------------------------------------
# ABC SQLite index (PMID -> JSON)
# -----------------------------------------------------------------------------
def open_abc_sqlite() -> sqlite3.Connection:
    conn = sqlite3.connect(abc_sqlite)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    return conn


def ensure_abc_sqlite_index():
    """
    Build SQLite index if missing or older than the gz.
    """
    gz_mtime = getmtime(json_file) if exists(json_file) else None
    needs_build = True

    if exists(abc_sqlite) and gz_mtime is not None:
        try:
            db_mtime = getmtime(abc_sqlite)
            # rebuild if DB is older than the gz
            needs_build = db_mtime < gz_mtime
        except Exception:
            needs_build = True

    conn = open_abc_sqlite()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS abc_ref (
                pmid INTEGER PRIMARY KEY,
                json TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()

    if not needs_build:
        logger.info("ABC PMID index is up-to-date: {}".format(abc_sqlite))
        return

    logger.info("Building ABC PMID index: {}".format(abc_sqlite))
    build_abc_sqlite_index()


def build_abc_sqlite_index():
    """
    Stream-parse the gz JSON and store (pmid -> ujson.dumps(record)) in SQLite.
    Memory-safe: does not load entire JSON into RAM.
    """
    conn = open_abc_sqlite()
    try:
        conn.execute("DROP TABLE IF EXISTS abc_ref;")
        conn.execute("""
            CREATE TABLE abc_ref (
                pmid INTEGER PRIMARY KEY,
                json TEXT NOT NULL
            )
        """)
        conn.commit()

        insert_sql = "INSERT OR REPLACE INTO abc_ref(pmid, json) VALUES (?, ?)"
        batch: List[Tuple[int, str]] = []
        batch_size = 5000
        n = 0

        with gzip.open(json_file, 'rb') as f:
            for rec in ijson.items(f, 'data.item'):
                pmid = extract_pmid_from_abc_record(rec)
                if not pmid:
                    continue
                batch.append((pmid, ujson.dumps(rec)))
                n += 1

                if len(batch) >= batch_size:
                    conn.executemany(insert_sql, batch)
                    conn.commit()
                    batch.clear()
                    logger.info("Indexed {} ABC records...".format(n))

        if batch:
            conn.executemany(insert_sql, batch)
            conn.commit()
            logger.info("Indexed {} ABC records...".format(n))

        conn.execute("CREATE INDEX IF NOT EXISTS idx_abc_ref_pmid ON abc_ref(pmid);")
        conn.commit()

        logger.info("ABC PMID index build complete. Total indexed: {}".format(n))

    finally:
        conn.close()


def extract_pmid_from_abc_record(rec: dict) -> Optional[int]:
    for c in rec.get('cross_references', []) or []:
        curie = c.get('curie', '')
        if curie.startswith('PMID:') and c.get('is_obsolete') is False:
            try:
                return int(curie.split(':', 1)[1])
            except Exception:
                return None
    return None


def get_abc_json_by_pmid(conn: sqlite3.Connection, pmid: int) -> Optional[dict]:
    row = conn.execute("SELECT json FROM abc_ref WHERE pmid = ?", (pmid,)).fetchone()
    if not row:
        return None
    try:
        return ujson.loads(row[0])
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Per-batch DB retrieval (memory-safe)
# -----------------------------------------------------------------------------
def retrieve_urls_for_refs(nex_session, ref_ids: List[int]) -> Dict[int, List[Tuple[str, str]]]:
    reference_id_to_urls: Dict[int, List[Tuple[str, str]]] = {}
    if not ref_ids:
        return reference_id_to_urls

    for x in nex_session.query(ReferenceUrl).filter(ReferenceUrl.reference_id.in_(ref_ids)).all():
        urls = reference_id_to_urls.get(x.reference_id, [])
        urls.append((x.url_type, x.obj_url))
        reference_id_to_urls[x.reference_id] = urls
    return reference_id_to_urls


def retrieve_abstracts_for_refs(nex_session, ref_ids: List[int]) -> Dict[int, str]:
    reference_id_to_abstract: Dict[int, str] = {}
    if not ref_ids:
        return reference_id_to_abstract

    q = (nex_session.query(Referencedocument)
         .filter(Referencedocument.document_type == 'Abstract',
                 Referencedocument.reference_id.in_(ref_ids)))
    for x in q.all():
        reference_id_to_abstract[x.reference_id] = x.text
    return reference_id_to_abstract


def retrieve_pubmed_types_for_refs(nex_session, ref_ids: List[int]) -> Dict[int, List[str]]:
    reference_id_to_types: Dict[int, List[str]] = {}
    if not ref_ids:
        return reference_id_to_types

    allTypes = (nex_session.query(Referencetype)
                .filter(Referencetype.reference_id.in_(ref_ids))
                .order_by(Referencetype.reference_id, Referencetype.display_name)
                .all())

    for x in allTypes:
        types = reference_id_to_types.get(x.reference_id, [])
        types.append(x.display_name)
        reference_id_to_types[x.reference_id] = types
    return reference_id_to_types


def retrieve_author_data_for_refs(nex_session, ref_ids: List[int]) -> Dict[int, List[Tuple[str, str, int]]]:
    reference_id_to_authors: Dict[int, List[Tuple[str, str, int]]] = {}
    if not ref_ids:
        return reference_id_to_authors

    allAuthors = (nex_session.query(Referenceauthor)
                  .filter(Referenceauthor.reference_id.in_(ref_ids))
                  .order_by(Referenceauthor.reference_id, Referenceauthor.author_order)
                  .all())

    for x in allAuthors:
        authors = reference_id_to_authors.get(x.reference_id, [])
        orcid = x.orcid if x.orcid else ''
        authors.append((x.display_name, orcid, x.author_order))
        reference_id_to_authors[x.reference_id] = authors
    return reference_id_to_authors


# -----------------------------------------------------------------------------
# Update logic (mostly your original code)
# -----------------------------------------------------------------------------
def update_orcid(nex_session, fw, pmid, reference_id, author2orcidDB, author2orcidABC):
    for (author, order) in author2orcidDB:
        orcidDB = author2orcidDB[(author, order)]
        orcidABC = author2orcidABC[(author, order)]
        if orcidABC != '' and orcidABC != orcidDB:
            logger.info("PMID:{}: The orcid for {} (author_order={}): new_orcid={}, old_orcid={}".format(
                pmid, author, order, orcidABC, orcidDB
            ))
            x = nex_session.query(Referenceauthor).filter_by(
                reference_id=reference_id, display_name=author, author_order=order
            ).one_or_none()
            if x:
                x.orcid = orcidABC
                nex_session.add(x)
                fw.write("PMID:{}: The orcid for {} (author_order={}) has been updated from {} to {}.\n".format(
                    pmid, author, order, orcidABC, orcidDB
                ))


def update_authors(nex_session, fw, pmid, reference_id, authorsDBwithOrcid, authorsABCwithOrcid, source_id):
    if authorsDBwithOrcid == authorsABCwithOrcid or len(authorsABCwithOrcid) == 0:
        return

    authorsDB = []
    author2orcidDB = {}
    for (authorName, orcid, order) in authorsDBwithOrcid:
        authorsDB.append((authorName, order))
        author2orcidDB[(authorName, order)] = orcid

    authorsABC = []
    author2orcidABC = {}
    for (authorName, orcid, order) in authorsABCwithOrcid:
        authorsABC.append((authorName, order))
        author2orcidABC[(authorName, order)] = orcid

    if authorsDB == authorsABC:
        update_orcid(nex_session, fw, pmid, reference_id, author2orcidDB, author2orcidABC)
        return

    logger.info("PMID:{}: old_authors={}".format(pmid, authorsDB))
    logger.info("PMID:{}: new_authors={}".format(pmid, authorsABC))

    for ra in nex_session.query(Referenceauthor).filter_by(reference_id=reference_id).order_by(Referenceauthor.author_order).all():
        logger.info("PMID:{}: deleting old author {}".format(pmid, ra.display_name))
        nex_session.delete(ra)
        nex_session.flush()

    for (author_name, orcid, author_order) in authorsABCwithOrcid:
        logger.info("PMID:{}: adding new author {}, {}".format(pmid, author_name, author_order))
        ra = Referenceauthor(
            display_name=author_name,
            source_id=source_id,
            orcid=orcid if orcid else None,
            obj_url='/author/' + author_name.replace(' ', '_'),
            reference_id=reference_id,
            author_order=author_order,
            author_type=AUTHOR_TYPE,
            created_by=CREATED_BY
        )
        nex_session.add(ra)
        nex_session.flush()
        nex_session.refresh(ra)

    fw.write("PMID:{}: The author(s) in Referenceauthor table are updated.\n".format(pmid))


def update_pubmedTypes(nex_session, fw, pmid, reference_id, pubmedTypesDB, pubmedTypesABC, source_id):
    if pubmedTypesDB == pubmedTypesABC or len(pubmedTypesABC) == 0:
        return

    message = ''
    for type in pubmedTypesDB:
        if type not in pubmedTypesABC:
            for pt in nex_session.query(Referencetype).filter_by(reference_id=reference_id, display_name=type).all():
                nex_session.delete(pt)
                message = "pubmedType:'{}' is deleted".format(type)
    for type in pubmedTypesABC:
        if type not in pubmedTypesDB:
            rt = Referencetype(
                display_name=type,
                source_id=source_id,
                obj_url='/referencetype/' + type.replace(' ', '_'),
                reference_id=reference_id,
                created_by=CREATED_BY
            )
            nex_session.add(rt)
            message = message + "pubmedType:'{}' is added".format(type)

    if message:
        fw.write("PMID:{}: The Referencetype is updated. See details: {}\n".format(pmid, message))


def update_reference_table(nex_session, fw, x, titleABC, yearABC, volumeABC, issueABC, pageABC, doiABC, pmcidABC,
                           pubStatusABC, citationABC, journalIdABC):
    message = ''
    if titleABC and x.title != titleABC:
        message = "TITLE updated from '{}' to '{}'. ".format(x.title, titleABC)
        x.title = titleABC
    if yearABC and x.year != yearABC:
        message = message + "YEAR updated from '{}' to '{}'. ".format(x.year, yearABC)
        x.year = yearABC
    if volumeABC and x.volume != volumeABC:
        message = message + "VOLUME updated from '{}' to '{}'. ".format(x.volume, volumeABC)
        x.volume = volumeABC
    if issueABC and x.issue != issueABC:
        message = message + "ISSUE updated from '{}' to '{}'. ".format(x.issue, issueABC)
        x.issue = issueABC
    if pageABC and x.page != pageABC:
        message = message + "PAGE updated from '{}' to '{}'. ".format(x.page, pageABC)
        x.page = pageABC
    if doiABC and x.doi != doiABC:
        message = message + "DOI updated from '{}' to '{}'. ".format(x.doi, doiABC)
        x.doi = doiABC
    if pmcidABC and x.pmcid != pmcidABC:
        message = message + "PMCID updated from '{}' to '{}'. ".format(x.pmcid, pmcidABC)
        x.pmcid = pmcidABC
    if pubStatusABC and x.publication_status != pubStatusABC:
        message = message + "PUBLICATION_STATUS updated from '{}' to '{}'. ".format(x.publication_status, pubStatusABC)
        x.publication_status = pubStatusABC
    if citationABC and x.citation != citationABC:
        message = message + "CITATION updated from '{}' to '{}'. ".format(x.citation, citationABC)
        x.citation = citationABC
    if x.book_id is None and journalIdABC and x.journal_id != journalIdABC:
        message = message + "JOURNAL_ID updated from '{}' to '{}'. ".format(x.journal_id, journalIdABC)
        x.journal_id = journalIdABC
    if message:
        nex_session.add(x)
        fw.write("PMID:{}: REFERENCE table updated: See details: {}\n".format(x.pmid, message))


def update_urls(nex_session, fw, pmid, reference_id, doi, pmcid, urls_in_db, source_id):
    doi_url = DOI_ROOT + doi if doi else None
    doi_url = doi_url.replace("&lt;", "<").replace("&gt;", ">") if doi_url else None
    pmc_url = PMC_ROOT + pmcid + '/' if pmcid else None

    if pmc_url is None and doi_url is None:
        return

    if urls_in_db is None:
        urls_in_db = []
    pmc_url_db = None
    doi_url_db = None
    for (type, url) in urls_in_db:
        if type == DOI_URL_TYPE:
            doi_url_db = url
        if type == PMC_URL_TYPE:
            pmc_url_db = url

    pmc_url_changed = 0
    doi_url_changed = 0

    if pmc_url:
        if pmc_url_db is None:
            ru = ReferenceUrl(
                display_name=PMC_URL_TYPE,
                obj_url=pmc_url,
                source_id=source_id,
                reference_id=reference_id,
                url_type=PMC_URL_TYPE,
                created_by=CREATED_BY
            )
            nex_session.add(ru)
            pmc_url_changed = 1
        elif pmc_url != pmc_url_db:
            ru = nex_session.query(ReferenceUrl).filter_by(reference_id=reference_id, url_type=PMC_URL_TYPE).one_or_none()
            if ru:
                ru.obj_url = pmc_url
                nex_session.add(ru)
                pmc_url_changed = 1

    if doi_url:
        if doi_url_db is None:
            ru = ReferenceUrl(
                display_name=DOI_URL_TYPE,
                obj_url=doi_url,
                source_id=source_id,
                reference_id=reference_id,
                url_type=DOI_URL_TYPE,
                created_by=CREATED_BY
            )
            nex_session.add(ru)
            doi_url_changed = 1
        elif doi_url != doi_url_db:
            ru = nex_session.query(ReferenceUrl).filter_by(reference_id=reference_id, url_type=DOI_URL_TYPE).one_or_none()
            if ru:
                ru.obj_url = doi_url
                nex_session.add(ru)
                doi_url_changed = 1

    if pmc_url_changed == 1:
        fw.write("PMID:{}: the PMC URL is updated. New URL: {} Old URL: {}\n".format(pmid, pmc_url, pmc_url_db))
    if doi_url_changed == 1:
        fw.write("PMID:{}: the DOI URL is updated. New URL: {} Old URL: {}\n".format(pmid, doi_url, doi_url_db))


def update_abstract(nex_session, fw, pmid, reference_id, abstractDB, abstractABC, source_id):
    if abstractABC is None or abstractABC == '' or abstractDB == abstractABC:
        return

    html = link_gene_names(abstractABC, {}, nex_session)

    logger.info("PMID:{}: old_abstract={}\n".format(pmid, abstractDB))
    logger.info("PMID:{}: new_abstract={}\n".format(pmid, abstractABC))
    logger.info("PMID:{}: new_html    ={}\n".format(pmid, html))

    if abstractDB == '':
        x = Referencedocument(
            document_type='Abstract',
            source_id=source_id,
            reference_id=reference_id,
            text=abstractABC,
            html=html,
            created_by=CREATED_BY
        )
        nex_session.add(x)
        fw.write("PMID:{}: new abstract added. New abstract: {}\n".format(pmid, abstractABC))
    else:
        x = nex_session.query(Referencedocument).filter_by(reference_id=reference_id, document_type='Abstract').one_or_none()
        if x:
            x.text = abstractABC
            x.html = html
            nex_session.add(x)
        fw.write("PMID:{}: the abstract is updated. New abstract: \"{}\"\n".format(pmid, abstractABC))
        fw.write("PMID:{}: the abstract is updated. Old abstract: \"{}\"\n".format(pmid, abstractDB))
        fw.write("PMID:{}: the abstract is updated. New html:     \"{}\"\n".format(pmid, html))


def update_comments_corrections(nex_session, fw, pmid, source_id, comment_corrections_from_ABC):
    if len(comment_corrections_from_ABC) == 0:
        return

    for (parent_id, child_id, type) in comment_corrections_from_ABC:
        found = 0
        foundRelation = {}
        for rr in get_parent(nex_session, child_id):
            foundRelation[rr[0]] = 1
            if rr[2] == type and rr[1] == parent_id:
                found = 1
                continue
            elif rr[1] == parent_id:
                update_reference_relation_type(nex_session, fw, pmid, parent_id, child_id, type)
                found = 1
            else:
                logger.info("PMID:{}: only in sgd {}, {}".format(pmid, rr[1], rr[2]))

        for rr in get_child(nex_session, parent_id):
            if rr[0] in foundRelation:
                continue
            if rr[2] == type and rr[1] == child_id:
                found = 1
            elif rr[1] == child_id:
                update_reference_relation_type(nex_session, fw, pmid, parent_id, child_id, type)
                found = 1

        if found == 0:
            add_new_reference_relation(nex_session, fw, pmid, source_id, parent_id, child_id, type)


def add_new_reference_relation(nex_session, fw, pmid, source_id, parent_id, child_id, type):
    x = nex_session.query(ReferenceRelation).filter_by(parent_id=parent_id, child_id=child_id, relation_type=type).one_or_none()
    if x:
        return
    x = ReferenceRelation(
        source_id=source_id,
        parent_id=parent_id,
        child_id=child_id,
        relation_type=type,
        created_by=CREATED_BY
    )
    nex_session.add(x)
    fw.write("PMID:{}: new reference_relation added. parent_id = {}, ".format(pmid, parent_id))
    fw.write("child_id = {}, relation_type = {}\n".format(child_id, type))


def update_reference_relation_type(nex_session, fw, pmid, parent_id, child_id, newType):
    x = nex_session.query(ReferenceRelation).filter_by(parent_id=parent_id, child_id=child_id).one_or_none()
    if x:
        x.relation_type = newType
        nex_session.add(x)
        fw.write("PMID:{}: the relation_type is updated to {} ".format(pmid, newType))
        fw.write("for parent_id = {} and child_id = {}\n".format(parent_id, child_id))


def get_parent(nex_session, reference_id):
    rows = nex_session.execute(
        "SELECT reference_relation_id, parent_id, relation_type "
        "FROM nex.reference_relation "
        "WHERE child_id = {}".format(reference_id)
    ).fetchall()
    return rows


def get_child(nex_session, reference_id):
    rows = nex_session.execute(
        "SELECT reference_relation_id, child_id, relation_type "
        "FROM nex.reference_relation "
        "WHERE parent_id = {}".format(reference_id)
    ).fetchall()
    return rows


def convert_publication_status(pubStatus):
    if pubStatus in ['ppublish', 'epublish']:
        return 'Published'
    elif pubStatus == 'aheadofprint':
        return 'Epub ahead of print'
    else:
        return pubStatus


def remove_html_tags(text):
    if '</' not in text:
        return text
    return BeautifulSoup(text, "lxml").text


def cleanup_text(text):
    text = text.replace("\\xa0", " ")
    text = text.replace("\\u2002", " ")
    text = text.replace("\\u2005", " ")
    text = text.replace("\\u2008", " ")
    text = text.replace("\\u2009", " ")
    text = text.replace("\\u2028", " ")
    text = text.replace("\\u202f", " ")
    text = text.replace("\\u200b", " ")
    text = text.replace("\\", "")
    return text


def get_reference_id_by_pmid(nex_session, pmid: int) -> Optional[int]:
    """
    On-demand PMID -> dbentity_id lookup for comment/corrections cross-refs.
    """
    try:
        rid = nex_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == pmid).scalar()
        return int(rid) if rid else None
    except Exception:
        return None


def parse_process_json_data(
    json_data: dict,
    pmid: int,
    pmid_to_reference_id_cache: Dict[int, int],
    nex_session,
    journalIdDB,
    journal_abbr_to_journal_id,
    journal_name_to_journal_id
):
    title = json_data.get('title', '')
    if title is None:
        title = ''
    title = title.replace("\\'", "'")

    year = json_data.get('date_published', '')
    if year is None:
        year = ''
    elif year:
        year = int(year[0:4])

    volume = json_data['volume'] if 'volume' in json_data else ''
    if volume is None:
        volume = ''

    issue = json_data['issue_name'] if 'issue_name' in json_data else ''
    if issue is None:
        issue = ''

    page = json_data['page_range'] if 'page_range' in json_data else ''
    if page is None:
        page = ''

    doi = None
    pmcid = None
    if "cross_references" in json_data:
        for cr in json_data['cross_references']:
            if cr['curie'].startswith('DOI:'):
                doi = cr['curie'].replace('DOI:', '')
            if cr['curie'].startswith('PMCID:'):
                pmcid = cr['curie'].replace('PMCID:', '')

    pubStatus = json_data['pubmed_publication_status'] if 'pubmed_publication_status' in json_data else ''
    if pubStatus is None:
        pubStatus = ''
    else:
        pubStatus = convert_publication_status(pubStatus)

    pubmedTypes = json_data.get('pubmed_types', [])
    pubmedTypes.sort()

    abstract = json_data.get('abstract', '')
    if abstract is None:
        abstract = ''
    abstract = abstract.replace("\\'", "'")

    authors = []
    author_list = []
    author_order = 0

    for author in json_data.get('authors', []):
        author_name = author.get('name', '')
        if 'last_name' in author and author['last_name'] and 'first_initial' in author and author['first_initial']:
            author_name = author['last_name'] + " " + author['first_initial']
        author_list.append(author_name.strip())
        orcid = author['orcid'].replace("ORCID:", "") if 'orcid' in author and author['orcid'] else ''
        author_order += 1
        authors.append((author_name.strip(), orcid, author_order))

    journalAbbr = json_data.get('resource_medline_abbreviation', '')
    journalName = json_data.get('resource_title', '')
    journalId = journal_abbr_to_journal_id.get(journalAbbr)
    journalId2 = journal_name_to_journal_id.get(journalName)
    if journalId2 and journalId2 == journalIdDB:
        journalId = journalId2

    commentCorrections = []
    if 'comment_and_corrections' in json_data and len(json_data['comment_and_corrections']) > 0:
        comments = json_data['comment_and_corrections']
        for type in comments:
            for x in comments[type]:
                pmid2 = int(x['PMID'].replace('PMID:', ''))

                # Resolve pmid2 -> reference_id (dbentity_id) with cache + on-demand DB lookup
                if pmid2 not in pmid_to_reference_id_cache:
                    rid = get_reference_id_by_pmid(nex_session, pmid2)
                    if rid:
                        pmid_to_reference_id_cache[pmid2] = rid

                if pmid2 in pmid_to_reference_id_cache and pmid in pmid_to_reference_id_cache:
                    parent_id = None
                    child_id = None
                    if type.endswith('In'):
                        parent_id = pmid_to_reference_id_cache[pmid]
                        child_id = pmid_to_reference_id_cache[pmid2]
                    else:
                        parent_id = pmid_to_reference_id_cache[pmid2]
                        child_id = pmid_to_reference_id_cache[pmid]

                    if type.startswith("Erratum"):
                        type_norm = "Erratum"
                    elif type.startswith("Comment"):
                        type_norm = "Comment"
                    elif type.startswith("Republished"):
                        type_norm = "Corrected and Republished"
                    elif type.startswith('Retraction'):
                        type_norm = "Retraction"
                    elif type.startswith('ExpressionOfConcern'):
                        type_norm = "ExpressionOfConcern"
                    elif type.startswith('Update'):
                        type_norm = "Update"
                    else:
                        type_norm = type

                    commentCorrections.append((parent_id, child_id, type_norm))

    citation = set_cite(title, author_list, year, journalAbbr, volume, issue, page)

    return (
        title, year, volume, issue, page, doi, pmcid, pubStatus, citation,
        journalId, authors, pubmedTypes, abstract, commentCorrections
    )


if __name__ == '__main__':
    update_data()
