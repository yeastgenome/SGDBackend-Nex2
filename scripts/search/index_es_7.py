from src.models import DBSession, Base, Colleague, ColleagueLocus, Dbentity, Locusdbentity, Filedbentity, FileKeyword, LocusAlias, Dnasequenceannotation, So, Locussummary, Phenotypeannotation, PhenotypeannotationCond, Phenotype, Goannotation, Go, Goslimannotation, Goslim, Apo, Straindbentity, Strainsummary, Reservedname, GoAlias, Goannotation, Referencedbentity, Referencedocument, Referenceauthor, ReferenceAlias, Chebi, Disease, Diseaseannotation, DiseaseAlias, Complexdbentity, ComplexAlias, ComplexReference, Complexbindingannotation
from sqlalchemy import create_engine, and_
from elasticsearch import Elasticsearch
#from mapping import mapping
from es7_mapping import mapping
import os
import requests
from threading import Thread
import json
import collections
from index_es_helpers import IndexESHelper
import concurrent.futures
import uuid
import logging


engine = create_engine(os.environ["NEX2_URI"], pool_recycle=3600)
DBSession.configure(bind=engine)
Base.metadata.bind = engine

INDEX_NAME = os.environ.get("ES_INDEX_NAME", "searchable_items_aws")
DOC_TYPE = "searchable_item"
ES_URI = os.environ["WRITE_ES_URI"]
es = Elasticsearch(ES_URI, retry_on_timeout=True)


def delete_mapping():
    print("Deleting mapping...")
    response = requests.delete(ES_URI + INDEX_NAME + "/")
    if response.status_code != 200:
        print(("ERROR: " + str(response.json())))
    else:
        print("SUCCESS")


def put_mapping():
    print("Putting mapping... ")
    try:
        response = requests.put(ES_URI + INDEX_NAME + "/", json=mapping)
        if response.status_code != 200:
            print(("ERROR: " + str(response.json())))
        else:
            print("SUCCESS")
    except Exception as e:
        print(e)


def cleanup():
    delete_mapping()
    put_mapping()


def setup():
    # see if index exists, if not create it
    indices = list(es.indices.get_alias().keys())
    index_exists = INDEX_NAME in indices
    if not index_exists:
        put_mapping()


def index_not_mapped_genes():
    url = "https://downloads.yeastgenome.org/curation/literature/genetic_loci.tab"
    bulk_data = []
    with open("./scripts/search/not_mapped.json",
              "r") as json_data:
        _data = json.load(json_data)
        print(("indexing " + str(len(_data)) + " not physically mapped genes"))
        for item in _data:
            temp_aliases = []
            if len(item["FEATURE_NAME"]) > 0:
                obj = {
                    "name": item["FEATURE_NAME"],
                    "href": url,
                    "category": "locus",
                    "feature_type": ["Unmapped Genetic Loci"],
                    "aliases": item["ALIASES"].split("|"),
                    "description": item["DESCRIPTION"],
                    "is_quick_flag": "False"
                }
                bulk_data.append({
                    "index": {
                        "_index": INDEX_NAME,
                        "_id": str(uuid.uuid4())
                    }
                })
                bulk_data.append(obj)
                if len(bulk_data) == 300:
                    es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
                    bulk_data = []

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_downloads():
    bulk_data = []
    dbentity_file_obj = IndexESHelper.get_file_dbentity_keyword()
    files = DBSession.query(Filedbentity).filter(Filedbentity.is_public == True,
                                                 Filedbentity.s3_url != None).all()
    print(("indexing " + str(len(files)) + " download files"))
    for x in files:
        try:
            keyword = []
            status = ""
            temp = dbentity_file_obj.get(x.dbentity_id)
            if temp:
                keyword = temp
            if (x.dbentity_status == "Active" or x.dbentity_status == "Archived"):
                if x.dbentity_status == "Active":
                    status = "Active"
                else:
                    status = "Archived"

            obj = {
                ""
                "name":
                    x.display_name,
                "href": x.s3_url if x else None,
                "category":
                    "download",
                "description":
                    x.description,
                "keyword":
                    keyword,
                "format":
                    str(x.format.display_name),
                "status":
                    str(status),
                "file_size":
                    str(IndexESHelper.convertBytes(x.file_size))
                    if x.file_size is not None else x.file_size,
                "year":
                    str(x.year),
                "readme_url": x.readme_file.s3_url if x.readme_file else None,
                "topic": x.topic.display_name,
                "data": x.data.display_name,
                "path_id": x.get_path_id()
            }

            bulk_data.append({
                "index": {
                    "_index": INDEX_NAME,
                    "_id": str(uuid.uuid4())
                }
            })

            bulk_data.append(obj)
            if len(bulk_data) == 50:
                es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
                bulk_data = []

        except Exception as e:
            logging.error(e.message)

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_reserved_names():
    # only index reservednames that do not have a locus associated with them
    reserved_names = DBSession.query(Reservedname).all()

    print(("Indexing " + str(len(reserved_names)) + " reserved names"))
    for reserved_name in reserved_names:
        name = reserved_name.display_name
        href = reserved_name.obj_url
        keys = [reserved_name.display_name.lower()]
        # change name if has an orf
        if reserved_name.locus_id:
            locus = DBSession.query(Locusdbentity).filter(
                Locusdbentity.dbentity_id == reserved_name.locus_id).one_or_none()
            name = name + " / " + locus.systematic_name
            href = locus.obj_url
            keys = []
        obj = {
            "name": name,
            "href": href,
            "description": reserved_name.name_description,
            "category": "reserved_name",
            "keys": keys
        }
        es.index(
            index=INDEX_NAME, body=obj, id=str(uuid.uuid4()))

def index_part_1():
    index_downloads()
    index_not_mapped_genes()


def index_part_2():
    index_reserved_names()
    index_toolbar_links()


def index_toolbar_links():
    links = [
        ("Gene List", "https://yeastmine.yeastgenome.org/yeastmine/bag.do", []),
        ("Yeastmine", "https://yeastmine.yeastgenome.org", "yeastmine"),
        ("Submit Data", "/submitData", []),
        ("SPELL", "https://spell.yeastgenome.org", "spell"),
        ("BLAST", "/blast-sgd", "blast"),
        ("Fungal BLAST", "/blast-fungal", "blast"),
        ("Pattern Matching", "/nph-patmatch", []),
        ("Design Primers", "/primer3", []),
        ("Restriction Mapper", "/restrictionMapper", []),
        ("Genome Browser", "https://browse.yeastgenome.org", []),
        ("Gene/Sequence Resources", "/seqTools", []),
        ("Download Genome", "https://downloads.yeastgenome.org/sequence/S288C_reference/genome_releases/", "download"),
        ("Genome Snapshot", "/genomesnapshot", []),
        ("Chromosome History", "https://wiki.yeastgenome.org/index.php/Summary_of_Chromosome_Sequence_and_Annotation_Updates", []),
        ("Systematic Sequencing Table", "/cache/chromosomes.shtml", []),
        ("Original Sequence Papers",
         "http://wiki.yeastgenome.org/index.php/Original_Sequence_Papers", []),
        ("Variant Viewer", "/variant-viewer", []),
        ("GO Term Finder", "/goTermFinder", "go"),
        ("GO Slim Mapper", "/goSlimMapper", "go"),
        ("GO Slim Mapping File",
         "https://downloads.yeastgenome.org/curation/literature/go_slim_mapping.tab", "go"),
        ("Expression", "https://spell.yeastgenome.org/#", []),
        ("Biochemical Pathways", "http://pathway.yeastgenome.org/", []),
        ("Browse All Phenotypes", "/ontology/phenotype/ypo", []),
        ("Interactions", "/interaction-search", []),
        ("YeastGFP", "https://yeastgfp.yeastgenome.org/", "yeastgfp"),
        ("Full-text Search", "http://textpresso.yeastgenome.org/", "texxtpresso"),
        ("New Yeast Papers", "/reference/recent", []),
        ("Genome-wide Analysis Papers",
         "https://yeastmine.yeastgenome.org/yeastmine/loadTemplate.do?name=GenomeWide_Papers&scope=all&method=results&format=tab", []),
        ("Find a Colleague", "/search?q=&category=colleague", []),
        ("Add or Update Info", "/colleague_update", []),
        ("Career Resources", "http://wiki.yeastgenome.org/index.php/Career_Resources", []),
        ("Future", "http://wiki.yeastgenome.org/index.php/Meetings#Upcoming_Conferences_.26_Courses", []),
        ("Yeast Genetics", "http://wiki.yeastgenome.org/index.php/Meetings#Past_Yeast_Meetings", []),
        ("Submit a Gene Registration", "/reserved_name/new", []),
        ("Nomenclature Conventions",
         "https://sites.google.com/view/yeastgenome-help/community-help/nomenclature-conventions", []),
        ("Strains and Constructs", "http://wiki.yeastgenome.org/index.php/Strains", []),
        ("Reagents", "http://wiki.yeastgenome.org/index.php/Reagents", []),
        ("Protocols and Methods", "http://wiki.yeastgenome.org/index.php/Methods", []),
        ("Physical & Genetic Maps",
         "http://wiki.yeastgenome.org/index.php/Combined_Physical_and_Genetic_Maps_of_S._cerevisiae", []),
        ("Genetic Maps", "http://wiki.yeastgenome.org/index.php/Yeast_Mortimer_Maps_-_Edition_12", []),
        ("Sequence", "http://wiki.yeastgenome.org/index.php/Historical_Systematic_Sequence_Information", []),
        ("Wiki", "http://wiki.yeastgenome.org/index.php/Main_Page", "wiki"),
        ("Resources", "http://wiki.yeastgenome.org/index.php/External_Links", [])
    ]

    print(("Indexing " + str(len(links)) + " toolbar links"))

    for l in links:
        obj = {
            "name": l[0],
            "href": l[1],
            "description": None,
            "category": "resource",
            "keys": l[2]
        }
        es.index(index=INDEX_NAME, body=obj, id=l[1])

if __name__ == "__main__":
    '''
        To run multi-processing add this: 
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
            index_references()
    '''

    cleanup()
    setup()
    t1 = Thread(target=index_part_1)
    t2 = Thread(target=index_part_2)
    t1.start()
    t2.start()
