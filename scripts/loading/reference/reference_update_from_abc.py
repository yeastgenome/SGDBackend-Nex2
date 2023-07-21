import sys
from src.models import Referencedbentity, Referenceauthor, ReferenceUrl, Referencetype, \
                       Journal, Source, Referencedocument, ReferenceRelation
from scripts.loading.database_session import get_session
from scripts.loading.reference.pubmed import set_cite
from scripts.loading.util import link_gene_names
import json
from datetime import datetime
from bs4 import BeautifulSoup
from os import environ
import boto3
from botocore.exceptions import ClientError
import logging
import gzip

__author__ = 'sweng66'

CREATED_BY = 'OTTO'
SRC = 'NCBI'
AUTHOR_TYPE = 'Author'
PMC_URL_TYPE = 'PMC full text'
DOI_URL_TYPE = 'DOI full text'
PMC_ROOT = 'http://www.ncbi.nlm.nih.gov/pmc/articles/'
DOI_ROOT = 'http://dx.doi.org/'
AWS_REGION = 'us-east-1'

limit = 2500
loop_count = 60
max_session = 10000
max_commit = 100

json_file = 'reference_SGD.json.gz'
bucketname = 'agr-literature'
s3_file_location = 'prod/reference/dumps/latest/' + json_file
log_file = "scripts/loading/reference/logs/reference_update_from_abc.log"

# Handlers need to be reset for use under Fargate. See
# https://stackoverflow.com/questions/37703609/using-python-logging-with-aws-lambda/56579088#56579088
# for details.  Applies to Fargate in addition to Lambda.

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

def update_data():

    logger.info("Downloading ABC reference_SGD.json file...")
    logger.info(datetime.now())
    
    download_reference_json_file_from_alliance_s3()

    logger.info("Reading ABC reference_SGD.json file...")
    logger.info(datetime.now())

    pmid_to_json_data = read_reference_data_from_abc()

    #################################################################
    nex_session = get_session()

    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()])
    
    logger.info("Getting data from Referenceauthor table...")
    logger.info(datetime.now())
    reference_id_to_authors = retrieve_author_data(nex_session)
    
    logger.info("Getting data from Referencetype table...")
    logger.info(datetime.now())
    reference_id_to_types = retrieve_pubmed_types(nex_session)

    logger.info("Getting data from Reference_url table...")
    logger.info(datetime.now())
    reference_id_to_urls = retrieve_urls(nex_session)

    logger.info("Getting data from journal table...")
    logger.info(datetime.now())
    journal_abbr_to_journal_id = dict([(x.med_abbr, x.journal_id) for x in nex_session.query(Journal).all()])
    journal_name_to_journal_id = dict([(x.display_name, x.journal_id) for x in nex_session.query(Journal).all()])
    
    logger.info("Getting data from referencedocument table...")
    logger.info(datetime.now())

    reference_id_to_abstract = retrieve_abstracts(nex_session)
    
    pmid_to_reference_id = dict([(x.pmid, x.dbentity_id) for x in nex_session.query(Referencedbentity).all()])

    source_id = source_to_id[SRC]

    fw = open(log_file, "w")
    
    i = 0
    
    for index in range(loop_count):

        offset = index * limit

        ## for testing
        # offset += 43036
        # if i == 0:
        #    i += 43036
        ## end of testing
            
        if i != 0 and i % max_session == 0:
            nex_session.commit()
            # nex_session.rollback()
            nex_session.close()
            nex_session = get_session()

        rows = nex_session.query(Referencedbentity).filter(Referencedbentity.pmid.isnot(None)).order_by(
            Referencedbentity.dbentity_id).offset(offset).limit(limit).all()
        if len(rows) == 0:
            break
        
        for x in rows:

            if x.pmid not in pmid_to_json_data:
                logger.info("PubMed paper in SGD: PMID:" + str(x.pmid) + " not in ABC")
                continue
        
            if i != 0 and i % max_commit == 0:
                nex_session.commit()
                # nex_session.rollback()
            i += 1
            
            # The f-string syntax, which allows you to embed expressions inside
            # string literals using curly braces {}, was introduced in Python 3.6.
            # Therefore, it is not supported in Python 3.5 and our system still has
            # python 3.5 =(
            
            # logger.info(f"processing ref: {i}: PMID:{x.pmid}")
            logger.info("processing ref: {}: PMID:{}".format(i, x.pmid))
            
            json_data = pmid_to_json_data.get(x.pmid, {})
            
            try:
                (titleABC, yearABC, volumeABC, issueABC, pageABC, doiABC, pmcidABC, pubStatusABC, \
                 citationABC, journalIdABC, authorsABC, pubmedTypesABC, abstractABC, \
                 commentCorrectionsABC) = parse_process_json_data(json_data, x.pmid,
                                                                  pmid_to_reference_id,
                                                                  x.journal_id,
                                                                  journal_abbr_to_journal_id,
                                                                  journal_name_to_journal_id)
    
            except Exception as e:
                # logger.info(f"Error parsing json data for PMID:{x.pmid}. See details: {e}")
                logger.info("Error parsing json data for PMID:{}. See details: {}".format(x.pmid, e))
                continue

            try:
                update_reference_table(nex_session, fw, x, titleABC, yearABC, volumeABC,
                                       issueABC, pageABC, doiABC, pmcidABC, pubStatusABC,
                                       citationABC, journalIdABC)

                update_authors(nex_session, fw, x.pmid, x.dbentity_id,
                               reference_id_to_authors.get(x.dbentity_id, []),
                               authorsABC, source_id)
            
                update_pubmedTypes(nex_session, fw, x.pmid, x.dbentity_id,
                                   reference_id_to_types.get(x.dbentity_id, []),
                                   pubmedTypesABC, source_id)
        
                update_abstract(nex_session, fw, x.pmid, x.dbentity_id,
                                reference_id_to_abstract.get(x.dbentity_id, ''),
                                abstractABC, source_id)
        
                update_urls(nex_session, fw, x.pmid, x.dbentity_id, doiABC, pmcidABC,
                            reference_id_to_urls.get(x.dbentity_id, []),
                            source_id)

                update_comments_corrections(nex_session, fw, x.pmid, source_id, commentCorrectionsABC)
                
            except Exception as e:
                logger.info("Error updating data for PMID:{}. See details: {}".format(x.pmid, e))
                pass

    nex_session.commit()
    # nex_session.rollback()
    nex_session.close()
    fw.close()
    logger.info("DONE!")
    logger.info(datetime.now())


def download_reference_json_file_from_alliance_s3():
    
    s3_client = boto3.client('s3',
                             region_name=AWS_REGION,
                             aws_access_key_id=environ['ABC_AWS_ACCESS_KEY_ID'],
                             aws_secret_access_key=environ['ABC_AWS_SECRET_ACCESS_KEY'])
    try:
        response = s3_client.download_file(bucketname, s3_file_location, json_file)
        if response is not None:
            logger.info("boto3 downloaded response: %s", response)
    except ClientError as e:
        logging.error(e)
        return False


def update_orcid(nex_session, fw, pmid, reference_id, author2orcidDB, author2orcidABC):

    for (author, order) in author2orcidDB:
        orcidDB = author2orcidDB[(author, order)]
        orcidABC = author2orcidABC[(author, order)]
        if orcidABC != '' and orcidABC != orcidDB:
            
            # logger.info(f"PMID:{pmid}: The orcid for {author} (author_order={order}): new_orcid={orcidABC}, old_orcid={orcidDB}")
            logger.info("PMID:{}: The orcid for {} (author_order={}): new_orcid={}, old_orcid={}".format(pmid, author, order, orcidABC, orcidDB))
            x = nex_session.query(Referenceauthor).filter_by(
                reference_id=reference_id, display_name=author, author_order=order).one_or_none()
            if x:
                x.orcid = orcidABC
                nex_session.add(x)
                fw.write("PMID:{}: The orcid for {} (author_order={}) has been updated from {} to {}.\n".format(pmid, author, order, orcidABC, orcidDB))
               
        
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
    for	(authorName, orcid, order) in authorsABCwithOrcid:
        authorsABC.append((authorName, order))
        author2orcidABC[(authorName, order)] = orcid

    if authorsDB == authorsABC:
        ## that means only thing changed is orcid info
        update_orcid(nex_session, fw, pmid, reference_id, author2orcidDB, author2orcidABC)
        return

    logger.info("PMID:{}: old_authors={}".format(pmid, authorsDB))
    logger.info("PMID:{}: new_authors={}".format(pmid, authorsABC))
    
    ## delete old ones
    for ra in nex_session.query(Referenceauthor).filter_by(reference_id=reference_id).order_by(Referenceauthor.author_order).all():
        logger.info("PMID:{}: deleting old author {}".format(pmid, ra.display_name))
        nex_session.delete(ra)
        nex_session.flush()
        
    ## add new ones
    for (author_name, orcid, author_order) in authorsABCwithOrcid:
        logger.info("PMID:{}: adding new author {}, {}".format(pmid, author_name, author_order)) 
        ra = Referenceauthor(display_name = author_name,
                             source_id = source_id,
                             orcid = orcid if orcid else None,
                             obj_url = '/author/' + author_name.replace(' ', '_'),
                             reference_id = reference_id,
                             author_order = author_order,
                             author_type = AUTHOR_TYPE,
                             created_by = CREATED_BY)
        nex_session.add(ra)
        nex_session.flush()
        nex_session.refresh(ra)
        
    fw.write("PMID:{}: The author(s) in Referenceauthor table are updated.\n".format(pmid))


def update_pubmedTypes(nex_session, fw, pmid, reference_id, pubmedTypesDB, pubmedTypesABC, source_id):

    if pubmedTypesDB == pubmedTypesABC or len(pubmedTypesABC) == 0:
        return

    # logger.info(f"PMID:{pmid}: old_pubmedTypes={pubmedTypesDB}")
    # logger.info(f"PMID:{pmid}: new_pubmedTypes={pubmedTypesABC}")
    
    message = ''
    for type in pubmedTypesDB:
        if type not in pubmedTypesABC:
            for pt in nex_session.query(Referencetype).filter_by(
                    reference_id=reference_id, display_name=type).all():
                nex_session.delete(pt)
                message = f"pubmedType:'{type}' is deleted"
    for type in pubmedTypesABC:
        if type not in pubmedTypesDB:
            rt = Referencetype(display_name = type,
                               source_id = source_id,
                               obj_url = '/referencetype/' + type.replace(' ', '_'),
                               reference_id = reference_id,
                               created_by = CREATED_BY)
            nex_session.add(rt)
            message = message + f"pubmedType:'{type}' is added"

    if message:
        # fw.write(f"PMID:{pmid}: The Referencetype is updated. See details: {message}\n")
        fw.write("PMID:{}: The Referencetype is updated. See details: {}\n".format(pmid, message))

def update_reference_table(nex_session, fw, x, titleABC, yearABC, volumeABC, issueABC, pageABC, doiABC, pmcidABC, pubStatusABC, citationABC, journalIdABC):

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
    if issueABC and x.issue	!= issueABC:
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
            ru = ReferenceUrl(display_name = PMC_URL_TYPE,
                              obj_url = pmc_url,
                              source_id = source_id,
                              reference_id = reference_id,
                              url_type = PMC_URL_TYPE,
                              created_by = CREATED_BY)
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
            ru = ReferenceUrl(display_name = DOI_URL_TYPE,
                              obj_url = doi_url,
                              source_id = source_id,
                              reference_id = reference_id,
                              url_type = DOI_URL_TYPE,
                              created_by = CREATED_BY)
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
        x = Referencedocument(document_type = 'Abstract',
                              source_id = source_id,
                              reference_id = reference_id,
                              text = abstractABC,
                              html = html,
                              created_by = CREATED_BY)
        
        nex_session.add(x)
        fw.write("PMID:{}: new abstract added. New abstract: {}\n".format(pmid, abstractABC))        
    else:
        x = nex_session.query(Referencedocument).filter_by(
            reference_id=reference_id, document_type='Abstract').one_or_none()
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

    # logger.info(comment_corrections_from_ABC)
    
    for (parent_id, child_id, type) in comment_corrections_from_ABC:
        found = 0
        foundRelation = {}
        for rr in get_parent(nex_session, child_id):
            foundRelation[rr[0]] = 1
            if rr[2] == type and rr[1] == parent_id:
                ## in database already
                found = 1
                continue
            elif rr[1] == parent_id:
                update_reference_relation_type(nex_session, fw, pmid, parent_id, child_id, type)
                found = 1
            else:
                ## this row is only in sgd
                logger.info("PMID:{}: only in sgd {}, {}".format(pmid, rr[1], rr[2]))
        for rr in get_child(nex_session, parent_id):
            if rr[0] in foundRelation:
                continue
            if rr[2] == type and rr[1] == child_id:
                found = 1
            elif rr[1] == child_id:
                update_reference_relation_type(nex_session, fw, pmid, parent_id, child_id, type)
                found =	1
        if found == 0:
            add_new_reference_relation(nex_session, fw, pmid, source_id, parent_id, child_id, type)

    
def add_new_reference_relation(nex_session, fw, pmid, source_id, parent_id, child_id, type):

    x = nex_session.query(ReferenceRelation).filter_by(
        parent_id=parent_id, child_id=child_id, relation_type = type).one_or_none()
    if x:
        return
    x = ReferenceRelation(source_id = source_id,
                          parent_id = parent_id,
                          child_id = child_id,
                          relation_type = type,
                          created_by = CREATED_BY)
    nex_session.add(x)
    fw.write("PMID:{}: new reference_relation added. parent_id = {}, ".format(pmid, parent_id))
    fw.write("child_id = {}, relation_type = {}\n".format(child_id, type))
    

def update_reference_relation_type(nex_session, fw, pmid, parent_id, child_id, newType):

    x = nex_session.query(ReferenceRelation).filter_by(
        parent_id=parent_id, child_id=child_id).one_or_none()
    if x:
        x.relation_type = newType
        nex_session.add(x)
        fw.write("PMID:{}: the relation_type is updated to {} ".format(pmid, newType))
        fw.write("for parent_id = {} and child_id = {}\n".format(parent_id, child_id))


def retrieve_urls(nex_session):

    reference_id_to_urls = {}
    for x in nex_session.query(ReferenceUrl).all():
        urls = []
        if x.reference_id in reference_id_to_urls:
            urls = reference_id_to_urls[x.reference_id]
        urls.append((x.url_type, x.obj_url))
        reference_id_to_urls[x.reference_id] = urls

    return reference_id_to_urls


def retrieve_abstracts(nex_session):

    reference_id_to_abstract = {}
    for x in nex_session.query(Referencedocument).filter_by(document_type='Abstract').all():
        reference_id_to_abstract[x.reference_id] = x.text
    return reference_id_to_abstract


def retrieve_pubmed_types(nex_session):

    allTypes = nex_session.query(Referencetype).order_by(
        Referencetype.reference_id, Referencetype.display_name).all()
    reference_id_to_types = {}
    for x in allTypes:
        types = []
        if x.reference_id in reference_id_to_types:
            types = reference_id_to_types[x.reference_id]
        types.append(x.display_name)
        reference_id_to_types[x.reference_id] = types
    return reference_id_to_types

        
def retrieve_author_data(nex_session):
    
    allAuthors = nex_session.query(Referenceauthor).order_by(
        Referenceauthor.reference_id, Referenceauthor.author_order).all()
    reference_id_to_authors = {}
    for x in allAuthors:
        authors = []
        if x.reference_id in reference_id_to_authors:
            authors = reference_id_to_authors[x.reference_id]
        orcid = x.orcid if x.orcid else ''
        authors.append((x.display_name, orcid, x.author_order))
        reference_id_to_authors[x.reference_id] = authors
    return reference_id_to_authors


def read_reference_data_from_abc():

    json_data = dict()
    with gzip.open(json_file, 'rb') as f:
        json_str = f.read()
        json_data = json.loads(json_str)

    pmid_to_json_data = {}
    for x in json_data['data']:
        if "cross_references" not in x:
            continue
        pmid = None
        for c in x['cross_references']:
            if c['curie'].startswith('PMID:') and c['is_obsolete'] == False:
                pmid = c['curie'].replace('PMID:', '')
        if pmid:
            pmid_to_json_data[int(pmid)] = x

    return pmid_to_json_data


def get_parent(nex_session, reference_id):

    rows = nex_session.execute("SELECT reference_relation_id, parent_id, relation_type " + \
                               "FROM nex.reference_relation " + \
                               "WHERE child_id = {}".format(reference_id)).fetchall()
    return rows

def get_child(nex_session, reference_id):

    rows = nex_session.execute("SELECT reference_relation_id, child_id, relation_type " + \
                               "FROM nex.reference_relation " + \
                               "WHERE parent_id = {}".format(reference_id)).fetchall()
    return rows
    
def convert_publication_status(pubStatu):

    if pubStatu == 'aheadoflogger.info':
        return 'Epub ahead of logger.info'
    if pubStatu in ['ppublish', 'epublish']:
        return 'Published'
    
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


def parse_process_json_data(json_data, pmid, pmid_to_reference_id, journalIdDB,
                            journal_abbr_to_journal_id, journal_name_to_journal_id):

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

    pubmedTypes = json_data.get('pubmed_types', [])
    pubmedTypes.sort()

    abstract = json_data.get('abstract', '')
    if abstract is None:
        abstract = ''
    abstract = abstract.replace("\\'", "'")

    authors = []
    author_list = []
    author_order = 0
    # https://pubmed.ncbi.nlm.nih.gov/35613595/
    # Yugang Zhang 1, Dan Su 1, Julia Zhu 1, Miao Wang 1, Yandong Zhang 1, Qin Fu 2, Sheng Zhang 2, Hening Lin 3
    # multiple first authors and they have same last_name first_initial (eg, Zhang Y)
    # so have to use order them base on the list provided by PubMed
    for author in json_data.get('authors', []):
        author_name = author['name']
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
        # logger.info("comments=" + str(comments))
        for type in comments:
            for x in comments[type]:
                pmid2 = int(x['PMID'].replace('PMID:', ''))
                if pmid2 in pmid_to_reference_id:
                    parent_id = None
                    child_id = None
                    if type.endswith('In'):
                        parent_id = pmid_to_reference_id[pmid]
                        child_id = pmid_to_reference_id[pmid2]
                    else:
                        parent_id = pmid_to_reference_id[pmid2]
                        child_id = pmid_to_reference_id[pmid]
                    if type.startswith("Erratum"):
                        type = "Erratum"
                    elif type.startswith("Comment"):
                        type = "Comment"
                    elif type.startswith("Republished"):
                        type = "Corrected and Republished"
                    ## following types are new to SGD
                    elif type.startswith('Retraction'):
                        type = "Retraction"
                    elif type.startswith('ExpressionOfConcern'):
                        type = "ExpressionOfConcern"
                    elif type.startswith('Update'):
                        type = "Update"
                    commentCorrections.append((parent_id, child_id, type))

    citation = set_cite(title, author_list, year, journalAbbr, volume, issue, page)

    return (title, year, volume, issue, page, doi, pmcid, pubStatus, citation, \
            journalId, authors, pubmedTypes, abstract, commentCorrections)


if __name__ == '__main__':

    update_data()
