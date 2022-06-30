import urllib.request, urllib.parse, urllib.error
import gzip
from os.path import exists
import logging
import os
from datetime import datetime
import sys
from src.models import Referencedbentity, ReferenceFile
from scripts.loading.database_session import get_session
from src.helpers import upload_file

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

# https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/73/60/PMC8595334.tar.gz
pmcRootUrl = 'https://ftp.ncbi.nlm.nih.gov/pub/pmc/'
dataDir = 'scripts/loading/suppl_files/data/'
supplementalFileDir = 'scripts/loading/suppl_files/supplemental_files/'

def download_files(mapping_file):

    # File,Article Citation,Accession ID,Last Updated (YYYY-MM-DD HH:MM:SS),PMID,License
    # oa_package/08/e0/PMC13900.tar.gz,Breast Cancer Res. 2001 Nov 2; 3(1):55-60,PMC13900,2019-11-05 11:56:12,11250746,NO-CC CODE

    pmid_to_oa_url = {}
    f = open(mapping_file)
    for line in f:
        if line.startswith('File,'):
            continue
        pieces = line.split(',')
        if pieces[4] and pieces[4].isdigit():
            pmid = int(pieces[4])
            pmid_to_oa_url[pmid] = pieces[0]
    f.close()

    nex_session = get_session()

    refernce_id_to_file_id = dict([(x.reference_id, x.file_id) for x in nex_session.query(ReferenceFile).filter_by(file_type='Supplemental').all()])

    for x in nex_session.query(Referencedbentity).filter(Referencedbentity.pmid.isnot(None)).all():
        if x.dbentity_id not in refernce_id_to_file_id:
            if x.pmid in pmid_to_oa_url:
                print (x.pmid, pmid_to_oa_url[x.pmid])
                to_file = supplementalFileDir + str(x.pmid) + '.tar.gz'
                if exists(to_file):
                    continue
                try:
                    urllib.request.urlretrieve(pmcRootUrl + pmid_to_oa_url[x.pmid], to_file)
                    urllib.request.urlcleanup()
                except Exception as e:
                    print ("Error occurred when downloading: ", pmcRootUrl + pmid_to_oa_url[x.pmid], " : error=" + str(e))
    nex_session.close()

    


    
if __name__ == "__main__":
        
    # https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_file_list.csv

    ### the following times out
    # url_path = 'ftp://ncbi.nlm.nih.gov/pub/pmc/'
    mapping_file = 'oa_file_list.csv'
    # urllib.request.urlretrieve(url_path + mapping_file, dataDir + mapping_file)

    download_files(dataDir + mapping_file)
    


    
        
