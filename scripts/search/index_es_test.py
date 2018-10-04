from src.models import DBSession, Base, Colleague, ColleagueLocus, Dbentity, Locusdbentity, Filedbentity, FileKeyword, LocusAlias, Dnasequenceannotation, So, Locussummary, Phenotypeannotation, PhenotypeannotationCond, Phenotype, Goannotation, Go, Goslimannotation, Goslim, Apo, Straindbentity, Strainsummary, Reservedname, GoAlias, Goannotation, Referencedbentity, Referencedocument, Referenceauthor, ReferenceAlias, Chebi, Disease, Diseaseannotation, DiseaseAlias, Complexdbentity, ComplexAlias, ComplexReference, Complexbindingannotation
from sqlalchemy import create_engine, and_
from elasticsearch import Elasticsearch
from mapping import mapping
import os
import requests
from threading import Thread
import json
import collections
from index_es_helpers import IndexESHelper
import concurrent.futures
import uuid


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
        print("ERROR: " + str(response.json()))
    else:
        print("SUCCESS")


def put_mapping():
    print("Putting mapping... ")
    response = requests.put(ES_URI + INDEX_NAME + "/", json=mapping)
    if response.status_code != 200:
        print("ERROR: " + str(response.json()))
    else:
        print("SUCCESS")


def index_toolbar_links():
    links = [
        ("Gene List", "https://yeastmine.yeastgenome.org/yeastmine/bag.do",
         []), ("Yeastmine", "https://yeastmine.yeastgenome.org",
               "yeastmine"), ("Submit Data", "/cgi-bin/submitData.pl",
                              []), ("SPELL", "https://spell.yeastgenome.org",
                                    "spell"), ("BLAST", "/blast-sgd", "blast"),
        ("Fungal BLAST", "/blast-fungal",
         "blast"), ("Pattern Matching", "/nph-patmatch",
                    []), ("Design Primers", "/cgi-bin/web-primer", []),
        ("Restriction Mapper", "/cgi-bin/PATMATCH/RestrictionMapper",
         []), ("Genome Browser", "/browse",
                             []), ("Gene/Sequence Resources",
                                   "/seqTools", []),
        ("Download Genome",
         "https://downloads.yeastgenome.org/sequence/S288C_reference/genome_releases/",
         "download"), ("Genome Snapshot", "/genomesnapshot",
                       []), ("Chromosome History",
                             "/cgi-bin/chromosomeHistory.pl", []),
        ("Systematic Sequencing Table", "/cache/chromosomes.shtml",
         []), ("Original Sequence Papers",
               "http://wiki.yeastgenome.org/index.php/Original_Sequence_Papers",
               []), ("Variant Viewer", "/variant-viewer",
                     []), ("Align Strain Sequences",
                           "/cgi-bin/FUNGI/alignment.pl", []),
        ("Synteny Viewer", "/cgi-bin/FUNGI/FungiMap",
         []), ("Fungal Alignment", "/cgi-bin/FUNGI/showAlign",
               []), ("PDB Search", "/cgi-bin/protein/get3d",
                     "pdb"), ("GO Term Finder", "/cgi-bin/GO/goTermFinder.pl",
                              "go"), ("GO Slim Mapper",
                                      "/cgi-bin/GO/goSlimMapper.pl", "go"),
        ("GO Slim Mapping File",
         "https://downloads.yeastgenome.org/curation/literature/go_slim_mapping.tab",
         "go"), ("Expression", "https://spell.yeastgenome.org/#",
                 []), ("Biochemical Pathways",
                       "http://pathway.yeastgenome.org/",
                       []), ("Browse All Phenotypes", "/ontology/phenotype/ypo",
                             []), ("Interactions", "/interaction-search", []),
        ("YeastGFP", "https://yeastgfp.yeastgenome.org/",
         "yeastgfp"), ("Full-text Search", "http://textpresso.yeastgenome.org/",
                       "texxtpresso"), ("New Yeast Papers", "/reference/recent",
                                        []),
        ("Genome-wide Analysis Papers", "/cache/genome-wide-analysis.html",
         []), ("Find a Colleague", "/cgi-bin/colleague/colleagueInfoSearch",
               []), ("Add or Update Info", "/cgi-bin/colleague/colleagueSearch",
                     []), ("Find a Yeast Lab", "/cache/yeastLabs.html", []),
        ("Career Resources",
         "http://wiki.yeastgenome.org/index.php/Career_Resources", []),
        ("Future",
         "http://wiki.yeastgenome.org/index.php/Meetings#Upcoming_Conferences_.26_Courses",
         []),
        ("Yeast Genetics",
         "http://wiki.yeastgenome.org/index.php/Meetings#Past_Yeast_Meetings",
         []), ("Submit a Gene Registration", "/cgi-bin/registry/geneRegistry",
               []), ("Gene Registry", "/help/community/gene-registry",
                     []), ("Nomenclature Conventions",
                           "/help/community/nomenclature-conventions", []),
        ("Global Gene Hunter", "/cgi-bin/geneHunter",
         []), ("Strains and Constructs",
               "http://wiki.yeastgenome.org/index.php/Strains",
               []), ("Reagents",
                     "http://wiki.yeastgenome.org/index.php/Reagents",
                     []), ("Protocols and Methods",
                           "http://wiki.yeastgenome.org/index.php/Methods", []),
        ("Physical & Genetic Maps",
         "http://wiki.yeastgenome.org/index.php/Combined_Physical_and_Genetic_Maps_of_S._cerevisiae",
         []),
        ("Genetic Maps",
         "http://wiki.yeastgenome.org/index.php/Yeast_Mortimer_Maps_-_Edition_12",
         []),
        ("Sequence",
         "http://wiki.yeastgenome.org/index.php/Historical_Systematic_Sequence_Information",
         []), ("Wiki", "http://wiki.yeastgenome.org/index.php/Main_Page",
               "wiki"), ("Resources",
                         "http://wiki.yeastgenome.org/index.php/External_Links",
                         [])
    ]

    print("Indexing " + str(len(links)) + " toolbar links")

    for l in links:
        obj = {
            "name": l[0],
            "href": l[1],
            "description": None,
            "category": "resource",
            "keys": l[2]
        }
        es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=obj, id=l[1])


def index_colleagues():
    colleagues = DBSession.query(Colleague).all()
    _locus_ids = IndexESHelper.get_colleague_locus()
    _locus_names = IndexESHelper.get_colleague_locusdbentity()
    _combined_list = IndexESHelper.combine_locusdbentity_colleague(
        colleagues, _locus_names, _locus_ids)
    print("Indexing " + str(len(colleagues)) + " colleagues")
    bulk_data = []
    for item_k, item_v in _combined_list.items():
        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                "_type": DOC_TYPE,
                "_id": str(uuid.uuid4())
            }
        })

        bulk_data.append(item_v)
        if len(bulk_data) == 1000:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []
    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_phenotypes():
    bulk_data = []
    phenotypes = DBSession.query(Phenotype).all()
    _result = IndexESHelper.get_pheno_annotations(phenotypes)
    print("Indexing " + str(len(_result)) + " phenotypes")
    for phenotype_item in _result:
        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                "_type": DOC_TYPE,
                "_id": str(uuid.uuid4())
            }
        })
        bulk_data.append(phenotype_item)
        if len(bulk_data) == 50:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []
    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def cleanup():
    delete_mapping()
    put_mapping()


def setup():
    # see if index exists, if not create it
    indices = es.indices.get_alias("*").keys()
    index_exists = INDEX_NAME in indices
    if not index_exists:
        put_mapping()


if __name__ == "__main__":
    '''
        To run multi-processing add this: 
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
            index_references()
    '''
    cleanup()
    setup()
    index_toolbar_links()
    index_colleagues()
    index_phenotypes()