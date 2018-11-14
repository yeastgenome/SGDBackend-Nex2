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
            "number_of_replicas": "1", #temporarily
            "number_of_shards": "5"
        }
    },
    "mappings": { # having a raw field means it can be a facet or sorted by
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
                        "suggest": {
                            "type": "completion"
                        },
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
                    "fielddata": True,
                    "fielddata": True
                },
                "first_name": {
                    "type": "keyword",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "last_name": {
                    "type": "keyword",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "institution": {
                    "type": "keyword",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "position": {
                    "type": "keyword",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "country": {
                    "type": "keyword",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "state": {
                    "type": "keyword",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "colleague_loci": {
                    "type": "keyword",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        },
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        }

                    }
                },
                "number_annotations": {
                    "type": "integer"
                },
                "feature_type": {
                    "type": "keyword",
                    "fields": {
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        },
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "name_description": {
                    "type": "keyword"
                },
                "summary": {
                    "type": "keyword"
                },
                "phenotypes": {
                    "type": "keyword",
                    "fields": {
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        }
                    }
                },
                "cellular_component": {
                    "type": "keyword",
                    "fields": {
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        },
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "biological_process": {
                    "type": "keyword",
                    "fields": {
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        },
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "molecular_function": {
                    "type": "keyword",
                    "fields": {
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        },
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "ec_number": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "protein": {
                    "type": "keyword",
                    "fields": {
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        }
                    }
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
                    "type": "string",
                    "analyzer": "symbols"
                },
                "keys": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "status": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "observable": {
                    "type": "keyword",
                    "fields": {
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        },
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "qualifier": {
                    "type": "keyword",
                    "fields": {
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        },
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "references": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "phenotype_loci": {
                    "type": "keyword",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        },
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        }

                    }
                },
                
                "chemical": {
                    "type": "keyword",
                    "fields": {
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        },
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "mutant_type": {
                    "type": "keyword",
                    "fields": {
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        },
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "synonyms": {
                    "type": "keyword"
                },
                "go_id": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols"
                },
                "gene_ontology_loci": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        },
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        }

                    }
                },
                "do_id": {
                    "type": "text",
                    "analyzer": "symbols"
                },
                "disease_loci": {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        },
                        "symbol": {
                            "type": "text",
                            "analyzer": "symbols"
                        }

                    }
                },
                "author": {
                    "type": "text",
                    "fielddata": True,
                    "analyzer": "symbols",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "journal": {
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
                    "analyzer": "symbols",
                    "fielddata": True,
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "index": False
                        }
                    }
                },
                "aliases": {
                        "type": "text",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            },
                            "symbol": {
                                "type": "text",
                                "analyzer": "symbols"
                            }

                        }
                   },
                "format": {
                        "type": "text",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            },
                            "symbol": {
                                "type": "text",
                                "analyzer": "symbols"
                            }

                        }
                   },
                "keyword": {
                        "type": "text",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            },
                            "symbol": {
                                "type": "text",
                                "analyzer": "symbols"
                            }

                        }
                   },
                "file_size": {
                        "type": "text",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            },
                            "symbol": {
                                "type": "text",
                                "analyzer": "symbols"
                            }

                        }
                   },
                "readme_url": {
                        "type": "text",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            },
                            "symbol": {
                                "type": "text",
                                "analyzer": "symbols"
                            }

                        }
                   },
                "topic": {
                        "type": "text",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            },
                            "symbol": {
                                "type": "text",
                                "analyzer": "symbols"
                            }

                        }
                   },
                "data": {
                        "type": "text",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            },
                            "symbol": {
                                "type": "text",
                                "analyzer": "symbols"
                            }

                        }
                   },
                "is_quick_flag": {
                        "type": "keyword",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            },
                            "symbol": {
                                "type": "text",
                                "analyzer": "symbols"
                            }

                        }
                   },
                "categories": {
                        "type": "text",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            },
                            "symbol": {
                                "type": "text",
                                "analyzer": "symbols"
                            }

                        }
                   },
                "tags": {
                        "type": "text",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            },
                            "symbol": {
                                "type": "text",
                                "analyzer": "symbols"
                            }

                        }
                    },
                "month": {
                        "type": "keyword",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "index": False
                            },
                            "symbol": {
                                "type": "text",
                                "analyzer": "symbols"
                            }

                        }
                    }
                }
            }
        }
}
