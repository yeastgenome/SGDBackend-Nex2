import os
import json
import re, sys
from sqlalchemy import create_engine
from src.models import Alleledbentity, DBSession
from src.data_helpers import get_pers_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_5.4.0_')
DBSession.configure(bind=engine)
SUBMISSION_TYPE = 'allele_ingest_set'
local_dir = 'scripts/dumping/alliance/data/'

DEFAULT_TAXID = '559292'

def get_allele_information():

    print("getting Alleles")

    alleleObjList = DBSession.query(Alleledbentity).all()

    print(("computing " + str(len(alleleObjList)) + " alleles"))

    result = []

    if (len(alleleObjList) > 0):

        try:
            for alleleObj in alleleObjList:
                simple_allele_obj = alleleObj.to_simple_dict()

                if re.search("\<sub\>", simple_allele_obj["format_name"]) or not simple_allele_obj["affected_geneObjs"]:
                    print("skipping: " + simple_allele_obj["format_name"])
                    continue
                obj = {}
                obj["internal"] = False
                obj["curie"] = "SGD:" + simple_allele_obj["sgdid"]
                print ('SGDID:' + simple_allele_obj["sgdid"]+ " " + simple_allele_obj["display_name"])
                obj["name"] = simple_allele_obj["display_name"]
                obj["taxon"] = "NCBITaxon:" + DEFAULT_TAXID
                if len(simple_allele_obj["references"]) > 0:
                    obj['references'] =[]
                    print ('getting refs:'+ str(len(simple_allele_obj["references"])))
                    for singlerefObj in simple_allele_obj["references"]:
                        print("PMID:"+ str(singlerefObj['pubmed_id']))
                        if singlerefObj['pubmed_id'] not in obj['references']: 
                            obj['references'].append("PMID:"+ str(singlerefObj['pubmed_id']))

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
