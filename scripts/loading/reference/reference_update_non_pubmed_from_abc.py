#!/usr/bin/env python3
"""
Update non-PubMed references in SGD from ABC reference_SGD.json.gz.

Definition of "non-PubMed" here:
  - ABC JSON record has at least one SGD curie (SGD:...)
  - ABC JSON record has NO PMID:... cross_reference
  - Local Referencedbentity row has pmid IS NULL

We match:
  ABC MOD curie: 'SGD:S100001513'
  DB sgdid:      'S100001513'  (stored on Referencedbentity via Dbentity.sgdid)
"""

import sys
import re
from datetime import datetime
from os import environ
import logging
import gzip

import ujson
from bs4 import BeautifulSoup
import boto3
from botocore.exceptions import ClientError

from src.models import (
    Dbentity,
    Referencedbentity,
    Referenceauthor,
    ReferenceUrl,
    Referencetype,
    Journal,
    Source,
    Referencedocument,
)
from scripts.loading.database_session import get_session
# reuse existing citation builder
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

MOD_PREFIX = 'SGD'  # ABC curies start with 'SGD:'
limit = 2500
loop_count = 60
max_session = 10000
max_commit = 100

json_file = 'reference_SGD.json.gz'
bucketname = 'agr-literature'
s3_file_location = 'prod/reference/dumps/latest/' + json_file
log_file = "scripts/loading/reference/logs/reference_update_from_abc_non_pubmed.log"

# Reset handlers (for Fargate / Lambda style environments)
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)

logging.basicConfig(
    format='%(message)s',
    handlers=[
        logging.FileHandler(environ['LOG_FILE']),
        logging.StreamHandler(sys.stderr)
    ],
    level=logging.INFO
)


def _parse_author_for_citation(author):
    """
    Convert various author name formats into 'Lastname Initials'.

    - If the name is already in 'Lastname Initials' form (e.g., 'Gros J'),
      return as-is.
    - If the name is like 'Bart Deplancke' → 'Deplancke B'
    - If the name is like 'M F Bauer'     → 'Bauer MF'
    - If the name is like 'H Efsun Arda'  → 'Arda HE'
    """
    author = author.strip().rstrip(',')
    if not author:
        return ""

    parts = author.split()

    # --- CASE 1: Already 'Lastname Initials' ---
    # Pattern: <LastName> <1–3 initials> (e.g., "Gros J", "Smith AB", "Deplancke B")
    if (
        len(parts) == 2
        and re.fullmatch(r"[A-Za-z][A-Za-z\-'’]*", parts[0])           # Last name
        and re.fullmatch(r"[A-Z](?:[A-Z])?", parts[1])                 # Initials, 1–2 letters
    ):
        return author   # SAFE: already formatted correctly

    # --- CASE 2: Multi-initial prefix + last name ---
    # Example: "M F Bauer" → initials = ["M","F"], last="Bauer"
    if len(parts) > 2 and all(len(p) == 1 and p.isalpha() and p.isupper() for p in parts[:-1]):
        last = parts[-1]
        initials = "".join(parts[:-1])
        return f"{last} {initials}"

    # --- CASE 3: First name(s) then last name ---
    # Example: "H Efsun Arda" → last="Arda", initials="H"+"E"
    last = parts[-1]
    initials = "".join([p[0].upper() for p in parts[:-1] if p])
    return f"{last} {initials}"


def generate_citation_and_display_name_from_citation(citation):
    """
    From a full citation like:
        'Bart Deplancke; Vanessa Vermeirssen, (2006) ...'
    generate:
        new_citation: 'Deplancke B, et al. (2006) ...'
        display_name: 'Deplancke B, et al. (2006)'

    If parsing fails, returns (None, None).
    """
    if not citation:
        return None, None

    m = re.search(r"\(\s*\d{4}\s*\)", citation)
    if not m:
        return None, None

    year_str = m.group(0).strip("()")

    authors_part = citation[:m.start()].strip().rstrip(",")
    rest = citation[m.end():].lstrip()

    raw_authors = [a.strip() for a in authors_part.split(";") if a.strip()]
    if not raw_authors:
        return None, None

    parsed_authors = [_parse_author_for_citation(a) for a in raw_authors]

    if len(parsed_authors) == 1:
        author_str = parsed_authors[0]
    elif len(parsed_authors) == 2:
        author_str = f"{parsed_authors[0]} and {parsed_authors[1]}"
    else:
        author_str = f"{parsed_authors[0]}, et al."

    new_citation = f"{author_str} ({year_str}) {rest}"
    display_name = f"{author_str} ({year_str})"

    return new_citation, display_name


def update_non_pubmed_data():
    logger.info("Downloading ABC reference_SGD.json file for non-PubMed refs...")
    logger.info(datetime.now())

    download_reference_json_file_from_alliance_s3()

    logger.info("Reading ABC reference_SGD.json file (non-PubMed)...")
    logger.info(datetime.now())

    # JSON: sgdid (without 'SGD:') -> JSON blob for non-PubMed records
    sgdid_to_json_data = read_reference_data_from_abc_non_pubmed()

    nex_session = get_session()

    source_to_id = dict(
        (x.display_name, x.source_id) for x in nex_session.query(Source).all()
    )
    source_id = source_to_id[SRC]

    logger.info("Getting data from Referenceauthor table...")
    logger.info(datetime.now())
    reference_id_to_authors = retrieve_author_data(nex_session)

    logger.info("Getting data from Reference_url table...")
    logger.info(datetime.now())
    reference_id_to_urls = retrieve_urls(nex_session)

    logger.info("Getting data from journal table...")
    logger.info(datetime.now())
    journal_abbr_to_journal_id = dict(
        (x.med_abbr, x.journal_id) for x in nex_session.query(Journal).all()
    )
    journal_name_to_journal_id = dict(
        (x.display_name, x.journal_id) for x in nex_session.query(Journal).all()
    )

    logger.info("Getting data from referencedocument table...")
    logger.info(datetime.now())
    reference_id_to_abstract = retrieve_abstracts(nex_session)

    fw = open(log_file, "w")

    i = 0

    for index in range(loop_count):
        offset = index * limit

        if i != 0 and i % max_session == 0:
            nex_session.commit()
            nex_session.close()
            nex_session = get_session()

        # non-PubMed: pmid IS NULL
        rows = (
            nex_session.query(Referencedbentity)
            .filter(Referencedbentity.pmid.is_(None))
            .order_by(Referencedbentity.dbentity_id)
            .offset(offset)
            .limit(limit)
            .all()
        )

        if len(rows) == 0:
            break

        for ref in rows:
            sgdid = getattr(ref, "sgdid", None)
            if not sgdid:
                continue

            if sgdid not in sgdid_to_json_data:
                logger.info(
                    "Non-PubMed paper in SGD: sgdid {} (dbentity_id={}) not in ABC non-PubMed JSON".format(
                        sgdid, ref.dbentity_id
                    )
                )
                continue

            if i != 0 and i % max_commit == 0:
                nex_session.commit()
            i += 1

            ident = "SGD:" + sgdid  # used in logs / file

            logger.info(
                "processing non-PubMed ref: {}: sgdid:{} dbentity_id:{}".format(
                    i, sgdid, ref.dbentity_id
                )
            )

            json_data = sgdid_to_json_data[sgdid]

            try:
                (
                    titleABC,
                    yearABC,
                    volumeABC,
                    issueABC,
                    pageABC,
                    doiABC,
                    pmcidABC,
                    pubStatusABC,
                    citationABC,
                    journalIdABC,
                    authorsABC,
                    abstractABC,
                ) = parse_process_json_data(
                    json_data,
                    ref.journal_id,
                    journal_abbr_to_journal_id,
                    journal_name_to_journal_id,
                )
            except Exception as e:
                logger.info(
                    "Error parsing json data for non-PubMed sgdid:{} (dbentity_id={}). "
                    "See details: {}".format(sgdid, ref.dbentity_id, e)
                )
                continue

            print(sgdid, "citationCleaned=", citationABC)
            
            # continue
            
            try:
                update_reference_table(
                    nex_session,
                    fw,
                    ident,
                    ref,
                    titleABC,
                    yearABC,
                    volumeABC,
                    issueABC,
                    pageABC,
                    doiABC,
                    pmcidABC,
                    pubStatusABC,
                    citationABC,
                    journalIdABC,
                )

                update_authors(
                    nex_session,
                    fw,
                    ident,
                    ref.dbentity_id,
                    reference_id_to_authors.get(ref.dbentity_id, []),
                    authorsABC,
                    source_id,
                )

                update_abstract(
                    nex_session,
                    fw,
                    ident,
                    ref.dbentity_id,
                    reference_id_to_abstract.get(ref.dbentity_id, ""),
                    abstractABC,
                    source_id,
                )

                update_urls(
                    nex_session,
                    fw,
                    ident,
                    ref.dbentity_id,
                    doiABC,
                    pmcidABC,
                    reference_id_to_urls.get(ref.dbentity_id, []),
                    source_id,
                )

            except Exception as e:
                logger.info(
                    "Error updating data for non-PubMed sgdid:{} (dbentity_id={}). "
                    "See details: {}".format(sgdid, ref.dbentity_id, e)
                )
                continue

    nex_session.commit()
    nex_session.close()
    fw.close()
    logger.info("DONE non-PubMed update!")
    logger.info(datetime.now())


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


def update_orcid(nex_session, fw, ident, reference_id, author2orcidDB, author2orcidABC):
    for (author, order) in author2orcidDB:
        orcidDB = author2orcidDB[(author, order)]
        orcidABC = author2orcidABC[(author, order)]
        if orcidABC != '' and orcidABC != orcidDB:
            logger.info(
                "{}: The orcid for {} (author_order={}): new_orcid={}, old_orcid={}".format(
                    ident, author, order, orcidABC, orcidDB
                )
            )
            x = nex_session.query(Referenceauthor).filter_by(
                reference_id=reference_id, display_name=author, author_order=order
            ).one_or_none()
            if x:
                x.orcid = orcidABC
                nex_session.add(x)
                fw.write(
                    "{}: The orcid for {} (author_order={}) has been updated from {} to {}.\n".format(
                        ident, author, order, orcidDB, orcidABC
                    )
                )


def update_authors(nex_session, fw, ident, reference_id,
                   authorsDBwithOrcid, authorsABCwithOrcid, source_id):

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
        # only ORCID info changed
        update_orcid(nex_session, fw, ident, reference_id, author2orcidDB, author2orcidABC)
        return

    logger.info("{}: old_authors={}".format(ident, authorsDB))
    logger.info("{}: new_authors={}".format(ident, authorsABC))

    # delete old ones
    for ra in nex_session.query(Referenceauthor).filter_by(
        reference_id=reference_id
    ).order_by(Referenceauthor.author_order).all():
        logger.info("{}: deleting old author {}".format(ident, ra.display_name))
        nex_session.delete(ra)
        nex_session.flush()

    # add new ones
    for (author_name, orcid, author_order) in authorsABCwithOrcid:
        logger.info("{}: adding new author {}, {}".format(ident, author_name, author_order))
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

    fw.write("{}: The author(s) in Referenceauthor table are updated.\n".format(ident))


def update_reference_table(nex_session, fw, ident, x, titleABC, yearABC, volumeABC,
                           issueABC, pageABC, doiABC, pmcidABC, pubStatusABC,
                           citationABC, journalIdABC):

    message = ''

    # NEW: derive new_citation + display_name from citationABC
    new_citation, new_display_name = generate_citation_and_display_name_from_citation(
        citationABC
    )
    citation_to_use = new_citation if new_citation else citationABC
    print(ident, "citation_to_use=", citation_to_use)
    print(ident, "display_name=", new_display_name)
    
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
        message = message + "PUBLICATION_STATUS updated from '{}' to '{}'. ".format(
            x.publication_status, pubStatusABC
        )
        x.publication_status = pubStatusABC

    # Use newly formatted citation
    if citation_to_use and x.citation != citation_to_use:
        message = message + "CITATION updated from '{}' to '{}'. ".format(
            x.citation, citation_to_use
        )
        x.citation = citation_to_use

    if x.book_id is None and journalIdABC and x.journal_id != journalIdABC:
        message = message + "JOURNAL_ID updated from '{}' to '{}'. ".format(
            x.journal_id, journalIdABC
        )
        x.journal_id = journalIdABC

    # NEW: update Dbentity.display_name based on new_display_name
    if new_display_name:
        dbentity_row = nex_session.query(Dbentity).filter_by(
            dbentity_id=x.dbentity_id
        ).one_or_none()
        if dbentity_row and dbentity_row.display_name != new_display_name:
            message = message + "DBENTITY.DISPLAY_NAME updated from '{}' to '{}'. ".format(
                dbentity_row.display_name, new_display_name
            )
            dbentity_row.display_name = new_display_name
            nex_session.add(dbentity_row)

    if message:
        nex_session.add(x)
        fw.write(
            "{}: REFERENCE table updated: See details: {}\n".format(ident, message)
        )


def update_urls(nex_session, fw, ident, reference_id, doi, pmcid, urls_in_db, source_id):

    doi_url = DOI_ROOT + doi if doi else None
    doi_url = doi_url.replace("&lt;", "<").replace("&gt;", ">") if doi_url else None
    pmc_url = PMC_ROOT + pmcid + '/' if pmcid else None

    if pmc_url is None and doi_url is None:
        return

    if urls_in_db is None:
        urls_in_db = []
    pmc_url_db = None
    doi_url_db = None
    for (t, url) in urls_in_db:
        if t == DOI_URL_TYPE:
            doi_url_db = url
        if t == PMC_URL_TYPE:
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
            ru = nex_session.query(ReferenceUrl).filter_by(
                reference_id=reference_id, url_type=PMC_URL_TYPE
            ).one_or_none()
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
            ru = nex_session.query(ReferenceUrl).filter_by(
                reference_id=reference_id, url_type=DOI_URL_TYPE
            ).one_or_none()
            if ru:
                ru.obj_url = doi_url
                nex_session.add(ru)
                doi_url_changed = 1

    if pmc_url_changed == 1:
        fw.write(
            "{}: the PMC URL is updated. New URL: {} Old URL: {}\n".format(
                ident, pmc_url, pmc_url_db
            )
        )
    if doi_url_changed == 1:
        fw.write(
            "{}: the DOI URL is updated. New URL: {} Old URL: {}\n".format(
                ident, doi_url, doi_url_db
            )
        )


def update_abstract(nex_session, fw, ident, reference_id,
                    abstractDB, abstractABC, source_id):

    if abstractABC is None or abstractABC == '' or abstractDB == abstractABC:
        return

    html = link_gene_names(abstractABC, {}, nex_session)

    logger.info("{}: old_abstract={}\n".format(ident, abstractDB))
    logger.info("{}: new_abstract={}\n".format(ident, abstractABC))
    logger.info("{}: new_html    ={}\n".format(ident, html))

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
        fw.write(
            "{}: new abstract added. New abstract: {}\n".format(ident, abstractABC)
        )
    else:
        x = nex_session.query(Referencedocument).filter_by(
            reference_id=reference_id, document_type='Abstract'
        ).one_or_none()
        if x:
            x.text = abstractABC
            x.html = html
            nex_session.add(x)
        fw.write(
            "{}: the abstract is updated. New abstract: \"{}\"\n".format(
                ident, abstractABC
            )
        )
        fw.write(
            "{}: the abstract is updated. Old abstract: \"{}\"\n".format(
                ident, abstractDB
            )
        )
        fw.write(
            "{}: the abstract is updated. New html:     \"{}\"\n".format(
                ident, html
            )
        )


def retrieve_urls(nex_session):
    reference_id_to_urls = {}
    for x in nex_session.query(ReferenceUrl).all():
        urls = reference_id_to_urls.get(x.reference_id, [])
        urls.append((x.url_type, x.obj_url))
        reference_id_to_urls[x.reference_id] = urls
    return reference_id_to_urls


def retrieve_abstracts(nex_session):
    reference_id_to_abstract = {}
    for x in nex_session.query(Referencedocument).filter_by(document_type='Abstract').all():
        reference_id_to_abstract[x.reference_id] = x.text
    return reference_id_to_abstract


def retrieve_author_data(nex_session):
    allAuthors = nex_session.query(Referenceauthor).order_by(
        Referenceauthor.reference_id, Referenceauthor.author_order
    ).all()
    reference_id_to_authors = {}
    for x in allAuthors:
        authors = reference_id_to_authors.get(x.reference_id, [])
        orcid = x.orcid if x.orcid else ''
        authors.append((x.display_name, orcid, x.author_order))
        reference_id_to_authors[x.reference_id] = authors
    return reference_id_to_authors


def read_reference_data_from_abc_non_pubmed(mod_prefix=MOD_PREFIX):
    """
    Return a dict mapping sgdid (without 'SGD:' prefix) -> JSON object
    for references that:
      - have at least one MOD curie starting with 'SGD:'
      - and DO NOT have a PMID cross_reference (non-PubMed).
    """
    with gzip.open(json_file, 'rb') as f:
        json_str = f.read()
        json_data = ujson.loads(json_str)

    sgdid_to_json_data = {}

    for x in json_data.get('data', []):
        if "cross_references" not in x:
            continue

        has_pmid = False
        mod_ids = []

        for c in x['cross_references']:
            if c.get('is_obsolete'):
                continue
            curie = c.get('curie', '')
            if curie.startswith('PMID:'):
                has_pmid = True
            elif curie.startswith(mod_prefix + ":"):
                sgdid = curie.split(":", 1)[1]  # strip 'SGD:'
                mod_ids.append(sgdid)

        # keep only non-PubMed
        if has_pmid:
            continue

        for sgdid in mod_ids:
            sgdid_to_json_data[sgdid] = x

    return sgdid_to_json_data


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


def parse_process_json_data(json_data, journalIdDB,
                            journal_abbr_to_journal_id, journal_name_to_journal_id):
    """
    Variant of parse_process_json_data that does NOT use pmid/comment_corrections
    and ignores pubmed_types, suitable for non-PubMed references.
    """

    title = json_data.get('title', '')
    if title is None:
        title = ''
    title = title.replace("\\'", "'")

    date_published = json_data.get('date_published', '')
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

    abstract = json_data.get('abstract', '')
    if abstract is None:
        abstract = ''
    abstract = abstract.replace("\\'", "'")

    authors = []
    author_list = []
    author_order = 0
    for author in json_data.get('authors', []):
        author_name = author['name']
        if 'last_name' in author and author['last_name'] and \
           'first_initial' in author and author['first_initial']:
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

    # citation = set_cite(title, author_list, year, journalAbbr, volume, issue, page)
    citation = json_data.get('citation', '')
    citation = re.sub(r"\s+", " ", citation)
    
    return (
        title,
        year,
        volume,
        issue,
        page,
        doi,
        pmcid,
        pubStatus,
        citation,
        journalId,
        authors,
        abstract,
    )


if __name__ == '__main__':
    update_non_pubmed_data()
