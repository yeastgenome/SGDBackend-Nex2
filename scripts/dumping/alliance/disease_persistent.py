""" Aggregate disease data for Alliance data submission

The script extracts data from ajson file into a dictionary that is written to another json file.
The json file is submitted to Alliance FOR THE PERSISTENT STORE for futher processing

This file requires packages listed in requirements.txt file and env.sh file.
The env.sh file contains environment variables

This file can be imported as a modules and contains the following functions:
    get_disease_association_data
"""
from dis import dis
import os
import sys
import json
import re
import concurrent.futures
from datetime import datetime
from src.models.models import DBSession, Diseaseannotation, Diseasesupportingevidence, Dbentity, Straindbentity, Locussummary
from src.data_helpers.data_helpers import get_eco_ids, get_pers_output, SUBMISSION_VERSION
from sqlalchemy import create_engine, and_

engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
DBSession.configure(bind=engine)

SUBMISSION_TYPE = "disease_gene_ingest_set"

eco_code_dict = {"236289": "IGI", "236296": "IMP", "236356": "ISS"}
""" EX: {
    "disease_gene_ingest_set": [
        {
            "evidence_codes": [
                "ECO:0000250",
                "ECO:0000316"
            ],
            "annotation_type": "manually curated",
            "single_reference": "PMID:21145416",
            "data_provider": "SGD",
            "object": "DOID:10588",
            "created_by": "SGD:STACIA",
            "modified_by": "SGD:STACIA",
            "creation_date": "2018-04-25T14:04:15-00:00",
            "subject": "SGD:S000001671",
            "related_notes": [{"free_text":"Yeast PXA2 is homologous to human ABCD1 and ABCD2, and has been used to study adrenoleukodystrophy",
            "note_type":"disease_summary",
            "internal":"false"}],
            "predicate": "is_implicated_in",
            "SGD_strain_background":"SGD:SXXXXXXXX",
            "with": [
                "HGNC:61",
                "HGNC:66"
            ]
        }
    ]
}
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
                "object": "",
                "single_reference": "",
                "subject": "",
                "created_by": "",
                "modified_by": "",
                #  "with": [],
                "data_provider": "SGD",
                "evidence_codes": [],
                "predicate": "",
                "creation_date":"",
                "annotation_type":"",
                "sgd_strain_background":""
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

                result[uniqkey]["evidence_codes"].append(
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
               # print('created by:'+ item.created_by)
                obj["object"] = str(item.disease.doid)
                obj["predicate"] = item.ro.display_name
              #  obj["objectRelation"]["objectType"] = "gene"
                obj["subject"] = "SGD:" + str(item.dbentity.sgdid)
                obj["creation_date"] = item.date_created.strftime(
                    "%Y-%m-%dT%H:%m:%S-00:00")
                obj["evidence_codes"].append(item.eco.ecoid)
                obj["single_reference"] = pubidref
                #            obj["with"] = evidence_list
            #    obj["data_provider"] = "SGD",
            #    obj["annotation_type"] = item.annotation_type
                obj["created_by"] = "SGD:" + item.created_by
                obj["modified_by"] = "SGD:" +item.created_by
                obj['internal'] = False
           #     obj["sgd_strain_background"] = 'SGD:'+ item.strain.sgdid

             #   obj["disease_annotation_summary"]: item.  # need to add disease summary
                if item.taxonomy_id and item.taxonomy.display_name != 'Saccharomyces cerevisiae':
                    strainObj = DBSession.query(Straindbentity).filter(Straindbentity.taxonomy_id == item.taxonomy_id).one() 
                    obj["sgd_strain_background"] = "SGD:" + strainObj.sgdid
                elif item.taxonomy_id and item.taxonomy.display_name == 'Saccharomyces cerevisiae':
                    obj["sgd_strain_background"] = "SGD:S000203479" 

                if item.annotation_type == 'manually curated':
                    obj["annotation_type"] = 'manually_curated'
                else:
                    obj["annotation_type"] = item.annotation_type

            ## disease summaries from locussummary table, subtype='Disease' if there is one##
                disSumObj = DBSession.query(Locussummary).filter(Locussummary.summary_type == 'Disease', Locussummary.locus_id==item.dbentity_id).one_or_none()
                if disSumObj is not None:
                    obj["related_notes"] = [{"free_text":disSumObj.text,"note_type":"disease_summary","internal":False}] 
                
                result[uniqkey] = obj

    if len(list(result.keys())) > 0:
        print("# objs:" + str(len(list(result.keys()))))
        output_obj = get_pers_output(SUBMISSION_TYPE, list(result.values()))
        file_name = 'data/SGD' + SUBMISSION_VERSION + 'persist_disease_association.json'
        json_file_str = os.path.join(root_path, file_name)
        if (output_obj):
            with open(json_file_str, 'w+') as res_file:
                res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))

if __name__ == '__main__':
    get_disease_association_data(THIS_FOLDER)