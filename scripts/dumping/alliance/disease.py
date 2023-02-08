import os
import json
import concurrent.futures
from src.models import DBSession, Diseaseannotation, Diseasesupportingevidence, Dbentity
from src.data_helpers import get_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600)
DBSession.configure(bind=engine)

local_dir = 'scripts/dumping/alliance/data/'


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


def get_disease_association_data():
    result = {}
    disease_data = DBSession.query(Diseaseannotation).all()
    print(("computing " + str(len(disease_data)) + " diseases"))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        for item in disease_data:

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
                    }
                }
            }

            evidence_list = []

            supporting_evidences = DBSession.query(
                Diseasesupportingevidence).filter_by(
                    annotation_id=item.annotation_id).with_entities(
                        Diseasesupportingevidence.dbxref_id).all()

            if len(supporting_evidences) > 0:
                for evidence in supporting_evidences:
                    evidence_list.append(evidence.dbxref_id)
                obj["with"] = evidence_list

            uniqkey = str(item.disease.disease_id) + "_" + str(
                item.dbentity.sgdid) + "_" + str(
                    item.reference.pmid) + "_" + "_".join(evidence_list)


            if uniqkey in list(result.keys()):

                result[uniqkey]["evidence"]["evidenceCodes"].append(
                    item.eco.ecoid)

            else:
                print(item.reference.pmid)

                ref_dbentity = DBSession.query(Dbentity).filter(
                    Dbentity.dbentity_id == item.reference.pmid).all()

                if item.reference.pmid:
                    pubidref = "PMID:" + str(item.reference.pmid)
                    sgdref = "SGD:" + str(ref_dbentity)
                else:
                    pubidref = "SGD:" + str(ref_dbentity.sgdid)

                if item.disease_qualifier == 'not':
                    obj["negation"] = "not"

                obj["DOid"] = str(item.disease.doid)
                obj["objectRelation"]["associationType"] = item.ro.display_name
                obj["objectRelation"]["objectType"] = "gene"
                obj["objectId"] = "SGD:" + str(item.dbentity.sgdid)
                obj["dateAssigned"] = item.date_created.strftime(
                    "%Y-%m-%dT%H:%m:%S-00:00")
                obj["evidence"]["evidenceCodes"].append(item.eco.ecoid)
                obj["evidence"]["publication"]["publicationId"] = pubidref
                obj["dataProvider"].append({
                    "crossReference": {
                        "id": "SGD:" + str(item.dbentity.sgdid),
                        "pages": ["gene/disease"]
                    },
                    "type": "curated"
                })

                result[uniqkey] = obj

    if len(list(result.keys())) > 0:
        print("# objs:" + str(len(list(result.keys()))))
        output_obj = get_output(list(result.values()))
        file_name = 'SGD' + SUBMISSION_VERSION + 'disease_association.json'
        json_file_str = os.path.join(local_dir, file_name)
        if (output_obj):
            with open(json_file_str, 'w+') as res_file:
                res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))

if __name__ == '__main__':
    get_disease_association_data()
