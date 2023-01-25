""" Aggregate phenotype data for Alliance data submission

The script extracts data from 1 table into a dictionary that is written to a json file.
The json file is 
submitted to Alliance for futher processing

This file requires packages listed in requirements.txt file and env.sh file.
The env.sh file contains environment variables

This file can be imported as a modules and contains the following functions:
    get_phenotypephenotype_data
"""
import os, re
import sys
import json
import concurrent.futures
from src.models import Dbentity, Phenotypeannotation, PhenotypeannotationCond, Chebi, DBSession
from src.data_helpers.data_helpers import get_output

local_dir = 'scripts/dumping/alliance/data/'

COND_TO_ZECO = {"treatment": "ZECO:0000105", #biological treatment
"radiation":"ZECO:0000208", #radiation
"chemical":"ZECO:0000111", #chemical treatment
"assay":"ZECO:0000104", #experimental conditions
"media": "ZECO:0000238",  #chemical treatment by environment
"temperature":"ZECO:0000160", #temperature exposure
"phase": "ZECO:0000104"}  #experimental conditions

#ECO_ID_TO_TERM = {
#    "ZECO:0000105":"biological treatment",
#"ZECO:0000208":"radiation",
#"ZECO:0000111", #chemical treatment
#"ZECO:0000104", #experimental conditions
##"ZECO:0000238",  #chemical treatment by environment
#"ZECO:0000160", #temperature exposure
#}""" 

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
            if item.allele:  #make allele object if there is an allele associated with a phenotype #
                alleleObj = {
                "objectId": "",
                "phenotypeTermIdentifiers": [],
                "phenotypeStatement": "",
                "dateAssigned": ""
                }
            ## Check for conditions; add to allele if there is one, otherwise add to gene ##
 #           print("ITEM: " + str(vars(item)))
            conditions = item.to_dict()[0]['properties']
          #  print ('properties: ' + str(conditions))

           # conditionObjs = DBSession.query(PhenotypeannotationCond).filter(PhenotypeannotationCond.annotation_id==item.annotation_id).all()
          #  print ('annotation id:' + str(item.annotation_id) + " Num conditions:" + str(len(conditionObjs))) 
            if len(conditions) > 0 :
                #print ("number of experiment conditions: " + str(item.count_experiment_categories))
                conditionList = []
                combinedObj = []

                for cond in conditions:
                  #  print('conditions: ' + str(vars(cond)))

                    class_type = cond['class_type'].lower()
                    print ('type-'+ class_type +"*")

                    if class_type == 'bioitem':
                     #   print('skipping bioitem')
                        continue
                    else: 
                        cObj = {"conditionClassId": COND_TO_ZECO[class_type]}
                    # special for chemical #
                        #print ('inside class type:' + class_type)
                        if class_type == 'chemical':
                            cObj["conditionStatement"] = class_type + ":" + cond['bioitem']['display_name']

                            if str(cond['bioitem']['link']) != 'None': # CHEBI ID exists 
                                print('url:' + str(cond['bioitem']['link']))
                                urllist= str(cond['bioitem']['link']).split("/")
                                chebi_id = urllist[2].split("'")[0]
                              #  print('chebi:' + chebi_id) 
                                cObj["chemicalOntologyId"] = chebi_id # "CHEBI:29321"

                            if cond['unit']:
                                cObj["conditionQuantity"] = cond['concentration']+ " " + cond['unit']

                        else: # for all non-chemicals #
                            cObj["conditionStatement"] = class_type + ":" + cond['note']
                   # print(cond.condition_class + ":" + cond.condition_name)

                            if cond['unit'] and class_type == 'temperature':
                                if re.match(", ", cond['note']):
                                    cObj["conditionQuantity"] = cond["note"].split(", ")[1]
                                else:
                                    cObj["conditionQuantity"] = cond["note"]
                                    print ("COND:" + cond['note']) 

                   # if cond.condition_class == 'chemical':  # get ChEBI ID
                   #     chebiObj = DBSession.query(Chebi).filter_by(display_name = cond.condition_name).all()
                   #     #print(chebiObj)
                   #     if len(chebiObj) > 1: ## more than one ChEBI ID, then take ONLY the is_obsolete='false'
                    #        print(str(item.annotation_id) + ":" + cond.condition_name + " has multiple ChEBI IDs")
                    #        for eachObj in chebiObj:
                    ##            if eachObj.is_obsolete == 'true':
                    #                chebiObj.remove(eachObj)
                     #   elif len(chebiObj) == 0:
                   #         print(str(item.annotation_id) + ":" + cond.condition_name + " has no ChEBI ID")
                   #         next

                   #     if len(chebiObj) == 1:   
                   #         if chebiObj[0].format_name:
                   #             cObj["chemicalOntologyId"] = chebiObj[0].format_name
                   #         else:
                   #             print(str(item.annotation_id) + ":" + cond.condition_name)
                   #             print ("NO or OBSOLETE CHEBI term")
                        combinedObj.append(cObj) 
                conditionList.append({'conditionRelationType':'has_condition', 'conditions':combinedObj})

                if item.allele:
                    alleleObj["conditionRelations"] = conditionList
                #    obj["primaryGeneticEntityIDs"] = ["SGD:" + item.allele.sgdid]
                else:
                    obj["conditionRelations"] = conditionList 
                   # obj["primaryGeneticEntityIDs"] = ["SGD:" + str(item.dbentity.sgdid)]

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
          #  else:
          #      print("no allele for " + item.dbentity.display_name + " pheno:" + pString)
        if len(result) > 0:
            output_obj = get_output(result)
            file_name = 'SGD' + SUBMISSION_VERSION + 'phenotype.json'
            json_file_str = os.path.join(local_dir, file_name)
            with open(json_file_str, 'w+') as res_file:
                res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))

if __name__ == '__main__':
    get_phenotypephenotype_data()
