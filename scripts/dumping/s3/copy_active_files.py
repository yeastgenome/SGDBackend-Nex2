import boto3
import os
S3_BUCKET = os.environ['S3_BUCKET']
S3_BUCKET2 = os.environ['ARCHIVE_S3_BUCKET']
from src.boto3_upload import boto3_copy_file
from src.models import Filedbentity, Dbentity
from scripts.loading.database_session import get_session

def copy_files():
   
    nex_session = get_session()

    copy_sgd_gpad_gpi(nex_session)
    
    copy_gff(nex_session)
    copy_gaf(nex_session)
    copy_gpad(nex_session)
    copy_gpi(nex_session)
    copy_noctua_gpad(nex_session) 
    copy_go_slim_mapping_file(nex_session)
    copy_rna_dbxref_file(nex_session)
    copy_gene_pmid_file(nex_session)

def copy_gene_pmid_file(nex_session):
    
    dstDir = "curation/literature/"
    gene2pmid_file = "gene2pmid.tab"

    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('gene2pmid.tab%')).filter(Filedbentity.dbentity_status=='Active').all():

        if x.s3_url is None:
            continue

        urlParam = x.s3_url.split('/')
        filename = urlParam[4].split('?')[0]
        srcFile = urlParam[3] + '/' + filename
        
        ## copy to archive                                                                                        
        dstFile = dstDir + "archive/" + filename
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

        ## copy to current directory                                                                               
        dstFile = dstDir + gene2pmid_file
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

        
def copy_rna_dbxref_file(nex_session):

    dstDir = "curation/chromosomal_feature/"
    rna_file = "SGD_ncRNA_xref.txt"

    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('SGD_ncRNA_xref.txt%')).filter(Filedbentity.dbentity_status=='Active').all():

        if x.s3_url is None:
            continue
    
        urlParam = x.s3_url.split('/')
        filename = urlParam[4].split('?')[0]
        srcFile = urlParam[3] + '/' + filename

        ## copy to archive
        dstFile = dstDir + "archive/" + filename
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)
        
        ## copy to current directory
        dstFile = dstDir + rna_file
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

def copy_go_slim_mapping_file(nex_session):

    dstDir = "curation/literature/"
    slimMapping_file = "go_slim_mapping.tab"

    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('go_slim_mapping.tab%')).filter(Filedbentity.dbentity_status=='Active').all():

        if x.s3_url is None:
            continue

        urlParam = x.s3_url.split('/')
        filename = urlParam[4].split('?')[0]
        srcFile = urlParam[3] + '/' + filename

        ## copy to archive                                                                                                                         
        dstFile = dstDir + "archive/" + filename
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

        ## copy to current directory                                                                                                               
        dstFile = dstDir + slimMapping_file
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)


def copy_noctua_gpad(nex_session):

    dstDir = "curation/literature/"
    gpad_file = "noctua_sgd.gpad.gz"

    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('noctua_sgd.gpad_%.gz')).filter(Filedbentity.dbentity_status=='Active').all():

        if x.s3_url is None:
            continue

        urlParam = x.s3_url.split('/')
        filename = urlParam[4].split('?')[0]
        srcFile = urlParam[3] + '/' + filename

        ## copy to archive
        dstFile = dstDir + "archive/" + filename
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

        ## copy to current directory
        dstFile = dstDir + gpad_file
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

def copy_sgd_gpad_gpi(nex_session):
    
    dstDir = "latest/"
    gpad_file = "gpad.sgd.gz"
    gpi_file = "gpi.sgd.gz"

    all_gpad = nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('gpad.sgd%.gz')).filter(Filedbentity.dbentity_status=='Active').all()
    if len(all_gpad) > 0:
        gpad = all_gpad.pop()
        if gpad.s3_url is not None:
            urlParam = gpad.s3_url.split('/')
            filename = urlParam[4].split('?')[0]
            srcFile = urlParam[3] + '/' + filename
            
            dstFile = dstDir + gpad_file
            print (gpad.dbentity_status, srcFile, dstFile)
            boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

    all_gpi = nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('gpi.sgd%.gz')).filter(Filedbentity.dbentity_status=='Active').all()
    
    if len(all_gpi) > 0:
        gpi = all_gpi.pop()
        if gpi.s3_url is not None:
            urlParam = gpi.s3_url.split('/')
            filename = urlParam[4].split('?')[0]
            srcFile = urlParam[3] + '/' + filename

            dstFile = dstDir + gpi_file
            print (gpi.dbentity_status, srcFile, dstFile)
            boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

def copy_gpi(nex_session):

    dstDir = "curation/literature/"
    gpi_file = "gp_information.559292_sgd.gpi.gz"

    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('gp_information.559292_sgd_%.gz')).filter(Filedbentity.dbentity_status=='Active').all():

        if x.s3_url is None:
            continue

        urlParam = x.s3_url.split('/')
        filename = urlParam[4].split('?')[0]
        srcFile = urlParam[3] + '/' + filename

        ## copy to archive
        dstFile = dstDir + "archive/" + filename
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

        ## copy to current directory
        dstFile = dstDir + gpi_file
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

def copy_gpad(nex_session):

    dstDir = "curation/literature/"
    gpad_file = "gp_association.559292_sgd.gpad.gz"

    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('gp_association.559292_sgd_%.gz')).filter(Filedbentity.dbentity_status=='Active').all():

        if x.s3_url is None:
            continue
        
        urlParam = x.s3_url.split('/')
        filename = urlParam[4].split('?')[0]
        srcFile = urlParam[3] + '/' + filename

        ## copy to archive
        dstFile = dstDir + "archive/" + filename
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

        ## copy to current directory
        dstFile = dstDir + gpad_file
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)


def copy_gaf(nex_session):

    dstDir = "curation/literature/"
    gaf_file = "gene_association.sgd.gaf.gz"

    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('gene_association.sgd.%.gz')).filter(Filedbentity.dbentity_status=='Active').all():

        if x.s3_url is None:
            continue

        urlParam = x.s3_url.split('/')
        filename = urlParam[4].split('?')[0]
        srcFile = urlParam[3] + '/' + filename

        ## copy to archive 
        dstFile = dstDir + "archive/" + filename
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

        ## copy to current directory
        dstFile = dstDir + gaf_file
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

        ## copy to latest directory 
        dstFile = "latest/" + gaf_file
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET, dstFile)

def copy_gff(nex_session):
    
    ## current directory

    dstDir = "curation/chromosomal_feature/"
    gff_file = "saccharomyces_cerevisiae.gff.gz"

    for x in nex_session.query(Filedbentity).filter(Filedbentity.previous_file_name.like('saccharomyces_cerevisiae.%.gff.gz')).filter(Filedbentity.dbentity_status=='Active').all():

        if x.s3_url is None:
            continue

        urlParam = x.s3_url.split('/')
        filename = urlParam[4].split('?')[0]
        srcFile = urlParam[3] + '/' + filename

        ## copy to archive
        dstFile = dstDir + "archive/" + filename
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

        ## copy to current directory
        dstFile = dstDir + gff_file
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET2, dstFile)

        ## copy to latest directory
        dstFile = "latest/" + gff_file
        print (x.dbentity_status, srcFile, dstFile)
        boto3_copy_file(S3_BUCKET, srcFile, S3_BUCKET, dstFile)

if __name__ == '__main__':

    copy_files()
