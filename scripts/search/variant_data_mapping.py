mapping = {
    "settings": {
        "index": {
            "max_result_window": 15000,
            "number_of_replicas": 1,
            "number_of_shards": 1,
            "max_ngram_diff": 10
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
                    ]
                },
                "autocomplete_search": {
                    "tokenizer": "autosuggest_search",
                    "filter": [
                        "lowercase"
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
                    "max_gram": "5"
                },
                "autosuggest_search": {
                    "type": "edge_ngram",
                    "min_gram": "2",
                    "max_gram": "5"
                },
                "regular_partial_search": {
                    "type": "ngram",
                    "min_gram": "2",
                    "max_gram": "5",
                    "token_chars": [
                        "letter",
                        "digit"
                    ]
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
            "sgdid": {
                "type": "text",
                "fielddata": True,
                "analyzer": "symbols"
            },
            "name": {
                "type": "text",
                "fielddata": True,
                "analyzer": "symbols"
            },
            "href": {
                "type": "text",
                "fielddata": True,
                "analyzer": "symbols"
            },
            "category": {
                "type": "text",
                "fielddata": True,
                "analyzer": "symbols"
            },
            "absolute_genetic_start": {
                "type": "keyword"
            },
            "format_name": {
                "type": "text",
                "fielddata": True,
                "analyzer": "symbols"
            },
            "dna_scores": {
                "type": "keyword"
            },
            "protein_scores": {
                "type": "keyword"
            },
            "snp_seqs": {
                "type": "nested"
            }
        }
    }
}
