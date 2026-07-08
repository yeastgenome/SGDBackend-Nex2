# script to create loading files for the Alliance persistent store
# 1. alleles_persistent file (AlleleDTO in allianceModel.schema.json)
# 2. allele_association file (AlleleGeneAssociationDTO in allianceModel.schema.json)
#

import os
import stat
import json
import re
import sys
import requests
import gzip
import shutil

from sqlalchemy import create_engine, and_
from src.models import DBSession, AllelealiasReference, Referencedbentity, AlleleAlias, LocusAllele, Alleledbentity, LocusalleleReference
from src.data_helpers import get_pers_output, get_allele_synonyms

# 2/4/24 Add creation of allele_association file for persistent store:

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION')
LINKML_VERSION = os.getenv('LINKML_VERSION')

# change to BETA for testing #
# CURATION_API_TOKEN = os.getenv('CURATION_API_TOKEN')
CURATION_API_TOKEN = os.getenv('BETA_CURATION_API_TOKEN')

DBSession.configure(bind=engine)
SUBMISSION_TYPE = 'allele_ingest_set'  # for allele entities file
# allelegeneassociation file
AG_SUBMISSION_TYPE = 'allele_gene_association_ingest_set'

local_dir = 'scripts/dumping/alliance/data/'
DEFAULT_TAXID = '559292'
# please add your curation interface API token to prod_variables.sh
headers = {
    'Authorization': 'APIToken ' + CURATION_API_TOKEN + ''
}


# takes Allele DBID and returns an allele-gene DTO
def get_allele_gene_information(alleleDbid):
 #   print("getting gene-allele associations")
    agObj = {}

    # *allele_identifier (string) *req
    # created_by_curie (string)
    # date_created (date-time string)
    # date_updated (date-time string)
    # db_date_created
    # db_date_updated
    # evidence_code_curie (string, curie of ECO term)
    # evidence_curies (array of strings, refs?)
    # *gene_identifier (string, primary_external_id) *req
    # *internal (bool, private or public - set to public all the time)
    # note_dto (NoteDTO)
    # obsolete (bool)
    # *relation_name (name of vocabularyterm representing relation of an association)
    # updated_by_curie (string)

    alleleObject = DBSession.query(Alleledbentity).filter(
        Alleledbentity.dbentity_id == alleleDbid).one_or_none()
   # simpleObj = alleleObject.to_simple_dict()
    # simple_allele_obj = alleleObj.to_simple_dict()
   # affectedGeneObjs = alleleObject.get_affected_geneObjs()

    agObj['internal'] = False
    agObj['relation_name'] = 'is_allele_of'
    agObj['allele_identifier'] = 'SGD:' + alleleObject.sgdid

    # get reference info #

    for x in DBSession.query(LocusAllele).filter_by(allele_id=alleleDbid).all():

        print('affected gene:' + x.locus.systematic_name + "/" + x.locus.sgdid)
        agObj['gene_identifier'] = 'SGD:' + x.locus.sgdid

        references = []
        locusalleleRefs = DBSession.query(LocusalleleReference).filter_by(
            locus_allele_id=x.locus_allele_id).all()
       # print("num refs:" + str(len(locusalleleRefs)))
        if len(locusalleleRefs) > 0:
            for y in locusalleleRefs:
                pubmedId = "PMID:" + str(y.reference.pmid)
                references.append(pubmedId)
            agObj["evidence_curies"] = references
        else:
            continue

        # agObj["date_created"] = x.date_created.strftime(
        #    "%Y-%m-%dT%H:%m:%S-00:00"),
        agObj["created_by_curie"] = "SGD:" + x.created_by
        agObj["updated_by_curie"] = "SGD:" + x.created_by

    return (agObj)


def make_file(records, sub_type, filename):
    output_obj = get_pers_output(sub_type, records, LINKML_VERSION)

    json_file_str = os.path.join(local_dir, filename)
    #  os.open(json_file_str, os.O_RDONLY)
    #   os.chmod(json_file_str, 0o666)
    #  os.close(json_file_str)

    with open(json_file_str, 'w+') as res_file:
        res_file.write(json.dumps(output_obj, indent=4, sort_keys=False))

    # compress file#
    compressed_file_str = json_file_str + '.gz'
    # os.chmod(compressed_file_str, 0o666)
    # exit(1)

    try:
        with open(json_file_str, 'rb') as f_in:
            with gzip.open(compressed_file_str, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        print('file successfully compressed: ' + compressed_file_str)
        return (compressed_file_str)
    except Exception as error:
        print('could not compress file: ' + json_file_str)
        print('exception occurred:', type(error).__name__, '-', error)
        exit()


def get_allele_information():

    print("getting Alleles")
    # f"left join nex.locus_allele la on la.allele_id = ad.dbentity_id "

    alleleObjList = DBSession.execute(
        "select ad.dbentity_id, db.sgdid,  ad.description, db.display_name, "
        "s.display_name, s.format_name, db.date_created "
        "from nex.alleledbentity ad "
        "inner join nex.dbentity db on ad.dbentity_id = db.dbentity_id "
        "inner join nex.so s on ad.so_id = s.so_id ").fetchall()
    # "where ad.dbentity_id in (2227050,2227066,2227068, 2227070)"

    print(("computing " + str(len(alleleObjList)) + " alleles"))

    result = []  # allele DTOs
    allele_gene_results = []

    if (len(alleleObjList) > 0):

        try:
            for alleleObj in alleleObjList:

                if re.search("\<sub\>", alleleObj[3]):
                    print("skipping: " + alleleObj[3])
                    continue
                obj = {}  # alleleDTO object

                obj["allele_database_status_dto"] = {  # :
                    "created_by_curie": "SGD",
                    "database_status_name": "approved",
                    "internal": False,
                    "obsolete": False,
                    "updated_by_curie": "SGD"
                }
                # 1/21/25 change 'mod_entity_id' to 'primary_external_id' for 8.1.0 release
                obj["internal"] = False
                obj["is_extinct"] = False
                obj["obsolete"] = False
                obj["updated_by_curie"] = "SGD"  # add curator name:
                obj["created_by_curie"] = "SGD"  # :
                obj["primary_external_id"] = "SGD:" + str(alleleObj[1])
                obj["data_provider_dto"] = {
                    "source_organization_abbreviation": "SGD",
                    "cross_reference_dto": {
                        "referenced_curie": "SGD:" + str(alleleObj[1]),
                        "display_name": "SGD:" + str(alleleObj[1]),
                        "prefix": "SGD",
                        "page_area": "allele",
                        "internal": False
                    },
                    "internal": False,
                    "obsolete": False,
                    "created_by_curie": "SGD",
                    "updated_by_curie": "SGD",
                }

                obj["allele_symbol_dto"] = {
                    "name_type_name": "nomenclature_symbol",
                    "synonym_scope_name": "exact",
                    "format_text": alleleObj[3],
                    "display_text": alleleObj[3],
                    "internal": False,
                    "obsolete": False,
                    "created_by_curie": "SGD",
                    "updated_by_curie": "SGD"
                }

                obj["allele_mutation_type_dtos"] = [{
                    "mutation_type_curies": [str(alleleObj[5])],
                    "internal": False,
                    "obsolete": False,
                    "created_by_curie": "SGD",
                    "updated_by_curie": "SGD"
                }]

# include SGD Secondary IDs in allele_Alias table

                allele_alias_list = DBSession.query(AlleleAlias).filter(#and_(
                    AlleleAlias.allele_id == alleleObj[0]).all() #, AlleleAlias.alias_type != 'SGD Secondary')).all()
                if (len(allele_alias_list) > 0):
                    obj["allele_synonym_dtos"] = get_allele_synonyms(
                        allele_alias_list)

                obj["taxon_curie"] = "NCBITaxon:" + DEFAULT_TAXID
                obj["date_created"] = alleleObj[6].strftime(
                    "%Y-%m-%dT%H:%m:%S-00:00")
                obj["date_updated"] = alleleObj[6].strftime(
                    "%Y-%m-%dT%H:%m:%S-00:00")

                if str(alleleObj[2]) != "None":  # if a DESCRIPTION exists, make note_dto
                    if (str(alleleObj[2].strip()) and str(alleleObj[2].strip()) != "" and len(str(alleleObj[2])) != 0):
                        # print(str(alleleObj[2]))
                        obj["note_dtos"] = [{
                            "free_text": str(alleleObj[2]),
                            "note_type_name": "mutation_description",
                            "internal": False,
                            "obsolete": False,
                            "created_by_curie": "SGD",
                            "updated_by_curie": "SGD",
                            "date_created": alleleObj[6].strftime("%Y-%m-%dT%H:%m:%S-00:00"),
                            "date_updated": alleleObj[6].strftime("%Y-%m-%dT%H:%m:%S-00:00")
                        }]
                alleleRefList = DBSession.execute(  # gets all annotation references associated with an allele
                    "select rdb.pmid "
                    "from nex.alleledbentity ad "
                    "left join nex.literatureannotation ar on ad.dbentity_id = ar.dbentity_id "
                    "left join nex.referencedbentity rdb on ar.reference_id = rdb.dbentity_id "
                    "where ad.dbentity_id =" + str(alleleObj[0])).fetchall()

                if alleleRefList:
                    for x in alleleRefList:
                        obj['reference_curies'] = []
                        if x not in obj['reference_curies'] and x is not None:
                            if str(x[0]) != 'None':
                                obj['reference_curies'].append(
                                    "PMID:" + str(x[0]))

       ###### get allele_gene_dto_obj ###
                alleleGeneAssnObj = get_allele_gene_information(
                    alleleObj[0])

               # append result arrays with objs #

                result.append(obj)  # add alleleDTO to result ##
                # add allele_gene_associationdto to diff list
                allele_gene_results.append(alleleGeneAssnObj)

        except Exception as e:
            print(e)
    files = {}

# make files

    if (len(result) > 0):
        file_name = 'SGD' + SUBMISSION_VERSION + 'allelesPersistent.json'
        compressed_allele_file = make_file(result, SUBMISSION_TYPE, file_name)
        files['ALLELE_SGD'] = open(compressed_allele_file, 'rb')

    if (len(allele_gene_results) > 0):
        file_name = 'SGD' + SUBMISSION_VERSION + 'alleleGeneAssnPersistent.json'
        compressed_ag_assn_file = make_file(
            allele_gene_results, AG_SUBMISSION_TYPE, file_name)
        files['ALLELE_ASSOCIATION_SGD'] = open(compressed_ag_assn_file, 'rb')

## upload files to persistent store ##
# open(FILE, 'r')
#        files = {
#            'ALLELE_SGD': open(compressed_allele_file, 'rb'),
#            'ALLELE_ASSOCIATION_SGD' : open(compressed_ag_assn_file,'rb')
#        }

 #       try:
        #          print('*Headers:', headers)
        #          print('*Files:', files)

        # FOR TESTING to BETA-CURATION SITE #
#            response = requests.post(
#                'https://beta-curation.alliancegenome.org/api/data/submit', files=files, headers=headers)

# uncomment for PRODUCTION #
#            response = requests.post(
#                'https://curation.alliancegenome.org/api/data/submit', files=files, headers=headers)

 #           print('Response:' + str(response.status_code))

#            if response.status_code == 200:
        # this doesn't work. It comes back as successful, but have to check dashboard
#                print('File uploaded successfully')
        # to make sure
#            else:
        # got 504, but the file was successfully upload to Alliance, continuing to load objs

#               print('Failed to upload file. Status code:', response.status_code)
#                print('Response:', response.text)
#                print('Headers:', headers)
 #               print('Files:', files)

  #      except Exception as e:
  #          print('An error occurred in file upload:', e)

    DBSession.close()


if __name__ == '__main__':
    get_allele_information()
