mapping = {
    "settings": {
        "index": {
            "max_result_window": 7000,
            "number_of_replicas": 1,
            "number_of_shards": 1,
            "max_ngram_diff": 5
        },
    },
    "mappings": {
        "properties": {
            "sgdid": {
                "type": "text"
            },
            "name": {
                "type": "text"
            },
            "href": {
                "type": "text"
            },
            "absolute_genetic_start": {
                "type": "integer"
            },
            "format_name": {
                "type": "text"
            },
            "dna_scores": {
                "type": "object"
            },
            "protein_scores": {
                "type": "object"
            },
            "snp_seqs": {
                "type": "object"
            }
        }
    }
}
