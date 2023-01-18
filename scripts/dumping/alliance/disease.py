""" Aggregate disease data for Alliance data submission

The script extracts data from ajson file into a dictionary that is written to another json file.
The json file is submitted to Alliance for futher processing

This file requires packages listed in requirements.txt file and env.sh file.
The env.sh file contains environment variables

This file can be imported as a modules and contains the following functions:
    get_disease_association_data
"""
import os
import sys
import json
import re
import concurrent.futures
from datetime import datetime
from src.models.models import DBSession, Diseaseannotation, Diseasesupportingevidence, Dbentity
from src.data_helpers.data_helpers import get_eco_ids, get_output, SUBMISSION_VERSION
from sqlalchemy import create_engine, and_

engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
DBSession.configure(bind=engine)

eco_code_dict = {"236289": "IGI", "236296": "IMP", "236356": "ISS"}
""" EX: { 
            "DOid": "DOID:10629", # diseaseannotation.
            "objectId": "SGD:S000000037",
            "objectName:",
            "objectRelation":,
            "negation":,
            "primaryGeneticEntityIDs": {
"type": "array",},
            "evidence": {
                "evidenceCodes": [
                    "IMP",
                    "ISS"
                ],
                "publication": {
                    "pubMedId": "PMID:11827457"
                }
            },
            "objectRelation": {
                "associationType": "is_implicated_in",  # diseaseannotation.association_type - ro.display_name
                "objectType": "gene" 
            },
            "dateAssigned": "2017-04-12T00:04:00-00:00",
            "dataProvider": [
                {
                    "crossReference": {
                        "id": "SGD",
                        "pages": [
                            "homepage"
                        ]
                    },
                    "type": "curated"
                }
            ],
            "with": [
                "HGNC:4837" ## diseasesupportingevidence.dbxref_id
            ]
        },
 """


def get_disease_association_data(root_path):
    result = {}  #[]
    #    file_name = 'src/data_assets/disease_association.json'
    #    json_file_str = os.path.join(root_path, file_name)
    #    with open(json_file_str) as data_file:
    #        content = json.load(data_file)
    #    if (content):
    disease_data = DBSession.query(Diseaseannotation).all()
    #result = []
    print(("computing " + str(len(disease_data)) + " diseases"))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        for item in disease_data:
            #toLsp = item.to_dict_lsp()
            #todoDict = item.to_dict()
            ## If object (DOID, objectid, pmid and HGNC have to all match) already exists, add to evidence --
            obj = {
                "DOid": "",
                "objectRelation": {
                    "associationType": "",
                    "objectType": ""
                },
                "objectId": "",
                "dateAssigned": "",
                "dataProvider": [],
                #  "with": [],
                "evidence": {
                    "evidenceCodes": [],
                    "publication": {
                        "publicationId": {}
                        #     "pubMedId": {} ## changed to publicationID in 1.0.0.8
                    }
                }
            }
            #get supporting evidence (HGNC ID)
            evidence_list = []

            supporting_evidences = DBSession.query(
                Diseasesupportingevidence).filter_by(
                    annotation_id=item.annotation_id).with_entities(
                        Diseasesupportingevidence.dbxref_id).all()

            #  print "|".join(supporting_evidences.dbxref_id)

            if len(supporting_evidences) > 0:
                for evidence in supporting_evidences:
                    evidence_list.append(evidence.dbxref_id)
                obj["with"] = evidence_list

        #  keyList = []
        # keylist = [str(item.disease.disease_id), str(item.dbentity.sgdid), str(item.reference.pmid)] #+ evidence_list
        # print "list key:" + str(item.disease.disease_id) + "|" +str(item.dbentity.sgdid) +"|"+str(item.reference.pmid)

        # eco_code = eco_code_dict[str(item.eco.eco_id)]
        # if eco_code = 'IMP':
        #     uniqkey = str(item.disease.disease_id) + "_" + str(item.dbentity.sgdid) + "_" + str(item.reference.pmid)
        # else:
            uniqkey = str(item.disease.disease_id) + "_" + str(
                item.dbentity.sgdid) + "_" + str(
                    item.reference.pmid) + "_" + "_".join(evidence_list)

            #  if re.match("S000005269", uniqkey):
            #     print "******** KEY:" + uniqkey

            # print "diseaseannotation_id: " + str(item.annotation_id)
            # print 'item ECO CODE:' + eco_code_dict[str(item.eco.eco_id)]
            ## if exists in results arleady, append ECO code:

            if uniqkey in list(result.keys()):
                #               print 'original eco code:' + '|'.join(result[uniqkey]["evidence"]["evidenceCodes"])

                result[uniqkey]["evidence"]["evidenceCodes"].append(
                    item.eco.ecoid)

            else:
                ## if not, make new obj for key
                ## publication ID ## PMID or SGDID
                ## reference SGDID
                print(item.reference.pmid)

                ref_dbentity = DBSession.query(Dbentity).filter(
                    Dbentity.dbentity_id == item.reference.pmid).all()

                if item.reference.pmid:
                    pubidref = "PMID:" + str(item.reference.pmid)
                    sgdref = "SGD:" + str(ref_dbentity)
                else:
                    pubidref = "SGD:" + str(ref_dbentity.sgdid)

                ## if 'not' qualifier
                if item.disease_qualifier == 'not':
                    obj["negation"] = "not"
            ## for if there is an object name
            # obj[]

                obj["DOid"] = str(item.disease.doid)
                obj["objectRelation"]["associationType"] = item.ro.display_name
                obj["objectRelation"]["objectType"] = "gene"
                obj["objectId"] = "SGD:" + str(item.dbentity.sgdid)
                obj["dateAssigned"] = item.date_created.strftime(
                    "%Y-%m-%dT%H:%m:%S-00:00")
                obj["evidence"]["evidenceCodes"].append(item.eco.ecoid)
                obj["evidence"]["publication"]["publicationId"] = pubidref
                #            obj["with"] = evidence_list
                obj["dataProvider"].append({
                    "crossReference": {
                        "id": "SGD:" + str(item.dbentity.sgdid),
                        "pages": ["gene/disease"]
                    },
                    "type": "curated"
                })

                #             if sgdref:
                #                 obj["evidence"]["crossReference"] = sgdref

                result[uniqkey] = obj

    if len(list(result.keys())) > 0:
        print("# objs:" + str(len(list(result.keys()))))
        output_obj = get_output(list(result.values()))
        file_name = 'data/SGD' + SUBMISSION_VERSION + 'disease_association.json'
        json_file_str = os.path.join(root_path, file_name)
        if (output_obj):
            with open(json_file_str, 'w+') as res_file:
                res_file.write(json.dumps(output_obj))

if __name__ == '__main__':
    get_disease_association_data(THIS_FOLDER)