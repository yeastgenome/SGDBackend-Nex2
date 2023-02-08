import os
import json
import re, sys
from sqlalchemy import create_engine
from src.models import Alleledbentity, DBSession
from src.data_helpers import get_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_5.4.0_')

DBSession.configure(bind=engine)
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
                if re.search("\<sub\>", simple_allele_obj["format_name"]
                             ) or not simple_allele_obj["affected_geneObj"]:

                    print("skipping: " + simple_allele_obj["format_name"])
                    continue

                obj = {}


                obj["primaryId"] = "SGD:" + simple_allele_obj["sgdid"]
                obj["symbolText"] = simple_allele_obj["format_name"]
                obj["symbol"] = simple_allele_obj["display_name"]
                if simple_allele_obj["description"] is not None:
                    if simple_allele_obj["description"] != "":
                        obj["description"] = simple_allele_obj["description"]
                obj["taxonId"] = "NCBITaxon:" + DEFAULT_TAXID

                if "aliases" in simple_allele_obj.keys(
                ) and simple_allele_obj['aliases'] is not None:
                    obj["synonyms"] = []
                    for aliasObj in simple_allele_obj["aliases"]:
                        obj["synonyms"].append(aliasObj["display_name"])
                obj["crossReferences"] = [{
                    "id":
                    "SGD:" + simple_allele_obj["sgdid"],
                    "pages": ["allele"]
                }]

                #TODO: alleleObj.affected_gene.sgdid doesn't have field sgdid; #skip for rdn25-C2925A, rdn25-C2942A, rdn25-U2861A, rdn25-A2941C
                # maybe switch to 'sgdid' for affected gene so it will be faster?
                #if simple_allele_obj["format_name"] != ("rdn25-C2925A" or "rdn25-C2942A" or "rdn25-U2861A" or "rdn25-A2941C"):
                if simple_allele_obj["affected_geneObj"]:

                    obj["alleleObjectRelations"] = [{
                        "objectRelation": {
                            "associationType":
                            "allele_of",
                            "gene":
                            "SGD:" +
                            simple_allele_obj["affected_geneObj"].sgdid
                        }
                    }]
                result.append(obj)
        except Exception as e:
            import pdb
            pdb.set_trace()
            print(e)

    if (len(result) > 0):
        output_obj = get_output(result)

        file_name = 'SGD' + SUBMISSION_VERSION + 'alleles.json'
        json_file_str = os.path.join(local_dir, file_name)

        with open(json_file_str, 'w+') as res_file:
            res_file.write(json.dumps(output_obj, indent=4, sort_keys=True)))


if __name__ == '__main__':
    get_allele_information()
