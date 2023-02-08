import os
import json
from sqlalchemy import create_engine, and_
from src.models import DBSession, DatasetReference, Datasetsample, Dbentity
from src.data_helpers import get_eco_ids, get_output

engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
DBSession.configure(bind=engine)

local_dir = 'scripts/dumping/alliance/data/'

DEFAULT_MMO = 'MMO:0000000'
CC = 'cellular component'
DEFAULT_TAXID = '559292'

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



def get_htp_sample_metadata():

    datasetSamples = DBSession.query(Datasetsample).filter(
        Datasetsample.biosample.in_(list(BIOSAMPLE_OBI_MAPPINGS.keys())),
        Datasetsample.dbxref_id != None).all()

    strain_name_to_sgdid = dict([
        (x.display_name, x.sgdid)
        for x in DBSession.query(Dbentity).filter_by(subclass='STRAIN').all()
    ])

    print(("computing " + str(len(datasetSamples)) + " datasamples"))

    datasamplesDone = []
    sampleResult = []


    for sampleObj in datasetSamples:

        dataset = sampleObj.dataset

        # check for references #
        dsRef = DBSession.query(DatasetReference).filter_by(
            dataset_id=dataset.dataset_id).all()
        # skip if not right kind of biosample,
        if len(dsRef) == 0 or sampleObj.display_name in datasamplesDone:

            continue
        else:
            datasamplesDone.append(sampleObj.display_name)
            obj = {
                "sampleTitle":
                sampleObj.display_name,
                "sampleType":
                BIOSAMPLE_OBI_MAPPINGS[sampleObj.biosample],
                "sampleId": {
                    "primaryId":
                    sampleObj.dbxref_type + ":" + sampleObj.dbxref_id,
                    "crossReferences": [{
                        "id":
                        sampleObj.dbxref_type + ":" + sampleObj.dbxref_id,
                        "pages": ["htp/datasetsample"]
                    }]
                },
                "dateAssigned":
                sampleObj.date_created.strftime("%Y-%m-%dT%H:%m:%S-00:00")
            }
            ## add genomic information (strain) if available
            if sampleObj.strain_name is not None:
                strains = sampleObj.strain_name.split("|")
                #   print "strain:" + ("*").join(strains)
                if str(strains[0]) in strain_name_to_sgdid:
                    obj["genomicInformation"] = {
                        "biosampleId":
                        "SGD:" + strain_name_to_sgdid[str(strains[0])],
                        "idType": "strain",
                        "bioSampleText": str(strains[0])
                        }
                else:
                    print (str(strains[0]) + " not a DB object")

            obj["taxonId"] = "NCBITaxon:" + DEFAULT_TAXID


            datasetsForSample = DBSession.query(Datasetsample).filter_by(
                dbxref_id=sampleObj.dbxref_id).with_entities(
                    Datasetsample).distinct()

            dsList = []
            dsassayList = []

            for dsSample in datasetsForSample:

                if dsSample.dataset.dbxref_id and dsSample.dataset.dbxref_id not in dsList:
                    dsList.append(dsSample.dataset.dbxref_type + ":" +
                                  dsSample.dataset.dbxref_id)
                    if dsSample.assay.obiid not in dsassayList:
                        dsassayList.append(dsSample.assay.obiid)

            obj["datasetIds"] = dsList
            print(dsSample.display_name + " in " + str(
                len(dsList)) + " datasets " + str(len(dsassayList)) + " assays")

            for dsAssay in dsassayList:
                if dsAssay in list(OBI_MMO_MAPPING.keys()):
                    obj["assayType"] = OBI_MMO_MAPPING[dsAssay]
                else:
                    obj["assayType"] = DEFAULT_MMO

            sampleResult.append(obj)


    if (len(sampleResult) > 0):
        output_obj = get_output(sampleResult)
        file_name = 'SGD' + SUBMISSION_VERSION + 'htp_samples.json'
        json_file_str = os.path.join(local_dir, file_name)
        with open(json_file_str, 'w+') as res_file:
            res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))
if __name__ == '__main__':
    get_htp_sample_metadata()
