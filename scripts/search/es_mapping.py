es_mapping = {
    "settings": {
        "index": {
            "max_result_window": 15000,
            "analysis": {
                "analyzer": {
                    "default": {
                        "type": "standard"
                    },
                    "autocomplete": {
                        "type": "custom",
                        "filter": ["lowercase", "autocomplete_filter"],
                        "tokenizer": "standard"
                    },
                    "raw": {
                        "type": "custom",
                        "filter": ["lowercase"],
                        "tokenizer": "keyword"
                    }
                },
                "filter": {
                    "autocomplete_filter": {
                        "min_gram": "1",
                        "type": "edge_ngram",
                        "max_gram": "20"
                    }
                }
            },
            "number_of_replicas": "1",
            "number_of_shards": "5"
        }
    },
    "mappings": {
        "searchable_item": {
            "properties": {
                "biological_process": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "category": {
                    "type": "text"
                },
                "observable": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "qualifier": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "references": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "phenotype_loci": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },

                "keys": {
                    "type": "text"
                },
                "secondary_sgdid": {
                    "type": "text"
                },
                "chemical": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "mutant_type": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "go_loci": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "do_loci": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "strain": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "author": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "journal": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "year": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "first_name": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        },
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "autocomplete"
                        }
                    }
                },
                "last_name": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        },
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "autocomplete"
                        }
                    }
                },
                "institution": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        },
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "autocomplete"
                        }
                    }
                },
                "position": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "country": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        },
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "autocomplete"
                        }
                    }
                },
                "state": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        },
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "autocomplete"
                        }
                    }
                },
                "colleague_loci": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "keywords": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        },
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "autocomplete"
                        }
                    }
                },
                "reference_loci": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "ec_number": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "tc_number": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "cellular_component": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "description": {
                    "type": "text"
                },
                "sequence_history": {
                    "type": "text"
                },
                "gene_history": {
                    "type": "text"
                },
                "summary": {
                    "type": "text"
                },
                "feature_type": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "href": {
                    "type": "text"
                },
                "molecular_function": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "name": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "analyzer": "raw"
                        },
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "autocomplete"
                        },
                        "search": {
                            "type": "text",
                            "analyzer": "default"
                        },
                    }
                },
                "go_id": {
                    "type": "text"
                },
                "do_id": {
                    "type": "text"
                },
                "number_annotations": {
                    "type": "integer"
                },
                "name_description": {
                    "type": "text"
                },
                "synonyms": {
                    "type": "text"
                },
                "phenotypes": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "aliases": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "format": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "keyword": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "status": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "file_size": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "readme_url": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "topic": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "data": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "is_quick_flag": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "categories": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "tags": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                },
                "month": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "text",
                            "index": False
                        }
                    }
                }
            }
        }
    }
}
