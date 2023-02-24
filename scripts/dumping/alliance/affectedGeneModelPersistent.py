import os
import json
import re, sys
from sqlalchemy import create_engine
import concurrent.futures

from src.models import Dbentity, DBSession, Straindbentity
from src.data_helpers import get_pers_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_5.4.0_')
LINKML_VERSION = os.getenv('LINKML_VERSION', 'v1.5.0')
DBSession.configure(bind=engine)
local_dir = 'scripts/dumping/alliance/data/'
DEFAULT_TAXID = '559292'
SUBMISSION_TYPE= 'agm_ingest_set'

def get_agm_information():

    combined_list = DBSession.query(Dbentity).filter(Dbentity.subclass == 'STRAIN').all()
    print(("computing " + str(len(combined_list)) + " strains"))

    result = []
    if (len(combined_list) > 0):

        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            for item in combined_list:
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
                obj["data_provider_name"] = "SGD"

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
