""" Aggregate expression data for Alliance data submission
The script extracts data from 5 tables into a dictionary that is written to a json file.
The json file is submitted to Alliance for futher processing
This file rewuires packages listed in requirements.txt file and env.sh file.
The env.sh file contains environment variables
This file can be imported as a modules and contains the following functions:
    get_htp_metadata

1. Get all HTP samples
2. skip ones that are not RNA-seq or transcription profiling by microarray
3. make sample objects, combine all datasets they are in
3b. keep track of datasets so objects aren't repeated
4. make dataset objects, include superseries
"""

import os
import sys
import json
import re
import concurrent.futures
from datetime import datetime
from sqlalchemy import create_engine, and_
from src.models.models import DBSession, Dataset, DatasetKeyword, DatasetReference, Referencedbentity, Datasetsample, Dbentity
from src.data_helpers.data_helpers import get_eco_ids, get_output, SUBMISSION_VERSION

engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
DBSession.configure(bind=engine)

#SUBMISSION_VERSION = '_1.0.1.1B_'  #os.getenv('SUBMISSION_VERSION', '_1.0.0.0_')
DEFAULT_MMO = 'MMO:0000000'  #MMO:0000642'
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
#ECO_FORMAT_NAME_LIST = ['ECO:0000314', 'ECO:0007005', 'ECO:0000353']
"""OBI TO MMO: OBI:0001271 RNA-seq assay	MMO:0000659
OBI:0001463 high throughput transcription profiling by array	MMO:0000648
OBI:0001235 high throughput transcription profiling by tiling array	MMO:0000650
OBI:0001985 high throughput transcription profiling by microarray	MMO:0000649
high throughput proteomic profiling	MMO:0000664
OBI:0001318 high throughput proteomic profiling by array	MMO:0000666
"""
"""two files need to be output. SGD_htp_datasets.json and SGD_htp_datasetSamples.json #
dataset.json object:
 { "data": [
 { "datasetId": {"primaryId":"GEO ID"}, dataset->dbxref_id
   "publication": [{"publicationId":"PMID"}], dataset->reference_dbentity_id -> pubmed
   "title": "string", dataset->display_name
   "summary":"text", dataset->description
   "numChannels": 1 or 2 (if microarray), dataset->channel_count
   "dateAssigned":"string-time", dataset->
   "datasetIds": [], (if a superset)
   "categoryTags": ["text", "text2","text3"]}], dataset_id -> dataset_keyword -> display_name
 "metaData":{}
 }

datasetSample object:
{ "data": [
 { "sampleId": {"primaryId":"GEO ID"},
   "publication": [{"publicationId":"PMID"}],
   "sampleTitle": "string",
   "sampleType":"text",
   "genomicInformation": "AGM in the future",
   "taxonId",
   "sequencingFormat",
   "assemblyVersion",
   "notes",
   "datasetId": [primaryIds],
   "microarraySampleDetails": {}, (for microarrays only)
   "dateAssigned":"string-time",
 "metaData":{}
 }

"""


def get_htp_sample_metadata(root_path):
    """ Get HTP metadata from database
    Parameters
    ----------
    root_path
        root directory name path
    Returns
    ------
    file
        writes HTP metadata to  TWO json files
    """
    #desired_eco_ids = get_eco_ids(ECO_FORMAT_NAME_LIST)
    #.limit(500)
    datasetSamples = DBSession.query(Datasetsample).filter(
        Datasetsample.biosample.in_(list(BIOSAMPLE_OBI_MAPPINGS.keys())),
        Datasetsample.dbxref_id != None).all()
    dataset_result = []
    datasample_result = []

    strain_name_to_sgdid = dict([
        (x.display_name, x.sgdid)
        for x in DBSession.query(Dbentity).filter_by(subclass='STRAIN').all()
    ])

    print(("computing " + str(len(datasetSamples)) + " datasamples"))

    dbentity_id_to_mmo = {}
    datasetobjs = []
    superseriesTodatasets = {}
    datasamplesDone = []
    #sample_num = 1

    sampleResult = []
    datasetResult = []
# with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:

    for sampleObj in datasetSamples:
        #print str(sample_num) + ". sample ID: " + sampleObj.display_name
        dataset = sampleObj.dataset
        dsAssayObi = sampleObj.assay.obiid

        # check for references #
        dsRef = DBSession.query(DatasetReference).filter_by(
            dataset_id=dataset.dataset_id).all()
        # skip if not right kind of biosample,
        if len(dsRef) == 0 or sampleObj.display_name in datasamplesDone:
            # print "skipping " + dsAssayObi + " wrong dataset OR no ref"
            continue
        else:
            #  print dsAssayObi + ":" + sampleObj.dbxref_id + sampleObj.display_name
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
            ## taxon ID
            # if sampleObj.taxonomy:
            #   obj["taxonId"] = "NCBITaxon:" + sampleObj.taxonomy.taxid.replace(
            #        'TAX:', '')
            #else:
            obj["taxonId"] = "NCBITaxon:" + DEFAULT_TAXID

            ## assay type ##
            #    obj["assayType"] =

            ## get all datasets

            datasetsForSample = DBSession.query(Datasetsample).filter_by(
                dbxref_id=sampleObj.dbxref_id).with_entities(
                    Datasetsample).distinct()

            dsList = []
            dsassayList = []

            for dsSample in datasetsForSample:
                #  print dsSample.display_name + " belongs to: " + dsSample.dataset.dbxref_id + "|" +
                #         dsSample.dataset.display_name + "*"
                if dsSample.dataset.dbxref_id and dsSample.dataset.dbxref_id not in dsList:
                    dsList.append(dsSample.dataset.dbxref_type + ":" +
                                  dsSample.dataset.dbxref_id)
                    if dsSample.assay.obiid not in dsassayList:
                        dsassayList.append(dsSample.assay.obiid)

                #  "datasetId": [primaryIds],
            # break
            ## make dataset list
            obj["datasetIds"] = dsList
            print(dsSample.display_name + " in " + str(
                len(dsList)) + " datasets " + str(len(dsassayList)) + " assays")

            for dsAssay in dsassayList:
                if dsAssay in list(OBI_MMO_MAPPING.keys()):
                    obj["assayType"] = OBI_MMO_MAPPING[dsAssay]
                else:
                    obj["assayType"] = DEFAULT_MMO

            #datasetobjs.append(dsList)
            #else:
            #    print "skipping " + dataset.assay.display_name + " right assay, wrong sample or no DBXREFID"
            #     continue

            sampleResult.append(obj)
        #    sample_num = sample_num + 1


## make datasetSample metadata file

    if (len(sampleResult) > 0):
        output_obj = get_output(sampleResult)
        file_name = 'data/SGD' + SUBMISSION_VERSION + 'htp_samples.json'
        json_file_str = os.path.join(root_path, file_name)
        with open(json_file_str, 'w+') as res_file:
            res_file.write(json.dumps(output_obj))
if __name__ == '__main__':
    get_htp_sample_metadata(THIS_FOLDER)