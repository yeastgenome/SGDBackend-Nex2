import urllib.request, urllib.parse, urllib.error
import gzip
import shutil
from urllib import request
from os import path,  makedirs
import logging
from datetime import datetime
import sys
from src.models import Referencedbentity, ReferenceFile, Filedbentity
from scripts.loading.database_session import get_session
from scripts.loading.suppl_files.load_pubmed_PMC_files import load_data
from src.helpers import upload_file

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

# https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/73/60/PMC8595334.tar.gz
pmcRootUrl = 'https://ftp.ncbi.nlm.nih.gov/pub/pmc/'
dataDir = 'scripts/loading/suppl_files/data/'
pmcFileDir = 'scripts/loading/suppl_files/pubmed_pmc_download/'

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

    file_id_to_s3_url = dict([(x.dbentity_id, x.s3_url) for x in nex_session.query(Filedbentity).filter_by(description='PubMed Central download').all()]) 

    i = 0
    for x in nex_session.query(Referencedbentity).filter(Referencedbentity.pmid.isnot(None)).all():
        file_id = refernce_id_to_file_id.get(x.dbentity_id)
        if file_id is None or file_id not in file_id_to_s3_url:
            if x.pmid in pmid_to_oa_url:
                i += 1
                print (x.pmid, pmid_to_oa_url[x.pmid])
                to_file = pmcFileDir + str(x.pmid) + '.tar.gz'
                if path.exists(to_file):
                    continue
                try:
                    urllib.request.urlretrieve(pmcRootUrl + pmid_to_oa_url[x.pmid], to_file)
                    urllib.request.urlcleanup()
                except Exception as e:
                    print ("Error occurred when downloading: ", pmcRootUrl + pmid_to_oa_url[x.pmid], " : error=" + str(e))
                                
    nex_session.close()


if __name__ == "__main__":

    if path.exists(pmcFileDir):
        shutil.rmtree(pmcFileDir)
    makedirs(pmcFileDir)

    oafile_url = 'ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_file_list.csv'
    mapping_file = dataDir + "oa_file_list.csv"

    try:
        log.info("Downloading " + oafile_url)
        req = request.urlopen(oafile_url)
        data = req.read()
        with open(mapping_file, 'wb') as fh:
            fh.write(data)
        download_files(mapping_file)
        load_data()
    except Exception as e:
        log.info("Error downloading the file: " + file + ". Error=" + str(e))


    
        
