""" Affected Gene Model information for Alliance data submission

The script extracts data into a dictionary that is written to a json file.
The json file is submitted to Alliance for futher processing

This file requires packages listed in requirements.txt file and env.sh file.
The env.sh file contains environment variables

08/09/20 - initially getting Strain background information for 12 common lab strains for AGM

"""

import os
import json
import re, sys
import time
from random import randint
from datetime import datetime
from sqlalchemy import create_engine, and_, inspect
import concurrent.futures
from src.models import LocusAlias, Dbentity, DBSession, Straindbentity, Referencedbentity
from src.data_helpers import get_output, get_locus_alias_data

engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_1.0.0.0_')
DBSession.configure(bind=engine)
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

"""
combine_panther_locus_list
get_panther_sgdids
Locusdbentity.get_s288c_genes
output_obj

SO types returned from get_s288c_genes:
SSO:0001268	snRNA gene
SO:0001272	tRNA gene
SO:0000718	blocked reading frame
SO:0000111	transposable element gene
SO:0002026	intein encoding region
SO:0000296	origin of replication
SO:0001643	telomerase RNA gene
SO:0001637	rRNA gene
SO:0000036	matrix attachment site
SO:0000577	centromere
SO:0000436	ARS
SO:0000624	telomere
SO:0005855	gene group
SO:0001984	silent mating type cassette array
SO:0001789	mating type region
SO:0000336	pseudogene
SO:0000236	ORF
SO:0001267	snoRNA gene
SO:0001263	ncRNA gene
SO:0000286	long terminal repeat (keep for non-gene)
SO:0000186	LTR retrotransposon (keep for non-gene)

AGM object:
# requirements -- name, primaryId and taxonId

properties": {
    "primaryID": {
      "$ref" : "../globalId.json#/properties/globalId",
      "description": "The prefixed primary (MOD) ID for an entity. For internal AGR use, e.g. FB:FBgn0003301, MGI:87917."
    },
    "name": {
      "type": "string",
      "description": "The name of the entity."
    },
    "subtype":{
      "enum": ["strain", "genotype"],
      "description": "a typing field that further qualifies an affectedGenomicModel as a strain or genotype.  This field is optional because some submissions will simply be submitting affectedGenomicModels that are more than just strains or genotypes, but fill the same biological model space as strains and genotypes at this time."
    },
    "taxonId": {
      "$ref" : "../globalId.json#/properties/globalId",
      "description" : "The taxonId for the species of the genotype entity."
    },
    "crossReference": {
      "description":"MOD database cross references for each genotype;the link back to the MOD.",
      "$ref" : "../crossReference.json#"
    },
    "synonyms": {
      "type": "array",
      "items": {
         "type": "string"
      },
    "uniqueItems": true
    },
    "secondaryIds":{
      "type": "array",
      "items": {
         "type": "string"
      },
    "uniqueItems": true
    },
    "affectedGenomicModelComponents": {
      "description": "Collection of genomic components that make up a model, ie: 'allele', each with a zygosity",
       "type": "array",
       "items": {
         "$ref" : "affectedGenomicModelComponent.json#"
       },
      "uniqueItems": true
    },
    "sequenceTargetingReagentIDs": {
      "description": "Collection of sequence targeting reagent components that make up a genotype.",
       "type": "array",
       "items": {
         "$ref" : "../globalId.json#/properties/globalId"
       },
      "uniqueItems": true
    },
    "parentalPopulationIDs": { "description": "Collection of background components that make up a genotype.",
       "type": "array",
       "items": {
         "$ref" : "../globalId.json#/properties/globalId"
       },
      "uniqueItems": true
     }
  }

SO_TYPES_TO_EXCLUDE = [
    'SO:0000186', 'SO:0000577', 'SO:0000286', 'SO:0000296', 'SO:0005855',
    'SO:0001984', 'SO:0002026', 'SO:0001789', 'SO:0000436', 'SO:0000624'
]

"""

#STRAINS = [
#    'BY4742', 'BY4741', 'S288C', 'CEN.PK', 'D273-10B', 'FL100', 'JK9-3d',
#    'RM11-1a', 'SEY6210', 'SK1', 'Sigma1278b', 'W303', 'X2180-1A', 'Y55'
#]

DEFAULT_TAXID = '559292'


def get_agm_information(root_path):
    """ Extract Affected Gene Model (AGM) information.

    Parameters
    ----------
    root_path
        root directory name path    

    Returns
    --------
    file
        writes data to json file

 datasetSamples = DBSession.query(Datasetsample).filter(
        Datasetsample.biosample.in_(BIOSAMPLE_OBI_MAPPINGS.keys()),
        Datasetsample.dbxref_id != None).all()
    """
    combined_list = DBSession.query(Dbentity).filter(
        Dbentity.subclass == 'STRAIN').all() #,
    #    Dbentity.display_name.in_(STRAINS)).all()

    # combined_list = DBSession.query(LocusAlias).filter(
    #    LocusAlias.locus_id == item.dbentity_id,
    #   LocusAlias.alias_type == 'PANTHER ID').one()
    #combined_list = combine_panther_locus_data(
    #pair_pantherid_to_sgdids(root_path), Locusdbentity.get_s288c_genes())
    print(("computing " + str(len(combined_list)) + " strains"))
    #   sys.exit()

    result = []
    if (len(combined_list) > 0):

        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            for item in combined_list:
                strainobj = DBSession.query(Straindbentity).filter(Straindbentity.dbentity_id == item.dbentity_id).one()
                
                if re.match('NTR', strainobj.taxonomy.taxid):
                  taxon = DEFAULT_TAXID #strainobj.taxonomy.taxid
                else:
                  taxon = strainobj.taxonomy.taxid.split(":")[1]

                obj = {
                    #"primaryID": "",
                    #    "name": "STRING",
                    #    "subtype": "strain",
                    #    "taxonId": "TAX:",
                    #    "crossReference": {"../crossReference.json#"},
                    #    "synonyms": [],
                    #    "secondaryIds": []
                }
                obj["primaryID"] = "SGD:" + item.sgdid
                obj["name"] = item.display_name
                obj["subtype"] = "strain"
                obj["taxonId"] = "NCBITaxon:" + taxon # DEFAULT_TAXID

                # item = combined_list[item_key]  #["locus_obj"]

                obj["crossReference"] = {
                    "id": "SGD:" + item.sgdid,
                    "pages": ["strain"]
                }

                result.append(obj)

            if (len(result) > 0):
                output_obj = get_output(result)

                file_name = 'data/SGD' + SUBMISSION_VERSION + 'affectedGeneModel.json'
                json_file_str = os.path.join(root_path, file_name)
                with open(json_file_str, 'w+') as res_file:
                    res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))


if __name__ == '__main__':
    get_agm_information(THIS_FOLDER)
