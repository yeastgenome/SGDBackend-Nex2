""" Alleles object information for Alliance data submission

The script extracts data into a dictionary that is written to a json file.
The json file is submitted to Alliance for futher processing

This file requires packages listed in requirements.txt file and env.sh file.
The env.sh file contains environment variables

09/29/20 - initial alleles objects

"""

import os
import json
import re, sys
import time
from random import randint
from datetime import datetime
from sqlalchemy import create_engine, and_, inspect
import concurrent.futures
from ..models.models import Alleledbentity, LocusAlias, Dbentity, DBSession, Straindbentity, Referencedbentity
from ..data_helpers.data_helpers import get_output, get_locus_alias_data

engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_1.0.0.0_')
DBSession.configure(bind=engine)
"""
Allele object:
# requirements -- symbol, symbolText, taxonId, primaryId

properties": {
    "primaryId": {
      "$ref": "../globalId.json#/properties/globalId",
      "description": "The prefixed primary (MOD) ID for an entity. For internal AGR use, e.g. FB:FBgn0003301, MGI:87917."
    },
    "symbol": {
      "type": "string",
      "description": "The symbol of the entity."
    },
    "symbolText": {
      "type": "string",
      "description": "the symbol in text format, replacing all html tags with <>.  There may be more than one set of <> in the symbol."
    },
    "taxonId": {
      "$ref": "../globalId.json#/properties/globalId",
      "description": "The taxonId for the species of the genotype entity."
    },
    "synonyms": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "uniqueItems": true
    },
    "description": {
      "type": "string",
      "description":"optional free text annotation area provided for the allele by the MOD curators."
    },
    "secondaryIds": {
      "type": "array",
      "items": {
        "$ref": "../globalId.json#/properties/globalId"
      },
      "uniqueItems": true
    },
    "alleleObjectRelations": {
	  "type": "array",
	  "items": {
          {
          "title": "alleleOf",
          "type": "object",
          "description": "allele_of can only be applied when objectType is gene",
          "required": [
            "gene"
          ],
          "properties": {
            "associationType": {
              "enum": [
                "allele_of"
              ]
            },
	     "gene" : {
      "$ref": "../globalId.json#/properties/globalId",
      "description": "The single affected gene of the allele."
	     }
	  }
	}
	      "description": "An object that describes how this allele object is related to either a gene or a construct or both."
	  }
    },
    "crossReferences": {
      "type": "array",
      "items": {
        "$ref": "../crossReference.json#"
      },
      "uniqueItems": true
    }
}
  }

"""

DEFAULT_TAXID = '559292'


def get_allele_information(root_path):
    """ Extract Allele information.

    Parameters
    ----------
    root_path
        root directory name path    

    Returns
    --------
    file
        writes data to json file

     datasetSamples = DBSession.query(Datasetsample).filter(
        Datasetsample.biosample.in_(BIOSAMPLE_OBI_MAPPINGS.keys()),
        Datasetsample.dbxref_id != None).all()
    """
    print("getting Alleles")

    alleleObjList = DBSession.query(Alleledbentity).all()

    print(("computing " + str(len(alleleObjList)) + " alleles"))
    #   sys.exit()
    result = []

    if (len(alleleObjList) > 0):
        # with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        try:
            for alleleObj in alleleObjList:
                simple_allele_obj = alleleObj.to_simple_dict()
                if re.search("\<sub\>", simple_allele_obj["format_name"]
                             ) or not simple_allele_obj["affected_geneObj"]:

                    print("skipping: " + simple_allele_obj["format_name"])
                    continue
                #print("|".join(dir(alleleObj)))
                #print ("|").join(simple_allele_obj.keys())
                obj = {}
                # "primaryID": "SGD:XXXXX",
                #    "symbol": "STRING"; symbol of the entity
                #    "symbolText": "STRING", the symbol in text format, replacing all html tags with <>.  There may be more than one set of <> in the symbol."
                #    "taxonId" ,"The taxonId for the species of the genotype entity."
                # "synonyms": LIST, strings
                # "description": free text
                # "secondaryIds": list of Ids (SGD:, etc)
                # "alleleObjectRelations": LIST of obj {
                #   "objectRelation": {"associationType":"allele_of", "gene":"SGD:XXXXX"}
                # }
                # "crossReferences": ["id":"Allele SGDID", "pages":["allele"]]

                #print(simple_allele_obj["sgdid"] + " allele's affected gene:")

                obj["primaryId"] = "SGD:" + simple_allele_obj["sgdid"]
                obj["symbolText"] = simple_allele_obj["format_name"]
                obj["symbol"] = simple_allele_obj["display_name"]
                #print("desc: " + simple_allele_obj["description"])
                if simple_allele_obj["description"] is not None:
                    if simple_allele_obj["description"] != "":
                        obj["description"] = simple_allele_obj["description"]
                obj["taxonId"] = "NCBITaxon:" + DEFAULT_TAXID

                if "aliases" in simple_allele_obj.keys(
                ) and simple_allele_obj['aliases'] is not None:
                    obj["synonyms"] = []
                    for aliasObj in simple_allele_obj["aliases"]:
                        obj["synonyms"].append(aliasObj["display_name"])
                        #obj["synonyms"] #= aliasList #simple_allele_obj["aliases"])
                obj["crossReferences"] = [{
                    "id":
                    "SGD:" + simple_allele_obj["sgdid"],
                    "pages": ["allele"]
                }]
                #obj["alleleObjectRelations"] = []

                #TODO: alleleObj.affected_gene.sgdid doesn't have field sgdid; #skip for rdn25-C2925A, rdn25-C2942A, rdn25-U2861A, rdn25-A2941C
                # maybe switch to 'sgdid' for affected gene so it will be faster?
                #if simple_allele_obj["format_name"] != ("rdn25-C2925A" or "rdn25-C2942A" or "rdn25-U2861A" or "rdn25-A2941C"):
                if simple_allele_obj[
                        "affected_geneObj"]:  # check the affected gene object; skip if None (should be None if no affected Gene or multiple affected Genes)
                    #print(simple_allele_obj["affected_geneObj"].sgdid)
                    affectedGenesList = []
                    for each in simple_allele_obj["affected_geneObj"]:
                        affectedGenesList.append
                          (
                        "objectRelation": {
                            "associationType":"allele_of",
                            "gene":"SGD:" + each.sgdid
                        })
                    obj["alleleObjectRelations"] = affectedGenesList
                #print ("done with " + simple_allele_obj["sgdid"])

                result.append(obj)
        except Exception as e:
            import pdb
            pdb.set_trace()
            print(e)

    if (len(result) > 0):
        output_obj = get_output(result)

        file_name = 'src/data/SGD' + SUBMISSION_VERSION + 'alleles.json'
        json_file_str = os.path.join(root_path, file_name)

        with open(json_file_str, 'w+') as res_file:
            res_file.write(json.dumps(output_obj))

if __name__ == '__main__':
    get_allele_information(THIS_FOLDER)