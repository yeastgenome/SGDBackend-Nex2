mapping = {
    "settings": {
        "index": {
            "max_result_window": 15000,
            "number_of_replicas": 1,
            "number_of_shards": 1,
            "max_ngram_diff": 20

        },
        "analysis": {
            "analyzer": {
                "default": {
                    "type": "custom",
                    "tokenizer": "whitespace",
                    "filter": [
                            "english_stemmer",
                            "lowercase"
                    ]
                },
                "autocomplete": {
                    "tokenizer": "autocomplete_index",
                    "filter": [
                        "lowercase"
                    ],
                    "char_filter": [
                        "replace_underscore"
                    ]
                },
                "autocomplete_search": {
                    "tokenizer": "autosuggest_search",
                    "filter": [
                        "lowercase"
                    ],
                    "char_filter": [
                        "replace_underscore"
                    ]
                },
                "partial_search": {
                    "tokenizer": "regular_partial_search",
                    "filter": ["lowercase"]
                },
                "symbols": {
                    "type": "custom",
                    "tokenizer": "whitespace",
                    "filter": [
                            "lowercase"
                    ]
                },
                "keyword": {
                    "type": "custom",
                    "tokenizer": "keyword"
                },
                "locus_search": {
                    "type": "custom",
                    "tokenizer": "locus_name_search",
                    "filter": [
                        "lowercase"
                    ]
                },
                "function_search": {
                    "type": "custom",
                    "tokenizer": "function_name_search",
                    "filter": [
                        "lowercase"
                    ]
                },
                "reference_search": {
                    "type": "custom",
                    "tokenizer": "reference_name_search",
                    "filter": [
                        "lowercase"
                    ]
                },
                "identity_search": {
                    "type": "custom",
                    "tokenizer": "id_search",
                    "filter": [
                        "lowercase"
                    ]
                },
                "chebi_search": {
                    "type": "custom",
                    "tokenizer": "chebi_name_search",
                    "filter": [
                        "lowercase"
                    ]
                },
                "alias_search": {
                    "type": "custom",
                    "tokenizer": "alias_name_search",
                    "filter": [
                        "lowercase"
                    ]
                },
                "other_search": {
                    "type": "custom",
                    "tokenizer": "other_name_search"
                },
                "locus_summary_search": {
                    "type": "custom",
                    "tokenizer": "locus_summary_text_search",
                }
            },
            "filter": {
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                }
            },
            "tokenizer": {
                "autocomplete_index": {
                    "type": "edge_ngram",
                    "min_gram": "2",
                    "max_gram": "20"
                },
                "autosuggest_search": {
                    "type": "edge_ngram",
                    "min_gram": "2",
                    "max_gram": "20"
                },
                "regular_partial_search": {
                    "type": "ngram",
                    "min_gram": "2",
                    "max_gram": "20",
                    "token_chars": [
                        "letter",
                        "digit"
                    ]
                },
                "locus_name_search": {
                    "type": "edge_ngram",
                    "min_gram": "1",
                    "max_gram": "10",
                    "token_chars": [
                        "letter",
                        "digit"
                    ]
                },
                "function_name_search": {
                    "type": "edge_ngram",
                    "min_gram": "4",
                    "max_gram": "50",
                    "token_chars": [
                        "letter",
                        "digit",
                        "punctuation"
                    ]
                },
                "reference_name_search": {
                    "type": "edge_ngram",
                    "min_gram": "10",
                    "max_gram": "30",
                    "token_chars": [
                        "letter"
                    ]
                },
                "id_search": {
                    "type": "edge_ngram",
                    "min_gram": "5",
                    "max_gram": "15"
                },
                "chebi_name_search": {
                    "type": "edge_ngram",
                    "min_gram": "1",
                    "max_gram": "100"
                },
                "alias_name_search": {
                    "type": "edge_ngram",
                    "min_gram": "3",
                    "max_gram": "10",
                    "token_chars": [
                        "letter",
                        "digit",
                        "punctuation",
                        "symbol"
                    ]

                },
                "other_name_search": {
                    "type": "edge_ngram",
                    "min_gram": "2",
                    "max_gram": "10"
                },
                "locus_summary_text_search": {
                    "type": "edge_ngram",
                    "min_gram": "5",
                    "max_gram": "100"
                }
            },
            "char_filter": {
                "replace_underscore": {
                    "type": "pattern_replace",
                    "pattern": "(_)",
                    "replacement": " "
                }
            }
        }
    },
    "mappings": {
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
                        "analyzer": "autocomplete",
                        "search_analyzer": "autocomplete_search"
                    }
                }
            },
            "identifier": {
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
                        "analyzer": "autocomplete",
                        "search_analyzer": "autocomplete_search"
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
            "resource_name": {
                "type": "keyword"
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
                "fielddata": True,
                "fields": {
                    "ngram": {
                        "type": "text",
                        "analyzer": "partial_search"
                    }
                }
            },
            "summary": {
                "type": "text",
                "fielddata": True
            },
            "phenotypes": {
                "type": "keyword",
                "fields": {
                    "engram": {
                        "type": "text",
                        "analyzer": "other_search"
                    }
                }
            },
            "diseases": {
                "type": "keyword",
                "fields": {
                    "engram": {
                        "type": "text",
                        "analyzer": "other_search"
                    }
                }
            },
            "cellular_component": {
                "type": "keyword",
                "fields": {
                    "engram": {
                        "type": "text",
                        "analyzer": "function_search"
                    },
                    "name": {
                        "type": "text",
                        "analyzer": "symbols"
                    }
                }
            },
            "biological_process": {
                "type": "keyword",
                "fields": {
                    "engram": {
                        "type": "text",
                        "analyzer": "function_search"
                    },
                    "name": {
                        "type": "text",
                        "analyzer": "symbols"
                    }
                }
            },
            "molecular_function": {
                "type": "keyword",
                "fields": {
                    "engram": {
                        "type": "text",
                        "analyzer": "function_search"
                    },
                    "name": {
                        "type": "text",
                        "analyzer": "symbols"
                    }
                }
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
                "analyzer": "identity_search"
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
                "analyzer": "keyword",
                "fields": {
                    "engram": {
                        "type": "text",
                        "analyzer": "other_search"
                    }
                }
            },
            "complex_loci": {
                "type": "text",
                "fielddata": True,
                "analyzer": "keyword",
                "fields": {
                    "engram": {
                        "type": "text",
                        "analyzer": "other_search"
                    }
                }
            },
            "pathway_loci": {
                "type": "text",
                "fielddata": True,
                "analyzer": "keyword",
                "fields": {
                    "engram": {
                        "type": "text",
                        "analyzer": "other_search"
                    }
                }
            },
            "allele_loci": {
                "type": "text",
                "fielddata": True,
                "analyzer": "keyword",
                "fields": {
                    "engram": {
                        "type": "text",
                        "analyzer": "other_search"
                    }
                }
            },
            "allele_types": {
                "type": "text",
                "fielddata": True,
                "analyzer": "keyword",
                "fields": {
                    "engram": {
                        "type": "text",
                        "analyzer": "other_search"
                    }
                }
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
                "analyzer": "identity_search"
            },
            "gene_ontology_loci": {
                "type": "text",
                "fielddata": True,
                "analyzer": "keyword"
            },
            "do_id": {
                "type": "text",
                "analyzer": "identity_search"
            },
            "disease_loci": {
                "type": "text",
                "fielddata": True,
                "analyzer": "keyword"
            },
            "author": {
                "type": "text",
                "fielddata": True,
                "analyzer": "keyword",
                "fields": {
                    "white_space": {
                        "type": "text",
                        "analyzer": "other_search"
                    }
                }
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
            "associated_complexes": {
                "type": "text",
                "fielddata": True,
                "analyzer": "keyword"
            },
            "associated_pathways": {
                "type": "text",
                "fielddata": True,
                "analyzer": "keyword"
            },
            "associated_alleles": {
                "type": "text",
                "fielddata": True,
                "analyzer": "keyword"
            },
            "associated_strains": {
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
                    },
                    "egram": {
                        "type": "text",
                        "analyzer": "alias_search",
                        "search_analyzer": "alias_search"
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
            },
            "colleague_name": {
                "type": "text",
                "fielddata": True,
                "fields": {
                        "white_space": {
                            "type": "text",
                            "analyzer": "symbols",
                        },
                        "ngram": {
                            "type": "text",
                            "analyzer": "partial_search"
                        },
                        "engram": {
                            "type": "text",
                            "analyzer": "other_search",
                            "search_analyzer": "other_search"
                        }
                }
            },
            "locus_name": {
                "type": "text",
                "fielddata": True,
                "fields": {
                    "ngram": {
                        "type": "text",
                        "analyzer": "partial_search",
                        "search_analyzer": "partial_search"
                    },
                    "engram": {
                        "type": "text",
                        "analyzer": "locus_search",
                        "search_analyzer": "locus_search"
                    }

                }
            },
            "raw_display_name": {
                "type": "text",
                "analyzer": "autocomplete_search"
            },
            "ref_citation": {
                "type": "text",
                "analyzer": "reference_search"
            },
            "locus_summary": {
                "type": "text",
                "analyzer": "locus_summary_search"
            },
            "sys_name": {
                "type": "text",
                "analyzer": "reference_search"
            },
            "unmapped_name": {
                "type": "text",
                "analyzer": "reference_search"

            },
            "observable_name": {
                "type": "text",
                "analyzer": "reference_search"

            },
            "strain_name": {
                "type": "text",
                "analyzer": "reference_search"

            },
            "disease_name": {
                "type": "text",
                "analyzer": "reference_search"

            },
            "reference_name": {
                "type": "text",
                "analyzer": "reference_search"

            },
            "complex_name": {
                "type": "text",
                "analyzer": "reference_search"

            },
            "pathway_name": {
                "type": "text",
                "analyzer": "reference_search"

            },
            "biocyc_id": {
                "type": "text",
                "fielddata": True,
                "analyzer": "reference_search"
            },
            "allele_name": {
                "type": "text",
                "analyzer": "reference_search"

            },
            "chemical_name": {
                "type": "text",
                "analyzer": "chebi_search"
            },
            "ncbi": {
                "type": "nested"
            }

        }
    }
}
