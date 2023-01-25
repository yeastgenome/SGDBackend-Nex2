""" Affected Gene Model information for Alliance data submission for persistent store

The script extracts data into a dictionary that is written to a json file.
The json file is submitted to Alliance for futher processing

This file requires packages listed in requirements.txt file and env.sh file.
The env.sh file contains environment variables

08/09/20 - initially getting Strain background information for 12 common lab strains for AGM
03/2022 - getting all strain backgrounds in database

"""

import os
import json
import re, sys
from sqlalchemy import create_engine
import concurrent.futures

#from src.disease.disease_persistent import SUBMISSION_TYPE
from src.models.models import LocusAlias, Dbentity, DBSession, Straindbentity, Referencedbentity
from src.data_helpers.data_helpers import get_output, get_locus_alias_data, get_pers_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600)
DBSession.configure(bind=engine)
local_dir = 'scripts/dumping/alliance/data/'

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
# requirements -- name, primaryId and taxon, subtype (strain), internal (false/true)

{
    "agm_ingest_set": [
        {"curie":"SGD:S00000xxxx", 
        "taxon": "NCBITaxon:xxxx",
        "created_by": "SGD:CURATOR",
        "modified_by": "SGD:CURATOR",
        "internal":"false",
        "name":"display_name",
        "synonyms": [{"synonym":"name","internal":"false"}],
        "secondary_identifiers":{"YYY","ZZZZ"},
        "references":[],
        "subtype":"strain",
        "creation_date":"date",
        "data_provider":"SGD"
        }
    ]
    
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
SUBMISSION_TYPE= 'agm_ingest_set'

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
                    taxon = DEFAULT_TAXID   #strainobj.taxonomy.taxid
                else:
                    taxon = strainobj.taxonomy.taxid.split(":")[1]

                obj = {#"internal":False
                    #"primaryID": "",
                    #    "name": "STRING",
                    #    "subtype": "strain",
                    #    "taxonId": "TAX:",
                    #    "crossReference": {"../crossReference.json#"},
                    #    "synonyms": [],
                    #    "secondaryIds": []
                }
                obj["curie"] = "SGD:" + item.sgdid
                obj["name"] = item.display_name
                obj["subtype"] = "strain"
                obj["taxon"] = "NCBITaxon:" + taxon #strainobj.taxonomy.taxid
                obj["internal"] = False
                obj["data_provider"] = "SGD"
              #  obj["creation_date"] = item.date
              #  obj["created_by"] = item.created_by
              #  obj[""]

                # item = combined_list[item_key]  #["locus_obj"]

            #    obj["crossReference"] = {
            #        "id": "SGD:" + item.sgdid,
            #        "pages": ["strain"]
            #    }

                result.append(obj)

            if (len(result) > 0):
                output_obj = get_pers_output(SUBMISSION_TYPE, result)

                file_name = 'SGD' + SUBMISSION_VERSION + 'agmPersistent.json'

                json_file_str = os.path.join(local_dir, file_name)

                with open(json_file_str, 'w+') as res_file:
                    res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))


if __name__ == '__main__':
    get_agm_information()
