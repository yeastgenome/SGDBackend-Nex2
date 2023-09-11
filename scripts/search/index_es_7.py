from src.models import DBSession, Base, Colleague, ColleagueLocus, Dbentity, \
    Locusdbentity, Filedbentity, FileKeyword, LocusAlias, Dnasequenceannotation, \
    So, Locussummary, Phenotypeannotation, PhenotypeannotationCond, Phenotype, \
    Regulationannotation, Posttranslationannotation, Goannotation, Go, Goslim, \
    Goslimannotation, Apo, Straindbentity, Functionalcomplementannotation, \
    Strainsummary, Reservedname, GoAlias, Goannotation, Referencedbentity, \
    Referencedocument, Referenceauthor, ReferenceAlias, Chebi, Disease, \
    Diseaseannotation, DiseaseAlias, Complexdbentity, ComplexAlias, \
    ComplexReference, Complexbindingannotation, Pathwaydbentity, \
    PathwayAlias, Pathwaysummary, PathwaysummaryReference, Pathwayannotation, \
    PathwayUrl, Tools, Alleledbentity, AlleleAlias, AllelealiasReference, \
    AlleleReference, LocusAllele, Literatureannotation
from sqlalchemy import create_engine, and_
from elasticsearch import Elasticsearch
# from mapping import mapping
from es7_mapping import mapping
import os
import requests
from threading import Thread
import json
import collections
from index_es_helpers import IndexESHelper
import concurrent.futures
import uuid
import logging


engine = create_engine(os.environ["NEX2_URI"], pool_recycle=3600)
DBSession.configure(bind=engine)
Base.metadata.bind = engine

INDEX_NAME = os.environ.get("ES_INDEX_NAME", "searchable_items_aws")
DOC_TYPE = "searchable_item"
ES_URI = os.environ["WRITE_ES_URI"]
es = Elasticsearch(ES_URI, retry_on_timeout=True)


def delete_mapping():
    print("Deleting mapping...")
    response = requests.delete(ES_URI + INDEX_NAME + "/")
    if response.status_code != 200:
        print(("ERROR: " + str(response.json())))
    else:
        print("SUCCESS")


def put_mapping():
    print("Putting mapping... ")
    try:
        response = requests.put(ES_URI + INDEX_NAME + "/", json=mapping)
        if response.status_code != 200:
            print(("ERROR: " + str(response.json())))
        else:
            print("SUCCESS")
    except Exception as e:
        print(e)


def cleanup():
    delete_mapping()
    put_mapping()


def setup():
    # see if index exists, if not create it
    indices = list(es.indices.get_alias().keys())
    index_exists = INDEX_NAME in indices
    if not index_exists:
        put_mapping()


def index_not_mapped_genes():
    url = "https://downloads.yeastgenome.org/curation/literature/genetic_loci.tab"
    bulk_data = []
    with open("./scripts/search/not_mapped.json",
              "r") as json_data:
        _data = json.load(json_data)
        print(("indexing " + str(len(_data)) + " not physically mapped genes"))
        for item in _data:
            temp_aliases = []
            if len(item["FEATURE_NAME"]) > 0:
                obj = {
                    "name": item["FEATURE_NAME"],
                    "locus_name": item["FEATURE_NAME"],
                    "unmapped_name": item["FEATURE_NAME"],
                    "href": url,
                    "category": "locus",
                    "feature_type": ["Unmapped Genetic Loci"],
                    "aliases": item["ALIASES"].split("|"),
                    "description": item["DESCRIPTION"],
                    "is_quick_flag": "False"
                }
                bulk_data.append({
                    "index": {
                        "_index": INDEX_NAME,
                        "_id": str(uuid.uuid4())
                    }
                })
                bulk_data.append(obj)
                if len(bulk_data) == 300:
                    es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
                    bulk_data = []

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_downloads():
    bulk_data = []
    dbentity_file_obj = IndexESHelper.get_file_dbentity_keyword()
    files = DBSession.query(Filedbentity).filter(Filedbentity.is_public == True,
                                                 Filedbentity.s3_url != None).all()
    print(("indexing " + str(len(files)) + " download files"))
    for x in files:
        try:
            keyword = []
            status = ""
            temp = dbentity_file_obj.get(x.dbentity_id)
            if temp:
                keyword = temp
            if (x.dbentity_status == "Active" or x.dbentity_status == "Archived"):
                if x.dbentity_status == "Active":
                    status = "Active"
                else:
                    status = "Archived"

            obj = {
                "name":
                    x.display_name,
                "raw_display_name":
                    x.display_name,
                "filename": " ".join(x.display_name.split("_")),
                "file_name_format": " ".join(x.display_name.split("_")),
                "href": x.s3_url if x else None,
                "category":
                    "download",
                "description":
                    x.description,
                "keyword":
                    keyword,
                "format":
                    str(x.format.display_name),
                "status":
                    str(status),
                "file_size":
                    str(IndexESHelper.convertBytes(x.file_size))
                    if x.file_size is not None else x.file_size,
                "year":
                    str(x.year),
                "readme_url": x.readme_file.s3_url if x.readme_file else None,
                "topic": x.topic.display_name,
                "data": x.data.display_name,
                "path_id": x.get_path_id()
            }

            bulk_data.append({
                "index": {
                    "_index": INDEX_NAME,
                    "_id": str(uuid.uuid4())
                }
            })

            bulk_data.append(obj)
            if len(bulk_data) == 50:
                es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
                bulk_data = []

        except Exception as e:
            logging.error(e.message)

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_colleagues():
    colleagues = DBSession.query(Colleague).all()
    _locus_ids = IndexESHelper.get_colleague_locus()
    _locus_names = IndexESHelper.get_colleague_locusdbentity()
    _combined_list = IndexESHelper.combine_locusdbentity_colleague(
        colleagues, _locus_names, _locus_ids)
    print(("Indexing " + str(len(colleagues)) + " colleagues"))
    bulk_data = []
    for item_k, item_v in list(_combined_list.items()):
        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                "_id": str(uuid.uuid4())
            }
        })

        bulk_data.append(item_v)
        if len(bulk_data) == 1000:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []
    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_genes():
    # Indexing just the S228C genes
    # dbentity: 1364643 (id) -> straindbentity -> 274901 (taxonomy_id)
    # list of dbentities comes from table DNASequenceAnnotation with taxonomy_id 274901
    # feature_type comes from DNASequenceAnnotation as well
    gene_ids_so = DBSession.query(
        Dnasequenceannotation.dbentity_id, Dnasequenceannotation.so_id).filter(
            Dnasequenceannotation.taxonomy_id == 274901).all()
    dbentity_ids_to_so = {}
    dbentity_ids = set([])
    so_ids = set([])
    for gis in gene_ids_so:
        dbentity_ids.add(gis[0])
        so_ids.add(gis[1])
        dbentity_ids_to_so[gis[0]] = gis[1]
    # add some non S288C genes
    not_s288c = DBSession.query(Locusdbentity.dbentity_id).filter(
        Locusdbentity.not_in_s288c == True).all()
    for id in not_s288c:
        dbentity_ids.add(id[0])
        # assume non S288C features to be ORFs
        dbentity_ids_to_so[id[0]] = 263757
    all_genes = DBSession.query(Locusdbentity).filter(
        Locusdbentity.dbentity_id.in_(list(dbentity_ids))).all()

    # make list of merged/deleted genes so they don"t redirect when they show up as an alias
    merged_deleted_r = DBSession.query(Locusdbentity.format_name).filter(
        Locusdbentity.dbentity_status.in_(["Merged", "Deleted"])).all()
    merged_deleted = [d[0] for d in merged_deleted_r]

    feature_types_db = DBSession.query(
        So.so_id, So.display_name).filter(So.so_id.in_(list(so_ids))).all()
    feature_types = {}
    for ft in feature_types_db:
        feature_types[ft[0]] = ft[1]

    tc_numbers_db = DBSession.query(LocusAlias).filter_by(
        alias_type="TC number").all()
    tc_numbers = {}
    for tc in tc_numbers_db:
        if tc.locus_id in tc_numbers:
            tc_numbers[tc.locus_id].append(tc.display_name)
        else:
            tc_numbers[tc.locus_id] = [tc.display_name]

    ec_numbers_db = DBSession.query(LocusAlias).filter_by(
        alias_type="EC number").all()
    ec_numbers = {}
    for ec in ec_numbers_db:
        if ec.locus_id in ec_numbers:
            ec_numbers[ec.locus_id].append(ec.display_name)
        else:
            ec_numbers[ec.locus_id] = [ec.display_name]

    secondary_db = DBSession.query(LocusAlias).filter_by(
        alias_type="SGDID Secondary").all()
    secondary_sgdids = {}

    for sid in secondary_db:
        if sid.locus_id in secondary_sgdids:
            secondary_sgdids[sid.locus_id].append(sid.display_name)
        else:
            secondary_sgdids[sid.locus_id] = [sid.display_name]

    bulk_data = []

    print(("Indexing " + str(len(all_genes)) + " genes"))
    ##### test newer methods ##########
    _summary = IndexESHelper.get_locus_dbentity_summary()
    _protein = IndexESHelper.get_locus_dbentity_alias(["NCBI protein name"])
    _phenos = IndexESHelper.get_locus_phenotypeannotation()
    _goids = IndexESHelper.get_locus_go_annotation()
    _aliases_raw = IndexESHelper.get_locus_dbentity_alias(
        ["Uniform", "Non-uniform", "Retired name", "UniProtKB ID"])

    ###################################
    # TODO: remove line below in the next release
    # not_mapped_genes = IndexESHelper.get_not_mapped_genes()
    is_quick_flag = True

    for gene in all_genes:
        _systematic_name = ''
        _name = ''
        if gene.gene_name:
            _name = gene.gene_name
            if gene.systematic_name and gene.gene_name != gene.systematic_name:
                _name += " / " + gene.systematic_name
        else:
            _name = gene.systematic_name
            _systematic_name = gene.systematic_name

        #summary = DBSession.query(Locussummary.text).filter_by(locus_id=gene.dbentity_id).all()
        summary = []
        if (_summary is not None):
            summary = _summary.get(gene.dbentity_id)
        #protein = DBSession.query(LocusAlias.display_name).filter_by(locus_id=gene.dbentity_id, alias_type="NCBI protein name").one_or_none()
        protein = _protein.get(gene.dbentity_id)
        if protein is not None:
            protein = protein[0].display_name

        # TEMP don"t index due to schema schange
        # sequence_history = DBSession.query(Locusnoteannotation.note).filter_by(dbentity_id=gene.dbentity_id, note_type="Sequence").all()
        # gene_history = DBSession.query(Locusnoteannotation.note).filter_by(dbentity_id=gene.dbentity_id, note_type="Locus").all()

        #phenotype_ids = DBSession.query(Phenotypeannotation.phenotype_id).filter_by(dbentity_id=gene.dbentity_id).all()
        phenotype_ids = []
        if _phenos is not None:
            temp = _phenos.get(gene.dbentity_id)
            if temp is not None:
                phenotype_ids = [x.phenotype_id for x in temp]
        if len(phenotype_ids) > 0:
            phenotypes = DBSession.query(Phenotype.display_name).filter(
                Phenotype.phenotype_id.in_(phenotype_ids)).all()
        else:
            phenotypes = []
        #go_ids = DBSession.query(Goannotation.go_id).filter(and_(Goannotation.go_qualifier != "NOT", Goannotation.dbentity_id == gene.dbentity_id)).all()
        go_ids = _goids.get(gene.dbentity_id)
        if go_ids is not None:
            go_ids = [x.go_id for x in go_ids]
        else:
            go_ids = []
        go_annotations = {
            "cellular component": set([]),
            "molecular function": set([]),
            "biological process": set([])
        }
        if len(go_ids) > 0:
            #go_ids = [g[0] for g in go_ids]
            go = DBSession.query(
                Go.display_name,
                Go.go_namespace).filter(Go.go_id.in_(go_ids)).all()
            for g in go:
                go_annotations[g[1]].add(g[0] + " (direct)")
        go_slim_ids = DBSession.query(Goslimannotation.goslim_id).filter(
            Goslimannotation.dbentity_id == gene.dbentity_id).all()
        if len(go_slim_ids) > 0:
            go_slim_ids = [g[0] for g in go_slim_ids]
            go_slim = DBSession.query(Goslim.go_id, Goslim.display_name).filter(
                Goslim.goslim_id.in_(go_slim_ids)).all()
            go_ids = [g[0] for g in go_slim]
            go = DBSession.query(
                Go.go_id, Go.go_namespace).filter(Go.go_id.in_(go_ids)).all()
            for g in go:
                for gs in go_slim:
                    if (gs[0] == g[0]):
                        go_annotations[g[1]].add(gs[1])

        # add "quick direct" keys such as aliases, SGD, UniProt ID and format aliases
        #aliases_raw = DBSession.query(LocusAlias.display_name, LocusAlias.alias_type).filter(and_(LocusAlias.locus_id==gene.dbentity_id, LocusAlias.alias_type.in_())).all()
        aliases_raw = _aliases_raw.get(gene.dbentity_id)
        alias_quick_direct_keys = []
        aliases = []
        if aliases_raw is not None:
            for alias_item in aliases_raw:
                name = alias_item.display_name
                if name not in merged_deleted:
                    alias_quick_direct_keys.append(name)
                if alias_item.alias_type != "UniProtKB ID":
                    aliases.append(name)
        '''for d in aliases_raw:
            name = d[0]
            if name not in merged_deleted:
                alias_quick_direct_keys.append(name)
            if d[1] != "UniProtKB ID":
                aliases.append(name)'''
        # make everything in keys lowercase to ignore case
        keys = []
        _keys = [gene.gene_name, gene.systematic_name, gene.sgdid
                 ] + alias_quick_direct_keys
        # Add SGD:<gene SGDID> to list of keywords for quick search
        _keys.append("SGD:{}".format(gene.sgdid))
        # If this gene has a reservedname associated with it, add that reservedname to
        # the list of keywords used for the quick search of this gene
        reservedname = DBSession.query(Reservedname).filter_by(
            locus_id=gene.dbentity_id).one_or_none()
        if reservedname:
            _keys.append(reservedname.display_name)
        for k in _keys:
            if k:
                keys.append(k.lower())
        
        ncbi_arr = None
        if gene.dbentity_id:
            ncbi_arr = IndexESHelper.get_locus_ncbi_data(gene.dbentity_id)
        obj = {
            "name":
                _name,
            "locus_name":
                _name,
            "sys_name":
                _systematic_name,
            "href":
                gene.obj_url,
            "description":
                gene.description,
            "category":
                "locus",
            "feature_type":
                feature_types[dbentity_ids_to_so[gene.dbentity_id]],
            "name_description":
                gene.name_description,
            "summary":
                summary,
            "locus_summary":
                summary,
            "phenotypes": [p[0] for p in phenotypes],
            "aliases":
                aliases,
            "cellular_component":
                list(go_annotations["cellular component"] - set([
                    "cellular component", "cellular component (direct)",
                    "cellular_component", "cellular_component (direct)"
                ])),
            "biological_process":
                list(go_annotations["biological process"] - set([
                    "biological process (direct)", "biological process",
                    "biological_process (direct)", "biological_process"
                ])),
            "molecular_function":
                list(go_annotations["molecular function"] - set([
                    "molecular function (direct)", "molecular function",
                    "molecular_function (direct)", "molecular_function"
                ])),
            "ec_number":
                ec_numbers.get(gene.dbentity_id),
            "protein":
                protein,
            "tc_number":
                tc_numbers.get(gene.dbentity_id),
            "secondary_sgdid":
                secondary_sgdids.get(gene.dbentity_id),
            "status":
                gene.dbentity_status,
            # TEMP don"t index due to schema change
            # "sequence_history": [s[0] for s in sequence_history],
            # "gene_history": [g[0] for g in gene_history],
            "bioentity_id":
                gene.dbentity_id,
            "keys":
                list(keys),
            "is_quick_flag": str(is_quick_flag),
            "ncbi": ncbi_arr
        }

        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                "_id": str(uuid.uuid4())
            }
        })
        bulk_data.append(obj)

        if len(bulk_data) == 1000:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_phenotypes():
    bulk_data = []
    phenotypes = DBSession.query(Phenotype).all()
    _result = IndexESHelper.get_pheno_annotations(phenotypes)
    print(("Indexing " + str(len(_result)) + " phenotypes"))
    for phenotype_item in _result:
        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                
                "_id": str(uuid.uuid4())
            }
        })
        bulk_data.append(phenotype_item)
        if len(bulk_data) == 50:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []
    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_observables():
    observables = DBSession.query(Apo).filter_by(
        apo_namespace="observable").all()

    print(("Indexing " + str(len(observables)) + " observables"))
    bulk_data = []

    for observable in observables:
        obj = {
            "name": observable.display_name,
            "observable_name": observable.display_name,
            "href": observable.obj_url,
            "description": observable.description,
            "category": "observable",
            "keys": []
        }

        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                
                "_id": str(uuid.uuid4())
            }
        })

        bulk_data.append(obj)

        if len(bulk_data) == 300:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_strains_old():
    strains = DBSession.query(Straindbentity).all()

    print(("Indexing " + str(len(strains)) + " strains"))
    for strain in strains:
        key_values = [
            strain.display_name, strain.format_name, strain.genbank_id
        ]

        keys = set([])
        for k in key_values:
            if k is not None:
                keys.add(k.lower())

        paragraph = DBSession.query(Strainsummary.text).filter_by(
            strain_id=strain.dbentity_id).one_or_none()
        description = None
        if paragraph:
            description = paragraph[0]

        obj = {
            "name": strain.display_name,
            "strain_name": strain.display_name,
            "href": strain.obj_url,
            "description": strain.headline,
            "category": "strain",
            "keys": list(keys)
        }

        es.index(
            index=INDEX_NAME,  body=obj, id=str(uuid.uuid4()))


def index_reserved_names():
    # only index reservednames that do not have a locus associated with them
    reserved_names = DBSession.query(Reservedname).all()

    print(("Indexing " + str(len(reserved_names)) + " reserved names"))
    for reserved_name in reserved_names:
        name = reserved_name.display_name
        href = reserved_name.obj_url
        keys = [reserved_name.display_name.lower()]
        # change name if has an orf
        if reserved_name.locus_id:
            locus = DBSession.query(Locusdbentity).filter(
                Locusdbentity.dbentity_id == reserved_name.locus_id).one_or_none()
            name = name + " / " + locus.systematic_name
            href = locus.obj_url
            keys = []
        obj = {
            "name": name,
            "reserved_name": name,
            "href": href,
            "description": reserved_name.name_description,
            "category": "reserved_name",
            "keys": keys
        }
        es.index(
            index=INDEX_NAME, body=obj, id=str(uuid.uuid4()))


def load_go_id_blacklist(list_filename):
    go_id_blacklist = set()
    for l in open(list_filename, "r"):
        go_id_blacklist.add(l[:-1])
    return go_id_blacklist


def index_go_terms():
    go_id_blacklist = load_go_id_blacklist(
        "scripts/search/go_id_blacklist.lst")

    gos = DBSession.query(Go).all()

    print(("Indexing " + str(len(gos) - len(go_id_blacklist)) + " GO terms"))

    bulk_data = []
    for go in gos:
        if go.goid in go_id_blacklist:
            continue

        synonyms = DBSession.query(GoAlias.display_name).filter_by(
            go_id=go.go_id).all()

        references = set([])
        gene_ontology_loci = set([])
        annotations = DBSession.query(Goannotation).filter_by(
            go_id=go.go_id).all()
        for annotation in annotations:
            if annotation.go_qualifier != "NOT":
                gene_ontology_loci.add(annotation.dbentity.display_name)
            references.add(annotation.reference.display_name)

        numerical_id = go.goid.split(":")[1]
        key_values = [
            go.goid, "GO:" + str(int(numerical_id)), numerical_id,
            str(int(numerical_id))
        ]

        keys = set([])
        for k in key_values:
            if k is not None:
                keys.add(k.lower())

        obj = {
            "name": go.display_name,
            "identifier": go.goid,
            "go_name": go.display_name,
            "href": go.obj_url,
            "description": go.description,
            "synonyms": [s[0] for s in synonyms],
            "go_id": go.goid,
            "gene_ontology_loci": sorted(list(gene_ontology_loci)),
            "number_annotations": len(annotations),
            "references": list(references),
            "category": go.go_namespace.replace(" ", "_"),
            "keys": list(keys)
        }

        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                
                "_id": str(uuid.uuid4())
            }
        })

        bulk_data.append(obj)

        if len(bulk_data) == 800:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_disease_terms():
    dos = DBSession.query(Disease).all()

    print(("Indexing " + str(len(dos)) + " DO terms"))

    bulk_data = []
    for do in dos:
        synonyms = DBSession.query(DiseaseAlias.display_name).filter_by(
            disease_id=do.disease_id).all()
        references = set([])
        disease_loci = set([])
        annotations = DBSession.query(Diseaseannotation).filter_by(
            disease_id=do.disease_id).all()
        for annotation in annotations:
            if annotation.disease_qualifier != "NOT":
                disease_loci.add(annotation.dbentity.display_name)
            references.add(annotation.reference.display_name)
        if do.doid != 'derives_from':
            numerical_id = do.doid.split(":")[1]
        key_values = [
            do.doid, "DO:" + str(int(numerical_id)), numerical_id,
            str(int(numerical_id))
        ]

        keys = set([])
        for k in key_values:
            if k is not None:
                keys.add(k.lower())
        obj = {
            "name": do.display_name,
            "identifier": do.doid,
            "disease_name": do.display_name,
            "category": "disease",
            "href": do.obj_url,
            "description": do.description,
            "synonyms": [s[0] for s in synonyms],
            "doid": do.doid,
            "disease_loci": sorted(list(disease_loci)),
            "number_annotations": len(annotations),
            "references": list(references),
            "keys": list(keys)
        }

        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                
                "_id": str(uuid.uuid4())
            }
        })

        bulk_data.append(obj)

        if len(bulk_data) == 800:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_strains():

    ## strains with taxonomy_id = 274803; same as 'Other' strain
    other_strains = [ "A364A", "AB972", "DC5", "Foster's B",
                      "Foster's O", "XJ24-24a", ]
    
    strains = DBSession.query(Straindbentity).all()

    print(("Indexing " + str(len(strains)) + " strains"))
            
    i = 0
    bulk_data = []
    for s in strains:
        key_values = [s.display_name, s.format_name, s.genbank_id ]
        keys = set([])
        for k in key_values:
            if k is not None:
                keys.add(k.lower())
                                                    
        i += 1
        
        taxonomy_id = s.taxonomy_id
        strain_link_url = s.obj_url
        description = s.headline
        display_name = s.display_name

        """
        phenotypes = set([])
        references = set([])
        diseases = set([])

        if s.display_name not in other_strains:

            for x in DBSession.query(Phenotypeannotation).filter_by(taxonomy_id=taxonomy_id).all():
                references.add(x.reference.display_name)
                phenotypes.add(x.phenotype.display_name)
            
            for x in DBSession.query(Posttranslationannotation).filter_by(taxonomy_id=taxonomy_id).all():
                references.add(x.reference.display_name)

            for x in DBSession.query(Regulationannotation).filter_by(taxonomy_id=taxonomy_id).all():
                references.add(x.reference.display_name)

            for x in DBSession.query(Regulationannotation).filter_by(taxonomy_id=taxonomy_id).all():
                references.add(x.reference.display_name)

            for x in DBSession.query(Functionalcomplementannotation).filter_by(taxonomy_id=taxonomy_id).all():
                references.add(x.reference.display_name)
                
            for x in DBSession.query(Diseaseannotation).filter_by(taxonomy_id = taxonomy_id).all():
                references.add(x.reference.display_name)
                diseases.add(x.disease.display_name)

        """
        
        # print(s.display_name, "references=", len(references), "phenotypes=", len(phenotypes), "diseases=", len(diseases))
        
        obj = {
            "name": display_name,
            "strain_name": display_name,
            "category": "strain",
            "href": strain_link_url,
            "description": description
        }
        """
            "references": list(references),
            "phenotype": sorted(list(phenotypes)),
            "disease": sorted(list(diseases))
        }
        """
        
        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                "_id": str(uuid.uuid4())
            }
        })
        bulk_data.append(obj)
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
        bulk_data = []


def get_references_for_strains(taxonomy_id_to_strain_name):

    regulations = DBSession.query(Regulationannotation).filter_by(
        annotation_type = "manually curated").all()

    diseases = DBSession.query(Diseaseannotation).all()

    ptms = DBSession.query(Posttranslationannotation).all()

    funcComplements = DBSession.query(Functionalcomplementannotation).all()

    phenotypes = DBSession.query(Phenotypeannotation).all()
    
    ref2strains = {}
    for x in regulations + diseases + ptms + funcComplements + phenotypes:
        strains = []
        if x.reference_id in ref2strains:
            strains = ref2strains[x.reference_id]
        strain = taxonomy_id_to_strain_name.get(x.taxonomy_id)
        if strain is not None and strain not in strains:
            strains.append(strain)
        ref2strains[x.reference_id] = strains

    return ref2strains


def index_references():
    # _ref_loci = IndexESHelper.get_dbentity_locus_note()
    _references = DBSession.query(Referencedbentity).all()
    _abstracts = IndexESHelper.get_ref_abstracts()
    _authors = IndexESHelper.get_ref_authors()
    _aliases = IndexESHelper.get_ref_aliases()

    main_strain_list = ["S288C", "W303", "Sigma1278b", "SK1",
                        "SEY6210", "X2180-1A", "CEN.PK", "D273-10B",
                        "JK9-3d", "FL100", "Y55", "RM11-1a"]
    taxonomy_id_to_strain_name = {}
    for x in DBSession.query(Straindbentity).all():
        if x.display_name in main_strain_list:
            taxonomy_id_to_strain_name[x.taxonomy_id] = x.display_name

    ref2strains = get_references_for_strains(taxonomy_id_to_strain_name)
    
    all = DBSession.query(Literatureannotation).all()
    ref2loci = {}
    ref2complexes = {}
    ref2alleles = {}
    ref2pathways = {}
    for x in all:
        if x.dbentity is None:
            continue
        if x.dbentity.subclass == 'LOCUS':
            loci = []
            if x.reference_id in ref2loci:
                loci = ref2loci[x.reference_id]
            if x.dbentity.display_name not in loci:
                loci.append(x.dbentity.display_name)
            ref2loci[x.reference_id] = loci
        elif x.dbentity.subclass == 'COMPLEX':
            complexes = []
            if x.reference_id in ref2complexes:
                complexes = ref2complexes[x.reference_id]
            if x.dbentity.display_name not in complexes:
                complexes.append(x.dbentity.display_name)
            ref2complexes[x.reference_id] = complexes
        elif x.dbentity.subclass == 'ALLELE':
            alleles = []
            if x.reference_id in ref2alleles:
                alleles = ref2alleles[x.reference_id]
            if x.dbentity.display_name not in alleles:
                alleles.append(x.dbentity.display_name)
            ref2alleles[x.reference_id] = alleles
        elif x.dbentity.subclass == 'PATHWAY':
            pathways = []
            if x.reference_id in ref2pathways:
                pathways = ref2pathways[x.reference_id]
            if x.dbentity.display_name not in pathways:
                pathways.append(x.dbentity.display_name)
            ref2pathways[x.reference_id] = pathways
            
    bulk_data = []
    print(("Indexing " + str(len(_references)) + " references"))

    for reference in _references:
        reference_loci = []
        reference_complexes = []
        reference_alleles = []
        reference_pathways = []
        reference_strains = []
        # if len(_ref_loci) > 0:
        #    temp_loci = _ref_loci.get(reference.dbentity_id)
        #    if temp_loci is not None:
        #        reference_loci = list(
        #            set([x.display_name for x in IndexESHelper.flattern_list(temp_loci)]))
        temp_loci = ref2loci.get(reference.dbentity_id)
        if temp_loci is not None:
            reference_loci = temp_loci
            
        temp_complexes = ref2complexes.get(reference.dbentity_id)
        if temp_complexes is not None:
            reference_complexes = temp_complexes

        temp_alleles = ref2alleles.get(reference.dbentity_id)
        if temp_alleles is not None:
            reference_alleles= temp_alleles
            
        temp_pathways = ref2pathways.get(reference.dbentity_id)
        if temp_pathways is not None:
            reference_pathways = temp_pathways

        temp_strains = ref2strains.get(reference.dbentity_id)
        if temp_strains is not None:
            reference_strains = temp_strains

        abstract = _abstracts.get(reference.dbentity_id)
        if abstract is not None:
            abstract = abstract[0]
        sec_sgdids = _aliases.get(reference.dbentity_id)
        sec_sgdid = None
        authors = _authors.get(reference.dbentity_id)
        if sec_sgdids is not None:
            sec_sgdid = sec_sgdids[0]

        if authors is None:
            authors = []

        journal = reference.journal
        if journal:
            journal = journal.display_name
        key_values = [
            reference.pmcid, reference.pmid, "pmid: " + str(reference.pmid),
            "pmid:" + str(reference.pmid), "pmid " + str(reference.pmid),
            reference.sgdid
        ]

        keys = set([])
        for k in key_values:
            if k is not None:
                keys.add(str(k).lower())

        name = ', '.join(authors) + ' (' + ' '.join(reference.citation.split('(')[1:])
        
        pmid = ''
        if reference.pmid:
            pmid = str(reference.pmid)
        obj = {
            "name": name,
            "identifier": pmid,
            "reference_name": reference.citation,
            "href": reference.obj_url,
            "description": abstract,
            "author": authors,
            "journal": journal,
            "year": str(reference.year),
            "reference_loci": reference_loci,
            "associated_alleles": reference_alleles,
            "associated_complexes": reference_complexes,
            "associated_pathways": reference_pathways,
            "associated_strains": reference_strains,
            "secondary_sgdid": sec_sgdid,
            "category": "reference",
            "keys": list(keys)
        }

        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                
                "_id": str(uuid.uuid4())
            }
        })
        bulk_data.append(obj)
        if len(bulk_data) == 1000:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_pathways():
    pathways = DBSession.query(Pathwaydbentity).all()
    print(("Indexing " + str(len(pathways)) + " pathways"))

    bulk_data = []

    pathway_id_to_summary  = dict([(x.pathway_id, (x.summary_id, x.text)) \
                                   for x in DBSession.query(Pathwaysummary).all()])

    for p in pathways:
        if p.dbentity_status == 'Deleted':
            continue
        synonyms = DBSession.query(PathwayAlias.display_name).filter_by(
            pathway_id=p.dbentity_id).all()
        
        summary_id = None
        summary_text = ''
        if p.dbentity_id in pathway_id_to_summary:
            (summary_id, summary_text) = pathway_id_to_summary[p.dbentity_id]
        
        references = set([])
        if summary_id is not None:
            refs = DBSession.query(PathwaysummaryReference).filter_by(
                summary_id=summary_id).all()
            for ref in refs:
                references.add(ref.reference.display_name)

        pathway_loci = set([])
        annotations = DBSession.query(Pathwayannotation).filter_by(
            pathway_id=p.dbentity_id).all()
        for a in annotations:
            pathway_loci.add(a.dbentity.display_name)

        bioCycURL = None
        yeastPathwayURL = None
        for x in DBSession.query(PathwayUrl).filter_by(pathway_id=p.dbentity_id).all():
            if x.url_type == 'BioCyc':
                bioCycURL = x.obj_url
            elif x.url_type == 'YeastPathways':
                yeastPathwayURL = x.obj_url
            
        keys = [p.biocyc_id, p.biocyc_id.lower()]
        obj = {
            "name": p.display_name,
            "identifier": p.biocyc_id,
            "pathway_name": p.display_name,
            "biocyc_id": p.biocyc_id,
            "href": yeastPathwayURL,
            "description": summary_text,
            "category": "pathway",
            "synonyms": [s[0] for s in synonyms],
            "pathway_loci": sorted(list(pathway_loci)),
            "references": list(references),
            "keys": keys
        }

        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                "_id": str(uuid.uuid4())
            }
        })

        bulk_data.append(obj)

        if len(bulk_data) == 800:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)

        
def index_complex_names():
    complexes = DBSession.query(Complexdbentity).all()
    print(("Indexing " + str(len(complexes)) + " complex names"))

    bulk_data = []

    for c in complexes:

        if c.dbentity_status == 'Deleted':
            continue
        
        synonyms = DBSession.query(ComplexAlias.display_name).filter_by(
            complex_id=c.dbentity_id).all()

        references = set([])
        refs = DBSession.query(ComplexReference).filter_by(
            complex_id=c.dbentity_id).all()
        for ref in refs:
            references.add(ref.reference.display_name)
            
        all_goannots = DBSession.query(Goannotation).filter_by(
                        dbentity_id=c.dbentity_id).all()
        process = set([])
        component = set([])
        function = set([])
        for x in all_goannots:
            if x.go.go_namespace == 'biological process':
                process.add(x.go.display_name)
            elif x.go.go_namespace == 'cellular component':
                component.add(x.go.display_name)
            else:
                function.add(x.go.display_name)
            
        complex_loci = set([])
        annotations = DBSession.query(Complexbindingannotation).filter_by(
            complex_id=c.dbentity_id).all()
        for a in annotations:
            interactor = a.interactor
            if interactor.locus_id is not None:
                complex_loci.add(interactor.locus.display_name)

        key_values = [
            c.intact_id, c.complex_accession, c.sgdid
        ]

        keys = set([])
        for k in key_values:
            if k is not None:
                keys.add(k.lower())

        obj = {
            "name": c.display_name,
            "identifier": c.complex_accession,
            "complex_name": c.display_name,
            "href": "/complex/" + c.complex_accession,
            "description": c.description + "; " + c.properties,
            "category": "complex",
            "synonyms": [s[0] for s in synonyms],
            "systematic_name": c.systematic_name,
            "intact_id": c.intact_id,
            "complex_accession": c.complex_accession,
            "complex_loci": sorted(list(complex_loci)),
            "cellular_component": sorted(list(component)),
            "biological_process": sorted(list(process)),
            "molecular_function": sorted(list(function)),
            "references": list(references),
            "keys": list(keys)
        }

        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                "_id": str(uuid.uuid4())
            }
        })

        bulk_data.append(obj)

        if len(bulk_data) == 800:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_alleles():

    so_id_to_term = dict([(x.so_id, x.display_name) for x in DBSession.query(So).all()])
    
    alleles = DBSession.query(Alleledbentity).all()
    
    print(("Indexing " + str(len(alleles)) + " allele names"))

    bulk_data = []

    for a in alleles:
        
        synonyms = DBSession.query(AlleleAlias.display_name).filter_by(allele_id=a.dbentity_id).all()

        allele_types = set([])
        allele_types.add(so_id_to_term.get(a.so_id))
        
        references = set([])
        for x in DBSession.query(Literatureannotation).filter_by(dbentity_id=a.dbentity_id).all():
            if x.reference.display_name not in references:
                references.add(x.reference.display_name)
            
        phenotypes = set([])
        allele_loci = set([])
        for x in DBSession.query(Phenotypeannotation).filter_by(allele_id=a.dbentity_id).all():
            if x.phenotype.display_name not in phenotypes:
                phenotypes.add(x.phenotype.display_name)
            if x.dbentity.display_name not in allele_loci:
                allele_loci.add(x.dbentity.display_name)

        for x in DBSession.query(LocusAllele).filter_by(allele_id=a.dbentity_id).all():
            if x.locus.display_name not in allele_loci:
                allele_loci.add(x.locus.display_name)
                
        obj = {
            "name": a.display_name,
            "allele_name": a.display_name,
            "href": "/allele/" + a.format_name,
            "allele_description": a.description,
            "category": "Allele",
            "synonyms": [s[0] for s in synonyms],
            "allele_types": list(allele_types),
            "references": list(references),
            "phenotypes": sorted(list(phenotypes)),
            "allele_loci": sorted(list(allele_loci))
        }

        bulk_data.append({
            "index": {
                "_index": INDEX_NAME,
                "_id": str(uuid.uuid4())
            }
        })

        bulk_data.append(obj)

        if len(bulk_data) == 800:
            es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
            bulk_data = []

    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_chemicals():
    all_chebi_data = DBSession.query(Chebi).all()
    _result = IndexESHelper.get_chebi_annotations(all_chebi_data)
    bulk_data = []
    print(("Indexing " + str(len(all_chebi_data)) + " chemicals"))
    for item_key, item_v in list(_result.items()):
        if item_v is not None:
            obj = {
                "name": item_v.display_name,
                "identifier": item_v.chebiid,
                "chemical_name": item_v.display_name,
                "href": item_v.obj_url,
                "description": item_v.description,
                "category": "chemical",
                "keys": [],
                "chebiid": item_v.chebiid
            }
            bulk_data.append({
                "index": {
                    "_index": INDEX_NAME,
                    
                    "_id": "chemical_" + str(item_key)
                }
            })

            bulk_data.append(obj)
            if len(bulk_data) == 300:
                es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)
                bulk_data = []
    if len(bulk_data) > 0:
        es.bulk(index=INDEX_NAME, body=bulk_data, refresh=True)


def index_part_1():
    index_strains()
    index_references()
    index_phenotypes()
    index_not_mapped_genes()
    index_colleagues()

    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        index_downloads()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        index_genes()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        index_chemicals()


def index_part_2():
    index_pathways()
    index_reserved_names()
    index_toolbar_links()
    index_observables()
    index_disease_terms()
    # index_references()
    index_alleles()
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        index_go_terms()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        index_complex_names()
    
        
def index_toolbar_links():

    tools = DBSession.query(Tools).all()
    
    print(("Indexing " + str(len(tools)) + " toolbar links"))

    for x in tools:
        keys = []
        if x.index_key:
            keys = x.index_key
        obj = {
            "name": x.display_name,
            "resource_name": x.display_name,
            "href": x.link_url,
            "description": None,
            "category": "resource",
            "keys": keys
        }
        es.index(index=INDEX_NAME, body=obj, id=x.link_url)


if __name__ == "__main__":
    '''
        To run multi-processing add this: 
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
            index_references()
    '''
    
    cleanup()
    setup()

    # index_strains()
    # index_references()

    t1 = Thread(target=index_part_1)
    t2 = Thread(target=index_part_2)
    t1.start()
    t2.start()
    
