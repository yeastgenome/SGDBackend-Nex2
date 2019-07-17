from elasticsearch import Elasticsearch
import os
from sqlalchemy import create_engine
from threading import Thread

from index_elastic_search import *
from mapping import mapping

engine = create_engine(os.environ["NEX2_URI"], pool_recycle=3600)
DBSession.configure(bind=engine)
Base.metadata.bind = engine

INDEX_NAME = "searchable_items_test"
DOC_TYPE = "searchable_item"
ES_URI = os.environ["WRITE_ES_URI"]
es = Elasticsearch(ES_URI, retry_on_timeout=True)
record_limit = 25

def index_part_1():
    index_phenotypes(record_limit)
    index_downloads(record_limit)
    index_not_mapped_genes()
    index_genes(record_limit)
    index_strains(record_limit)
    index_colleagues(record_limit)
    index_chemicals(record_limit)


def index_part_2():
    index_reserved_names(record_limit)
    index_toolbar_links()
    index_observables(record_limit)
    index_go_terms(record_limit)
    index_disease_terms(record_limit)
    index_complex_names(record_limit)
    index_references(record_limit)

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