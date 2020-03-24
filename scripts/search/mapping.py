mapping = {
    "settings": {
        "index": {
            "max_result_window": 15000,
            "analysis": {
                "analyzer": {
                    "default": {
                        "type": "custom",
                        "tokenizer": "whitespace",
                        "filter": ["english_stemmer", "lowercase"]
                    },
                    "autocomplete": {
                        "type": "custom",
                        "tokenizer": "whitespace",
                        "filter": ["lowercase", "autocomplete_filter"]
                    },
                    "symbols": {
                        "type": "custom",
                        "tokenizer": "whitespace",
                        "filter": ["lowercase"]
                    },
                    "keyword": {
                        "type": "custom",
                        "tokenizer": "keyword",
                        "filter": ["lowercase"]
                    }
                },
                "filter": {
                    "english_stemmer": {
                        "type": "stemmer",
                        "language": "english"
                    },
                    "autocomplete_filter": {
                        "type": "edge_ngram",
                        "min_gram": "1",
                        "max_gram": "20"
                    }
                }
            },
            "number_of_replicas": "1",  # temporarily
            "number_of_shards": "3"
        }
    },

    "mappings": {  # having a raw field means it can be a facet or sorted by
        "searchable_item": {
            "properties": {
                "name": {
                    "type": "text",
                    "fielddata": True,
                    "fields": {
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        },
                        "raw": {
                            "type": "keyword",
                            "index": False
                        },
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "autocomplete"
                        }
                    }
                },
                "category": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "href": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "description": {
                    "type": "text",
                    "fielddata": True
                },
                "first_name": {
                    "type": "keyword"
                },
                "last_name": {
                    "type": "keyword"
                },
                "institution": {
                    "type": "keyword"
                },
                "position": {
                    "type": "keyword"
                },
                "country": {
                    "type": "keyword"
                },
                "state": {
                    "type": "keyword"
                },
                "colleague_loci": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "keyword"
                },
                "number_annotations": {
                    "type": "integer"
                },
                "feature_type": {
                    "type": "keyword"
                },
                "name_description": {
                    "type": "text",
                    "fielddata": True
                },
                "summary": {
                    "type": "text",
                    "fielddata": True
                },
                "phenotypes": {
                    "type": "keyword"
                },
                "cellular_component": {
                    "type": "keyword"
                },
                "biological_process": {
                    "type": "keyword"
                },
                "molecular_function": {
                    "type": "keyword"
                },
                "ec_number": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "protein": {
                    "type": "keyword"
                },
                "tc_number": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "secondary_sgdid": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "sequence_history": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "gene_history": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "bioentity_id": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "chebiid": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "keys": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "status": {
                    "type": "keyword"
                },
                "observable": {
                    "type": "keyword"
                },
                "qualifier": {
                    "type": "keyword"
                },
                "references": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "keyword"
                },
                "phenotype_loci": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "keyword"
                },

                "chemical": {
                    "type": "keyword"
                },
                "mutant_type": {
                    "type": "keyword"
                },
                "synonyms": {
                    "type": "text",
                    "fielddata": True
                },
                "go_id": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "gene_ontology_loci": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "keyword"
                },
                "do_id": {
                    "type": "text",
                    "analyzer": "symbols"
                },
                "disease_loci": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "keyword"
                },
                "author": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "keyword"
                },
                "journal": {
                    "type": "keyword",
                    "index": True
                },
                "year": {
                    "type": "text",
                    "analyzer": "symbols",
                    "fielddata": True,
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "reference_loci": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "keyword"
                },
                "aliases": {
                    "type": "text",
                    "fielddata": True,
                    "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            }
                    }
                },
                "format": {
                    "type": "keyword"
                },
                "keyword": {
                    "type": "keyword"
                },
                "file_size": {
                    "type": "keyword"
                },
                "readme_url": {
                    "type": "keyword"
                },
                "topic": {
                    "type": "keyword"
                },
                "data": {
                    "type": "keyword"
                },
                "is_quick_flag": {
                    "type": "keyword"
                },
                "categories": {
                    "type": "keyword"
                },
                "tags": {
                    "type": "keyword"
                },
                "month": {
                    "type": "keyword"
                }
            }
        }
    }
}
