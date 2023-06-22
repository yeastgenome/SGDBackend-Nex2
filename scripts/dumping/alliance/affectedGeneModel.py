import os
import json
import re, sys

from sqlalchemy import create_engine
import concurrent.futures
from src.models import Dbentity, DBSession, Straindbentity
from src.data_helpers import get_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
DBSession.configure(bind=engine)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_5.4.0_')
local_dir = 'scripts/dumping/alliance/data/'
DEFAULT_TAXID = '559292'


def get_agm_information():

    #combined_list = DBSession.query(Dbentity).filter(Dbentity.subclass == 'STRAIN').all()
    strains_in_db = DBSession.query(Straindbentity).order_by(Straindbentity.display_name).all()
    filtered_strains = list([strain for strain in strains_in_db if
                                 strain.strain_type == 'Alternative Reference' or strain.strain_type == 'Reference' or (
                                         strain.taxonomy.taxid == 'TAX:4932' and strain.display_name.upper() == 'OTHER')])
    print(("computing " + str(len(filtered_strains)) + " strains"))

    result = []
    if (len(filtered_strains) > 0):

        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            for item in filtered_strains:
                strainobj = DBSession.query(Straindbentity).filter(Straindbentity.dbentity_id == item.dbentity_id).one()
                
                if re.match('NTR', strainobj.taxonomy.taxid):
                  taxon = DEFAULT_TAXID
                else:
                  taxon = strainobj.taxonomy.taxid.split(":")[1]

                obj = {}
                obj["primaryID"] = "SGD:" + item.sgdid
                obj["name"] = item.display_name
                obj["subtype"] = "strain"
                obj["taxonId"] = "NCBITaxon:" + taxon
                obj["crossReference"] = {
                    "id": "SGD:" + item.sgdid,
                    "pages": ["strain"]
                }

                result.append(obj)

            if (len(result) > 0):
                output_obj = get_output(result)
                local_file_name = 'SGD' + SUBMISSION_VERSION + 'affectedGeneModel.json'
                json_file_str = os.path.join(local_dir, local_file_name)
                with open(json_file_str, 'w+') as res_file:
                    res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))

    DBSession.close()


if __name__ == '__main__':
    get_agm_information()
