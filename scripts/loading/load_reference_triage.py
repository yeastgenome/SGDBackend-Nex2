from datetime import datetime
from io import StringIO
import logging
import os
from Bio import Entrez, Medline 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from zope.sqlalchemy import ZopeTransactionExtension
import transaction

from src.models import Referencedbentity, Referencetriage, Referencedeleted, Locusdbentity, LocusAlias
from scripts.loading.reference.pubmed import get_pmid_list, get_pubmed_record, set_cite, get_abstract
from scripts.loading.util import extract_gene_names

__author__ = 'sweng66'
# adjusted to run in curation environment

TERMS = ['yeast', 'cerevisiae']
URL = 'http://www.ncbi.nlm.nih.gov/pubmed/'
DAY = 14
RETMAX = 10000
MAX = 500

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

NEX2_URI = os.environ['NEX2_URI']

def load_references():
    # create session
    engine = create_engine(os.environ['NEX2_URI'])
    session_factory = sessionmaker(bind=engine, extension=ZopeTransactionExtension())
    db_session = scoped_session(session_factory)
    # some preparation
    pmid_to_reference_id = dict([(x.pmid, x.dbentity_id) for x in db_session.query(Referencedbentity).all()])
    pmid_to_curation_id = dict([(x.pmid, x.curation_id) for x in db_session.query(Referencetriage).all()])
    pmid_to_refdeleted_id = dict([(x.pmid, x.referencedeleted_id) for x in db_session.query(Referencedeleted).all()])
    doi_to_reference_id = dict([(x.doi, x.dbentity_id) for x in db_session.query(Referencedbentity).all()])
    
    # get gene names to highlight
    gene_list = []
    all_loci = db_session.query(Locusdbentity).all()
    for x in all_loci:
        if len(x.systematic_name) > 12 or len(x.systematic_name) < 4:
            continue
        gene_list.append(str(x.systematic_name.upper()))
        if x.gene_name and x.gene_name != x.systematic_name:
            gene_list.append(str(x.gene_name.upper()))
    alias_to_name = {}
    for x in db_session.query(LocusAlias).all():
        if x.alias_type not in ['Uniform', 'Non-uniform']:
            continue
        if len(x.display_name) < 4:
            continue
        name = x.locus.gene_name if x.locus.gene_name else x.locus.systematic_name 
        alias_to_name[x.display_name] = name
    # get new PMIDs
    log.info(str(datetime.now()))
    log.info("Getting PMID list...")
    pmid_list = get_pmid_list(TERMS, RETMAX, DAY)
    pmids_all = []
    for pmid in pmid_list:
        if int(pmid) in pmid_to_reference_id:
            continue
        if int(pmid) in pmid_to_curation_id:
            continue
        if int(pmid) in pmid_to_refdeleted_id:
            continue
        pmids_all.append(pmid)

    if len(pmids_all) == 0:
        log.info("No new papers")
        return
    # get data for each PMID entry
    log.info(str(datetime.now()))
    log.info("Getting Pubmed records...")

    pmids = []
    i = 0
    for pmid in pmids_all:
        pmids.append(pmid)
        i = i + 1
        if i > MAX:
            records = get_pubmed_record(','.join(pmids))
            handle_one_record(db_session, records, gene_list, alias_to_name, doi_to_reference_id)
            i = 0

    log.info("Done!")

    if i > 0:
        records = get_pubmed_record(','.join(pmids))
        handle_one_record(db_session, records, gene_list, alias_to_name, doi_to_reference_id)

    log.info("Done!")

def handle_one_record(db_session, records, gene_list, alias_to_name, doi_to_reference_id):

    i = 1
    for rec in records:
        rec_file = StringIO(rec)
        record = Medline.read(rec_file)
        pmid = record.get('PMID')
        pubmed_url = 'http://www.ncbi.nlm.nih.gov/pubmed/' + str(pmid)
        doi_url = ""
        if record.get('AID'):
            # ['S0167-7012(17)30042-8 [pii]', '10.1016/j.mimet.2017.02.002 [doi]']
            doi = None
            for id in record['AID']:
                if id.endswith('[doi]'):
                    doi = id.replace(' [doi]', '')
                    break
            if doi and doi in doi_to_reference_id:
                continue
            if doi:
                doi_url = "/".join(['http://dx.doi.org', doi])

        if doi_url and doi_url in doi_to_reference_id:
            continue
        
        title = record.get('TI', '')
        authors = record.get('AU', [])
        pubdate = record.get('DP', '')  # 'PubDate': '2012 Mar 20'  
        year = pubdate.split(' ')[0]
        journal = record.get('TA', '')
        volume = record.get('VI', '')
        issue = record.get('IP', '')
        pages = record.get('PG', '')
        citation = set_cite(title, authors, year, journal, volume, issue, pages)  
        abstract = record.get('AB', '')
        gene_names = extract_gene_names(abstract, gene_list, alias_to_name)

        # insert formatted data to DB
        insert_reference(db_session, pmid, citation, doi_url, abstract, " ".join(gene_names))

def insert_reference(db_session, pmid, citation, doi_url, abstract, gene_list):
    x = None
    if doi_url and abstract:
        x = Referencetriage(pmid = pmid,
                            citation = citation,
                            fulltext_url = doi_url,
                            abstract = abstract,
                            abstract_genes = gene_list)
    elif doi_url:
        x = Referencetriage(pmid = pmid,
                            citation = citation,
                            fulltext_url = doi_url,
                            abstract_genes = gene_list)
    elif abstract:
        x = Referencetriage(pmid = pmid,
                            citation = citation,
                            abstract = abstract,
                            abstract_genes = gene_list)
    else:
        x = Referencetriage(pmid = pmid,
                            citation = citation,
                            abstract_genes = gene_list)
    db_session.add(x)
    transaction.commit()
    log.info("Insert new reference: " + citation)

if __name__ == '__main__':    
    load_references()
