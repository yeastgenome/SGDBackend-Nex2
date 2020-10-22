import urllib.request, urllib.parse, urllib.error
from urllib.request import urlopen
import gzip
import shutil
import logging
import os
from datetime import datetime
import sys
import importlib
importlib.reload(sys)  # Reload does the trick!
from src.models import Source, Dbentity, LocusUrl
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']
PLACEMENT = 'LOCUS_ALLIANCE_ICONS'
URL_TYPE = 'Alliance'

root_url = 'https://www.alliancegenome.org/'
infile = 'scripts/loading/alliance/data/alliance_orthologs_sorted.txt'
sgdidFile = 'scripts/loading/alliance/data/genes_submitted_to_alliance.txt'
db_list = ['WB', 'FB', 'MGI', 'RGD', 'ZFIN', 'HGNC']

def load_data():

    nex_session = get_session()

    src = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = src.source_id
    sgdid_to_dbentity_id = dict([(x.sgdid, x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='LOCUS').all()])
    
    log.info(str(datetime.now()))
    
    log.info("Loading data...\n") 

    f = open(infile)

    db2linkTemplate = db_to_link_template()

    key_to_link = {}
    
    for line in f:
        pieces = line.strip().split('\t')
        sgdid = pieces[0].replace('SGD:', '')
        gene = pieces[1]
        db = pieces[2]
        query = pieces[3]
        ids = pieces[4].split('|')
        link_url = ''
        link_url2 = ''
        if len(ids) > 1:
            link_url = db2linkTemplate[db].replace("_SUBSTITUTE_", pieces[4].replace('|', '+'))
            # link_url2 = db2linkTemplate[db].replace("_SUBSTITUTE_", query)
            # if len(link_url) > 500:
            #    # print ("TOO LONG ID LIST: len=", len(link_url),  link_url)
            #    if len(link_url2) <= 500:
            #        link_url = link_url2
            #    else:
            #        # print ("TOO LONG QUERY LIST: len=", len(link_url2),  link_url2)
            #        link_url = db2linkTemplate[db].replace("_SUBSTITUTE_", gene)
        else:
            link_url = root_url + "gene/" + ids[0]
        key = (sgdid, db)
        key_to_link[key] = link_url

    f.close()

    i = 0
    
    f = open(sgdidFile)
    
    for line in f:
        
        sgdid = line.strip()
        dbentity_id = sgdid_to_dbentity_id.get(sgdid)
        if dbentity_id is None:
            continue
        
        i = i + 1
        
        ## link to alliance sgd page
        sgd_link_url = root_url + 'gene/SGD:' + sgdid 
        insert_locus_url(nex_session, dbentity_id, source_id, 'SGD', sgd_link_url)

        ## link to other db pages
        for db in db_list:
            key = (sgdid, db)
            if key in key_to_link:
                insert_locus_url(nex_session, dbentity_id, source_id, db, key_to_link[key])

        if i > 300:        
            # nex_session.rollback()
            nex_session.commit()
            i = 0

    f.close()
    
    # nex_session.rollback()
    nex_session.commit()
    
    nex_session.close()

    log.info(str(datetime.now()))

    log.info("Done!\n\n")

def insert_locus_url(nex_session, locus_id, source_id, display_name, link_url):

    if display_name == 'HGNC':
        display_name = "A " + display_name
    elif display_name == 'MGI':
        display_name = "B " + display_name
    elif display_name == 'RGD':
        display_name = "C " + display_name
    elif display_name == 'ZFIN':
        display_name = "D " + display_name
    elif display_name == 'FB':
        display_name = "E " + display_name
    elif display_name == 'WB':
        display_name = "F " + display_name
    elif display_name == 'SGD':
        display_name = "G " + display_name
        
    print (locus_id, source_id, display_name, link_url)
    
    x = LocusUrl(locus_id = locus_id,
                 source_id = source_id,
                 display_name = display_name,
                 obj_url = link_url,
                 url_type = URL_TYPE,
                 placement = PLACEMENT,
                 created_by = CREATED_BY)
    
    nex_session.add(x)

    
def db_to_link_template():

    url = root_url + "search?biotypes=protein_coding_gene&category=gene&q=_SUBSTITUTE_&species="

    return { "ZFIN": url + "Danio%20rerio",
             "RGD":  url + "Rattus%20norvegicus",
             "MGI":  url + "Mus%20musculus",
             "FB":   url + "Drosophila%20melanogaster",
             "WB":   url + "Caenorhabditis%20elegans",
             "HGNC": url + "Homo%20sapiens" }


    
if __name__ == "__main__":

    load_data()


    
        
