import os
import json
import re, sys
from sqlalchemy import create_engine
from src.models import DBSession, AllelealiasReference, Referencedbentity, AlleleAlias
from src.data_helpers import get_pers_output, get_allele_synonyms

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_7.0.0_')
LINKML_VERSION = os.getenv('LINKML_VERSION', 'v1.11.0')
DBSession.configure(bind=engine)
SUBMISSION_TYPE = 'allele_ingest_set'
local_dir = 'scripts/dumping/alliance/data/'

DEFAULT_TAXID = '559292'

def get_allele_information():

    print("getting Alleles")

    alleleObjList = DBSession.execute(
        f"select ad.dbentity_id, db.sgdid,  ad.description, db.display_name, "
        f"s.display_name, s.so_id, db.date_created "
        f"from nex.alleledbentity ad "
        f"inner join nex.dbentity db on ad.dbentity_id = db.dbentity_id "
        f"inner join nex.so s on ad.so_id = s.so_id "
        f"left join nex.locus_allele la on la.allele_id = ad.dbentity_id ").fetchall()

    print(("computing " + str(len(alleleObjList)) + " alleles"))

    result = []

    if (len(alleleObjList) > 0):

        try:
            for alleleObj in alleleObjList:

                if re.search("\<sub\>", alleleObj[3]):
                    print("skipping: " + alleleObj[3])
                    continue
                obj = {}
                obj["allele_database_status_dto"]: {
                    "created_by_curie": "SGD",
                    "database_status_name": "Active",
                    "internal": False,
                    "obsolete": False,
                    "updated_by_curie": "SGD"
                }
                obj["internal"] = False
                obj["is_extinct"] = False
                obj["obsolete"] = False
                obj["updated_by_curie"]: "SGD"
                obj["created_by_curie"]: "SGD"
                obj["curie"] = "SGD:" + str(alleleObj[1])
                obj["data_provider_dto"] = {
                    "source_organization_abbreviation": "SGD",
                    "cross_reference_dto": {
                    "referenced_curie": "SGD:" + str(alleleObj[1]),
                    "display_name": "SGD:" + str(alleleObj[1]),
                    "prefix": "SGD",
                    "page_area": "allele",
                    "internal": False
                    },
                    "internal": False,
                    "obsolete": False,
                    "created_by_curie": "SGD",
                    "updated_by_curie": "SGD",
                    }


                obj["allele_symbol_dto"] = {
                        "name_type_name": "nomenclature_symbol",
                        "synonym_scope_name": "exact",
                        "format_text": alleleObj[3],
                        "display_text": alleleObj[3],
                        "internal": False,
                        "obsolete": False,
                        "created_by_curie": "SGD",
                        "updated_by_curie": "SGD"
                }

                obj["allele_mutation_type_dtos"] = [{
                    "mutation_type_curies": ["SO:"+ str(alleleObj[5])],
                    "internal": False,
                    "obsolete": False,
                    "created_by_curie": "SGD",
                    "updated_by_curie": "SGD"
                }]

                allele_alias_list = DBSession.query(AlleleAlias).filter(AlleleAlias.allele_id == alleleObj[0]).all()
                if (len(allele_alias_list) > 0):
                    obj["allele_synonym_dtos"]= get_allele_synonyms(allele_alias_list)

                obj["taxon_curie"] = "NCBITaxon:" + DEFAULT_TAXID
                obj["date_created"] = alleleObj[6].strftime("%Y-%m-%dT%H:%m:%S-00:00")
                obj["date_updated"] = alleleObj[6].strftime("%Y-%m-%dT%H:%m:%S-00:00")

                if str(alleleObj[2]) != "None":
                    obj["note_dtos"] = [{
                        "free_text": str(alleleObj[2]),
                        "note_type_name": "description",
                        "internal": False,
                        "obsolete": False,
                        "created_by_curie": "SGD",
                        "updated_by_curie": "SGD",
                        "date_created": alleleObj[6].strftime("%Y-%m-%dT%H:%m:%S-00:00"),
                        "date_updated": alleleObj[6].strftime("%Y-%m-%dT%H:%m:%S-00:00")
                    }]

                alleleRefList = DBSession.execute(
                    f"select rdb.pmid "
                    f"from nex.alleledbentity ad "
                    f"left join nex.literatureannotation ar on ad.dbentity_id = ar.dbentity_id "
                    f"left join nex.referencedbentity rdb on ar.reference_id = rdb.dbentity_id "
                    f"where ad.dbentity_id =" + str(alleleObj[0])).fetchall()

                if alleleRefList:
                    obj['reference_curies'] = []
                    for x in alleleRefList:
                        if x not in obj['reference_curies'] and x is not None:
                            if str(x[0]) != 'None':
                                obj['reference_curies'].append("PMID:" + str(x[0]))

                # alleleGeneList = DBSession.execute(
                #     f"select db.sgdid "
                #     f"from nex.alleledbentity ad "
                #     f"left join nex.locus_allele la on la.allele_id = ad.dbentity_id "
                #     f"inner join nex.dbentity db on db.dbentity_id = la.locus_id "
                #     f"where ad.dbentity_id =" + str(alleleObj[0])).fetchall()

                # if alleleGeneList:
                #     for gene in alleleGeneList:
                #         if gene is not None:
                #             obj["allele_gene_associations"] = {
                #                     "associationType": "allele_of",
                #                     "gene": "SGD:" + str(gene[0])
                #             }
                result.append(obj)
        except Exception as e:
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
