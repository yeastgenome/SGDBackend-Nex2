import os
import re
import json
from datetime import datetime
from sqlalchemy import create_engine
from src.models import DBSession, Base, Colleague, ColleagueLocus, Dbentity, Eco, Locusdbentity, \
    LocusUrl, LocusAlias, Dnasequenceannotation, So, Locussummary, Phenotypeannotation, PhenotypeannotationCond, \
    Phenotype, Goannotation, Go, Goslimannotation, Goslim, Apo, Straindbentity, Strainsummary, Reservedname, GoAlias, \
    Goannotation, Referencedbentity, Referencedocument, Referenceauthor, ReferenceAlias, Chebi

SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_1.0.0.0_')
engine = create_engine(os.getenv('CURATE_NEX2_URI'), pool_recycle=3600)
DBSession.configure(bind=engine)


def get_sgdids_for_panther(root_path):
    """ Populate sgd ids to a text file to search in panther.
     
     Returns
     --------
     file
        txt file containing sgd ids
     
     """

    locus_data = Locusdbentity.get_s288c_genes()
    sgdids = []
    for locus_item in locus_data:
        sgdids.append(locus_item.sgdid)

    txt_file = os.path.join(root_path,
                            'src/data_assets/panther_search_input.txt')
    result = json.dumps(sgdids, ensure_ascii=False)
    with open(txt_file, 'W+') as result_file:
        result_file.write(
            result.replace('"', '').replace('[', '').replace(']', ''))


def pair_pantherid_to_sgdids(root_path=None):
    """Pair panther ids to sgd ids.    

    Paramaters
    ----------
    root_path : str
        The file location of panther ids text file. Tab deliminated text file.
        To get this file from panther you have to give panther list of sgd ids.
        Please check get_sgdids_for_panther() method for further details on how
        to extract sgd ids to pass to panther website
    
    Returns
    -------
    dictionary
        key-value pair panther data to sgd data
    
    """

    data_dict = {}
    panther_json_file = os.path.join(
        root_path, 'src/data_assets/panther_search_results.json')
    with open(panther_json_file) as data_file:
        json_data = json.load(data_file)
        try:
            for item in json_data:
                if (len(item) > 1):
                    temp_str = ','.join(map(str, item))
                    reg_pattern = r'(SGD=S\d+)|(PTHR\d+)'  # pattern has changed
                    reg_result = sorted(
                        list(set(re.findall(reg_pattern, temp_str))))
                    if (len(reg_result) > 1):
                        item_str1 = ''.join(reg_result[0])
                        item_str2 = ''.join(reg_result[1]).split("=")
                        data_dict[item_str2[1]] = item_str1
                    elif (len(reg_result) == 1):
                        item_str1 = ''.join(reg_result[0]).split("=")
                        data_dict[item[1]] = None
                    else:
                        continue
        except Exception as ex:
            print(ex)
        return data_dict


def combine_panther_locus_data(panther_list, locus_list):
    """ Create dictionary with panther ids and locus objects.

    Parameters
    ----------
    panther_list
        list of panther objects
    locus_list
        list of locus object
    
    Returns
    -------
    dictionary

    """

    combined_data = {}
    if (len(panther_list) > 0 and len(locus_list) > 0):
        for item in locus_list:
            obj = {"panther_id": "", "locus_obj": ""}
            if (panther_list.get(item.sgdid) is not None):
                obj["panther_id"] = panther_list.get(item.sgdid)
                obj["locus_obj"] = item
                combined_data[item.dbentity_id] = obj
            else:
                obj["panther_id"] = None
                obj["locus_obj"] = item
                combined_data[item.dbentity_id] = obj

    return combined_data


def get_eco_ids(eco_format_name_list):
    """ Get eco ids based on given format names.

    Parameters
    ----------
    eco_format_name_list
        list of string eco format_name
    
    Returns
    -------
    list
        list of eco ids based on eco ids

    """
    if (eco_format_name_list):
        desired_eco_ids = DBSession.query(Eco.eco_id).filter(
            Eco.format_name.in_(eco_format_name_list)).all()
        return desired_eco_ids
    else:
        return None


def get_locus_alias_data(locus_alias_list, dbentity_id, item_obj):
    """ create locus alias data object

    Parameters
    ----------
    locus_alias_list
    dbentity_id
    item_obj

    Returns
    -------
    dictionary

    """
    data_dict = {}
    aliases = []
    aliases_types = ["Uniform", "Non-uniform"]
    aliases_types_other = ["SGDID Secondary", "UniProtKB ID", "Gene ID"]
    obj = {"secondaryIds": [], "crossReferences": []}
    flag = False
    for item in locus_alias_list:
        if (item_obj):
            obj["crossReferences"].append
        if (item.alias_type in aliases_types):
            aliases.append(item.display_name)
        if (item.alias_type == "SGDID Secondary"):
            obj["secondaryIds"].append(item.source.display_name + ":" +
                                       item.display_name)
            flag = True
        if (item.alias_type == "UniProtKB ID"):
            obj["crossReferences"].append("UniProtKB:" + item.display_name)
            flag = True
        if (item.alias_type == "Gene ID"
                and item.source.display_name == 'NCBI'):
            obj["crossReferences"].append("NCBI_Gene:" + item.display_name)
            flag = True

    if (flag):
        data_dict[dbentity_id] = obj
    data_dict["aliases"] = aliases
    return data_dict


def get_output(result_data):
    """Get generated data and format it to fit Alliance schema.

    Parameters
    ----------
    result_data: list

    Returns
    -------
    dictionary
    """

    if (result_data):
        output_obj = {
            "data": result_data,
            "metaData": {
                "dataProvider": {
                    "crossReference": {
                        "id": "SGD",
                        "pages": ["homepage"]
                    },
                    "type": "curated"
                },
                "dateProduced":
                datetime.utcnow().strftime("%Y-%m-%dT%H:%m:%S-00:00"),
                "release":
                "SGD " + SUBMISSION_VERSION.replace("_", "").strip() + " " +
                datetime.utcnow().strftime("%Y-%m-%d")
            }
        }
        return output_obj
    else:
        return None

def get_pers_output(submission_type, result_data):
    """Get generated data and format it to fit Alliance persistent schema.

    Parameters
    ----------
    result_data: list

    Returns
    -------
    dictionary
    """

    if (result_data):
        output_obj = {
            submission_type : result_data
        }
        return output_obj
    else:
        return None
