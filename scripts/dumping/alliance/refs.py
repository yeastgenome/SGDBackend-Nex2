import os
import json
import re, sys
import boto3

from datetime import datetime
from sqlalchemy import create_engine
import concurrent.futures
from src.models import DBSession, Referencedbentity, Referencedeleted
from src.data_helpers import get_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION')
DBSession.configure(bind=engine)

# S3_BUCKET = os.environ['S3_BUCKET']
# session = boto3.Session()
# s3 = session.resource('s3')
# s3_dir = 'latest/'
local_dir = 'scripts/dumping/alliance/data/'

DEFAULT_TAXID = '559292'

REFTYPE_TO_ALLIANCE_CATEGORIES ={
"Journal Article": "Research Article",
"Comparative Study":"Research Article",
"Evaluation Study":"Research Article",
"English Abstract":"Conference Publication",
"Historical Article":"Research Article",
"Case Reports":"Research Article",
"Introductory Journal Article":"Research Article",
"Chapter":"Research or review article",
"Meta-Analysis":"Research Article",
"Lecture": "Conference Publication",
"Technical Report":"Research Article",
"Corrected and Republished Article":"Research Article",
"Book":"Book",
"Randomized Controlled Trial":"Research Article",
"Clinical Trial":"Research Article",
"Dataset":"Direct Submission",
"Personal Communication in Publication":"Personal Communication",
"Classical Article":"Research Article",
"Book Chapter":"Research Article",
"Controlled Clinical Trial":"Research Article",
"Systematic Review":"Review Article",
"Duplicate Publication":"Research Article",
"Consensus Development Conference":"Conference Publication",
"Overall":"Conference Publication",
"Corrected And Republished Article":"Research Article",#
"Review": "Review Article",#
"Thesis": "Thesis",#
"Book": "Book",#
"Other": "Other",#
"Preprint": "Preprint",#
"Clinical Conference": "Research Publication",#
"Personal Communication in Publication": "Personal Communication",#
"Direct Submission to SGD": "Direct Data Submission",#
"Published Erratum":"Research Article",
"Congress":"Conference Publication",
"Unknown": "Unknown",#
"Retracted Publication": "Retraction",
"Clinical Study": "Clinical Trial",
"Observational Study": "Research Article",
"Randomized Controlled Trial, Veterinary": "Research Article",
"Expression of Concern":"Other"}#

def make_ref_obj(refObj):
    
    newRefObj = refObj.to_dict()
    
    obj = {
    "datePublished": str(refObj.year),
    "citation": refObj.citation,
    "crossReferences":[{'id':'SGD:'+refObj.sgdid,'pages':['reference']}]
    }

    if refObj.title is not None and refObj.title != "":
        obj['title'] = refObj.title
    else:
        obj["title"] = refObj.citation

    if refObj.pmid is not None and refObj.pmid != "":
        primaryID = obj['primaryId'] = 'PMID:' + str(refObj.pmid)
        
    else:
        primaryID = obj['primaryId'] = 'SGD:' + refObj.sgdid
    
    obj['tags'] = [{'referenceId':primaryID, 'tagName':'inCorpus', 'tagSource': 'SGD'}]

    if refObj.volume is not None and refObj.volume != "":
        obj["volume"] = str(refObj.volume)

    if refObj.page is not None and refObj.page != "":
        obj["pages"] = refObj.page

    if refObj.issue is not None and refObj.issue != "":
        obj["issueName"] = refObj.issue


    if newRefObj["abstract"] is not None:
        obj['abstract'] = newRefObj['abstract']['text']

    if refObj.date_revised:
        obj['dateLastModified'] = refObj.date_revised.strftime("%Y-%m-%dT%H:%m:%S-00:00")

    if refObj.date_published:
        obj['datePublished']= refObj.date_published

    
    if newRefObj['authors'] is not None and newRefObj['authors'] != '':
        obj['authors'] = []
        
        for name in newRefObj['authors']:

            authObj = {
                'name': name['display_name'],
                'referenceId': primaryID,
                'authorRank': newRefObj['authors'].index(name) + 1
            }
 
            obj['authors'].append(authObj)
    if len(obj['authors']) == 0:
        del obj['authors']

              
    if 'reftypes' in newRefObj and newRefObj['reftypes'] is not None:

        (allianceCat, refTypesList) = defineAllianceCat(newRefObj['reftypes'])
        
        obj['allianceCategory'] = allianceCat

        if len(refTypesList) > 0:
            obj["MODReferenceTypes"] = refTypesList

    else:
        obj['allianceCategory'] = "Unknown"


    if refObj.book is not None:
        if refObj.book.publisher is not None:
           obj['publisher'] = refObj.book.publisher
        if refObj.book.title is not None:
           obj['resourceAbbreviation'] = refObj.book.title
    elif refObj.journal is not None:

        if refObj.journal.med_abbr is not None:
            obj['resourceAbbreviation'] = refObj.journal.med_abbr    


    if refObj.pmcid is not None:
        obj['crossReferences'].append({'id': 'PMCID:' + refObj.pmcid})

    if refObj.doi is not None:
        obj['crossReferences'].append({'id': 'DOI:' + refObj.doi})
    if refObj.pmid is not None:
       obj['crossReferences'].append({'id': 'PMID:' + str(refObj.pmid)})

    return obj

def defineAllianceCat(referenceTypes):

    refTypesList = []
    refDisplayList = []

    for eachType in referenceTypes:
        refTypesList.append({'referenceType':eachType['display_name'], 'source':'SGD'})              
        refDisplayList.append(eachType['display_name'])

    refTypes = "|".join(refDisplayList)

    if re.search('Journal Article', refTypes):
 
        if re.search('Review', refTypes):
            return ("Review Article", refTypesList)
        if re.search('Retracted Publication', refTypes):
            return ("Retraction", refTypesList)
        if re.search("Personal Communication in Publication", refTypes):
            return("Personal Communication", refTypesList)
        if re.search("Erratum", refTypes) or re.search("Comment", refTypes):
            return("Other", refTypesList) 
        
        return ("Research Article", refTypesList)
    else:
        if 'Book' in refDisplayList:
            return ("Book", refTypesList)
            
        if 'Thesis' in refDisplayList:
            return ("Thesis", refTypesList)

        if 'Preprint' in refDisplayList:
            return("Preprint", refTypesList)
        if "Clinical Conference" in refDisplayList:
            return("Conference Publication", refTypesList)
        if "Personal Communication to SGD" in refDisplayList:
            return("Personal Communication", refTypesList)
        if "Direct Submission to SGD" in refDisplayList:
            return("Direct Data Submission", refTypesList)
        else:
            return("Other", refTypesList) 
 
 
def get_refs_information():

###### REFERENCES with PMIDS ###########

    print("getting ALL References")
    print("start time:" + str(datetime.now()))

    ref_result = []
    ref_exchange_result = []

    print ('Processing Resources -- deleted PMIDS')
    local_refDeleted_file =  'SGD_false_positive_pmids.txt'
    #s3_refDeleted_file = s3_dir + 'SGD_false_positive_pmids.txt'
    refDel_str = os.path.join(local_dir, local_refDeleted_file)

    deletedObjList = DBSession.query(Referencedeleted).filter(Referencedeleted.pmid != None).all()

    print ("computing " + str(len(deletedObjList)) + " refs (deleted-PMID)")

    if (len(deletedObjList) > 0):

        with open(refDel_str, 'w+') as res_file:

            for resource in deletedObjList:
                print(resource.pmid)
                deletedPMID = resource.pmid
                ref_deleted_result = str(deletedPMID) +"\n"
                res_file.write(ref_deleted_result)

    #s3.meta.client.upload_file(refDel_str, S3_BUCKET, s3_refDeleted_file, ExtraArgs={'ACL': 'public-read'})
    referencesObjList = DBSession.query(Referencedbentity).filter(Referencedbentity.pmid != None).all()

    print("computing " + str(len(referencesObjList)) + " references")

    if (len(referencesObjList) > 0):
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:

            for dbObj in referencesObjList:

                extRefObj = dbObj.to_dict()

                fileObj = make_ref_obj(dbObj)

                refExObj = {
                    "pubMedId": "PMID:" + str(extRefObj['pubmed_id']),
                    "modId": "SGD:" + dbObj.sgdid
                }
                if dbObj.date_revised:
                    refExObj["dateLastModified"] = dbObj.date_revised.strftime("%Y-%m-%dT%H:%m:%S-00:00")
                
                refExObj['tags'] = [{'referenceId':"PMID:" + str(extRefObj['pubmed_id']), 'tagName':'inCorpus', 'tagSource': 'SGD'}]
                
                if 'reftypes' in extRefObj:
                    (allianceCat, refTypesList) = defineAllianceCat(extRefObj['reftypes'])
        
                    refExObj['allianceCategory'] = allianceCat
                    
                    if len(refTypesList) > 0:
                        refExObj["MODReferenceTypes"] = refTypesList
                else:
                    obj['allianceCategory'] = "Unknown"

       
                ref_result.append(fileObj)
                ref_exchange_result.append(refExObj)

##### Process references with no PMIDs for references.py ####

    print ('Processing Resources -- refs without PMIDS')
    resourceObjList = DBSession.query(Referencedbentity).filter(Referencedbentity.pmid == None).all()
    print ("computing " + str(len(resourceObjList)) + " refs (non-PMID)")

    if (len(resourceObjList) > 0):

        for resource in resourceObjList:
            print(str(resourceObjList.index(resource)) + ': reference:' + resource.sgdid)
            nonPMIDObj = make_ref_obj(resource)
            ref_result.append(nonPMIDObj)



    if (len(ref_result) > 0):
        ref_output_obj = get_output(ref_result)
        local_ref_file_name =  'REFERENCE_SGD.json'
        #s3_ref_file = s3_dir + 'REFERENCE_SGD.json'
        json_file_str = os.path.join(local_dir, local_ref_file_name)
        
        with open(json_file_str, 'w+') as res_file:
            res_file.write(json.dumps(ref_output_obj, indent=4, sort_keys=True))

        # print(local_ref_file_name, s3_ref_file)
        # s3.meta.client.upload_file(json_file_str, S3_BUCKET, s3_ref_file, ExtraArgs={'ACL': 'public-read'})

    
    if (len(ref_exchange_result) > 0):
        refExch_obj = get_output(ref_exchange_result)
        local_refExch_file =  'SGD' + SUBMISSION_VERSION + 'referenceExchange.json'
        #s3_refExch_file = s3_dir + 'SGD' + SUBMISSION_VERSION + 'referenceExchange.json'
        refEx_str = os.path.join(local_dir, local_refExch_file)

        with open(refEx_str, 'w+') as res_file:
            res_file.write(json.dumps(refExch_obj, indent=4, sort_keys=True))

        # print(local_refExch_file, s3_refExch_file)
        # s3.meta.client.upload_file(refEx_str, S3_BUCKET, s3_refExch_file, ExtraArgs={'ACL': 'public-read'})


    print("end time:" + str(datetime.now()))

    DBSession.close()


if __name__ == '__main__':
    get_refs_information()
