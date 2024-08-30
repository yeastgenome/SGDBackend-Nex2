import os
from sqlalchemy import text
from src.models import Sgdid, Dbentity, Referencedbentity, Referencedocument, Referenceauthor,\
    Referencetype, ReferenceUrl, Source, Journal
from scripts.loading.database_session import get_session
from scripts.loading.reference.pubmed import set_cite
from scripts.loading.util import link_gene_names

doi_root = 'http://dx.doi.org/'
pubmed_root = 'http://www.ncbi.nlm.nih.gov/pubmed/'
pmc_root = 'http://www.ncbi.nlm.nih.gov/pmc/articles/'
status = 'Published'
epub_status = 'Epub ahead of print'
pdf_status = 'N'
epub_pdf_status = 'NAP'

CREATED_BY = os.environ['DEFAULT_USER']


def add_paper(record, nex_session=None):
     
    if nex_session is None:
        nex_session = get_session()

    source_id = get_source_id(nex_session, 'NCBI')

    (sgdid, display_name, pubStatus, citation, pmid, pmcid, doi, pubdate, year, volume,
     issue, page, title, author_list, journal, journal_title, journal_id) = extract_data(nex_session, record)

    print("Inserting into sgdid table:")

    insert_sgdid(nex_session, sgdid, source_id)
        
    try:
        
        print("Inserting into dbentity/referencedbentity tables:")

        dbentity_id = insert_referencedbentity(nex_session, pmid, pmcid, doi, pubdate, year,
                                               volume, issue, page, title, citation,
                                               journal_id, pubStatus, source_id, sgdid,
                                               display_name)

        print("Inserting into author table:")

        insert_authors(nex_session, dbentity_id, author_list, source_id)

        print("Inserting into referencetype table:")

        insert_pubtypes(nex_session, pmid, dbentity_id, record.get('pubmed_types', []), source_id)

        print("Inserting into URL table:")

        insert_urls(nex_session, pmid, dbentity_id, doi, pmcid, source_id)

        print("Inserting into abstract table:")

        insert_abstract(nex_session, pmid, dbentity_id, record,
                        source_id, journal, journal_title, author_list)
        
        nex_session.commit()
        return dbentity_id
    
    except Exception as e:
        nex_session.rollback()
        print("An error occured when adding reference entry for " + sgdid + ". Error=" + str(e))
        return None
        

def insert_urls(nex_session, pmid, reference_id, doi, pmcid, source_id):
    
    x = ReferenceUrl(display_name = 'PubMed',
                     obj_url = pubmed_root + str(pmid),
                     reference_id = reference_id,
                     url_type = 'PubMed',
                     source_id = source_id,
                     created_by = CREATED_BY)
    nex_session.add(x)
    if doi:
        doi_url = doi_url = doi_root + doi
        x = ReferenceUrl(display_name = 'DOI full text',
                         obj_url = doi_url,
                         reference_id = reference_id,
                         url_type = 'DOI full text',
                         source_id = source_id,
                         created_by= CREATED_BY)
        nex_session.add(x)
    if pmcid:
        pmc_url = pmc_root + pmcid
        x =ReferenceUrl(display_name = 'PMC full text',
                        obj_url = pmc_url,
                        reference_id = reference_id,
                        url_type = 'PMC full text',
                        source_id = source_id,
                        created_by= CREATED_BY)
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)


def insert_pubtypes(nex_session, pmid, reference_id, pubtypes, source_id):
    
    for type in pubtypes:
        x = Referencetype(display_name = type,
                          obj_url = '/referencetype/'+ type.replace(' ', '_'),
                          source_id = source_id,
                          reference_id = reference_id,
                          created_by = CREATED_BY)
        nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)


def insert_abstract(nex_session, pmid, reference_id, record, source_id, journal_abbrev, journal_title, authors):

    text = record.get('abstract', '')

    if text == '':
        return
    
    x = Referencedocument(document_type = 'Abstract',
                          source_id = source_id,
                          reference_id = reference_id,
                          text = text,
                          html = link_gene_names(text, {}, nex_session),
                          created_by = CREATED_BY)
    nex_session.add(x)
    
    entries = create_bibentry(pmid, record, journal_abbrev, journal_title, authors)
    y = Referencedocument(document_type = 'Medline',
                          source_id = source_id,
                          reference_id = reference_id,
                          text = '\n'.join([key + ' - ' + str(value) for key, value in entries if value is not None]),
                          html = '\n'.join([key + ' - ' + str(value) for key, value in entries if value is not None]),
                          created_by = CREATED_BY)
    nex_session.add(y)
    nex_session.flush()
    nex_session.refresh(x)


def create_bibentry(pmid, record, journal_abbrev, journal_title, authors):

    entries = []
    
    pubdate = record.get('date_published', '')
    year = pubdate.split(' ')[0]
    title = record.get('title', '')
    volume = record.get('volume', '')
    issue = record.get('issue_name', '')
    pages = record.get('page_range', '')

    entries.append(('PMID', pmid))
    entries.append(('STAT', 'Active'))
    entries.append(('DP', pubdate))
    entries.append(('TI', title))
    entries.append(('IP', issue))
    entries.append(('PG', pages))
    entries.append(('VI', volume))
    entries.append(('SO', 'SGD'))
    authors = record.get('AU', [])
    for author in authors:
        entries.append(('AU', author))
    pubtypes = record.get('pubmed_types', [])
    for pubtype in pubtypes:
        entries.append(('PT', pubtype))
    if record.get('abstract') is not None:
        entries.append(('AB', record.get('abstract')))
 
    if journal_abbrev:
        entries.append(('TA', journal_abbrev))
    if journal_title:
        entries.append(('JT', journal_title))
    return entries


def insert_authors(nex_session, reference_id, authors, source_id):

    if len(authors) == 0:
        return

    i = 0
    for author in authors:
        i = i + 1
        x = Referenceauthor(display_name = author,
                            obj_url = '/author/' + author.replace(' ', '_'),
                            source_id = source_id,
                            reference_id = reference_id,
                            author_order = i,
                            author_type = 'Author', 
                            created_by = CREATED_BY)
        nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)
    

def extract_data(nex_session, record):

    journal_id, journal, journal_title = get_journal_id(nex_session, record)
    pubdate = record.get('date_published', '')
    year = pubdate
    if year is None:
        year = ''
    elif year:
        year = int(year[0:4])
    title = record.get('title', '')
    if title is None:
        title = '' 
    title = title.replace("\\'", "'")

    authors = []
    author_list = []
    author_order = 0
    # https://pubmed.ncbi.nlm.nih.gov/35613595/
    # Yugang Zhang 1, Dan Su 1, Julia Zhu 1, Miao Wang 1, Yandong Zhang 1, Qin Fu 2, Sheng Zhang 2, Hening Lin 3
    # multiple first authors and they have same last_name first_initial (eg, Zhang Y)
    # so have to use order them base on the list provided by PubMed
    for author in record.get('authors', []):
        author_name = author['name']
        if 'last_name' in author and author['last_name'] and 'first_initial' in author and author['first_initial']:
            author_name = author['last_name'] + " " + author['first_initial']
        author_list.append(author_name.strip())
        orcid = author['orcid'].replace("ORCID:", "") if 'orcid' in author and author['orcid'] else ''
        author_order += 1
        authors.append((author_name.strip(), orcid, author_order))

    volume = record['volume'] if 'volume' in record else ''
    if volume is None:
        volume = ''
    issue = record['issue_name'] if 'issue_name' in record else ''
    if issue is None:
        issue = ''
    page = record['page_range'] if 'page_range' in record else ''
    if page is None:
        page = ''

    doi = None
    pmcid = None
    pmid = None
    sgdid = None
    if "cross_references" in record:
        for cr in record['cross_references']:
            if cr['curie'].startswith('PMID:'):
                pmid = int(cr['curie'].replace('PMID:', ''))
            if cr['curie'].startswith('DOI:'):
                doi = cr['curie'].replace('DOI:', '')
            if cr['curie'].startswith('PMCID:'):
                pmcid = cr['curie'].replace('PMCID:', '')
            if cr['curie'].startswith('SGD:'):
                sgdid = cr['curie'].replace('SGD:', '')
                
    pubStatus = record['pubmed_publication_status'] if 'pubmed_publication_status' in record else ''
    if pubStatus is None:
        pubStatus = ''
    else:
        pubStatus = convert_publication_status(pubStatus)

    citation = set_cite(title, author_list, year, journal, volume, issue, page)
    display_name = citation.split(')')[0] + ")"

    return (sgdid, display_name, pubStatus, citation, pmid, pmcid, doi, pubdate, year, volume,
            issue, page, title, author_list, journal, journal_title, journal_id)
    

def insert_sgdid(nex_session, sgdid, source_id):

    row = nex_session.query(Sgdid).filter_by(display_name = sgdid).one_or_none()
    if row is None:
        x = Sgdid(format_name = sgdid,
                  display_name = sgdid,
                  obj_url = '/sgdid/' + sgdid,
                  source_id = source_id,
                  subclass = 'REFERENCE',
                  sgdid_status = 'Primary',
                  created_by = CREATED_BY)
        nex_session.add(x)
        nex_session.commit()
    

def insert_referencedbentity(nex_session, pmid, pmcid, doi, pubdate, year, volume, issue, page, title, citation, journal_id, pubStatus, source_id, sgdid, display_name): 

    print("inserting referencedbentity:", pmid, pmcid, doi, pubdate, year, volume, issue, page, title, citation, journal_id, pubStatus, source_id, sgdid, display_name)
    
    x = Referencedbentity(sgdid = sgdid,
                          source_id = source_id,
                          format_name = sgdid,
                          display_name = display_name,
                          subclass = 'REFERENCE',
                          dbentity_status = 'Active',
                          obj_url = '/reference/' + sgdid,
                          created_by = CREATED_BY,
                          method_obtained = 'Curator triage',
                          publication_status = pubStatus,
                          fulltext_status = pdf_status,
                          citation = citation,
                          year = year,
                          pmid = pmid,
                          pmcid = pmcid,
                          date_published = pubdate,
                          issue = issue,
                          page = page,
                          volume = volume,
                          title = title,
                          doi = doi,
                          journal_id = journal_id)

    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    return x.dbentity_id


def convert_publication_status(pubStatus):

    if pubStatus in ['ppublish', 'epublish']:
        return 'Published'
    elif pubStatus == 'aheadofprint':
        return 'Epub ahead of print'
    return pubStatus


def get_journal_id(nex_session, record, source_id=None):

    journal_abbr = record.get('resource_medline_abbreviation', '')
    journal_full_name = record.get('resource_title', '')

    if journal_abbr:
        journals = nex_session.query(Journal).filter_by(med_abbr=journal_abbr).all()
        if len(journals) > 0:
            return journals[0].journal_id, journals[0].med_abbr, journal_full_name

    if source_id is None:
        source_id = get_source_id(nex_session, 'PubMed')

    format_name = journal_full_name.replace(' ', '_') + journal_abbr.replace(' ', '_')
    j = Journal(display_name = journal_full_name,
                format_name = format_name,
                title = journal_full_name,
                med_abbr = journal_abbr,
                source_id = source_id,
                obj_url = '/journal/'+format_name,
                created_by = CREATED_BY)
    nex_session.add(j)
    nex_session.flush()
    nex_session.refresh(j)
    return j.journal_id, j.med_abbr, journal_full_name


def get_source_id(nex_session, source):
    
    src = nex_session.query(Source).filter_by(display_name=source).all()
    return src[0].source_id
