import os
import json
import concurrent.futures
from src.models import DBSession, Diseaseannotation, Diseasesupportingevidence, Dbentity, Straindbentity, Locussummary
from src.data_helpers import get_pers_output
from sqlalchemy import create_engine

engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_1.5.0_')
DBSession.configure(bind=engine)

local_dir = 'scripts/dumping/alliance/data/'

LINKML_VERSION = "linkml_version"+": " + os.getenv('LINKLM_VERSION', '1.5.0') +","+ '\n'
SUBMISSION_TYPE = "disease_gene_ingest_set"

eco_code_dict = {"236289": "IGI", "236296": "IMP", "236356": "ISS"}

"""
https://github.com/alliance-genome/agr_curation_schema/blob/main/test/data/disease_gene_test.json
"""


def get_disease_association_data():
    result = {}
    disease_data = DBSession.query(Diseaseannotation).all()
    print(("computing " + str(len(disease_data)) + " diseases"))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        for item in disease_data:

            obj = {
                "do_term_curie": "",
                "reference_curie": "",
                "gene_curie": "",
                "created_by_curie": "",
                "updated_by_curie": "",
                "data_provider_name": "SGD",
                "evidence_code_curies": [],
                "disease_relation_name": "",
                "date_created":"",
                "annotation_type_name":"",
                "sgd_strain_background_curie":""
            }

            evidence_list = []

            supporting_evidences = DBSession.query(
                Diseasesupportingevidence).filter_by(
                    annotation_id=item.annotation_id).with_entities(
                        Diseasesupportingevidence.dbxref_id).all()

            if len(supporting_evidences) > 0:
                for evidence in supporting_evidences:
                    evidence_list.append(evidence.dbxref_id)
                obj["with_gene_curies"] = evidence_list

            uniqkey = str(item.disease.disease_id) + "_" + str(
                item.dbentity.sgdid) + "_" + str(
                    item.reference.pmid) + "_" + "_".join(evidence_list)


            if uniqkey in list(result.keys()):
                result[uniqkey]["evidence_code_curies"].append(
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

                obj["do_term_curie"] = str(item.disease.doid)
                obj["disease_relation_name"] = item.ro.display_name
                obj["gene_curie"] = "SGD:" + str(item.dbentity.sgdid)
                obj["date_created"] = item.date_created.strftime("%Y-%m-%dT%H:%m:%S-00:00")
                obj["evidence_code_curies"].append(item.eco.ecoid)
                obj["reference_curie"] = pubidref
                obj["created_by_curie"] = "SGD:" + item.created_by
                obj["updated_by_curie"] = "SGD:" +item.created_by
                obj['internal'] = False

                if item.taxonomy_id and item.taxonomy.display_name != 'Saccharomyces cerevisiae':
                    strainObj = DBSession.query(Straindbentity).filter(Straindbentity.taxonomy_id == item.taxonomy_id).one() 
                    obj["sgd_strain_background_curie"] = "SGD:" + strainObj.sgdid
                elif item.taxonomy_id and item.taxonomy.display_name == 'Saccharomyces cerevisiae':
                    obj["sgd_strain_background_curie"] = "SGD:S000203479"

                if item.annotation_type == 'manually curated':
                    obj["annotation_type_name"] = 'manually_curated'
                else:
                    obj["annotation_type_name"] = item.annotation_type

                ## disease summaries from locussummary table, subtype='Disease' if there is one##
                disSumObj = DBSession.query(Locussummary).filter(Locussummary.summary_type == 'Disease', Locussummary.locus_id==item.dbentity_id).one_or_none()
                if disSumObj is not None:
                    obj["note_dtos"] = [{"free_text":disSumObj.text, "note_type_name":"disease_summary","internal":False}]
                
                result[uniqkey] = obj

    if len(list(result.keys())) > 0:
        print("# objs:" + str(len(list(result.keys()))))
        output_obj = get_pers_output(SUBMISSION_TYPE, list(result.values()))
        file_name = 'SGD' + SUBMISSION_VERSION + 'persist_disease_association.json'
        json_file_str = os.path.join(local_dir, file_name)
        if (output_obj):
            with open(json_file_str, 'w+') as res_file:
                res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))

if __name__ == '__main__':
    get_disease_association_data()
