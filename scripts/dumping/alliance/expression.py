import os
import json
from sqlalchemy import create_engine, and_

from src.models import DBSession, Locusdbentity, Goannotation, Go, Referencedbentity
from src.data_helpers import get_eco_ids, get_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
DBSession.configure(bind=engine)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_5.4.0_')

local_dir = 'scripts/dumping/alliance/data/'

DEFAULT_MMO = 'MMO:0000642'
CC = 'cellular component'
ECO_FORMAT_NAME_LIST = ['ECO:0000314', 'ECO:0007005', 'ECO:0000353']
PMID_TO_MMO = {
    14562095: 'MMO:0000662',
    26928762: 'MMO:0000662',
    16823961: 'MMO:0000534',
    24769239: 'MMO:0000534',
    22842922: 'MMO:0000662',
    14576278: 'MMO:0000534',
    11914276: 'MMO:0000662',
    22932476: 'MMO:0000662',
    24390141: 'MMO:0000662',
    16622836: 'MMO:0000664',
    26777405: 'MMO:0000662',
    12150911: 'MMO:0000662',
    14690591: 'MMO:0000662',
    10684247: 'MMO:0000534',
    16702403: 'MMO:0000662',
    16407407: 'MMO:0000534',
    19053807: 'MMO:0000662',
    23212245: 'MMO:0000534',
    12068309: 'MMO:0000662',
    9448009: 'MMO:0000662',
    11983894: 'MMO:0000534',
    19040720: 'MMO:0000534',
    15282802: 'MMO:0000662',
    24868093: 'MMO:0000662',
    10449419: 'MMO:0000534',
    12392552: 'MMO:0000534',
    8915539: 'MMO:0000647',
    10377396: 'MMO:0000534'
}


def get_expression_data():

    desired_eco_ids = get_eco_ids(ECO_FORMAT_NAME_LIST)
    genes = Locusdbentity.get_s288c_genes()
    result = []
    print(("computing " + str(len(genes)) + " expression data points"))
    dbentity_id_to_mmo = {}
    for gene in genes:
        go_annotations = DBSession.query(Goannotation, Go).outerjoin(Go).filter(and_(\
            Goannotation.dbentity_id==gene.dbentity_id,\
            Goannotation.annotation_type != 'computational',\
            Goannotation.eco_id.in_(desired_eco_ids),\
            Go.go_namespace == CC,\
            Go.display_name!= CC\
        )).all()
        for x in go_annotations:
            annotation = x[0]
            ref_id = annotation.reference_id
            go = x[1]
            ref = DBSession.query(
                Referencedbentity.pmid, Referencedbentity.sgdid).filter(
                    Referencedbentity.dbentity_id == ref_id).one_or_none()
            pmid = ref[0]
            sgdid = ref[1]
            mmo = None
            if ref_id in list(dbentity_id_to_mmo.keys()):
                mmo = dbentity_id_to_mmo[ref_id]
            else:
                if pmid not in list(PMID_TO_MMO.keys()):
                    mmo = DEFAULT_MMO
                else:
                    mmo = PMID_TO_MMO[pmid]
                dbentity_id_to_mmo[ref_id] = mmo
            obj = {
                "geneId":
                "SGD:" + str(gene.sgdid),
                "evidence": {
                    "crossReference": {
                        "id": "SGD:" + sgdid,
                        "pages": ["reference"]
                    },
                    "publicationId": "PMID:" + str(pmid)
                },
                "whenExpressed": {
                    "stageName": "N/A"
                },
                "whereExpressed": {
                    "whereExpressedStatement": go.display_name,
                    "cellularComponentTermId": go.format_name
                },
                "assay":
                mmo,
                "dateAssigned":
                annotation.date_created.strftime("%Y-%m-%dT%H:%m:%S-00:00")
            }
            result.append(obj)
    if (len(result) > 0):
        output_obj = get_output(result)
        file_name = 'SGD' + SUBMISSION_VERSION + 'expression.json'
        json_file_str = os.path.join(local_dir, file_name)
        with open(json_file_str, 'w+') as res_file:
            res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))

    DBSession.close()

if __name__ == '__main__':
    get_expression_data()
