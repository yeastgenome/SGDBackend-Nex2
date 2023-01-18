""" Aggregate basic gene information  for Alliance data submission

The script extracts data from ~8 tables into a dictionary that is written to a json file.
The json file is submitted to Alliance for futher processing

This file requires packages listed in requirements.txt file and env.sh file.
The env.sh file contains environment variables

# get panther IDs from database, 07/19/19
# added phenotype Xref link 08/22/2020

This file can be imported as a modules and contains the following functions:
    get_expression_data
"""

import os
import json
import re
import time
from random import randint
from datetime import datetime
from sqlalchemy import create_engine, and_, inspect
import concurrent.futures
from ..models.models import LocusAlias, Dnasequenceannotation, DBSession, Eco, Locusdbentity, Goannotation, Go, Referencedbentity
from ..data_helpers.data_helpers import combine_panther_locus_data, pair_pantherid_to_sgdids, get_output, get_locus_alias_data

engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_1.0.0.0_')
DBSession.configure(bind=engine)
"""
combine_panther_locus_list
get_panther_sgdids
Locusdbentity.get_s288c_genes
output_obj

SO types returned from get_s288c_genes:
SO:0001268	snRNA gene
SO:0001272	tRNA gene
SO:0000718	blocked reading frame
SO:0000111	transposable element gene
SO:0002026	intein encoding region
SO:0000296	origin of replication
SO:0001643	telomerase RNA gene
SO:0001637	rRNA gene
SO:0000036	matrix attachment site #not gene
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
SO:0002059  recombination enhancer (not gene)
SO:0000286	long terminal repeat (keep for non-gene)
SO:0000186	LTR retrotransposon (keep for non-gene)

"""
SO_TYPES_TO_EXCLUDE = [
    'SO:0000186', 'SO:0000577', 'SO:0000286', 'SO:0000296', 'SO:0005855',
    'SO:0001984', 'SO:0002026', 'SO:0001789', 'SO:0000436', 'SO:0000624',
    'SO:0000036', 'SO:0002059'
]


def get_basic_gene_information(root_path):
    """ Extract basic gene information.

    Parameters
    ----------
    root_path
        root directory name path    

    Returns
    --------
    file
        writes data to json file

    """
    combined_list = Locusdbentity.get_s288c_genes()

    # combined_list = DBSession.query(LocusAlias).filter(
    #    LocusAlias.locus_id == item.dbentity_id,
    #   LocusAlias.alias_type == 'PANTHER ID').one()
    #combined_list = combine_panther_locus_data(
    #pair_pantherid_to_sgdids(root_path), Locusdbentity.get_s288c_genes())
    print(("computing " + str(len(combined_list)) + " s288c genes"))
    result = []
    if (len(combined_list) > 0):

        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            for item in combined_list:
                obj = {
                    "basicGeneticEntity": {
                        "crossReferences": [],
                        "primaryId":
                        "",
                        "genomeLocations": [{
                            "startPosition": 0,
                            "chromosome": "",
                            "assembly": "R64-3-1",
                            "endPosition": 0,
                            "strand": ""
                        }],
                        "taxonId":
                        "NCBITaxon:559292",
                        "synonyms": []
                    },
                    "soTermId": "",
                    "geneSynopsis": "",
                    "symbol": ""
                }
                # item = combined_list[item_key]  #["locus_obj"]
                temp_itm = ["gene"]
                temp_itm.append("gene/references")
                temp_itm.append("homepage")
                if (item.has_expression):
                    temp_itm.append("gene/expression")
                    temp_itm.append("gene/spell")
                if (item.has_interaction):
                    temp_itm.append("gene/interactions")
                if (item.has_disease):
                    temp_itm.append("gene/disease")
                if (item.has_phenotype):
                    temp_itm.append("gene/phenotypes")

                obj["basicGeneticEntity"]["crossReferences"].append({
                    "id":
                    "SGD:" + item.sgdid,
                    "pages":
                    temp_itm
                })

                #item_panther = combined_list[item_key]["panther_id"] #get panther information
                item_panther = DBSession.query(LocusAlias).filter(
                    LocusAlias.locus_id == item.dbentity_id,
                    LocusAlias.alias_type == 'PANTHER ID').first()

                #    if item_panther is not None:
                #        print('SGD:' + item.sgdid + "->" + 'PANTHER:' +
                #              item_panther.display_name)

                # get locus alias info
                locus_alias_data = DBSession.query(LocusAlias).filter(
                    LocusAlias.locus_id == item.dbentity_id).all()

                #do the following if there is locus alias info #
                #  if (len(locus_alias_data) > 0):
                dna_seq_annotation_obj = DBSession.query(
                    Dnasequenceannotation).filter(
                        Dnasequenceannotation.dbentity_id == item.dbentity_id,
                        Dnasequenceannotation.taxonomy_id == 274901,
                        Dnasequenceannotation.dna_type == "GENOMIC").all()
                # IF it is a SO ID to exclude, then skip ('continue')
                if dna_seq_annotation_obj[0].so.soid in SO_TYPES_TO_EXCLUDE:
                    continue

                if (len(dna_seq_annotation_obj) > 0):
                    strnd = ""
                    if dna_seq_annotation_obj[0].strand == "0":
                        strnd = "."
                    else:
                        strnd = dna_seq_annotation_obj[0].strand

                    chromosome = dna_seq_annotation_obj[
                        0].contig.display_name.split(" ")
                    obj["basicGeneticEntity"]["genomeLocations"][0][
                        "startPosition"] = dna_seq_annotation_obj[
                            0].start_index
                    obj["basicGeneticEntity"]["genomeLocations"][0][
                        "endPosition"] = dna_seq_annotation_obj[0].end_index
                    obj["basicGeneticEntity"]["genomeLocations"][0][
                        "strand"] = strnd
                    obj["basicGeneticEntity"]["genomeLocations"][0][
                        "startPosition"] = dna_seq_annotation_obj[
                            0].start_index
                    obj["basicGeneticEntity"]["genomeLocations"][0][
                        "chromosome"] = "chr" + chromosome[1]
                    #      obj["basicGeneticEntity"]["genomeLocations"][0][["assembly"] = dna_seq_annotation_obj[0].genome_release

                    if dna_seq_annotation_obj[
                            0].so.so_id == 263757:  #change ORF to gene SO ID
                        obj["soTermId"] = "SO:0001217"
                    else:
                        obj["soTermId"] = dna_seq_annotation_obj[0].so.soid

## Add locus alias data if there is any ##
                if (len(locus_alias_data) > 0):
                    mod_locus_alias_data = get_locus_alias_data(
                        locus_alias_data, item.dbentity_id, item)

                    for mod_item in mod_locus_alias_data:
                        mod_value = mod_locus_alias_data.get(mod_item)
                        if (type(mod_value) is list):
                            if (mod_locus_alias_data.get("aliases")
                                    is not None):
                                obj["basicGeneticEntity"][
                                    "synonyms"] = mod_locus_alias_data.get(
                                        "aliases")

                        else:
                            if (mod_value.get("secondaryIds") is not None):
                                temp_sec_item = mod_value.get("secondaryIds")
                                if (len(temp_sec_item) > 0):
                                    if (item.name_description is not None):
                                        obj["name"] = item.name_description
                                    if (len(temp_sec_item) > 1):
                                        obj["basicGeneticEntity"][
                                            "secondaryIds"] = [
                                                str(x) for x in temp_sec_item
                                            ]
                                    else:
                                        if (len(temp_sec_item) == 1):
                                            obj["basicGeneticEntity"][
                                                "secondaryIds"] = [
                                                    str(temp_sec_item[0])
                                                ]
                            if (mod_value.get("crossReferences") is not None):
                                temp_cross_item = mod_value.get(
                                    "crossReferences")
                                if (len(temp_cross_item) > 1):
                                    for x_ref in temp_cross_item:
                                        obj["basicGeneticEntity"][
                                            "crossReferences"].append(
                                                {"id": str(x_ref)})
                                else:
                                    if (len(temp_cross_item) == 1):
                                        obj["basicGeneticEntity"][
                                            "crossReferences"].append({
                                                "id":
                                                str(temp_cross_item[0])
                                            })
                                        #obj["crossReferences"] = [str(temp_cross_item[0])]

    # add synonyms,geneSynopsis, symbol, primaryId
                obj["geneSynopsis"] = item.description
                obj["symbol"] = item.gene_name if item.gene_name is not None else item.systematic_name
                obj["basicGeneticEntity"]["synonyms"].append(
                    item.systematic_name)
                obj["basicGeneticEntity"]["primaryId"] = "SGD:" + item.sgdid

                ## ADD PANTHER DATA if there is any
                if (item_panther is not None):  #DO THIS IF NO PANTHER DATA
                    obj["basicGeneticEntity"]["crossReferences"].append(
                        {"id": "PANTHER:" + item_panther.display_name})
                    #obj["crossReferences"].append("PANTHER:" + item_panther)
                #   item = combined_list[item_key]["locus_obj"]
                # obj["geneSynopsis"] = item.description


# Add name_description if it exists
                if (item.name_description is not None):
                    obj["name"] = item.name_description
                #   obj["basicGeneticEntity"]["synonyms"].append(
                #       item.systematic_name)

                # result.append(obj)

            # else:  # DO THIS IF THERE IS PANTHER DATA
            #  obj["basicGeneticEntity"][
            #      "primaryId"] = "SGD:" + item.sgdid
            #   item = combined_list[item_key]["locus_obj"]
            #    obj["symbol"] = item.gene_name if item.gene_name is not None else item.systematic_name

            #    if (item.name_description is not None):
            #     obj["name"] = item.name_description

                result.append(obj)

            if (len(result) > 0):
                print("# of bgi objects:" + str(len(result)))

                output_obj = get_output(result)

                file_name = 'src/data/SGD' + SUBMISSION_VERSION + 'basicGeneInformation.json'
                json_file_str = os.path.join(root_path, file_name)
                with open(json_file_str, 'w+') as res_file:
                    res_file.write(json.dumps(output_obj))
if __name__ == '__main__':
    get_basic_gene_information(THIS_FOLDER