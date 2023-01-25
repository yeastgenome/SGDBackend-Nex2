""" Alleles object information for Alliance data submission

The script extracts data into a dictionary that is written to a json file.
The json file is submitted to Alliance for futher processing

This file requires packages listed in requirements.txt file and env.sh file.
The env.sh file contains environment variables

09/29/20 - initial alleles objects
05/02/22 - for alliance persistent store


"""

import os
import json
import re, sys
from sqlalchemy import create_engine
from src.models.models import Alleledbentity, LocusAlias, Dbentity, DBSession, PsimodRelation, Straindbentity, Referencedbentity
from src.data_helpers.data_helpers import get_output, get_locus_alias_data, get_pers_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600)
DBSession.configure(bind=engine)
SUBMISSION_TYPE = 'allele_ingest_set'
local_dir = 'scripts/dumping/alliance/data/'

"""
Allele object:
# requirements -- curie, taxon, internal (true/false), name
"""

DEFAULT_TAXID = '559292'

def get_allele_information():
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
              #  simple_allele_obj = alleleObj.to_dict()[0]
               # dbentityObj = DBSession.query(Dbentity).filter(Dbentity.dbentity_id == alleleObj.dbentity_id)
              #  print("info from dbentity table:" + str(simple_allele_obj["date_created"]))

                if re.search("\<sub\>", simple_allele_obj["format_name"]) or not simple_allele_obj["affected_geneObjs"]:
                    print("skipping: " + simple_allele_obj["format_name"])
                    continue
                #print("|".join(dir(alleleObj)))
                #print ("|").join(simple_allele_obj.keys())
                obj = {}
                obj["internal"] = False
                obj["curie"] = "SGD:" + simple_allele_obj["sgdid"]
                print ('SGDID:' + simple_allele_obj["sgdid"]+ " " + simple_allele_obj["display_name"])
             #   obj["name"] = simple_allele_obj["format_name"]
                obj["name"] = simple_allele_obj["display_name"]
            #    obj["date_created"] = simple_allele_obj["date_created"]
        ## Place holder for allele notes 
                #print("desc: " + simple_allele_obj["description"])
          #      if simple_allele_obj["description"] is not None:
          #          if simple_allele_obj["description"] != "":
          #              obj["related_notes"]= [{
          ##                  "internal" = 'false',
           #                 "free_text" = simple_allele_obj["description"],
           #                 "note_type" = ""
           #             }]  ## Place holder for allele notes
           #  
                obj["taxon"] = "NCBITaxon:" + DEFAULT_TAXID

       # Notes for Alleles for p.s.#
        #        if "description" in simple_allele_obj.keys() and simple_allele_obj['description'] is not None:
        #            obj["related_notes"] =[]
        #        }
               # print (str(len(simple_allele_obj["references"]))+"!\n")
        # associated References #
                if len(simple_allele_obj["references"]) > 0:
                    obj['references'] =[]
                    print ('getting refs:'+ str(len(simple_allele_obj["references"])))
                    for singlerefObj in simple_allele_obj["references"]:
                        print("PMID:"+ str(singlerefObj['pubmed_id']))
                        if singlerefObj['pubmed_id'] not in obj['references']: 
                            obj['references'].append("PMID:"+ str(singlerefObj['pubmed_id']))
                            
        ## Synonyms # 
          #      if "aliases" in simple_allele_obj.keys() and simple_allele_obj['aliases'] is not None:
          #          obj["synonyms"] = []
          #          print('getting synonyms')
          #          for aliasObj in simple_allele_obj["aliases"]:
          #              obj["synonyms"].append(aliasObj["display_name"])

                        #obj["synonyms"] #= aliasList #simple_allele_obj["aliases"])
            #    obj["crossReferences"] = [{
            #        "id":
            #        "SGD:" + simple_allele_obj["sgdid"],
            #        "pages": ["allele"]
            #    }]
            #    #obj["alleleObjectRelations"] = []

            #    todo: alleleObj.affected_gene.sgdid doesn't have field sgdid; #skip for rdn25-C2925A, rdn25-C2942A, rdn25-U2861A, rdn25-A2941C
            #    # maybe switch to 'sgdid' for affected gene so it will be faster?
            #    #if simple_allele_obj["format_name"] != ("rdn25-C2925A" or "rdn25-C2942A" or "rdn25-U2861A" or "rdn25-A2941C"):
            #    if simple_allele_obj[
            #            "affected_geneObj"]:  # check the affected gene object; skip if None (should be None if no affected Gene or multiple affected Genes)
            #        #print(simple_allele_obj["affected_geneObj"].sgdid)
            #        obj["alleleObjectRelations"] = [{
            #            "objectRelation": {
            #                "associationType":
            #                "allele_of",
            #                "gene":
            #                "SGD:" +
            #                simple_allele_obj["affected_geneObj"].sgdid
            #            }
            #        }]
            #    #print ("done with " + simple_allele_obj["sgdid"])

                result.append(obj)
        except Exception as e:
            import pdb
            pdb.set_trace()
            print(e)

    if (len(result) > 0):
        output_obj = get_pers_output(SUBMISSION_TYPE, result)

        file_name = 'SGD' + SUBMISSION_VERSION + 'allelesPersistent.json'
        json_file_str = os.path.join(local_dir, file_name)

        with open(json_file_str, 'w+') as res_file:
            res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))

if __name__ == '__main__':
    get_allele_information()
