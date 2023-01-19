""" Resource object information for Alliance data submission

The script extracts data into a dictionary that is written to a json file.
The json file is submitted to Alliance for futher processing

This file requires packages listed in requirements.txt file and env.sh file.
The env.sh file contains environment variables

just makes the resources.json -- non-PMID journals/books/personal communications

"properties": {
    "primaryId": {
      "$ref": "../globalId.json#/properties/globalId",
      "description": "The globally unique identifier for the resource.  ie: NLMId or ISBN or MOD Id.  Each identifier should be prefixed and of the form prefix:Id "
    },
    "title" : {
      "type": "string",
      "description": "The title of the resource."
    },
    "titleSynonyms":  {
      "type" : "array",
        "items": {
          "type": "string"
        },
      "uniqueItems": true
    },
    "abbreviationSynonyms":  {
      "type" : "array",
        "items": {
          "type": "string"
        },
      "uniqueItems": true
    },
    "isoAbbreviation": {
      "type": "string"
    },
    "medlineAbbreviation": {
      "type": "string"
    },
    "copyrightDate": {
      "type": "string",
      "format": "date-time"
    },
    "publisher": {
      "type": "string"
    },
    "printISSN" : {
      "type": "string"
    },
    "onlineISSN" : {
      "type": "string"
    },
    "editorsOrAuthors": {
      "type": "array",
      "items": {
        "$ref": "authorReference.json"
      }
    },
    "volumes": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "pages": {
      "type": "string"
    },
    "abstractOrSummary": {
      "type": "string"
    },
    "crossReferences":{
      "type": "array",
      "items": {
         "$ref": "../crossReference.json"
      }

"""

import os
import json
import re, sys
import time
from random import randint
from datetime import datetime
from sqlalchemy import create_engine, and_, inspect
import concurrent.futures
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.sqltypes import NullType

from sqlalchemy.sql.type_api import NULLTYPE
from src.models.models import LocusAlias, Dbentity, DBSession, Straindbentity, Referencedbentity
from src.data_helpers.data_helpers import get_output, get_locus_alias_data


engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_1.0.0.0_')
DBSession.configure(bind=engine)

###################### 
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
###########

DEFAULT_TAXID = '559292'
REFTYPE_TO_ALLIANCE_CATEGORIES ={
"Journal Article": "Research Article",#
"Review": "Review Article",#
"Thesis": "Thesis",#
"Book": "Book",#
"Other": "Other",#
"Preprint": "Preprint",#
"Clinical Conference": "Conference Publication",#
"Personal Communication in Publication": "Personal Communication",#
"Direct Submission to SGD": "Direct Data Submission",#
#"": "Internal Process Reference",
"Unknown": "Unknown",#
"Retracted Publication": "Retraction"}#

def get_resources_information(root_path):
    """ Extract Reference information.

    Parameters
    ----------
    root_path
        root directory name path    

    Returns
    --------
    file
        writes data to json file

    """
    addedResources = []
##### Process references with no PMIDs for Resources ####
    resources_result = []

    print ('Processing Resources -- refs without PMIDS')
    refObjList = DBSession.query(Referencedbentity).filter(Referencedbentity.pmid == None).all()

    print ("computing " + str(len(refObjList)) + " non-PMID references") 

    if (len(refObjList) > 0):
       # with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
      #  try:
        for reference in refObjList:
            print(str(refObjList.index(reference)) + ': reference:' + reference.sgdid)

          ## get journal or book obj ##
            if reference.journal_no:
                resourceObj = reference.journal
            elif reference.book_no:
                resourceObj = reference.book
            else:
                continue
        ## skip if resource already in obj ##
            if resourceObj.display_name in addedResources:
                continue
        ## add if new resource ##

            obj = {
            'title': resourceObj.title,
            }
            # resource is a book #
            if hasattr(resourceObj, 'isbn'):
                if resourceObj.isbn is not NullType:
                    obj["primaryId"] = "ISBN:" + resourceObj.isbn
            if hasattr(resourceObj, 'publisher'):
                obj["publisher"] = resourceObj.publisher
            if hasattr(resourceObj,'total_pages'):
                if resourceObj.total_pages is not NullType:
                    obj["pages"] = resourceObj.total_pages
            if hasattr(resourceObj,'medabbr'):
                if resourceObj.medabbr is not NullType:
                    obj["medlineAbbreviation"] = resourceObj.medabbr
            if hasattr(resourceObj,'issn_print'):
                if resourceObj.issn_print is not NullType:
                    obj["printISSN] = resourceObj.issn_print
            if hasattr(resourceObj,'issn_electronic'):
                if resourceObj.issn_electronic is not NullType:
                    obj["onlineISSN"] = resourceObj.issn_electronic
 
            resources_result.append(obj) 

    if (len(resources_result) > 0):
        resource_output_obj = get_output(resources_result)
        resources_file = 'data/SGD' + SUBMISSION_VERSION + 'resources.json'
        resource_file_str = os.path.join(root_path, resources_file)
        
        with open(resource_file_str, 'w+') as res_file:
            res_file.write(json.dumps(resource_output_obj, indent=4, sort_keys=True))

if __name__ == '__main__':
    get_resources_information(THIS_FOLDER)