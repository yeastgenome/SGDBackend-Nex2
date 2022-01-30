from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from sqlalchemy import create_engine
import os

from .models import DBSession, Base

def main(global_config, **settings):
    engine = create_engine(os.environ['NEX2_URI'], echo=False, pool_recycle=3600, pool_size=100)
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
    config.add_route('get_all_variant_objects', '/get_all_variant_objects', request_method='GET')
    
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
    config.add_route('reference_disease_details', '/reference/{id}/disease_details', request_method='GET')
    config.add_route('reference_regulation_details', '/reference/{id}/regulation_details', request_method='GET')
    config.add_route('reference_list', '/reference_list')
    config.add_route('reference_posttranslational_details', '/reference/{id}/posttranslational_details', request_method='GET')
    config.add_route('reference_functional_complement_details', '/reference/{id}/functional_complement_details', request_method='GET')
    
    config.add_route('author', '/author/{format_name}', request_method='GET')

    config.add_route('chemical', '/chemical/{format_name}', request_method='GET')
    config.add_route('chemical_phenotype_details', '/chemical/{id}/phenotype_details', request_method='GET')
    config.add_route('chemical_go_details', '/chemical/{id}/go_details', request_method='GET')
    config.add_route('chemical_proteinabundance_details', '/chemical/{id}/proteinabundance_details', request_method='GET')
    config.add_route('chemical_complex_details', '/chemical/{id}/complex_details', request_method='GET')
    config.add_route('chemical_network_graph', '/chemical/{id}/network_graph', request_method='GET')

    config.add_route('allele', '/allele/{id}', request_method='GET')
    config.add_route('allele_phenotype_details', '/allele/{id}/phenotype_details', request_method='GET')
    config.add_route('allele_interaction_details', '/allele/{id}/interaction_details', request_method='GET')
    config.add_route('allele_network_graph', '/allele/{id}/network_graph', request_method='GET')

    config.add_route('phenotype', '/phenotype/{format_name}', request_method='GET')
    config.add_route('phenotype_locus_details', '/phenotype/{id}/locus_details', request_method='GET')

    config.add_route('observable', '/observable/{format_name}', request_method='GET')
    config.add_route('observable_locus_details', '/observable/{id}/locus_details', request_method='GET')
    config.add_route('observable_ontology_graph', '/observable/{id}/ontology_graph', request_method='GET')
    config.add_route('observable_locus_details_all', '/observable/{id}/locus_details_all', request_method='GET')

    config.add_route('get_all_go_for_regulations','/go/regulations', request_method='GET')
    config.add_route('go', '/go/{format_name}', request_method='GET')
    config.add_route('go_ontology_graph', '/go/{id}/ontology_graph', request_method='GET')
    config.add_route('go_locus_details', '/go/{id}/locus_details', request_method='GET')
    config.add_route('go_locus_details_all', '/go/{id}/locus_details_all', request_method='GET')

    config.add_route('disease', '/disease/{id}', request_method='GET')
    config.add_route('disease_ontology_graph', '/disease/{id}/ontology_graph', request_method='GET')
    config.add_route('disease_locus_details', '/disease/{id}/locus_details', request_method='GET')
    config.add_route('disease_locus_details_all', '/disease/{id}/locus_details_all', request_method='GET')

    config.add_route('locus', '/locus/{sgdid}', request_method='GET')
    config.add_route('locus_tabs', '/locus/{id}/tabs', request_method='GET')
    config.add_route('locus_phenotype_details', '/locus/{id}/phenotype_details', request_method='GET')
    config.add_route('locus_phenotype_graph', '/locus/{id}/phenotype_graph', request_method='GET')
    config.add_route('locus_literature_details', '/locus/{id}/literature_details', request_method='GET')
    config.add_route('locus_literature_graph', '/locus/{id}/literature_graph', request_method='GET')
    config.add_route('locus_go_details', '/locus/{id}/go_details', request_method='GET')
    config.add_route('locus_go_graph', '/locus/{id}/go_graph', request_method='GET')
    config.add_route('locus_disease_details', '/locus/{id}/disease_details', request_method='GET')
    config.add_route('locus_disease_graph', '/locus/{id}/disease_graph', request_method='GET')
    config.add_route('locus_interaction_details', '/locus/{id}/interaction_details', request_method='GET')
    config.add_route('locus_interaction_graph', '/locus/{id}/interaction_graph', request_method='GET')
    config.add_route('locus_complement_details', '/locus/{id}/complement_details', request_method='GET')
    config.add_route('locus_homolog_details', '/locus/{id}/homolog_details', request_method='GET')
    config.add_route('locus_fungal_homolog_details', '/locus/{id}/fungal_homolog_details', request_method='GET')
    
    # TEMP disable
    # config.add_route('locus_expression_details', '/locus/{id}/expression_details', request_method='GET')
    config.add_route('locus_expression_graph', '/locus/{id}/expression_graph', request_method='GET')
    config.add_route('locus_regulation_graph', '/locus/{id}/regulation_graph', request_method='GET')
    config.add_route('locus_neighbor_sequence_details', '/locus/{id}/neighbor_sequence_details', request_method='GET')
    config.add_route('locus_sequence_details', '/locus/{id}/sequence_details', request_method='GET')
    config.add_route('locus_posttranslational_details', '/locus/{id}/posttranslational_details', request_method='GET')
    config.add_route('locus_ecnumber_details', '/locus/{id}/ecnumber_details', request_method='GET')
    config.add_route('locus_protein_experiment_details', '/locus/{id}/protein_experiment_details', request_method='GET')
    config.add_route('locus_protein_abundance_details', '/locus/{id}/protein_abundance_details', request_method='GET')
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
    config.add_route('get_keywords', '/get_keywords', request_method='GET')
    
    config.add_route('ecnumber', '/ecnumber/{id}', request_method='GET')
    config.add_route('ecnumber_locus_details', '/ecnumber/{id}/locus_details', request_method='GET')

    config.add_route('complex', '/complex/{id}', request_method='GET')

    config.add_route('goslim', '/goslim', request_method='GET')

    config.add_route('ambiguous_names', '/ambiguous_names', request_method='GET')

    config.add_route('alignment', '/alignment/{id}', request_method='GET')

    config.add_route('primer3', '/primer3', request_method='GET')
    
    # curator interfaces
    config.add_route('account', '/account')
    config.add_route('sign_in', '/signin')
    config.add_route('db_sign_in', '/db_sign_in')
    config.add_route('sign_out', '/signout')
    config.add_route('colleague_update', '/colleagues/{id}', request_method='PUT')
    # config.add_route('new_colleague', '/colleagues', request_method='POST')
    config.add_route('colleague_triage_index', '/colleagues/triage', request_method='GET')
    config.add_route('colleague_triage_show', '/colleagues/triage/{id}', request_method='GET')
    config.add_route('colleague_triage_update', '/colleagues/triage/{id}', request_method='PUT')
    config.add_route('colleague_triage_promote', '/colleagues/triage/{id}/promote', request_method='PUT')
    config.add_route('colleague_triage_delete', '/colleagues/triage/{id}', request_method='DELETE')
    config.add_route('colleague_with_subscription', '/colleagues_subscriptions', request_method='GET')
    config.add_route('get_newsletter_sourcecode', '/get_newsletter_sourcecode', request_method='POST')
    config.add_route('send_newsletter', '/send_newsletter', request_method='POST')

    # config.add_route('colleague_triage_accept', '/colleagues/triage/{id}', request_method='POST')
    # config.add_route('colleague_triage_update', '/colleagues/triage/{id}', request_method='PUT')
    # config.add_route('colleague_triage_delete', '/colleagues/triage/{id}', request_method='DELETE')

    # config.add_route('colleague_create', '/colleagues', request_method='POST')
    # config.add_route('colleague_update', '/colleagues/{format_name}', request_method='PUT')
    config.add_route('colleague_get', '/colleagues/{format_name}', request_method='GET')
    config.add_route('refresh_homepage_cache', '/refresh_homepage_cache', request_method='POST')

    #add new colleague
    config.add_route('add_new_colleague_triage', '/colleagues', request_method='POST')

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
    config.add_route('upload_file_curate', '/upload_file_curate', request_method='POST')
    config.add_route('upload_tar_file', '/upload_tar_file', request_method='POST')
    config.add_route('file_curate_menus', 'file_curate_menus', request_method='GET')
    config.add_route('get_file', '/get_file/{name}', request_method='GET')


    config.add_route('reserved_name_index', '/reservations', request_method='GET')
    config.add_route('reserved_name_curate_show', '/reservations/{id}', request_method='GET')
    config.add_route('reserved_name_update', '/reservations/{id}', request_method='PUT')
    config.add_route('reserved_name_standardize', '/reservations/{id}/standardize', request_method='POST')
    config.add_route('extend_reserved_name', '/reservations/{id}/extend', request_method='PUT')
    config.add_route('reserved_name_delete', '/reservations/{id}', request_method='DELETE')
    config.add_route('reserved_name_promote', '/reservations/{id}/promote', request_method='PUT')
    config.add_route('new_gene_name_reservation', '/reserve', request_method='POST')

    config.add_route('ptm_file_insert','/ptm_file',request_method='POST')
    config.add_route('get_strains','/get_strains',request_method='GET')
    config.add_route('get_psimod', '/get_psimod', request_method='GET')

    config.add_route('ptm_by_gene', '/ptm/{id}', request_method='GET')
    config.add_route('ptm_update', '/ptm', request_method='POST')
    config.add_route('ptm_delete','/ptm/{id}',request_method='DELETE')

    config.add_route('regulation_insert_update','/regulation', request_method='POST')
    config.add_route('get_all_eco_for_regulations','/eco/regulations', request_method='GET')
    config.add_route('regulations_by_filters','/get_regulations',request_method='POST')
    config.add_route('regulation_delete','/regulation/{id}', request_method='DELETE')
    config.add_route('regulation_file','/regulation_file',request_method='POST')
    config.add_route('triage_count','/triage_count',request_method='GET')
    config.add_route('get_apo','/get_apo/{namespace}',request_method='GET')
    config.add_route('get_observable','/get_observable',request_method='GET')
    config.add_route('get_allele','/get_allele',request_method='GET')
    config.add_route('get_reporter','/get_reporter',request_method='GET')
    config.add_route('get_chebi','/get_chebi',request_method='GET')
    config.add_route('get_eco','/get_eco',request_method='GET')
    config.add_route('get_publication_year','/get_publication_year',request_method='GET')
    config.add_route('get_curation_tag','/get_curation_tag',request_method='GET')
    config.add_route('get_literature_topic','/get_literature_topic',request_method='GET')
    config.add_route('get_papers_by_tag','/get_papers_by_tag/{tag}/{gene}/{year}',request_method='GET')
    config.add_route('literature_guide_update','/literature_guide_update', request_method='POST')
    config.add_route('literature_guide_add','/literature_guide_add', request_method='POST')

    config.add_route('get_obi','/get_obi',request_method='GET')
    config.add_route('get_all_datasets','/get_all_datasets',request_method='GET')
    config.add_route('get_dataset_data','/get_dataset_data/{format_name}',request_method='GET')
    config.add_route('get_datasets','/get_datasets/{query}',request_method='GET')
    config.add_route('dataset_update','/dataset_update', request_method='POST')
    config.add_route('datasetsample_update','/datasetsample_update', request_method='POST')
    config.add_route('datasettrack_update','/datasettrack_update', request_method='POST')
    config.add_route('dataset_load','/dataset_load', request_method='POST')
    config.add_route('datasetsample_load','/datasetsample_load', request_method='POST')
    config.add_route('dataset_delete','/dataset_delete', request_method='POST')
    config.add_route('datasetsample_delete','/datasetsample_delete', request_method='POST')
    config.add_route('datasettrack_delete','/datasettrack_delete', request_method='POST')
    
    config.add_route('get_phenotypes','/get_phenotypes/{gene}/{reference}', request_method='GET')
    config.add_route('get_phenotype','/get_phenotype/{annotation_id}/{group_id}', request_method='GET')
    config.add_route('phenotype_add','/phenotype_add', request_method='POST')
    config.add_route('phenotype_update','/phenotype_update', request_method='POST')
    config.add_route('phenotype_delete','/phenotype_delete', request_method='POST')

    config.add_route('get_allele_types','/get_allele_types', request_method='GET')
    config.add_route('get_alleles','/get_alleles/{allele_query}', request_method='GET')
    config.add_route('get_allele_data','/get_allele_data/{allele_format_name}', request_method='GET')
    config.add_route('allele_add','/allele_add', request_method='POST')
    config.add_route('allele_update','/allele_update', request_method='POST')
    config.add_route('allele_delete','/allele_delete', request_method='POST')

    config.add_route('get_edam','/get_edam/{namespace}',request_method='GET')
    config.add_route('get_readme','/get_readme',request_method='GET')
    config.add_route('get_path','/get_path',request_method='GET')
    config.add_route('get_file_metadata','/get_file_metadata/{query}', request_method='GET')
    config.add_route('get_one_file_metadata','/get_one_file_metadata/{sgdid}', request_method='GET')
    config.add_route('file_metadata_update','/file_metadata_update', request_method='POST')
    config.add_route('file_metadata_delete','/file_metadata_delete', request_method='POST')
    config.add_route('upload_suppl_file', '/upload_suppl_file', request_method='POST')
    
    config.add_route('disease_insert_update','/disease', request_method='POST')
    config.add_route('diseases_by_filters','/get_diseases',request_method='POST')
    config.add_route('disease_delete','/disease/{id}/{dbentity_id}', request_method='DELETE')
    config.add_route('disease_file', '/disease_file', request_method='POST')
    config.add_route('get_all_do','/do', request_method='GET')
    config.add_route('get_all_eco', '/eco', request_method='GET')

    config.add_route('complement_insert_update','/complement', request_method='POST')
    config.add_route('complements_by_filters','/get_complements',request_method='POST')
    config.add_route('complement_delete','/complement/{id}/{dbentity_id}', request_method='DELETE')
    config.add_route('complement_file', '/complement_file', request_method='POST')
    config.add_route('get_all_ro','/ro', request_method='GET')
    
    config.add_route('add_author_response','/add_author_response', request_method='POST')
    config.add_route('edit_author_response','/edit_author_response', request_method='POST')
    config.add_route('all_author_responses','/author_responses', request_method='GET')
    config.add_route('one_author_response', '/author_responses/{id}', request_method='GET')

    config.add_route('transfer_delete_reference_annotations','/reference/{id}/transfer_delete_reference_annotations', request_method='POST')
    config.add_route('get_reference_annotations','/reference_annotations/{id}',request_method='GET')
    config.add_route('delete_reference','/reference/{id}/delete_reference',request_method='DELETE')
    config.add_route('healthcheck', '/healthcheck')

    #swagger
    #config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('api_portal', '/api', request_method='GET')
    config.scan()
    config.add_static_view(name='assets', path='./build')

    return config.make_wsgi_app()
