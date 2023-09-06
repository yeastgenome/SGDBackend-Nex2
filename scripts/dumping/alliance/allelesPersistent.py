import os
import json
import re, sys
from sqlalchemy import create_engine
from src.models import Alleledbentity, DBSession
from src.data_helpers import get_pers_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_5.4.0_')
LINKML_VERSION = os.getenv('LINKML_VERSION', 'v1.7.5')
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
                obj["data_provider_dto"] = {
                    "source_organization_abbreviation": "SGD",
                    "internal": False}
                obj["allele_symbol_dto"] = {
                    "name_type_name": "nomenclature_symbol",
                    "format_text": simple_allele_obj["display_name"],
                    "display_text": simple_allele_obj["display_name"],
                    "internal": False}
                obj["allele_mutation_type_dtos"] = [{
                    "mutation_type_curies": [simple_allele_obj["allele_so_id"]],
                    "internal": False}]
                obj["taxon_curie"] = "NCBITaxon:" + DEFAULT_TAXID
                if len(simple_allele_obj["references"]) > 0:
                    obj['reference_curies'] =[]
                    #print ('getting refs:'+ str(len(simple_allele_obj["references"])))
                    for singlerefObj in simple_allele_obj["references"]:
                        print("PMID:"+ str(singlerefObj['pubmed_id']))
                        if singlerefObj['pubmed_id'] not in obj['reference_curies']:
                            obj['reference_curies'].append("PMID:"+ str(singlerefObj['pubmed_id']))
                result.append(obj)
        except Exception as e:
            #import pdb
            #pdb.set_trace()
            print(simple_allele_obj)
            print(e)

    if (len(result) > 0):
        output_obj = get_pers_output(SUBMISSION_TYPE, result, LINKML_VERSION)
        file_name = 'SGD' + SUBMISSION_VERSION + 'allelesPersistent.json'
        json_file_str = os.path.join(local_dir, file_name)
        with open(json_file_str, 'w+') as res_file:
            res_file.write(json.dumps(output_obj, indent=4, sort_keys=False))

    DBSession.close()

if __name__ == '__main__':
    get_allele_information()
