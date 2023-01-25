""" Reference object information for Alliance data submission

The script extracts data into a dictionary that is written to a json file.
The json file is submitted to Alliance for futher processing

This file requires packages listed in requirements.txt file and env.sh file.
The env.sh file contains environment variables

01/05/2021 - initial References objects
splits into 3 files -- references.json, resources.json, resourceExchange.json
references.json -- PMID articles
resources.json -- non-PMID articles/books/personal communications
refExchange.json -- all PMIDs to update? future submissions?

"""

import os
import json
import re, sys
import boto3

from datetime import datetime
from sqlalchemy import create_engine
import concurrent.futures
from src.models import DBSession, Referencedbentity, Referencedeleted
from src.data_helpers import get_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600)
DBSession.configure(bind=engine)

S3_BUCKET = os.environ['S3_BUCKET']
session = boto3.Session()
s3 = session.resource('s3')
s3_dir = 'latest/'
local_dir = 'scripts/dumping/alliance/data/'


###########
# Reference file requirements -
# required: [
# primaryId - string,
# title - string,
# datePublished -string (date-time format),
# citation - string,
# allianceCategory - string (ENUM),
# resourceId - globalId.json
# ],
# optional --
# dateLastModified - string, date-time,
# authors - list,
# volume - string
# pages - string
# abstract - string
# keywords - array
# pubMedType - list of strings (should be directly from PubMed)
# publisher - string,
# MODReferenceTypes - list of MODReferenceType objs
# issueName - string
# tags - list of referenceTag objs
# meshTerms - list of meshDetail.json objs
# crossReferences - list of crossReference.json  
####################### 
# Resource file requirements -- 
# required:
# primaryId - string
# title: string
#
# optional:
# 
# titleSynonyms - list
# abbreviationSynonyms -- list
# isoAbbreviation - string
# medlineAbbreviation - string
# copyrightDate - string (date-time)
# publisher - string
# printISSN - string
# onlineISSN - string
# editorsOrAuthors - list of authorRefObjects
# volumes -- list
# pages - string
# abstractOrSummary -string
# crossReferences - list of crossReference objects
##############
# referenceExchange file requirements
# required: 
# PubMedId: string
# allianceCategory - "enum": ["Research Article","Review Article","Thesis","Book","Other","Preprint","Conference Publication","Personal Communication","Direct Data Submission","Internal Process Reference", "Unknown","Retraction"],
# 
# optional: 
# MODReferenceTypes
# modId
# dataLastModified - string (date-time)
# tags - list of referenceTag objects
# ################




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
    
    obj = {  #reference obj
 #   "primaryId": "PMID:" + str(newRefObj['pubmed_id'])  #"SGD:" + refObj.sgdid,
 #   "title": refObj.title,
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


    if refObj.date_revised: # dateLastModified for refexchange & refs (opt)
        obj['dateLastModified'] = refObj.date_revised.strftime("%Y-%m-%dT%H:%m:%S-00:00")

## datePublished (req'd) - refObj.date_published || refObj.year if date_published isn't available
    if refObj.date_published:
        obj['datePublished']= refObj.date_published #.strftime("%Y-%m-%dT%H:%m:%S-00:00")

## Authors for references##
    authorOrder = 1
    authorList = []
    
    if newRefObj['authors'] is not None and newRefObj['authors'] != '':
        obj['authors'] = []
        
        for name in newRefObj['authors']:
               # nameList = name['display_name'].split(' ')
            authObj = {
                'name': name['display_name'],
                'referenceId': primaryID, #'PMID:' + str(newRefObj['pubmed']) #'SGD:' + refObj.sgdid,
                'authorRank': newRefObj['authors'].index(name) + 1
            }
 
            obj['authors'].append(authObj)
    if len(obj['authors']) == 0:
        del obj['authors']

## crossref for author? id: SGD:last_first, pages"["/author"] 
              #  authorOrder += 1
              
    if 'reftypes' in newRefObj and newRefObj['reftypes'] is not None:
    #    refTypesList = []
    #    modRefTypeList = []
        (allianceCat, refTypesList) = defineAllianceCat(newRefObj['reftypes'])
        
        obj['allianceCategory'] = allianceCat

        if len(refTypesList) > 0:
            obj["MODReferenceTypes"] = refTypesList

    else:
        obj['allianceCategory'] = "Unknown"

            
## journal or book publication ##
    if refObj.book is not None:
        if refObj.book.publisher is not None:
           obj['publisher'] = refObj.book.publisher
        if refObj.book.title is not None:
           obj['resourceAbbreviation'] = refObj.book.title
    elif refObj.journal is not None:
      #  if refObj.journal.title is not None:
      #      obj['publisher'] = refObj.journal.title
        if refObj.journal.med_abbr is not None:
            obj['resourceAbbreviation'] = refObj.journal.med_abbr    

## crossReferences for reference.json file #
              # refObj.pmid, refObj.pmcid refObj.doi
    if refObj.pmcid is not None:
        obj['crossReferences'].append({'id': 'PMCID:' + refObj.pmcid})

    if refObj.doi is not None:
        obj['crossReferences'].append({'id': 'DOI:' + refObj.doi})
    if refObj.pmid is not None:
       obj['crossReferences'].append({'id': 'PMID:' + str(refObj.pmid)})

    return obj

def defineAllianceCat(referenceTypes):
    ### alliance category for both objects (req'd) and make MODReferenceTypes (opt)               
    refTypesList = []
    refDisplayList = []

    for eachType in referenceTypes:
        refTypesList.append({'referenceType':eachType['display_name'], 'source':'SGD'})              
        refDisplayList.append(eachType['display_name'])
## default category - research article
    refTypes = "|".join(refDisplayList)

    if re.search('Journal Article', refTypes):#'Journal Article' in refTypesList:
 
        if re.search('Review', refTypes): #'Review' in refTypesList:
            return ("Review Article", refTypesList)
                       # continue
        if re.search('Retracted Publication', refTypes): #Retracted Publication' in refTypesList:
            return ("Retraction", refTypesList)
                       # continue
        if re.search("Personal Communication in Publication", refTypes): # in refTypesList:
            return("Personal Communication", refTypesList)
                       # continue
        if re.search("Erratum", refTypes) or re.search("Comment", refTypes): #in refTypesList or "Comment" in refTypesList:
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
        else:  # not any of the others
            return("Other", refTypesList) 
 
 
def get_refs_information():

###### REFERENCES with PMIDS ###########

    print("getting ALL References")
    print("start time:" + str(datetime.now()))

    ref_result = []
    ref_exchange_result = []
    ref_deleted_result = []

    print ('Processing Resources -- deleted PMIDS')
    deletedObjList = DBSession.query(Referencedeleted).filter(Referencedeleted.pmid != None).limit(20).all()

    print ("computing " + str(len(deletedObjList)) + " refs (deleted-PMID)")

    if (len(deletedObjList) > 0):

        for resource in deletedObjList:
            print(resource.pmid)
            deletedPMID = resource.pmid
            ref_deleted_result.append(deletedPMID)

### Process references with PMIDs ###
    referencesObjList = DBSession.query(Referencedbentity).filter(Referencedbentity.pmid != None).limit(20).all()

    print("computing " + str(len(referencesObjList)) + " references")

    if (len(referencesObjList) > 0):
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
      #  try:
            for dbObj in referencesObjList:
               # print(str(referencesObjList.index(refObj)) + ': reference:' + refObj.sgdid)
                extRefObj = dbObj.to_dict()

                fileObj = make_ref_obj(dbObj)  ##FOR REF FILE##

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
    resourceObjList = DBSession.query(Referencedbentity).filter(Referencedbentity.pmid == None).limit(20).all()

    print ("computing " + str(len(resourceObjList)) + " refs (non-PMID)")

    if (len(resourceObjList) > 0):

        for resource in resourceObjList:
            print(str(resourceObjList.index(resource)) + ': reference:' + resource.sgdid)

            nonPMIDObj = make_ref_obj(resource)
  
            ref_result.append(nonPMIDObj)

    if (len(ref_result) > 0):
        ref_output_obj = get_output(ref_result)
        #file_name = 'src/data_dump/SGD' + SUBMISSION_VERSION + 'references.json'
        local_ref_file_name =  'REFERENCE_SGD.json'
        s3_ref_file = s3_dir + 'REFERENCE_SGD.json'
        json_file_str = os.path.join(local_dir, local_ref_file_name)
        
        with open(json_file_str, 'w+') as res_file:
            res_file.write(json.dumps(ref_output_obj, indent=4, sort_keys=True))

        print(local_ref_file_name, s3_ref_file)
        s3.meta.client.upload_file(json_file_str, S3_BUCKET, s3_ref_file, ExtraArgs={'ACL': 'public-read'})

    
    if (len(ref_exchange_result) > 0):
        refExch_obj = get_output(ref_exchange_result)
        local_refExch_file =  'SGD' + SUBMISSION_VERSION + 'referenceExchange.json'
        s3_refExch_file = s3_dir + 'SGD' + SUBMISSION_VERSION + 'referenceExchange.json'
        refEx_str = os.path.join(local_dir, local_refExch_file)

        with open(refEx_str, 'w+') as res_file:
            res_file.write(json.dumps(refExch_obj, indent=4, sort_keys=True))

        print(local_refExch_file, s3_refExch_file)
        s3.meta.client.upload_file(refEx_str, S3_BUCKET, s3_refExch_file, ExtraArgs={'ACL': 'public-read'})

    if (len(ref_deleted_result) > 0):
        refDeleted_obj = get_output(ref_deleted_result)
        local_refDeleted_file =  'SGD_false_positive_pmids.txt'
        s3_refDeleted_file = s3_dir + 'SGD_false_positive_pmids.txt'
        refDel_str = os.path.join(local_dir, local_refDeleted_file)

        with open(refDel_str, 'w+') as res_file:
            res_file.write(json.dumps(refDeleted_obj, indent=4, sort_keys=True))

        print(local_refDeleted_file, s3_refDeleted_file)
        s3.meta.client.upload_file(refDel_str, S3_BUCKET, s3_refDeleted_file, ExtraArgs={'ACL': 'public-read'})

    print("end time:" + str(datetime.now()))

if __name__ == '__main__':
    get_refs_information()
