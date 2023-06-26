from scripts.search.es7_mapping import mapping
import re

MAX_AGG_SIZE = 999
FIELD_MAP = mapping['mappings']['properties']


def build_autocomplete_search_body_request(query,
                                           category='locus',
                                           field='name'):
    _source_fields = ['name', 'identifier', 'reference_name', 'href', 'category', 'gene_symbol']
    if category == 'colleague':
        _source_fields = _source_fields + ['institution']
    es_query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "locus_name.engram^15",
                                "colleague_name.engram^7",
                                "name.autocomplete^8",
                                "identifier.autocomplete^15",
                                "name_description",
                                "author.white_space",
                                "aliases.egram^6",
                                "keys",
                                "cellular_component.engram",
                                "biological_process.engram",
                                "molecular_function.engram",
                                "locus_summary"
                            ]
                        }
                    }
                ],
                "should": {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "author.white_space"
                        ]
                    }
                }
            }
        },
        "_source": _source_fields
    }
# _source: _source_fields: depprecated
    if category != '':
        es_query["query"]["bool"]["must"].append(
            {"match": {"category": category}})
        if category != "locus":
            es_query["query"]["bool"].pop("should")

    if field != 'name':
        es_query['aggs'] = {}
        es_query['aggs'][field] = {
            'terms': {'field': field, 'size': 999}
        }

        es_query['query']['bool']['must'][0]['match'] = {}
        es_query['query']['bool']['must'][0]['match'][field + '.autocomplete'] = {
            'query': query,
            'analyzer': 'standard'
        }

        es_query['_source'] = [field, 'href', 'category']
    return es_query


def format_autocomplete_results(es_response, field='name'):
    formatted_results = []
    if field != 'name':
        results = es_response['aggregations'][field]['buckets']
        for r in results:
            obj = {
                'name': r['key']
            }
            formatted_results.append(obj)
    else:
        for hit in es_response['hits']['hits']:
            name = hit['_source']['name']
            if hit['_source'].get('identifier'):
                if hit['_source'].get('reference_name'):
                    name = hit['_source']['identifier'] + ": " + hit['_source']['reference_name']
                else:
                    name = hit['_source']['identifier'] + ": " + name
            obj = {
                'name': name,
                'href': hit['_source']['href'],
                'category': hit['_source']['category']
            }
            if 'institution' in hit['_source'].keys():
                obj['institution'] = hit['_source']['institution']
            if obj['category'] == 'colleague':
                format_name = hit['_source']['href'].replace('/colleague/', '')
                obj['format_name'] = format_name

            if hit['_source'].get('gene_symbol') and hit['_source']['category'] == "locus":
                obj['name'] = hit['_source']['gene_symbol'].upper()

            formatted_results.append(obj)
    return formatted_results


def build_es_aggregation_body_request(es_query, category, category_filters):
    agg_query_body = {
        'query': es_query,
        'size': 0,
        'aggs': {}
    }

    if category == '':
        agg_query_body['aggs'] = {
            'categories': {
                'terms': {'field': 'category', 'size': 50}
            }
        }
    elif category in category_filters.keys():
        for subcategory in category_filters[category]:
            agg_query_body['aggs'][subcategory[1]] = {
                'terms': {
                    'field': subcategory[1],
                    'size': MAX_AGG_SIZE
                }
            }
    else:
        return {}

    return agg_query_body


def format_aggregation_results(aggregation_results, category, category_filters):
    if category == '':
        category_obj = {
            'values': [],
            'key': 'category'
        }

        for bucket in aggregation_results['aggregations']['categories']['buckets']:
            category_obj['values'].append({
                'key': bucket['key'],
                'total': bucket['doc_count']
            })

        return [category_obj]
    elif category in category_filters.keys():
        formatted_agg = []

        for subcategory in category_filters[category]:
            agg_obj = {
                'key': subcategory[1],
                'values': []
            }
            if subcategory[1] in aggregation_results['aggregations']:
                for agg in aggregation_results['aggregations'][subcategory[1]]['buckets']:

                    agg_obj['values'].append({
                        'key': agg['key'],
                        'total': agg['doc_count']
                    })
            formatted_agg.append(agg_obj)

        return formatted_agg
    else:
        return []


def build_es_search_body_request(query, category, es_query, json_response_fields, search_fields, sort_by):
    es_search_body = {
        '_source': json_response_fields + ["keys"],
        'highlight': {
            'fields': {}
        },
        'query': {},
        'track_total_hits': True
    }
    if query == '' and category == '':
        es_search_body["query"] = {
            "function_score": {
                "query": es_query,
                "random_score": {"seed": 12345}
            }
        }
    else:
        es_search_body["query"] = es_query

    for field in search_fields:
        es_search_body['highlight']['fields'][field] = {}

    if sort_by == 'alphabetical':
        es_search_body['sort'] = [
            {
                "name.raw": {
                    "order": "asc"
                }
            }
        ]

    return es_search_body


def build_search_query(query, search_fields, category, category_filters, args, alias_flag=False, terms=[], ids=[], wildcard=None):
    
    es_query = build_search_params(
        query, search_fields, alias_flag, terms, ids, wildcard, category)
    if category == '':
        return es_query
    
    if es_query != {"match_all": {}}:
        query = es_query
        query['bool']['must'].append({
            'term': {
                'category': category
            }
        })
        
    else:
        query = {
            'bool': {
                'must': [{
                    'term': {
                        'category': category
                    }
                }]
                
            }
        }

    if category in category_filters.keys():
        for item in category_filters[category]:
            if args.get(item[1]):
                for param in args.get(item[1]):
                    query['bool']['must'].append({
                        'term': {
                            (item[1]): param
                        }
                    })

    return query

    
def build_search_params(query, search_fields, alias_flag=False, terms=[], ids=[], wildcard=None, category=None):
    ## terms = words in the search query
    ## search_fields = a list of search fields eg, "feature_type", "name_description", "summary",
    ##      "phenotypes", "cellular_component", etc
    ## alias_flag = if search query is an alias
    ## ids = one or more of these ['go', 'pmid', 'sgd', 'chebi', 'doid'] IDs
    ## category = locus, disease, or allele, etc
    es_query = None
    skip_fields = ["name", "locus_name", "aliases",
                   "chemical_name", "locus_summary", "keys"]
    if query == "":
        es_query = {"match_all": {}}
    else:
        es_query = {
            "bool": {
                "must":
                [
                    {
                        "bool": {
                            "should": []
                        }
                    }
                ],
                "should": [
                    {
                        "bool": {
                            "should": []
                        }
                    }
                ]
            }
        }

        ## remove single and double quotes from the search query
        if (query[0] in ('"', "'") and query[-1] in ('"', "'")):
            query = query[1:-1]
        ## if gene name follow by '-' remove the '-' eg, act1- => act1
        if query[-1] == '-' and query[3:-1].isdigit():
            query = query[0:-1]
        bool_must = es_query["bool"]["must"][0]["bool"]["should"]
        match_type = "multi_match"
        if wildcard is True:
            match_type = "query_string"
        if alias_flag:
            if terms:
                for item in terms:
                    bool_must.append({
                        match_type: {
                            "query": item,
                            "fields": [
                                "name",
                                "aliases.egram^5",
                                "aliases"
                            ]
                        }
                    })
            else:
                multi_field_match = {
                    match_type: {
                        "query": query,
                        "type": "phrase_prefix",
                        "fields": [
                            "name^9",
                            "locus_name^11",
                            "locus_name.engram^10",
                            "name.symbol^8",
                            "aliases.egram^7",
                            "aliases^6",
                            "phenotype_loci",
                            "gene_ontology_loci",
                            "keys"
                        ]
                    }
                }
                bool_must.append(multi_field_match)

        elif ids:
            for item in ids:
                bool_must.append({
                        match_type: {
                            "query": item,
                            "type": "phrase_prefix",
                                "fields": [
                                    "keys^10",
                                    "go_id",
                                    "biocyc_id",
                                    "do_id",
                                    "chebiid",
                                    "bioentity_id"
                                ]
                            }
                        })
            skip_fields.\
                extend(["keys", "biocyc_id", "go_id", "do_id", "chebiid", "bioentity_id"])

        elif terms:
            if category == 'locus':
                for item in terms:
                    bool_must.append({
                        match_type: {
                            "query": item,
                            "type": "phrase_prefix",
                            "fields": [
                                "locus_name.engram^10",
                                "name^8",
                                "aliases.egram^9",
                                "chemical_name",
                                "phenotypes.engram",
                                "cellular_component.engram",
                                "biological_process.engram",
                                "molecular_function.engram",
                                "description",
                                "name_description",
                                "phenotype_loci",
                                "gene_ontology_loci",
                                "keys",
                                "locus_summary"
                            ]

                        }
                    })
                skip_fields.\
                    extend(["locus_summary", "keys", "gene_ontology_loci",
                            "description", "molecular_function",
                            "biological_process", "cellular_component"])
            else:
                for item in terms:
                    bool_must.append({
                        match_type: {
                            "query": item,
                            "type": "phrase_prefix",
                            "fields": [
                                "locus_name.engram^10",
                                "name^9",
                                "aliases.egram^8",
                                "chemical_name",
                                "phenotypes.engram",
                                "cellular_component.engram",
                                "biological_process.engram",
                                "molecular_function.engram",
                                "description",
                                "name_description",
                                "phenotype_loci",
                                "gene_ontology_loci",
                                "keys",
                                "locus_summary"
                            ]

                        }
                    })
        ### single word search
        else:
            multi_name_field = {
                match_type: {
                    "query": query,
                    "type": "phrase_prefix",
                    "fields": [
                        "name^16",
                        "colleague_name.engram^6",
                        "author.white_space^4",
                        "name.symbol",
                        "raw_display_name",
                        "ref_citation",
                        "keys",
                        "description"
                    ]
                }
            }
            multi_locus_name_field = {
                match_type: {
                    "query": query,
                    "type": "phrase_prefix",
                    "fields": [
                        "locus_name",
                        "locus_name.engram^5",
                        "aliases.egram^7",
                        "aliases",
                        "chemical_name^15",
                        "locus_summary"
                    ]
                }
            }
            bool_must.append(multi_name_field)
            bool_must.append(multi_locus_name_field)
        if len(terms) == 0:
            if ids:
                for id in ids:
                    map_other_search_field(
                        id, es_query, search_fields, skip_fields)
            else:
                es_query = map_other_search_field(query, es_query, search_fields,
                                                  skip_fields, wildcard)

    return es_query

                                                                                                                                                                                                                                           
def map_other_search_field(query, es_query, search_fields, skip_fields, wildcard=None):
    if es_query:
        other_fields = es_query['bool']['must'][0]["bool"]["should"]
        keyword_fields = es_query["bool"]["must"][0]["bool"]["should"]

        for field in search_fields:
            if field not in skip_fields:
                if FIELD_MAP[field]['type'] == 'text':
                    temp_fields = FIELD_MAP[field].get('fields', None)
                    keyword_analyzer = FIELD_MAP[field].get('analyzer', None)

                    if temp_fields is not None:
                        most_fields = get_search_query_context(
                            field, 'text', temp_fields)
                        match_type = "multi_match"
                        if wildcard is True:
                            match_type = "query_string"
                        other_fields.append({
                            match_type: {
                                "query": query,
                                "type": "phrase_prefix",
                                "fields": most_fields
                            }
                        })
                    else:
                        if (keyword_analyzer == 'keyword'):
                            match_type = "match_bool_prefix"
                            query_type = "query"
                            if wildcard is True:
                                match_type = "wildcard"
                                query_type = "value"
                            keyword_fields.append({
                                match_type: {
                                    field: {
                                        query_type: query
                                    }
                                }
                            })
                        elif (field == "description"):
                            if wildcard is True:
                                keyword_fields.append({
                                    "wildcard": {
                                        field: {
                                            "value": query
                                        }
                                    }
                                })
                            else:
                                keyword_fields.append({
                                    "match": {
                                        field: {
                                            "query": query,
                                            "operator": "AND"
                                        }
                                    }
                                })
                        elif(field == "references"):
                            if wildcard is True:
                                keyword_fields.append({
                                    "wildcard": {
                                        field: {
                                            "value": query
                                        }
                                    }
                                })
                            else:
                                keyword_fields.append({
                                    "match": {
                                        field: {
                                            "query": query,
                                            "operator": "or"
                                        }
                                    }
                                })
                        else:
                            match_type = "match_phrase_prefix"
                            query_type = "query"
                            if wildcard is True:
                                match_type = "wildcard"
                                query_type = "value"
                            other_fields.append({
                                match_type: {
                                    field: {
                                        query_type: query
                                    }
                                }
                            })
                if FIELD_MAP[field]['type'] == 'keyword':
                    if field in ['last_name', 'first_name']:
                        match_type = "term"
                        if wildcard is True:
                            match_type = "wildcard"
                        if(isinstance(query, int)):
                            keyword_fields.append({
                                match_type: {
                                    field: {
                                        "value": query,
                                        "boost": 0.9
                                    }
                                }
                            })
                        else:
                            keyword_fields.append({
                                match_type: {
                                    field: {
                                        "value": query.capitalize(),
                                        "boost": 100
                                    }
                                }
                            })
                    elif field in ['feature_type']:
                        match_type = "match_bool_prefix"
                        query_type = "query"
                        if wildcard is True:
                            match_type = "wildcard"
                            query_type = "value"
                        keyword_fields.append({
                            match_type: {
                                field: {
                                    query_type: query,
                                    "boost": 10
                                }
                            }
                        })
                    elif field in ['resource_name']:
                        match_type = "match_bool_prefix"
                        query_type = "query"
                        if wildcard is True:
                            match_type = "wildcard"
                            query_type = "value"
                        keyword_fields.append({
                            match_type: {
                                field: {
                                    query_type: query,
                                    "boost": 400
                                }
                            }
                        })
                    elif field in ['molecular_function', 'biological_process', 'cellular_component']:
                        match_type = "match_phrase_prefix"
                        query_type = "query"
                        if wildcard is True:
                            match_type = "wildcard"
                            query_type = "value"
                        keyword_fields.append({
                            match_type: {
                                field + ".engram": {
                                    query_type: query,
                                    "boost": "5.0"
                                }
                            }
                        })
                    else:
                        match_type = "term"
                        if wildcard is True:
                            match_type = "wildcard"
                        keyword_fields.append({
                            match_type: {
                                field: {
                                    "value": query,
                                    "boost": 3.8
                                }
                            }
                        })
                            
        return es_query
    else:
        return {"match_all": {}}


def filter_highlighting(highlight):
    if highlight is None:
        return None

    for k in highlight.keys():
        if k.endswith(".symbol") and k.split(".")[0] in highlight:
            if highlight[k] == highlight[k.split(".")[0]]:
                highlight.pop(k, None)
            else:
                highlight[k.split(".")[0]] = highlight[k]
                highlight.pop(k, None)
    return highlight


def format_search_results(search_results, json_response_fields, query):
    formatted_results = []

    for r in search_results['hits']['hits']:
        raw_obj = r.get('_source')
        obj = {}
        for field in json_response_fields:
            obj[field] = raw_obj.get(field)

        obj['highlights'] = filter_highlighting(r.get('highlight'))
        obj['id'] = r.get('_id')

        if raw_obj.get('keys'):  # colleagues don't have keys
            item = raw_obj.get('aliases')

            if query.replace('"', '').lower().strip() in raw_obj.get('keys'):
                if obj["category"] == "locus":
                    if obj["is_quick_flag"]:
                        obj['is_quick'] = True
                    else:
                        obj['is_quick'] = False
                elif obj["category"] == "resource":
                    obj['is_quick'] = False
                else:
                    obj['is_quick'] = True

        formatted_results.append(obj)

    return formatted_results


def build_sequence_objects_search_query(query):
    if query == '':
        search_body = {
            'query': {'match_all': {}},
            'sort': {'absolute_genetic_start': {'order': 'asc'}}
        }
    elif ',' in query:
        search_body = {
            'query': {
                'bool': {
                    'filter': {
                        'terms': {
                            '_all': [q.strip() for q in query.split(',')]
                        }
                    }
                }
            }
        }
    else:
        query_type = 'wildcard' if '*' in query else 'match_phrase'
        search_body = {
            'query': {
                query_type: {
                    '_all': query
                }
            }
        }

    search_body['_source'] = ['sgdid', 'name', 'href', 'absolute_genetic_start',
                              'format_name', 'dna_scores', 'protein_scores', 'snp_seqs']

    return search_body


def get_search_query_context(name, type, fields=None):
    """ Create search multi-field query object
    Params
    ------
    name: str
    type: str
    fields: list

    Returns
    -------
    list

    Notes
    -----
    Some fields contain same text but are analyzed differently.
    Making other fields available for search will help boost search 
    relevance

    """

    if fields and name:
        temp = [name]
        for key, val in fields.items():
            if key not in ['autocomplete', 'raw']:
                temp.append(name + "." + key)
        return temp
    
    return []


def is_digit(term, int_flag=False):
    temp = ['go', 'pmid', 'sgd', 'chebi', 'doid']
    is_sgd_list = re.findall(r"([Ss]\d{9,10})", term)

    if term:
        num_list = []
        if int_flag:
            num_list = [int(num) for num in re.findall(r"\b\d+\b", term)]
        else:
            # re.compile("^[a-zA-Z]+$")
            if term.isdigit():
                num_list = re.findall(r"\b\d+\b", term)
            elif any(q_term in term.lower() for q_term in temp) or is_sgd_list:
                # TODO: extract number or 
                # num_list = re.findall(r"\b\d+\b", term)
                num_list = re.findall(r"([a-zA-Z]{2,7})[:|\s](\d{1,6})", term)
                num_list = [':'.join(mod_term) for mod_term in num_list]
                num_list = num_list + is_sgd_list

        if len(num_list) > 0:
            return num_list

    return []


# TODO: handle custom character group
def has_special_characters(term, char_group=None):
    flag = False
    if term:
        reg_expression = re.compile(r"(\s|\|)")
        digit_flag = re.compile(r"[a-zA-Z]{3,5}\d{1,3}")
        if reg_expression.search(term) and digit_flag.search(term):
            temp = re.split(" ", term)
            for elem in temp:
                if (digit_flag.search(elem)) is None:
                    flag = False
                    break
                else:
                    flag = True
            return flag
    else:
        return flag


def get_multiple_terms(term, char_group=None):
    if term:
        terms_container = re.split("(\s|\|)", term)
        if len(terms_container) > 0:
            terms_container = list(filter(str.strip, terms_container))
            return terms_container
    return []


def has_long_query(term):
    ''' split long query into terms '''
    terms = []
    if term:
        temp = term.split(" ")
        for elem in temp:
            if(elem.isdigit()):
                terms.append(elem)
            else:
                terms = []
                break
    return terms


def is_ncbi_term(term):
    ''' check if term is ncbi name '''
    flag = False
    if term:
        if re.findall(r"(^NP_\d{6,8})", term):
            flag = True

    return flag


def get_ncbi_search_item(term, source, highlight):
    if term:
        obj = {}
        _query = {
            "nested": {
                "path": "ncbi",
                "query": {
                        "bool": {
                            "must": [
                                {
                                    "match": {
                                        "ncbi.display_name": term.upper()
                                    }
                                }
                            ]
                        }
                }
            }
        }
        obj["search_body"] = {
            "_source": source,
            "highlight": highlight,
            "query": _query,
            "track_total_hits": True
        }
        obj["es_query"] = _query
     
        return obj

    return None
