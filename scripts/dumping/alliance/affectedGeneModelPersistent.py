import os
import json
import re, sys
from sqlalchemy import create_engine
import concurrent.futures

from src.models import Dbentity, DBSession, Straindbentity, Taxonomy
from src.data_helpers import get_pers_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_5.4.0_')
LINKML_VERSION = os.getenv('LINKML_VERSION', 'v1.7.5')
DBSession.configure(bind=engine)
local_dir = 'scripts/dumping/alliance/data/'
DEFAULT_TAXID = '559292'
SUBMISSION_TYPE= 'agm_ingest_set'

def get_agm_information():

    strains_in_db = DBSession.query(Straindbentity).order_by(Straindbentity.display_name).all()
    filtered_strains = list([strain for strain in strains_in_db if
                                 strain.strain_type == 'Alternative Reference' or strain.strain_type == 'Reference' or (
                                         strain.taxonomy.taxid == 'TAX:4932' and strain.display_name.upper() == 'OTHER')])
    print(("computing " + str(len(filtered_strains)) + " strains"))
    result = []
    if (len(strains_in_db) > 0):

        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            for item in filtered_strains:
                strainobj = DBSession.query(Straindbentity).filter(Straindbentity.dbentity_id == item.dbentity_id).one()
                if re.match('NTR', strainobj.taxonomy.taxid):
                    taxon = DEFAULT_TAXID
                else:
                    taxon = strainobj.taxonomy.taxid.split(":")[1]
                obj = {}
                obj["curie"] = "SGD:" + item.sgdid
                obj["name"] = item.display_name
                obj["subtype_name"] = "strain"
                obj["taxon_curie"] = "NCBITaxon:" + taxon
                obj["internal"] = False
                obj["created_by_curie"] = "SGD"
                obj["updated_by_curie"] = "SGD"
                #obj["data_provider_name"] = "SGD"
                obj["data_provider_dto"] = {
                    "source_organization_abbreviation": "SGD",
                    "internal": False}

                result.append(obj)

            if (len(result) > 0):
                output_obj = get_pers_output(SUBMISSION_TYPE, result, LINKML_VERSION)
                file_name = 'SGD' + SUBMISSION_VERSION + 'agmPersistent.json'
                json_file_str = os.path.join(local_dir, file_name)
                with open(json_file_str, 'w+') as res_file:
                    res_file.write(json.dumps(output_obj, indent=4, sort_keys=False))

    DBSession.close()


if __name__ == '__main__':
    get_agm_information()
