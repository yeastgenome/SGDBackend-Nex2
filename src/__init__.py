from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from sqlalchemy import create_engine
import os

from .models import DBSession, Base

def main(global_config, **settings):
    engine = create_engine(os.environ['NEX2_URI'], echo=False, pool_recycle=3600, pool_size=15)
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings)

    config.add_route('home', '/')
    config.add_route('get_recent_annotations', '/annotations')
    #search
    config.add_route('search', '/get_search_results')
    config.add_route('autocomplete_results', '/autocomplete_results')

    #variant viewer
    config.add_route('search_sequence_objects', '/search_sequence_objects', request_method='GET')
    config.add_route('get_sequence_object', '/get_sequence_object/{id}', request_method='GET')

    #genomesnapshot
    config.add_route('genomesnapshot', '/genomesnapshot', request_method='GET')

    # nex2
    config.add_route('reserved_name', '/reservedname/{id}', request_method='GET')

    config.add_route('strain', '/strain/{id}', request_method='GET')

    config.add_route('reference_this_week', '/references/this_week', request_method='GET')
    config.add_route('reference', '/reference/{id}', request_method='GET')

    config.add_route('reference_literature_details', '/reference/{id}/literature_details', request_method='GET')
    config.add_route('reference_interaction_details', '/reference/{id}/interaction_details', request_method='GET')
    config.add_route('reference_go_details', '/reference/{id}/go_details', request_method='GET')
    config.add_route('reference_phenotype_details', '/reference/{id}/phenotype_details', request_method='GET')
    config.add_route('reference_regulation_details', '/reference/{id}/regulation_details', request_method='GET')
    config.add_route('reference_list', '/reference_list')

    config.add_route('author', '/author/{format_name}', request_method='GET')

    config.add_route('chemical', '/chemical/{format_name}', request_method='GET')
    config.add_route('chemical_phenotype_details', '/chemical/{id}/phenotype_details', request_method='GET')

    config.add_route('phenotype', '/phenotype/{format_name}', request_method='GET')
    config.add_route('phenotype_locus_details', '/phenotype/{id}/locus_details', request_method='GET')

    config.add_route('observable', '/observable/{format_name}', request_method='GET')
    config.add_route('observable_locus_details', '/observable/{id}/locus_details', request_method='GET')
    config.add_route('observable_ontology_graph', '/observable/{id}/ontology_graph', request_method='GET')
    config.add_route('observable_locus_details_all', '/observable/{id}/locus_details_all', request_method='GET')

    config.add_route('go', '/go/{format_name}', request_method='GET')
    config.add_route('go_ontology_graph', '/go/{id}/ontology_graph', request_method='GET')
    config.add_route('go_locus_details', '/go/{id}/locus_details', request_method='GET')
    config.add_route('go_locus_details_all', '/go/{id}/locus_details_all', request_method='GET')

    config.add_route('locus', '/locus/{sgdid}', request_method='GET')
    config.add_route('locus_tabs', '/locus/{id}/tabs', request_method='GET')
    config.add_route('locus_phenotype_details', '/locus/{id}/phenotype_details', request_method='GET')
    config.add_route('locus_phenotype_graph', '/locus/{id}/phenotype_graph', request_method='GET')
    config.add_route('locus_literature_details', '/locus/{id}/literature_details', request_method='GET')
    config.add_route('locus_literature_graph', '/locus/{id}/literature_graph', request_method='GET')
    config.add_route('locus_go_details', '/locus/{id}/go_details', request_method='GET')
    config.add_route('locus_go_graph', '/locus/{id}/go_graph', request_method='GET')
    config.add_route('locus_interaction_details', '/locus/{id}/interaction_details', request_method='GET')
    config.add_route('locus_interaction_graph', '/locus/{id}/interaction_graph', request_method='GET')
    # TEMP disable
    # config.add_route('locus_expression_details', '/locus/{id}/expression_details', request_method='GET')
    config.add_route('locus_expression_graph', '/locus/{id}/expression_graph', request_method='GET')
    config.add_route('locus_regulation_graph', '/locus/{id}/regulation_graph', request_method='GET')
    config.add_route('locus_neighbor_sequence_details', '/locus/{id}/neighbor_sequence_details', request_method='GET')
    config.add_route('locus_sequence_details', '/locus/{id}/sequence_details', request_method='GET')
    config.add_route('locus_posttranslational_details', '/locus/{id}/posttranslational_details', request_method='GET')
    config.add_route('locus_ecnumber_details', '/locus/{id}/ecnumber_details', request_method='GET')
    config.add_route('locus_protein_experiment_details', '/locus/{id}/protein_experiment_details', request_method='GET')
    config.add_route('locus_protein_domain_details', '/locus/{id}/protein_domain_details', request_method='GET')
    config.add_route('locus_protein_domain_graph', '/locus/{id}/protein_domain_graph', request_method='GET')
    config.add_route('locus_binding_site_details', '/locus/{id}/binding_site_details', request_method='GET')
    config.add_route('locus_regulation_details', '/locus/{id}/regulation_details', request_method='GET')
    config.add_route('locus_regulation_target_enrichment', '/locus/{id}/regulation_target_enrichment', request_method='GET')

    config.add_route('domain','/domain/{format_name}', request_method='GET')
    config.add_route('domain_locus_details','/domain/{id}/locus_details', request_method='GET')
    config.add_route('domain_enrichment','/domain/{id}/enrichment', request_method='GET')

    config.add_route('contig', '/contig/{format_name}', request_method='GET')
    config.add_route('contig_sequence_details', '/contig/{id}/sequence_details', request_method='GET')

    config.add_route('bioentity_list', '/bioentity_list', request_method='POST')

    config.add_route('dataset', '/dataset/{id}', request_method='GET')
    config.add_route('keyword', '/keyword/{id}', request_method='GET')
    config.add_route('keywords', '/keywords', request_method='GET')

    config.add_route('ecnumber', '/ecnumber/{id}', request_method='GET')
    config.add_route('ecnumber_locus_details', '/ecnumber/{id}/locus_details', request_method='GET')

    config.add_route('primer3', '/primer3', request_method='POST')
    
    # curator interfaces
    config.add_route('account', '/account')
    config.add_route('sign_in', '/signin')
    config.add_route('db_sign_in', '/db_sign_in')
    config.add_route('sign_out', '/signout')
    config.add_route('colleague_update', '/colleagues/{id}', request_method='PUT')
    config.add_route('new_colleague', '/colleagues', request_method='POST')
    config.add_route('colleague_triage_index', '/colleagues/triage', request_method='GET')
    config.add_route('colleague_triage_show', '/colleagues/triage/{id}', request_method='GET')
    config.add_route('colleague_triage_update', '/colleagues/triage/{id}', request_method='PUT')
    config.add_route('colleague_triage_promote', '/colleagues/triage/{id}/promote', request_method='PUT')
    config.add_route('colleague_triage_delete', '/colleagues/triage/{id}', request_method='DELETE')

    # config.add_route('colleague_triage_accept', '/colleagues/triage/{id}', request_method='POST')
    # config.add_route('colleague_triage_update', '/colleagues/triage/{id}', request_method='PUT')
    # config.add_route('colleague_triage_delete', '/colleagues/triage/{id}', request_method='DELETE')

    # config.add_route('colleague_create', '/colleagues', request_method='POST')
    # config.add_route('colleague_update', '/colleagues/{format_name}', request_method='PUT')
    config.add_route('colleague_get', '/colleagues/{format_name}', request_method='GET')
    config.add_route('refresh_homepage_cache', '/refresh_homepage_cache', request_method='POST')

    config.add_route('get_new_reference_info', '/reference/confirm', request_method='POST')
    config.add_route('new_reference', '/reference', request_method='POST')
    config.add_route('reference_triage_index', '/reference_triage', request_method='GET')
    config.add_route('reference_triage_promote', '/reference/triage/{id}/promote', request_method='PUT')
    config.add_route('reference_triage_id', '/reference/triage/{id}', request_method='GET')
    config.add_route('reference_triage_id_update', '/reference/triage/{id}', request_method='PUT')
    config.add_route('reference_triage_id_delete', '/reference/triage/{id}', request_method='DELETE')
    config.add_route('reference_tags', '/reference/{id}/tags', request_method='GET')
    config.add_route('update_reference_tags', '/reference/{id}/tags', request_method='PUT')

    config.add_route('get_locus_curate', '/locus/{sgdid}/curate', request_method='GET')
    config.add_route('locus_curate_summaries', '/locus/{sgdid}/curate', request_method='PUT')
    config.add_route('locus_curate_basic', '/locus/{sgdid}/basic', request_method='PUT')
    
    config.add_route('formats', '/formats')
    config.add_route('topics', '/topics')
    config.add_route('extensions', '/extensions')
    config.add_route('upload', '/upload')
    config.add_route('upload_spreadsheet', '/upload_spreadsheet', request_method='POST')
    config.add_route('reserved_name_index', '/reservations', request_method='GET')
    config.add_route('reserved_name_curate_show', '/reservations/{id}', request_method='GET')
    config.add_route('reserved_name_update', '/reservations/{id}', request_method='PUT')
    config.add_route('reserved_name_standardize', '/reservations/{id}/standardize', request_method='POST')
    config.add_route('extend_reserved_name', '/reservations/{id}/extend', request_method='PUT')
    config.add_route('reserved_name_delete', '/reservations/{id}', request_method='DELETE')
    config.add_route('reserved_name_promote', '/reservations/{id}/promote', request_method='PUT')
    config.add_route('new_gene_name_reservation', '/reserve', request_method='POST')
    config.add_route('healthcheck', '/healthcheck')
    config.scan()
    config.add_static_view(name='assets', path='./build')

    return config.make_wsgi_app()
