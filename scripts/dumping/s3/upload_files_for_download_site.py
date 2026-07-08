import boto3
import os
import shutil
from os import path, remove
from datetime import date

S3_BUCKET = os.environ['ARCHIVE_S3_BUCKET']

local_dir = "scripts/dumping/tab_files_for_download_site/data/"
s3_top_dir = "curation/"

s3_lit_dir = s3_top_dir + "literature/"
s3_chr_feat_dir = s3_top_dir + "chromosomal_feature/"
s3_protein_dir = s3_top_dir + "calculated_protein_info/"

S3_LATEST_BUCKET = os.environ['S3_BUCKET']
s3_latest_dir = "latest/"

lit_files = [
    "regulation.tab",
    "phenotype_data.tab",
    "molecularComplexes.tab",
    "interaction_data_PMID:27708008.tab.gz",
    "interaction_data_PMID:20093466.tab.gz",
    "interaction_data.tab.gz",
    "go_terms.tab",
    "go_protein_complex_slim.tab",
    "gene_literature.tab",
    "functional_complementation.tab",
    "biochemical_pathways.tab",
    "alleles.tab",
    "yeastHumanDisease.tab"
]

feat_files = [
    "SGD_features.tab",
    "dbxref.tab",
    "deleted_merged_features.tab"
]

protein_files = [
    "protein_properties.tab"
]

session = boto3.Session()
s3 = session.resource('s3')

def upload_files():

    datestamp = str(date.today()).replace("-", "")
    
    for filename in os.listdir(local_dir):
        s3_dir = None
        if filename in lit_files:
            s3_dir = s3_lit_dir
        elif filename in feat_files:
            s3_dir = s3_chr_feat_dir
        elif filename in protein_files:
            s3_dir = s3_protein_dir
        if s3_dir is not None:
            ### upload files to the current directories
            local_file = local_dir + filename
            s3_file = s3_dir + filename
            print (local_file, s3_file)
            s3.meta.client.upload_file(local_file, S3_BUCKET, s3_file, ExtraArgs={'ACL': 'public-read'})

            ### upload files to latest directory
            s3_latest_file = s3_latest_dir + filename
            s3.meta.client.upload_file(local_file, S3_LATEST_BUCKET, s3_latest_file, ExtraArgs={'ACL': 'public-read'})
            
            ### upload files to archive directories
            filename_with_datestamp = filename + "_" + datestamp
            local_file_with_datestamp = local_dir + filename_with_datestamp 
            s3_archive_file = s3_dir + "archive/" + filename_with_datestamp
            shutil.copy(local_file, local_file_with_datestamp)
            print(local_file_with_datestamp, s3_archive_file)
            s3.meta.client.upload_file(local_file_with_datestamp, S3_BUCKET, s3_archive_file, ExtraArgs={'ACL': 'public-read'})
            remove(local_file_with_datestamp)

if __name__ == '__main__':

    upload_files()
