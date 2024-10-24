import os
import re
import json
from datetime import datetime
from sqlalchemy import create_engine, and_
from src.models import DBSession, Eco, Locusdbentity, LocusAliasReferences, Referencedbentity,\
    AllelealiasReference, LocusReferences

SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_5.4.0_')
engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
DBSession.configure(bind=engine)


def get_sgdids_for_panther(root_path):

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

    if (eco_format_name_list):
        desired_eco_ids = DBSession.query(Eco.eco_id).filter(
            Eco.format_name.in_(eco_format_name_list)).all()
        return desired_eco_ids
    else:
        return None


def get_locus_alias_data(locus_alias_list, dbentity_id, item_obj):

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


def get_locus_synonyms(locus_alias_list):

    aliases_types = ["Uniform", "Non-uniform"]
    obj = []
    for item in locus_alias_list:
        if (item.alias_type in aliases_types):
            syn = ""
            if item.alias_type == "Non-uniform":
                syn = "non_uniform"
            elif item.alias_type == "Uniform":
                syn = "uniform"
            a_pmids = DBSession.query(LocusAliasReferences,
                                      Referencedbentity.pmid).filter(
                LocusAliasReferences.alias_id == item.alias_id).outerjoin(Referencedbentity).all()
            alias_pmids_results = ["PMID:"+str(y[1]) for y in a_pmids if str(y[1]) != 'None']
            entry = {
             "name_type_name": syn, #item.alias_type.lower(),
             "format_text": item.display_name,
             "display_text": item.display_name,
             "internal": False
            }
            if len(alias_pmids_results) > 0:
                entry["evidence_curies"] = alias_pmids_results
            obj.append(entry)
    return obj

def get_locus_symbols(item):

    obj = []
    pmids_results = DBSession.query(LocusReferences,
                                    Referencedbentity.pmid).filter(
        and_(LocusReferences.locus_id == item.dbentity_id,
             LocusReferences.reference_class == 'gene_name')).outerjoin(
        Referencedbentity).all()
    gene_name_pmids = ["PMID:" + str(x[1]) for x in pmids_results if str(x[1]) != 'None']

    if (len(gene_name_pmids) == 0):
        obj.append({
        "created_by_curie": "SGD",
        "updated_by_curie": "SGD",
        "name_type_name": "nomenclature_symbol",
        "format_text": item.gene_name if item.gene_name is not None else item.systematic_name,
        "display_text": item.gene_name if item.gene_name is not None else item.systematic_name,
        "internal": False,
        "obsolete": False,
        "synonym_scope_name": "exact"
    })

    if (len(gene_name_pmids) > 0):
        obj.append({
            "created_by_curie": "SGD",
            "updated_by_curie": "SGD",
            "name_type_name": "nomenclature_symbol",
            "format_text": item.gene_name if item.gene_name is not None else item.systematic_name,
            "display_text": item.gene_name if item.gene_name is not None else item.systematic_name,
            "internal": False,
            "obsolete": False,
            "synonym_scope_name": "exact",
            "evidence_curies": gene_name_pmids
        })
    return obj


def get_allele_synonyms(allele_alias_list):
    obj = []
    for item in allele_alias_list:
        a_pmids = DBSession.query(AllelealiasReference,
                                  Referencedbentity.pmid).filter\
            (AllelealiasReference.allele_alias_id == item.allele_alias_id).outerjoin(Referencedbentity).all()
        alias_pmids_results = ["PMID:"+str(y[1]) for y in a_pmids if str(y[1]) != 'None']

        if (len(alias_pmids_results) == 0):
            obj.append({
            "display_text": item.display_name,
            "format_text": item.display_name,
            "synonym_scope_name": "exact",
            "name_type_name": "uniform",
            "internal": False,
            "obsolete": False,
            "created_by_curie": "SGD",
            "updated_by_curie": "SGD",
            "date_created": item.date_created.strftime("%Y-%m-%dT%H:%m:%S-00:00"),
            "date_updated": item.date_created.strftime("%Y-%m-%dT%H:%m:%S-00:00")
            })
        if (len(alias_pmids_results) > 0):
            obj.append({
            "display_text": item.display_name,
            "format_text": item.display_name,
            "synonym_scope_name": "exact",
            "name_type_name": "unspecified",
            "internal": False,
            "obsolete": False,
            "created_by_curie": "SGD",
            "updated_by_curie": "SGD",
            "date_created": item.date_created.strftime("%Y-%m-%dT%H:%m:%S-00:00"),
            "date_updated": item.date_created.strftime("%Y-%m-%dT%H:%m:%S-00:00"),
            "evidence_curies": alias_pmids_results
            })
    return obj

def get_locus_crossrefs(locus_alias_list):

    obj = []
    for item in locus_alias_list:
        if (item.alias_type == "UniProtKB ID"):
            obj.append({
                "referenced_curie": "UniProtKB:"+item.display_name,
                "created_by_curie": "SGD",
                "updated_by_curie": "SGD",
                "page_area": "default",
                "prefix": "UniProtKB",
                "display_name": "UniProtKB:"+item.display_name,
                "internal": False
            })
        if (item.alias_type == "Gene ID" and item.source.display_name == 'NCBI'):
            obj.append({
                "referenced_curie": "NCBI_Gene:"+item.display_name,
                "created_by_curie": "SGD",
                "updated_by_curie": "SGD",
                "page_area": "default",
                "prefix": "NCBI_Gene",
                "display_name": "NCBI_Gene:"+item.display_name,
                "internal": False
            })
    return obj

def get_locus_secondaryids(locus_alias_list):

    obj = []
    for item in locus_alias_list:
        if (item.alias_type == "SGDID Secondary"):
            obj.append({
             "secondary_id": item.source.display_name + ":" +item.display_name,
              "internal": False
            })
    return obj

def get_output(result_data):

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

def get_pers_output(submission_type, result_data, linkml_version):

    if (result_data):
        output_obj = {
            "linkml_version": linkml_version,
            submission_type : result_data
        }
        return output_obj
    else:
        return None
