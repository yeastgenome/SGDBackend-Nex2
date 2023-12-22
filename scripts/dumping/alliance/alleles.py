import os
import json
import re, sys
from sqlalchemy import create_engine
from src.models import Alleledbentity, DBSession
from src.data_helpers import get_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_7.0.0_')
DBSession.configure(bind=engine)
local_dir = 'scripts/dumping/alliance/data/'
DEFAULT_TAXID = '559292'

def get_allele_information():

    print("getting Alleles")
    alleleObjList = DBSession.execute(
        f"select ad.dbentity_id, db.sgdid,  ad.description, db.display_name, "
        f"aa.display_name, s.display_name "
        f"from nex.alleledbentity ad "
        f"inner join nex.dbentity db on ad.dbentity_id = db.dbentity_id "
        f"inner join nex.so s on ad.so_id = s.so_id "
        f"left join nex.allele_alias aa on ad.dbentity_id = aa.allele_id "
        f"left join nex.locus_allele la on la.allele_id = ad.dbentity_id ").fetchall()

    print(("computing " + str(len(alleleObjList)) + " alleles"))
    result = []
    if (len(alleleObjList) > 0):

        try:
            for alleleObj in alleleObjList:

                if re.search("\<sub\>", alleleObj[3]) :
                    print("skipping: " + alleleObj[3])
                    continue
                obj = {}
                obj["primaryId"] = "SGD:" + str(alleleObj[1])
                obj["symbolText"] = alleleObj[3]
                obj["symbol"] = alleleObj[3]

                if alleleObj[2] is not None:
                    if alleleObj[2] != "":
                        obj["description"] = alleleObj[2]
                obj["taxonId"] = "NCBITaxon:" + DEFAULT_TAXID

                if alleleObj[4] is not None:
                    obj["synonyms"] = [alleleObj[4]]

                obj["crossReferences"] = [{
                    "id": "SGD:" + str(alleleObj[1]),
                    "pages": ["allele"]
                }]

                alleleRefList = DBSession.execute(
                    f"select rdb.pmid "
                    f"from nex.alleledbentity ad "
                    f"left join nex.literatureannotation ar on ad.dbentity_id = ar.dbentity_id "
                    f"left join nex.referencedbentity rdb on ar.reference_id = rdb.dbentity_id "
                    f"where ad.dbentity_id ="+ str(alleleObj[0])).fetchall()

                if alleleRefList:
                    obj['references'] = []
                    for x in alleleRefList:
                        if x not in obj['references'] and x is not None:
                            obj['references'].append("PMID:" + str(x[0]))

                alleleGeneList = DBSession.execute(
                    f"select db.sgdid "
                    f"from nex.alleledbentity ad "
                    f"left join nex.locus_allele la on la.allele_id = ad.dbentity_id "
                    f"inner join nex.dbentity db on db.dbentity_id = la.locus_id "
                    f"where ad.dbentity_id ="+ str(alleleObj[0])).fetchall()

                if alleleGeneList:
                    for gene in alleleGeneList:
                        if gene is not None:
                            obj["alleleObjectRelations"] = [{
                                "objectRelation": {
                                "associationType": "allele_of",
                                "gene": "SGD:" + str(gene[0])
                                }
                            }]
                result.append(obj)
        except Exception as e:
            print(e)

    if (len(result) > 0):
        output_obj = get_output(result)
        file_name = 'SGD' + SUBMISSION_VERSION + 'alleles.json'
        json_file_str = os.path.join(local_dir, file_name)
        with open(json_file_str, 'w+') as res_file:
            res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))

    DBSession.close()

if __name__ == '__main__':
    get_allele_information()
