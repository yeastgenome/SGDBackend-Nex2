from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPOk, HTTPNotFound
from pyramid.response import Response, FileResponse
from pyramid.view import view_config
from pyramid.compat import escape
from sqlalchemy import func, distinct, and_, or_
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from primer3 import bindings, designPrimers
from collections import defaultdict
from sqlalchemy.orm import joinedload
from urllib.request import Request, urlopen
from intermine.webservice import Service

import os
import re
import transaction
import traceback
import datetime
import logging
import json
from pathlib import Path

from .models import DBSession, ESearch, Colleague, Dbentity, Edam, Referencedbentity, ReferenceFile, Referenceauthor, FileKeyword, Keyword, Referencedocument, Chebi, ChebiUrl, PhenotypeannotationCond, Phenotypeannotation, Reservedname, Straindbentity, Literatureannotation, Phenotype, Apo, Go, Referencetriage, Referencedeleted, Locusdbentity, LocusAlias, Dataset, DatasetKeyword, Contig, Proteindomain, Ec, Dnasequenceannotation, Straindbentity, Disease, Complexdbentity, Filedbentity, Goslim, So, ApoRelation, GoRelation, Psimod,Posttranslationannotation, Alleledbentity, AlleleAlias, Pathwaydbentity, PathwayUrl
from .helpers import extract_id_request, link_references_to_file, link_keywords_to_file, FILE_EXTENSIONS, get_locus_by_id, get_go_by_id, get_disease_by_id, primer3_parser, count_alias
from .search_helpers import build_autocomplete_search_body_request, format_autocomplete_results, build_search_query, build_es_search_body_request, build_es_aggregation_body_request, format_search_results, format_aggregation_results, build_sequence_objects_search_query, is_digit, has_special_characters, get_multiple_terms, has_long_query, is_ncbi_term, get_ncbi_search_item
from .models_helpers import ModelsHelper
from .models import SGD_SOURCE_ID, TAXON_ID
from .variant_helpers import get_variant_data, get_all_variant_data

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
log = logging.getLogger()

ES_INDEX_NAME = os.environ.get('ES_INDEX_NAME', 'searchable_items_aws')
ES_VARIANT_INDEX_NAME = os.environ.get('ES_VARIANT_INDEX_NAME', 'variant_data_index')


models_helper = ModelsHelper()

@view_config(route_name='home', request_method='GET', renderer='home.jinja2')
def home_view(request):
    return {
        'google_client_id': os.environ['GOOGLE_CLIENT_ID'],
        'pusher_key': os.environ['PUSHER_KEY']
    }
@view_config(route_name='autocomplete_results', renderer='json', request_method='GET')
def search_autocomplete(request):
    query = request.params.get('q', '')
    category = request.params.get('category', '')
    field = request.params.get('field', 'name')

    if query == '':
        return {
            "results": None
        }

    autocomplete_results = ESearch.search(
        index=ES_INDEX_NAME,
        body=build_autocomplete_search_body_request(query, category, field)
    )

    return {
        "results": format_autocomplete_results(autocomplete_results, field)
    }

@view_config(route_name='search', renderer='json', request_method='GET')
def search(request):
    # initialize parameters
    search_terms = []
    flag = False
    name_flag = False
    sys_flag = False
    alias_flag = False
    terms = []
    ids = []
    wildcard = None
    terms_digits_flag = False

    # get query string
    query = request.params.get('q', '').strip()
    query = query.upper()
    
    if query.endswith('\\'):
        query = query.replace('\\', '')
    elif "\\" in query:
        query = query.replace('\\', ' ')
        
    temp_container = query.split(' ')
    int_flag = False
    if(temp_container):
        for elem in temp_container:
            if elem.isdigit():
                int_flag = True
            else:
                int_flag = False
                break

    digit_container = is_digit(query, int_flag)

    ncbi_term = is_ncbi_term(query.upper())
    if digit_container:
        ids = digit_container

    is_quick_flag = request.params.get('is_quick', False)
    has_spec_chars = has_special_characters(query)
    term_container = []
    if has_spec_chars:
        terms = get_multiple_terms(query)
    else:
        if(len(query) > 50):
            term_container = has_long_query(query)
            if(term_container):
                terms = term_container
    if terms or ids:
        terms_digits_flag = True
    if len(terms) > 100:
        terms = terms[:50]
        # subcategory filters. Map: (request GET param name from frontend, ElasticSearch field name)
    category_filters = {
        "locus": [('feature type', 'feature_type'), ('molecular function',
                                                     'molecular_function'),
                  ('phenotype', 'phenotypes'), ('cellular component',
                                                'cellular_component'),
                  ('biological process', 'biological_process'), ('status',
                                                                 'status')],
        "phenotype": [("observable", "observable"), ("qualifier", "qualifier"),
                      ("references", "references"), ("phenotype_locus",
                                                     "phenotype_loci"),
                      ("chemical", "chemical"), ("mutant_type", "mutant_type")],

        "biological_process": [("go_locus", "gene_ontology_loci")],
        "cellular_component": [("go_locus", "gene_ontology_loci")],
        "molecular_function": [("go_locus", "gene_ontology_loci")],

        "disease": [("disease_locus", "disease_loci")],
        "reference": [("author", "author"), ("journal", "journal"),
                      ("year", "year"), ("reference_locus", "reference_loci"),
                      ("associated_alleles", "associated_alleles"),
                      ("associated_complexes", "associated_complexes"),
                      ("associated_pathways", "associated_pathways"),
                      ("associated_strains", "associated_strains")],
        "contig": [("strain", "strain")],
        "allele": [("references", "references"),
                   ("allele_types", "allele_types"),
                   ("allele_loci", "allele_loci"),
                   ("phenotypes", "phenotypes")],
        "strain": [("references", "references"),
                   ("diseases", "diseases"),
                   ("phenotypes", "phenotypes")],
        "pathway": [("references", "references"),
                    ("pathway_loci", "pathway_loci")],
        "complex": [("references", "references"),
                    ("complex_loci", "complex_loci"),
                    ('molecular function', 'molecular_function'),
                    ('cellular component','cellular_component'),
                    ('biological process', 'biological_process')],
        "colleague": [("last_name", "last_name"), ("position", "position"),
                      ("institution", "institution"), ("country", "country"),
                      ("keywords", "keywords"), ("colleague_loci",
                                                 "colleague_loci")],
        "download": [("topic", "topic"), ("data", "data"), ("keyword", "keyword"), ("format", "format"),
                     ("status", "status"), ("year", "year")]
    }

    search_fields = [
        "name",
        "description",
        "first_name",
        "last_name",
        "institution",
        "colleague_loci",
        "feature_type",
        "name_description",
        "summary",
        "phenotypes",
        "cellular_component",
        "biological_process",
        "molecular_function",
        "ec_number",
        "protein",
        "tc_number",
        "secondary_sgdid",
        "sequence_history",
        "gene_history",
        "observable",
        "qualifier",
        "references",
        "phenotype_loci",
        "chemical",
        "mutant_type",
        "synonyms",
        "go_id",
        "gene_ontology_loci",
        "allele_loci",
        "pathway_loci",
        "biocyc_id",
        "author",
        "journal",
        "reference_loci",
        "associated_alleles",
        "associated_complexes",
        "associated_pathways",
        "associated_strains",
        "aliases",
        "data",
        "topic",
        "format",
        "status",
        "keyword",
        "file_size",
        "year",
        "readme_url",
        "chebiid",
        "colleague_name",
        "raw_display_name",
        "ref_citation",
        "chemical_name",
        "resource_name",
        "locus_summary"
    ]  # year not inserted, have to change to str in mapping

    json_response_fields = [
        'name', 'href', 'description', 'category', 'bioentity_id',
        'phenotype_loci', 'gene_ontology_loci', 'reference_loci',
        'associated_alleles', 'associated_complexes', 'associated_pathways',
        'aliases', 'year', 'keyword', 'format', 'status', 'file_size',
        'readme_url', 'topic', 'data', 'is_quick_flag'
    ]


    
        
    # see if we can search for a simple gene name in db without using ES

    aliases_count = 0
    if is_quick_flag == 'true' and query != '' and terms_digits_flag == False:
        t_query = query.strip().upper()
        sys_pattern = re.compile(r'(?i)^y.{2,}')
        is_sys_name_match = sys_pattern.match(t_query)
        
        ## adding code to check if it is an unmapped gene
        is_unmapped = 0
        unmapped_url = "https://downloads.yeastgenome.org/curation/literature/genetic_loci.tab"
        response = urlopen(unmapped_url)
        unmapped_data = response.read().decode('utf-8').split("\n")
        for line in unmapped_data:
            if line == '' or line.startswith('#') or line.startswith('FEATURE_NAME'):
                continue
            pieces = line.split('\t')
            if pieces[0] == t_query:
                is_unmapped = 1
                break
        if is_unmapped == 1:
            unmapped_search_obj = {
                'href': '/search?q=' + query + '&category=locus',
                'is_quick': True
            }
            return {
                'total': 1,
                'results': [unmapped_search_obj],
                'aggregations': []
            }
        
        ## end of unmapped gene check
        
        if Locusdbentity.is_valid_gene_name(t_query) or is_sys_name_match or t_query.startswith('MATA'):
            maybe_gene_url = DBSession.query(Locusdbentity.obj_url).filter(or_(Locusdbentity.gene_name == t_query, Locusdbentity.systematic_name == t_query)).scalar()
            aliases_count = DBSession.query(LocusAlias).filter(and_(LocusAlias.alias_type.in_(['Uniform', 'Non-uniform']),LocusAlias.display_name == t_query)).count()
            if aliases_count == 0 and maybe_gene_url:
                fake_search_obj = {
                    'href': maybe_gene_url,
                    'is_quick': True
                }
                return {
                    'total': 1,
                    'results': [fake_search_obj],
                    'aggregations': []
                }            
            elif aliases_count > 0:
                alias_flag = True
    elif (Locusdbentity.is_valid_gene_name(query.strip().upper()) and terms_digits_flag == False):
        aliases_count = DBSession.query(LocusAlias).filter(and_(LocusAlias.alias_type.in_(
            ['Uniform', 'Non-uniform']), LocusAlias.display_name == query.strip().upper())).count()
        if aliases_count > 0:
            alias_flag = True
    elif (terms_digits_flag):
        # check for alias
        terms = [elem.upper() for elem in terms]
        count = count_alias(terms)
        if (count > 0):
            alias_flag = True



    ## added for allele search
    # query2 = query.replace('Δ', "delta").replace('-', "delta")
    # if is_quick_flag == 'true' and ('delta' in query2):
    if "*" in query or "?" in query:
        wildcard = True

    if is_quick_flag:
        allele_name = query.strip()
        maybe_allele_url = None
        maybe_allele = DBSession.query(Dbentity).filter_by(subclass='ALLELE').filter(Dbentity.display_name.ilike(query)).one_or_none()
        if maybe_allele:
            maybe_allele_url = maybe_allele.obj_url

        if maybe_allele_url is None:
            aa = DBSession.query(AlleleAlias).filter(AlleleAlias.display_name.ilike(allele_name)).one_or_none()
            if aa is not None:
                maybe_allele_url = aa.allele.obj_url
        if maybe_allele_url:
            allele_search_obj = {
                'href': maybe_allele_url,
                'is_quick': True
            }
            return {
                'total': 1,
                'results': [allele_search_obj],
                'aggregations': []
            }

    ## end of allele search section

    ## check if it is a biocyc_id
    pathway_kws = ['PWY', 'YEAST', 'BIOSYNTHESIS', 'DEGRADATION', 'BYPASS', 'GLUCOSE-MANNOSYL', 'GLYCOLYSIS', 'HOMOCYS']
    maybe_biocyc_id = None
    for keyword in pathway_kws:
        if keyword in query.upper():
            maybe_biocyc_id = query.strip()
            break
    if is_quick_flag and maybe_biocyc_id and not query.endswith('*') and not query.endswith('?'):
        query = query + "*"
    ## end of pathway search section       
            
    limit = int(request.params.get('limit', 10))
    offset = int(request.params.get('offset', 0))
    category = request.params.get('category', '')
    sort_by = request.params.get('sort_by', '')

    args = {}

    search_body = None
    es_query = None
    for key in list(request.params.keys()):
        args[key] = request.params.getall(key)

    if ncbi_term:
        _source = [
            "is_quick_flag", "category", "keys", "name", "href", "ncbi",
            "summary", "description"
            ]
        highlight = {
            "fields": {
                "name": {}, 
                "is_quick_flag": {},
                "href": {},
                "ncbi": {},
                "category": {},
                "summary": {},
                "description": {}
            }
        }
        search_obj = get_ncbi_search_item(query, _source, highlight)
        if search_obj:
            try:
                es_query = search_obj["es_query"]
                search_body = search_obj["search_body"]
                search_results = ESearch.search(
                    index=ES_INDEX_NAME,
                    body=search_body,
                    size=limit,
                    from_=offset,
                    preference='p_'+query
                )

                arr = search_results["hits"]["hits"]
                if len(arr) == 1:
                    temp = arr[0]
                    if temp["_source"]["is_quick_flag"]:
                        href = temp["_source"]["ncbi"][0]["url"]
                        result = {
                            "total": 1,
                            "results": [
                                {
                                    "is_quick": True,
                                    "href": href
                                }
                            ],
                            "aggregations": []
                        }
                        return result
            except Exception as e:
                logging.error(e.message)
                return {
                    "total": 0,
                    "results": [],
                    "aggregations": []
                }

    else:
        if "*" in query or "?" in query:
            if query[0] == '*' and query[-1] not in ['*', '?']:
                query = query + "*"
            wildcard = True

        es_query = build_search_query(query, search_fields, category,
                                    category_filters, args, alias_flag,
                                    terms, ids, wildcard)
        search_body = build_es_search_body_request(query,
                                                category,
                                                es_query,
                                                json_response_fields,
                                                search_fields,
                                                sort_by)
    valid_query = ESearch.indices.validate_query(
        index=ES_INDEX_NAME,
        body=search_body,
    )
    if valid_query == False:
        return []
    else:
        search_results = ESearch.search(
            index=ES_INDEX_NAME,
            body=search_body,
            size=limit,
            from_=offset,
            preference='p_'+query
        )

        if search_results['hits']['total'] == 0:
            return {
                'total': 0,
                'results': [],
                'aggregations': []
            }

        aggregation_body = build_es_aggregation_body_request(
            es_query,
            category,
            category_filters
        )
        
        aggregation_results = ESearch.search(
            index=ES_INDEX_NAME,
            body=aggregation_body,
            preference='p_'+query
        )

        return {
            'total': search_results['hits']['total'],
            'results': format_search_results(search_results, json_response_fields, query),
            'aggregations': format_aggregation_results(
                aggregation_results,
                category,
                category_filters
            )
        }

@view_config(route_name='genomesnapshot', renderer='json', request_method='GET')
def genomesnapshot(request):
    try:
        GENOMIC = 'GENOMIC'
        genome_snapshot = dict()
        phenotype_slim_data = DBSession.query(Apo).filter(and_(Apo.source_id==SGD_SOURCE_ID, Apo.apo_namespace=='observable', Apo.is_in_slim==True)).all()
        phenotype_slim_terms = [phenotype_slim.to_snapshot_dict() for phenotype_slim in phenotype_slim_data]
        genome_snapshot['phenotype_slim_terms'] = phenotype_slim_terms
        phenotype_slim_relationships = list()
        phenotype_slim_relationships.append(["Child", "Parent"])
        for phenotype in phenotype_slim_terms:
            parent = DBSession.query(ApoRelation).filter(ApoRelation.child_id==phenotype['id']).one_or_none()
            phenotype_slim_relationships.append([phenotype['id'], parent.parent_id])
        genome_snapshot['phenotype_slim_relationships'] = phenotype_slim_relationships
        go_slim_data = DBSession.query(Goslim).filter_by(slim_name='Yeast GO-Slim').all()
        go_slim_terms = [go_slim.to_snapshot_dict() for go_slim in go_slim_data]
        genome_snapshot['go_slim_terms'] = go_slim_terms
        go_slim_relationships = list()
        go_slim_relationships.append(["Child", "Parent"])
        for go_slim in go_slim_terms:
            if go_slim['is_root'] is False:
                go_namespace = DBSession.query(Go.go_namespace).filter(Go.go_id==go_slim['id']).scalar()
                parent = DBSession.query(Go).filter(Go.display_name==go_namespace.replace('_', ' ')).one_or_none()
                go_slim_relationships.append([go_slim['id'], parent.go_id])
        genome_snapshot['go_slim_relationships'] = go_slim_relationships
        so = DBSession.query(So).filter_by(display_name = 'primary transcript').one_or_none()
        distinct_so_ids = []
        for x in DBSession.query(Dnasequenceannotation).filter_by(taxonomy_id=TAXON_ID).filter(Dnasequenceannotation.so_id != so.so_id).all():
            if x.so_id not in distinct_so_ids:
                distinct_so_ids.append(x.so_id)
        # rows = DBSession.query(So.so_id, So.display_name).filter(So.so_id.in_(distinct_so_ids)).all()
        rows = DBSession.query(So).filter(So.so_id.in_(distinct_so_ids)).all()
        contigs = DBSession.query(Contig).filter(or_(Contig.display_name.like("%micron%"), Contig.display_name.like("Chromosome%"))).order_by(Contig.contig_id).all()
        columns = [contig.to_dict_sequence_widget() for contig in contigs]
        genome_snapshot['columns'] = columns
        data = list()
        active_db_entity_ids = DBSession.query(Dbentity.dbentity_id).filter(Dbentity.dbentity_status=='Active')
        for row in rows:
            row_data = list()
            # Insert display_name of each row as first item in each 'data' list item.
            # Data needs to be sorted in descending order of number of features
            row_data.append(row.display_name)
            for column in columns:
                count = DBSession.query(Dnasequenceannotation).filter(and_(Dnasequenceannotation.so_id==row.so_id, Dnasequenceannotation.contig_id==column['id'], Dnasequenceannotation.dna_type==GENOMIC, Dnasequenceannotation.dbentity_id.in_(active_db_entity_ids))).count()
                row_data.append(count)
            data.append(row_data)
        # sort the list of lists 'data' in descending order based on sum of values in each list except first item(display_name)
        data = sorted(data, key=lambda item: sum(item[1:]), reverse=True)
        data_row = list()
        for item in data:
            # Pop the display name of each row and add it to row data
            data_row.append(item.pop(0))
        # sub-categories for 'ORF' data row
        sub_categories = ['Verified', 'Dubious', 'Uncharacterized']
        data_row.extend(sub_categories)
        orf_so = DBSession.query(So).filter_by(display_name='ORF').one_or_none()
        orf_so_id = orf_so.so_id
        for category in sub_categories:
            row_data = list()
            for column in columns:
                db_entity_ids = []
                for x in DBSession.query(Dnasequenceannotation).filter(and_(Dnasequenceannotation.so_id==orf_so_id, Dnasequenceannotation.dna_type==GENOMIC, Dnasequenceannotation.contig_id==column['id'])):
                    db_entity_ids.append(x.dbentity_id)
                count = DBSession.query(Locusdbentity).filter(and_(Locusdbentity.dbentity_id.in_(db_entity_ids), Locusdbentity.qualifier==category)).count()
                row_data.append(count)
            data.append(row_data)
        genome_snapshot['data'] = data
        genome_snapshot['rows'] = data_row
        return genome_snapshot
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='formats', renderer='json', request_method='GET')
def formats(request):
    try:
        formats_db = DBSession.query(Edam).filter(Edam.edam_namespace == 'format').all()
        return {'options': [f.to_dict() for f in formats_db]}
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='topics', renderer='json', request_method='GET')
def topics(request):
    try:
        topics_db = DBSession.query(Edam).filter(Edam.edam_namespace == 'topic').all()
        return {'options': [t.to_dict() for t in topics_db]}
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='extensions', renderer='json', request_method='GET')
def extensions(request):
    try:
        return {'options': [{'id': e, 'name': e} for e in FILE_EXTENSIONS]}
    except Exception as e:
        log.error(e)

@view_config(route_name='reference_this_week', renderer='json', request_method='GET')
def reference_this_week(request):
    try:
        start_date = datetime.datetime.today() - datetime.timedelta(days=30)
        end_date = datetime.datetime.today()
        recent_literature = DBSession.query(Referencedbentity).filter(Referencedbentity.date_created >= start_date).order_by(Referencedbentity.date_created.desc()).all()
        # refs = [x.to_dict_citation() for x in recent_literature]
        refs = []
        for x in recent_literature:
            citation_dict = x.to_dict_citation()
            citation_dict['entity_list'] = x.annotations_to_dict()
            refs.append(citation_dict)
        return {
            'start': start_date.strftime("%Y-%m-%d"),
            'end': end_date.strftime("%Y-%m-%d"),
            'references': refs
        }
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='reference_list', renderer='json', request_method='POST')
def reference_list(request):
    reference_ids = request.POST.get('reference_ids', request.json_body.get('reference_ids', None))

    if reference_ids is None or len(reference_ids) == 0:
        return HTTPBadRequest(body=json.dumps({'error': "No reference_ids sent. JSON object expected: {\"reference_ids\": [\"id_1\", \"id_2\", ...]}"}))
    else:
        try:
            reference_ids = [int(r) for r in reference_ids]
            references = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(reference_ids)).all()

            if len(references) == 0:
                return HTTPNotFound(body=json.dumps({'error': "Reference_ids do not exist."}))

            return [r.to_bibentry() for r in references]
        except ValueError:
            return HTTPBadRequest(body=json.dumps({'error': "IDs must be string format of integers. Example JSON object expected: {\"reference_ids\": [\"1\", \"2\"]}"}))
        except Exception as e:
            log.error(e)
        finally:
            if DBSession:
                DBSession.remove()

@view_config(route_name='get_all_variant_objects', request_method='GET')
def get_all_variant_objects(request):
    query = request.params.get('query', '')
    offset = request.params.get('offset', 0)
    limit = request.params.get('limit', 7000)
    try:
        data = get_all_variant_data(request, query, offset, limit)
        return HTTPOk(body=json.dumps(data), content_type="text/json")
    except Exception as e:
        logging.exception(str(e))
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type="text/json")
        
@view_config(route_name='search_sequence_objects', request_method='GET')
def search_sequence_objects(request):
    query = request.params.get('query', '').upper()
    offset = request.params.get('offset', 0)
    limit = request.params.get('limit', 1000)

    if query != '':
        try:
            data = get_all_variant_data(request, query, offset, limit)
            return HTTPOk(body=json.dumps(data), content_type="text/json")
        except Exception as e:
            logging.exception(str(e))
            return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type="text/json")

    try:
        search_result = ESearch.search(
            index=ES_VARIANT_INDEX_NAME,
            body=build_sequence_objects_search_query(''),
            size=limit,
            from_=offset
        )
        
        simple_hits = []
        for hit in search_result['hits']['hits']:
            simple_hits.append(hit['_source'])
        
        formatted_response = {
            'loci': simple_hits,
            'total': limit,
            'offset': offset
        }
        
        return Response(body=json.dumps(formatted_response), content_type='application/json', charset='UTF-8')
    
    except Exception as e:
        logging.exception(str(e))
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type="text/json")
    
@view_config(route_name='get_sequence_object', renderer='json', request_method='GET')
def get_sequence_object(request):

    try:
        data = get_variant_data(request)
        return HTTPOk(body=json.dumps(data), content_type="text/json")
    except Exception as e:
        logging.exception(str(e))
        return HTTPBadRequest(body=json.dumps({'error': str(e)}), content_type="text/json")
    
@view_config(route_name='reserved_name', renderer='json', request_method='GET')
def reserved_name(request):
    try:
        id = extract_id_request(request, 'reservedname', 'id', True)
        if id:
            reserved_name = DBSession.query(Reservedname).filter_by(reservedname_id=id).one_or_none()
        else:
            reserved_name = DBSession.query(Reservedname).filter_by(display_name=request.matchdict['id']).one_or_none()
        if reserved_name:
            return reserved_name.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='strain', renderer='json', request_method='GET')
def strain(request):
    try:
        id = extract_id_request(request, 'strain')
        strain = DBSession.query(Straindbentity).filter_by(dbentity_id=id).one_or_none()
            
        if strain:
            return strain.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='reference', renderer='json', request_method='GET')
def reference(request):
    try:
        id = extract_id_request(request, 'reference', 'id', True)
        # allow reference to be accessed by sgdid even if not in disambig table
        if id:
            reference = DBSession.query(Referencedbentity).filter_by(dbentity_id=id).one_or_none()
        else:
            reference = DBSession.query(Referencedbentity).filter_by(sgdid=request.matchdict['id']).one_or_none()

        if reference:
            return reference.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='reference_literature_details', renderer='json', request_method='GET')
def reference_literature_details(request):
    try:
        id = extract_id_request(request, 'reference', 'id', True)
        # allow reference to be accessed by sgdid even if not in disambig table
        if id:
            reference = DBSession.query(Referencedbentity).filter_by(dbentity_id=id).one_or_none()
        else:
            reference = DBSession.query(Referencedbentity).filter_by(sgdid=request.matchdict['id']).one_or_none()

        if reference:
            return reference.annotations_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='reference_interaction_details', renderer='json', request_method='GET')
def reference_interaction_details(request):
    try:
        id = extract_id_request(request, 'reference')
        reference = DBSession.query(Referencedbentity).filter_by(dbentity_id=id).one_or_none()

        if reference:
            return reference.interactions_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='reference_go_details', renderer='json', request_method='GET')
def reference_go_details(request):
    try:
        id = extract_id_request(request, 'reference')
        reference = DBSession.query(Referencedbentity).filter_by(dbentity_id=id).one_or_none()

        if reference:
            return reference.go_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='reference_functional_complement_details', renderer='json', request_method='GET')
def reference_functional_complement_details(request):
    try:
        id = extract_id_request(request, 'reference')
        reference = DBSession.query(Referencedbentity).filter_by(dbentity_id=id).one_or_none()

        if reference:
            return reference.functional_complement_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

            
@view_config(route_name='reference_phenotype_details', renderer='json', request_method='GET')
def reference_phenotype_details(request):
    try:
        id = extract_id_request(request, 'reference')
        reference = DBSession.query(Referencedbentity).filter_by(dbentity_id=id).one_or_none()

        if reference:
            return reference.phenotype_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()


@view_config(route_name='sgd_blast_metadata', renderer='json', request_method='GET')
def sgd_blast_metadata(request):

    from datetime import datetime
    datestamp = str(datetime.now()).split(" ")[0]

    taxon_id = "NCBITaxon:4932"
    
    try:
        data = []
        for x in DBSession.query(Filedbentity).filter(Filedbentity.description.like('BLAST: %')).order_by(Filedbentity.dbentity_id).all():
            seqtype = 'nucl'
            if 'pep' in x.previous_file_name:
                seqtype = 'prot'
            desc = x.description.replace('BLAST: ', '').split(' | ')
            description = desc[0]
            version = ''
            if len(desc) > 1:
                version = desc[1]
            data.append({'URI': x.s3_url,
                         'md5sum': x.md5sum, 
                         'description': description,
                         'genus': 'Saccharomyces',
                         'species': 'cerevisiae',
                         'version': version,
                         'blast_title': description,
                         'seqtype': seqtype,
                         'taxon_id': taxon_id 
                       })
        obj = { 'data': data,
                'metaData': {
                    'contact': 'sweng@stanford.edu',
                    'dataProvider': 'SGD',
                    'dateProduced': datestamp,
                    'release': "SGD:" + datestamp 
                }
        }
        return obj
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
            
@view_config(route_name='reference_disease_details', renderer='json', request_method='GET')
def reference_disease_details(request):
    try:
        id = extract_id_request(request, 'reference')
        reference = DBSession.query(Referencedbentity).filter_by(dbentity_id=id).one_or_none()

        if reference:
            return reference.disease_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='reference_regulation_details', renderer='json', request_method='GET')
def reference_regulation_details(request):
    try:
        id = extract_id_request(request, 'reference')
        reference = DBSession.query(Referencedbentity).filter_by(dbentity_id=id).one_or_none()

        if reference:
            return reference.regulation_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='author', renderer='json', request_method='GET')
def author(request):
    try:
        format_name = extract_id_request(request, 'author', param_name="format_name")

        key = "/author/" + format_name.decode("utf-8")
    
        authors_ref = DBSession.query(Referenceauthor).filter_by(obj_url=key).all()

        references_dict = sorted([author_ref.reference.to_dict_reference_related() for author_ref in authors_ref], key=lambda r: r["display_name"])

        if len(authors_ref) > 0:
            return {
                "display_name": authors_ref[0].display_name,
                "references": sorted(references_dict, key=lambda r: r["year"], reverse=True)
            }
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='chemical', renderer='json', request_method='GET')
def chemical(request):
    try:
        #chebiID = request.matchdict['id']
        #chebi = None
        #if chebiID.startswith('CHEBI:'):
        #    chebi = DBSession.query(Chebi).filter_by(format_name=chebiID).one_or_none()
        #else:

        id = extract_id_request(request, 'chebi', param_name="format_name")
        chebi = DBSession.query(Chebi).filter_by(chebi_id=id).one_or_none()
        if chebi:
            return chebi.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='chemical_phenotype_details', renderer='json', request_method='GET')
def chemical_phenotype_details(request):
    try:
        id = extract_id_request(request, 'chebi')

        chebi = DBSession.query(Chebi).filter_by(chebi_id=id).one_or_none()
        if chebi:
            return chebi.phenotype_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='chemical_go_details', renderer='json', request_method='GET')
def chemical_go_details(request):
    try:
        id = extract_id_request(request, 'chebi')

        chebi = DBSession.query(Chebi).filter_by(chebi_id=id).one_or_none()
        if chebi:
            return chebi.go_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='chemical_proteinabundance_details', renderer='json', request_method='GET')
def chemical_proteinabundance_details(request):
    try:
        id = extract_id_request(request, 'chebi')
        chebi = DBSession.query(Chebi).filter_by(chebi_id=id).one_or_none()
        if chebi:
            return chebi.proteinabundance_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='chemical_complex_details', renderer='json', request_method='GET')
def chemical_complex_details(request):
    try:
        id = extract_id_request(request, 'chebi')

        chebi = DBSession.query(Chebi).filter_by(chebi_id=id).one_or_none()
        if chebi:
            return chebi.complex_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='chemical_network_graph', renderer='json', request_method='GET')
def chemical_network_graph(request):
    try:
        id = extract_id_request(request, 'chebi')

        chebi = DBSession.query(Chebi).filter_by(chebi_id=id).one_or_none()
        if chebi:
            return chebi.chemical_network()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='phenotype', renderer='json', request_method='GET')
def phenotype(request):
    try:
        id = extract_id_request(request, 'phenotype', param_name="format_name")
        phenotype = DBSession.query(Phenotype).filter_by(phenotype_id=id).one_or_none()
        if phenotype:
            return phenotype.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='phenotype_locus_details', renderer='json', request_method='GET')
def phenotype_locus_details(request):
    try:
        id = extract_id_request(request, 'phenotype')
        phenotype = DBSession.query(Phenotype).filter_by(phenotype_id=id).one_or_none()
        if phenotype:
            return phenotype.annotations_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='observable', renderer='json', request_method='GET')
def observable(request):
    try:
        if request.matchdict['format_name'].upper() == "YPO": # /ontology/phenotype/ypo -> root of APOs
            return Apo.root_to_dict()

        id = extract_id_request(request, 'apo', param_name="format_name")
        observable = DBSession.query(Apo).filter_by(apo_id=id).one_or_none()
        if observable:
            return observable.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='observable_locus_details', renderer='json', request_method='GET')
def observable_locus_details(request):
    try:
        id = extract_id_request(request, 'apo')
        observable = DBSession.query(Apo).filter_by(apo_id=id).one_or_none()
        if observable:
            return observable.annotations_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='observable_ontology_graph', renderer='json', request_method='GET')
def observable_ontology_graph(request):
    try:
        id = extract_id_request(request, 'apo')
        observable = DBSession.query(Apo).filter_by(apo_id=id).one_or_none()
        if observable:
            return observable.ontology_graph()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='observable_locus_details_all', renderer='json', request_method='GET')
def observable_locus_details_all(request):
    try:
        id = extract_id_request(request, 'apo')
        observable = DBSession.query(Apo).filter_by(apo_id=id).one_or_none()
        if observable:
            return observable.annotations_and_children_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='go', renderer='json', request_method='GET')
def go(request):
    try:
        id = extract_id_request(request, 'go', param_name="format_name")
        go = get_go_by_id(id)
        if go:
            return go.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='go_ontology_graph', renderer='json', request_method='GET')
def go_ontology_graph(request):
    try:
        id = extract_id_request(request, 'go')
        go = get_go_by_id(id)
        if go:
            return go.ontology_graph()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='go_locus_details', renderer='json', request_method='GET')
def go_locus_details(request):
    try:
        id = extract_id_request(request, 'go')
        go = get_go_by_id(id)
        if go:
            return go.annotations_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='go_locus_details_all', renderer='json', request_method='GET')
def go_locus_details_all(request):
    try:
        id = extract_id_request(request, 'go')
        go = get_go_by_id(id)
        if go:
            return go.annotations_and_children_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='disease', renderer='json', request_method='GET')
def disease(request):
    try:
        disease_id = request.matchdict['id'].upper()
        disease = DBSession.query(Disease).filter_by(doid=disease_id).one_or_none()
        if disease:
            return disease.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='disease_ontology_graph', renderer='json', request_method='GET')
def disease_ontology_graph(request):
    try:
        disease_id = request.matchdict['id'].upper()
        disease = DBSession.query(Disease).filter_by(disease_id=disease_id).one_or_none()
        if disease:
            return disease.ontology_graph()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='disease_locus_details', renderer='json', request_method='GET')
def disease_locus_details(request):
    try:
        disease_id = request.matchdict['id'].upper()
        disease = DBSession.query(Disease).filter_by(disease_id=disease_id).one_or_none()
        if disease:
            return disease.annotations_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='disease_locus_details_all', renderer='json', request_method='GET')
def disease_locus_details_all(request):
    try:
        disease_id = request.matchdict['id'].upper()
        disease = DBSession.query(Disease).filter_by(disease_id=disease_id).one_or_none()
        if disease:
            return disease.annotations_and_children_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus', renderer='json', request_method='GET')
def locus(request):
    id = extract_id_request(request, 'locus', param_name="sgdid")
    try:
        locus = get_locus_by_id(id)
        if locus:
            return locus.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
        
@view_config(route_name='locus_tabs', renderer='json', request_method='GET')
def locus_tabs(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.tabs()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='locus_phenotype_details', renderer='json', request_method='GET')
def locus_phenotype_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.phenotype_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_phenotype_graph', renderer='json', request_method='GET')
def locus_phenotype_graph(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.phenotype_graph()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='locus_go_graph', renderer='json', request_method='GET')
def locus_go_graph(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.go_graph()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='locus_disease_graph', renderer='json', request_method='GET')
def locus_disease_graph(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.disease_graph()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_expression_graph', renderer='json', request_method='GET')
def locus_expression_graph(request):
    try:
        return {
            'nodes': [],
            'edges': []
        }
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.expression_graph()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

            	
@view_config(route_name='locus_complement_details', renderer='json', request_method='GET')
def locus_complement_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.complements_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()


@view_config(route_name='locus_homolog_details', renderer='json', request_method='GET')
def locus_homolog_details(request):
    try:
        sgdid = request.matchdict['id']
        allianceAPI = "https://www.alliancegenome.org/api/gene/SGD:" + sgdid + "/homologs?limit=10000"
        req = Request(allianceAPI)
        res = urlopen(req)
        records = json.loads(res.read().decode('utf-8'))
        data = []
        for record in records['results']:
            homolog = record['homologGene']
            data.append(homolog)
        dataSortBySpecies = sorted(data, key=lambda d: d['species']['name'])
        return HTTPOk(body=json.dumps(dataSortBySpecies), content_type="text/json")
    except Exception as e:
        log.error(e)
    
@view_config(route_name='locus_fungal_homolog_details', renderer='json', request_method='GET')
def locus_fungal_homolog_details(request):
    try:
        ## gene name can be gene name, orf name, sgdid
        gene_name = request.matchdict['id']
        service = Service("https://yeastmine.yeastgenome.org/yeastmine/service")
        query = service.new_query("Gene")
        query.add_view(
            "secondaryIdentifier",
            "homologues.homologue.organism.shortName",
            "homologues.homologue.primaryIdentifier",
            "homologues.homologue.symbol",
            "homologues.dataSets.dataSource.name",
            "homologues.homologue.briefDescription"
        )
        query.add_sort_order("Gene.homologues.homologue.organism.shortName", "ASC")
        query.add_constraint("homologues.homologue.organism.shortName", "ONE OF", ["A. flavus NRRL3357", "A. fumigatus Af293", "A. nidulans FGSC A4", "A. niger ATCC 1015", "C. albicans SC5314", "C. albicans WO-1", "C. dubliniensis CD36", "C. gattii R265", "C. gattii WM276", "C. glabrata CBS 138", "C. immitis H538.4", "C. immitis RS", "C. neoformans var. grubii H99", "C. neoformans var. neoformans JEC21", "C. parapsilosis CDC317", "C. posadasii C735 delta SOWgp", "M. oryzae 70-15", "N. crassa OR74A", "S. cerevisiae", "S. pombe", "T. marneffei ATCC 18224", "U. maydis 521"], code="C")
        query.add_constraint("organism.shortName", "=", "S. cerevisiae", code="B")
        query.add_constraint("Gene", "LOOKUP", gene_name, code="A")
        data = []
        for row in query.rows():
            data.append({ 'species': row["homologues.homologue.organism.shortName"],
                          'gene_id': row["homologues.homologue.primaryIdentifier"],
                          'gene_name': row["homologues.homologue.symbol"],
                          'source': row["homologues.dataSets.dataSource.name"],
                          'description': row["homologues.homologue.briefDescription"] })
        
        #dataSortByID = sorted(data, key=lambda d: d['gene_id'])
        dataSortBySpecies = sorted(data, key=lambda d: d['species'])
        return HTTPOk(body=json.dumps(dataSortBySpecies), content_type="text/json")        
    except Exception as e:
        log.error(e)        
        
@view_config(route_name='locus_literature_details', renderer='json', request_method='GET')
def locus_literature_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.literature_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='locus_literature_graph', renderer='json', request_method='GET')
def locus_literature_graph(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.literature_graph()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='locus_interaction_graph', renderer='json', request_method='GET')
def locus_interaction_graph(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.interaction_graph()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='locus_regulation_graph', renderer='json', request_method='GET')
def locus_regulation_graph(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.regulation_graph()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_go_details', renderer='json', request_method='GET')
def locus_go_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.go_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_disease_details', renderer='json', request_method='GET')
def locus_disease_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.disease_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_interaction_details', renderer='json', request_method='GET')
def locus_interaction_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.interactions_to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

# TEMP disable
# @view_config(route_name='locus_expression_details', renderer='json', request_method='GET')
# def locus_expression_details(request):
#     id = extract_id_request(request, 'locus')
#     locus = get_locus_by_id(id)
#     if locus:
#         return locus.expression_to_dict()
#     else:
#         return HTTPNotFound()

@view_config(route_name='locus_neighbor_sequence_details', renderer='json', request_method='GET')
def locus_neighbor_sequence_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.neighbor_sequence_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_sequence_details', renderer='json', request_method='GET')
def locus_sequence_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.sequence_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='bioentity_list', renderer='json', request_method='POST')
def analyze(request):
    try:
        data = request.json
    except ValueError:
        return HTTPBadRequest(body=json.dumps({'error': 'Invalid JSON format in body request'}))

    if "bioent_ids" not in data:
        return HTTPBadRequest(body=json.dumps({'error': 'Key \"bioent_ids\" missing'}))

    try:
        if "is_name" in data and data['is_name'] is True:
            loci = DBSession.query(Locusdbentity).filter(Locusdbentity.systematic_name.in_(data['bioent_ids'])).all()
        else:
            loci = DBSession.query(Locusdbentity).filter(Locusdbentity.dbentity_id.in_(data['bioent_ids'])).all()

        return [locus.to_dict_analyze() for locus in loci]
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='dataset', renderer='json', request_method='GET')
def dataset(request):
    try:
        id = extract_id_request(request, 'dataset')
        dataset = DBSession.query(Dataset).filter_by(dataset_id=id).one_or_none()
        if dataset:
            return dataset.to_dict(add_conditions=True, add_resources=True)
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='keyword', renderer='json', request_method='GET')
def keyword(request):
    try:
        id = extract_id_request(request, 'keyword')
        keyword = DBSession.query(Keyword).filter_by(keyword_id=id).one_or_none()
        if keyword:
            return keyword.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='keywords', renderer='json', request_method='GET')
def keywords(request):
    try:
        # keyword_ids = DBSession.query(distinct(DatasetKeyword.keyword_id)).all()
        keyword_ids = []
        for x in DBSession.query(DatasetKeyword).all():
            if x.keyword_id not in keyword_ids:
                keyword_ids.append(x.keyword_id)
        keywords = DBSession.query(Keyword).filter(Keyword.keyword_id.in_(keyword_ids)).all()
        simple_keywords = [k.to_simple_dict() for k in keywords]
        for k in simple_keywords:
            k['name'] = k['display_name']
        return simple_keywords
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='contig', renderer='json', request_method='GET')
def contig(request):
    try:
        id = extract_id_request(request, 'contig', param_name="format_name")
        contig = DBSession.query(Contig).filter_by(contig_id=id).one_or_none()
        if contig:
            return contig.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='contig_sequence_details', renderer='json', request_method='GET')
def contig_sequence_details(request):
    try:
        id = extract_id_request(request, 'contig')
        contig = DBSession.query(Contig).filter_by(contig_id=id).one_or_none()
        if contig:
            return contig.sequence_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_posttranslational_details', renderer='json', request_method='GET')
def locus_posttranslational_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.posttranslational_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='reference_posttranslational_details', renderer='json', request_method='GET')
def reference_posttranslational_details(request):
    try:
        id = extract_id_request(request, 'reference')
        reference = DBSession.query(Referencedbentity).filter_by(dbentity_id = id).one_or_none()
        if reference:
            ptms = DBSession.query(Posttranslationannotation).filter_by(reference_id = reference.dbentity_id).options(joinedload('psimod'),joinedload('modifier'),joinedload('dbentity')).all()
            ptms_return_value = []
            for ptm in ptms:
                obj = {
                    'protein':ptm.dbentity.display_name,
                    'site_residue':ptm.site_residue,
                    'site_index':ptm.site_index,
                    'modification':ptm.psimod.display_name,
                    'modifier':None
                }
                if ptm.modifier:
                    obj['modifier'] = ptm.modifier.display_name
                ptms_return_value.append(obj)
            return ptms_return_value
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()


@view_config(route_name='locus_ecnumber_details', renderer='json', request_method='GET')
def locus_ecnumber_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.ecnumber_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            

@view_config(route_name='locus_protein_experiment_details', renderer='json', request_method='GET')
def locus_protein_experiment_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.protein_experiment_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_protein_abundance_details', renderer='json', request_method='GET')
def locus_protein_abundance_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.protein_abundance_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_protein_domain_details', renderer='json', request_method='GET')
def locus_protein_domain_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.protein_domain_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()


@view_config(route_name='locus_binding_site_details', renderer='json', request_method='GET')
def locus_binding_site_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.binding_site_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_regulation_details', renderer='json', request_method='GET')
def locus_regulation_details(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.regulation_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_regulation_target_enrichment', renderer='json', request_method='GET')
def locus_regulation_target_enrichment(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.regulation_target_enrichment()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='locus_protein_domain_graph', renderer='json', request_method='GET')
def locus_protein_domain_graph(request):
    try:
        id = extract_id_request(request, 'locus')
        locus = get_locus_by_id(id)
        if locus:
            return locus.protein_domain_graph()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='domain', renderer='json', request_method='GET')
def domain(request):
    try:
        id = extract_id_request(request, 'proteindomain', param_name="format_name")
        proteindomain = DBSession.query(Proteindomain).filter_by(proteindomain_id=id).one_or_none()
        if proteindomain:
            return proteindomain.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='domain_locus_details', renderer='json', request_method='GET')
def domain_locus_details(request):
    try:
        id = extract_id_request(request, 'proteindomain')
        proteindomain = DBSession.query(Proteindomain).filter_by(proteindomain_id=id).one_or_none()
        if proteindomain:
            return proteindomain.locus_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='domain_enrichment', renderer='json', request_method='GET')
def domain_enrichment(request):
    try:
        id = extract_id_request(request, 'proteindomain')
        proteindomain = DBSession.query(Proteindomain).filter_by(proteindomain_id=id).one_or_none()
        if proteindomain:
            return proteindomain.enrichment()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='ecnumber', renderer='json', request_method='GET')
def ecnumber(request):
    try:
        id = extract_id_request(request, 'ec')
        ec = DBSession.query(Ec).filter_by(ec_id=id).one_or_none()
        if ec:
            return ec.to_dict()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
    
@view_config(route_name='primer3', renderer='json', request_method='GET') 
def primer3(request):

    gene_name = request.params.get('gene_name', '')
    sequence = request.params.get('sequence', '')
    if gene_name == "None":
        gene_name = ''
    if sequence == "None":
        sequence = ''
                                        
    if gene_name != '' and sequence != '':
        return HTTPBadRequest(body=json.dumps({'error': 'Both gene name AND sequence provided'}))

    if gene_name == '' and sequence == '':
            return HTTPBadRequest(body=json.dumps({'error': 'No gene name OR sequence provided'}))

    if gene_name == '':
        # sequence = str(sequence.replace('\r', '').replace('\n', ''))  
        regex = re.compile('[^a-zA-Z]')
        sequence = regex.sub('', sequence)
        decodeseq = sequence
        input = 'seq'
    else:
        gene_name = gene_name.upper()
        locus = DBSession.query(Locusdbentity).filter(or_(Locusdbentity.gene_name == gene_name, Locusdbentity.systematic_name == gene_name)).one_or_none()
        if locus is None:
            return HTTPBadRequest(body=json.dumps({'error': 'Gene name provided does not exist in the database:  ' + gene_name}))
        tax = DBSession.query(Straindbentity).filter(Straindbentity.strain_type =='Reference').one_or_none()
        tax_id = tax.taxonomy_id        
        seqRow = DBSession.query(Dnasequenceannotation).filter(and_(Dnasequenceannotation.taxonomy_id == tax_id, Dnasequenceannotation.dbentity_id == locus.dbentity_id, Dnasequenceannotation.dna_type =='1KB')).one_or_none()
        if seqRow is None:
            return HTTPBadRequest(body=json.dumps({'error': 'Sequence for provided gene name does not exist in the database:  ' + gene_name}))
        else:
            dna = seqRow.residues
            decodeseq = dna
            sequence = str(dna)
            # sequence = sequence[1:-1]
            input = 'name'

    if 'maximum_tm' in request.params:
        maximum_tm = int(request.params.get('maximum_tm'))
    if 'minimum_tm' in request.params:
        minimum_tm = int(request.params.get('minimum_tm'))
    if 'optimum_tm' in request.params:
        optimum_tm = int(request.params.get('optimum_tm'))
    if 'maximum_gc' in request.params:
        maximum_gc = int(request.params.get('maximum_gc'))
    if 'minimum_gc' in request.params:
        minimum_gc = int(request.params.get('minimum_gc'))
    if 'optimum_gc' in request.params:
        optimum_gc = int(request.params.get('optimum_gc'))
    if 'maximum_length' in request.params:
        maximum_length = int(request.params.get('maximum_length'))
    if 'minimum_length' in request.params:
        minimum_length = int(request.params.get('minimum_length'))
    if 'optimum_primer_length' in request.params:
        optimum_primer_length = int(request.params.get('optimum_primer_length'))
    if 'max_three_prime_pair_complementarity' in request.params:
        max_three_prime_pair_complementarity = int(request.params.get('max_three_prime_pair_complementarity'))
    if 'max_pair_complementarity' in request.params:
        max_pair_complementarity = int(request.params.get('max_pair_complementarity'))
    if 'max_three_prime_self_complementarity' in request.params:
        max_three_prime_self_complementarity= int(request.params.get('max_three_prime_self_complementarity'))
    if 'max_self_complementarity' in request.params:
        max_self_complementarity = int(request.params.get('max_self_complementarity'))
    if 'input_end' in request.params:
        input_end = int(request.params.get('input_end'))
    if 'input_start' in request.params:
        input_start = int(request.params.get('input_start'))
    maximum_product_size = None
    if 'mum_product_size' in request.params:
        maximum_product_size = request.params.get('maximum_product_size')
        if maximum_product_size != 'None':
            maximum_product_size = int(maximum_product_size)
    if 'end_point' in request.params:
        end_point = request.params.get('end_point')
       
    if gene_name == '':
        target_start = input_start
        target_extend_by =  input_end - input_start
    else:
        if input_start < 0:
            target_start = 1000 - abs(input_start)
            target_extend_by = (1000 + input_end) - target_start
        else:
            target_start = 1000 + input_start
            target_extend_by = input_end - input_start

    interval_range = [[100, 150], [150, 250], [100, 300], [301, 400], [401, 500], [501, 600], [601, 700], [701, 850], [851, 1000]]
    if maximum_product_size:
        range_start = target_extend_by
        range_stop = maximum_product_size
        if maximum_product_size < target_extend_by:
            return HTTPBadRequest(body=json.dumps({'error': 'Maximum product size cannot be less than target size.'}))
        interval_range = [[range_start, range_stop]]
    elif(target_extend_by > 800):
        interval_range = [[target_extend_by, target_extend_by+300]]

    sequence_target = [[target_start, target_extend_by]]
    if end_point == 'YES':
        force_left_start = target_start
        force_right_start = target_start + target_extend_by
        sequence_target = []
    elif end_point == 'NO':
        force_left_start = -1000000
        force_right_start = -1000000

    try:
        result = bindings.designPrimers(
            {
                'SEQUENCE_ID': str(gene_name),
                'SEQUENCE_TEMPLATE': sequence,
                'SEQUENCE_TARGET': sequence_target,
                'SEQUENCE_FORCE_LEFT_START': force_left_start,
                'SEQUENCE_FORCE_RIGHT_START': force_right_start
            },
            {
                'PRIMER_FIRST_BASE_INDEX': 1,
                'PRIMER_THERMODYNAMIC_OLIGO_ALIGNMENT': 1,
                'PRIMER_THERMODYNAMIC_TEMPLATE_ALIGNMENT' : 0,
                'PRIMER_PICK_LEFT_PRIMER': 1,
                'PRIMER_PICK_INTERNAL_OLIGO': 0,
                'PRIMER_PICK_RIGHT_PRIMER': 1,
                'PRIMER_LIBERAL_BASE': 1,
                'PRIMER_LIB_AMBIGUITY_CODES_CONSENSUS': 0,
                'PRIMER_LOWERCASE_MASKING': 0,
                'PRIMER_PICK_ANYWAY': 0,
                'PRIMER_EXPLAIN_FLAG': 1,
                'PRIMER_MASK_TEMPLATE': 0,
                'PRIMER_TASK' : 'generic',
                'PRIMER_MASK_FAILURE_RATE': 0.1,
                'PRIMER_MASK_5P_DIRECTION': 1,
                'PRIMER_MASK_3P_DIRECTION': 0,
                'PRIMER_MIN_QUALITY': 0,
                'PRIMER_MIN_END_QUALITY': 0,
                'PRIMER_QUALITY_RANGE_MIN': 0,
                'PRIMER_QUALITY_RANGE_MAX': 100,
                'PRIMER_MIN_SIZE': minimum_length,
                'PRIMER_OPT_SIZE': optimum_primer_length,
                'PRIMER_MAX_SIZE': maximum_length,
                'PRIMER_MIN_TM': minimum_tm,
                'PRIMER_OPT_TM': optimum_tm,
                'PRIMER_MAX_TM': maximum_tm,
                'PRIMER_PAIR_MAX_DIFF_TM': 5.0,
                'PRIMER_TM_FORMULA': 1,
                'PRIMER_PRODUCT_MIN_TM': -1000000.0,
                'PRIMER_PRODUCT_OPT_TM' : 0.0,
                'PRIMER_PRODUCT_MAX_TM' : 1000000.0,
                'PRIMER_MIN_GC' : minimum_gc,
                'PRIMER_OPT_GC_PERCENT' : optimum_gc,
                'PRIMER_MAX_GC' : maximum_gc,
                'PRIMER_PRODUCT_SIZE_RANGE': interval_range,
                'PRIMER_NUM_RETURN': 5,
                'PRIMER_MAX_END_STABILITY' : 9.0,
                'PRIMER_MAX_LIBRARY_MISPRIMING' : 12.00,
                'PRIMER_PAIR_MAX_LIBRARY_MISPRIMING' : 20.00,
                'PRIMER_MAX_SELF_ANY_TH' : 45.0,
                'PRIMER_MAX_SELF_END_TH' : 35.0,
                'PRIMER_PAIR_MAX_COMPL_ANY_TH' : 45.0,
                'PRIMER_PAIR_MAX_COMPL_END_TH' : 35.0,
                'PRIMER_MAX_HAIRPIN_TH' : 24.0,
                'PRIMER_MAX_SELF_ANY' : max_self_complementarity,
                'PRIMER_MAX_SELF_END' : max_three_prime_self_complementarity,
                'PRIMER_PAIR_MAX_COMPL_ANY' : max_pair_complementarity,
                'PRIMER_PAIR_MAX_COMPL_END' : max_three_prime_pair_complementarity,
                'PRIMER_MAX_TEMPLATE_MISPRIMING_TH' : 40.00,
                'PRIMER_PAIR_MAX_TEMPLATE_MISPRIMING_TH' : 70.00,
                'PRIMER_MAX_TEMPLATE_MISPRIMING' : 12.00,
                'PRIMER_PAIR_MAX_TEMPLATE_MISPRIMING' : 24.00,
                'PRIMER_MAX_NS_ACCEPTED' : 0,
                'PRIMER_MAX_POLY_X' : 4,
                'PRIMER_INSIDE_PENALTY' : -1.0,
                'PRIMER_OUTSIDE_PENALTY' : 0,
                'PRIMER_GC_CLAMP' : 0,
                'PRIMER_MAX_END_GC' : 5,
                'PRIMER_MIN_LEFT_THREE_PRIME_DISTANCE' : 3,
                'PRIMER_MIN_RIGHT_THREE_PRIME_DISTANCE' : 3,
                'PRIMER_MIN_5_PRIME_OVERLAP_OF_JUNCTION' : 7,
                'PRIMER_MIN_3_PRIME_OVERLAP_OF_JUNCTION' : 4,
                'PRIMER_SALT_MONOVALENT' : 50.0,
                'PRIMER_SALT_CORRECTIONS' : 1,
                'PRIMER_SALT_DIVALENT' : 1.5,
                'PRIMER_DNTP_CONC' : 0.6,
                'PRIMER_DNA_CONC' : 50.0,
                'PRIMER_SEQUENCING_SPACING' : 500,
                'PRIMER_SEQUENCING_INTERVAL' : 250,
                'PRIMER_SEQUENCING_LEAD' : 50,
                'PRIMER_SEQUENCING_ACCURACY' : 20,
                'PRIMER_WT_SIZE_LT' : 1.0,
                'PRIMER_WT_SIZE_GT' : 1.0,
                'PRIMER_WT_TM_LT' : 1.0,
                'PRIMER_WT_TM_GT' : 1.0,
                'PRIMER_WT_GC_PERCENT_LT' : 0.0,
                'PRIMER_WT_GC_PERCENT_GT' : 0.0,
                'PRIMER_WT_SELF_ANY_TH' : 0.0,
                'PRIMER_WT_SELF_END_TH' : 0.0,
                'PRIMER_WT_HAIRPIN_TH' : 0.0,
                'PRIMER_WT_TEMPLATE_MISPRIMING_TH' : 0.0,
                'PRIMER_WT_SELF_ANY' : 0.0,
                'PRIMER_WT_SELF_END' : 0.0,
                'PRIMER_WT_TEMPLATE_MISPRIMING' : 0.0,
                'PRIMER_WT_NUM_NS' : 0.0,
                'PRIMER_WT_LIBRARY_MISPRIMING' : 0.0,
                'PRIMER_WT_SEQ_QUAL' : 0.0,
                'PRIMER_WT_END_QUAL' : 0.0,
                'PRIMER_WT_POS_PENALTY' : 0.0,
                'PRIMER_WT_END_STABILITY' : 0.0,
                'PRIMER_WT_MASK_FAILURE_RATE' : 0.0,
                'PRIMER_PAIR_WT_PRODUCT_SIZE_LT' : 0.0,
                'PRIMER_PAIR_WT_PRODUCT_SIZE_GT' : 0.0,
                'PRIMER_PAIR_WT_PRODUCT_TM_LT' : 0.0,
                'PRIMER_PAIR_WT_PRODUCT_TM_GT' : 0.0,
                'PRIMER_PAIR_WT_COMPL_ANY_TH' : 0.0,
                'PRIMER_PAIR_WT_COMPL_END_TH' : 0.0,
                'PRIMER_PAIR_WT_TEMPLATE_MISPRIMING_TH': 0.0,
                'PRIMER_PAIR_WT_COMPL_ANY' : 0.0,
                'PRIMER_PAIR_WT_COMPL_END' : 0.0,
                'PRIMER_PAIR_WT_TEMPLATE_MISPRIMING' : 0.0,
                'PRIMER_PAIR_WT_DIFF_TM' : 0.0,
                'PRIMER_PAIR_WT_LIBRARY_MISPRIMING' : 0.0,
                'PRIMER_PAIR_WT_PR_PENALTY' : 1.0,
                'PRIMER_PAIR_WT_IO_PENALTY' : 0.0,
                'PRIMER_INTERNAL_MIN_SIZE' : 18,
                'PRIMER_INTERNAL_OPT_SIZE' : 20,
                'PRIMER_INTERNAL_MAX_SIZE' : 27,
                'PRIMER_INTERNAL_MIN_TM' : 57.0,
                'PRIMER_INTERNAL_OPT_TM' : 60.0,
                'PRIMER_INTERNAL_MAX_TM' : 63.0,
                'PRIMER_INTERNAL_MIN_GC' : 20.0,
                'PRIMER_INTERNAL_OPT_GC_PERCENT' : 50.0,
                'PRIMER_INTERNAL_MAX_GC' : 80.0,
                'PRIMER_INTERNAL_MAX_SELF_ANY_TH': 47.00,
                'PRIMER_INTERNAL_MAX_SELF_END_TH' : 47.00,
                'PRIMER_INTERNAL_MAX_HAIRPIN_TH' : 47.00,
                'PRIMER_INTERNAL_MAX_SELF_ANY': 12.00,
                'PRIMER_INTERNAL_MAX_SELF_END': 12.00,
                'PRIMER_INTERNAL_MIN_QUALITY': 0,
                'PRIMER_INTERNAL_MAX_NS_ACCEPTED' : 0,
                'PRIMER_INTERNAL_MAX_POLY_X' : 5,
                'PRIMER_INTERNAL_MAX_LIBRARY_MISHYB' : 12.00,
                'PRIMER_INTERNAL_SALT_MONOVALENT' : 50.0,
                'PRIMER_INTERNAL_DNA_CONC' : 50.0,
                'PRIMER_INTERNAL_SALT_DIVALENT' : 1.5,
                'PRIMER_INTERNAL_DNTP_CONC' : 0.0,
                'PRIMER_INTERNAL_WT_SIZE_LT' : 1.0,
                'PRIMER_INTERNAL_WT_SIZE_GT' : 1.0,
                'PRIMER_INTERNAL_WT_TM_LT' : 1.0,
                'PRIMER_INTERNAL_WT_TM_GT' : 1.0,
                'PRIMER_INTERNAL_WT_GC_PERCENT_LT' : 0.0,
                'PRIMER_INTERNAL_WT_GC_PERCENT_GT' : 0.0,
                'PRIMER_INTERNAL_WT_SELF_ANY_TH' : 0.0,
                'PRIMER_INTERNAL_WT_SELF_END_TH' : 0.0,
                'PRIMER_INTERNAL_WT_HAIRPIN_TH' : 0.0,
                'PRIMER_INTERNAL_WT_SELF_ANY' : 0.0,
                'PRIMER_INTERNAL_WT_SELF_END' : 0.0,
                'PRIMER_INTERNAL_WT_NUM_NS' : 0.0,
                'PRIMER_INTERNAL_WT_LIBRARY_MISHYB': 0.0,
                'PRIMER_INTERNAL_WT_SEQ_QUAL' : 0.0,
                'PRIMER_INTERNAL_WT_END_QUAL': 0.0
        }, debug=False)

        presult, notes = primer3_parser(result)
        obj = {'result' : presult, 'gene_name': gene_name, 'seq': decodeseq, 'input': input}
        return obj

    except Exception as e:
        log.error(e)
        return HTTPBadRequest(body=json.dumps({'error': str(e) }))

@view_config(route_name='ecnumber_locus_details', renderer='json', request_method='GET')
def ecnumber_locus_details(request):
    try:
        id = extract_id_request(request, 'ec')
        ec = DBSession.query(Ec).filter_by(ec_id=id).one_or_none()
        if ec:
            return ec.locus_details()
        else:
            return HTTPNotFound()
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='goslim', renderer='json', request_method='GET')
def goslim(request):
    try:
        slim_data = DBSession.query(Goslim).all()
        data = {}
        for x in slim_data:
            slim_type = x.slim_name + ": " + x.go.go_namespace.split(' ')[1]
            slim_terms = []
            if slim_type in data:
                slim_terms = data[slim_type]
            slim_terms.append(x.go.display_name + " ; " + x.go.goid)
            data[slim_type] = slim_terms

        orderedData = []
        for slim_type in sorted(data.keys()):
            orderedData.append({"slim_type": slim_type,
                                "terms": sorted(data[slim_type])})

        return orderedData
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='ambiguous_names', renderer='json', request_method='GET')
def ambiguous_names(request):

    locus_data = DBSession.query(Locusdbentity).filter_by(has_summary='1').all()
    mapping = {}
    locus_id2systematic_name = {}
    for x in locus_data:
        mapping[x.systematic_name] = x
        if x.gene_name:
            mapping[x.gene_name] = x
        locus_id2systematic_name[x.dbentity_id] = x.systematic_name

    data = {}
    # alias_data = DBSession.query(LocusAlias).filter_by(alias_type='Uniform').all()
    alias_data = DBSession.query(LocusAlias).filter(LocusAlias.alias_type.in_(['Uniform', 'Non-uniform'])).all()   
    display_name_to_locus_id = {}
    for y in alias_data:
        display_name = y.display_name
        locus_id_list = []
        if display_name in display_name_to_locus_id:
            locus_id_list = display_name_to_locus_id[display_name]
        locus_id_list.append(y.locus_id)
        display_name_to_locus_id[display_name] = locus_id_list
        if display_name not in mapping:
            continue
        if display_name not in data:
            x = mapping[display_name]
            data[display_name] = [{ "systematic_name": x.systematic_name,
                                    "gene_name": x.gene_name,
                                    "sgdid": x.sgdid,
                                    "name_type": 'gene_name' }]
        names = data[display_name]
        systematic_name = locus_id2systematic_name[y.locus_id]
        x = mapping[systematic_name]
        names.append({ "systematic_name": systematic_name,
                       "gene_name": x.gene_name,
                       "sgdid": x.sgdid,
                       "alias_name": display_name,
                       "name_type": 'alias_name' })
        data[display_name] = names

    for display_name in display_name_to_locus_id:
        if len(display_name_to_locus_id[display_name]) > 1:
            locus_id_list = display_name_to_locus_id[display_name]
            names = []
            if display_name in data:
                names = data[display_name]
            for locus_id in locus_id_list:
                systematic_name = locus_id2systematic_name[locus_id]
                x = mapping[systematic_name]
                names.append({ "systematic_name": systematic_name,
                               "gene_name": x.gene_name,
                               "sgdid": x.sgdid,
                               "alias_name": display_name,
                               "name_type": 'alias_name' })
            data[display_name] = names

    return data


@view_config(route_name='complex', renderer='json', request_method='GET')
def complex(request):
    try:
        complexAC = request.matchdict['id']
        complex = DBSession.query(Complexdbentity).filter(or_(Complexdbentity.format_name==complexAC, Complexdbentity.sgdid==complexAC)).one_or_none()
        if complex is not None:
            return complex.protein_complex_details()
        else:
            return {}
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='allele', renderer='json', request_method='GET')
def allele(request):
    try:
        # allele = allele.replace('%C3%8E%C2%94', 'Δ')
        # allele = request.matchdict['id'].replace('SGD:S', 'S').replace('Δ', 'delta')
        allele = request.matchdict['id'].replace('SGD:S', 'S')
        alleleObj = None
        if allele.startswith('S0'):
            alleleObj = DBSession.query(Alleledbentity).filter_by(sgdid=allele).one_or_none()
        else:
            alleleObj = DBSession.query(Alleledbentity).filter(Alleledbentity.format_name.ilike(allele)).one_or_none()
        if alleleObj is None:
            aa = DBSession.query(AlleleAlias).filter(AlleleAlias.display_name.ilike(allele)).one_or_none()
            if aa is not None:
                alleleObj = aa.allele
                
        if alleleObj is not None:
            return alleleObj.to_dict()
        else:
            return {}
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()
            
@view_config(route_name='allele_phenotype_details', renderer='json', request_method='GET')
def allele_phenotype_details(request):

    try:
        allele = request.matchdict['id'].replace('SGD:S', 'S')

        alleleObj = None
        if allele.startswith('S0'):
            alleleObj = DBSession.query(Alleledbentity).filter_by(sgdid=allele).one_or_none()
        else:
            alleleObj = DBSession.query(Alleledbentity).filter(Alleledbentity.format_name.ilike(allele)).one_or_none()

        if alleleObj is not None:
            return alleleObj.phenotype_to_dict()
        else:
            return []
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='allele_interaction_details', renderer='json', request_method='GET')
def allele_interaction_details(request):
    try:
        allele = request.matchdict['id'].replace('SGD:S', 'S')

        alleleObj = None
        if allele.startswith('S0'):
            alleleObj = DBSession.query(Alleledbentity).filter_by(sgdid=allele).one_or_none()
        else:
            alleleObj = DBSession.query(Alleledbentity).filter(Alleledbentity.format_name.ilike(allele)).one_or_none()

        if alleleObj is not None:
            return alleleObj.interaction_to_dict()
        else:
            return []
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='allele_network_graph', renderer='json', request_method='GET')
def allele_network_graph(request):
    try:
        allele = request.matchdict['id'].replace('SGD:S', 'S')

        alleleObj = None
        if allele.startswith('S0'):
            alleleObj = DBSession.query(Alleledbentity).filter_by(sgdid=allele).one_or_none()
        else:
            alleleObj = DBSession.query(Alleledbentity).filter(Alleledbentity.format_name.ilike(allele)).one_or_none()

        if alleleObj is not None:
            return alleleObj.allele_network()
        else:
            return []
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

@view_config(route_name='alignment', renderer='json', request_method='GET')
def alignment(request):
    try:
        locus = request.matchdict['id']
        files = DBSession.query(Filedbentity).filter(Filedbentity.previous_file_name.like(locus+'%')).all()

        if len(files) > 0:
            data = {}
            for file in files:
                s3_url = file.s3_url.split("?versionId=")[0]
                if file.previous_file_name not in [locus+".png", locus+".align", locus+"_dna.png", locus+"_dna.align"]:
                    continue
                if '_dna' in file.previous_file_name:
                    if ".png" in file.previous_file_name:
                        data['dna_images_url'] = s3_url
                    else:
                        data['dna_align_url'] = s3_url
                else:
                    if ".png" in file.previous_file_name:
                        data['protein_images_url'] = s3_url
                    else:
                        data['protein_align_url'] = s3_url
            return data
        else:
            return {}
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

# check for basic rad54 response
@view_config(route_name='healthcheck', renderer='json', request_method='GET')
def healthcheck(request):
    MAX_QUERY_ATTEMPTS = 3
    attempts = 0
    ldict = None
    while attempts < MAX_QUERY_ATTEMPTS:
        try:
            locus = get_locus_by_id(1268789)
            ldict = locus.to_dict()
            break
        except DetachedInstanceError:
            traceback.print_exc()
            log.info('DB session closed from detached instance state.')
            DBSession.remove()
            attempts += 1
        except IntegrityError:
            traceback.print_exc()
            log.info('DB rolled back from integrity error.')
            DBSession.rollback()
            DBSession.remove()
            attempts += 1
    return ldict


# api portal with swagger
@view_config(route_name='api_portal', renderer='json')
def api_portal(request):
    try:
        request.response.headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST,GET,DELETE,PUT,OPTIONS',
            'Access-Control-Allow-Headers': 'Origin, Content-Type, Accept, Authorization'
        })
        json_file = os.path.join(str(Path(__file__).parent.parent), "api_docs/swagger.json")
        with open(json_file) as f:
            data = json.load(f)

        return data
    except Exception as e:
        log.error(e)
    finally:
        if DBSession:
            DBSession.remove()

