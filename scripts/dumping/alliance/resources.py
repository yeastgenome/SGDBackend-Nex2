import os
import json
from sqlalchemy import create_engine
from sqlalchemy.sql.sqltypes import NullType
from src.models import DBSession, Referencedbentity
from src.data_helpers  import get_output,


engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_5.4.0_')
DBSession.configure(bind=engine)
local_dir = 'scripts/dumping/alliance/data/'

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

def get_resources_information():

    addedResources = []
    resources_result = []

    print ('Processing Resources -- refs without PMIDS')
    refObjList = DBSession.query(Referencedbentity).filter(Referencedbentity.pmid == None).all()

    print ("computing " + str(len(refObjList)) + " non-PMID references") 

    if (len(refObjList) > 0):

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
        resources_file = 'SGD' + SUBMISSION_VERSION + 'resources.json'
        resource_file_str = os.path.join(local_dir, resources_file)
        
        with open(resource_file_str, 'w+') as res_file:
            res_file.write(json.dumps(resource_output_obj, indent=4, sort_keys=True))

if __name__ == '__main__':
    get_resources_information()
