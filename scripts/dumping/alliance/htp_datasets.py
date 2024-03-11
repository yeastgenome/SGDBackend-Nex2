import os
import json
from sqlalchemy import create_engine
from src.models import DBSession, Dataset
from src.data_helpers  import get_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
DBSession.configure(bind=engine)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION')

local_dir = 'scripts/dumping/alliance/data/'

DEFAULT_MMO = 'MMO:0000642'
CC = 'cellular component'
DEFAULT_TAXID = '559292'
DEFAULT_TAG = 'unclassified'

BIOSAMPLE_OBI_MAPPINGS = {
    'total RNA extract': 'OBI:0000895',
    'polyA RNA extract': 'OBI:0000869',
    'RNA extract': 'OBI:0000880',
    'nuclear RNA extract': 'OBI:0000862',
    'extract': 'OBI:0000423',
    'cytoplasmic RNA extract': 'OBI:0000876',
    'polyA depleted RNA extract': 'OBI:0002573',
    'ribosomal RNA-depleted RNA extract': 'OBI:0002627'
}
MICROARRAY_OBI = ['OBI:0001463', 'OBI:0001235', 'OBI:0001985']

OBI_MMO_MAPPING = {
    'OBI:0001271': 'MMO:0000659',
    'OBI:0001463': 'MMO:0000648',
    'OBI:0001235': 'MMO:0000650',
    'OBI:0001985': 'MMO:0000649',
    'OBI:0001318': 'MMO:0000666'
}
CATEGORY_TAG_MAPPING = {
    "cell cycle": "cell cycle regulation",
    "response to chemical stimulus": "chemical stimulus",
    "lipid metabolism": "lipid metabolic process",
    "organelles, biogenesis, structure, and function": "subcellular component",
    "response to hypoxia": "oxygen level alteration",
    "osmotic stress": "response to osmotic stress",
    "radiation": "response to radiation",
    "starvation": "response to starvation",
    "heat shock": "response to temperature stimulus"
}

result = []

def make_json_obj(dataset):
    ds = dataset

    datasetObject = {
        "datasetId": {
            "primaryId":
            ds.dbxref_type + ":" + ds.dbxref_id,
            "preferredCrossReference": {
                "id": "SGD:" + ds.format_name,
                "pages": ["htp/dataset"]
            },
            "crossReferences": [{
                "id": ds.dbxref_type + ":" + ds.dbxref_id,
                "pages": ["htp/dataset"]
            }]
        },
        "title": ds.display_name,
        "summary": ds.description,
        "dateAssigned": ds.date_public.strftime("%Y-%m-%dT%H:%m:%S-00:00")
    }
    assays = []

    for each in ds.samples:

        if each.assay.obiid not in assays:

            assays.append(each.assay.obiid)

        obiSet = set(OBI_MMO_MAPPING.keys())
        assaysSet = set(assays)
        if (assaysSet.isdisjoint(obiSet)):
            continue

        if (obiSet & assaysSet) and (ds.channel_count == 1
                                     or ds.channel_count == 2):
            datasetObject["numChannels"] = ds.channel_count

    dsRefList = []

    if ds.references:
        for ref in ds.references:
            dsRefList.append(
                {"publicationId": "PMID:" + str(ref.reference.pmid)})
        datasetObject["publications"] = dsRefList

    keywordList = []

    if ds.keywords:

        for kw in ds.keywords:
            if kw.keyword.display_name in list(CATEGORY_TAG_MAPPING.keys(
            )):  ##some tags need to be mapped
                keywordList.append(
                    CATEGORY_TAG_MAPPING[kw.keyword.display_name])
            else:
                keywordList.append(kw.keyword.display_name)
        datasetObject["categoryTags"] = keywordList

    else:
        datasetObject["categoryTags"] = [DEFAULT_TAG]

    return datasetObject



def get_htp_datasets():

    dsObjs = DBSession.query(Dataset).all()
    print("processing " + str(len(dsObjs)) + " datasets")
    superSeriesDict = dict()

    dsWithParents = DBSession.query(Dataset).filter(
        Dataset.parent_dataset != None).all()
    ssIdList = list()
    for subDs in dsWithParents:
        ssIdList.append(subDs.parent_dataset.dataset_id)

    for ds in dsObjs:

        if ds.dataset_id in ssIdList:
            continue

        if ds.dbxref_id:
            count = 1
   
            for obj in result:
                if (obj["datasetId"]["primaryId"] == ds.dbxref_type+":"+ds.dbxref_id):

                    obj["datasetId"]["crossReferences"].append({
                        "id": "SGD:" + ds.format_name,
                        "pages": ["htp/dataset"]
                        })
                    count = count + 1

                    break
            if count == 1:
                dsjsonObj = make_json_obj(ds)

                result.append(dsjsonObj)

                if ds.parent_dataset:  # make list of primary Ids for children series; add to hash with parent Dataset ID as key
                    if str(ds.parent_dataset.dataset_id) in superSeriesDict.keys():
                        superSeriesDict[str(
                            ds.parent_dataset.dataset_id)].append(ds.dbxref_type +
                                                                  ":" +
                                                                  ds.dbxref_id)
                    else:
                        superSeriesDict[str(ds.parent_dataset.dataset_id)] = [
                            ds.dbxref_type + ":" + ds.dbxref_id
                        ]

        else:
            continue

    if len(superSeriesDict.keys()) > 0:
        for superSeries in superSeriesDict.keys():
            ssObj = DBSession.query(Dataset).filter(
                Dataset.dataset_id == superSeries).one_or_none()

            if ssObj.dbxref_id:
                ssJsonObj = make_json_obj(ssObj)
                ssJsonObj["subSeries"] = superSeriesDict[superSeries]
                result.append(ssJsonObj)

    if (len(result) > 0):
        print('final:' + str(len(result)) + ' datasets')
        output_obj = get_output(result)
        file_name = 'SGD' + SUBMISSION_VERSION + 'htp_dataset.json'
        json_file_str = os.path.join(local_dir, file_name)
        with open(json_file_str, 'w+') as res_file:
            res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))

    DBSession.close()
if __name__ == '__main__':
    get_htp_datasets()
