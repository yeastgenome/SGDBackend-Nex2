import os, re
import json
import concurrent.futures
from src.models import Phenotypeannotation, DBSession
from src.data_helpers import get_output
from sqlalchemy import create_engine


engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
DBSession.configure(bind=engine)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_7.0.0_')

local_dir = 'scripts/dumping/alliance/data/'

COND_TO_ZECO = {"treatment": "ZECO:0000105", #biological treatment
"radiation":"ZECO:0000208", #radiation
"chemical":"ZECO:0000111", #chemical treatment
"assay":"ZECO:0000104", #experimental conditions
"media": "ZECO:0000238",  #chemical treatment by environment
"temperature":"ZECO:0000160", #temperature exposure
"phase": "ZECO:0000104"}  #experimental conditions

def get_phenotypephenotype_data():

    phenotype_data = DBSession.query(Phenotypeannotation).all()
    #phenotype_data = DBSession.query(Phenotypeannotation).filter_by(dbentity_id='1285516').all() # RPB2 test
    result = []
    print(("computing " + str(len(phenotype_data)) + " phenotypes"))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        for item in phenotype_data:
            print('Phenoannotation ID:' + str(item.annotation_id))
            obj = {
                "objectId": "",
                "phenotypeTermIdentifiers": [],
                "phenotypeStatement": "",
                "dateAssigned": ""
                }
            if item.allele:
                alleleObj = {
                "objectId": "",
                "phenotypeTermIdentifiers": [],
                "phenotypeStatement": "",
                "dateAssigned": ""
                }

            conditions = item.to_dict()[0]['properties']

            if len(conditions) > 0 :
                conditionList = []
                combinedObj = []
                for cond in conditions:
                    class_type = cond['class_type'].lower()
                    print ('type-'+ class_type +"*")
                    if class_type == 'bioitem':
                        continue
                    else: 
                        cObj = {"conditionClassId": COND_TO_ZECO[class_type]}
                        if class_type == 'chemical':
                            cObj["conditionStatement"] = class_type + ":" + cond['bioitem']['display_name']

                            if str(cond['bioitem']['link']) != 'None':
                                print('url:' + str(cond['bioitem']['link']))
                                urllist= str(cond['bioitem']['link']).split("/")
                                chebi_id = urllist[2].split("'")[0]
                                cObj["chemicalOntologyId"] = chebi_id
                            if cond['unit']:
                                cObj["conditionQuantity"] = cond['concentration']+ " " + cond['unit']
                        else:
                            cObj["conditionStatement"] = class_type + ":" + cond['note']
                            if cond['unit'] and class_type == 'temperature':
                                if re.match(", ", cond['note']):
                                    cObj["conditionQuantity"] = cond["note"].split(", ")[1]
                                else:
                                    cObj["conditionQuantity"] = cond["note"]
                                    print ("COND:" + cond['note'])
                        combinedObj.append(cObj) 
                conditionList.append({'conditionRelationType':'has_condition', 'conditions':combinedObj})

                if item.allele:
                    alleleObj["conditionRelations"] = conditionList
                else:
                    obj["conditionRelations"] = conditionList
            if item.phenotype.qualifier:
                pString = item.phenotype.qualifier.display_name
                obj["phenotypeTermIdentifiers"].append({
                    "termId":
                    str(item.phenotype.qualifier.apoid),
                    "termOrder":
                    1
                })
                if item.allele: #add phenotype to allele obj
                    alleleObj["phenotypeTermIdentifiers"].append({
                        "termId":
                        str(item.phenotype.qualifier.apoid),
                        "termOrder":
                        1
                 })
                if item.phenotype.observable:
                    pString = pString + " " + item.phenotype.observable.display_name
                    obj["phenotypeTermIdentifiers"].append({
                        "termId":
                        str(item.phenotype.observable.apoid),
                        "termOrder":
                        2
                    })
                    if item.allele: # adding observable to allele pheno obj
                        alleleObj["phenotypeTermIdentifiers"].append({
                        "termId":
                        str(item.phenotype.observable.apoid),
                        "termOrder":
                        2
                    })

            else:
                if item.phenotype.observable:
                    pString = item.phenotype.observable.display_name
                    obj["phenotypeTermIdentifiers"].append({
                        "termId":
                        str(item.phenotype.observable.apoid),
                        "termOrder":
                        1
                    })
                    if item.allele: # adding only observable to allele pheno obj
                        alleleObj["phenotypeTermIdentifiers"].append({
                        "termId":
                        str(item.phenotype.observable.apoid),
                        "termOrder":
                        1
                    })

            obj["objectId"] = "SGD:" + str(item.dbentity.sgdid)
            obj["phenotypeStatement"] = pString

            print ('Annotation:' + pString) 

            if item.reference.pmid:
                pubId = "PMID:" + str(item.reference.pmid)
            else:
                pubId = "SGD:" + str(item.reference.sgdid)
            obj["evidence"] = {"publicationId": pubId}
            obj["dateAssigned"] = item.date_created.strftime(
                "%Y-%m-%dT%H:%m:%S-00:00")
            
            if item.allele:
               # add allele SGDID to gene-level phenotype if there is an allele; ADD STRAIN_BACKGROUND too? -- NCBI TaxonID? if NOT 'OTHER'
                obj["primaryGeneticEntityIDs"] = ["SGD:" + item.allele.sgdid]
                # adding basic info to allele obj # ## already added conditions to it #
                # alleleObj["primaryGeneticEntityIDs"] = ["SGD:" + item.allele.sgdid]
                alleleObj["objectId"] = "SGD:" + item.allele.sgdid
                alleleObj["phenotypeStatement"] = pString
                alleleObj["evidence"] = {"publicationId": pubId}
                alleleObj["dateAssigned"] = item.date_created.strftime(
                "%Y-%m-%dT%H:%m:%S-00:00")
            result.append(obj)

            if item.allele: # adding allele level phenotype if it exists
                result.append(alleleObj)
        if len(result) > 0:
            output_obj = get_output(result)
            file_name = 'SGD' + SUBMISSION_VERSION + 'phenotype.json'
            json_file_str = os.path.join(local_dir, file_name)
            with open(json_file_str, 'w+') as res_file:
                res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))

    DBSession.close()

if __name__ == '__main__':
    get_phenotypephenotype_data()
