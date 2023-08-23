from sqlalchemy import Column, BigInteger, UniqueConstraint, Float, Boolean, SmallInteger, Integer, DateTime, ForeignKey, Index, Numeric, String, Text, text, FetchedValue, func, or_, and_, distinct, inspect
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
# from zope.sqlalchemy import ZopeTransactionExtension
from zope.sqlalchemy import register
from elasticsearch import Elasticsearch
import os
import io
from math import floor, log
import json
import copy
import requests
import re
import traceback
import transaction
import logging
from datetime import datetime, timedelta
from itertools import groupby
import hashlib
import urllib.request, urllib.parse, urllib.error
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from src.curation_helpers import ban_from_cache, get_author_etc, link_gene_names, get_curator_session, clear_list_empty_values
from scripts.loading.util import link_gene_complex_names

from src.boto3_upload import upload_one_file_to_s3

DBSession = scoped_session(sessionmaker(autoflush=False))
register(DBSession)
ESearch = Elasticsearch(os.environ['ES_URI'], retry_on_timeout=True)

ALLIANCE_API_BASE_URL = "https://www.alliancegenome.org/api/gene/"
QUERY_LIMIT = 25000
SGD_SOURCE_ID = 834
DIRECT_SUBMISSION_SOURCE_ID = 759
SEPARATOR = ' '
TAXON_ID = 274901

S3_BUCKET = os.environ['S3_BUCKET']
S3_ACCESS_KEY = ''
S3_SECRET_KEY = ''

# get list of URLs to visit from comma-separated ENV variable cache_urls 'url1, url2'
cache_urls = None
if 'CACHE_URLS' in list(os.environ.keys()):
    cache_urls = os.environ['CACHE_URLS'].split(',')
else:
    cache_urls = ['http://localhost:6545']

class CacheBase(object):
    def get_base_url(self):
        url_segment = '/locus/'
        if self.__url_segment__:
            url_segment = self.__url_segment__
        return url_segment + self.sgdid

    def get_secondary_base_url(self):
        return ''

    # list all dependent urls to ping, like secondary requests
    def get_secondary_cache_urls(self, is_quick=False):
        return []

    def can_skip_cache(self):
        return False

    def get_all_cache_urls(self, is_quick=False):
        if is_quick and self.can_skip_cache():
            return []
        base_target_url = self.get_base_url()
        target_urls = [base_target_url]
        details_urls = self.get_secondary_cache_urls(is_quick)
        target_urls = target_urls + details_urls
        urls = []
        for relative_url in target_urls:
            for base_url in cache_urls:
                url = base_url + relative_url
                urls.append(url)
        # if gene, add /locus/:name
        is_locus = ('locus' in self.__url_segment__)
        if is_locus:
            name_url = base_url + '/locus/' + self.get_name()
            urls.append(name_url)
        return urls

    def refresh_cache(self):
        urls = self.get_all_cache_urls()
        for url in urls:
            try:
                # purge
                response = requests.request('PURGE', url)
                if (response.status_code != 200):
                    raise ValueError('Error fetching ')
            except Exception as e:
                print(('error fetching ' + self.display_name))

    def ban_from_cache(self):
        try:
            targets = [str(self.sgdid), str(self.dbentity_id)]
            ban_from_cache(targets)
        except Exception as e:
            traceback.print_exc()
            print(('Error banning cache ' + self.sgdid))

Base = declarative_base(cls=CacheBase)

class Allele(Base):
    __tablename__ = 'allele'
    __table_args__ = {'schema': 'nex'}

    allele_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    description = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')


class Apo(Base):
    __tablename__ = 'apo'
    __table_args__ = {'schema': 'nex'}

    apo_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    apoid = Column(String(20), nullable=False, unique=True)
    apo_namespace = Column(String(20), nullable=False)
    namespace_group = Column(String(40))
    description = Column(String(1000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    is_obsolete = Column(Boolean, nullable=False)
    is_in_slim = Column(Boolean, nullable=False)

    source = relationship('Source')

    db_cache = {}

    ROOT_ID = 169833

    @staticmethod
    def get_apo_by_id(apo_id):
        if apo_id in Apo.db_cache:
            return Apo.db_cache[apo_id]
        else:
            apo = DBSession.query(Apo).filter_by(apo_id=apo_id).one_or_none()
            Apo.db_cache[apo_id] = apo
            return apo

    @staticmethod
    def root_to_dict():
        return {
            "display_name": "Yeast Phenotype Ontology",
            "description": "Features of Saccharomyces cerevisiae cells, cultures, or colonies that can be detected, observed, measured, or monitored.",
            "id": Apo.ROOT_ID
        }

    def to_dict(self):
        # phenotypes = DBSession.query(Phenotype.obj_url, Phenotype.qualifier_id, Phenotype.phenotype_id).filter_by(observable_id=self.apo_id).all()
        phenotypes = DBSession.query(Phenotype).filter_by(observable_id=self.apo_id).all() 
        
        annotations_count = DBSession.query(Phenotypeannotation.dbentity_id, func.count(Phenotypeannotation.dbentity_id)).filter(Phenotypeannotation.phenotype_id.in_([p.phenotype_id for p in phenotypes])).group_by(Phenotypeannotation.dbentity_id).count()

        children_relation = DBSession.query(ApoRelation).filter_by(parent_id=self.apo_id).all()
        if len(children_relation) > 0:
            children_phenotype_ids = []
            for x in DBSession.query(Phenotype).filter(Phenotype.observable_id.in_([c.child_id for c in children_relation])).all():
                children_phenotype_ids.append(x.phenotype_id)
            children_annotation_count = DBSession.query(Phenotypeannotation.dbentity_id, func.count(Phenotypeannotation.dbentity_id)).filter(Phenotypeannotation.phenotype_id.in_([i for i in children_phenotype_ids])).group_by(Phenotypeannotation.dbentity_id).count()
        else:
            children_annotation_count = 0

        qualifiers = []
        for phenotype in phenotypes:
            # qualifier_name = DBSession.query(Apo.display_name).filter_by(apo_id=phenotype[1]).one_or_none()
            qualifier = DBSession.query(Apo).filter_by(apo_id=phenotype.qualifier_id).one_or_none()
            if qualifier:
                qualifiers.append({
                    "link": phenotype.obj_url,
                    "qualifier": qualifier.display_name
                })

        return {
            "id": self.apo_id,
            "display_name": self.display_name,
            "description": self.description,
            "phenotypes": qualifiers,
            "overview": Phenotypeannotation.create_count_overview([p.phenotype_id for p in phenotypes]),
            "locus_count": annotations_count,
            "descendant_locus_count": annotations_count + children_annotation_count
        }

    def to_snapshot_dict(self):
        phenotypes = DBSession.query(Phenotype.obj_url, Phenotype.qualifier_id, Phenotype.phenotype_id).filter_by(observable_id=self.apo_id).all()
        annotations_count = DBSession.query(Phenotypeannotation.dbentity_id, func.count(Phenotypeannotation.dbentity_id)).filter(Phenotypeannotation.phenotype_id.in_([p[2] for p in phenotypes])).group_by(Phenotypeannotation.dbentity_id).count()
        children_relation = DBSession.query(ApoRelation).filter_by(parent_id=self.apo_id).all()
        if len(children_relation) > 0:
            children_phenotype_ids = []
            for x in DBSession.query(Phenotype).filter(Phenotype.observable_id.in_([c.child_id for c in children_relation])).all():
                children_phenotype_ids.append(x.phenotype_id)
            children_annotation_count = DBSession.query(Phenotypeannotation.dbentity_id, func.count(Phenotypeannotation.dbentity_id)).filter(Phenotypeannotation.phenotype_id.in_(children_phenotype_ids)).group_by(Phenotypeannotation.dbentity_id).count()
        else:
            children_annotation_count = 0
        return {
            "id": self.apo_id,
            "display_name": self.display_name,
            "format_name": self.format_name,
            "link": self.obj_url,
            "direct_annotation_gene_count": annotations_count,
            "descendant_annotation_gene_count": annotations_count + children_annotation_count,
            "is_root": False
        }

    def annotations_to_dict(self):
        phenotypes = DBSession.query(Phenotype).filter_by(observable_id=self.apo_id).all()

        obj = []

        for phenotype in phenotypes:
            obj += phenotype.annotations_to_dict()

        return obj

    def annotations_and_children_to_dict(self):
        phenotypes = DBSession.query(Phenotype).filter_by(observable_id=self.apo_id).all()

        children_relation = DBSession.query(ApoRelation).filter_by(parent_id=self.apo_id).all()
        if len(children_relation) > 0:
            children_phenotypes = DBSession.query(Phenotype).filter(Phenotype.observable_id.in_([c.child_id for c in children_relation])).all()
            phenotypes += children_phenotypes

        obj = []

        for phenotype in phenotypes:
            annotations = DBSession.query(Phenotypeannotation).filter_by(phenotype_id=phenotype.phenotype_id).all()

            for a in annotations:
                obj += a.to_dict(phenotype=phenotype)

        return obj

    def ontology_graph(self):
        phenotypes = DBSession.query(Phenotype).filter_by(observable_id=self.apo_id).all()

        annotations = DBSession.query(Phenotypeannotation.dbentity_id, func.count(Phenotypeannotation.dbentity_id)).filter(Phenotypeannotation.phenotype_id.in_([p.phenotype_id for p in phenotypes])).group_by(Phenotypeannotation.dbentity_id).count()

        if self.apo_id == Apo.ROOT_ID:
            nodes = [{
                "data": {
                    "link": "/ontology/phenotype/ypo",
                    "sub_type": "FOCUS",
                    "name": "Yeast Phenotype Ontology",
                    "id": str(self.apo_id)
                }
            }]
        else:
            nodes = [{
                "data": {
                    "link": self.obj_url,
                    "sub_type": "FOCUS",
                    "name": self.display_name.replace("_"," ") + " (" + str(annotations) + ")",
                    "id": str(self.apo_id)
                }
            }]

        edges = []
        all_children = []

        children_relation = DBSession.query(ApoRelation).filter_by(parent_id=self.apo_id).all()

        add_parent_type = False
        children_level = 0
        if self.apo_id == Apo.ROOT_ID:
            children_level = len(children_relation)
            add_parent_type = True
        level = 0

        for child_relation in children_relation:
            child_node = child_relation.to_graph(nodes, edges, add_child=True, add_parent_type=add_parent_type)
            all_children.append({
                "display_name": child_node.display_name,
                "link": child_node.obj_url
            })

            if level < children_level:
                children_relation += DBSession.query(ApoRelation).filter_by(parent_id=child_node.apo_id).all()
                level += 1

        level = 0
        parent_level = 3
        parents_relation = DBSession.query(ApoRelation).filter_by(child_id=self.apo_id).all()
        for parent_relation in parents_relation:
            parent_relation.to_graph(nodes, edges, add_parent=True)

            if level < parent_level:
                parents_relation += DBSession.query(ApoRelation).filter_by(child_id=parent_relation.parent.apo_id).all()
                level += 1


        graph = {
            "edges": edges,
            "nodes": nodes,
            "all_children": all_children
        }

        if self.apo_id == Apo.ROOT_ID:
            graph["full_ontology"] = Apo.get_full_ontology()

        return graph

    @staticmethod
    def get_full_ontology():
        node_ids = [Apo.ROOT_ID]

        root = Apo.get_apo_by_id(Apo.ROOT_ID)

        ontology = {
            "child_to_parent": {},
            "elements": [{
                "display_name": "Yeast Phenotype Ontology",
                "id": root.apo_id,
                "link": root.obj_url
            }]
        }

        apos = DBSession.query(Apo).all()
        relations = DBSession.query(ApoRelation).all()

        for apo in apos:
            if apo.apo_id != Apo.ROOT_ID:
                if apo.obj_url.split("/")[1] == "observable":
                    ontology["elements"].append({
                        "display_name": apo.display_name,
                        "id": apo.apo_id,
                        "link": apo.obj_url
                    })

        for relation in relations:
            ontology["child_to_parent"][relation.child_id] = relation.parent_id

        return ontology

    def get_base_url(self):
        return '/observable/' + self.format_name

    def get_secondary_cache_urls(self, is_quick=False):
        url1 = self.get_secondary_base_url() + '/locus_details'
        return [url1]

    def get_secondary_base_url(self):
        return '/webservice/observable/' + str(self.apo_id)

class ApoAlia(Base):
    __tablename__ = 'apo_alias'
    __table_args__ = (
        UniqueConstraint('apo_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    apo_id = Column(ForeignKey('nex.apo.apo_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    apo = relationship('Apo')
    source = relationship('Source')


class ApoRelation(Base):
    __tablename__ = 'apo_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.apo.apo_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.apo.apo_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Apo', primaryjoin='ApoRelation.child_id == Apo.apo_id')
    parent = relationship('Apo', primaryjoin='ApoRelation.parent_id == Apo.apo_id')
    ro = relationship('Ro')
    source = relationship('Source')

    def to_graph(self, nodes, edges, add_parent=False, add_child=False, add_parent_type=False):
        parent = Apo.get_apo_by_id(self.parent_id)

        adding_nodes = []
        if add_parent:
            adding_nodes.append(parent)

        if add_child:
            child = Apo.get_apo_by_id(self.child_id)
            adding_nodes.append(child)

        for node in adding_nodes:
            if node.display_name == "observable":
                type = "observable"
                name = "Yeast Phenotype Ontology"
            else:
                phenotypes = DBSession.query(Phenotype).filter_by(observable_id=node.apo_id).all()

                annotations = DBSession.query(Phenotypeannotation.dbentity_id, func.count(Phenotypeannotation.dbentity_id)).filter(Phenotypeannotation.phenotype_id.in_([p.phenotype_id for p in phenotypes])).group_by(Phenotypeannotation.dbentity_id).count()

                if add_parent_type:
                    type = parent.display_name
                    if type == "observable":
                        type = node.display_name
                else:
                    type = "development"
                name = node.display_name + " (" + str(annotations) + ")"

            nodes.append({
                "data": {
                    "link": node.obj_url,
                    "sub_type": type,
                    "name": name,
                    "id": str(node.apo_id)
                }
            })

        edges.append({
            "data": {
                "name": self.ro.display_name,
                "target": str(self.child_id),
                "source": str(self.parent_id)
            }
        })

        return self.child


class ApoUrl(Base):
    __tablename__ = 'apo_url'
    __table_args__ = (
        UniqueConstraint('apo_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    apo_id = Column(ForeignKey('nex.apo.apo_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    apo = relationship('Apo')
    source = relationship('Source')
class ArchContig(Base):
    __tablename__ = 'arch_contig'
    __table_args__ = {'schema': 'nex'}

    contig_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500))
    source_id = Column(BigInteger, nullable=False, index=True)
    taxonomy_id = Column(BigInteger, nullable=False, index=True)
    so_id = Column(BigInteger, nullable=False, index=True)
    centromere_start = Column(Integer)
    centromere_end = Column(Integer)
    genbank_accession = Column(String(40))
    gi_number = Column(String(40))
    refseq_id = Column(String(40))
    reference_chromosome_id = Column(BigInteger)
    reference_start = Column(Integer)
    reference_end = Column(Integer)
    reference_percent_identity = Column(Float(53))
    reference_alignment_length = Column(Integer)
    seq_version = Column(DateTime)
    coord_version = Column(DateTime)
    genomerelease_id = Column(BigInteger, index=True)
    file_header = Column(String(200))
    download_filename = Column(String(200))
    file_id = Column(BigInteger, index=True)
    description = Column(String(500))
    residues = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False)
    created_by = Column(String(12), nullable=False)
    date_archived = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))


class ArchContigchange(Base):
    __tablename__ = 'arch_contigchange'
    __table_args__ = (
        UniqueConstraint('contig_id', 'genomerelease_id', 'change_type', 'change_min_coord', 'change_max_coord'),
        {'schema': 'nex'}
    )

    archive_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.archive_seq'::regclass)"))
    contig_id = Column(ForeignKey('nex.arch_contig.contig_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(BigInteger, nullable=False)
    bud_id = Column(BigInteger)
    genomerelease_id = Column(BigInteger, nullable=False, index=True)
    change_type = Column(String(40), nullable=False)
    change_min_coord = Column(Integer, nullable=False)
    change_max_coord = Column(Integer, nullable=False)
    old_value = Column(String(1000))
    new_value = Column(String(1000))
    date_changed = Column(DateTime, nullable=False)
    changed_by = Column(String(12), nullable=False)
    date_archived = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))

    contig = relationship('ArchContig')


class ArchDnasequenceannotation(Base):
    __tablename__ = 'arch_dnasequenceannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'taxonomy_id', 'contig_id', 'genomerelease_id', 'so_id', 'dna_type'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(BigInteger, nullable=False)
    source_id = Column(BigInteger, nullable=False, index=True)
    taxonomy_id = Column(BigInteger, nullable=False, index=True)
    reference_id = Column(BigInteger, index=True)
    bud_id = Column(BigInteger)
    so_id = Column(BigInteger, nullable=False, index=True)
    dna_type = Column(String(50), nullable=False)
    contig_id = Column(ForeignKey('nex.arch_contig.contig_id', ondelete='CASCADE'), index=True)
    seq_version = Column(DateTime)
    coord_version = Column(DateTime)
    genomerelease_id = Column(BigInteger, index=True)
    start_index = Column(Integer)
    end_index = Column(Integer)
    strand = Column(String(1), nullable=False)
    file_header = Column(String(200))
    download_filename = Column(String(200))
    file_id = Column(BigInteger, index=True)
    residues = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False)
    created_by = Column(String(12), nullable=False)
    date_archived = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))

    contig = relationship('ArchContig')


class ArchDnasubsequence(Base):
    __tablename__ = 'arch_dnasubsequence'
    __table_args__ = (
        UniqueConstraint('annotation_id', 'dbentity_id', 'genomerelease_id', 'relative_start_index', 'relative_end_index'),
        {'schema': 'nex'}
    )

    dnasubsequence_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.detail_seq'::regclass)"))
    annotation_id = Column(ForeignKey('nex.arch_dnasequenceannotation.annotation_id', ondelete='CASCADE'), nullable=False)
    dbentity_id = Column(BigInteger, nullable=False, index=True)
    display_name = Column(String(500), nullable=False)
    bud_id = Column(BigInteger)
    so_id = Column(BigInteger, nullable=False, index=True)
    relative_start_index = Column(Integer, nullable=False)
    relative_end_index = Column(Integer, nullable=False)
    contig_start_index = Column(Integer, nullable=False)
    contig_end_index = Column(Integer, nullable=False)
    seq_version = Column(DateTime)
    coord_version = Column(DateTime)
    genomerelease_id = Column(BigInteger, index=True)
    file_header = Column(String(200), nullable=False)
    download_filename = Column(String(100), nullable=False)
    file_id = Column(BigInteger, index=True)
    residues = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False)
    created_by = Column(String(12), nullable=False)
    date_archived = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))

    annotation = relationship('ArchDnasequenceannotation')


class ArchLiteratureannotation(Base):
    __tablename__ = 'arch_literatureannotation'
    __table_args__ = (
        UniqueConstraint('reference_id', 'topic', 'locus_id'),
        {'schema': 'nex'}
    )

    archive_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.archive_seq'::regclass)"))
    reference_id = Column(BigInteger, nullable=False)
    source_id = Column(BigInteger, nullable=False)
    taxonomy_id = Column(BigInteger, nullable=False)
    locus_id = Column(BigInteger)
    bud_id = Column(BigInteger)
    topic = Column(String(42), nullable=False)
    date_created = Column(DateTime, nullable=False)
    created_by = Column(String(12), nullable=False)
    date_archived = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))


class ArchLocuschange(Base):
    __tablename__ = 'arch_locuschange'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'change_type', 'old_value', 'new_value', 'date_added_to_database'),
        {'schema': 'nex'}
    )

    archive_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.archive_seq'::regclass)"))
    dbentity_id = Column(BigInteger, nullable=False)
    source_id = Column(BigInteger, nullable=False)
    bud_id = Column(BigInteger)
    change_type = Column(String(100), nullable=False)
    old_value = Column(String(40))
    new_value = Column(String(40))
    date_added_to_database = Column(DateTime, nullable=False)
    added_by = Column(String(12), nullable=False)
    date_archived = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    date_name_standardized = Column(DateTime, nullable=False)


    def to_dict(self):
        return {
            "category": self.display_name,
            "history_type": "LSP" if self.note_type.upper() == "LOCUS" else self.note_type.upper(),
            "note": self.note,
            "date_created": self.date_created.strftime("%Y-%m-%d"),
            "references": [self.reference.to_dict_citation()]
        }



class ArchProteinsequenceannotation(Base):
    __tablename__ = 'arch_proteinsequenceannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'taxonomy_id', 'contig_id', 'genomerelease_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(BigInteger, nullable=False)
    source_id = Column(BigInteger, nullable=False, index=True)
    taxonomy_id = Column(BigInteger, nullable=False, index=True)
    reference_id = Column(BigInteger, index=True)
    bud_id = Column(BigInteger)
    contig_id = Column(ForeignKey('nex.arch_contig.contig_id', ondelete='CASCADE'), nullable=False, index=True)
    seq_version = Column(DateTime)
    genomerelease_id = Column(BigInteger, index=True)
    file_header = Column(String(200))
    download_filename = Column(String(200))
    file_id = Column(BigInteger, index=True)
    residues = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False)
    created_by = Column(String(12), nullable=False)
    date_archived = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))

    contig = relationship('ArchContig')


class Authorresponse(Base):
    __tablename__ = 'authorresponse'
    __table_args__ = {'schema': 'nex'}

    curation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.curation_seq'::regclass)"))
    pmid = Column(BigInteger)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    colleague_id = Column(ForeignKey('nex.colleague.colleague_id', ondelete='CASCADE'), index=True)
    author_email = Column(String(100), nullable=False)
    has_novel_research = Column(Boolean, nullable=False)
    has_large_scale_data = Column(Boolean, nullable=False)
    has_fast_track_tag = Column(Boolean, nullable=False)
    curator_checked_datasets = Column(Boolean, nullable=False)
    curator_checked_genelist = Column(Boolean, nullable=False)
    no_action_required = Column(Boolean, nullable=False)
    research_results = Column(Text)
    gene_list = Column(String(4000))
    dataset_description = Column(String(4000))
    other_description = Column(String(4000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    colleague = relationship('Colleague')
    source = relationship('Source')


class Bindingmotifannotation(Base):
    __tablename__ = 'bindingmotifannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'motif_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    obj_url = Column(String(500), nullable=False)
    motif_id = Column(BigInteger, nullable=False)
    logo_url = Column(String(500), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict(self):
        return {
            "motif_id": self.motif_id,
            "link": self.logo_url
        }

class Book(Base):
    __tablename__ = 'book'
    __table_args__ = (
        UniqueConstraint('title', 'volume_title'),
        {'schema': 'nex'}
    )

    book_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    title = Column(String(200), nullable=False)
    volume_title = Column(String(200))
    isbn = Column(String(20))
    total_pages = Column(Integer)
    publisher = Column(String(100))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')


class Chebi(Base):
    __tablename__ = 'chebi'
    __table_args__ = {'schema': 'nex'}

    chebi_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    chebiid = Column(String(20), nullable=False, unique=True)
    description = Column(String(2000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    is_obsolete = Column(Boolean, nullable=False)
    source = relationship('Source')

    def to_dict(self):

        urls = DBSession.query(ChebiUrl).filter_by(chebi_id=self.chebi_id).all()
        synonyms = DBSession.query(ChebiAlia).filter_by(chebi_id=self.chebi_id).filter(ChebiAlia.alias_type.in_(['EXACT', 'RELATED', 'IUPAC name'])).all()
        is_ntr = 0
        if self.chebiid.startswith("NTR:"):
            is_ntr = 1

            
        obj = {
            "id": self.chebi_id,
            "display_name": self.display_name,
            "chebi_id": self.chebiid,
            "is_ntr": is_ntr,
            "definition": self.description,
            "synonyms": [synonym.to_dict() for synonym in synonyms],
            "urls": [url.to_dict() for url in urls]
        }
        
        ## need to fix the following...
        obj["complexes"] = self.complex_to_dict() 
        obj["phenotype"] = self.phenotype_to_dict()
        obj["go"] = self.go_to_dict()
        obj["protein_abundance"] = self.proteinabundance_to_dict()
        obj["pathways"] = self.pathway_to_dict()
        obj["structure_image_url"] = self.get_structure_url()
        obj["pharmGKB_link_url"] = self.get_pharmGKB_url()
        obj["network_graph"] = self.chemical_network()

        return obj
    
    def phenotype_to_dict(self):
        conditions = DBSession.query(PhenotypeannotationCond).filter_by(condition_name=self.display_name).all()

        annotation_ids = []
        for x in conditions:
            annotation_ids.append(x.annotation_id)
        phenotype_annotations = DBSession.query(Phenotypeannotation).filter(Phenotypeannotation.annotation_id.in_(annotation_ids)).all()

        obj = []

        for annotation in phenotype_annotations:
            # obj += annotation.to_dict(chemical=self)
            for annot in annotation.to_dict(chemical=self):
                properties = annot.get("properties")
                if properties is None:
                    continue
                is_right_chemical = False
                for p in properties: 
                    if p['class_type'] == 'CHEMICAL' and p['bioitem']['display_name'] == self.display_name:
                        is_right_chemical = True
                if is_right_chemical:
                    obj.append(annot)
        return obj

    def go_to_dict(self):

        extensions = DBSession.query(Goextension).filter_by(dbxref_id=self.chebiid).all()
        annotation_ids = []
        for x in extensions:
            annotation_ids.append(x.annotation_id)

        go_annotations = DBSession.query(Goannotation).filter(Goannotation.annotation_id.in_(annotation_ids)).all()

        obj = []

        for annotation in go_annotations:
            ## obj += annotation.to_dict() 
            for annot in annotation.to_dict():
                properties = annot.get("properties")
                if properties is not None and len(properties) == 1 and properties[0]["bioentity"]["display_name"] != self.display_name:
                    continue
                obj.append(annot)

        return obj

    def proteinabundance_to_dict(self):

        annotations = DBSession.query(Proteinabundanceannotation).filter_by(chemical_id=self.chebi_id).all()
        new_reference_ids = [a.reference_id for a in annotations]
        orig_reference_ids = [a.original_reference_id for a in annotations]
        reference_ids = list(set(new_reference_ids + orig_reference_ids))
        references = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(reference_ids)).all()

        ids_to_references = {}
        for r in references:
            ids_to_references[r.dbentity_id] = r

        data = [a.to_dict(chebi=self, references=ids_to_references) for a in annotations]
        return sorted(data, key=lambda d: d['order_by'])

    def complex_to_dict(self):

        interactors = DBSession.query(Interactor).filter_by(format_name=self.chebiid).all()

        interactor_ids = []
        for x in interactors:
            interactor_ids.append(x.interactor_id)

        annotations = DBSession.query(Complexbindingannotation).filter(Complexbindingannotation.interactor_id.in_(interactor_ids)).all()

        annotations2 = DBSession.query(Complexbindingannotation).filter(Complexbindingannotation.binding_interactor_id.in_(interactor_ids)).all()

        complexes = []
        found = {}
        for annotation in annotations + annotations2:
            complex = annotation.complex
            if complex.format_name in found:
                continue
            found[complex.format_name] = 1
            complexes.append({ "display_name": complex.display_name,
                               "intact_id": complex.intact_id,
                               "format_name": complex.format_name,
                               "link_url": complex.obj_url,
                               "description": complex.description })

        return complexes

    def pathway_to_dict(self):

        rows = DBSession.query(ChebiAlia).filter_by(chebi_id=self.chebi_id, alias_type='YeastPathway ID').all()

        biocycIDs = []
        for x in rows:
            biocycIDs.append(x.display_name)

        pathwayRows = DBSession.query(Pathwaydbentity).filter(Pathwaydbentity.biocyc_id.in_(biocycIDs)).all()
        
        pathways = []
        for row in pathwayRows:
            pathways.append({ "display_name": row.display_name,
                              "biocyc_id": row.biocyc_id,
                              "link_url": "https://pathway.yeastgenome.org/YEAST/NEW-IMAGE?type=NIL&object=" + row.biocyc_id + "&redirect=T"})
            
        pathwaysSorted = sorted(pathways, key=lambda p: p['display_name'])
        
        return pathwaysSorted
    
    def get_structure_url(self):
        chebiURL = "https://www.ebi.ac.uk/chebi/"
        try:
            timeout = 0.5 # half second
            response = requests.get(chebiURL, timeout=timeout)
            if response.status_code != 200:
                return ''
        except:
            return ''
        url = "https://www.ebi.ac.uk/chebi/displayImage.do?defaultImage=true&imageIndex=0&chebiId=" + self.format_name.replace("CHEBI:", "") + "&dimensions=200"
        response = urlopen(url)
        res = response.read()
        if len(res) > 0:
            return url
        return ""

    def get_pharmGKB_url(self):
        rows = DBSession.query(ChebiAlia).filter_by(chebi_id=self.chebi_id, alias_type='PharmGKB ID').all()
        if len(rows) > 0:
            return "https://www.pharmgkb.org/chemical/" + rows[0].display_name
        return ""
        
    def chemical_network(self):
        
        network_nodes =[]
        network_edges =[]

        network_nodes_ids = {}
        network_edges_added = {}

        network_nodes.append({
            "name": self.display_name,
            "id": self.format_name,
            "href": "/chemical/" + self.format_name,
            "category": "FOCUS",
        })
        network_nodes_ids[self.format_name] = True

        ## go
        extensions = DBSession.query(Goextension).filter_by(dbxref_id=self.chebiid).all()
        annotation_ids = []
        for x in extensions:
            annotation_ids.append(x.annotation_id)
        go_annotations = DBSession.query(Goannotation).filter(Goannotation.annotation_id.in_(annotation_ids)).all()
        
        for g in go_annotations:
            extensions = DBSession.query(Goextension).filter_by(annotation_id=g.annotation_id).all()
            for ext in extensions:

                if ext.dbxref_id.startswith("CHEBI:") and ext.dbxref_id != self.format_name:

                    if ext.dbxref_id not in network_nodes_ids:

                        chebi = DBSession.query(Chebi).filter_by(format_name=ext.dbxref_id).one_or_none()
                        if chebi is None:
                            continue

                        network_nodes.append({
                            "name": chebi.display_name,
                            "id": ext.dbxref_id,
                            "href": "/chemical/" + ext.dbxref_id,
                            "category": "CHEMICAL",
                        })
                        network_nodes_ids[ext.dbxref_id] = True
                
                    if g.go.goid not in network_nodes_ids:
                        network_nodes.append({
                            "name": g.go.display_name,
                            "id": g.go.goid,
                            "href": g.go.obj_url,
                            "category": "GO",
                        })
                        network_nodes_ids[g.go.goid] = True

                    if (self.format_name,  g.go.goid) not in network_edges_added:
                        network_edges.append({
                            "source": self.format_name,
                            "target": g.go.goid
                        })
                        network_edges_added[(self.format_name,  g.go.goid)] = True

                    if (ext.dbxref_id, g.go.goid) not in network_edges_added:
                        network_edges.append({
                            "source": ext.dbxref_id,
                            "target": g.go.goid
                        })
                        network_edges_added[(ext.dbxref_id,  g.go.goid)] = True
            
        ## phenotype

        conditions = DBSession.query(PhenotypeannotationCond).filter_by(condition_class = 'chemical', condition_name=self.display_name).all()

        annotation_ids = []
        for x in conditions:
            annotation_ids.append(x.annotation_id)

        phenotype_annotations = DBSession.query(Phenotypeannotation).filter(Phenotypeannotation.annotation_id.in_(annotation_ids)).all()
        
        phenotype_to_id = {}
        for p in phenotype_annotations:
            if p.phenotype.display_name.startswith('resistance to chemicals:'):
                continue
            pheno_id = "phenotype_" + str(p.phenotype_id)
            conditions = DBSession.query(PhenotypeannotationCond).filter_by(annotation_id = p.annotation_id, condition_class = 'chemical').all() 
            for cond in conditions:
                chebiObjs = DBSession.query(Chebi).filter_by(display_name=cond.condition_name).all()
                for c in chebiObjs:
                    if c.format_name == self.format_name:
                        continue
                    if c.format_name not in network_nodes_ids:
                        chebi = DBSession.query(Chebi).filter_by(format_name=c.format_name).one_or_none()
                        if chebi is None:
                            continue
                        network_nodes.append({
                                "name": chebi.display_name,
                                "id": c.format_name,
                                "href": "/chemical/" + c.format_name,
                                "category": "CHEMICAL",
                        })
                        network_nodes_ids[c.format_name] = True
                    
                    if p.phenotype.display_name in phenotype_to_id:
                        pheno_id = phenotype_to_id[p.phenotype.display_name]
                    else:
                        phenotype_to_id[p.phenotype.display_name] = pheno_id 

                    if pheno_id not in network_nodes_ids:
                        network_nodes.append({
                            "name": p.phenotype.display_name,
                            "id": pheno_id,
                            "href": p.phenotype.obj_url,
                            "category": "PHENOTYPE",
                        })
                        network_nodes_ids[pheno_id] = True

                    if (self.format_name, pheno_id) not in network_edges_added:
                        network_edges.append({
                                "source": self.format_name,
                                "target": pheno_id
                        })
                        network_edges_added[(self.format_name, pheno_id)] = True

                    if (c.format_name, pheno_id) not in network_edges_added:
                        network_edges.append({
                                "source": c.format_name,
                                "target": pheno_id
                        })
                        network_edges_added[(c.format_name, pheno_id)] = True
                        
        ## complex

        interactors = DBSession.query(Interactor).filter_by(format_name=self.chebiid).all()

        interactor_ids = []
        for x in interactors:
            interactor_ids.append(x.interactor_id)

        annotations = DBSession.query(Complexbindingannotation).filter(Complexbindingannotation.interactor_id.in_(interactor_ids)).all()

        annotations2 = DBSession.query(Complexbindingannotation).filter(Complexbindingannotation.binding_interactor_id.in_(interactor_ids)).all()
        
        found = {}
        for annotation in annotations + annotations2:
            complex_id = annotation.complex_id
            if complex_id in found:
                continue
            found[complex_id] = 1
            annots = DBSession.query(Complexbindingannotation).filter_by(complex_id=complex_id).all()
            
            for a in annots:
                interactors = DBSession.query(Interactor).filter_by(interactor_id=a.interactor_id).all()
                binding_interactors = DBSession.query(Interactor).filter_by(interactor_id=a.binding_interactor_id).all()
                
                complex = a.complex

                for i in interactors + binding_interactors:
                    if i.format_name.startswith("CHEBI:") and i.format_name != self.format_name:
                        if i.format_name not in network_nodes_ids:
                            chebi = DBSession.query(Chebi).filter_by(format_name=i.format_name).one_or_none()
                            if chebi is None:
                                continue
                            network_nodes.append({
                                "name": chebi.display_name,
                                "id": i.format_name,
                                "href": "/chemical/" + i.format_name,
                                "category": "CHEMICAL",
                            })
                            network_nodes_ids[i.format_name] = True

                        if complex.format_name not in network_nodes_ids:
                            network_nodes.append({
                                    "name": complex.display_name,
                                    "id": complex.format_name,
                                    "href": "/complex/" + complex.format_name,
                                    "category": "COMPLEX",
                            })
                            network_nodes_ids[complex.format_name] = True

                        if (self.format_name, complex.format_name) not in network_edges_added:
                            network_edges.append({
                                    "source": self.format_name,
                                    "target": complex.format_name
                            })
                            network_edges_added[(self.format_name, complex.format_name)] = True

                        if (i.format_name, complex.format_name) not in network_edges_added:
                            network_edges.append({
                                    "source": i.format_name,
                                    "target": complex.format_name
                            })
                            network_edges_added[(i.format_name, complex.format_name)] = True

        data = { "edges": network_edges, "nodes": network_nodes }

        return data


class ChebiAlia(Base):
    __tablename__ = 'chebi_alias'
    __table_args__ = (
        UniqueConstraint('chebi_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    chebi_id = Column(ForeignKey('nex.chebi.chebi_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    chebi = relationship('Chebi')
    source = relationship('Source')

    def to_dict(self):
        return {
            "display_name": self.display_name,
            "synonym_type": self.alias_type
        }

class ChebiUrl(Base):
    __tablename__ = 'chebi_url'
    __table_args__ = (
        UniqueConstraint('chebi_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    chebi_id = Column(ForeignKey('nex.chebi.chebi_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    chebi = relationship('Chebi')
    source = relationship('Source')

    def to_dict(self):
        return {
            "link": self.obj_url
        }

class Colleague(Base):
    __tablename__ = 'colleague'
    __table_args__ = {'schema': 'nex'}

    colleague_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    orcid = Column(String(20), unique=True)
    first_name = Column(String(40), nullable=False)
    middle_name = Column(String(20))
    last_name = Column(String(40), nullable=False)
    suffix = Column(String(4))
    other_last_name = Column(String(40))
    profession = Column(String(100))
    job_title = Column(String(100))
    institution = Column(String(100))
    address1 = Column(String(100))
    address2 = Column(String(100))
    address3 = Column(String(100))
    city = Column(String(50))
    state = Column(String(50))
    country = Column(String(40))
    postal_code = Column(String(40))
    work_phone = Column(String(40))
    other_phone = Column(String(40))
    email = Column(String(100))
    is_pi = Column(Boolean, nullable=False)
    is_contact = Column(Boolean, nullable=False)
    is_beta_tester = Column(Boolean, nullable=False)
    display_email = Column(Boolean, nullable=False)
    is_in_triage = Column(Boolean, nullable=False)
    date_last_modified = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    colleague_note = Column(String(1000))
    research_interest = Column(String(4000))

    source = relationship('Source')

    def get_keywords(self):
        lst = DBSession.query(Colleague,ColleagueKeyword).join(ColleagueKeyword).filter(ColleagueKeyword.colleague_id == Colleague.colleague_id).all()
        obj = {}
        keyword_ids = []
        for item in lst:
            if item[1]:
                keyword_ids.append(item[1].keyword_id)
            if item[1].keyword_id not in obj:
                obj[item[1].keyword_id] = []
            obj[item[1].keyword_id].append(item)
        keywords = []
        if len(keyword_ids) > 0:
            keywords = DBSession.query(Keyword).filter(
                Keyword.keyword_id.in_(keyword_ids)).all()
        for k in keywords:
            obj[k.keyword_id].append({'id': k.keyword_id, 'name': k.display_name})
        return obj

    def to_simple_dict(self):
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'orcid': self.orcid,
            'email': self.email,
            'display_email': self.display_email,
            'receive_quarterly_newsletter': self.is_contact,
            'willing_to_be_beta_tester': self.is_beta_tester,
            'colleague_id': self.colleague_id,
            'link': self.obj_url,
            'is_pi': self.is_pi
        }

    def to_dict_basic_data(self):
        return {
            "colleague_id": self.colleague_id,
            "email": self.email if self.display_email else None,
            "format_name": self.format_name,
            "name": self.display_name,
            "link": self.obj_url,
            "institution": self.institution,
            "state": self.state,
            "city": self.city,
            "country": self.country,
            "address1": self.address1,
            "address2": self.address2,
            "address3": self.address3
        }

    def to_dict(self):
        websites = []
        c_urls = DBSession.query(ColleagueUrl.obj_url, ColleagueUrl.url_type).filter(ColleagueUrl.colleague_id == self.colleague_id).all()
        for x in c_urls:
            websites.append({
                'link': x[0],
                'type': x[1]
            })
        # format full name
        fullname = ''
        if self.suffix:
            fullname = fullname + self.suffix + ' '
        if self.first_name:
            fullname = fullname + self.first_name + ' '
        if self.middle_name:
            fullname = fullname + self.middle_name + ' '
        if self.last_name:
            fullname = fullname + self.last_name
        _dict = {
            'colleague_id': self.colleague_id,
            'orcid': self.orcid,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name': self.last_name,
            'suffix': self.suffix,
            'fullname': fullname,
            'institution': self.institution,
            'email': self.email if self.display_email else None,
            'link': self.obj_url,
            'profession': self.profession,
            'position': self.job_title,
            'research_interests': self.research_interest,
            'work_phone': self.work_phone,
            'phone_number': self.work_phone,
            'other_phone': self.other_phone,
            'format_name': self.format_name,
            'name': self.display_name,
            'address1': self.address1,
            'address2': self.address2,
            'address3': self.address3,
            'postal_code': self.postal_code,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'colleague_note': self.colleague_note,
            'websites': websites,
            'display_email': self.display_email,
            'receive_quarterly_newsletter': self.is_contact,
            'willing_to_be_beta_tester': self.is_beta_tester,
            'is_pi': self.is_pi
        }
        _dict['lab_page'] = ''
        _dict['research_page'] = ''

        keyword_ids = []
        for x in DBSession.query(ColleagueKeyword).filter(ColleagueKeyword.colleague_id == self.colleague_id).all():
            keyword_ids.append(x.keyword_id)

        if len(keyword_ids) > 0:
            keywords = DBSession.query(Keyword).filter(Keyword.keyword_id.in_(keyword_ids)).all()
            _dict['keywords'] = [k.display_name for k in keywords]
        else:
            _dict['keywords'] = []
            
        colleague_loci = DBSession.query(ColleagueLocus, Locusdbentity.display_name).outerjoin(Locusdbentity).filter(ColleagueLocus.colleague_id == self.colleague_id).all()
        colleague_loci = [x[1] for x in colleague_loci]
        if len(colleague_loci):
            associated_genes = ', '.join(colleague_loci)
        else:
            associated_genes = None
        _dict['associated_genes'] = associated_genes
        return _dict

    def get_collegue_url(self):
        item = DBSession.query(ColleagueUrl).filter(
            ColleagueUrl.colleague_id == self.colleague_id).first()
        return item

class CuratorActivity(Base):
    __tablename__ = 'curatoractivity'
    __table_args__ = (
        UniqueConstraint('curation_id'),
        {'schema': 'nex'}
    )

    curation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    activity_category = Column(String(100), nullable=False)
    dbentity_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=True)
    message = Column(String(500), nullable=False)
    json = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    def to_dict(self):
        href = self.obj_url
        time_created = ''
        if self.dbentity_id != 1 or self.dbentity_id == None:
            is_mod_date = json.loads(self.json).get('modified_date', None)
            if is_mod_date: #self.activity_category == 'download':
                href = re.sub(r'\?.+', '', href).replace(':433', '').strip()
                return {
                    'category': self.activity_category,
                    'created_by': self.created_by,
                    'href': href,
                    'date_created': self.date_created.strftime("%Y-%m-%d"),
                    'time_created': datetime.strptime(json.loads(self.json)["modified_date"], '%Y-%m-%d %H:%M:%S.%f').isoformat(),
                    'name': self.display_name,
                    'type': self.message,
                    'is_curator_activity': True,
                    'data': json.loads(self.json)

                }
       
        return {
            'category': self.activity_category,
            'created_by': self.created_by,
            'href': href,
            'date_created': self.date_created.strftime("%Y-%m-%d"),
            'time_created': time_created,
            'name': self.display_name,
            'type': self.message,
            'is_curator_activity': True,
            'data': json.loads(self.json)
        }


class ColleagueKeyword(Base):
    __tablename__ = 'colleague_keyword'
    __table_args__ = (
        UniqueConstraint('keyword_id', 'colleague_id'),
        {'schema': 'nex'}
    )

    colleague_keyword_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    colleague_id = Column(ForeignKey('nex.colleague.colleague_id', ondelete='CASCADE'), nullable=False, index=True)
    keyword_id = Column(ForeignKey('nex.keyword.keyword_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    colleague = relationship('Colleague')
    keyword = relationship('Keyword')
    source = relationship('Source')


class ColleagueLocus(Base):
    __tablename__ = 'colleague_locus'
    __table_args__ = (
        UniqueConstraint('colleague_id', 'locus_id'),
        {'schema': 'nex'}
    )

    colleague_locus_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    colleague_id = Column(ForeignKey('nex.colleague.colleague_id', ondelete='CASCADE'), nullable=False)
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    colleague = relationship('Colleague')
    locus = relationship('Locusdbentity')
    source = relationship('Source')


class ColleagueReference(Base):
    __tablename__ = 'colleague_reference'
    __table_args__ = (
        UniqueConstraint('colleague_id', 'reference_id'),
        {'schema': 'nex'}
    )

    colleague_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    colleague_id = Column(ForeignKey('nex.colleague.colleague_id', ondelete='CASCADE'), nullable=False)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    colleague = relationship('Colleague')
    reference = relationship('Referencedbentity')
    source = relationship('Source')


class ColleagueRelation(Base):
    __tablename__ = 'colleague_relation'
    __table_args__ = (
        UniqueConstraint('colleague_id', 'associate_id', 'association_type'),
        {'schema': 'nex'}
    )

    colleague_relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    colleague_id = Column(ForeignKey('nex.colleague.colleague_id', ondelete='CASCADE'), nullable=False)
    associate_id = Column(ForeignKey('nex.colleague.colleague_id', ondelete='CASCADE'), nullable=False, index=True)
    association_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    associate = relationship('Colleague', primaryjoin='ColleagueRelation.associate_id == Colleague.colleague_id')
    colleague = relationship('Colleague', primaryjoin='ColleagueRelation.colleague_id == Colleague.colleague_id')
    source = relationship('Source')


class ColleagueUrl(Base):
    __tablename__ = 'colleague_url'
    __table_args__ = (
        UniqueConstraint('colleague_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    colleague_id = Column(ForeignKey('nex.colleague.colleague_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    colleague = relationship('Colleague')
    source = relationship('Source')


class Colleaguetriage(Base):
    __tablename__ = 'colleaguetriage'
    __table_args__ = {'schema': 'nex'}

    curation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.curation_seq'::regclass)"))
    triage_type = Column(String(10), nullable=False)
    colleague_id = Column(BigInteger)
    json = Column(Text, nullable=False)
    curator_comment = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))

    def to_dict(self):
        data = json.loads(self.json)
        if data is None:
            data = {}
        data['id'] = self.curation_id
        data['type'] = self.triage_type
        data['submission_date'] = self.date_created.strftime("%Y-%m-%d")
        return data


class Contig(Base):
    __tablename__ = 'contig'
    __table_args__ = {'schema': 'nex'}

    contig_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    so_id = Column(ForeignKey('nex.so.so_id', ondelete='CASCADE'), nullable=False, index=True)
    centromere_start = Column(Integer)
    centromere_end = Column(Integer)
    genbank_accession = Column(String(40), nullable=False)
    gi_number = Column(String(40))
    refseq_id = Column(String(40))
    reference_chromosome_id = Column(BigInteger)
    reference_start = Column(Integer)
    reference_end = Column(Integer)
    reference_percent_identity = Column(Float(53))
    reference_alignment_length = Column(Integer)
    seq_version = Column(DateTime)
    coord_version = Column(DateTime)
    genomerelease_id = Column(ForeignKey('nex.genomerelease.genomerelease_id', ondelete='CASCADE'), index=True)
    file_header = Column(String(200), nullable=False)
    download_filename = Column(String(100), nullable=False)
    file_id = Column(ForeignKey('nex.filedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    residues = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    file = relationship('Filedbentity')
    genomerelease = relationship('Genomerelease')
    so = relationship('So')
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict_sequence_widget(self):
        return {
            "display_name": self.display_name,
            "format_name": self.format_name,
            "is_chromosome": self.so_id == 264265, # soid = SO:0000340 = Chromosome
            "centromere_start": self.centromere_start,
            "centromere_end": self.centromere_end,
            "link": self.obj_url,
            "id": self.contig_id,
            "length": len(self.residues),
            "format_name": self.format_name,
            "strain": {
                "display_name": "S288C",
                "link": "/strain/S288C/overview",
                "id": 1,
                "format_name": "S288C"
            }
        }

    def to_dict_strain_table(self, chromosome_cache={}):
        obj = {
            "display_name": self.display_name,
            "format_name": self.format_name,
            "genbank_accession": self.genbank_accession,
            "link": self.obj_url,
            "reference_alignment": None,
            "centromere_end": self.centromere_end,
            "centromere_start": self.centromere_start,
            "length": len(self.residues),
            "id": self.contig_id,
            "refseq_id": self.refseq_id
        }

        if self.reference_chromosome_id != None:
            if chromosome_cache.get(self.reference_chromosome_id):
                chromosome = chromosome_cache.get(self.reference_chromosome_id)
            else:
                chromosome = DBSession.query(Contig.format_name, Contig.obj_url).filter_by(contig_id=self.reference_chromosome_id).one_or_none()
                chromosome_cache[self.reference_chromosome_id] = chromosome

            if chromosome:
                obj['reference_alignment'] = {
                    "percent_identity": self.reference_percent_identity,
                    "start": self.reference_start,
                    "end": self.reference_end,
                    "alignment_length": self.reference_alignment_length,
                    "chromosome": {
                        "format_name": chromosome[0],
                        "link": chromosome[1]
                    }
                }

        return obj

    def to_dict(self):
        strains = Straindbentity.get_strains_by_taxon_id(self.taxonomy_id)
        urls = DBSession.query(ContigUrl).filter_by(contig_id=self.contig_id).all()
        # get sequences and group by feature type, exclude inactive and non S288c features

        inactive_ids = []
        for x in DBSession.query(Locusdbentity).filter(Locusdbentity.dbentity_status != 'Active').all():
            inactive_ids.append(x.dbentity_id)
        
        so_id = get_transcript_so_id()
        
        sequences = DBSession.\
            query(Dnasequenceannotation.so_id, func.count(Dnasequenceannotation.annotation_id)).\
            filter(and_(Dnasequenceannotation.contig_id==self.contig_id, Dnasequenceannotation.dna_type=="GENOMIC", Dnasequenceannotation.taxonomy_id == TAXON_ID, Dnasequenceannotation.so_id != so_id, ~Dnasequenceannotation.dbentity_id.in_(inactive_ids))).\
            group_by(Dnasequenceannotation.so_id).all()
        so_ids = set([ov[0] for ov in sequences])
        so = DBSession.query(So).filter(So.so_id.in_(list(so_ids))).all()
        sos = {}
        for s in so:
            sos[s.so_id] = s.display_name
        obj = {
            "display_name": self.display_name,
            "strain": {
                "link": strains[0].obj_url,
                "display_name": strains[0].display_name
            },
            "residues": self.residues,
            "urls": [u.to_dict() for u in urls],
            "header": self.file_header,
            "genbank_accession": self.genbank_accession,
            "id": self.contig_id,
            "overview": [["Feature Type", "Count"]] + [(sos[ov[0]], ov[1]) for ov in sorted(sequences, key=lambda k: k[1], reverse=True)]
        }
        if self.download_filename:
            obj["filename"] = self.download_filename
        return obj

    def sequence_details(self):

        so_id = get_transcript_so_id()
        
        dnas = DBSession.query(Dnasequenceannotation).filter(and_(Dnasequenceannotation.contig_id==self.contig_id, Dnasequenceannotation.dna_type=="GENOMIC", Dnasequenceannotation.so_id != so_id)).all()

        active_genomic_dna = []
        for dna in dnas:
            if dna.dbentity.dbentity_status == "Active":
                active_genomic_dna.append(dna.to_dict())

        return {
            "genomic_dna": active_genomic_dna
        }


class ContigUrl(Base):
    __tablename__ = 'contig_url'
    __table_args__ = (
        UniqueConstraint('contig_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    contig_id = Column(ForeignKey('nex.contig.contig_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    contig = relationship('Contig')
    source = relationship('Source')

    def to_dict(self):
        return {
            "link": self.obj_url,
            "display_name": self.display_name
        }


class Contignoteannotation(Base):
    __tablename__ = 'contignoteannotation'
    __table_args__ = (
        UniqueConstraint('contig_id', 'note_type', 'display_name', 'note'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    contig_id = Column(ForeignKey('nex.contig.contig_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    bud_id = Column(Integer)
    note_type = Column(String(40), nullable=False)
    display_name = Column(String(500), nullable=False)
    note = Column(String(2000), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    contig = relationship('Contig')
    reference = relationship('Referencedbentity')
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')


class CurationLocus(Base):
    __tablename__ = 'curation_locus'
    __table_args__ = (
        UniqueConstraint('curation_tag', 'locus_id'),
        {'schema': 'nex'}
    )

    curation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.curation_seq'::regclass)"))
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    curation_tag = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    curator_comment = Column(String(2000))
    json = Column(Text)

    locus = relationship('Locusdbentity', foreign_keys=[locus_id])
    source = relationship('Source')

    acceptable_tags = {
        'go_needs_review': 'GO needs review',
        'headline_reviewed': 'Headline reviewed',
        'paragraph_not_needed': 'Paragraph not needed',
        'phenotype_uncuratable': 'Phenotype uncuratable'
    }

    @staticmethod
    def factory(tag, gene_id_list, comment, created_by, source_id=824, json=None):
        if tag not in acceptable_tags:
            return None

        obj = []
        for dbentity_id in gene_id_list:
            obj.append(
                CurationLocus(
                    locus_id=dbentity_id,
                    source_id=source_id,
                    curation_tag=acceptable_tags[tag],
                    created_by=created_by,
                    json=json
                )
            )
        return obj


class CurationReference(Base):
    __tablename__ = 'curation_reference'
    __table_args__ = (
        UniqueConstraint('reference_id', 'curation_tag', 'dbentity_id'),
        {'schema': 'nex'}
    )

    curation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.curation_seq'::regclass)"))
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), index=True)
    curation_tag = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    curator_comment = Column(String(2000))
    json = Column(Text)

    dbentity = relationship('Dbentity')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')

    acceptable_tags = {
        'high_priority': 'High Priority',
        'delay': 'Delay',
        'homology_disease': 'Homology/Disease',
        'go': 'GO information',
        'classical_phenotype': 'Classical phenotype information',
        'headline_information': 'Headline information',
        'gene_model': 'Gene model',
        'headline_needs_review': 'Headline needs review',
        'htp_phenotype': 'HTP phenotype',
        'not_yet_curated': 'Not yet curated',
        'non_phenotype_htp': 'Non-phenotype HTP',
        'paragraph_needs_review': 'Paragraph needs review',
        'pathways': 'Pathways',
        'phenotype_needs_review': 'Phenotype needs review',
        'ptm': 'Post-translational modifications',
        'regulation_information': 'Regulation information',
        'fast_track': 'Fast Track',
        'engineering': 'Engineering',
        'alleles': 'Alleles'
    }

    @staticmethod
    def factory(reference_id, tag, comment, dbentity_id, created_by, source_id=824, json=None):
        if tag not in CurationReference.acceptable_tags:
            return None

        return CurationReference(
            reference_id=reference_id,
            source_id=source_id,
            dbentity_id=dbentity_id,
            curation_tag=CurationReference.acceptable_tags[tag],
            created_by=created_by,
            curator_comment=comment,
            json=json
        )

    def get_name(self):
        c_name = self.curation_tag
        for key, value in CurationReference.acceptable_tags.items():
            if value == c_name:
                return key
        return None

class Dataset(Base):
    __tablename__ = 'dataset'
    __table_args__ = {'schema': 'nex'}

    dataset_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    dbxref_id = Column(String(40))
    dbxref_type = Column(String(40))
    date_public = Column(DateTime)
    parent_dataset_id = Column(ForeignKey('nex.dataset.dataset_id', ondelete='CASCADE'), index=True)
    channel_count = Column(SmallInteger)
    sample_count = Column(Integer, nullable=False)
    is_in_spell = Column(Boolean, nullable=False)
    is_in_browser = Column(Boolean, nullable=False)
    description = Column(String(4000))
    date_created = Column(DateTime, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    parent_dataset = relationship('Dataset', remote_side=[dataset_id])
    source = relationship('Source')

    def to_dict(self, reference=None, dataset_keywords=None, add_conditions=False, add_resources=False):
        keywords = DBSession.query(DatasetKeyword).filter_by(dataset_id=self.dataset_id).all()

        tags = [keyword.to_dict() for keyword in keywords]

        obj = {
            "id": self.dataset_id,
            "format_name": self.format_name,
            "display_name": self.display_name,
            "link": self.obj_url,
            "short_description": self.description,
            "condition_count": self.sample_count,
            "channel_count": self.channel_count,
            "geo_id": self.dbxref_id,
            "tags": tags
        }

        if reference:
            obj["reference"] = {
                "display_name": reference.display_name,
                "link": reference.obj_url,
                "pubmed_id": reference.pmid,
                "id": reference.dbentity_id
            }
        else:
            references = DBSession.query(DatasetReference).filter_by(dataset_id=self.dataset_id).all()
            formatted_refs = []
            for datasetreference in references:
                reference = datasetreference.reference
                ref_obj =  {
                    "display_name": reference.display_name,
                    "link": reference.obj_url,
                    "pubmed_id": reference.pmid,
                    "id": reference.dbentity_id
                }
                formatted_refs.append(ref_obj)
            obj["references"] = formatted_refs

        if add_conditions:
            conditions = DBSession.query(Datasetsample).filter_by(dataset_id=self.dataset_id).all()

            obj["datasetcolumns"] = []
            for condition in conditions:
                geo_id = condition.dbxref_id
                if geo_id is None:
                    geo_id = ''
                obj["datasetcolumns"].append({
                    "display_name": condition.display_name,
                    "geo_id": geo_id,
                    "link": condition.dbxref_url
                })

        if add_resources:
            urls = DBSession.query(DatasetUrl).filter_by(dataset_id=self.dataset_id).all()

            obj["urls"] = []

            files = DBSession.query(DatasetFile).filter_by(dataset_id=self.dataset_id).all()
            for f in files:
                if f.file.s3_url is not None:
                    obj["urls"].append({
                        "link": f.file.s3_url,
                        "display_name": "Download data"
                    })

            for url in urls:
                url_obj = {
                    "link": url.obj_url,
                    "display_name": url.display_name
                }

                if url.url_type == "GEO":
                    url_obj["category"] = "External"
                    obj['geo_url'] = url.obj_url
                obj["urls"].append(url_obj)

        return obj


class DatasetFile(Base):
    __tablename__ = 'dataset_file'
    __table_args__ = (
        UniqueConstraint('dataset_id', 'file_id'),
        {'schema': 'nex'}
    )

    dataset_file_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    dataset_id = Column(ForeignKey('nex.dataset.dataset_id', ondelete='CASCADE'), nullable=False)
    file_id = Column(ForeignKey('nex.filedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dataset = relationship('Dataset')
    file = relationship('Filedbentity', primaryjoin='Filedbentity.dbentity_id == DatasetFile.file_id')
    source = relationship('Source')


class DatasetKeyword(Base):
    __tablename__ = 'dataset_keyword'
    __table_args__ = (
        UniqueConstraint('keyword_id', 'dataset_id'),
        {'schema': 'nex'}
    )

    dataset_keyword_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    keyword_id = Column(ForeignKey('nex.keyword.keyword_id', ondelete='CASCADE'), nullable=False)
    dataset_id = Column(ForeignKey('nex.dataset.dataset_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dataset = relationship('Dataset')
    keyword = relationship('Keyword')
    source = relationship('Source')

    def to_dict(self):
        return {
            "display_name": self.keyword.display_name,
            "link": self.keyword.obj_url
        }


class DatasetReference(Base):
    __tablename__ = 'dataset_reference'
    __table_args__ = (
        UniqueConstraint('reference_id', 'dataset_id'),
        {'schema': 'nex'}
    )

    dataset_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    dataset_id = Column(ForeignKey('nex.dataset.dataset_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dataset = relationship('Dataset')
    reference = relationship('Referencedbentity')
    source = relationship('Source')


class DatasetUrl(Base):
    __tablename__ = 'dataset_url'
    __table_args__ = (
        UniqueConstraint('dataset_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    dataset_id = Column(ForeignKey('nex.dataset.dataset_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dataset = relationship('Dataset')
    source = relationship('Source')


class Datasetlab(Base):
    __tablename__ = 'datasetlab'
    __table_args__ = (
        UniqueConstraint('lab_name', 'dataset_id'),
        {'schema': 'nex'}
    )

    datasetlab_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    dataset_id = Column(ForeignKey('nex.dataset.dataset_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(BigInteger, nullable=False)
    lab_name = Column(String(40), nullable=False)
    lab_location = Column(String(100), nullable=False)
    colleague_id = Column(ForeignKey('nex.colleague.colleague_id', ondelete='CASCADE'), index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    colleague = relationship('Colleague')
    dataset = relationship('Dataset')


class Datasetsample(Base):
    __tablename__ = 'datasetsample'
    __table_args__ = {'schema': 'nex'}

    datasetsample_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), index=True)
    dataset_id = Column(ForeignKey('nex.dataset.dataset_id', ondelete='CASCADE'), nullable=False, index=True)
    sample_order = Column(Integer, nullable=False)
    dbxref_id = Column(String(40))
    dbxref_type = Column(String(40))
    dbxref_url = Column(String(500))
    biosample = Column(String(500))
    strain_name = Column(String(500))
    description = Column(String(500))
    assay_id = Column(ForeignKey('nex.obi.obi_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    dbxref_url = Column(String(12), nullable=False)

    dataset = relationship('Dataset')
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')
    assay = relationship('Obi')

class Datasettrack(Base):
    __tablename__ = 'datasettrack'
    __table_args__ = {'schema': 'nex'}

    datasettrack_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    dataset_id = Column(ForeignKey('nex.dataset.dataset_id', ondelete='CASCADE'), nullable=False, index=True)
    track_order = Column(BigInteger, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dataset = relationship('Dataset')
    source = relationship('Source')


class Dbentity(Base):
    __tablename__ = 'dbentity'
    __table_args__ = (
        UniqueConstraint('format_name', 'subclass'),
        {'schema': 'nex'}
    )

    dbentity_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id'), nullable=False, index=True)
    bud_id = Column(Integer)
    sgdid = Column(String(20), nullable=False, unique=True)
    subclass = Column(String(40), nullable=False)
    dbentity_status = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')

class Pathwaydbentity(Dbentity):
    __tablename__ = 'pathwaydbentity'
    __table_args__ = {'schema': 'nex'}

    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    biocyc_id = Column(String(40))


class Referencedbentity(Dbentity):
    __tablename__ = 'referencedbentity'
    __table_args__ = {'schema': 'nex'}
    __url_segment__ = '/reference/'

    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    method_obtained = Column(String(40), nullable=False)
    publication_status = Column(String(40), nullable=False)
    fulltext_status = Column(String(40), nullable=False)
    citation = Column(String(500), nullable=False, unique=True)
    year = Column(SmallInteger, nullable=False)
    pmid = Column(BigInteger, unique=True)
    pmcid = Column(String(20), unique=True)
    date_published = Column(String(40))
    date_revised = Column(DateTime)
    issue = Column(String(100))
    page = Column(String(40))
    volume = Column(String(40))
    title = Column(String(400))
    doi = Column(String(100))
    journal_id = Column(ForeignKey('nex.journal.journal_id', ondelete='SET NULL'), index=True)
    book_id = Column(ForeignKey('nex.book.book_id', ondelete='SET NULL'), index=True)

    book = relationship('Book')
    journal = relationship('Journal')

    go_blacklist = None

    # takes a PMID and deleted matching entried from REFERENCETRIAGE and REFERENCEDELETED, raises error if found in REFERENCEDBENTITY
    @classmethod
    def clear_from_triage_and_deleted(Referencedbentity, user_pmid, username):
        curator_session = None
        try:
            curator_session = get_curator_session(username)
            exists = curator_session.query(Referencedbentity).filter(Referencedbentity.pmid==user_pmid).one_or_none()
            if exists:
                raise ValueError('Reference already exists.')
            curator_session.query(Referencedeleted).filter_by(pmid=user_pmid).delete(synchronize_session=False)
            curator_session.query(Referencetriage).filter_by(pmid=user_pmid).delete(synchronize_session=False)
            transaction.commit()
        except Exception as e:
            traceback.print_exc()
            transaction.abort()
            raise(e)
        finally:
            if curator_session:
                curator_session.close()

    # See if in referencedeleted or referencetriage and return string describing error to see if curators really want to add. Returns None if no errors
    @classmethod
    def get_deletion_warnings(Referencedbentity, user_pmid):
        ref_deleted = DBSession.query(Referencedeleted).filter_by(pmid=user_pmid).scalar()
        is_in_triage = DBSession.query(Referencetriage).filter_by(pmid=user_pmid).count()
        is_in_ref = DBSession.query(Referencedbentity).filter_by(pmid=user_pmid).count()
        if ref_deleted:
            return 'Warning: previously deleted: ' + ref_deleted.reason_deleted + 'by ' + ref_deleted.created_by
        elif is_in_triage:
            return 'Warning: in triage'
        elif is_in_ref:
            return 'Warning: already in database'
        else:
            return None

    @staticmethod
    def get_go_blacklist_ids():
        if Referencedbentity.go_blacklist is None:
            blacklist = []
            for x in DBSession.query(ReferenceAlias.reference_id).filter_by(alias_type="GO reference ID").all():
                blacklist.append(x.reference_id)
            Referencedbentity.go_blacklist = blacklist
        return Referencedbentity.go_blacklist

    def to_bibentry(self):
        entries = []

        data = [("PMID", self.pmid),
                ("STAT", self.publication_status),
                ("DP", self.date_published),
                ("TI", self.title),
                ("SO", self.method_obtained),
                ("LR", self.date_revised),
                ("IP", self.issue),
                ("PG", self.page),
                ("VI", self.volume),
                ("SO", "SGD")
        ]

        for x in DBSession.query(Referenceauthor).filter_by(reference_id=self.dbentity_id).order_by(Referenceauthor.author_order).all():
            data.append(("AU", x.display_name))

        for x in DBSession.query(Referencetype).filter_by(reference_id=self.dbentity_id).all():
            data.append(("PT", x.display_name))

        for x in DBSession.query(Referencedocument).filter(and_(Referencedocument.reference_id==self.dbentity_id, Referencedocument.document_type=="Abstract")).all():
            data.append(("AB", x.text))

        if self.journal is not None:
            data.append(("TA", self.journal.med_abbr))
            data.append(("JT", self.journal.title))
            data.append(("IS", self.journal.issn_print))

        if self.book is not None:
            data.append(("BTI", self.book.title))
            data.append(("VTI", self.book.volume_title))
            data.append(("ISBN", self.book.isbn))

        for d in data:
            if d[1] is not None:
                entries.append(d[0] + " - " + str(d[1]))

        return {
            "id": self.dbentity_id,
            "text": '\n'.join(entries)
        }

    def to_dict_citation(self):
        if(self.pmid == 23241746):
            print('found pmid')
        obj = {
            "id": self.dbentity_id,
            "display_name": self.display_name,
            "citation": self.citation,
            "pubmed_id": self.pmid,
            "link": self.obj_url,
            "year": self.year,
            "urls": []
        }

        ref_urls = DBSession.query(ReferenceUrl).filter_by(reference_id=self.dbentity_id).all()
        for url in ref_urls:
            obj["urls"].append({
                "display_name": url.display_name,
                "link": url.obj_url,
            })

        return obj

    def to_dict_reference_related(self):
        obj = {
            "id": self.dbentity_id,
            "display_name": self.display_name,
            "link": self.obj_url,
            "citation": self.citation,
            "pubmed_id": self.pmid,
            "abstract": None,
            "year": self.year,
            "reftypes": [],
            "urls": []
        }

        ref_urls = DBSession.query(ReferenceUrl).filter_by(reference_id=self.dbentity_id).all()
        for url in ref_urls:
            obj["urls"].append({
                "display_name": url.display_name,
                "link": url.obj_url,
            })

        abstract = DBSession.query(Referencedocument).filter_by(reference_id=self.dbentity_id, document_type="Abstract").one_or_none()
        if abstract:
            obj["abstract"] = {
                "text": abstract.html
            }

        reftypes = DBSession.query(Referencetype).filter_by(reference_id=self.dbentity_id).all()
        for ref in reftypes:
            obj["reftypes"].append({
                "display_name": ref.display_name
            })

        return obj

    def to_dict(self):
        obj = {
            "display_name": self.display_name,
            "citation": self.citation,
            "abstract": None,
            "link": self.obj_url,
            "pubmed_id": self.pmid,
            "journal": None,
            "sgdid": self.sgdid,
            "year": self.year,
            "id": self.dbentity_id,

            "related_references": [],
            "expression_datasets": [],
            "downloadable_files": []
        }

        if self.pmid != None and self.journal:
            obj["journal"] = {
                "med_abbr": self.journal.med_abbr
            }
        
        datasets = DBSession.query(DatasetReference).filter_by(reference_id=self.dbentity_id).all()
        obj["expression_datasets"] = [data.dataset.to_dict(self) for data in datasets]

        files = DBSession.query(ReferenceFile).filter_by(reference_id=self.dbentity_id).all()
        obj["downloadable_files"] = [data.file.to_dict() for data in files]

        abstract = DBSession.query(Referencedocument).filter_by(reference_id=self.dbentity_id, document_type="Abstract").one_or_none()
        if abstract:
            obj["abstract"] = {
                "text": abstract.html
            }

        ref_urls = DBSession.query(ReferenceUrl).filter_by(reference_id=self.dbentity_id).all()
        ref_urls_obj = []
        for url in ref_urls:
            ref_urls_obj.append({
                "display_name": url.display_name,
                "link": url.obj_url,
            })
        obj["urls"] = ref_urls_obj

        reference_types = DBSession.query(Referencetype).filter_by(reference_id=self.dbentity_id).all()
        obj["reftypes"] = []
        for type in reference_types:
            obj["reftypes"].append({
                "display_name": type.display_name
            })

        authors = DBSession.query(Referenceauthor.display_name, Referenceauthor.obj_url).filter_by(reference_id=self.dbentity_id).order_by(Referenceauthor.author_order).all()
        obj["authors"] = []
        for author in authors:
            obj["authors"].append({
                "display_name": author[0],
                "link": author[1]
            })

        reference_relation_parent = DBSession.query(ReferenceRelation).filter_by(parent_id=self.dbentity_id).all()
        for ref in reference_relation_parent:
            obj["related_references"].append(ref.child.to_dict_reference_related())

        reference_relation_child = DBSession.query(ReferenceRelation).filter_by(child_id=self.dbentity_id).all()
        for ref in reference_relation_child:
            obj["related_references"].append(ref.parent.to_dict_reference_related())

        obj["counts"] = {
            "interaction": DBSession.query(Physinteractionannotation).filter_by(reference_id=self.dbentity_id).count() + DBSession.query(Geninteractionannotation).filter_by(reference_id=self.dbentity_id).count(),
            "go": DBSession.query(Goannotation).filter_by(reference_id=self.dbentity_id).count(),
            "phenotype": DBSession.query(Phenotypeannotation).filter_by(reference_id=self.dbentity_id).count(),
            "disease": DBSession.query(Diseaseannotation).filter_by(reference_id=self.dbentity_id).count(),
            "complement": DBSession.query(Functionalcomplementannotation).filter_by(reference_id=self.dbentity_id).count(),
            "regulation": DBSession.query(Regulationannotation).filter_by(reference_id=self.dbentity_id).count(),
            "ptms":DBSession.query(Posttranslationannotation).filter_by(reference_id=self.dbentity_id).count()
        }

        return obj

    def annotations_to_dict(self):
        
        annotations = DBSession.query(Literatureannotation).filter_by(reference_id=self.dbentity_id).all()

        loci = []
        complexes = []
        pathways = []
        alleles = []
        for annotation in annotations:
            annotation_dict = annotation.to_dict()
            if annotation_dict["locus"] is not None:
                locus = annotation_dict["locus"]
                if 'complex' in locus["link"]:
                    complexes.append(annotation.to_dict())
                elif 'pathway' in locus["link"]:
                    pathways.append(annotation.to_dict())
                elif 'allele' in locus["link"]:
                    alleles.append(annotation.to_dict()) 
                else:
                    loci.append(annotation.to_dict())

        return loci + complexes + pathways + alleles
    
    def annotations_summary_to_dict(self):
        preview_url = '/reference/' + self.sgdid
        return {
            'category': 'reference',
            'created_by' : self.created_by,
            'href': preview_url,
            'date_created': self.date_created.strftime("%Y-%m-%d"),
            'time_created': self.date_created.isoformat(),
            'name': self.citation,
            'type': 'added',
            'tags': self.get_tags()
        }

    def interactions_to_dict(self):
        obj = []

        interactions = DBSession.query(Physinteractionannotation).filter_by(reference_id=self.dbentity_id).all() + DBSession.query(Geninteractionannotation).filter_by(reference_id=self.dbentity_id).all()
        
        return [interaction.to_dict(self) for interaction in interactions]

    def go_to_dict(self):
        obj = []

        gos = DBSession.query(Goannotation).filter_by(reference_id=self.dbentity_id).all()

        for go_annotation in gos:
            for annotation in go_annotation.to_dict():
                if annotation not in obj:
                    obj.append(annotation)

        return obj

    def functional_complement_to_dict(self):

        all_annotations = DBSession.query(Functionalcomplementannotation).filter_by(reference_id=self.dbentity_id).all()

        return [a.to_dict(self.dbentity_id) for a in all_annotations]
    
    def phenotype_to_dict(self):
        phenotypes = DBSession.query(Phenotypeannotation).filter_by(reference_id=self.dbentity_id).all()

        obj = []
        for phenotype in phenotypes:
            obj += phenotype.to_dict(reference=self)
        return obj

    def disease_to_dict(self):
        do_annotations = DBSession.query(Diseaseannotation).filter_by(reference_id=self.dbentity_id).all()

        obj = []

        for do_annotation in do_annotations:
            for annotation in do_annotation.to_dict():
                if annotation not in obj:
                    obj.append(annotation)
        # get human gene symbols from Alliance API
        #human_gene_ids_to_symbols = {}
        human_gene_ids_to_symbols = {'display name' : 'TEST1'}
        for x in obj:
            try:
                for y in x['properties']:
                    if 'bioentity' in list(y.keys()):
                        entry = y['bioentity']
                        hgnc_id = entry['display_name']
                        if hgnc_id in list(human_gene_ids_to_symbols.keys()):
                            entry['display_name'] = human_gene_ids_to_symbols[hgnc_id]
                        else:
                            url = ALLIANCE_API_BASE_URL + hgnc_id
                            symbol = requests.request('GET', url).json()['symbol']
                            entry['display_name'] = symbol
                            human_gene_ids_to_symbols[hgnc_id] = symbol
            except Exception as e:
                traceback.print_exc()
        return obj

    def regulation_to_dict(self):
        obj = []

        regulations = DBSession.query(Regulationannotation).filter_by(reference_id=self.dbentity_id).all()

        return [regulation.to_dict(self) for regulation in regulations]

    def get_secondary_cache_urls(self, is_quick=False):
        base_url = self.get_base_url()
        url1 = base_url + '/literature_details'
        return [url1]

    def get_tags(self):

        tags = []

        ## for gene names vs CurationReference
        curation_refs = DBSession.query(CurationReference, Locusdbentity).filter_by(reference_id=self.dbentity_id).outerjoin(Locusdbentity).all()
        for x in curation_refs:
            locus_name = None
            locus = x.Locusdbentity
            if locus:
                locus_name = locus.get_name()
            obj = {
                'name': x.CurationReference.get_name(),
                'dbentity_name': locus_name,
                'comment': x.CurationReference.curator_comment
            }
            tags.append(obj)

        ## for complex vs CurationReference
        curation_refs = DBSession.query(CurationReference, Complexdbentity).filter_by(reference_id=self.dbentity_id).outerjoin(Complexdbentity).all()
        for x in curation_refs:
            complex_name = None
            complex = x.Complexdbentity
            if complex:
                complex_name = complex.format_name
            obj = {
                'name': x.CurationReference.get_name(),
                'dbentity_name': complex_name,
                'comment': x.CurationReference.curator_comment
            }
            tags.append(obj)

        ## for pathway vs CurationReference
        curation_refs = DBSession.query(CurationReference, Pathwaydbentity).filter_by(reference_id=self.dbentity_id).outerjoin(Pathwaydbentity).all()
        for x in curation_refs:
            pathway_name = None
            pathway = x.Pathwaydbentity
            if pathway:
                pathway_name = pathway.biocyc_id
            obj = {
                'name': x.CurationReference.get_name(),
                'dbentity_name': pathway_name,
                'comment': x.CurationReference.curator_comment
            }
            tags.append(obj)

        ## for allele vs CurationReference
        curation_refs = DBSession.query(CurationReference, Alleledbentity).filter_by(reference_id=self.dbentity_id).outerjoin(Alleledbentity).all()
        for x in curation_refs:
            allele_name = None
            allele = x.Alleledbentity
            if allele:
                allele_name = allele.format_name
            obj = {
                'name': x.CurationReference.get_name(),
                'dbentity_name': allele_name,
                'comment': x.CurationReference.curator_comment
            }
            tags.append(obj)
            
        ## Literatureannotation
        items = []
        lit_annotations = DBSession.query(Literatureannotation, Locusdbentity).filter_by(reference_id=self.dbentity_id).outerjoin(Locusdbentity).all()
        for x in lit_annotations:
            locus_name = None
            locus = x.Locusdbentity
            if locus:
                locus_name = locus.get_name()
            name = x.Literatureannotation.get_name()
            items.append((name, locus_name))

        lit_annotations = DBSession.query(Literatureannotation, Complexdbentity).filter_by(reference_id=self.dbentity_id).outerjoin(Complexdbentity).all()
        for x in lit_annotations:
            complex_name = None
            complex = x.Complexdbentity
            if complex:
                complex_name = complex.format_name
            name = x.Literatureannotation.get_name()
            items.append((name, complex_name))

        lit_annotations = DBSession.query(Literatureannotation, Pathwaydbentity).filter_by(reference_id=self.dbentity_id).outerjoin(Pathwaydbentity).all()
        for x in lit_annotations:
            pathway_name = None
            pathway= x.Pathwaydbentity
            if pathway:
                pathway_name = pathway.biocyc_id
            name = x.Literatureannotation.get_name()
            items.append((name, pathway_name))

        lit_annotations = DBSession.query(Literatureannotation, Alleledbentity).filter_by(reference_id=self.dbentity_id).outerjoin(Alleledbentity).all()
        for x in lit_annotations:
            allele_name = None
            allele= x.Alleledbentity
            if allele:
                allele_name = allele.format_name
            name = x.Literatureannotation.get_name()                                                        
            items.append((name, allele_name))

        for (name, dbentity_name) in items:
            # ignore omics tags bc already have internal   
            if name in ['non_phenotype_htp', 'htp_phenotype']:
                continue
            # Don't append to tags if it is a primary and already in tags.  
            if name in ['other_primary', 'go', 'classical_phenotype', 'headline_information']:
                found = 0
                for tag in tags:
                    if tag['name'] in ['go', 'classical_phenotype', 'headline_information'] and tag['dbentity_name'] == dbentity_name:
                        found = 1
                        break
                if found == 0:
                    # it is a other_primary tag since it is not one of ['go', 'classical_phenotype', 'headline_information']
                    tags.append(
                        { 'name':  'other_primary',
                          'dbentity_name': dbentity_name,
                          'comment': None
                    })
            else:
                tags.append(
                    { 'name':  name,
                      'dbentity_name': dbentity_name,
                      'comment': None
                    })
                
        ###################################################
        tag2dbentityNames = {}
        tag2comments = {}
        for x in tags:
            tag = x['name']
            dbentity_name = x['dbentity_name']
            comment = x['comment']
            dbentity_names = []
            if tag in tag2dbentityNames:
                dbentity_names = tag2dbentityNames[tag]
            if dbentity_name and dbentity_name not in dbentity_names:
                dbentity_names.append(dbentity_name)
            tag2dbentityNames[tag] = dbentity_names
            comments = []
            if tag in tag2comments:
                comments = tag2comments[tag]
            if comment and comment not in comments:
                comments.append(comment)
            tag2comments[tag] = comments

        tag_list = []    
        for tag in tag2dbentityNames:
            dbentity_names = tag2dbentityNames[tag]
            comments = tag2comments[tag]
            dbentity_str = SEPARATOR.join(dbentity_names)
            comment_str = "; ".join(comments)
            tag_list.append({
                    'name': tag,
                    'genes': dbentity_str,
                    'comment': comment_str
            })
        return tag_list

    def update_tags(self, tags, username):
        curator_session = None
        try:
            curator_session = get_curator_session(username)
            tags = validate_tags(tags)
            # delete old tags
            curator_session.query(CurationReference).filter_by(reference_id=self.dbentity_id).delete(synchronize_session=False)
            curator_session.query(Literatureannotation).filter_by(reference_id=self.dbentity_id).delete(synchronize_session=False)
            transaction.commit()
            curator_session.flush()
            # track which loci have primary annotations for this reference to only have one primary per reference
            primary_gene_ids = []
            has_omics = False
            for tag in tags:
                name = tag['name']
                comment = tag['comment']
                if comment == '':
                    comment = None
                raw_genes = tag['genes'].strip()
                gene_ids = []

                # add tags by gene
                if len(raw_genes):
                    gene_ids = raw_genes.strip().split()
                    # ignore duplicates
                    gene_ids = list(set(gene_ids))
                    tag_dbentity_ids = []
                    for g_id in gene_ids:
                        g_id = g_id.strip()
                        if g_id == '':
                            continue
                        upper_g_id = g_id.upper()

                        gene_dbentity_id = None
                        ## check for gene name/systematc name
                        row = curator_session.query(Locusdbentity).filter(or_(Locusdbentity.display_name == upper_g_id, Locusdbentity.format_name == g_id)).one_or_none()
                        if row:
                            gene_dbentity_id = row.dbentity_id

                        ## check for complex ID
                        if gene_dbentity_id is None:
                            row = curator_session.query(Dbentity).filter_by(format_name=upper_g_id, subclass='COMPLEX').one_or_none()
                            if row:
                                gene_dbentity_id = row.dbentity_id

                        ## check for pathway ID
                        if gene_dbentity_id is None:
                            row = curator_session.query(Pathwaydbentity).filter_by(biocyc_id=upper_g_id).one_or_none()
                            if row:
                                gene_dbentity_id = row.dbentity_id
                        
                        ## check for allele name
                        if gene_dbentity_id is None:
                            row = curator_session.query(Alleledbentity).filter(Alleledbentity.display_name.ilike(upper_g_id)).one_or_none()
                            if row:
                                gene_dbentity_id = row.dbentity_id
                            
                        # ignore duplicates
                        if gene_dbentity_id in tag_dbentity_ids:
                            continue
                        if gene_dbentity_id is None:
                            continue
                        tag_dbentity_ids.append(gene_dbentity_id)
                        
                        curation_ref = CurationReference.factory(self.dbentity_id, name, comment, gene_dbentity_id, username)
                        if curation_ref:
                            curator_session.add(curation_ref)
                            
                        # add primary lit annotation
                        lit_annotation = Literatureannotation.factory(self.dbentity_id, name, gene_dbentity_id, username)
                        if lit_annotation:
                            # only make a single primary tag
                            if lit_annotation.topic == 'Primary Literature':
                                if gene_dbentity_id in primary_gene_ids:
                                    continue
                                else:
                                    primary_gene_ids.append(gene_dbentity_id)
                            curator_session.add(lit_annotation)
                # add a tag with no gene
                else:
                    curation_ref = CurationReference.factory(self.dbentity_id, name, comment, None, username)
                    if curation_ref:
                        curator_session.add(curation_ref)
                    lit_annotation = Literatureannotation.factory(self.dbentity_id, name, None, username)
                    if lit_annotation:
                        # only make a single omics tag
                        if lit_annotation.topic == 'Omics':
                            if has_omics:
                                continue
                            else:
                                has_omics = True
                        curator_session.add(lit_annotation)
            transaction.commit()
            self.sync_to_curate_activity(username)
        except Exception as e:
            traceback.print_exc()
            transaction.abort()
            curator_session.rollback()
            raise(e)
        finally:
            if curator_session:
                curator_session.close()

    def sync_to_curate_activity(self, username):
        tags_obj = self.get_tags()
        try:
            curator_session = get_curator_session(username)
            existing = curator_session.query(CuratorActivity).filter(CuratorActivity.dbentity_id == self.dbentity_id).one_or_none()
            message = 'added'
            if existing:
                curator_session.delete(existing)
                message = 'updated'
            diplay_name = self.display_name + ' PMID: ' + str(self.pmid)
            new_curate_activity = CuratorActivity(
                display_name = diplay_name,
                obj_url = self.obj_url,
                activity_category = 'reference',
                dbentity_id = self.dbentity_id,
                message = message,
                json = json.dumps({ 'tags': tags_obj, 'modified_date':str(datetime.now())}),
                created_by = username
            )
            curator_session.add(new_curate_activity)
            transaction.commit()
        except Exception as e:
            traceback.print_exc()
            transaction.abort()
            raise(e)
        finally:
            if curator_session:
                curator_session.close()

    # does not delete annotations
    def delete_with_children(self, username):
        curator_session = None
        try:
            curator_session = get_curator_session(username)
            self = curator_session.merge(self)
            ref_aliases = curator_session.query(ReferenceAlias).filter(ReferenceAlias.reference_id == self.dbentity_id)
            ref_aliases.delete(synchronize_session=False)
            ref_authors = curator_session.query(Referenceauthor).filter(Referenceauthor.reference_id == self.dbentity_id)
            ref_authors.delete(synchronize_session=False)
            ref_docs = curator_session.query(Referencedocument).filter(Referencedocument.reference_id == self.dbentity_id)
            ref_docs.delete(synchronize_session=False)
            ref_types = curator_session.query(Referencetype).filter(Referencetype.reference_id == self.dbentity_id)
            ref_types.delete(synchronize_session=False)
            ref_urls = curator_session.query(ReferenceUrl).filter(ReferenceUrl.reference_id == self.dbentity_id)
            ref_urls.delete(synchronize_session=False)
            ref_unlinks = curator_session.query(Referenceunlink).filter(Referenceunlink.reference_id == self.dbentity_id)
            ref_unlinks.delete(synchronize_session=False)
            locus_refs = curator_session.query(LocusReferences).filter(LocusReferences.reference_id == self.dbentity_id)
            locus_refs.delete(synchronize_session=False)
            ref_files = curator_session.query(ReferenceFile).filter(ReferenceFile.reference_id == self.dbentity_id)
            ref_files.delete(synchronize_session=False)
            curate_act = curator_session.query(CuratorActivity).filter(CuratorActivity.dbentity_id == self.dbentity_id)
            curate_act.delete(synchronize_session=False)
            curator_session.delete(self)
            transaction.commit()
        except Exception as e:
            traceback.print_exc()
            transaction.abort()
            raise(e)
        finally:
            if curator_session:
                curator_session.close()


    def get_all_annotations(self, username):

        curator_session = None
        annotation_list = dict()

        self.returnValue = {
            "annotations":[],
            "not_annotations":[]
        }
        def helper(key,items):
            val = None

            try:
                obj = {}
                values = []
                for item in items:
                    val = item
                    values.append(item.__dict__)
                    if '_sa_instance_state' in values[-1]:
                        values[-1].pop('_sa_instance_state')
                    if 'date_created' in values[-1]:
                        values[-1].pop('date_created')
                    if 'date_assigned' in values[-1]:
                        values[-1].pop('date_assigned')
                    if 'source_id' in values[-1]:
                        values[-1].pop('source_id')
                    if 'bud_id' in values[-1]:
                        values[-1].pop('bud_id')
                    if 'taxonomy_id' in values[-1]:
                        values[-1].pop('taxonomy_id')
                if len(values) > 0:
                    obj[key] = values
                    self.returnValue['annotations'].append(obj)


            except Exception as ex:
                log.exception(ex)

        def get_count(table_name,key):
            count = curator_session.query(table_name).filter_by(reference_id=self.dbentity_id).count()
            if count >0 :
                self.returnValue['not_annotations'].append({key: count})

        try:
            curator_session = get_curator_session(username)

            binding_motif = curator_session.query(Bindingmotifannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Bindingmotifannotation",binding_motif)

            literature_annot = curator_session.query(Literatureannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Literatureannotation",literature_annot)

            disease_annot = curator_session.query(Diseaseannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Diseaseannotation",disease_annot)

            disease_subset_annot = curator_session.query(Diseasesubsetannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Diseasesubsetannotation",disease_subset_annot)

            dnaseq_annot = curator_session.query(Dnasequenceannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Dnasequenceannotation",dnaseq_annot)

            enzyme_annot = curator_session.query(Enzymeannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Enzymeannotation",enzyme_annot)

            expression_annot = curator_session.query(Expressionannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Expressionannotation",expression_annot)

            goslim_annot = curator_session.query(Goslimannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Goslimannotation",goslim_annot)

            pathway_annot = curator_session.query(Pathwayannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Pathwayannotation",pathway_annot)

            phenotype_annot = curator_session.query(Phenotypeannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Phenotypeannotation",phenotype_annot)

            posttranslation_annot = curator_session.query(Posttranslationannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Posttranslationannotation",posttranslation_annot)

            proteindomain_annot = curator_session.query(Proteindomainannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Proteindomainannotation",proteindomain_annot)

            proteinexpt_annot = curator_session.query(Proteinexptannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Proteinexptannotation",proteinexpt_annot)

            proteinseq_annot = curator_session.query(Proteinsequenceannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Proteinsequenceannotation",proteinseq_annot)

            regulation_annot = curator_session.query(Regulationannotation).filter_by(reference_id=self.dbentity_id).all()
            helper("Regulationannotation",regulation_annot)

            # Table that are not annotations.
            # author_response = curator_session.query(Authorresponse).filter_by(reference_id=self.dbentity_id)
            # contignote_ref = curator_session.query(Contignoteannotation).filter_by(reference_id=self.dbentity_id).all()

            get_count(Geninteractionannotation,"Geninteractionannotation")
            get_count(Goannotation,"Goannotation")
            get_count(Physinteractionannotation,"Physinteractionannotation")
            get_count(ColleagueReference,"ColleagueReference")

            get_count(CurationReference,"CurationReference")
            get_count(DatasetReference,"DatasetReference")
            get_count(LocusReferences,"LocusReferences")
            get_count(LocusAliasReferences,"LocusAliasReferences")
            get_count(LocusnoteReference,"LocusnoteReference")
            get_count(LocusRelationReference,"LocusRelationReference")
            get_count(LocussummaryReference,"LocussummaryReference")
            get_count(PathwaysummaryReference,"PathwaysummaryReference")
            get_count(Reservedname,"Reservedname")
            get_count(StrainsummaryReference,"StrainsummaryReference")
            get_count(ReferenceAlias,"ReferenceAlias")
            get_count(ReferenceUrl,"ReferenceUrl")
            get_count(Referenceauthor,"Referenceauthor")
            get_count(Referencedocument,"Referencedocument")
            get_count(Referencetype,"Referencetype")
            get_count(Referenceunlink,"Referenceunlink")
            get_count(ReferenceFile,"ReferenceFile")

            return self.returnValue

        except Exception as e:
            traceback.print_exc()
            transaction.abort()
            curator_session.rollback()
            raise(e)
        finally:
            if curator_session:
                curator_session.close()            

class FilePath(Base):
    __tablename__ = 'file_path'
    __table_args__ = {'schema': 'nex'}

    file_path_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    file_id = Column(ForeignKey('nex.filedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    path_id = Column(ForeignKey('nex.path.path_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    source = relationship('Source')

class Path(Base):
    __tablename__ = 'path'
    __table_args__ = (UniqueConstraint('path_id', 'path'),{'schema': 'nex'})
    path_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    path = Column(String(500), nullable=False)
    description = Column(String(1000), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')

    def path_to_dict(self):
        obj = {
            "description": self.description
        }
        return obj


class Filedbentity(Dbentity):
    __tablename__ = 'filedbentity'
    __table_args__ = {'schema': 'nex'}

    dbentity_id = Column(
        ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'),
        primary_key=True,
        server_default=text("nextval('nex.object_seq'::regclass)"))
    topic_id = Column(
        ForeignKey('nex.edam.edam_id', ondelete='CASCADE'),
        nullable=False,
        index=True)
    data_id = Column(
        ForeignKey('nex.edam.edam_id', ondelete='CASCADE'),
        nullable=False,
        index=True)
    format_id = Column(
        ForeignKey('nex.edam.edam_id', ondelete='CASCADE'),
        nullable=False,
        index=True)
    file_extension = Column(String(10), nullable=False)
    file_date = Column(DateTime, nullable=False)
    is_public = Column(Boolean, nullable=False)
    is_in_spell = Column(Boolean, nullable=False)
    is_in_browser = Column(Boolean, nullable=False)
    md5sum = Column(String(32), index=True)
    readme_file_id = Column(
        ForeignKey('nex.filedbentity.dbentity_id', ondelete='CASCADE'),
        index=True)
    previous_file_name = Column(String(100))
    s3_url = Column(String(500))
    description = Column(String(4000))
    json = Column(Text)
    year = Column(SmallInteger, nullable=False)
    file_size = Column(SmallInteger)
    data = relationship(
        'Edam', primaryjoin='Filedbentity.data_id == Edam.edam_id')
    format = relationship(
        'Edam', primaryjoin='Filedbentity.format_id == Edam.edam_id')
    readme_file = relationship(
        'Filedbentity',
        foreign_keys=[dbentity_id],
        primaryjoin='Filedbentity.dbentity_id == Filedbentity.readme_file_id', uselist=False)
    topic = relationship(
        'Edam', primaryjoin='Filedbentity.topic_id == Edam.edam_id')

    def to_dict(self):
        mod_s3_url = ''
        readme_s3 = None
        if self.s3_url:
            mod_s3_url = re.sub(
                r'\?.+', '', self.s3_url).replace(':433', '').strip()
        
        if self.readme_file:
            readme_s3 = re.sub(r'\?.+', '', self.readme_file.s3_url).replace(':433', '').strip()

        obj = {
            "id":
                self.dbentity_id,
            "data_id":
                self.data_id if self.format_id else 0,
            "format_id":
                self.format_id if self.format_id else 0,
            "readme_file_id":
                self.readme_file_id if self.readme_file_id else '',
            "file_size":
                self.file_size if self.file_size else 0,
            "data":
                self.data.to_dict() if self.data else '',
            "format":
                self.format.to_dict() if self.format else '',
            "is_public":
                str(self.is_public),
            "file_extension":
                self.file_extension if self.file_extension else '',
            "topic":
                self.topic.to_dict() if self.topic else '',
            "s3_url": mod_s3_url,
            "description": self.description if self.description else '',
            "year": self.year,
            "display_name": self.display_name,
            "status": self.dbentity_status,
            "readme_file_url": readme_s3
        }
        return obj


    def to_simple_dict(self):
        readme_s3 = None
        s3_url = ''
        
        if self.s3_url:
            s3_url = re.sub(r'\?.+', '', self.s3_url).replace(':433', '').strip()
        if self.readme_file:
            readme_s3 = re.sub(r'\?.+', '', self.readme_file.s3_url).replace(':433', '').strip()

        obj = {
            "id":
                self.dbentity_id,
            "data_id":
                self.data_id if self.format_id else 0,
            "format_id":
                self.format_id if self.format_id else 0,
            "readme_file_id":
                self.readme_file_id if self.readme_file_id else '',
            "file_size":
                self.file_size if self.file_size else 0,
            "is_public":
                str(self.is_public),
            "file_extension":
                self.file_extension if self.file_extension else '',
            "s3_url": s3_url,
            "description": self.description if self.description else '',
            "year": self.year,
            "display_name": self.display_name,
            "status": self.dbentity_status,
            "readme_file_url": readme_s3
        }
        return obj

    def upload_file_to_s3(self, file, filename, is_web_file=False, file_path=None, flag=True):


        try:
            s3_path = self.sgdid + '/' + filename
            s3_url = upload_one_file_to_s3(file, s3_path)
            self.s3_url = s3_url
        except Exception as e:
            logging.error(e, exc_info=True)
        return


    
        ## we can get rid of the following code when everything is working good  

        try:
            # get s3_url and upload
            s3_path = self.sgdid + '/' + filename
            if file_path:
                new_s3_file = simple_s3_upload(file_path, s3_path, True)
                conn = boto.connect_s3(S3_ACCESS_KEY, S3_SECRET_KEY)
                bucket = conn.get_bucket(S3_BUCKET)
                k = Key(bucket)
                k.key = s3_path
                file_s3 = bucket.get_key(k.key)
                etag_md5_s3 = file_s3.etag.strip('"').strip("'")
                file.seek(0)
                mod_s3_url = file_s3.generate_url(
                    expires_in=0, query_auth=False)
                # multipart upload adds parts to 32 bit string making it break db constraint
                # e.g: "md5sumgibberish-1000"
                if "-" in etag_md5_s3:
                    self.md5sum = etag_md5_s3.split('-')[0]
                else:
                    self.md5sum = etag_md5_s3
                # get file size
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                self.file_size = file_size
                self.s3_url = re.sub(r'\?.+', '', mod_s3_url).replace(':433', '').strip()
                #TODO: Remove this after optimization of querries
                if flag:
                    # multiplte commits are fluching pending transactions
                    transaction.commit()
    
            else:
                conn = boto.connect_s3(S3_ACCESS_KEY, S3_SECRET_KEY)
                bucket = conn.get_bucket(S3_BUCKET)
                k = Key(bucket)
                k.key = s3_path
                # make content-type 'text/plain' if it's a README
                if self.readme_file_id is None:
                    k.content_type = 'text/plain'
                file_bytes = io.BytesIO(file.read())
                k.set_contents_from_file(file_bytes, rewind=True)
                k.make_public()
                file_s3 = bucket.get_key(k.key)
        
                # get local md5sum https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
                hash_md5 = hashlib.md5()
                local_md5 = get_checksum(file)
                file.seek(0)
                for chunk in iter(lambda: file.read(4096), b""):
                    hash_md5.update(chunk)
                local_md5sum = hash_md5.hexdigest()
                file.seek(0)

                if self.md5sum != local_md5sum or is_web_file:
                    # self.md5sum = local_md5sum
                    # get file size
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    self.file_size = file_size
                    mod_s3_url = file_s3.generate_url(
                        expires_in=0, query_auth=False)
                    self.s3_url = re.sub(
                        r'\?.+', '', mod_s3_url).replace(':433', '').strip()
                    logging.info("Added file to s3")
                    return True
                return False
        except Exception as e:
            logging.error(e, exc_info=True)
            

    def get_path(self):
        path_res = DBSession.query(FilePath, Path).filter(
            FilePath.file_id == self.dbentity_id).outerjoin(Path).all()
        if len(path_res) == 0:
            return None
        base = path_res[0][1].path
        return base + '/' + self.display_name

    def get_path_id(self):
        path_res = DBSession.query(FilePath, Path).filter(
            FilePath.file_id == self.dbentity_id).outerjoin(Path).all()
        if not len(path_res):
            return None
        path = path_res[0][1]
        return path.path_id


class Locusdbentity(Dbentity):
    __tablename__ = 'locusdbentity'
    __table_args__ = {'schema': 'nex'}
    __url_segment__ = '/locus/'

    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    systematic_name = Column(String(40), nullable=False, unique=True)
    gene_name = Column(String(20))
    qualifier = Column(String(40))
    genetic_position = Column(Float)
    name_description = Column(String(100))
    headline = Column(String(70))
    description = Column(String(500))
    has_summary = Column(Boolean, nullable=False)
    has_sequence = Column(Boolean, nullable=False)
    has_history = Column(Boolean, nullable=False)
    has_literature = Column(Boolean, nullable=False)
    has_go = Column(Boolean, nullable=False)
    has_disease = Column(Boolean, nullable=False)
    has_phenotype = Column(Boolean, nullable=False)
    has_interaction = Column(Boolean, nullable=False)
    has_expression = Column(Boolean, nullable=False)
    has_regulation = Column(Boolean, nullable=False)
    has_protein = Column(Boolean, nullable=False)
    has_homology = Column(Boolean, nullable=False)
    has_sequence_section = Column(Boolean, nullable=False)
    not_in_s288c = Column(Boolean, nullable=False)

    @classmethod
    def get_s288c_genes(Locusdbentity):
        # get all dbentity_ids from dnasequenceannotation model
        all_dbentity_ids = DBSession.query(
            Dnasequenceannotation).filter(
                Dnasequenceannotation.taxonomy_id == TAXON_ID,
                Dnasequenceannotation.dna_type == 'GENOMIC').all()
        comp = [x.dbentity_id for x in all_dbentity_ids if x.dbentity.dbentity_status == 'Active' ]
        locus_data = DBSession.query(Locusdbentity).filter(Locusdbentity.dbentity_id.in_(comp),Locusdbentity.not_in_s288c == False).all()
        return locus_data

    # returns true of 3 letters and a number
    @classmethod
    def is_valid_gene_name(Locusdbentity, potential_name):
        gene_name_pattern = re.compile(r'\b[A-Z]{3}[0-9]+\b')
        return gene_name_pattern.match(potential_name)

    def regulation_target_enrichment(self):

        target_ids = []
        for x in DBSession.query(Regulationannotation).filter_by(regulator_id=self.dbentity_id).all():
            target_ids.append(x.target_id)
        format_names = []
        for x in DBSession.query(Dbentity).filter(Dbentity.dbentity_id.in_(target_ids)).all():
            format_names.append(x.format_name)

        genes = ",".join(format_names)
        data = urllib.parse.urlencode({
            "genes": genes,
            "aspect": "P"
        })
    
        try:
            req = Request(url=os.environ['BATTER_URI'], data=data.encode('utf-8'))
            res = urlopen(req)
            response_json = json.loads(res.read().decode('utf-8'))
        except:
            return []
        
        obj = []
        for row in response_json:
            obj.append({
                "go": {
                    "display_name": row["term"],
                    "link": '/go/' + row["goid"],
                    "id": row["goid"]
                },
                "match_count": row["num_gene_annotated"],
                "pvalue": row["pvalue"]
            })
        return obj


    def regulation_details(self):
        annotations = DBSession.query(Regulationannotation).filter(or_(Regulationannotation.target_id==self.dbentity_id, Regulationannotation.regulator_id==self.dbentity_id)).all()
        return [a.to_dict() for a in annotations]

    def binding_site_details(self):
        motifs = DBSession.query(Bindingmotifannotation).filter_by(dbentity_id=self.dbentity_id).all()

        return [m.to_dict() for m in motifs]

    def protein_domain_graph(self):
        main_gene_proteindomain_annotations = DBSession.query(Proteindomainannotation).filter_by(dbentity_id=self.dbentity_id).all()
        main_gene_proteindomain_ids = [a.proteindomain_id for a in main_gene_proteindomain_annotations]

        genes_sharing_proteindomain = DBSession.query(Proteindomainannotation).filter((Proteindomainannotation.proteindomain_id.in_(main_gene_proteindomain_ids)) & (Proteindomainannotation.dbentity_id != self.dbentity_id)).all()
        genes_to_proteindomain = {}
        for annotation in genes_sharing_proteindomain:
            gene = annotation.dbentity_id
            proteindomain = annotation.proteindomain_id
            if gene in genes_to_proteindomain:
                genes_to_proteindomain[gene].add(proteindomain)
            else:
                genes_to_proteindomain[gene] = set([proteindomain])

        list_genes_to_proteindomain = sorted([(g, genes_to_proteindomain[g]) for g in genes_to_proteindomain], key=lambda x: len(x[1]), reverse=True)

        edges = []
        nodes = {}

        edges_added = set([])

        nodes[self.format_name] = {
            "data": {
                "name": self.display_name,
                "id": self.format_name,
                "dbentity_id": self.dbentity_id, 
                "link": self.obj_url,
                "type": "BIOENTITY",
                "sub_type": "FOCUS"
            }
        }

        i = 0
        while i < len(list_genes_to_proteindomain) and len(nodes) <= 30 and len(edges) <= 50:
            dbentity = DBSession.query(Dbentity.display_name, Dbentity.format_name, Dbentity.dbentity_id, Dbentity.obj_url).filter_by(dbentity_id=list_genes_to_proteindomain[i][0]).one_or_none()

            proteindomain_ids = list_genes_to_proteindomain[i][1]

            if dbentity[1] not in nodes:
                nodes[dbentity[1]] = {
                    "data": {
                        "name": dbentity[0],
                        "id": dbentity[1],
                        "dbentity_id": dbentity[2],
                        "link": dbentity[3],
                        "type": "BIOENTITY"
                    }
                }

            for proteindomain_id in proteindomain_ids:
                proteindomain = DBSession.query(Proteindomain).filter_by(proteindomain_id=proteindomain_id).one_or_none()

                if proteindomain.format_name not in nodes:
                    nodes[proteindomain.format_name] = {
                        "data": {
                            "name": proteindomain.display_name,
                            "id": proteindomain.format_name,
                            "link": proteindomain.obj_url,
                            "type": "DOMAIN",
                            "source": proteindomain.source.display_name
                        }
                    }

                if (proteindomain.format_name + " " + dbentity[1]) not in edges_added:
                    edges.append({
                        "data": {
                            "source": proteindomain.format_name,
                            "target": dbentity[1]
                        }
                    })
                    edges_added.add(proteindomain.format_name + " " + dbentity[1])

                if (proteindomain.format_name + " " + self.format_name) not in edges_added:
                    edges.append({
                        "data": {
                            "source": proteindomain.format_name,
                            "target": self.format_name
                        }
                    })
                    edges_added.add(proteindomain.format_name + " " + self.format_name)

            i += 1

        return {
            "nodes": [nodes[n] for n in nodes],
            "edges": edges
        }


    def protein_domain_details(self):
        taxonomy_id = self.get_main_strain('taxonomy_id')
        annotations = DBSession.query(Proteindomainannotation).filter_by(dbentity_id=self.dbentity_id, taxonomy_id=taxonomy_id).all()

        return [a.to_dict(locus=self) for a in annotations]

    def protein_experiment_details(self):
        annotations = DBSession.query(Proteinexptannotation).filter_by(dbentity_id=self.dbentity_id).all()

        reference_ids = [a.reference_id for a in annotations]
        references = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(reference_ids)).all()

        ids_to_references = {}
        for r in references:
            ids_to_references[r.dbentity_id] = r

        return [a.to_dict(locus=self, references=ids_to_references) for a in annotations]

    def protein_abundance_details(self):
        annotations = DBSession.query(Proteinabundanceannotation).filter_by(dbentity_id=self.dbentity_id).all()
        new_reference_ids = [a.reference_id for a in annotations]
        orig_reference_ids = [a.original_reference_id for a in annotations]
        reference_ids = list(set(new_reference_ids + orig_reference_ids))
        references = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(reference_ids)).all()

        ids_to_references = {}
        for r in references:
            ids_to_references[r.dbentity_id] = r
        
        # return [a.to_dict(locus=self, references=ids_to_references) for a in annotations]
        data = [a.to_dict(locus=self, references=ids_to_references) for a in annotations] 
        return sorted(data, key=lambda d: d['order_by'])

    def ecnumber_details(self):
        aliases = DBSession.query(LocusAlias).filter(LocusAlias.locus_id == self.dbentity_id, LocusAlias.alias_type == "EC number").all()

        obj = []
        for alias in aliases:
            obj.append({
                "ecnumber": {
                    "display_name": alias.display_name,
                    "link": alias.obj_url
                }
            })
        return obj

    def complex_details(self):

        interactors = DBSession.query(Interactor).filter_by(locus_id = self.dbentity_id).all()   
        if len(interactors) == 0:
            rna_ids = DBSession.query(LocusAlias).filter_by(alias_type='RNAcentral ID', locus_id=self.dbentity_id).all()
            if len(rna_ids) == 0:
                return []
            interactors = DBSession.query(Interactor).filter_by(format_name = rna_ids[0].display_name).all()
            if len(interactors) == 0:
                return []

        interactor = interactors[0]
        complexes = DBSession.query(Complexbindingannotation).filter_by(interactor_id = interactor.interactor_id).all()
        data = []
        found = {}
        for x in complexes:
            complex = x.complex
            if complex.format_name in found:
                continue
            found[complex.format_name] = 1
            data.append({ "format_name": complex.format_name,
                          "display_name": complex.display_name })
        data = sorted(data, key=lambda c: c['display_name'])
        return data
    

    def posttranslational_details(self):
        annotations = DBSession.query(Posttranslationannotation).filter_by(dbentity_id=self.dbentity_id).order_by(Posttranslationannotation.site_index).all()

        reference_ids = [a.reference_id for a in annotations]
        references = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(reference_ids)).all()

        ids_to_references = {}
        for r in references:
            ids_to_references[r.dbentity_id] = r

        return [a.to_dict(locus=self, references=ids_to_references) for a in annotations]

    def sequence_details(self):
        taxonomy_id = self.get_main_strain('taxonomy_id')
        dnas = DBSession.query(Dnasequenceannotation).filter_by(dbentity_id=self.dbentity_id).all()

        obj = {
            "genomic_dna": [],
            "coding_dna": [],
            "protein": [],
            "1kb": []
        }

        main_strain_genomic = None
        main_strain_coding = None
        main_strain_1KB = None
        main_strain_protein = None
        
        for dna in dnas:
            dna_dict = dna.to_dict()

            if dna_dict:
                if dna.dna_type == "GENOMIC":
                    if dna.taxonomy_id == taxonomy_id:
                        main_strain_genomic = dna_dict
                    else:
                        obj["genomic_dna"].append(dna_dict)
                elif dna.dna_type == "CODING":
                    if dna.taxonomy_id == taxonomy_id:
                        main_strain_coding = dna_dict
                    else:
                        obj["coding_dna"].append(dna_dict)
                elif dna.dna_type == "1KB":
                    if dna.taxonomy_id == taxonomy_id:
                        main_strain_1KB = dna_dict
                    else:
                        obj["1kb"].append(dna_dict)

        if main_strain_genomic is not None:
            obj["genomic_dna"].insert(0, main_strain_genomic)
        if main_strain_coding is not None:
            obj["coding_dna"].insert(0, main_strain_coding)
        if main_strain_1KB is not None:
            obj["1kb"].insert(0, main_strain_1KB)

        protein_dnas = DBSession.query(Proteinsequenceannotation).filter_by(dbentity_id=self.dbentity_id).all()
        for protein_dna in protein_dnas:
            protein_dna_dict = protein_dna.to_dict(locus=self)
            if protein_dna_dict:
                if protein_dna.taxonomy_id == taxonomy_id:
                    main_strain_protein = protein_dna_dict
                else:
                    obj["protein"].append(protein_dna_dict)

        if main_strain_protein is not None:
            obj["protein"].insert(0, main_strain_protein)
            
        return obj

    def neighbor_sequence_details(self):

        #dnas = DBSession.query(Dnasequenceannotation).filter_by(dbentity_id=self.dbentity_id).all()
        taxonomy_id = self.get_main_strain('taxonomy_id')
        dnas = DBSession.query(Dnasequenceannotation).filter_by(dbentity_id=self.dbentity_id, dna_type='GENOMIC', taxonomy_id=taxonomy_id).all()

        #####################
        obj = {}

        locus_ids = set([dna.dbentity_id for dna in dnas])
        neighbors_annotation_ids = []

        inactive_loci = []
        for x in DBSession.query(Dbentity).filter(and_(Dbentity.dbentity_status != 'Active', Dbentity.subclass == 'LOCUS')).all():
            inactive_loci.append(x.dbentity_id)

        neighbors_list = {}

        for dna in dnas:
            strain = Straindbentity.get_strains_by_taxon_id(dna.taxonomy_id)
            so_id = get_transcript_so_id()
            
            if len(strain) < 1:
                continue

            start = dna.start_index
            end = dna.end_index

            midpoint = int(round((start + (end - start)/2)/1000))*1000
            start = max(1, midpoint - 5000)
            end = min(len(dna.contig.residues), start + 10000)

            neighbors = DBSession.query(Dnasequenceannotation).filter(and_(Dnasequenceannotation.dna_type == 'GENOMIC', Dnasequenceannotation.so_id != so_id, Dnasequenceannotation.contig_id == dna.contig_id, Dnasequenceannotation.end_index >= start, Dnasequenceannotation.start_index <= end, ~Dnasequenceannotation.dbentity_id.in_(inactive_loci))).all()

            for neighbor in neighbors:
                locus_ids.add(neighbor.dbentity_id)
                neighbors_annotation_ids.append(neighbor.annotation_id)

            neighbors_list[(dna.annotation_id, dna.taxonomy_id)] = neighbors

        # Caching the queries to fetch Locus and Dnasubsequences
        loci_list = DBSession.query(Locusdbentity).filter(Locusdbentity.dbentity_id.in_(locus_ids)).all()

        loci = {}
        for locus in loci_list:
            loci[locus.dbentity_id] = locus

        dnasubsequences = {}
        tags_list = DBSession.query(Dnasubsequence).filter(Dnasubsequence.annotation_id.in_(neighbors_annotation_ids)).all()
        for tag in tags_list:
            if tag.annotation_id in dnasubsequences:
                dnasubsequences[tag.annotation_id].append(tag)
            else:
                dnasubsequences[tag.annotation_id] = [tag]

        for annotation_id in neighbors_annotation_ids:
            if annotation_id not in dnasubsequences:
                dnasubsequences[annotation_id] = []

        for annotation in neighbors_list:
            strain = Straindbentity.get_strains_by_taxon_id(annotation[1])

            if len(strain) < 1:
                continue

            neighbors = neighbors_list[annotation]

            obj[strain[0].display_name] = {
                "start": start,
                "end": end,
                "neighbors": [n.to_dict(loci=loci, dnasubsequences=dnasubsequences) for n in neighbors]
            }

        return obj

    def expression_to_dict(self):
        expression_annotations = DBSession.query(Expressionannotation).filter_by(dbentity_id=self.dbentity_id).all()

        dataset_expression_values = {}

        reference_ids = {}
        dataset_ids = set()

        histogram_expression_value = {}
        min_expression_value = 0
        max_expression_value = 0

        for annotation in expression_annotations:
            dataset = annotation.datasetsample.dataset

            dataset_ids.add(dataset.dataset_id)
            reference_ids[dataset.dataset_id] = annotation.reference_id

            value = annotation.log_ratio_value

            rounded = floor(float(value))
            if value - rounded >= .5:
                rounded += .5

            if rounded < min_expression_value:
                min_expression_value = rounded
            if rounded > max_expression_value:
                max_expression_value = rounded

            rounded = max(-5.5, min(5, rounded))
            if rounded in histogram_expression_value:
                histogram_expression_value[rounded] += 1
            else:
                histogram_expression_value[rounded] = 1

            if annotation.datasetsample.dataset_id in dataset_expression_values:
                dataset_expression_values[dataset.dataset_id].add(rounded)
            else:
                dataset_expression_values[dataset.dataset_id] = set([rounded])

        datasets = DBSession.query(Dataset).filter(Dataset.dataset_id.in_(list(dataset_ids))).all()

        obj = {
            "min_value": min_expression_value,
            "max_value": max_expression_value,
            "overview": histogram_expression_value,
            "datasets": []
        }

        for dataset in datasets:
            dataset_dict = dataset.to_dict(DBSession.query(Referencedbentity).filter_by(dbentity_id=reference_ids[dataset.dataset_id]).one_or_none())
            dataset_dict["hist_values"] = sorted(dataset_expression_values[dataset.dataset_id])
            obj["datasets"].append(dataset_dict)

        return obj

    def interactions_to_dict(self):
        physical_interactions = DBSession.query(Physinteractionannotation).filter(or_(Physinteractionannotation.dbentity1_id == self.dbentity_id, Physinteractionannotation.dbentity2_id == self.dbentity_id)).all()

        genetic_interactions = DBSession.query(Geninteractionannotation).filter(or_(Geninteractionannotation.dbentity1_id == self.dbentity_id, Geninteractionannotation.dbentity2_id == self.dbentity_id)).all()

        obj = []
        for interaction in physical_interactions + genetic_interactions:
            obj.append(interaction.to_dict())

        return obj

    def go_to_dict(self):
        go_annotations = DBSession.query(Goannotation).filter_by(dbentity_id=self.dbentity_id).all()

        obj = []

        for go_annotation in go_annotations:
            for annotation in go_annotation.to_dict():
                if annotation not in obj:
                    obj.append(annotation)

        return obj

    def disease_to_dict(self):
        
        do_annotations = DBSession.query(Diseaseannotation).filter_by(dbentity_id=self.dbentity_id).all()

        obj = []
        for do_annotation in do_annotations:
            for annotation in do_annotation.to_dict():
                if annotation not in obj:
                    obj.append(annotation)
        # get human gene symbols from Alliance API
        #human_gene_ids_to_symbols = {}
        human_gene_ids_to_symbols = {'display name' : 'TEST1'}
        for x in obj:
            try:
                for y in x['properties']:
                    if 'bioentity' in list(y.keys()):
                        entry = y['bioentity']
                        hgnc_id = entry['display_name']
                        if hgnc_id in list(human_gene_ids_to_symbols.keys()):
                            entry['display_name'] = human_gene_ids_to_symbols[hgnc_id]
                        else:
                            url = ALLIANCE_API_BASE_URL + hgnc_id
                            if "symbol" in requests.request('GET', url).json():
                                symbol = requests.request('GET', url).json()['symbol']                            
                                entry['display_name'] = symbol
                                human_gene_ids_to_symbols[hgnc_id] = symbol
            except Exception as e:
                traceback.print_exc()
        return obj

    def literature_graph(self):
        main_gene_lit_annotations = DBSession.query(Literatureannotation).filter((Literatureannotation.dbentity_id==self.dbentity_id) & (Literatureannotation.topic == "Primary Literature")).all()
        main_gene_reference_ids = [a.reference_id for a in main_gene_lit_annotations]

        genes_sharing_references = DBSession.query(Literatureannotation).filter((Literatureannotation.reference_id.in_(main_gene_reference_ids)) & (Literatureannotation.dbentity_id != self.dbentity_id)).all()
        genes_to_references = {}
        for annotation in genes_sharing_references:
            gene = annotation.dbentity_id
            reference = annotation.reference_id
            if gene in genes_to_references:
                genes_to_references[gene].add(reference)
            else:
                genes_to_references[gene] = set([reference])

        list_genes_to_references = sorted([(g, genes_to_references[g]) for g in genes_to_references], key=lambda x: len(x[1]), reverse=True)

        edges = []
        nodes = {}

        nodes[self.format_name] = {
            "data": {
                "name": self.display_name,
                "id": self.format_name,
                "link": self.obj_url,
                "type": "BIOENTITY",
                "sub_type": "FOCUS",
            }
        }

        edges_added = set([])

        min_cutoff = 99999999
        max_cutoff = 0

        i = 0
        while i < len(list_genes_to_references) and len(nodes) <= 20 and len(edges) <= 50:
            dbentity = DBSession.query(Dbentity.display_name, Dbentity.format_name, Dbentity.obj_url).filter_by(dbentity_id=list_genes_to_references[i][0]).one_or_none()
            reference_ids = list_genes_to_references[i][1]

            if len(reference_ids) > max_cutoff:
                max_cutoff = len(reference_ids)

            if len(reference_ids) < min_cutoff:
                min_cutoff = len(reference_ids)

            if dbentity[1] not in nodes:
                nodes[dbentity[1]] = {
                    "data": {
                        "name": dbentity[0],
                        "id": dbentity[1],
                        "link": dbentity[2],
                        "type": "BIOENTITY",
                        "gene_count": len(reference_ids)
                    }
                }

            for reference_id in list(reference_ids)[:2]:
                reference = DBSession.query(Referencedbentity).filter_by(dbentity_id=reference_id).one_or_none()

                if reference.format_name not in nodes:
                    nodes[reference.format_name] = {
                        "data": {
                            "name": reference.display_name,
                            "id": reference.format_name,
                            "link": reference.obj_url,
                            "type": "REFERENCE",
                            "gene_count": len(reference_ids)
                        }
                    }

                if (reference.format_name + " " + dbentity[1]) not in edges_added:
                    edges.append({
                        "data": {
                            "source": reference.format_name,
                            "target": dbentity[1]
                        }
                    })
                    edges_added.add(reference.format_name + " " + dbentity[1])

                if (reference.format_name + " " + self.format_name) not in edges_added:
                    edges.append({
                        "data": {
                            "source": reference.format_name,
                            "target": self.format_name
                        }
                    })
                    edges_added.add(reference.format_name + " " + self.format_name)

            i += 1

        nodes[self.format_name]["data"]["gene_count"] = max_cutoff

        if len(list_genes_to_references) == 0:
            min_cutoff = max_cutoff

        return {
            "min_cutoff": min_cutoff,
            "max_cutoff": max_cutoff,
            "nodes": [nodes[n] for n in nodes],
            "edges": edges
        }

    def literature_to_dict(self):
        obj = {
            "interaction": [],
            "additional": [],
            "review": [],
            "primary": [],
            "regulation": [],
            "phenotype": [],
            "disease": [],
            "go": [],
            "ptm": [],
            "funComplement": [],
            "htp": []
        }

        primary_ids = set([])
        additional_ids = set([])
        reviews_ids = set([])
        all_ids = set([])
        literature_annotations = DBSession.query(Literatureannotation).filter_by(dbentity_id = self.dbentity_id).all()

        for annotation in literature_annotations:
            if annotation.topic == "Primary Literature":
                primary_ids.add(annotation.reference_id)
                all_ids.add(annotation.reference_id)
            elif annotation.topic == "Additional Literature":
                additional_ids.add(annotation.reference_id)
                all_ids.add(annotation.reference_id)
            elif annotation.topic == "Reviews":
                reviews_ids.add(annotation.reference_id)
                all_ids.add(annotation.reference_id)

        all_references = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(list(all_ids))).all()
                
        primary = []
        additional = []
        reviews = []
        for reference in all_references:
            if reference.dbentity_id in primary_ids:
                primary.append(reference)
            if reference.dbentity_id in additional_ids:
                additional.append(reference)
            if reference.dbentity_id in reviews_ids:
                reviews.append(reference)

        primary_lit = sorted(sorted(primary, key=lambda p: p.display_name), key=lambda p: p.year, reverse=True)
        additional_lit = sorted(sorted(additional, key=lambda p: p.display_name), key=lambda p: p.year, reverse=True)
        reviews_lit = sorted(sorted(reviews, key=lambda p: p.display_name), key=lambda p: p.year, reverse=True)

        for lit in primary_lit:
            obj["primary"].append(lit.to_dict_citation())

        for lit in additional_lit:
            obj["additional"].append(lit.to_dict_citation())

        for lit in reviews_lit:
            obj["review"].append(lit.to_dict_citation())

        interactions = DBSession.query(Geninteractionannotation).filter(or_(Geninteractionannotation.dbentity1_id == self.dbentity_id, Geninteractionannotation.dbentity2_id == self.dbentity_id)).all() + DBSession.query(Physinteractionannotation.reference_id).filter(or_(Physinteractionannotation.dbentity1_id == self.dbentity_id, Physinteractionannotation.dbentity2_id == self.dbentity_id)).all()

        interaction_ids = []
        for x in interactions:
            interaction_ids.append(x.reference_id)

        interaction_lit = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(interaction_ids)).order_by(Referencedbentity.year.desc(), Referencedbentity.display_name.asc()).all()

        for lit in interaction_lit:
            obj["interaction"].append(lit.to_dict_citation())

        ####
        regulations = DBSession.query(Regulationannotation).\
            filter(Regulationannotation.annotation_type == "manually curated", or_(Regulationannotation.target_id == self.dbentity_id, Regulationannotation.regulator_id == self.dbentity_id)).\
            all()

        regulation_ids = []
        for x in regulations:
            regulation_ids.append(x.reference_id)

        regulation_lit = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(regulation_ids)).order_by(Referencedbentity.year.desc(), Referencedbentity.display_name.asc()).all()
        
        for lit in regulation_lit:
            obj["regulation"].append(lit.to_dict_citation())
        ###
        regulations_htp = DBSession.query(Regulationannotation).filter(or_(Regulationannotation.target_id == self.dbentity_id, Regulationannotation.regulator_id == self.dbentity_id),Regulationannotation.annotation_type == "high-throughput").all()

        regulation_ids_htp = []
        for x in regulations_htp:
            if x.reference_id not in regulation_ids_htp:
                regulation_ids_htp.append(x.reference_id)

        # regulation_lit_htp = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(regulation_ids_htp)).order_by(Referencedbentity.year.desc(), Referencedbentity.display_name.asc()).all()

        disease_ref_ids = []
        for x in DBSession.query(Diseaseannotation).filter_by(dbentity_id = self.dbentity_id).all():
            disease_ref_ids.append(x.reference_id)
            
        disease_lit = DBSession.query(Referencedbentity).filter(
            Referencedbentity.dbentity_id.in_(disease_ref_ids)).order_by(
                Referencedbentity.year.desc(),
                Referencedbentity.display_name.asc()).all()
        for lit in disease_lit:
            obj["disease"].append(lit.to_dict_citation())

        # posttranslationannotation
        ptm_ref_ids = []
        for x in DBSession.query(Posttranslationannotation).filter_by(dbentity_id = self.dbentity_id).all():
            ptm_ref_ids.append(x.reference_id)
            
        ptm_lit = DBSession.query(Referencedbentity).filter(
            Referencedbentity.dbentity_id.in_(ptm_ref_ids)).order_by(
                Referencedbentity.year.desc(),
                Referencedbentity.display_name.asc()).all()

        for lit in ptm_lit:
            obj["ptm"].append(lit.to_dict_citation())
            
        # functionalcomplementannotation
        fc_ref_ids = []
        for x in DBSession.query(Functionalcomplementannotation).filter_by(dbentity_id = self.dbentity_id).all():
            fc_ref_ids.append(x.reference_id)

        fc_lit = DBSession.query(Referencedbentity).filter(
            Referencedbentity.dbentity_id.in_(fc_ref_ids)).order_by(
                Referencedbentity.year.desc(),
                Referencedbentity.display_name.asc()).all()
        for lit in fc_lit:
             obj["funComplement"].append(lit.to_dict_citation())

        ##############################################
        apo_ids = []
        apo_ids_large_scale = []
        for x in DBSession.query(Apo).all():
            if x.namespace_group == "classical genetics":
                apo_ids.append(x.apo_id)
            elif x.namespace_group == "large-scale survey":
                apo_ids_large_scale.append(x.apo_id)

        ######
        # phenotype_ids = DBSession.query(Phenotypeannotation.reference_id, Phenotypeannotation.experiment_id).filter(Phenotypeannotation.dbentity_id == self.dbentity_id).all()

        # primary_ids = set(primary_ids)

        # valid_phenotype_ref_ids = []
        #for phenotype_id_experiment in phenotype_ids:
        #    if (phenotype_id_experiment[0],) in primary_ids or phenotype_id_experiment[1] in apo_ids:
        #        valid_phenotype_ref_ids.append(phenotype_id_experiment[0])

        #valid_phenotype_ref_ids_lsc = []
        #for phenotype_id_experiment in phenotype_ids:
        #    if (phenotype_id_experiment[0],) in primary_ids or phenotype_id_experiment[1] in  apo_ids_large_scale:
        #        valid_phenotype_ref_ids_lsc.append(phenotype_id_experiment[0])
        #####
        
        valid_phenotype_ref_ids = []
        for x in DBSession.query(Phenotypeannotation).filter_by(dbentity_id = self.dbentity_id).filter(Phenotypeannotation.experiment_id.in_(apo_ids)).all():
            if x.reference_id not in valid_phenotype_ref_ids:
                valid_phenotype_ref_ids.append(x.reference_id)

        valid_phenotype_ref_ids_lsc = []
        for x in DBSession.query(Phenotypeannotation).filter_by(dbentity_id = self.dbentity_id).filter(Phenotypeannotation.experiment_id.in_(apo_ids_large_scale)).all():
            if x.reference_id not in valid_phenotype_ref_ids_lsc:
                valid_phenotype_ref_ids_lsc.append(x.reference_id)
        
        phenotype_lit = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(valid_phenotype_ref_ids)).order_by(Referencedbentity.year.desc(), Referencedbentity.display_name.asc()).all()

        for lit in phenotype_lit:
            obj["phenotype"].append(lit.to_dict_citation())

        # phenotype_lit_lsc = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(valid_phenotype_ref_ids_lsc)).order_by(Referencedbentity.year.desc(), Referencedbentity.display_name.asc()).all()
        # for lit in phenotype_lit_lsc:
        #    if lit.to_dict_citation() not in obj["htp"]:
        #        obj["htp"].append(lit.to_dict_citation())

        go_ids = []
        for x in DBSession.query(Goannotation).filter(and_(Goannotation.dbentity_id == self.dbentity_id, Goannotation.annotation_type != "high-throughput")).all():
            go_ids.append(x.reference_id)
            
        go_ids = set(go_ids) - set(Referencedbentity.get_go_blacklist_ids())
        go_lit = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(go_ids)).order_by(Referencedbentity.year.desc(), Referencedbentity.display_name.asc()).all()

        for lit in go_lit:
            obj["go"].append(lit.to_dict_citation())
            
        go_ids_htp = []
        for x in DBSession.query(Goannotation).filter(and_(Goannotation.dbentity_id == self.dbentity_id, Goannotation.annotation_type == "high-throughput")).all():
            if x.reference_id not in go_ids_htp:
                go_ids_htp.append(x.reference_id)
            
        go_ids_htp = set(go_ids_htp) - set(Referencedbentity.get_go_blacklist_ids())

        # go_lit_htp = DBSession.query(Referencedbentity).filter(
        #    Referencedbentity.dbentity_id.in_(go_ids_htp)).order_by(
        #        Referencedbentity.year.desc(),
        #        Referencedbentity.display_name.asc()).all()

        htp_ids = regulation_ids_htp + valid_phenotype_ref_ids_lsc + list(go_ids_htp)
        all_lit_htp = DBSession.query(Referencedbentity).filter(
            Referencedbentity.dbentity_id.in_(htp_ids)).order_by(
                Referencedbentity.year.desc(),
                Referencedbentity.display_name.asc()).all()
        
        for lit in all_lit_htp:
            if lit.to_dict_citation() not in obj["htp"]:
                obj["htp"].append(lit.to_dict_citation())
                
        return obj

    def go_graph(self):
        main_gene_go_annotations = DBSession.query(Goannotation).filter_by(dbentity_id=self.dbentity_id).all()
        main_gene_go_ids = [a.go_id for a in main_gene_go_annotations]

        genes_sharing_go = DBSession.query(Goannotation).filter((Goannotation.go_id.in_(main_gene_go_ids)) & (Goannotation.dbentity_id != self.dbentity_id)).all()
        genes_to_go = {}
        for annotation in genes_sharing_go:
            gene = annotation.dbentity_id
            go = annotation.go_id
            if gene in genes_to_go:
                genes_to_go[gene].add(go)
            else:
                genes_to_go[gene] = set([go])

        list_genes_to_go = sorted([(g, genes_to_go[g]) for g in genes_to_go], key=lambda x: len(x[1]), reverse=True)

        edges = []
        nodes = {}

        edges_added = set([])

        nodes[self.format_name] = {
            "data": {
                "name": self.display_name.replace("_", " "),
                "id": self.format_name,
                "dbentity_id": self.dbentity_id,
                "link": self.obj_url,
                "type": "BIOENTITY",
                "category": "FOCUS"
            }
        }

        min_cutoff = 99999999
        max_cutoff = 0

        i = 0
        while i < len(list_genes_to_go) and len(nodes) <= 20 and len(edges) <= 50:
            dbentity = DBSession.query(Dbentity.display_name, Dbentity.format_name, Dbentity.dbentity_id, Dbentity.obj_url).filter_by(dbentity_id=list_genes_to_go[i][0]).one_or_none()

            go_ids = list_genes_to_go[i][1]

            if len(go_ids) > max_cutoff:
                max_cutoff = len(go_ids)

            if len(go_ids) < min_cutoff:
                min_cutoff = len(go_ids)

            if dbentity[1] not in nodes:
                nodes[dbentity[1]] = {
                    "data": {
                        "name": dbentity[0],
                        "id": dbentity[1],
                        "dbentity_id": dbentity[2],
                        "link": dbentity[3],
                        "type": "BIOENTITY",
                        "gene_count": len(go_ids)
                    }
                }

            for go_id in go_ids:
                go = DBSession.query(Go).filter_by(go_id=go_id).one_or_none()

                if go.format_name not in nodes:
                    nodes[go.format_name] = {
                        "data": {
                            "name": go.display_name.replace("_", " "),
                            "id": go.format_name,
                            "link": go.obj_url,
                            "type": "GO",
                            "gene_count": len(go_ids)
                        }
                    }

                if (go.format_name + " " + dbentity[1]) not in edges_added:
                    edges.append({
                        "data": {
                            "source": go.format_name,
                            "target": dbentity[1]
                        }
                    })
                    edges_added.add(go.format_name + " " + dbentity[1])

                if (go.format_name + " " + self.format_name) not in edges_added:
                    edges.append({
                        "data": {
                            "source": go.format_name,
                            "target": self.format_name
                        }
                    })
                    edges_added.add(go.format_name + " " + self.format_name)

            i += 1

        nodes[self.format_name]["data"]["gene_count"] = max_cutoff

        if len(list_genes_to_go) == 0:
            min_cutoff = max_cutoff

        return {
            "min_cutoff": min_cutoff,
            "max_cutoff": max_cutoff,
            "nodes": [nodes[n] for n in nodes],
            "edges": edges
        }

    def disease_graph(self):
        main_gene_disease_annotations = DBSession.query(Diseaseannotation, Diseasesupportingevidence.dbxref_id, Diseasesupportingevidence.obj_url).join(Diseasesupportingevidence).filter(Diseaseannotation.dbentity_id==self.dbentity_id).all()
        main_gene_do_ids = [a[0].disease_id for a in main_gene_disease_annotations]

        genes_sharing_do_annotations = DBSession.query(Diseaseannotation, Diseasesupportingevidence.dbxref_id, Diseasesupportingevidence.obj_url).join(Diseasesupportingevidence).filter(
            (Diseaseannotation.disease_id.in_(main_gene_do_ids)) & (Diseaseannotation.dbentity_id != self.dbentity_id)).all()
        genes_to_do = {}
        # get all gene and disease names
        all_gene_ids = set([])
        all_human_gene_ids = set([])
        all_disease_ids = set([])
        for x in main_gene_disease_annotations:
            all_gene_ids.add(x[0].dbentity_id)
            all_disease_ids.add(x[0].disease_id)
            all_human_gene_ids.add(x[1])
        for x in genes_sharing_do_annotations:
            all_gene_ids.add(x[0].dbentity_id)
            all_disease_ids.add(x[0].disease_id)
            all_human_gene_ids.add(x[1])
        # get names up front
        gene_names = DBSession.query(Locusdbentity.dbentity_id, Locusdbentity.display_name, Locusdbentity.format_name, Locusdbentity.obj_url).filter(Locusdbentity.dbentity_id.in_(all_gene_ids)).all()
        gene_ids_to_names = {}
        human_gene_ids_to_names = {}
        gene_ids_to_format_names = {}
        gene_ids_to_urls = {}
        for x in gene_names:
            gene_ids_to_names[x[0]] = x[1]
            gene_ids_to_format_names[x[0]] = x[2]
            gene_ids_to_urls[x[0]] = x[3]
        disease_names = DBSession.query(Disease.disease_id, Disease.display_name, Disease.obj_url).filter(Disease.disease_id.in_(all_disease_ids)).all()
        disease_ids_to_names = {}
        disease_ids_to_urls = {}
        for x in disease_names:
            disease_ids_to_names[x[0]] = x[1]
            disease_ids_to_urls[x[0]] = x[2]
        # get human gene symbols from Alliance API
        for x in all_human_gene_ids:
            try:
                url = ALLIANCE_API_BASE_URL + x
                symbol = requests.request('GET', url).json()['symbol']
                human_gene_ids_to_names[x] = symbol
            except Exception as e:
                human_gene_ids_to_names[x] = x
        all_node_ids = [self.dbentity_id]
        all_edge_slugs = []
        nodes = [{
            "name": self.display_name.replace("_", " "),
            "id": self.format_name,
            "href": self.obj_url,
            "category": self.display_name.replace("_", " ")
        }]
        edges = []
        for x in main_gene_disease_annotations:
            disease_annotation = x[0]
            human_gene_id = x[1]
            human_gene_url = x[2]
            if human_gene_id not in all_node_ids:
                nodes.append({
                    "name": human_gene_ids_to_names[human_gene_id],
                    "id": human_gene_id,
                    "href": human_gene_url,
                    "category": 'Human Gene'
                })
                all_node_ids.append(human_gene_id)
            edge_slug = self.format_name + '.' + human_gene_id
            if edge_slug not in all_edge_slugs:
                edges.append({
                    "source": self.format_name,
                    "target": human_gene_id,
                })
                all_edge_slugs.append(edge_slug)
            d_id = disease_annotation.disease_id
            if d_id not in all_node_ids:
                nodes.append({
                    "name": disease_ids_to_names[d_id],
                    "id": d_id,
                    "href": disease_ids_to_urls[d_id],
                    "category": "Disease"
                })
                all_node_ids.append(d_id)
            edge_slug = human_gene_id + "." + str(d_id)
            if edge_slug not in all_edge_slugs:
                edges.append({
                    "source": human_gene_id,
                    "target": d_id
                })
                all_edge_slugs.append(edge_slug)
            # add edge to connect directly focus -> disease
            direct_edge_slug = self.format_name + '.' + str(d_id)
            if direct_edge_slug not in all_edge_slugs:
                edges.append({
                    "source": self.format_name,
                    "target": d_id,
                })
                all_edge_slugs.append(direct_edge_slug)

        # add focus_gene -> human_gene -> disease nodes and edges
        for x in genes_sharing_do_annotations:
            disease_annotation = x[0]
            human_gene_id = x[1]
            human_gene_url = x[2]
            yeast_gene_id = disease_annotation.dbentity_id
            if yeast_gene_id not in all_node_ids:
                format_name = gene_ids_to_format_names[yeast_gene_id]
                nodes.append({
                    "name": gene_ids_to_names[yeast_gene_id],
                    "id": format_name,
                    "href": gene_ids_to_urls[yeast_gene_id],
                    "category": 'Yeast Gene'
                })
                all_node_ids.append(yeast_gene_id)
            edge_slug = format_name + '.' + human_gene_id
            if edge_slug not in all_edge_slugs:
                edges.append({
                    "source": format_name,
                    "target": human_gene_id,
                })
                all_edge_slugs.append(edge_slug)
            
            if human_gene_id not in all_node_ids:
                nodes.append({
                    "name": human_gene_ids_to_names[human_gene_id],
                    "id": human_gene_id,
                    "href": human_gene_url,
                    "category": "Human Gene"
                })
                all_node_ids.append(human_gene_id)
            d_id = disease_annotation.disease_id
            if d_id not in all_node_ids:
                nodes.append({
                    "name": disease_ids_to_names[d_id],
                    "id": d_id,
                    "href": disease_ids_to_urls[d_id],
                    "category": "Disease"
                })
                all_node_ids.append(d_id)
            edge_slug = human_gene_id + "." + str(d_id)
            if edge_slug not in all_edge_slugs:
                edges.append({
                    "source": human_gene_id,
                    "target": d_id
                })
                all_edge_slugs.append(edge_slug)
            edge_slug = format_name + "." + str(d_id)
            if edge_slug not in all_edge_slugs:
                edges.append({
                    "source": format_name,
                    "target": d_id
                })
                all_edge_slugs.append(edge_slug)
        return {
            "nodes": nodes,
            "edges": edges
        }

    def interaction_graph_secondary_edges(self, Interaction, edge_type, nodes, edges):
        secondary_nodes = set(nodes.keys()) - set([self.dbentity_id])

        interactions = DBSession.query(Interaction).filter(and_(Interaction.dbentity1_id.in_(secondary_nodes), Interaction.dbentity2_id.in_(secondary_nodes))).all()

        edges_to_annotations = {}
        for annotation in interactions:
            if annotation.dbentity1_id < annotation.dbentity2_id:
                add = str(annotation.dbentity1_id) + "_" + str(annotation.dbentity2_id)
            else:
                add = str(annotation.dbentity2_id) + "_" + str(annotation.dbentity1_id)

            if add in edges_to_annotations:
                edges_to_annotations[add].add(annotation)
            else:
                edges_to_annotations[add] = set([annotation])

        edges_added = set([])

        i = 0
        while i < len(interactions) and len(edges_added) <= 50:
            dbentity1_id = interactions[i].dbentity1_id
            dbentity2_id = interactions[i].dbentity2_id

            source = nodes[dbentity1_id]["data"]["id"]
            target = nodes[dbentity2_id]["data"]["id"]

            if dbentity1_id < dbentity2_id:
                key = str(dbentity1_id) + "_" + str(dbentity2_id)
            else:
                key = str(dbentity2_id) + "_" + str(dbentity1_id)

            if (source + " " + target) not in edges_added and (target + " " + source) not in edges_added:
                edges.append({
                    "data": {
                        "source": source,
                        "target": target,
                        "class_type": edge_type,
                        "evidence": len(edges_to_annotations[key])
                    }
                })
                edges_added.add(source + " " + target)
            i += 1

    def interaction_graph(self):
        phys_graph = self.interaction_graph_builder(Physinteractionannotation, "PHYSICAL")
        gen_graph = self.interaction_graph_builder(Geninteractionannotation, "GENETIC")

        nodes = {}

        for node in phys_graph["nodes"]:
            nodes[node] = phys_graph["nodes"][node]
            nodes[node]["data"]["physical"] = phys_graph["nodes"][node]["data"]["evidence"]

        for node in gen_graph["nodes"]:
            if node not in nodes:
                nodes[node] = gen_graph["nodes"][node]
                nodes[node]["data"]["genetic"] = gen_graph["nodes"][node]["data"]["evidence"]
            else:
                nodes[node]["data"]["genetic"] = gen_graph["nodes"][node]["data"]["evidence"]
                nodes[node]["data"]["evidence"] = max(nodes[node]["data"]["genetic"], nodes[node]["data"]["physical"])

        edges = phys_graph["edges"] + gen_graph["edges"]

        self.interaction_graph_secondary_edges(Physinteractionannotation, "PHYSICAL", nodes, edges)
        self.interaction_graph_secondary_edges(Geninteractionannotation, "GENETIC", nodes, edges)

        # limiting cutoffs by 10. The interface converts > 10 to '+10' to save space

        return {
            "nodes": [nodes[n] for n in nodes],
            "edges": edges,
            "max_phys_cutoff": min(phys_graph["max_evidence_cutoff"], 10),
            "max_gen_cutoff": min(gen_graph["max_evidence_cutoff"], 10),
            "min_evidence_cutoff": min(min(phys_graph["min_evidence_cutoff"], gen_graph["min_evidence_cutoff"]), 10),
            "max_evidence_cutoff": min(max(phys_graph["max_evidence_cutoff"], gen_graph["max_evidence_cutoff"]), 10),
        }

    def interaction_graph_builder(self, Interaction, edge_type):
        main_gene_annotations = DBSession.query(Interaction).filter(or_(Interaction.dbentity1_id == self.dbentity_id, Interaction.dbentity2_id == self.dbentity_id)).all()

        genes_to_interactions = {}
        for annotation in main_gene_annotations:
            if annotation.dbentity1_id == self.dbentity_id:
                add = annotation.dbentity2_id
            else:
                add = annotation.dbentity1_id

            if add in genes_to_interactions:
                genes_to_interactions[add].add(annotation.annotation_id)
            else:
                genes_to_interactions[add] = set([annotation.annotation_id])

        list_genes_to_interactions = sorted([(g, genes_to_interactions[g]) for g in genes_to_interactions], key=lambda x: len(x[1]), reverse=True)

        nodes = {}
        edges = []

        edges_added = set([])

        nodes[self.dbentity_id] = {
            "data": {
                "name": self.display_name,
                "id": self.format_name,
                "link": self.obj_url,
                "type": "BIOENTITY",
                "sub_type": "FOCUS",
                "evidence": 0
            }
        }

        min_cutoff = 99999999
        max_cutoff = 0

        genes_cache_query = DBSession.query(Dbentity.dbentity_id, Dbentity.display_name, Dbentity.format_name, Dbentity.obj_url).filter(Dbentity.dbentity_id.in_(list(genes_to_interactions.keys()))).all()
        genes_cache = {}
        for gene in genes_cache_query:
            genes_cache[gene.dbentity_id] = gene

        i = 0
        while i < len(list_genes_to_interactions) and len(nodes) <= 20:
            dbentity_id = list_genes_to_interactions[i][0]
            dbentity = genes_cache[dbentity_id]

            if len(list_genes_to_interactions[i][1]) > max_cutoff:
                max_cutoff = len(list_genes_to_interactions[i][1])

            if len(list_genes_to_interactions[i][1]) < min_cutoff:
                min_cutoff = len(list_genes_to_interactions[i][1])

            if dbentity_id not in nodes:
                nodes[dbentity_id] = {
                    "data": {
                        "name": dbentity.display_name,
                        "id": dbentity.format_name,
                        "link": dbentity.obj_url,
                        "type": "BIOENTITY",
                        "evidence": len(list_genes_to_interactions[i][1])
                    }
                }

            if (self.format_name + " " + dbentity.format_name) not in edges_added or (dbentity.format_name + " " + self.format_name) not in edges_added:
                edges.append({
                    "data": {
                        "source": self.format_name,
                        "target": dbentity.format_name,
                        "class_type": edge_type,
                        "evidence": len(list_genes_to_interactions[i][1])
                    }
                })
                edges_added.add(self.format_name + " " + dbentity.format_name)

            i += 1

        nodes[self.dbentity_id]["data"]["gene_count"] = max_cutoff

        return {
            "nodes": nodes,
            "edges": edges,
            "min_evidence_cutoff": min_cutoff,
            "max_evidence_cutoff": max_cutoff
        }

    def regulation_graph(self):
        MAX_NODES = 150
        # get annotations to and from gene, or among regulators/targets
        direct_relations = DBSession.query(Regulationannotation.target_id, Regulationannotation.regulator_id).filter(or_(Regulationannotation.target_id == self.dbentity_id, Regulationannotation.regulator_id == self.dbentity_id)).all()
        target_ids = []
        regulator_ids = []
        for d in direct_relations:
            target_ids.append(d[0])
            regulator_ids.append(d[1])
        target_ids = list(set(target_ids))
        regulator_ids = list(set(regulator_ids))
        ids = list(set(target_ids + regulator_ids))
        main_gene_annotations = DBSession.query(Regulationannotation).filter(and_(Regulationannotation.target_id.in_(ids), Regulationannotation.regulator_id.in_(ids))).all()
        genes_to_regulations = {}
        # get unique relations and append annotations so key = {regulator_id}_{target_id}
        for d in main_gene_annotations:
            id_str = str(d.regulator_id) + '_' + str(d.target_id)
            if id_str in genes_to_regulations:
                genes_to_regulations[id_str].append(d)
            else:
                genes_to_regulations[id_str] = [d]
        def sortfn(x):
            BOOST = 1.25
            score = len(genes_to_regulations[x])
            # boost score if has focus locus
            str_ids = x.split('_')
            if str(self.dbentity_id) in str_ids:
                score = score * BOOST
            return score
        all_keys = list(genes_to_regulations.keys())
        sorted_ids_keys = sorted(all_keys, key=lambda x: sortfn(x), reverse=True)
        sorted_ids_keys = sorted_ids_keys[:MAX_NODES]
        ids_from_keys = []
        for k in sorted_ids_keys:
            str_ids = k.split('_')
            for d in str_ids:
                ids_from_keys.append(int(d))
        ids_from_keys = list(set(ids_from_keys))
        # format nodes
        nodes = []
        all_gene_info = DBSession.query(Dbentity.dbentity_id, Dbentity.display_name, Dbentity.format_name, Dbentity.obj_url).filter(Dbentity.dbentity_id.in_(ids_from_keys)).all()
        # ensure self is first
        def self_sort_fn(x):
            if x[0] == self.dbentity_id:
                return 1
            return -1
        all_gene_info = sorted(all_gene_info, key=lambda x: self_sort_fn(x), reverse=True)
        gene_ids_info = {}
        for d in all_gene_info:
            gene_ids_info[str(d[0])] = d
            d_id = d[0]
            cat = None
            if d_id == self.dbentity_id:
                cat = "FOCUS"
            elif d_id in target_ids:
                cat = "TARGET"
            elif d_id in regulator_ids:
                cat = "REGULATOR"
            nodes.append({
                "name": d[1],
                "id": d[2],
                "link": d[3],
                "type": "BIOENTITY",
                "category": cat
            })
        # format edges
        edges = []
        included_genes = list(gene_ids_info.keys())
        # get all edges for included nodes
        selected_edge_keys = []
        for d in all_keys:
            reg_id = d.split('_')[0]
            target_id = d.split('_')[1]
            if reg_id in included_genes and target_id in included_genes:
                selected_edge_keys.append(d)
        for d in selected_edge_keys:
            regulator = gene_ids_info[d.split('_')[0]]
            target = gene_ids_info[d.split('_')[1]]
            regulator_format_name = regulator[2]
            target_format_name = target[2]
            edges.append({
                "action": "expression null",
                "source": regulator_format_name,
                "target": target_format_name,
                "evidence": len(genes_to_regulations[d])
            })
        return {
            "nodes": nodes,
            "edges": edges,
            "min_evidence_count": 1
        }

    def expression_graph(self):
        annotations = DBSession.query(Expressionannotation).filter_by(dbentity_id=self.dbentity_id).all()

        datasetsample_to_exp_value = {}
        datasetsample_ids = []
        for a in annotations:
            datasetsample_ids.append(a.datasetsample_id)
            datasetsample_to_exp_value[a.datasetsample_id] = a.normalized_expression_value

        genes_in_same_datasetsamples = DBSession.query(Expressionannotation.dbentity_id, Expressionannotation.datasetsample_id, Expressionannotation.normalized_expression_value).filter(and_(Expressionannotation.datasetsample_id.in_(datasetsample_ids), Expressionannotation.dbentity_id != self.dbentity_id)).all()


        genes_data = []

        for g in genes_in_same_datasetsamples:
            genes_data.append((g.dbentity_id, g.datasetsample_id, g.normalized_expression_value * datasetsample_to_exp_value[g.datasetsample_id]))

        list_genes = sorted(genes_data, key=lambda x: x[2], reverse=True)

        edges = []
        nodes = {}

        edges_added = set([])

        nodes[self.dbentity_id] = {
            "data": {
                "name": self.display_name,
                "id": self.format_name,
                "link": self.obj_url,
                "type": "BIOENTITY",
                "sub_type": "FOCUS"
            }
        }

        min_coeff = 9999999999
        max_coeff = 0

        i = 0
        while i < len(list_genes) and len(nodes) <= 20 and len(edges) <= 50:
            gene = list_genes[i][0]

            if gene not in nodes:
                dbentity = DBSession.query(Dbentity.display_name, Dbentity.format_name, Dbentity.obj_url).filter_by(dbentity_id=gene).one_or_none()

                nodes[gene] = {
                    "data": {
                        "name": dbentity[0],
                        "id": dbentity[1],
                        "link": dbentity[2],
                        "type": "BIOENTITY",
                        "category": None
                    }
                }

                score = list_genes[i][2] / list_genes[0][2] / 10, # normalizing

                max_coeff = max(max_coeff, score)
                min_coeff = min(min_coeff, score)

                if (dbentity[1] + " " + self.format_name) not in edges_added:
                    edges.append({
                        "data": {
                            "source": dbentity[1],
                            "target": self.format_name,
                            "score": score,
                            "class_type": "EXPRESSION",
                            "direction": "positive"
                        }
                    })

            i += 1


        return {
            "min_coeff": min_coeff,
            "max_coeff": max_coeff,
            "nodes": [nodes[n] for n in nodes],
            "edges": edges
        }

    def get_main_strain(self, type=None):
        main_strain_list = ["S288C", "W303", "Sigma1278b", "SK1", "SEY6210", "X2180-1A", "CEN.PK", "D273-10B", "JK9-3d", "FL100", "Y55", "RM11-1a"]
        main_strain = None
        for strain in main_strain_list:
            x = DBSession.query(Straindbentity).filter_by(display_name=strain, subclass='STRAIN').one_or_none()
            y = DBSession.query(Dnasequenceannotation).filter_by(taxonomy_id=x.taxonomy_id, dbentity_id=self.dbentity_id, dna_type='GENOMIC').all()
            if len(y) == 0:
                continue
            if  main_strain is None:
                main_strain = strain
                TAXON_ID = x.taxonomy_id
                if main_strain == 'S288C':
                    break
            z = DBSession.query(Proteindomainannotation).filter_by(taxonomy_id=x.taxonomy_id, dbentity_id=self.dbentity_id).all()
            if len(z) > 0:
                main_strain = strain
                TAXON_ID = x.taxonomy_id
                break
        if main_strain is None:
            main_strain = 'Unknown'
            TAXON_ID = 99999
        if type == 'taxonomy_id':
            return TAXON_ID
        else:
            return [main_strain, TAXON_ID]
            
    def phenotype_graph(self):
        main_gene_phenotype_annotations = DBSession.query(Phenotypeannotation).filter_by(dbentity_id=self.dbentity_id).all()
        main_gene_phenotype_ids = [a.phenotype_id for a in main_gene_phenotype_annotations]

        genes_sharing_phenotypes = DBSession.query(Phenotypeannotation).filter((Phenotypeannotation.phenotype_id.in_(main_gene_phenotype_ids)) & (Phenotypeannotation.dbentity_id != self.dbentity_id)).all()
        genes_to_phenotypes = {}
        for annotation in genes_sharing_phenotypes:
            gene = annotation.dbentity_id
            phenotype = annotation.phenotype_id
            if gene in genes_to_phenotypes:
                genes_to_phenotypes[gene].add(phenotype)
            else:
                genes_to_phenotypes[gene] = set([phenotype])

        list_genes_to_phenotypes = sorted([(g, genes_to_phenotypes[g]) for g in genes_to_phenotypes], key=lambda x: len(x[1]), reverse=True)

        edges = []
        nodes = {}

        edges_added = set([])

        nodes[self.format_name] = {
            "data": {
                "name": self.display_name,
                "id": self.format_name,
                "dbentity_id": self.dbentity_id,
                "link": self.obj_url,
                "type": "BIOENTITY",
                "sub_type": "FOCUS"
            }
        }

        min_cutoff = 99999999
        max_cutoff = 0

        i = 0
        while i < len(list_genes_to_phenotypes) and len(nodes) <= 20 and len(edges) <= 50:
            dbentity = DBSession.query(Dbentity.display_name, Dbentity.format_name, Dbentity.dbentity_id, Dbentity.obj_url).filter_by(dbentity_id=list_genes_to_phenotypes[i][0]).one_or_none()

            observable_ids = DBSession.query(distinct(Phenotype.observable_id)).filter(Phenotype.phenotype_id.in_(list_genes_to_phenotypes[i][1])).all()

            if len(observable_ids) > max_cutoff:
                max_cutoff = len(observable_ids)

            if len(observable_ids) < min_cutoff:
                min_cutoff = len(observable_ids)

            if dbentity[1] not in nodes:
                nodes[dbentity[1]] = {
                    "data": {
                        "name": dbentity[0],
                        "id": dbentity[1],
                        "dbentity_id": dbentity[2],
                        "link": dbentity[3],
                        "type": "BIOENTITY",
                        "gene_count": len(observable_ids)
                    }
                }

            for observable_id in observable_ids:
                observable = Apo.get_apo_by_id(observable_id[0])

                if observable.format_name not in nodes:
                    nodes[observable.format_name] = {
                        "data": {
                            "name": observable.display_name,
                            "id": observable.format_name,
                            "link": observable.obj_url,
                            "type": "OBSERVABLE",
                            "gene_count": len(observable_ids)
                        }
                    }

                if (observable.format_name + " " + dbentity[1]) not in edges_added:
                    edges.append({
                        "data": {
                            "source": observable.format_name,
                            "target": dbentity[1]
                        }
                    })
                    edges_added.add(observable.format_name + " " + dbentity[1])

                if (observable.format_name + " " + self.format_name) not in edges_added:
                    edges.append({
                        "data": {
                            "source": observable.format_name,
                            "target": self.format_name
                        }
                    })
                    edges_added.add(observable.format_name + " " + self.format_name)

            i += 1

        nodes[self.format_name]["data"]["gene_count"] = max_cutoff

        if len(list_genes_to_phenotypes) == 0:
            min_cutoff = max_cutoff

        return {
            "min_cutoff": min_cutoff,
            "max_cutoff": max_cutoff,
            "nodes": [nodes[n] for n in nodes],
            "edges": edges
        }

    def phenotype_to_dict(self):
        phenotype_annotations = DBSession.query(Phenotypeannotation).filter_by(dbentity_id=self.dbentity_id).all()

        conditions = DBSession.query(PhenotypeannotationCond).filter(PhenotypeannotationCond.annotation_id.in_([p.annotation_id for p in phenotype_annotations])).all()
        temp_lst = list(set([c.condition_name for c in conditions]))
        condition_names = clear_list_empty_values(temp_lst)

        conditions_dict = {}
        for condition in conditions:
            if condition.annotation_id in conditions_dict:
                conditions_dict[condition.annotation_id].append(condition)
            else:
                conditions_dict[condition.annotation_id] = [condition]
        if len(condition_names) > 0:
            urls = DBSession.query(Chebi.display_name, Chebi.obj_url).filter(Chebi.display_name.in_(condition_names)).all()
        else:
            urls = []
        chebi_urls = {}
        for url in urls:
            chebi_urls[url[0]] = url[1]

        obj = []
        for annotation in phenotype_annotations:
            obj += annotation.to_dict(locus=self, conditions=conditions_dict.get(annotation.annotation_id, []), chebi_urls=chebi_urls)
        return obj

    def to_dict_analyze(self):
        return {
            "id": self.dbentity_id,
            "display_name": self.display_name,
            "link": self.obj_url,
            "description": self.description,
            "format_name": self.format_name
        }

    def to_dict_sequence_widget(self):
        obj = {
            "id": self.dbentity_id,
            "display_name": self.display_name,
            "format_name": self.format_name,
            "headline": self.headline,
            "link": self.obj_url
        }
        
        taxonomy_id = self.get_main_strain('taxonomy_id')

        query = "SELECT display_name FROM nex.so where so_id IN (SELECT so_id FROM nex.dnasequenceannotation WHERE dbentity_id = " + str(self.dbentity_id) + " and taxonomy_id =" + str(taxonomy_id) + " GROUP BY so_id)"

        locus_type = []
        so_display_names = DBSession.execute(query)

        for so_display_name in so_display_names:
            locus_type.append(so_display_name[0])

        obj["locus_type"] = ",".join(locus_type)

        return obj
        
    def to_dict(self):
        
        obj = {
            "id": self.dbentity_id,
            "display_name": self.display_name,
            "format_name": self.format_name,
            "gene_name": self.gene_name,
            "link": self.obj_url,
            "sgdid": self.sgdid,
            "qualities": [],
            "aliases": [],
            "references": [],
            "locus_type": None,
            "qualifier": self.qualifier,
            "bioent_status": self.dbentity_status,
            "description": self.description,
            "name_description": self.name_description,
            "paralogs": self.paralogs_to_dict(),
            "complements": self.complements_to_dict(),
            "urls": [],
            "alliance_icon_links": [],
            "protein_overview": self.protein_overview_to_dict(),
            "go_overview": self.go_overview_to_dict(),
            "pathways": [],
            "alleles": [],
            "sequence_summary": '',
            "protein_summary": '',
            "regulation_summary": '',
            "phenotype_overview": self.phenotype_overview_to_dict(),
            "interaction_overview": self.interaction_overview_to_dict(),
            "paragraph": {
                "date_edited": None
            },
            "literature_overview": self.literature_overview_to_dict(),
            "disease_overview": self.disease_overview_to_dict(),
            "ecnumbers": [],
            "URS_ID": None
        }

        ## set alliance icon links

        SO_TYPES_TO_EXCLUDE = "'SO:0000186', 'SO:0000577', 'SO:0000286', 'SO:0000296', 'SO:0005855', 'SO:0001984', 'SO:0002026', 'SO:0001789', 'SO:0000436', 'SO:0000624', 'SO:0000036', 'SO:0002059'"

        rows = DBSession.execute(f"SELECT annotation_id "
                                 f"FROM nex.dnasequenceannotation "
                                 f"WHERE dbentity_id = {self.dbentity_id} "
                                 f"AND taxonomy_id = {TAXON_ID} "
                                 f"AND dna_type = 'GENOMIC' "
                                 f"AND so_id not in "
                                 f"(select so_id from nex.so where soid in ({SO_TYPES_TO_EXCLUDE}))").fetchall()

        if len(rows) > 0:
            allianceSearchRootUrl = "https://www.alliancegenome.org/"
            allianceSearchUrl = allianceSearchRootUrl + "search?biotypes=protein_coding_gene&category=gene&q=_SUBSTITUTE_&species="
            mod_to_template_url = { "ZFIN": allianceSearchUrl + "Danio%20rerio",
                                    "RGD":  allianceSearchUrl + "Rattus%20norvegicus",
                                    "MGI":  allianceSearchUrl + "Mus%20musculus",
                                    "FB":   allianceSearchUrl + "Drosophila%20melanogaster",
                                    "WB":   allianceSearchUrl + "Caenorhabditis%20elegans",
                                    "HGNC": allianceSearchUrl + "Homo%20sapiens" }
            allianceAPI = "https://www.alliancegenome.org/api/gene/SGD:" + self.sgdid + "/homologs?limit=10000"
            try:
                req = Request(allianceAPI)
                res = urlopen(req)
                records = json.loads(res.read().decode('utf-8'))
                mod_to_ids = {}
                for record in records['results']:
                    homolog = record['homologGene']
                    mod = homolog['id'].split(':')[0]
                    ids = []
                    if mod in mod_to_ids:
                        ids = mod_to_ids[mod]
                    if len(ids) < 100:
                        ids.append(homolog['id'])
                    mod_to_ids[mod] = ids
                linkData = []
                for mod in ['HGNC', 'MGI', 'RGD', 'ZFIN', 'FB', 'WB']:
                    if mod in mod_to_ids:
                        if len(mod_to_ids[mod]) > 1:
                            ids = "+".join(mod_to_ids[mod])
                            linkData.append({"mod": mod,
                                             "icon_url": mod_to_template_url[mod].replace("_SUBSTITUTE_", ids)})
                        else:
                            linkData.append({"mod": mod,
                                             "icon_url": allianceSearchRootUrl + "gene/" + mod_to_ids[mod][0]})
                # linkData.insert(0, {"mod": 'SGD',
                #                "icon_url": allianceSearchRootUrl + "gene/SGD:" + self.sgdid})
                linkData.append({"mod": 'SGD',                                                                                  
                                "icon_url": allianceSearchRootUrl + "gene/SGD:" + self.sgdid})
                obj['alliance_icon_links'] = linkData
            except Exception as e:
                print('error fetching alliance homolog data:' + str(e))
                
        sequence_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type="Sequence").one_or_none()
        if sequence_summary:
            obj["sequence_summary"] = sequence_summary.html

        protein_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type="Protein").one_or_none()
        if protein_summary:
            obj["protein_summary"] = protein_summary.html

        regulation_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type="Regulation").one_or_none()
        if regulation_summary:
            obj["regulation_summary"] = regulation_summary.html

        [main_strain, taxonomy_id] = self.get_main_strain()
        obj['main_strain'] = main_strain

        if self.genetic_position:
            obj["genetic_position"] = self.genetic_position
            
        # summaries and paragraphs
        summaries = DBSession.query(Locussummary.summary_id, Locussummary.html, Locussummary.date_created,Locussummary.summary_order,Locussummary.summary_type).filter_by(locus_id=self.dbentity_id).all()
        summary_types = {}
        for s in summaries:
            if s[4] in summary_types:
                summary_types[s[4]].append(s)
            else:
                summary_types[s[4]] = [s]
        summary_gene = sorted(summary_types.get("Gene", []), key=lambda s: s[3])
        summary_regulation = sorted(summary_types.get("Regulation", []), key=lambda s: s[3])
        obj["regulation_overview"] = self.regulation_overview_to_dict(summary_regulation)
        if len(summary_gene) > 0:
            text = ""
            for s in summary_gene:
                text += s[1]
            modify_summary_gene = sorted(summary_gene,key=lambda s: s[2])
            obj["paragraph"] = {
                "text": text,
                "date_edited": modify_summary_gene[-1][2].strftime("%Y-%m-%d")
            }
        else:
            obj["paragraph"] = None
        references_obj = self.references_overview_to_dict([s[0] for s in summary_gene])
        obj["qualities"] = references_obj["qualities"]
        obj["references"] = references_obj["references"]
        obj["reference_mapping"] = references_obj["reference_mapping"]
        
        if obj["paragraph"] is not None:
            obj["paragraph"]["text"] = self.format_paragraph(obj["paragraph"]["text"], references_obj)
    
        # aliases/external IDs
        aliases = DBSession.query(LocusAlias).filter(and_(LocusAlias.locus_id==self.dbentity_id, ~LocusAlias.alias_type.in_(['Pathway ID', 'Retired name', 'SGDID Secondary']))).all()
        for alias in aliases:
            if alias.alias_type == "EC number":
                # generate URL to internal page, not expasy
                internal_url = "/ecnumber/EC:" + alias.display_name
                obj["ecnumbers"].append({
                    "display_name": alias.display_name,
                    "link": internal_url
                })
            
            category = ""
            if alias.alias_type == "Uniform" or alias.alias_type == "Non-uniform":
                category = "Alias"
            elif alias.alias_type == "NCBI protein name":
                category = "NCBI protein name"
            else:
                category = alias.alias_type
        
            references_alias = DBSession.query(LocusAliasReferences).filter_by(alias_id=alias.alias_id).all()

            reference_alias_dict = []
            for r in references_alias:
                reference_dict = r.reference.to_dict_citation()
                reference_alias_dict.append(reference_dict)
                if(reference_dict not in obj["references"]):
                    obj["references"].append(reference_dict)
    
                order = len(list(obj["reference_mapping"].keys()))
                if r.reference_id not in obj["reference_mapping"]:
                    obj["reference_mapping"][r.reference_id] = order + 1

                    
            alias_obj = {
                "id": alias.alias_id,
                "display_name": alias.display_name,
                "link": alias.obj_url,
                "category": category,
                "references": reference_alias_dict,
                "source": {
                    "display_name": alias.source.display_name
                }
            }
            if alias.has_external_id_section:
                alias_obj["protein"] = True

            obj["aliases"].append(alias_obj)
            
        ## alleles
        alleles = []
        for x in DBSession.query(LocusAllele).filter_by(locus_id=self.dbentity_id).all():
            allele = x.allele
            alleles.append({ "display_name": allele.display_name,
                             "link_url": allele.obj_url })
        if len(alleles) > 0:
            alleles = sorted(alleles, key=lambda r: r['display_name'])
            obj["alleles"] = alleles 
    
        # URLs (resources)
        so_ids = []
        for x in DBSession.query(Dnasequenceannotation).filter(Dnasequenceannotation.dbentity_id == self.dbentity_id,Dnasequenceannotation.taxonomy_id == taxonomy_id).all():
            if x.so_id not in so_ids:
                so_ids.append(x.so_id)
        locus_type = []
        for x in DBSession.query(So).filter(So.so_id.in_(so_ids)).all():
            locus_type.append(x.display_name)
        obj["locus_type"] = ",".join(locus_type)

        urls = DBSession.query(LocusUrl).filter_by(locus_id=self.dbentity_id).order_by(LocusUrl.display_name).all()
        obj["urls"] = [u.to_dict() for u in urls]

        # get RNACentral URS ID from EBI
        # https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/id_mapping/database_mappings/sgd.tsv
        if "RNA" in obj["locus_type"]:
            url_path = 'https://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/id_mapping/database_mappings/'
            mapping_file = 'sgd.tsv'
            urllib.request.urlretrieve(url_path + mapping_file, mapping_file)
            f = open(mapping_file)
            for line in f:
                pieces = line.split('\t')
                if pieces[2] == self.sgdid:
                    try:
                        content = urlopen("https://rnacentral.org/api/v1/rna/" + pieces[0] + "/2d/svg/")
                    except:
                        break
                    obj["URS_ID"] = pieces[0]
                    break
            f.close()
            os.remove(mapping_file)
        
        uniprotID = None
        aliases = DBSession.query(LocusAlias).filter_by(locus_id=self.dbentity_id, alias_type='UniProtKB ID').all()
        if aliases:
            uniprotID = aliases[0].display_name
        if uniprotID:
            obj["urls"].append({
                "category": "LOCUS_SEQUENCE",
                "link": "https://alphafold.ebi.ac.uk/entry/" + uniprotID,
                "display_name": "AlphaFold Protein Structure"
            })

        obj["urls"].append({
            "category": "LOCUS_SEQUENCE",
            "link": "/seqTools?seqname=" + self.systematic_name,
            "display_name": "Gene/Sequence Resources"
        })
        if not self.systematic_name.startswith('R00'):
            obj["urls"].append({
                "category": "LOCUS_SEQUENCE",
                "link": "https://browse.yeastgenome.org/?loc=" + self.systematic_name,
                "display_name": "JBrowse"
            })
        if uniprotID:
            obj["urls"].append({
                "category": "LOCUS_SEQUENCE",
                "link": "https://www.uniprot.org/uniprot/" + uniprotID,
                "display_name": "UniProtKB"
            })

        locus_notes = DBSession.query(Locusnote).filter_by(locus_id=self.dbentity_id).all()
        obj["history"] = [h.to_dict() for h in locus_notes]

        # pathways
        pathwayannotations = DBSession.query(Pathwayannotation).filter_by(dbentity_id=self.dbentity_id).distinct(Pathwayannotation.pathway_id).all()
        obj["pathways"] = [a.to_dict() for a in pathwayannotations]

        obj["complexes"] = self.complex_details()
        
        # reserved name
        reservedname = DBSession.query(Reservedname).filter_by(locus_id=self.dbentity_id).one_or_none()
        if reservedname:
            r_obj = reservedname.to_dict()
            r_obj["link"] = reservedname.obj_url
            r_obj["class_type"] = "RESERVEDNAME"
            obj["reserved_name"] = r_obj
            obj["name_description"] = reservedname.name_description
            if reservedname.reference:
                ref = reservedname.reference
                ref_obj = reservedname.reference.to_dict_citation()
                ref_obj['id'] = ref.dbentity_id
                r_obj["reference"] = ref_obj

        return obj

    def format_paragraph(self, text, references_obj):
        sgdid_pattern = re.compile(r'<reference:(S\d\d\d\d\d\d\d\d\d)>')

        formatted_text = ""

        last_cursor = 0
        for match in sgdid_pattern.finditer(text):
            reference = references_obj["sgdid_ref"].get(match.group(1))
            if reference:
                formatted_text += text[last_cursor:match.start()] + "<span data-tooltip aria-haspopup=\"true\" class=\"has-tip\" title=\"" + reference.display_name + "\"><a href=\"" + reference.obj_url + "\">" + str(references_obj["reference_mapping"][reference.dbentity_id]) + "</a></span>"
                last_cursor = match.end()

        return formatted_text + text[last_cursor:]

    def references_overview_to_dict(self, summary_ids):
        blacklist = (551590,)
        references = DBSession.query(LocusReferences).filter(and_(LocusReferences.locus_id==self.dbentity_id, ~LocusReferences.reference_id.in_(blacklist))).all()

        obj = {}

        obj["qualities"] = {
            "gene_name": {
                "references": []
            },
            "feature_type": {
                "references": []
            },
            "qualifier": {
                "references": []
            },
            "description": {
                "references": []
            },
            "name_description": {
                "references": []
            },
            "id": {
                "references": []
            }
        }

        obj["sgdid_ref"] = {}

        obj["references"] = []

        reference_ids = set([])

        for ref in references:
            ref_dict = ref.reference.to_dict_citation()

            if ref.reference_class == "description":
                obj["qualities"]["description"]["references"].append(ref_dict)
            elif ref.reference_class == "name_description":
                obj["qualities"]["name_description"]["references"].append(ref_dict)
            elif ref.reference_class == "gene_name":
                obj["qualities"]["gene_name"]["references"].append(ref_dict)
            elif ref.reference_class == "qualifier":
                obj["qualities"]["qualifier"]["references"].append(ref_dict)
            elif ref.reference_class == "feature_type":
                obj["qualities"]["feature_type"]["references"].append(ref_dict)
            elif ref.reference_class == "systematic_name":
                obj["qualities"]["id"]["references"].append(ref_dict)
            else:
                continue

            if ref.reference_id not in reference_ids:
                if(ref_dict not in obj["references"]):
                    obj["references"].append(ref_dict)

                obj["sgdid_ref"][ref.reference.sgdid] = ref.reference

            reference_ids.add(ref.reference_id)

        summary_references = DBSession.query(LocussummaryReference).filter(and_(LocussummaryReference.summary_id.in_(summary_ids), ~LocussummaryReference.reference_id.in_(blacklist))).order_by(LocussummaryReference.reference_order).all()
        for s in summary_references:
            if s.reference_id not in reference_ids:
                temp_ref = s.reference.to_dict_citation()
                if(temp_ref not in obj["references"]):
                    obj["references"].append(temp_ref)

                obj["sgdid_ref"][s.reference.sgdid] = s.reference
                reference_ids.add(s.reference_id)

        obj["reference_mapping"] = {}

        order = 1
        for reference in obj["references"]:
            obj["reference_mapping"][reference["id"]] = order
            order += 1

        return obj

    def regulation_overview_to_dict(self, summary_regulation):
        blacklist = (551590,)
        obj = {
            "regulator_count": DBSession.query(Regulationannotation).filter_by(target_id=self.dbentity_id).distinct(Regulationannotation.regulator_id).count(),
            "target_count": DBSession.query(Regulationannotation).filter_by(regulator_id=self.dbentity_id).distinct(Regulationannotation.target_id).count()
        }

        if len(summary_regulation) > 0:
            text = ""
            summary_ids = []
            for s in summary_regulation:
                text += s[1]
                summary_ids.append(s[0])

            summary_references = DBSession.query(LocussummaryReference).filter(and_(LocussummaryReference.summary_id.in_(summary_ids), ~LocussummaryReference.reference_id.in_(blacklist))).order_by(LocussummaryReference.reference_order).all()

            obj["paragraph"] = {
                "text": text,
                "date_edited": summary_regulation[-1][2].strftime("%Y-%m-%d"),
                "references": [r.reference.to_dict_citation() for r in summary_references]
            }

        return obj

    def paralogs_to_dict(self):
        PARALOG_RO_ID = 169738
        paralog_relations = DBSession.query(LocusRelation).filter(and_(LocusRelation.ro_id == PARALOG_RO_ID, or_(LocusRelation.parent_id == self.dbentity_id, LocusRelation.child_id == self.dbentity_id))).all()
        return [a.to_dict(self.dbentity_id) for a in paralog_relations]
    
    def complements_to_dict(self):
        complement_relations = DBSession.query(Functionalcomplementannotation).filter_by(dbentity_id=self.dbentity_id).all()
        return [a.to_dict(self.dbentity_id) for a in complement_relations]

    def protein_overview_to_dict(self):
        obj = {
            "length": 0,
            "molecular_weight": None,
            "pi": None, 
            "median_value": None,
            "median_abs_dev_value": None,
            "half_life": None
        }

        taxonomy_id = self.get_main_strain('taxonomy_id')
        protein = DBSession.query(Proteinsequenceannotation).filter_by(dbentity_id=self.dbentity_id, taxonomy_id=taxonomy_id).one_or_none()
        if protein:
            protein_sequence = DBSession.query(ProteinsequenceDetail).filter_by(annotation_id=protein.annotation_id).one_or_none()
            if protein_sequence:
                obj = protein_sequence.to_dict_lsp()
            else:
                obj["length"] = len(protein.residues) - 1

        abundance_data = DBSession.query(Proteinabundanceannotation).filter_by(dbentity_id=self.dbentity_id).all()
        for row in abundance_data:
            if row.median_value:
                obj["median_value"] = int(row.median_value)
                if row.median_abs_dev_value:
                    obj["median_abs_dev_value"] = int(row.median_abs_dev_value)
                break

        expt_data = DBSession.query(Proteinexptannotation).filter_by(dbentity_id=self.dbentity_id).all()
        if len(expt_data) > 0:
            obj["half_life"] = { 'data_value': str(expt_data[0].data_value),
                                 'data_unit': str(expt_data[0].data_unit) }

        return obj


    def phenotype_overview_to_dict(self):
        obj = {
            "paragraph": None,
            "classical_phenotypes": {},
            "large_scale_phenotypes": {}
        }

        phenotype_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type="Phenotype").one_or_none()

        if phenotype_summary:
            obj["paragraph"] = phenotype_summary.html

        phenotype_annotations = DBSession.query(Phenotypeannotation).filter_by(dbentity_id=self.dbentity_id).all()

        for annotation in phenotype_annotations:
            json = annotation.to_dict_lsp()

            if json["mutant"] in obj[json["experiment_category"]]:
                if json["phenotype"]["display_name"] not in [p["display_name"] for p in obj[json["experiment_category"]][json["mutant"]]]:
                    obj[json["experiment_category"]][json["mutant"]].append(json["phenotype"])
            else:
                obj[json["experiment_category"]][json["mutant"]] = [json["phenotype"]]

        counts = Phenotypeannotation.create_count_overview(None, phenotype_annotations=phenotype_annotations)
        obj["strains"] = counts["strains"]
        obj["experiment_categories"] = counts["experiment_categories"]

        return obj

    def literature_overview_to_dict(self):
        obj = {
            "primary_count": 0,
            "additional_count": 0,
            "review_count": 0,
            "go_count": 0,
            "phenotype_count": 0,
            "disease_count": 0,
            "interaction_count": 0,
            "regulation_count": 0,
            "ptm_count": 0,
            "funComplement_count": 0,
            "htp_count": 0,
            "total_count": 0
        }

        literature_counts = DBSession.query(Literatureannotation.topic, func.count(Literatureannotation.annotation_id)).filter_by(dbentity_id=self.dbentity_id).group_by(Literatureannotation.topic).all()

        for lit_count in literature_counts:
            if lit_count[0] == "Additional Literature":
                obj["additional_count"] = lit_count[1]
            elif lit_count[0] == "Reviews":
                obj["review_count"] = lit_count[1]
            elif lit_count[0] == "Primary Literature":
                obj["primary_count"] = lit_count[1]

        literature_ids = []
        for x in DBSession.query(Literatureannotation).filter_by(dbentity_id=self.dbentity_id).all():
            literature_ids.append(x.reference_id)
    
        interaction_ids = []
        for x in DBSession.query(Geninteractionannotation).filter(or_(Geninteractionannotation.dbentity1_id == self.dbentity_id, Geninteractionannotation.dbentity2_id == self.dbentity_id)).all() + DBSession.query(Physinteractionannotation.reference_id).filter(or_(Physinteractionannotation.dbentity1_id == self.dbentity_id, Physinteractionannotation.dbentity2_id == self.dbentity_id)).all():
            interaction_ids.append(x.reference_id)

        regulation_ids = []
        for x in DBSession.query(Regulationannotation).filter(or_(Regulationannotation.target_id == self.dbentity_id, Regulationannotation.regulator_id == self.dbentity_id)).all():
            regulation_ids.append(x.reference_id)

        regulation_htp_ids = []
        for x in DBSession.query(Regulationannotation).filter(or_(Regulationannotation.target_id == self.dbentity_id, Regulationannotation.regulator_id == self.dbentity_id)).filter(Regulationannotation.annotation_type == "high-throughput").all():
            regulation_htp_ids.append(x.reference_id)
        
        disease_ids = []
        for x in DBSession.query(Diseaseannotation).filter_by(dbentity_id = self.dbentity_id).all():
            disease_ids.append(x.reference_id)
        
        apo_ids = []
        for x in DBSession.query(Apo).filter_by(namespace_group="classical genetics").all():
            apo_ids.append(x.apo_id)
            
        phenotype_ids = []
        for x in DBSession.query(Phenotypeannotation).filter(and_(Phenotypeannotation.dbentity_id == self.dbentity_id, Phenotypeannotation.experiment_id.in_(apo_ids))).all():
            phenotype_ids.append(x.reference_id)

        apo_ids_large_scale = []
        for x in DBSession.query(Apo).filter_by(namespace_group="large-scale survey").all():
            apo_ids_large_scale.append(x.apo_id)

        phenotype_htp_ids = []
        for x in DBSession.query(Phenotypeannotation).filter(and_(Phenotypeannotation.dbentity_id == self.dbentity_id, Phenotypeannotation.experiment_id.in_(apo_ids_large_scale))).all():
            phenotype_htp_ids.append(x.reference_id)
        
        go_ids = []
        for x in DBSession.query(Goannotation).filter(and_(Goannotation.dbentity_id == self.dbentity_id, Goannotation.annotation_type != "high-throughput")).all():
            go_ids.append(x.reference_id)
            
        go_ids = set(go_ids) - set(Referencedbentity.get_go_blacklist_ids())

        go_htp_ids = []
        for x in DBSession.query(Goannotation).filter(and_(Goannotation.dbentity_id == self.dbentity_id, Goannotation.annotation_type == "high-throughput")).all():
            go_htp_ids.append(x.reference_id)

        htp_ids = regulation_htp_ids + phenotype_htp_ids + go_htp_ids

        ptm_ids = []
        for x in DBSession.query(Posttranslationannotation).filter_by(dbentity_id = self.dbentity_id).all():
            ptm_ids.append(x.reference_id)

        fc_ids = []
        for x in DBSession.query(Functionalcomplementannotation).filter_by(dbentity_id = self.dbentity_id).all():
            fc_ids.append(x.reference_id)
            
        obj["go_count"] = len(set(list(go_ids)))
        obj["phenotype_count"] = len(set(phenotype_ids))
        obj["interaction_count"] = len(set(interaction_ids))
        obj["regulation_count"] = len(set(regulation_ids))
        obj["disease_count"] = len(set(disease_ids))
        obj["ptm_count"] = len(set(ptm_ids))
        obj["funComplement_count"] = len(set(fc_ids))
        obj["htp_count"] = len(set(htp_ids))
        obj["total_count"] = len(set(literature_ids + interaction_ids + disease_ids + regulation_ids + phenotype_ids + ptm_ids + fc_ids + htp_ids + list(go_ids)))
        
        return obj

    def interaction_overview_to_dict(self):
        from .helpers import calc_venn_measurements

        obj = {
            "total_interactions": 0,
            "total_interactors": 0,
            "num_phys_interactors": 0,
            "num_gen_interactors": 0,
            "num_both_interactors": 0,
            "physical_experiments": {},
            "genetic_experiments": {},
            "total_interactions": 0,
            "gen_circle_size": 0,
            "phys_circle_size": 0,
            "circle_distance": 0
        }

        physical_interactions = DBSession.query(Physinteractionannotation.biogrid_experimental_system, func.count(Physinteractionannotation.annotation_id)).filter(or_(Physinteractionannotation.dbentity1_id == self.dbentity_id, Physinteractionannotation.dbentity2_id == self.dbentity_id)).group_by(Physinteractionannotation.biogrid_experimental_system).all()

        genetic_interactions = DBSession.query(Geninteractionannotation.biogrid_experimental_system, func.count(Geninteractionannotation.annotation_id)).filter(or_(Geninteractionannotation.dbentity1_id == self.dbentity_id, Geninteractionannotation.dbentity2_id == self.dbentity_id)).group_by(Geninteractionannotation.biogrid_experimental_system).all()

        physical_interactors_1 = DBSession.query(Physinteractionannotation.dbentity2_id).distinct(Physinteractionannotation.dbentity2_id).filter_by(dbentity1_id=self.dbentity_id).all()
        physical_interactors_2 = DBSession.query(Physinteractionannotation.dbentity1_id).distinct(Physinteractionannotation.dbentity1_id).filter_by(dbentity2_id=self.dbentity_id).all()
        genetic_interactors_1 = DBSession.query(Geninteractionannotation.dbentity2_id).distinct(Geninteractionannotation.dbentity2_id).filter(Geninteractionannotation.dbentity1_id==self.dbentity_id).all()
        genetic_interactors_2 = DBSession.query(Geninteractionannotation.dbentity1_id).distinct(Geninteractionannotation.dbentity1_id).filter(Geninteractionannotation.dbentity2_id==self.dbentity_id).all()

        for interaction in physical_interactions:
            obj["physical_experiments"][interaction[0]] = interaction[1]
            obj["total_interactions"] += interaction[1]

        for interaction in genetic_interactions:
            obj["genetic_experiments"][interaction[0]] = interaction[1]
            obj["total_interactions"] += interaction[1]

        physical_interactors = set(physical_interactors_1 + physical_interactors_2)
        genetic_interactors = set(genetic_interactors_1 + genetic_interactors_2)

        obj["num_both_interactors"] = len(physical_interactors.intersection(genetic_interactors))
        obj["num_phys_interactors"] = len(physical_interactors)
        obj["num_gen_interactors"] = len(genetic_interactors)
        obj["total_interactors"] =  obj["num_phys_interactors"] + obj["num_gen_interactors"] - obj["num_both_interactors"]

        x, y, z = calc_venn_measurements(obj["num_gen_interactors"], obj["num_phys_interactors"], obj["num_both_interactors"])
        obj["gen_circle_size"], obj["phys_circle_size"], obj["circle_distance"] = x, y, z

        interaction_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type="Interaction").one_or_none()
        if interaction_summary:
            obj["paragraph"] = interaction_summary.html

        return obj

    def go_overview_to_dict(self):
        obj = {
            "manual_molecular_function_terms": [],
            "manual_biological_process_terms": [],
            "manual_cellular_component_terms": [],
            "htp_molecular_function_terms": [],
            "htp_biological_process_terms": [],
            "htp_cellular_component_terms": [],
            "computational_annotation_count": 0,
            "go_slim": [],
            "go_slim_grouped": [],
            "date_last_reviewed": None
        }

        go_slims = DBSession.query(Goslimannotation).filter_by(dbentity_id=self.dbentity_id).all()
        process_go_slim_list = []
        function_go_slim_list = []
        component_go_slim_list = []
        complex_go_slim_list = []
        go_slim_list = []
        for go_slim in go_slims:
            go_slim_dict = go_slim.to_dict()
            if go_slim_dict not in go_slim_list:
                go_slim_list.append(go_slim_dict)
            if 'complex' in go_slim_dict['slim_name'].lower():
                if go_slim_dict not in complex_go_slim_list:
                    complex_go_slim_list.append(go_slim_dict)
            else:
                go = DBSession.query(Go).filter_by(go_id=go_slim_dict['go_id']).one_or_none()
                if go is None:
                    continue
                if 'component' in go.go_namespace:
                    if go_slim_dict not in component_go_slim_list:
                        component_go_slim_list.append(go_slim_dict)
                elif 'function' in go.go_namespace:
                    if go_slim_dict not in function_go_slim_list:
                        function_go_slim_list.append(go_slim_dict)
                elif go_slim_dict not in process_go_slim_list:
                    process_go_slim_list.append(go_slim_dict)
                          
        ## sort goslim terms here
        obj['go_slim'] = sorted(go_slim_list, key=lambda p: p['display_name'])
        process_go_slim_sorted_list = sorted(process_go_slim_list, key=lambda p: p['display_name'])
        function_go_slim_sorted_list = sorted(function_go_slim_list, key=lambda p: p['display_name'])
        component_go_slim_sorted_list = sorted(component_go_slim_list, key=lambda p: p['display_name'])
        complex_go_slim_sorted_list = sorted(complex_go_slim_list, key=lambda p: p['display_name'])
        obj['go_slim_grouped'] = function_go_slim_sorted_list + process_go_slim_sorted_list + component_go_slim_sorted_list + complex_go_slim_sorted_list
        
        go = {
            "cellular component": {},
            "molecular function": {},
            "biological process": {}
        }

        go_annotations_mc = DBSession.query(Goannotation).filter_by(dbentity_id=self.dbentity_id, annotation_type="manually curated").all()
        for annotation in go_annotations_mc:
            if obj["date_last_reviewed"] is None or annotation.date_assigned.strftime("%Y-%m-%d") > obj["date_last_reviewed"]:
                obj["date_last_reviewed"] = annotation.date_assigned.strftime("%Y-%m-%d")
        
            json = annotation.to_dict_lsp()

            namespace = json["namespace"]
            term = json["term"]["display_name"]

            if term in go[namespace]:
                for ec in json["evidence_codes"]:
                    if ec["display_name"] not in [e["display_name"] for e in go[namespace][term]["evidence_codes"]]:
                        go[namespace][term]["evidence_codes"].append(ec)
            else:
                go[namespace][term] = json
    
        for namespace in list(go.keys()):
            terms = sorted(list(go[namespace].keys()), key=lambda k : k.lower())
            if namespace == "cellular component":
                for term in terms:
                    obj["manual_cellular_component_terms"].append(self.modify_go_display_name(go[namespace][term]))
            elif namespace == "molecular function":
                for term in terms:
                    obj["manual_molecular_function_terms"].append(self.modify_go_display_name(go[namespace][term]))
            elif namespace == "biological process":
                for term in terms:
                    obj["manual_biological_process_terms"].append(self.modify_go_display_name(go[namespace][term]))

        obj["computational_annotation_count"] = DBSession.query(Goannotation).filter_by(dbentity_id=self.dbentity_id, annotation_type="computational").count()

        go = {
            "cellular component": {},
            "molecular function": {},
            "biological process": {}
        }

        go_annotations_htp = DBSession.query(Goannotation).filter_by(dbentity_id=self.dbentity_id, annotation_type="high-throughput").all()
        for annotation in go_annotations_htp:
            json = annotation.to_dict_lsp()

            namespace = json["namespace"]
            term = json["term"]["display_name"]

            if term in go[namespace]:
                for ec in json["evidence_codes"]:
                    if ec["display_name"] not in [e["display_name"] for e in go[namespace][term]["evidence_codes"]]:
                        go[namespace][term]["evidence_codes"].append(ec)
            else:
                go[namespace][term] = json

        for namespace in list(go.keys()):
            terms = sorted(list(go[namespace].keys()), key=lambda k : k.lower())

            if namespace == "cellular component":
                obj["htp_cellular_component_terms"] = [go[namespace][term] for term in terms]
            elif namespace == "molecular function":
                obj["htp_molecular_function_terms"] = [go[namespace][term] for term in terms]
            elif namespace == "biological process":
                obj["htp_biological_process_terms"] = [go[namespace][term] for term in terms]

        go_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type="Function").one_or_none()
        if go_summary:
            obj["paragraph"] = go_summary.html

        return obj

    def disease_overview_to_dict(self):
        obj = {
            "manual_disease_terms": [],
            "htp_disease_terms": [],
            "computational_annotation_count": 0,
            "date_last_reviewed": None
        }

        do = {
            "manually curated": {},
            "high-throughput": {},
            "computational": {}
        }

        do_annotations_mc = DBSession.query(Diseaseannotation).filter_by(dbentity_id=self.dbentity_id).all()
        for annotation in do_annotations_mc:
            if obj["date_last_reviewed"] is None or annotation.date_assigned.strftime("%Y-%m-%d") > obj[
                "date_last_reviewed"]:
                obj["date_last_reviewed"] = annotation.date_assigned.strftime("%Y-%m-%d")

            json = annotation.to_dict_lsp()

            namespace = json["annotation_type"]
            term = json["term"]["display_name"]

            if term in do[namespace]:
                for ec in json["evidence_codes"]:
                    if ec["display_name"] not in [e["display_name"] for e in do[namespace][term]["evidence_codes"]]:
                        do[namespace][term]["evidence_codes"].append(ec)
            else:
                do[namespace][term] = json

        for namespace in list(do.keys()):
            terms = sorted(list(do[namespace].keys()), key=lambda k: k.lower())
            if namespace == "manually curated":
                for term in terms:
                    obj["manual_disease_terms"].append(self.modify_go_display_name(do[namespace][term]))
            elif namespace == "high-throughput":
                for term in terms:
                    obj["htp_disease_terms"].append(self.modify_go_display_name(do[namespace][term]))

        obj["computational_annotation_count"] = DBSession.query(Diseaseannotation).filter_by(dbentity_id=self.dbentity_id,
                                                                                        annotation_type="computational").count()

        do_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id,
                                                                  summary_type="Disease").one_or_none()
        if do_summary:
            obj["paragraph"] = do_summary.html

        return obj

    def modify_go_display_name(self,item):
        item["term"]["display_name"] = item["term"]["display_name"].replace("_", " ")
        return item

    def get_go_count(self):
        return DBSession.query(Goannotation).filter_by(dbentity_id=self.dbentity_id).count()

    def get_phenotype_count(self):
        return DBSession.query(Phenotypeannotation).filter_by(dbentity_id=self.dbentity_id).count()

    def get_interaction_count(self):
        phys = DBSession.query(Physinteractionannotation).filter(or_(Physinteractionannotation.dbentity1_id == self.dbentity_id, Physinteractionannotation.dbentity2_id == self.dbentity_id)).count()
        genetic = DBSession.query(Geninteractionannotation).filter(or_(Geninteractionannotation.dbentity1_id == self.dbentity_id, Geninteractionannotation.dbentity2_id == self.dbentity_id)).count()
        return phys + genetic

    def get_literature_count(self):
        return DBSession.query(Literatureannotation.reference_id).filter((Literatureannotation.dbentity_id == self.dbentity_id)).count()

    def tabs(self):
        return {
            "id": self.dbentity_id,
            "protein_tab": self.has_protein,
            "interaction_tab": self.has_interaction,
            "summary_tab": self.has_summary,
            "go_tab": self.has_go,
            "sequence_section": self.has_sequence_section,
            "expression_tab": self.has_expression,
            "phenotype_tab": self.has_phenotype,
            "literature_tab": self.has_literature,
            "wiki_tab": False,
            "regulation_tab": self.has_regulation,
            "sequence_tab": self.has_sequence,
            "history_tab": self.has_history,
            "homology_tab": self.has_homology,
            "disease_tab": self.has_disease
        }

    # make some tabs false if the data is small, to return a smaller set of URLs for tab priming
    def get_quick_tabs(self):
        tabs = self.tabs()
        if tabs['go_tab']:
            gos = self.get_go_count()
            if (gos < 15):
                tabs['go_tab'] = False
        if tabs['interaction_tab']:
            interactions = self.get_interaction_count()
            if (interactions < 100):
                tabs['interaction_tab'] = False
        if tabs['literature_tab']:
            literatures = self.get_literature_count()
            if (literatures < 30):
                tabs['literature_tab'] = False
        return tabs

    # clears the URLs for all tabbed pages and secondary XHR requests on tabbed pages
    def get_secondary_cache_urls(self, is_quick=False):
        phenotype_items = ['phenotype_details', 'phenotype_graph']
        if is_quick:
            tabs = self.get_quick_tabs()
            protein_items = []
            if tabs['phenotype_tab']:
                phenotype_count = self.get_phenotype_count()
                if (phenotype_count < 15):
                    phenotype_items = []
        else:
            tabs = self.tabs()
            protein_items = ['sequence_details', 'posttranslational_details', 'ecnumber_details', 'protein_experiment_details', 'protein_domain_details', 'protein_domain_details']
        backend_urls_by_tab = {
            'protein_tab': protein_items,
            'interaction_tab': ['interaction_details', 'interaction_graph'],
            'summary_tab': ['expression_details'],
            'go_tab': ['go_details', 'go_graph'],
            'sequence_section': ['neighbor_sequence_details', 'sequence_details'],
            'expression_tab': [],
            'phenotype_tab': phenotype_items,
            'literature_tab': ['literature_details', 'literature_graph'],
            'regulation_tab': ['regulation_details', 'regulation_graph'],
            'sequence_tab': ['neighbor_sequence_details', 'sequence_details'],
            'history_tab': [],
            'homology_tab': ['homology_details'],
            'disease_tab': ['disease_details', 'disease_graph'],
        }
        base_url = self.get_base_url() + '/'
        backend_base_segment = self.get_secondary_base_url() + '/'
        urls = []

        # get all the urls
        for key in tabs:
            if key in ['sequence_section', 'id', 'summary_tab']:
                continue
            # if the tab is present, append all the needed urls to urls
            elif tabs[key]:
                for d in backend_urls_by_tab[key]:
                    secondary_url = backend_base_segment + d
                    urls.append(secondary_url)
        target_urls = list(set(urls))
        # filter out graph URLs if is_quick
        if is_quick:
            target_urls = [x for x in target_urls if 'graph' not in x]
        return target_urls

    def get_secondary_base_url(self):
        return '/webservice/locus/' + str(self.dbentity_id)

    def to_curate_dict(self):
        phenotype_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type='Phenotype').one_or_none()
        regulation_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type='Regulation').one_or_none()
        protein_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type='Protein').one_or_none()
        sequence_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type='Sequence').one_or_none()
        interaction_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type='Interaction').one_or_none()
        disease_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type='Disease').one_or_none()
        function_summary = DBSession.query(Locussummary).filter_by(locus_id=self.dbentity_id,summary_type='Function').one_or_none()

        if not phenotype_summary:
            phenotype_summary = ''
            phenotype_summary_pmids = ''
        else:
            summary_ref_ids = []
            for x in DBSession.query(LocussummaryReference).filter_by(summary_id=phenotype_summary.summary_id).all():
                summary_ref_ids.append(x.reference_id)
            pmids = []
            for x in DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(summary_ref_ids)).all():
                pmids.append(str(x.pmid))
            phenotype_summary_pmids = SEPARATOR.join(pmids)
            phenotype_summary = phenotype_summary.text
        if not regulation_summary:
            regulation_summary = ''
            regulation_summary_pmids = ''
        else:
            summary_ref_ids = DBSession.query(LocussummaryReference.reference_id).filter_by(summary_id=regulation_summary.summary_id).all()
            pmids = DBSession.query(Referencedbentity.pmid).filter(Referencedbentity.dbentity_id.in_(summary_ref_ids)).all()
            pmids = [str(x[0]) for x in pmids]
            regulation_summary_pmids = SEPARATOR.join(pmids)
            regulation_summary = regulation_summary.text
        if protein_summary:
            protein_summary = protein_summary.text
        if sequence_summary:
            sequence_summary = sequence_summary.text
        if interaction_summary:
            interaction_summary = interaction_summary.text
        if disease_summary:
            disease_summary = disease_summary.text 
        if function_summary:
            function_summary = function_summary.text    
        aliases = DBSession.query(LocusAlias).filter(and_(LocusAlias.locus_id==self.dbentity_id, LocusAlias.alias_type.in_(['Uniform', 'Non-uniform', 'Retired name']))).all()
        aliases_list = []
        for x in aliases:
            a_pmids = DBSession.query(LocusAliasReferences, Referencedbentity.pmid).filter(LocusAliasReferences.alias_id==x.alias_id).outerjoin(Referencedbentity).all()
            pmids_results = [str(y[1]) for y in a_pmids]
            aliases_list.append({
                'alias_id':x.alias_id,
                'alias': x.display_name,
                'pmids': SEPARATOR.join(pmids_results),
                'type': x.alias_type
            })

        gene_name_pmids = ''
        if self.gene_name:
            pmids_results = DBSession.query(LocusReferences, Referencedbentity.pmid).filter(and_(LocusReferences.locus_id==self.dbentity_id, LocusReferences.reference_class=='gene_name')).outerjoin(Referencedbentity).all()
            pmids_results = [str(x[1]) for x in pmids_results]
            gene_name_pmids = SEPARATOR.join(pmids_results)
        name_description_pmids = ''
        if self.name_description:
            pmids_results = DBSession.query(LocusReferences, Referencedbentity.pmid).filter(and_(LocusReferences.locus_id==self.dbentity_id, LocusReferences.reference_class=='name_description')).outerjoin(Referencedbentity).all()
            pmids_results = [str(x[1]) for x in pmids_results]
            name_description_pmids = SEPARATOR.join(pmids_results)
        description_pmids = ''
        if self.description:
            pmids_results = DBSession.query(LocusReferences, Referencedbentity.pmid).filter(and_(LocusReferences.locus_id==self.dbentity_id, LocusReferences.reference_class=='description')).outerjoin(Referencedbentity).all()
            pmids_results = [str(x[1]) for x in pmids_results]
            description_pmids = SEPARATOR.join(pmids_results)
        feature_type = DBSession.query(So.display_name).outerjoin(Dnasequenceannotation).filter(Dnasequenceannotation.dbentity_id == self.dbentity_id,Dnasequenceannotation.taxonomy_id == TAXON_ID, Dnasequenceannotation.dna_type == 'GENOMIC').scalar()
        protein_name = DBSession.query(LocusAlias.display_name).filter(LocusAlias.locus_id == self.dbentity_id, LocusAlias.alias_type == 'NCBI protein name').scalar()

        return {
            'name': self.display_name,
            'sgdid': self.sgdid,
            'systematic_name': self.systematic_name,
            'paragraphs': {
                'phenotype_summary': phenotype_summary,
                'phenotype_summary_pmids': phenotype_summary_pmids,
                'regulation_summary': regulation_summary,
                'regulation_summary_pmids': regulation_summary_pmids,
                'protein_summary':protein_summary,
                'sequence_summary':sequence_summary,
                'interaction_summary':interaction_summary,
                'disease_summary':disease_summary,
                'function_summary':function_summary
            },
            'basic': {
                'aliases': aliases_list,
                'description': self.description,
                'description_pmids': description_pmids,
                'feature_type': feature_type,
                'gene_name': self.gene_name,
                'gene_name_pmids': gene_name_pmids,
                'headline': self.headline,
                'name_description': self.name_description,
                'name_description_pmids': name_description_pmids,
                'qualifier': self.qualifier,
                'ncbi_protein_name': protein_name
            }
        }

    def update_basic(self, new_info, username):
        old_info = self.to_curate_dict()['basic']
        if 'feature_type' in list(new_info.keys()) and (new_info['feature_type'] == None or new_info['feature_type'] == ''):
            raise ValueError('Feature type cannot be blank.')
        if ('old_gene_name_alias_type' in list(new_info.keys())) and not new_info['old_gene_name_alias_type']:
            raise ValueError('Please select an alias type for old gene name.')
        # sanitize aliases
        if 'aliases' not in list(new_info.keys()):
            new_info['aliases'] = old_info['aliases']
        new_aliases = new_info['aliases']
        for x in new_aliases:
            if x['pmids'] is None:
                x['pmids'] = ''
        # list which keys need updating
        keys_to_update = []
        for key in list(new_info.keys()):
            # ignore old_gene_name_alias_type
            if key == 'old_gene_name_alias_type':
                continue
            if new_info[key] != old_info[key]:
                keys_to_update.append(key)
        # if changing gene name, append old name as alias
        if 'gene_name' in keys_to_update and old_info['gene_name']:
            new_alias_type = new_info['old_gene_name_alias_type']
            new_alias = { 'alias': old_info['gene_name'], 'pmids': old_info['gene_name_pmids'], 'type': new_alias_type }
            new_info['aliases'].append(new_alias)
            keys_to_update.append('aliases')        
        if len(keys_to_update) == 0:
            raise ValueError('Nothing has been changed.')
        else:
            curator_session = None
            try:
                curator_session = get_curator_session(username)
                self = curator_session.merge(self)
                for key in keys_to_update:
                    if key == 'description':
                        self.description = new_info['description']
                        # make headline
                        new_headline = new_info['description'][:70]
                        sep = ';'
                        new_headline = new_headline.split(sep, 1)[0]
                        self.headline = new_headline
                    elif key == 'gene_name':
                        new_name = new_info['gene_name']
                        if new_name == '' or new_name is None:
                            new_name = None
                            self.display_name = self.systematic_name
                        else:
                            # see if new name already exists, and if proper name
                            new_name_already_exists = curator_session.query(Locusdbentity).filter(Locusdbentity.gene_name == new_name).one_or_none()
                            if new_name_already_exists:
                                raise ValueError(new_name + ' is already a standard gene name and cannot be used.')
                            is_valid_gene_name = Locusdbentity.is_valid_gene_name(new_name)
                            if not is_valid_gene_name:
                                raise ValueError(new_name + ' does not follow standards for standard gene names.')
                            self.display_name = new_name
                            self.gene_name = new_name
                            # add locusnote and locusnotereference(s) for old gene_name_pmids
                            old_pmids = convert_space_separated_pmids_to_list(old_info['gene_name_pmids'])
                            for p in old_pmids:
                                ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == p).scalar()
                                note_html_str = '<b>Name:</b> ' + new_name
                                new_locusnote = Locusnote(
                                    source_id = SGD_SOURCE_ID,
                                    locus_id = self.dbentity_id,
                                    note_class = 'Locus',
                                    note_type = 'Name',
                                    note = note_html_str,
                                    created_by = username
                                )
                                curator_session.add(new_locusnote)
                                curator_session.flush()
                                curator_session.refresh(new_locusnote)
                                new_locusnote_ref = LocusnoteReference(
                                    note_id = new_locusnote.note_id,
                                    reference_id = ref_id,
                                    source_id = SGD_SOURCE_ID,
                                    created_by = username
                                )
                                curator_session.add(new_locusnote_ref)
                    elif key == 'name_description':
                        self.name_description = new_info['name_description']
                    elif key == 'qualifier':
                        self.qualifier = new_info['qualifier']
                    # changes outside of locusdbentity
                    elif key == 'ncbi_protein_name':
                        protein_alias = DBSession.query(LocusAlias).filter(LocusAlias.locus_id == self.dbentity_id, LocusAlias.alias_type == 'NCBI protein name').one_or_none()
                        protein_alias.display_name = new_info['ncbi_protein_name']
                    elif key == 'feature_type':
                        new_so_id = curator_session.query(So.so_id).filter(So.display_name == new_info['feature_type']).scalar()
                        dna_seq = curator_session.query(Dnasequenceannotation).filter(and_(Dnasequenceannotation.dbentity_id == self.dbentity_id, Dnasequenceannotation.taxonomy_id == TAXON_ID))\
                            .update({ 'so_id': new_so_id })
                    elif key == 'gene_name_pmids':
                        # delete the old name gene_name PMIDS
                        curator_session.query(LocusReferences).filter(and_(LocusReferences.locus_id==self.dbentity_id, LocusReferences.reference_class=='gene_name')).delete(synchronize_session=False)
                        pmid_list = convert_space_separated_pmids_to_list(new_info['gene_name_pmids'])
                        # add new entries
                        for p in pmid_list:
                            new_ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == p).scalar()
                            new_locus_ref = LocusReferences(
                                reference_id = new_ref_id,
                                locus_id = self.dbentity_id,
                                source_id = SGD_SOURCE_ID,
                                reference_class = 'gene_name',
                                created_by = username
                            )
                            curator_session.add(new_locus_ref)
                    elif key == 'description_pmids':
                        # delete the old name description PMIDS
                        old_pmid_list = convert_space_separated_pmids_to_list(old_info['description_pmids'])
                        new_pmid_list = convert_space_separated_pmids_to_list(new_info['description_pmids'])
                        
                        for old in old_pmid_list:
                            if old not in new_pmid_list:
                                ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == old).scalar()
                                if ref_id:
                                    curator_session.query(LocusReferences).filter(and_(LocusReferences.locus_id==self.dbentity_id, LocusReferences.reference_class=='description',LocusReferences.reference_id == ref_id)).delete(synchronize_session=False)


                        for new in new_pmid_list:
                            if new not in old_pmid_list:
                                ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == new).scalar()
                                if ref_id:
                                    new_locus_ref = LocusReferences(reference_id = ref_id,
                                                                    locus_id = self.dbentity_id,
                                                                    source_id = SGD_SOURCE_ID,
                                                                    reference_class = 'description',
                                                                    created_by = username
                                                                    )
                                    curator_session.add(new_locus_ref)

                        # curator_session.query(LocusReferences).filter(and_(LocusReferences.locus_id==self.dbentity_id, LocusReferences.reference_class=='description')).delete(synchronize_session=False)
                        # pmid_list = convert_space_separated_pmids_to_list(new_info['description_pmids'])
                        # # add new entries
                        # for p in pmid_list:
                        #     new_ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == p).scalar()
                        #     new_locus_ref = LocusReferences(
                        #         reference_id = new_ref_id,
                        #         locus_id = self.dbentity_id,
                        #         source_id = SGD_SOURCE_ID,
                        #         reference_class = 'description',
                        #         created_by = username
                        #     )
                        #     curator_session.add(new_locus_ref)

                    elif key == 'name_description_pmids':
                        # delete the old name name_description PMIDS
                        
                        old_pmid_list = convert_space_separated_pmids_to_list(old_info['name_description_pmids'])
                        new_pmid_list = convert_space_separated_pmids_to_list(new_info['name_description_pmids'])
                        
                        for old in old_pmid_list:
                            if old not in new_pmid_list:
                                ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == old).scalar()
                                if ref_id:
                                    curator_session.query(LocusReferences).filter(and_(LocusReferences.locus_id==self.dbentity_id, LocusReferences.reference_class=='name_description',LocusReferences.reference_id == ref_id)).delete(synchronize_session=False)


                        for new in new_pmid_list:
                            if new not in old_pmid_list:
                                ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == new).scalar()
                                if ref_id:
                                    new_locus_ref = LocusReferences(reference_id = ref_id,
                                                                    locus_id = self.dbentity_id,
                                                                    source_id = SGD_SOURCE_ID,
                                                                    reference_class = 'name_description',
                                                                    created_by = username
                                                                    )
                                    curator_session.add(new_locus_ref)
                        
                        # curator_session.query(LocusReferences).filter(and_(LocusReferences.locus_id==self.dbentity_id, LocusReferences.reference_class=='name_description')).delete(synchronize_session=False)
                        # pmid_list = convert_space_separated_pmids_to_list(new_info['name_description_pmids'])
                        # # add new entries
                        # for p in pmid_list:
                        #     new_ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == p).scalar()
                        #     new_locus_ref = LocusReferences(
                        #         reference_id = new_ref_id,
                        #         locus_id = self.dbentity_id,
                        #         source_id = SGD_SOURCE_ID,
                        #         reference_class = 'name_description',
                        #         created_by = username
                        #     )
                        #     curator_session.add(new_locus_ref)
                    elif key == 'aliases':
                        # delete old aliases and references
                        old_aliases = old_info['aliases']
                        new_aliases = new_info['aliases']
                        existing_ids = [ i['alias_id'] for i in old_aliases]
                        new_ids = [ i['alias_id'] for i in new_aliases]
                        existing_aliases_dict = {i['alias_id'] : i for i in old_aliases}
                        
                        #delete the one removed from the new_aliases
                        for alias in old_aliases:
                            if alias['alias_id'] not in new_ids:
                                alias_in_db = curator_session.query(LocusAlias).filter(and_(LocusAlias.alias_id==alias['alias_id'], LocusAlias.alias_type.in_(['Uniform', 'Non-uniform', 'Retired name']))).one_or_none()
                                note = '<b>Name:</b> '+alias['alias']
                                aliasnote_in_db = curator_session.query(Locusnote).filter(and_(Locusnote.locus_id==alias_in_db.locus_id,Locusnote.note == note)).one_or_none()
                                if aliasnote_in_db:
                                    curator_session.query(LocusnoteReference).filter(LocusnoteReference.note_id == aliasnote_in_db.note_id).delete(synchronize_session=False)
                                    curator_session.delete(aliasnote_in_db)    
                                curator_session.query(LocusAliasReferences).filter(LocusAliasReferences.alias_id == alias['alias_id']).delete(synchronize_session=False)
                                curator_session.delete(alias_in_db)
                        
                        curator_session.flush()

                        #TODO: Work on add/updating alias,aliasreference,notes
                        #add or update the one in new_aliases
                        for alias in new_aliases:
                            #Adding new LocusAlias, LocusAliasReference, Locusanote, Locusnote_reference
                            if alias['alias_id'] is None:
                                new_alias = LocusAlias(display_name = alias['alias'],
                                                       locus_id = self.dbentity_id,
                                                       alias_type = alias['type'],
                                                       has_external_id_section = False,
                                                       source_id = SGD_SOURCE_ID,
                                                       created_by = username)
                                curator_session.add(new_alias)
                                curator_session.flush()

                                int_pmids = convert_space_separated_pmids_to_list(alias['pmids'])
                                
                                #Add Locusnote
                                note = '<b>Name:</b> '+alias['alias']
                                locusnote = Locusnote(source_id = SGD_SOURCE_ID,locus_id = self.dbentity_id,note_class = 'Locus',
                                                      note_type = 'Name',note = note,created_by = username)
                                curator_session.add(locusnote)
                                curator_session.flush()

                                for p in int_pmids:
                                    new_ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == p).scalar()
                                    new_locus_alias_ref = LocusAliasReferences(alias_id = new_alias.alias_id,
                                                                               reference_id = new_ref_id,
                                                                               source_id = SGD_SOURCE_ID,
                                                                               created_by = username)
                                    #Add LocusnoteReference
                                    new_locus_note_ref = LocusnoteReference(note_id = locusnote.note_id,reference_id = new_ref_id,source_id = SGD_SOURCE_ID,created_by = username)
                                    curator_session.add(new_locus_alias_ref)
                                    curator_session.add(new_locus_note_ref)

                            #Update exisiting LocusAlias, LocusAliasReference, Locusnote, Locusnote_reference
                            elif alias['alias_id'] in existing_ids:
                                    note = '<b>Name:</b> '+existing_aliases_dict[alias['alias_id']]['alias']
                                    alias_in_db = curator_session.query(LocusAlias).filter(and_(LocusAlias.alias_id==alias['alias_id'], LocusAlias.alias_type.in_(['Uniform', 'Non-uniform', 'Retired name']))).one_or_none()
                                    aliasnote_in_db = curator_session.query(Locusnote).filter(and_(Locusnote.locus_id==self.dbentity_id,Locusnote.note == note)).one_or_none()
                                    #Only check for alias and type
                                    if alias['alias'] != existing_aliases_dict[alias['alias_id']]['alias'] or alias['type'] != existing_aliases_dict[alias['alias_id']]['type']:
                                        alias_in_db.display_name = alias['alias']
                                        alias_in_db.alias_type = alias['type']
                                        
                                        if aliasnote_in_db:    
                                            note = '<b>Name:</b> '+alias['alias']
                                            aliasnote_in_db.note = note
                                    
                                    #Check if pmids are add or deleted
                                    existing_pmids = convert_space_separated_pmids_to_list(existing_aliases_dict[alias['alias_id']]['pmids'])
                                    new_pmids = convert_space_separated_pmids_to_list(alias['pmids'])
                                    
                                    for new in new_pmids:
                                        if new not in existing_pmids:
                                            new_ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == new).scalar()
                                            new_locus_alias_ref = LocusAliasReferences(alias_id = alias_in_db.alias_id,
                                                                                       reference_id = new_ref_id,
                                                                                       source_id = SGD_SOURCE_ID,
                                                                                       created_by = username)
                                            if aliasnote_in_db:    
                                                new_locus_note_ref = LocusnoteReference(note_id = aliasnote_in_db.note_id,
                                                                                        reference_id = new_ref_id,
                                                                                        source_id = SGD_SOURCE_ID,
                                                                                        created_by = username)
                                                curator_session.add(new_locus_note_ref)    
                                            curator_session.add(new_locus_alias_ref)
                                    for old in existing_pmids:
                                        if old not in new_pmids:
                                            old_ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == old).scalar()
                                            old_locus_alias_ref = curator_session.query(LocusAliasReferences).filter(and_(LocusAliasReferences.alias_id==alias_in_db.alias_id,LocusAliasReferences.reference_id==old_ref_id)).one_or_none()
                                            
                                            if aliasnote_in_db:
                                                #delete any locus note reference 
                                                old_locus_note_ref = curator_session.query(LocusnoteReference).filter(and_(LocusnoteReference.note_id==aliasnote_in_db.note_id,LocusnoteReference.reference_id==old_ref_id)).one_or_none()
                                                curator_session.delete(old_locus_note_ref)
                                            
                                            curator_session.delete(old_locus_alias_ref)

                        # old_aliases = curator_session.query(LocusAlias).filter(and_(LocusAlias.locus_id==self.dbentity_id, LocusAlias.alias_type.in_(['Uniform', 'Non-uniform', 'Retired name']))).all()
                        # for a in old_aliases:
                        #     curator_session.query(LocusAliasReferences).filter(LocusAliasReferences.alias_id == a.alias_id).delete(synchronize_session=False)
                        #     curator_session.delete(a)
                        # curator_session.flush()

                        # for a in new_info['aliases']:
                        #     new_alias = LocusAlias(
                        #         display_name = a['alias'],
                        #         locus_id = self.dbentity_id,
                        #         alias_type = a['type'],
                        #         has_external_id_section = False,
                        #         source_id = SGD_SOURCE_ID,
                        #         created_by = username
                        #     )
                        #     curator_session.add(new_alias)
                        #     curator_session.flush()

                        #     int_pmids = convert_space_separated_pmids_to_list(a['pmids'])
                            
                        #     for p in int_pmids:
                        #         new_ref_id = curator_session.query(Referencedbentity.dbentity_id).filter(Referencedbentity.pmid == p).scalar()
                        #         new_locus_alias_ref = LocusAliasReferences(
                        #             alias_id = new_alias.alias_id,
                        #             reference_id = new_ref_id,
                        #             source_id = SGD_SOURCE_ID,
                        #             created_by = username
                        #         )
                        #         curator_session.add(new_locus_alias_ref)

                # create curator activity
                update_dict = {}
                for key in keys_to_update:
                    new_val = None
                    if key == 'aliases':
                        new_val = ''
                        for a in new_info[key]:
                            new_val = new_val + a['alias'] + ' '
                    else:
                        new_val = new_info[key]
                    update_dict[key] = new_val
                new_curate_activity = CuratorActivity(
                    display_name = self.display_name,
                    obj_url = self.obj_url,
                    activity_category = 'locus',
                    dbentity_id = self.dbentity_id,
                    message = 'updated locus information',
                    json = json.dumps({ 'keys': update_dict, 'modified_date': str(datetime.now())}),
                    created_by = username
                )
                curator_session.add(new_curate_activity)
                transaction.commit()
                self.ban_from_cache()
            except Exception as e:
                transaction.abort()
                traceback.print_exc()
                raise(e)
            finally:
                if curator_session:
                    curator_session.remove()
        return self.to_curate_dict()

    def update_summary(self, summary_type, username, text, pmid_list=[]):
        curator_session = None
        try:
            summary_type = summary_type.lower().capitalize()
            if summary_type == 'Regulation' and len(text) and len(pmid_list) == 0:
                raise ValueError('Regulation summaries require PMIDs.')
            # get a special session we can close
            curator_session = get_curator_session(username)
            summary = curator_session.query(Locussummary.summary_type, Locussummary.summary_id, Locussummary.html, Locussummary.date_created, Locussummary.text).filter_by(locus_id=self.dbentity_id, summary_type=summary_type).one_or_none()
            num_summary_refs = 0
            if summary and len(pmid_list):
                num_summary_refs = curator_session.query(LocussummaryReference).filter_by(summary_id=summary.summary_id).count()
            # ignore if same as old summary
            if summary and summary.text == text and num_summary_refs == len(pmid_list):
                return
            # ignore if blank and no summary
            if summary is None and len(text) == 0:
                return
            # if old summary exists and new value is blank, delete summary and locus summary references
            if summary and len(text) == 0:
                curator_session.query(LocussummaryReference).filter_by(summary_id=summary.summary_id).delete(synchronize_session=False)
                curator_session.query(Locussummary).filter_by(locus_id=self.dbentity_id, summary_type=summary_type).delete(synchronize_session=False)
                transaction.commit()
                curator_session.flush()
                return
            locus_names_ids = curator_session.query(Locusdbentity.display_name, Locusdbentity.sgdid).all()
            summary_html = link_gene_names(text, locus_names_ids, self.gene_name)
            # update
            if summary:
                curator_session.query(Locussummary).filter_by(summary_id=summary.summary_id).update({ 'text': text, 'html': summary_html })
            else:
                new_summary = Locussummary(
                    locus_id = self.dbentity_id,
                    summary_type = summary_type,
                    text = text,
                    html = summary_html,
                    created_by = username,
                    source_id = SGD_SOURCE_ID
                )
                curator_session.add(new_summary)
                summary = new_summary
            new_curate_activity = CuratorActivity(
                display_name = self.display_name,
                obj_url = self.obj_url,
                activity_category = 'locus',
                dbentity_id = self.dbentity_id,
                message = 'updated  ' + summary_type + ' summary',
                json = json.dumps({ 'keys': { 'summary': text },'modified_date': str(datetime.now()) }),
                created_by = username
            )
            curator_session.add(new_curate_activity)
            summary = curator_session.query(Locussummary.summary_type, Locussummary.summary_id, Locussummary.html, Locussummary.date_created).filter_by(locus_id=self.dbentity_id, summary_type=summary_type).one_or_none()
            # add LocussummaryReference(s)
            if len(pmid_list):
                matching_refs = curator_session.query(Referencedbentity).filter(Referencedbentity.pmid.in_(pmid_list)).all()
                if len(matching_refs) != len(pmid_list):
                    raise ValueError('PMID is not currently in SGD.')
                pmids = pmid_list
                for _i, p in enumerate(pmids):
                    matching_ref = [x for x in matching_refs if x.pmid == int(p)][0]
                    summary_id = summary.summary_id
                    reference_id = matching_ref.dbentity_id
                    order = _i + 1
                    # look for matching LocussummaryReference
                    matching_locussummary_refs = curator_session.query(LocussummaryReference).filter_by(summary_id=summary_id, reference_id=reference_id).all()
                    if len(matching_locussummary_refs):
                        curator_session.query(LocussummaryReference).filter_by(summary_id=summary_id,reference_id=reference_id).update({ 'reference_order': order })
                    else:
                        new_locussummaryref = LocussummaryReference(
                            summary_id = summary_id,
                            reference_id = reference_id,
                            reference_order = order,
                            source_id = SGD_SOURCE_ID,
                            created_by = username
                        )
                        curator_session.add(new_locussummaryref)
            # commit and close session to keep user session out of connection pool
            transaction.commit()
            return text
        except Exception as e:
            traceback.print_exc()
            if curator_session:
                curator_session.rollback()
            raise
        finally:
            if curator_session:
                curator_session.remove()

    def get_name(self):
        if self.gene_name:
            return self.gene_name
        else:
            return self.systematic_name

class Straindbentity(Dbentity):
    __tablename__ = 'straindbentity'
    __table_args__ = {'schema': 'nex'}
    __url_segment__ = '/strain/'

    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    strain_type = Column(String(40), nullable=False)
    genotype = Column(String(500))
    genbank_id = Column(String(40))
    assembly_size = Column(Integer)
    fold_coverage = Column(SmallInteger)
    scaffold_number = Column(Integer)
    longest_scaffold = Column(Integer)
    scaffold_nfifty = Column(Integer)
    feature_count = Column(Integer)
    headline = Column(String(70), nullable=False)

    taxonomy = relationship('Taxonomy')

    db_cache = {}

    @staticmethod
    def get_strains_by_taxon_id(taxon_id):
        if taxon_id in Straindbentity.db_cache:
            return Straindbentity.db_cache[taxon_id]
        else:
            strain = DBSession.query(Straindbentity).filter_by(taxonomy_id=taxon_id).all()
            Straindbentity.db_cache[taxon_id] = strain
            return strain

    def to_dict(self):
        obj = {
            "display_name": self.display_name,
            "urls": [],
            "status": self.strain_type,
            "genotype": self.genotype,
            "description": self.headline,
            "assembly_size": self.assembly_size,
            "genbank_id": self.genbank_id,
            "fold_coverage": self.fold_coverage,
            "scaffold_number": self.scaffold_number,
            "longest_scaffold": self.longest_scaffold,
            "scaffold_n50": self.scaffold_nfifty,
            "feature_count": self.feature_count,
            "paragraph": None
        }

        if obj["genotype"] == '' or obj["genotype"] == None:
            obj["genotype"] = None
        elif (len(obj["genotype"]) > 1 and obj["genotype"][0] == "\"" and obj["genotype"][-1] == "\""):
            obj["genotype"] = obj["genotype"][1:len(obj["genotype"])-1]

        rows = DBSession.query(StrainUrl).filter_by(strain_id=self.dbentity_id).all() 
        for u in rows:
            category = u.url_type.lower()
            if category == "external id":
                category = "source"

            obj["urls"].append({
                "display_name": u.display_name,
                "category": category,
                "link": u.obj_url
            })
            
        # paragraph = DBSession.query(Strainsummary.summary_id, Strainsummary.html).filter_by(strain_id=self.dbentity_id).one_or_none()

        paragraph = DBSession.query(Strainsummary).filter_by(strain_id=self.dbentity_id).one_or_none()
        if paragraph:
            reference_ids = []
            for x in DBSession.query(StrainsummaryReference).filter_by(summary_id=paragraph.summary_id).order_by(StrainsummaryReference.reference_order).all():
                reference_ids.append(x.reference_id)

            references = []
            if len(reference_ids):
                # reference_ids = [r[0] for r in reference_ids]
                references = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(reference_ids)).order_by(Referencedbentity.year.desc()).all()

            obj["paragraph"] = {
                "text": paragraph.html,
                "references": [r.to_dict_citation() for r in references]
            }

        contigs = DBSession.query(Contig).filter_by(taxonomy_id=self.taxonomy_id).all()
        obj["contigs"] = []

        chromosome_cache = {}
        for co in contigs:
            if co.display_name != "2-micron plasmid":
                obj["contigs"].append(co.to_dict_strain_table(chromosome_cache))

        return obj

    def get_strains_with_taxonomy(self):
        obj = {
            "display_name": self.display_name,
            "status": self.strain_type,
            "taxonomy_id": self.taxonomy.taxonomy_id
        }
        return obj

class Dbuser(Base):
    __tablename__ = 'dbuser'
    __table_args__ = {'schema': 'nex'}

    dbuser_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    username = Column(String(12), nullable=False, unique=True)
    first_name = Column(String(40), nullable=False)
    last_name = Column(String(40), nullable=False)
    status = Column(String(40), nullable=False)
    is_curator = Column(Boolean, nullable=False)
    email = Column(String(100), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))


class Deletelog(Base):
    __tablename__ = 'deletelog'
    __table_args__ = {'schema': 'nex'}

    deletelog_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.deletelog_seq'::regclass)"))
    bud_id = Column(Integer)
    tab_name = Column(String(60), nullable=False)
    primary_key = Column(BigInteger, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    deleted_row = Column(Text, nullable=False)


class Disease(Base):
    __tablename__ = 'disease'
    __table_args__ = {'schema': 'nex'}

    disease_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    doid = Column(String(20), nullable=False, unique=True)
    description = Column(String(2000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    is_obsolete = Column(Boolean, nullable=False)

    source = relationship('Source')

    # Allowed relationships (ro_ids) for graphs
    # 169782 'is_a', 169466 'regulates', 169299 'part of', 169468 'positively regulates', 169467 'negatively regulates'
    allowed_relationships = (169782, 169466, 169299, 169468, 169467)

    def to_dict(self):
        annotations_count = DBSession.query(Diseaseannotation.dbentity_id, func.count(Diseaseannotation.dbentity_id)).filter_by(disease_id=self.disease_id).group_by(Diseaseannotation.dbentity_id).count()

        children_relation = DBSession.query(DiseaseRelation).filter_by(parent_id=self.disease_id).all()
        if len(children_relation) > 0:
            children_annotations = len(set([c.child_id for c in children_relation]))
        else:
            children_annotations = 0

        obj = {
            "display_name": self.display_name.replace("_"," "),
            "urls": [],
            "disease_id": self.disease_id,
            "description": self.description,
            "aliases": [],
            "id": self.disease_id,
            "link": self.obj_url,
            "descendant_locus_count": 0,
            "locus_count": annotations_count,
            "descendant_locus_count": annotations_count + children_annotations
        }

        urls = DBSession.query(DiseaseUrl).filter_by(disease_id=self.disease_id).all()

        for url in urls:
            obj["urls"].append({
                "display_name": url.display_name,
                "link": url.obj_url,
                "category": url.url_type,
            })

        synonyms = DBSession.query(DiseaseAlias).filter_by(disease_id=self.disease_id).all()
        for synonym in synonyms:
            obj["aliases"].append(synonym.display_name)

        obj["locus_count"] = DBSession.query(Diseaseannotation.dbentity_id, func.count(Diseaseannotation.dbentity_id)).filter_by(disease_id=self.disease_id).group_by(Diseaseannotation.dbentity_id).count()

        return obj


    def ontology_graph(self):
        annotations = DBSession.query(Diseaseannotation.dbentity_id, func.count(Diseaseannotation.dbentity_id)).filter_by(disease_id=self.disease_id).group_by(Diseaseannotation.dbentity_id).count()

        nodes = [{
            "data": {
                "link": self.obj_url,
                "sub_type": "FOCUS",
                "name": self.display_name.replace("_"," ") + " (" + str(annotations) + ")",
                "id": str(self.disease_id)
            }
        }]

        edges = []
        all_children = []

        children_relation = DBSession.query(DiseaseRelation).filter(and_(DiseaseRelation.parent_id == self.disease_id, DiseaseRelation.ro_id.in_(Go.allowed_relationships))).all()

        for child_relation in children_relation[:6]:
            child_node = child_relation.to_graph(nodes, edges, add_child=True)
            all_children.append({
                "display_name": child_node.display_name,
                "link": child_node.obj_url
            })

        for child_relation in children_relation[7:]:
            child_node = child_relation.child
            all_children.append({
                "display_name": child_node.display_name,
                "link": child_node.obj_url
            })

        if len(children_relation) - 7 > 0:
            nodes.append({
                "data": {
                    "name": str(len(children_relation) - 7) + " more children",
                    "sub_type": "",
                    "link": None,
                    "id": "NodeMoreChildren"
                }
            })
            edges.append({
                "data": {
                    "name": "",
                    "target": "NodeMoreChildren",
                    "source": str(self.disease_id)
                }
            })

        parent_relations = self.parent_tree()
        for relation in parent_relations:
            relation.to_graph(nodes, edges, add_parent=True)

        graph = {
            "edges": edges,
            "nodes": nodes,
            "all_children": sorted(all_children, key=lambda f: str(f["display_name"]).lower())
        }

        return graph

    def parent_tree(self, max_level=3):
        relations = []

        level = 0
        parents_relation = DBSession.query(DiseaseRelation).filter(and_(DiseaseRelation.child_id == self.disease_id, DiseaseRelation.ro_id.in_(Go.allowed_relationships))).all()

        # breath-first-search stopping at level 3
        parents_at_level = len(parents_relation)
        while len(parents_relation) > 0:
            parent_relation = parents_relation[0]
            relations.append(parent_relation)

            del parents_relation[0]

            if level < max_level:
                new_parents = DBSession.query(DiseaseRelation).filter(and_(DiseaseRelation.child_id == parent_relation.parent.disease_id, DiseaseRelation.ro_id.in_(Disease.allowed_relationships))).all()

                parents_relation_ids = [p.relation_id for p in parents_relation]
                for p in new_parents:
                    if p.relation_id not in parents_relation_ids:
                        parents_relation.append(p)

                parents_at_level -= 1
                if parents_at_level == 0:
                    level += 1
                    parents_at_level = len(parents_relation)

        return relations


    def annotations_to_dict(self):
        annotations = DBSession.query(Diseaseannotation).filter_by(disease_id=self.disease_id).all()
        annotations_dict = []
        #human_gene_ids_to_symbols = {}
        human_gene_ids_to_symbols = {'display name' : 'TEST1'}

        for a in annotations:
            annotation = a.to_dict(disease=self)
            try:
                for y in annotation[0]['properties']:
                    if 'bioentity' in list(y.keys()):
                        entry = y['bioentity']
                        hgnc_id = entry['display_name']
                        if hgnc_id in list(human_gene_ids_to_symbols.keys()):
                            entry['display_name'] = human_gene_ids_to_symbols[hgnc_id]
                        else:
                            url = ALLIANCE_API_BASE_URL + hgnc_id
                            symbol = requests.request('GET', url).json()['symbol']
                            entry['display_name'] = symbol
                            human_gene_ids_to_symbols[hgnc_id] = symbol
            except Exception as e:
                traceback.print_exc()
            annotations_dict += annotation
        return annotations_dict

    def annotations_and_children_to_dict(self):

        annotations = DBSession.query(Diseaseannotation).filter_by(disease_id=self.disease_id).all()

        annotations_dict = []
        #human_gene_ids_to_symbols = {}
        human_gene_ids_to_symbols = {'display name' : 'TEST1'}

        for a in annotations:
            annotation = a.to_dict(disease=self)
            try:
                for y in annotation[0]['properties']:
                    if 'bioentity' in list(y.keys()):
                        entry = y['bioentity']
                        hgnc_id = entry['display_name']
                        if hgnc_id in list(human_gene_ids_to_symbols.keys()):
                            entry['display_name'] = human_gene_ids_to_symbols[hgnc_id]
                        else:
                            url = ALLIANCE_API_BASE_URL + hgnc_id
                            symbol = requests.request('GET', url).json()['symbol']
                            entry['display_name'] = symbol
                            human_gene_ids_to_symbols[hgnc_id] = symbol
            except Exception as e:
                traceback.print_exc()
            annotations_dict += annotation

        children_relation = DBSession.query(DiseaseRelation).filter(
            and_(DiseaseRelation.parent_id == self.disease_id, DiseaseRelation.ro_id.in_(Disease.allowed_relationships))).all()
        children = [c.child for c in children_relation]
        children_ids = [c.child_id for c in children_relation]

        for child in children:
            annotations = DBSession.query(Diseaseannotation).filter_by(disease_id=child.disease_id).all()

            for a in annotations:
                annotation = a.to_dict(disease=child)
                try:
                    for y in annotation[0]['properties']:
                        if 'bioentity' in list(y.keys()):
                            entry = y['bioentity']
                            hgnc_id = entry['display_name']
                            if hgnc_id in list(human_gene_ids_to_symbols.keys()):
                                entry['display_name'] = human_gene_ids_to_symbols[hgnc_id]
                            else:
                                url = ALLIANCE_API_BASE_URL + hgnc_id
                                symbol = requests.request('GET', url).json()['symbol']
                                entry['display_name'] = symbol
                                human_gene_ids_to_symbols[hgnc_id] = symbol
                except Exception as e:
                    traceback.print_exc()
                annotations_dict += annotation

            children_relation = DBSession.query(DiseaseRelation).filter(
                and_(DiseaseRelation.parent_id == child.disease_id, DiseaseRelation.ro_id.in_(Disease.allowed_relationships))).all()
            for c in children_relation:
                if c.child_id not in children_ids:
                    children.append(c.child)
                    children_ids.append(c.child_id)

        return annotations_dict

    def get_base_url(self):
        return self.obj_url

    def get_secondary_cache_urls(self, is_quick=False):
        url1 = self.get_secondary_base_url() + '/locus_details'
        return [url1]

    def can_skip_cache(self):
        annotation_count = annotations = DBSession.query(Diseaseannotation).filter_by(disease_id=self.disease_id).count()
        return annotation_count < 100

    def get_secondary_base_url(self):
        return '/webservice/disease/' + str(self.disease_id)

    def get_all_cache_urls(self, is_quick=False):
        if is_quick and self.can_skip_cache():
            return []
        base_target_url = self.get_base_url()
        target_urls = [base_target_url]
        if is_quick:
            target_urls = []
        details_urls = self.get_secondary_cache_urls(is_quick)
        target_urls = target_urls + details_urls
        urls = []
        for relative_url in target_urls:
            for base_url in cache_urls:
                url = base_url + relative_url
                urls.append(url)
        return urls


class DiseaseAlias(Base):
    __tablename__ = 'disease_alias'
    __table_args__ = (
        UniqueConstraint('disease_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    disease_id = Column(ForeignKey('nex.disease.disease_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    disease = relationship('Disease')
    source = relationship('Source')


class DiseaseRelation(Base):
    __tablename__ = 'disease_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.disease.disease_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.disease.disease_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Disease', primaryjoin='DiseaseRelation.child_id == Disease.disease_id')
    parent = relationship('Disease', primaryjoin='DiseaseRelation.parent_id == Disease.disease_id')
    ro = relationship('Ro')
    source = relationship('Source')

    def to_graph(self, nodes, edges, add_parent=False, add_child=False):
        adding_nodes = []
        if add_parent:
            adding_nodes.append(self.parent)

        if add_child:
            adding_nodes.append(self.child)

        for node in adding_nodes:
            annotations = DBSession.query(Diseaseannotation.dbentity_id, func.count(Diseaseannotation.dbentity_id)).filter_by(disease_id=node.disease_id).group_by(Diseaseannotation.dbentity_id).count()

            type = "development"
            name = node.display_name + " (" + str(annotations) + ")"

            nodes.append({
                "data": {
                    "link": node.obj_url,
                    "sub_type": type,
                    "name": name,
                    "id": str(node.disease_id)
                }
            })

        edges.append({
            "data": {
                "name": self.ro.display_name,
                "target": str(self.child.disease_id),
                "source": str(self.parent.disease_id)
            }
        })

        return self.child


class DiseaseUrl(Base):
    __tablename__ = 'disease_url'
    __table_args__ = (
        UniqueConstraint('disease_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    disease_id = Column(ForeignKey('nex.disease.disease_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    disease = relationship('Disease')
    source = relationship('Source')


class Diseaseannotation(Base):
    __tablename__ = 'diseaseannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'disease_id', 'eco_id', 'reference_id', 'annotation_type', 'disease_qualifier', 'source_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    disease_id = Column(ForeignKey('nex.disease.disease_id', ondelete='CASCADE'), nullable=False, index=True)
    eco_id = Column(ForeignKey('nex.eco.eco_id', ondelete='CASCADE'), nullable=False, index=True)
    annotation_type = Column(String(40), nullable=False)
    association_type = Column(String(20), nullable=False)
    disease_qualifier = Column(String(40), nullable=False)
    date_assigned = Column(DateTime, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity')
    disease = relationship('Disease')
    eco = relationship('Eco')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict_lsp(self):
        obj = {
            "annotation_type": self.annotation_type,
            "qualifiers": [self.disease_qualifier],
            "term": {
                "link": self.disease.obj_url,
                "display_name": self.disease.display_name.replace("_", " ")
            },
            "evidence_codes": []
        }

        alias = DBSession.query(EcoAlias).filter_by(eco_id=self.eco_id).all()

        experiment_name = alias[0].display_name
        for alia in alias:
            if len(experiment_name) > len(alia.display_name):
                experiment_name = alia.display_name

        alias_url = DBSession.query(EcoUrl).filter_by(eco_id=self.eco_id).all()

        experiment_url = None
        for url in alias_url:
            if url.display_name == "DO":
                experiment_url = url.obj_url
                break
        if experiment_url == None and len(alias_url) > 1:
            experiment_url = alias_url[1].obj_url

        obj["evidence_codes"] = [{
            "display_name": experiment_name,
            "link": experiment_url
        }]

        return obj

    # a Do annotation can be duplicated based on the Dosupportingevidence group id
    # so its to_dict method must return an array of dictionaries
    def to_dict(self, disease=None, reference=None):
        if disease == None:
            disease = self.disease

        if reference == None:
            reference = self.reference

        alias = DBSession.query(EcoAlias).filter_by(eco_id=self.eco_id).all()
        experiment_name = alias[0].display_name

        for alia in alias:
            if len(experiment_name) > len(alia.display_name):
                experiment_name = alia.display_name

        alias_url = DBSession.query(EcoUrl).filter_by(eco_id=self.eco_id).all()

        experiment_url = None
        for url in alias_url:
            if url.display_name == "DO":
                experiment_url = url.obj_url
                break
        if experiment_url == None and len(alias_url) > 1:
            experiment_url = alias_url[1].obj_url

        disease_obj = {
            "id": self.annotation_id,
            "annotation_type": self.annotation_type,
            "date_created": self.date_created.strftime("%Y-%m-%d"),
            "qualifier": self.disease_qualifier,
            "locus": {
                "display_name": self.dbentity.display_name,
                "link": self.dbentity.obj_url,
                "id": self.dbentity.dbentity_id,
                "format_name": self.dbentity.format_name
            },
            "disease": {
                "display_name": disease.display_name.replace("_", " "),
                "link": disease.obj_url,
                "disease_id": disease.doid,
                "id": disease.disease_id
            },
            "reference": {
                "display_name": self.reference.display_name,
                "link": self.reference.obj_url,
                "pubmed_id": self.reference.pmid
            },
            "source": {
                "display_name": self.source.display_name
            },
            "experiment": {
                "display_name": experiment_name,
                "link": experiment_url
            },
            "properties": []
        }

        supporting_evidences = DBSession.query(Diseasesupportingevidence).filter_by(annotation_id=self.annotation_id).all()
        se_groups = {}
        for se in supporting_evidences:
            evidence_dict = se.to_dict()
            if evidence_dict:
                if se.group_id not in se_groups:
                    se_groups[se.group_id] = [evidence_dict]
                else:
                    se_groups[se.group_id].append(evidence_dict)

        go_obj_evidence = []
        for group_id in se_groups:
            obj = copy.deepcopy(disease_obj)
            obj["properties"] = se_groups[group_id]
            go_obj_evidence.append(obj)

        if len(go_obj_evidence) == 0:
            go_obj_evidence = [disease_obj]

        final_obj = []
        for group_id in se_groups:
            obj = copy.deepcopy(disease_obj)
            obj["properties"] += se_groups[group_id]
            final_obj.append(obj)

        if len(final_obj) == 0:
            if len(go_obj_evidence) == 0:
                final_obj = [disease_obj]
            else:
                final_obj = go_obj_evidence

        return final_obj


class Diseasesubset(Base):
    __tablename__ = 'diseasesubset'
    __table_args__ = {'schema': 'nex'}

    diseasesubset_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    disease_id = Column(ForeignKey('nex.disease.disease_id', ondelete='CASCADE'), nullable=False, index=True)
    subset_name = Column(String(50), nullable=False)
    genome_count = Column(Integer, nullable=False)
    description = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    disease = relationship('Disease')
    source = relationship('Source')


class Diseasesubsetannotation(Base):
    __tablename__ = 'diseasesubsetannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'diseasesubset_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    diseasesubset_id = Column(ForeignKey('nex.diseasesubset.diseasesubset_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity')
    diseasesubset = relationship('Diseasesubset')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')


class Diseasesupportingevidence(Base):
    __tablename__ = 'diseasesupportingevidence'
    __table_args__ = (
        UniqueConstraint('annotation_id', 'dbxref_id', 'group_id', 'evidence_type'),
        {'schema': 'nex'}
    )

    diseasesupportingevidence_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.detail_seq'::regclass)"))
    annotation_id = Column(ForeignKey('nex.diseaseannotation.annotation_id', ondelete='CASCADE'), nullable=False)
    group_id = Column(BigInteger, nullable=False)
    dbxref_id = Column(String(40), nullable=False)
    obj_url = Column(String(500), nullable=False)
    evidence_type = Column(String(10), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    annotation = relationship('Diseaseannotation')

    def to_dict(self):
        source_id = self.dbxref_id.split(":")

        # the frontend expects a capitalized "role" to place the evidence in the right column of the annotation table
        if source_id[0] == "SGD":
            sgdid = source_id[1]
            dbentity = DBSession.query(Dbentity).filter_by(sgdid=sgdid).one_or_none()
            return {
                "bioentity": {
                    "display_name": dbentity.display_name,
                    "link": dbentity.obj_url,
                    "class_type": dbentity.subclass
                },
                "role": self.evidence_type.capitalize()
            }
        else:
            return {
                "bioentity": {
                    "display_name": self.dbxref_id,
                    "link": self.obj_url
                },
                "role": self.evidence_type.capitalize()
            }

        return None


class Dnasequenceannotation(Base):
    __tablename__ = 'dnasequenceannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'taxonomy_id', 'contig_id', 'so_id', 'dna_type'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    bud_id = Column(Integer)
    so_id = Column(ForeignKey('nex.so.so_id', ondelete='CASCADE'), nullable=False, index=True)
    dna_type = Column(String(50), nullable=False)
    contig_id = Column(ForeignKey('nex.contig.contig_id', ondelete='CASCADE'), nullable=False, index=True)
    seq_version = Column(DateTime)
    coord_version = Column(DateTime)
    genomerelease_id = Column(ForeignKey('nex.genomerelease.genomerelease_id', ondelete='CASCADE'), index=True)
    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)
    strand = Column(String(1), nullable=False)
    file_header = Column(String(200), nullable=False)
    download_filename = Column(String(100), nullable=False)
    file_id = Column(ForeignKey('nex.filedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    residues = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    contig = relationship('Contig')
    dbentity = relationship('Dbentity')
    file = relationship('Filedbentity', foreign_keys=[file_id])
    genomerelease = relationship('Genomerelease')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    so = relationship('So')
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict(self, loci=None, dnasubsequences=None):
        strains = Straindbentity.get_strains_by_taxon_id(self.contig.taxonomy_id)

        if len(strains) == 0:
            return None
        
        if loci and self.dbentity.subclass == 'LOCUS':
            locus = loci[self.dbentity_id]
        else:
            locus = DBSession.query(Locusdbentity).filter_by(dbentity_id=self.dbentity_id).one_or_none()
        if dnasubsequences:
            tags = dnasubsequences[self.annotation_id]
        else:
            tags = DBSession.query(Dnasubsequence).filter_by(annotation_id=self.annotation_id).all()

        tags = sorted(tags, key=lambda t: t.contig_end_index, reverse=(self.strand == "-"))

        if self.dbentity.subclass != 'LOCUS':
            return {
                "start": self.start_index,
                "end": self.end_index,
                "residues": self.residues,
                "contig": self.contig.to_dict_sequence_widget(),
                "strand": self.strand,
                "dna_type": self.dna_type
            }

        return {
            "start": self.start_index,
            "end": self.end_index,
            "residues": self.residues,
            "contig": self.contig.to_dict_sequence_widget(),
            "tags": [t.to_dict(self.strand) for t in tags],
            "strain": {
                "display_name": strains[0].display_name,
                "status": strains[0].strain_type,
                "format_name": "CEN.PK" if strains[0].format_name == "CENPK" else strains[0].format_name,
                "id": strains[0].dbentity_id,
                "link": strains[0].obj_url,
                "description": strains[0].headline
            },
            "locus": locus.to_dict_sequence_widget(),
            "strand": self.strand,
            "dna_type": self.dna_type,
            "feature_status": locus.dbentity_status
        }

class Dnasubsequence(Base):
    __tablename__ = 'dnasubsequence'
    __table_args__ = (
        UniqueConstraint('annotation_id', 'dbentity_id', 'relative_start_index', 'relative_end_index'),
        {'schema': 'nex'}
    )

    dnasubsequence_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.detail_seq'::regclass)"))
    annotation_id = Column(ForeignKey('nex.dnasequenceannotation.annotation_id', ondelete='CASCADE'), nullable=False)
    dbentity_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    display_name = Column(String(500), nullable=False)
    bud_id = Column(Integer)
    so_id = Column(ForeignKey('nex.so.so_id', ondelete='CASCADE'), nullable=False, index=True)
    relative_start_index = Column(Integer, nullable=False)
    relative_end_index = Column(Integer, nullable=False)
    contig_start_index = Column(Integer, nullable=False)
    contig_end_index = Column(Integer, nullable=False)
    seq_version = Column(DateTime)
    coord_version = Column(DateTime)
    genomerelease_id = Column(ForeignKey('nex.genomerelease.genomerelease_id', ondelete='CASCADE'), index=True)
    file_header = Column(String(200), nullable=False)
    download_filename = Column(String(100), nullable=False)
    file_id = Column(ForeignKey('nex.filedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    residues = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    annotation = relationship('Dnasequenceannotation')
    dbentity = relationship('Locusdbentity')
    file = relationship('Filedbentity')
    genomerelease = relationship('Genomerelease')
    so = relationship('So')

    def to_dict(self, strand):
        seq_version = self.seq_version
        if seq_version:
            seq_version = seq_version.strftime("%Y-%m-%d")

        coord_version = self.coord_version
        if coord_version:
            coord_version = coord_version.strftime("%Y-%m-%d")

        start = self.contig_start_index
        end = self.contig_end_index
        if strand == "-":
            start, end = end, start

        return {
            "relative_end": self.relative_end_index,
            "relative_start": self.relative_start_index,
            "display_name": self.display_name,
            "chromosomal_start": start,
            "chromosomal_end": end,
            "seq_version": seq_version,
            "class_type": self.display_name.upper(),
            "coord_version": coord_version,
            "date_created": self.date_created.strftime("%Y-%m-%d"),
            "format_name": self.display_name,
            "id": self.dnasubsequence_id
        }


class Dnasequencealignment(Base):
    __tablename__ = 'dnasequencealignment'
    __table_args__ = (
        UniqueConstraint('locus_id', 'display_name', 'dna_type'),
        {'schema': 'nex'}
    )

    alignment_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    contig_id = Column(ForeignKey('nex.contig.contig_id', ondelete='CASCADE'), nullable=False)
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    display_name = Column(String(500), nullable=False)
    dna_type = Column(String(50), nullable=False)
    block_sizes = Column(String(250), nullable=True)
    block_starts = Column(String(250), nullable=True)
    contig_start_index = Column(Integer, nullable=False)
    contig_end_index = Column(Integer, nullable=False)
    aligned_sequence = Column(String(500000), nullable=False)
    snp_sequence = Column(String(500000), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    contig = relationship('Contig')
    locus = relationship('Locusdbentity')


class Proteinsequencealignment(Base):
    __tablename__ = 'proteinsequencealignment'
    __table_args__ = (
        UniqueConstraint('display_name'),
        {'schema': 'nex'}
    )

    alignment_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    display_name = Column(String(500), nullable=False)
    aligned_sequence = Column(String(50000), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

class Sequencevariant(Base):
    __tablename__ = 'sequencevariant'
    __table_args__ = (
        UniqueConstraint('locus_id', 'seq_type', 'snp_type', 'start_index', 'end_index'),
        {'schema': 'nex'}
    )

    variant_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    seq_type = Column(String(50), nullable=False)
    score = Column(Integer, nullable=False)
    variant_type = Column(String(100), nullable=False)
    snp_type = Column(String(100), nullable=False)
    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    
class Ec(Base):
    __tablename__ = 'ec'
    __table_args__ = {'schema': 'nex'}

    ec_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    ecid = Column(String(20), nullable=False, unique=True)
    description = Column(String(1000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    is_obsolete = Column(Boolean, nullable=False)
    source = relationship('Source')

    def locus_details(self):
        loci = []
        for x in DBSession.query(LocusAlias).filter(and_(LocusAlias.display_name == self.display_name.replace("EC:", ""), LocusAlias.alias_type == "EC number")).all():
            loci.append(x.locus_id)
        loci_obj = DBSession.query(Locusdbentity).filter(Locusdbentity.dbentity_id.in_(loci)).all()

        return [{
            "locus": {
                "id": locus.dbentity_id,
                "display_name": locus.display_name,
                "format_name": locus.format_name,
                "link": locus.obj_url,
                "description": locus.description
            },
            "id": None
        } for locus in loci_obj]



    def to_dict(self):
        urls = DBSession.query(EcUrl).filter_by(ec_id=self.ec_id).all()

        return {
            "id": self.ec_id,
            "display_name": self.display_name.replace("EC:", ""),
            "description": self.description,
            "urls": [u.to_dict() for u in urls],
            "link": self.obj_url,
            "format_name": self.format_name
        }


class EcAlias(Base):
    __tablename__ = 'ec_alias'
    __table_args__ = (
        UniqueConstraint('ec_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    ec_id = Column(ForeignKey('nex.ec.ec_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    ec = relationship('Ec')
    source = relationship('Source')


class EcUrl(Base):
    __tablename__ = 'ec_url'
    __table_args__ = (
        UniqueConstraint('ec_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    ec_id = Column(ForeignKey('nex.ec.ec_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    ec = relationship('Ec')
    source = relationship('Source')

    def to_dict(self):
        return {
            "display_name": self.display_name,
            "link": self.obj_url
        }


class Eco(Base):
    __tablename__ = 'eco'
    __table_args__ = {'schema': 'nex'}

    eco_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    ecoid = Column(String(20), nullable=False, unique=True)
    description = Column(String(1000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    is_obsolete = Column(Boolean, nullable=False)

    source = relationship('Source')


class EcoAlias(Base):
    __tablename__ = 'eco_alias'
    __table_args__ = (
        UniqueConstraint('eco_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    eco_id = Column(ForeignKey('nex.eco.eco_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    eco = relationship('Eco')
    source = relationship('Source')


class EcoRelation(Base):
    __tablename__ = 'eco_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.eco.eco_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.eco.eco_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Eco', primaryjoin='EcoRelation.child_id == Eco.eco_id')
    parent = relationship('Eco', primaryjoin='EcoRelation.parent_id == Eco.eco_id')
    ro = relationship('Ro')
    source = relationship('Source')


class EcoUrl(Base):
    __tablename__ = 'eco_url'
    __table_args__ = (
        UniqueConstraint('eco_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    eco_id = Column(ForeignKey('nex.eco.eco_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    eco = relationship('Eco')
    source = relationship('Source')


class Edam(Base):
    __tablename__ = 'edam'
    __table_args__ = {'schema': 'nex'}

    edam_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    edamid = Column(String(20), nullable=False, unique=True)
    edam_namespace = Column(String(20), nullable=False)
    description = Column(String(2000))
    is_obsolete = Column(Boolean, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    source = relationship('Source')
    def to_dict(self):
        return {
            "id": self.edam_id,
            "name": self.format_name if self.format_name else '',
            "obj_url": self.obj_url if self.obj_url else '',
            "description": self.description if self.description else ''
        }


class EdamAlia(Base):
    __tablename__ = 'edam_alias'
    __table_args__ = (
        UniqueConstraint('edam_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    edam_id = Column(ForeignKey('nex.edam.edam_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    edam = relationship('Edam')
    source = relationship('Source')


class EdamRelation(Base):
    __tablename__ = 'edam_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.edam.edam_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.edam.edam_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Edam', primaryjoin='EdamRelation.child_id == Edam.edam_id')
    parent = relationship('Edam', primaryjoin='EdamRelation.parent_id == Edam.edam_id')
    ro = relationship('Ro')
    source = relationship('Source')


class EdamUrl(Base):
    __tablename__ = 'edam_url'
    __table_args__ = (
        UniqueConstraint('edam_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    edam_id = Column(ForeignKey('nex.edam.edam_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    edam = relationship('Edam')
    source = relationship('Source')


class Enzymeannotation(Base):
    __tablename__ = 'enzymeannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'ec_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    ec_id = Column(ForeignKey('nex.ec.ec_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity')
    ec = relationship('Ec')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')


class Expressionannotation(Base):
    __tablename__ = 'expressionannotation'
    __table_args__ = (
        UniqueConstraint('datasetsample_id', 'dbentity_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    datasetsample_id = Column(ForeignKey('nex.datasetsample.datasetsample_id', ondelete='CASCADE'), nullable=False)
    normalized_expression_value = Column(Float(53), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    log_ratio_value = Column(Float(53), nullable=False)

    datasetsample = relationship('Datasetsample')
    dbentity = relationship('Dbentity')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict(self):
        return self.datasetsample.dataset.to_dict(self.reference)

class Functionalcomplementannotation(Base):
    __tablename__ = 'functionalcomplementannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id','taxonomy_id','dbxref_id','direction','eco_id','reference_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False)
    eco_id = Column(ForeignKey('nex.eco.eco_id', ondelete='CASCADE'), nullable=False)
    dbxref_id = Column(String(30), nullable=False)
    obj_url = Column(String(300), nullable=False)
    direction = Column(String(70), nullable=False)
    curator_comment = Column(String(100), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    eco = relationship('Eco')
    ro = relationship('Ro')
    taxonomy = relationship('Taxonomy')

    # def to_dict(self, complement=None, reference=None):
    #    if complement == None:
    #        complement = self.complement
    def to_dict(self, reference=None): 
        if reference == None:
            reference = self.reference

        strain = Straindbentity.get_strains_by_taxon_id(self.taxonomy_id)

        strain_background = None
        if len(strain) == 1:
            strain_background = strain[0].display_name
        else:
            strain_background =	"Other"
            
        ## todo: add data to gene_name
    
        obj = {
            "id": self.annotation_id,
            "obj_url": self.obj_url,
            "species": map_id_species(self.dbxref_id),
            "strain_background": strain_background,
            "date_created": self.date_created.strftime("%Y-%m-%d"),
            "direction": self.direction,
            "dbxref_id": self.dbxref_id,
            "gene_name": self.dbentity.display_name,
            "curator_comment": self.curator_comment,
            "locus": {
                "display_name": self.dbentity.display_name,
                "link": self.dbentity.obj_url,
                "id": self.dbentity.dbentity_id,
                "format_name": self.dbentity.format_name
            },
            "references": [{
                "display_name": self.reference.display_name,
                "link": self.reference.obj_url,
                "pubmed_id": self.reference.pmid
            }],
            "source": {
                "display_name": self.source.display_name
            }
        }
        return obj

class FileKeyword(Base):
    __tablename__ = 'file_keyword'
    __table_args__ = (
        UniqueConstraint('file_id', 'keyword_id'),
        {'schema': 'nex'}
    )

    file_keyword_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    file_id = Column(ForeignKey('nex.filedbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    keyword_id = Column(ForeignKey('nex.keyword.keyword_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    file = relationship('Filedbentity')
    keyword = relationship('Keyword')
    source = relationship('Source')

class Geninteractionannotation(Base):
    __tablename__ = 'geninteractionannotation'
    __table_args__ = (
        UniqueConstraint('dbentity1_id', 'dbentity2_id', 'bait_hit', 'biogrid_experimental_system', 'reference_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity1_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    dbentity2_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    phenotype_id = Column(ForeignKey('nex.phenotype.phenotype_id', ondelete='CASCADE'), index=True)
    biogrid_experimental_system = Column(String(100), nullable=False)
    annotation_type = Column(String(20), nullable=False)
    bait_hit = Column(String(10), nullable=False)
    mutant_id = Column(ForeignKey('nex.apo.apo_id', ondelete='CASCADE'), nullable=False, index=True)
    description = Column(String(1000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity1 = relationship('Dbentity', primaryjoin='Geninteractionannotation.dbentity1_id == Dbentity.dbentity_id')
    dbentity2 = relationship('Dbentity', primaryjoin='Geninteractionannotation.dbentity2_id == Dbentity.dbentity_id')
    phenotype = relationship('Phenotype')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')
    mutant = relationship('Apo', primaryjoin='Geninteractionannotation.mutant_id == Apo.apo_id')

    def to_dict(self, reference=None):
        dbentity1 = self.dbentity1
        dbentity2 = self.dbentity2
        phenotype = self.phenotype

        if reference is None:
            reference = self.reference

        note = self.description
        if note:
            note = self.description.split('|')[0]
            
        obj = {
            "id": self.annotation_id,
            "note": note,
            "bait_hit": self.bait_hit,
            "locus1": {
                "id": self.dbentity1_id,
                "display_name": dbentity1.display_name,
                "link": dbentity1.obj_url,
                "format_name": dbentity1.format_name
            },
            "locus2": {
                "id": self.dbentity2_id,
                "display_name": dbentity2.display_name,
                "link": dbentity2.obj_url,
                "format_name": dbentity2.format_name
            },
            "experiment": {
                "display_name": self.biogrid_experimental_system,
                "link": None
            },
            "phenotype": None,
            "mutant_type": "unspecified", # This column exists in NEX, but doesn't in NEX2. In NEX they are "unspecified" for the whole table. It was asked to removed it.
            "interaction_type": "Genetic",
            "annotation_type": self.annotation_type,
            "source": {
                "display_name": self.source.display_name
            },
            "reference": {
                "display_name": reference.display_name,
                "pubmed_id": reference.pmid,
                "link": reference.obj_url
            }
        }

        if phenotype:
            obj["phenotype"] = {
                "display_name": phenotype.display_name,
                "link": phenotype.obj_url
            }

        ## adding alleles/scores/pvalues
        alleles = []
        for x in DBSession.query(AlleleGeninteraction).filter_by(interaction_id=self.annotation_id).all():
            allele1_name = ""
            if x.allele1_id:
                allele1_name = x.allele1.display_name
            allele2_name = ""
            if x.allele2_id:
                allele2_name = x.allele2.display_name
            alleles.append({ "allele1_name": allele1_name,
                             "allele2_name": allele2_name,
                             "sga_score": str(x.sga_score),
                             "pvalue": str(x.pvalue) })
        obj['alleles'] = alleles

        return obj


class Genomerelease(Base):
    __tablename__ = 'genomerelease'
    __table_args__ = {'schema': 'nex'}

    genomerelease_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    file_id = Column(ForeignKey('nex.filedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    sequence_release = Column(SmallInteger, nullable=False)
    annotation_release = Column(SmallInteger, nullable=False)
    curation_release = Column(SmallInteger, nullable=False)
    release_date = Column(DateTime, nullable=False)
    description = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    file = relationship('Filedbentity')
    source = relationship('Source')


class Go(Base):
    __tablename__ = 'go'
    __table_args__ = {'schema': 'nex'}

    go_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    goid = Column(String(20), nullable=False, unique=True)
    go_namespace = Column(String(20), nullable=False)
    description = Column(String(2000))
    is_obsolete = Column(Boolean, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')

    # Allowed relationships (ro_ids) for graphs
    # 169782 'is_a', 169466 'regulates', 169299 'part of', 169468 'positively regulates', 169467 'negatively regulates'
    allowed_relationships = (169782, 169466, 169299, 169468, 169467)

    def to_dict(self):
        annotations_count = DBSession.query(Goannotation.dbentity_id, func.count(Goannotation.dbentity_id)).filter_by(go_id=self.go_id).group_by(Goannotation.dbentity_id).count()

        children_relation = DBSession.query(GoRelation).filter_by(parent_id=self.go_id).all()
        if len(children_relation) > 0:
            children_annotations = len(set([c.child_id for c in children_relation]))
        else:
            children_annotations = 0

        obj = {
            "display_name": self.display_name.replace("_"," "),
            "urls": [],
            "go_id": self.goid,
            "go_aspect": self.go_namespace,
            "description": self.description,
            "aliases": [],
            "id": self.go_id,
            "link": self.obj_url,
            "descendant_locus_count": 0,
            "locus_count": annotations_count,
            "descendant_locus_count": annotations_count + children_annotations
        }

        urls = DBSession.query(GoUrl).filter_by(go_id=self.go_id).all()

        for url in urls:
            obj["urls"].append({
                "display_name": url.display_name,
                "link": url.obj_url,
                "category": url.url_type
            })

        synonyms = DBSession.query(GoAlias).filter_by(go_id=self.go_id).all()
        for synonym in synonyms:
            obj["aliases"].append(synonym.display_name)

        obj["locus_count"] = DBSession.query(Goannotation.dbentity_id, func.count(Goannotation.dbentity_id)).filter_by(go_id=self.go_id).group_by(Goannotation.dbentity_id).count()

        return obj

    def ontology_graph(self):
        annotations = DBSession.query(Goannotation.dbentity_id, func.count(Goannotation.dbentity_id)).filter_by(go_id=self.go_id).group_by(Goannotation.dbentity_id).count()

        nodes = [{
            "data": {
                "link": self.obj_url,
                "sub_type": "FOCUS",
                "name": self.display_name.replace("_"," ") + " (" + str(annotations) + ")",
                "id": str(self.go_id)
            }
        }]

        edges = []
        all_children = []

        children_relation = DBSession.query(GoRelation).filter(and_(GoRelation.parent_id == self.go_id, GoRelation.ro_id.in_(Go.allowed_relationships))).all()

        for child_relation in children_relation[:6]:
            child_node = child_relation.to_graph(nodes, edges, add_child=True)
            all_children.append({
                "display_name": child_node.display_name,
                "link": child_node.obj_url
            })

        for child_relation in children_relation[7:]:
            child_node = child_relation.child
            all_children.append({
                "display_name": child_node.display_name,
                "link": child_node.obj_url
            })

        if len(children_relation) - 7 > 0:
            nodes.append({
                "data": {
                    "name": str(len(children_relation) - 7) + " more children",
                    "sub_type": "",
                    "link": None,
                    "id": "NodeMoreChildren"
                }
            })
            edges.append({
                "data": {
                    "name": "",
                    "target": "NodeMoreChildren",
                    "source": str(self.go_id)
                }
            })

        parent_relations = self.parent_tree()
        for relation in parent_relations:
            relation.to_graph(nodes, edges, add_parent=True)

        graph = {
            "edges": edges,
            "nodes": nodes,
            "all_children": sorted(all_children, key=lambda f: str(f["display_name"]).lower())
        }

        return graph

    def parent_tree(self, max_level=3):
        relations = []

        level = 0
        parents_relation = DBSession.query(GoRelation).filter(and_(GoRelation.child_id == self.go_id, GoRelation.ro_id.in_(Go.allowed_relationships))).all()

        # breath-first-search stopping at level 3
        parents_at_level = len(parents_relation)
        while len(parents_relation) > 0:
            parent_relation = parents_relation[0]
            relations.append(parent_relation)

            del parents_relation[0]

            if level < max_level:
                new_parents = DBSession.query(GoRelation).filter(and_(GoRelation.child_id == parent_relation.parent.go_id, GoRelation.ro_id.in_(Go.allowed_relationships))).all()

                parents_relation_ids = [p.relation_id for p in parents_relation]
                for p in new_parents:
                    if p.relation_id not in parents_relation_ids:
                        parents_relation.append(p)

                parents_at_level -= 1
                if parents_at_level == 0:
                    level += 1
                    parents_at_level = len(parents_relation)

        return relations


    def annotations_to_dict(self):
        annotations = DBSession.query(Goannotation).filter_by(go_id=self.go_id).all()

        annotations_dict = []
        for a in annotations:
            annotations_dict += a.to_dict(go=self)

        return annotations_dict

    def annotations_and_children_to_dict(self):
        annotations_dict = []

        annotations = DBSession.query(Goannotation).filter_by(go_id=self.go_id).all()
        for a in annotations:
            annotations_dict += a.to_dict(go=self)

        children_relation = DBSession.query(GoRelation).filter(and_(GoRelation.parent_id == self.go_id, GoRelation.ro_id.in_(Go.allowed_relationships))).all()
        children = [c.child for c in children_relation]
        children_ids = [c.child_id for c in children_relation]

        for child in children:
            annotations = DBSession.query(Goannotation).filter_by(go_id=child.go_id).all()

            for a in annotations:
                annotations_dict += a.to_dict(go=child)

            children_relation = DBSession.query(GoRelation).filter(and_(GoRelation.parent_id == child.go_id, GoRelation.ro_id.in_(Go.allowed_relationships))).all()
            for c in children_relation:
                if c.child_id not in children_ids:
                    children.append(c.child)
                    children_ids.append(c.child_id)

        return annotations_dict

    def get_base_url(self):
        return self.obj_url

    def get_secondary_cache_urls(self, is_quick=False):
        url1 = self.get_secondary_base_url() + '/locus_details'
        return [url1]

    def can_skip_cache(self):
        annotation_count = annotations = DBSession.query(Goannotation).filter_by(go_id=self.go_id).count()
        return annotation_count < 100

    def get_secondary_base_url(self):
        return '/webservice/go/' + str(self.go_id)

    def get_all_cache_urls(self, is_quick=False):
        if is_quick and self.can_skip_cache():
            return []
        base_target_url = self.get_base_url()
        target_urls = [base_target_url]
        if is_quick:
            target_urls = []
        details_urls = self.get_secondary_cache_urls(is_quick)
        target_urls = target_urls + details_urls
        urls = []
        for relative_url in target_urls:
            for base_url in cache_urls:
                url = base_url + relative_url
                urls.append(url)
        return urls

class GoAlias(Base):
    __tablename__ = 'go_alias'
    __table_args__ = (
        UniqueConstraint('go_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    go_id = Column(ForeignKey('nex.go.go_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    go = relationship('Go')
    source = relationship('Source')


class GoRelation(Base):
    __tablename__ = 'go_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.go.go_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.go.go_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Go', primaryjoin='GoRelation.child_id == Go.go_id')
    parent = relationship('Go', primaryjoin='GoRelation.parent_id == Go.go_id')
    ro = relationship('Ro')
    source = relationship('Source')

    def to_graph(self, nodes, edges, add_parent=False, add_child=False):
        adding_nodes = []
        if add_parent:
            adding_nodes.append(self.parent)

        if add_child:
            adding_nodes.append(self.child)

        for node in adding_nodes:
            annotations = DBSession.query(Goannotation.dbentity_id, func.count(Goannotation.dbentity_id)).filter_by(go_id=node.go_id).group_by(Goannotation.dbentity_id).count()

            type = "development"
            name = node.display_name + " (" + str(annotations) + ")"

            nodes.append({
                "data": {
                    "link": node.obj_url,
                    "sub_type": type,
                    "name": name,
                    "id": str(node.go_id)
                }
            })

        edges.append({
            "data": {
                "name": self.ro.display_name,
                "target": str(self.child.go_id),
                "source": str(self.parent.go_id)
            }
        })

        return self.child


class GoUrl(Base):
    __tablename__ = 'go_url'
    __table_args__ = (
        UniqueConstraint('go_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    go_id = Column(ForeignKey('nex.go.go_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    go = relationship('Go')
    source = relationship('Source')


class Goannotation(Base):
    __tablename__ = 'goannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'go_id', 'eco_id', 'reference_id', 'annotation_type', 'go_qualifier', 'source_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    go_id = Column(ForeignKey('nex.go.go_id', ondelete='CASCADE'), nullable=False, index=True)
    eco_id = Column(ForeignKey('nex.eco.eco_id', ondelete='CASCADE'), nullable=False, index=True)
    annotation_type = Column(String(40), nullable=False)
    go_qualifier = Column(String(40), nullable=False)
    date_assigned = Column(DateTime, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity')
    eco = relationship('Eco')
    go = relationship('Go')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict_lsp(self):
        obj = {
            "namespace": self.go.go_namespace,
            "qualifiers": [self.go_qualifier.replace("_", " ")],
            "term": {
                "link": self.go.obj_url,
                "display_name": self.go.display_name.replace("_", " ")
            },
            "evidence_codes": []
        }

        alias = DBSession.query(EcoAlias).filter_by(eco_id=self.eco_id).all()
        
        experiment_name = None
        if len(alias) > 0:
            experiment_name = alias[0].display_name

        for alia in alias:
            if len(experiment_name) > len(alia.display_name):
                experiment_name = alia.display_name

        alias_url = DBSession.query(EcoUrl).filter_by(eco_id=self.eco_id).all()

        experiment_url = None
        for url in alias_url:
            if url.display_name not in ['BioPortal', 'OLS', 'Ontobee']:
                experiment_url = url.obj_url
                break
        if experiment_url == None and len(alias_url) > 1:
            experiment_url = alias_url[1].obj_url

        obj["evidence_codes"] = [{
            "display_name": experiment_name,
            "link": experiment_url
        }]

        return obj

    # a Go annotation can be duplicated based on the Gosupportingevidence group id
    # so its to_dict method must return an array of dictionaries
    def to_dict(self, go=None):
        if go == None:
            go = self.go

        alias = DBSession.query(EcoAlias).filter_by(eco_id=self.eco_id).all()

        experiment_name = None
        if len(alias) > 0:
            experiment_name = alias[0].display_name

        for alia in alias:
            if len(experiment_name) > len(alia.display_name):
                experiment_name = alia.display_name

        if experiment_name is None and self.eco.display_name.startswith('biological system reconstruction evidence'):
            experiment_name = 'BSR'
                
        alias_url = DBSession.query(EcoUrl).filter_by(eco_id=self.eco_id).all()

        experiment_url = None
        for url in alias_url:
            if url.display_name not in ['BioPortal', 'OLS', 'Ontobee']:
                experiment_url = url.obj_url
                break
        if experiment_url == None and len(alias_url) > 1:
            experiment_url = alias_url[1].obj_url
            
        date_created = self.date_created
        if self.annotation_type == 'computational':
            date_created = self.date_assigned
        go_obj = {
            "id": self.annotation_id,
            "annotation_type": self.annotation_type,
            "date_created": date_created.strftime("%Y-%m-%d"),
            "qualifier": self.go_qualifier.replace("_", " "),
            "locus": {
                "display_name": self.dbentity.display_name,
                "link": self.dbentity.obj_url,
                "id": self.dbentity.dbentity_id,
                "format_name": self.dbentity.format_name
            },
            "go": {
                "display_name": go.display_name.replace("_", " "),
                "link": go.obj_url,
                "go_id": go.goid,
                "go_aspect": go.go_namespace,
                "id": go.go_id
            },
            "reference": {
                "display_name": self.reference.display_name,
                "link": self.reference.obj_url,
                "pubmed_id": self.reference.pmid
            },
            "source": {
                "display_name": self.source.display_name
            },
            "experiment": {
                "display_name": experiment_name,
                "link": experiment_url
            },
            "properties": []
        }

        properties = []

        extensions = DBSession.query(Goextension).filter_by(annotation_id=self.annotation_id).all()
        extension_groups = {}
        for extension in extensions:
            extension_dict = extension.to_dict()
            if extension_dict:
                if extension.group_id not in extension_groups:
                    extension_groups[extension.group_id] = [extension_dict]
                else:
                    extension_groups[extension.group_id].append(extension_dict)

        supporting_evidences = DBSession.query(Gosupportingevidence).filter_by(annotation_id=self.annotation_id).all()
        se_groups = {}
        for se in supporting_evidences:
            evidence_dict = se.to_dict()
            if evidence_dict:
                if se.group_id not in se_groups:
                    se_groups[se.group_id] = [evidence_dict]
                else:
                    se_groups[se.group_id].append(evidence_dict)

        go_obj_extensions = []
        for group_id in extension_groups:
            obj = copy.deepcopy(go_obj)
            obj["properties"] = extension_groups[group_id]
            go_obj_extensions.append(obj)

        if len(go_obj_extensions) == 0:
            go_obj_extensions = [go_obj]

        final_obj = []
        for group_id in se_groups:
            for c in go_obj_extensions:
                obj = copy.deepcopy(c)
                obj["properties"] += se_groups[group_id]
                final_obj.append(obj)

        if len(final_obj) == 0:
            if len(go_obj_extensions) == 0:
                final_obj = [go_obj]
            else:
                final_obj = go_obj_extensions

        return final_obj


class Goextension(Base):
    __tablename__ = 'goextension'
    __table_args__ = (
        UniqueConstraint('annotation_id', 'dbxref_id', 'group_id', 'ro_id'),
        {'schema': 'nex'}
    )

    goextension_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.detail_seq'::regclass)"))
    annotation_id = Column(ForeignKey('nex.goannotation.annotation_id', ondelete='CASCADE'), nullable=False)
    group_id = Column(BigInteger, nullable=False)
    dbxref_id = Column(String(40), nullable=False)
    obj_url = Column(String(500), nullable=False)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    annotation = relationship('Goannotation')
    ro = relationship('Ro')

    def to_dict(self):
        source_id = self.dbxref_id.split(":")

        if source_id[0] == "SGD":
            sgdid = source_id[1]
            dbentity = DBSession.query(Dbentity).filter_by(sgdid=sgdid).one_or_none()
            return {
                "bioentity": {
                    "display_name": dbentity.display_name,
                    "link": dbentity.obj_url,
                    "class_type": dbentity.subclass
                },
                "role": self.ro.display_name
            }
        elif source_id[0] == "GO":
            go_evidence = DBSession.query(Go).filter_by(goid=self.dbxref_id).one_or_none()
            if go_evidence:
                return {
                    "bioentity": {
                        "display_name": go_evidence.display_name,
                        "link": go_evidence.obj_url
                    },
                    "role": self.ro.display_name
                }
        elif source_id[0] == "CHEBI":
            chebi = DBSession.query(Chebi).filter_by(chebiid=self.dbxref_id).one_or_none()
            if chebi:
                return {
                    "bioentity": {
                        "display_name": chebi.display_name,
                        "link": chebi.obj_url
                    },
                    "role": self.ro.display_name
                }
        else:

            dbxref_id = source_id[1]
            if dbxref_id in ['MGI', 'locus']:
                dbxref_id = dbxref_id + ":" + source_id[2]
                
            return {
                "bioentity": {
                    "display_name": dbxref_id,
                    "link": self.obj_url
                },
                "role": self.ro.display_name
            }

        return None


class Goslim(Base):
    __tablename__ = 'goslim'
    __table_args__ = {'schema': 'nex'}

    goslim_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    go_id = Column(ForeignKey('nex.go.go_id', ondelete='CASCADE'), nullable=False, index=True)
    slim_name = Column(String(40), nullable=False)
    genome_count = Column(Integer, nullable=False)
    description = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    go = relationship('Go')
    source = relationship('Source')

    def to_dict(self):
        # if self.slim_name == "Yeast GO-Slim":
        return {
            "slim_name": self.slim_name,
            "go_id": self.go_id,
            "link": self.obj_url,
            "display_name": self.display_name.replace("_", " ")
        }
        # else:
        #    return None

    def to_snapshot_dict(self):
        direct_annotation_gene_count = DBSession.query(Goannotation).filter_by(go_id=self.go_id).count()
        return {
            "descendant_annotation_gene_count": self.genome_count,
            "format_name": self.display_name if self.display_name in ['molecular_function', 'biological_process', 'cellular_component'] else self.obj_url.split('/')[2],
            "display_name": self.display_name.replace('_', ' '),
            "link": self.obj_url,
            "direct_annotation_gene_count": direct_annotation_gene_count,
            "id": self.go_id,
            "is_root": True if self.display_name in ['molecular_function', 'biological_process', 'cellular_component'] else False
        }

class Goslimannotation(Base):
    __tablename__ = 'goslimannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'goslim_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    goslim_id = Column(ForeignKey('nex.goslim.goslim_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity')
    goslim = relationship('Goslim')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict(self):
        return self.goslim.to_dict()


class Gosupportingevidence(Base):
    __tablename__ = 'gosupportingevidence'
    __table_args__ = (
        UniqueConstraint('annotation_id', 'dbxref_id', 'group_id', 'evidence_type'),
        {'schema': 'nex'}
    )

    gosupportingevidence_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.detail_seq'::regclass)"))
    annotation_id = Column(ForeignKey('nex.goannotation.annotation_id', ondelete='CASCADE'), nullable=False)
    group_id = Column(BigInteger, nullable=False)
    dbxref_id = Column(String(40), nullable=False)
    obj_url = Column(String(500), nullable=False)
    evidence_type = Column(String(10), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    annotation = relationship('Goannotation')

    def to_dict(self):
        source_id = self.dbxref_id.split(":")

        # the frontend expects a capitalized "role" to place the evidence in the right column of the annotation table

        if source_id[0] == "SGD":
            sgdid = source_id[1]
            dbentity = DBSession.query(Dbentity).filter_by(sgdid=sgdid).one_or_none()
            return {
                "bioentity": {
                    "display_name": dbentity.display_name,
                    "link": dbentity.obj_url,
                    "class_type": dbentity.subclass
                },
                "role": self.evidence_type.capitalize()
            }
        elif source_id[0] == "GO":
            go_evidence = DBSession.query(Go).filter_by(goid=self.dbxref_id).one_or_none()
            if go_evidence:
                return {
                    "bioentity": {
                        "display_name": go_evidence.display_name,
                        "link": go_evidence.obj_url
                    },
                    "role": self.evidence_type.capitalize()
                }
        elif source_id[0] == "CHEBI":
            chebi = DBSession.query(Chebi).filter_by(chebiid=self.dbxref_id).one_or_none()
            if chebi:
                return {
                    "bioentity": {
                        "display_name": chebi.display_name,
                        "link": chebi.obj_url
                    },
                    "role": self.evidence_type.capitalize()
                }
        else:

            dbxref_id = source_id[1]
            if dbxref_id in ['MGI', 'locus']:
                dbxref_id = dbxref_id + ":" + source_id[2]

            return {
                "bioentity": {
                    "display_name": dbxref_id,
                    "link": self.obj_url
                },
                "role": self.evidence_type.capitalize()
            }

        return None

class Journal(Base):
    __tablename__ = 'journal'
    __table_args__ = (
        UniqueConstraint('med_abbr', 'title'),
        {'schema': 'nex'}
    )

    journal_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    med_abbr = Column(String(100))
    title = Column(String(200))
    issn_print = Column(String(10))
    issn_electronic = Column(String(10))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')


class Keyword(Base):
    __tablename__ = 'keyword'
    __table_args__ = {'schema': 'nex'}

    keyword_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False, index=True)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    description = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    is_obsolete = Column(Boolean, nullable=False)
    
    source = relationship('Source')

    def to_simple_dict(self):
        return {
            "link": self.obj_url,
            "display_name": self.display_name
        }

    def to_dict(self):
        obj = {
            "display_name": self.display_name,
            "description": self.description,
            "bioitems": []
        }

        dataset_keywords = DBSession.query(DatasetKeyword).filter_by(keyword_id=self.keyword_id).all()

        dataset_ids = [d.dataset_id for d in dataset_keywords]
        datasets = DBSession.query(Dataset).filter(Dataset.dataset_id.in_(list(dataset_ids))).all()
        for dataset in datasets:
            obj["bioitems"].append(dataset.to_dict())

        return obj

class Literatureannotation(Base):
    __tablename__ = 'literatureannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'reference_id', 'topic'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    topic = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    acceptable_tags = {
        'classical_phenotype': 'Primary Literature',
        'go': 'Primary Literature',
        'other_primary': 'Primary Literature',
        'headline_information': 'Primary Literature',
        'additional_literature': 'Additional Literature',
        'htp_phenotype': 'Omics',
        'non_phenotype_htp': 'Omics',
        'reviews': 'Reviews'
    }

    @staticmethod
    def is_primary_tag(tag):
        if tag not in Literatureannotation.acceptable_tags:
            return False
        return 'Primary' in Literatureannotation.acceptable_tags[tag]

    @staticmethod
    def factory(reference_id, tag, dbentity_id, created_by, source_id=824, taxonomy_id=274803):
        if tag not in Literatureannotation.acceptable_tags:
            return None

        return Literatureannotation(
            dbentity_id=dbentity_id,
            source_id=source_id,
            taxonomy_id=taxonomy_id,
            reference_id=reference_id,
            topic=Literatureannotation.acceptable_tags[tag],
            created_by=created_by
        )

    def to_dict(self):
        obj = {
            "topic": self.topic,
            "locus": None
        }

        entity = self.dbentity

        if entity:
            link = entity.obj_url
            if entity.subclass == 'COMPLEX':
                link = '/complex/' + entity.format_name
            elif entity.subclass == 'PATHWAY':
                pathway = DBSession.query(Pathwaydbentity).filter_by(dbentity_id=entity.dbentity_id).one_or_none()
                link = 'https://pathway.yeastgenome.org/YEAST/new-image?type=PATHWAY&object=' + pathway.biocyc_id + '&detail-level=2'
            elif entity.subclass == 'ALLELE':
                link = '/allele/' + entity.format_name
                
            obj["locus"] = {
                "display_name": entity.display_name,
                "link": link
            }

        return obj

    def get_name(self):
        c_name = self.topic
        for key, value in Literatureannotation.acceptable_tags.items():
            if value == c_name:
                return key
        return None

class LocusAlias(Base):
    __tablename__ = 'locus_alias'
    __table_args__ = (
        UniqueConstraint('locus_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    has_external_id_section = Column(Boolean, nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    locus = relationship('Locusdbentity')
    source = relationship('Source')


class LocusAliasReferences(Base):
    __tablename__ = 'locusalias_reference'
    __table_args__ = (
        UniqueConstraint('alias_id', 'reference_id', 'source_id'),
        {'schema': 'nex'}
    )

    locusalias_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    alias_id = Column(ForeignKey('nex.locus_alias.alias_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    alias = relationship('LocusAlias')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')


class LocusReferences(Base):
    __tablename__ = 'locus_reference'
    __table_args__ = (
        UniqueConstraint('locus_id', 'reference_id', 'source_id'),
        {'schema': 'nex'}
    )

    locus_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_class = Column(String(40), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    locus = relationship('Locusdbentity', foreign_keys=[locus_id])
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')


class LocusRelation(Base):
    __tablename__ = 'locus_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    parent_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Locusdbentity', primaryjoin='LocusRelation.child_id == Locusdbentity.dbentity_id')
    parent = relationship('Locusdbentity', primaryjoin='LocusRelation.parent_id == Locusdbentity.dbentity_id')
    ro = relationship('Ro')
    source = relationship('Source')

    def to_dict(self, real_parent_id):
        # the parent should be the gene in the real_parent_id parameter, not parent_id column bc relatinships are only represented once
        parent = self.parent
        child = self.child
        if self.child_id == real_parent_id:
            parent = self.child
            child = self.parent
        locusrelation_refs = DBSession.query(LocusRelationReference).filter_by(relation_id=self.relation_id).all()
        refs = [a.to_dict() for a in locusrelation_refs]
        return {
            'id': self.relation_id,
            'parent': parent.to_dict_analyze(),
            'child': child.to_dict_analyze(),
            'date_created': self.date_created.strftime("%Y-%m-%d"),
            'relation_type': self.ro.display_name,
            'references': refs,
            'source': self.source.to_dict()
        }

class LocusUrl(Base):
    __tablename__ = 'locus_url'
    __table_args__ = (
        UniqueConstraint('locus_id', 'display_name', 'obj_url', 'placement'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    placement = Column(String(100), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    locus = relationship('Locusdbentity')
    source = relationship('Source')

    def to_dict(self):
        placement = self.placement
        if placement.endswith('INTERACTION_RESOURCES') or placement.endswith('EXPRESSION_RESOURCES') or placement.startswith('LOCUS_PROTEIN'):
            placement = self.placement.replace("_RESOURCES", "", 1)

        if placement == "LOCUS_PROTEIN_LOCALIZATION": # yes, this typo is propagated in the frontend, so it needs to be 'adjusted' here
            placement = "LOCUS_PROEIN_LOCALIZATION"

        if placement == "LOCUS_PROTEIN_PTM":
            placement = "LOCUS_PROTEIN_MODIFICATIONS"

        return {
            "category": placement,
            "link": self.obj_url,
            "display_name": self.display_name
        }


class Locusnote(Base):
    __tablename__ = 'locusnote'
    __table_args__ = {'schema': 'nex'}

    note_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.note_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    locus_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    note_class = Column(String(40), nullable=False)
    note_type = Column(String(40), nullable=False)
    note = Column(String(2000), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')

    def to_dict(self):
        references = DBSession.query(LocusnoteReference).filter_by(note_id=self.note_id).all()

        return {
            "category": self.note_type,
            "history_type": "LSP" if self.note_class.upper() == "LOCUS" else self.note_class.upper(),
            "note": self.note,
            "date_created": self.date_created.strftime("%Y-%m-%d"),
            "references": [ref.reference.to_dict_citation() for ref in references]
        }


class LocusnoteReference(Base):
    __tablename__ = 'locusnote_reference'
    __table_args__ = {'schema': 'nex'}

    note_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    note_id = Column(ForeignKey('nex.locusnote.note_id', ondelete='CASCADE'), index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    note = relationship('Locusnote')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')


class Locussummary(Base):
    __tablename__ = 'locussummary'
    __table_args__ = (
        UniqueConstraint('locus_id', 'summary_type', 'summary_order'),
        {'schema': 'nex'}
    )

    summary_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.summary_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    summary_type = Column(String(40), nullable=False)
    summary_order = Column(SmallInteger, nullable=False, server_default=text("1"))
    text = Column(Text, nullable=False)
    html = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=FetchedValue())
    created_by = Column(String(12), nullable=False)

    locus = relationship('Locusdbentity')
    source = relationship('Source')

    def to_dict(self):
        summary_type_url_segment = self.summary_type.lower()
        if summary_type_url_segment not in ['phenotype', 'regulation']:
            summary_type_url_segment = ''
        preview_url = '/locus/' + self.locus.sgdid + '/' + summary_type_url_segment
        return {
            'category': 'locus',
            'created_by' : self.created_by,
            'href': preview_url,
            'date_created': self.date_created.strftime("%Y-%m-%d"),
            'time_created': self.date_created.isoformat(),
            'name': self.locus.display_name,
            'type': self.summary_type + ' summary',
            'value': self.text
        }

   
class LocussummaryReference(Base):
    __tablename__ = 'locussummary_reference'
    __table_args__ = (
        UniqueConstraint('summary_id', 'reference_id'),
        {'schema': 'nex'}
    )

    summary_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    summary_id = Column(ForeignKey('nex.locussummary.summary_id', ondelete='CASCADE'), nullable=False)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_order = Column(SmallInteger, nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    reference = relationship('Referencedbentity')
    source = relationship('Source')
    summary = relationship('Locussummary')

class LocusRelationReference(Base):
    __tablename__ = 'locusrelation_reference'
    __table_args__ = (
        UniqueConstraint('relation_id', 'reference_id'),
        {'schema': 'nex'}
    )

    locusrelation_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    relation_id = Column(ForeignKey('nex.locus_relation.relation_id', ondelete='CASCADE'), nullable=False)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    reference = relationship('Referencedbentity')
    source = relationship('Source')
    relation = relationship('LocusRelation')

    def to_dict(self):
        ref = self.reference
        return {
            'display_name': ref.display_name,
            'format_name': ref.format_name,
            'link': ref.obj_url,
            'pubmed_id': ref.pmid,
            'year': ref.year,
            'id': ref.dbentity_id
        }

class Obi(Base):
    __tablename__ = 'obi'
    __table_args__ = {'schema': 'nex'}

    obi_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    obiid = Column(String(20), nullable=False, unique=True)
    description = Column(String(2000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    is_obsolete = Column(Boolean, nullable=False)

    source = relationship('Source')


class ObiRelation(Base):
    __tablename__ = 'obi_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.obi.obi_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.obi.obi_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Obi', primaryjoin='ObiRelation.child_id == Obi.obi_id')
    parent = relationship('Obi', primaryjoin='ObiRelation.parent_id == Obi.obi_id')
    ro = relationship('Ro')
    source = relationship('Source')


class ObiUrl(Base):
    __tablename__ = 'obi_url'
    __table_args__ = (
        UniqueConstraint('obi_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    obi_id = Column(ForeignKey('nex.obi.obi_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    obi = relationship('Obi')
    source = relationship('Source')


class PathwayAlias(Base):
    __tablename__ = 'pathway_alias'
    __table_args__ = (
        UniqueConstraint('pathway_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    pathway_id = Column(ForeignKey('nex.pathwaydbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    pathway = relationship('Pathwaydbentity')
    source = relationship('Source')


class PathwayUrl(Base):
    __tablename__ = 'pathway_url'
    __table_args__ = (
        UniqueConstraint('pathway_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    pathway_id = Column(ForeignKey('nex.pathwaydbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    pathway = relationship('Pathwaydbentity')
    source = relationship('Source')


class Pathwayannotation(Base):
    __tablename__ = 'pathwayannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'pathway_id', 'reference_id', 'ec_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    pathway_id = Column(ForeignKey('nex.pathwaydbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    ec_id = Column(ForeignKey('nex.ec.ec_id', ondelete='CASCADE'), index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity')
    ec = relationship('Ec')
    pathway = relationship('Pathwaydbentity', foreign_keys=[pathway_id])
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict(self):
        row = DBSession.query(PathwayUrl).filter(and_(PathwayUrl.pathway_id == self.pathway_id, PathwayUrl.url_type == 'YeastPathways')).one_or_none()
        url = row.obj_url if row else ''
        row = DBSession.query(Dbentity).filter_by(dbentity_id=self.pathway.dbentity_id).one_or_none()
        display_name = row.display_name if row else ''
        return {
            'pathway': {
		'display_name': display_name,
                'link': url
            }
        }

class Pathwaysummary(Base):
    __tablename__ = 'pathwaysummary'
    __table_args__ = (
        UniqueConstraint('pathway_id', 'summary_type'),
        {'schema': 'nex'}
    )

    summary_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.summary_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    pathway_id = Column(ForeignKey('nex.pathwaydbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    summary_type = Column(String(40), nullable=False)
    text = Column(Text, nullable=False)
    html = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=FetchedValue())
    created_by = Column(String(12), nullable=False)

    pathway = relationship('Pathwaydbentity')
    source = relationship('Source')


class PathwaysummaryReference(Base):
    __tablename__ = 'pathwaysummary_reference'
    __table_args__ = (
        UniqueConstraint('summary_id', 'reference_id'),
        {'schema': 'nex'}
    )

    summary_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    summary_id = Column(ForeignKey('nex.pathwaysummary.summary_id', ondelete='CASCADE'), nullable=False)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_order = Column(BigInteger, nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    reference = relationship('Referencedbentity')
    source = relationship('Source')
    summary = relationship('Pathwaysummary')


class Phenotype(Base):
    __tablename__ = 'phenotype'
    __table_args__ = {'schema': 'nex'}

    phenotype_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    observable_id = Column(ForeignKey('nex.apo.apo_id', ondelete='CASCADE'), nullable=False, index=True)
    qualifier_id = Column(ForeignKey('nex.apo.apo_id', ondelete='CASCADE'), index=True)
    description = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    observable = relationship('Apo', primaryjoin='Phenotype.observable_id == Apo.apo_id')
    qualifier = relationship('Apo', primaryjoin='Phenotype.qualifier_id == Apo.apo_id')
    source = relationship('Source')

    def to_main_dict(self):
        return { c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs }

    def to_dict(self):
        obj = {
            "id": self.phenotype_id,
            "display_name": self.display_name,
            "observable": {
                "display_name": self.observable.display_name,
                "link": self.observable.obj_url
            },

            "overview": Phenotypeannotation.create_count_overview([self.phenotype_id])
        }

        if self.qualifier:
            obj["qualifier"] = self.qualifier.display_name
        else:
            obj["qualifier"] = "None"

        return obj


    def annotations_to_dict(self):
        phenotype_annotations = DBSession.query(Phenotypeannotation).filter_by(phenotype_id=self.phenotype_id).all()
        temp = [p.annotation_id for p in phenotype_annotations]
        pheno_ids = clear_list_empty_values(temp)
        conditions = DBSession.query(PhenotypeannotationCond).filter(PhenotypeannotationCond.annotation_id.in_(pheno_ids)).all()
        condition_names = clear_list_empty_values(list(set([c.condition_name for c in conditions])))

        conditions_dict = {}
        for condition in conditions:
            if condition.annotation_id in conditions_dict:
                conditions_dict[condition.annotation_id].append(condition)
            else:
                conditions_dict[condition.annotation_id] = [condition]
        if len(condition_names) > 0:
            urls = DBSession.query(Chebi.display_name, Chebi.obj_url).filter(Chebi.display_name.in_(condition_names)).all()
        else:
            urls = []
        chebi_urls = {}
        for url in urls:
            chebi_urls[url[0]] = url[1]

        obj = []
        for annotation in phenotype_annotations:
            obj += annotation.to_dict(phenotype=self, conditions=conditions_dict.get(annotation.annotation_id, []), chebi_urls=chebi_urls)
        return obj

    def get_base_url(self):
        return '/phenotype/' + self.format_name

    def can_skip_cache(self):
        annotation_count = annotations = DBSession.query(Phenotypeannotation).filter_by(phenotype_id=self.phenotype_id).count()
        return annotation_count < 100

    def get_secondary_cache_urls(self, is_quick=False):
        url1 = self.get_secondary_base_url() + '/locus_details'
        return [url1]

    def get_secondary_base_url(self):
        return '/webservice/phenotype/' + str(self.phenotype_id)

class Phenotypeannotation(Base):
    __tablename__ = 'phenotypeannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'phenotype_id', 'experiment_id', 'mutant_id', 'reference_id', 'taxonomy_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    phenotype_id = Column(ForeignKey('nex.phenotype.phenotype_id', ondelete='CASCADE'), nullable=False, index=True)
    experiment_id = Column(ForeignKey('nex.apo.apo_id', ondelete='CASCADE'), nullable=False, index=True)
    mutant_id = Column(ForeignKey('nex.apo.apo_id', ondelete='CASCADE'), nullable=False, index=True)
    allele_id = Column(ForeignKey('nex.alleledbentity.dbentity_id', ondelete='CASCADE'), index=True)
    reporter_id = Column(ForeignKey('nex.reporter.reporter_id', ondelete='CASCADE'), index=True)
    assay_id = Column(ForeignKey('nex.obi.obi_id', ondelete='CASCADE'), index=True)
    strain_name = Column(String(100))
    details = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    experiment_comment = Column(String(200))
    allele_comment = Column(String(200))
    reporter_comment = Column(String(200))

    allele = relationship('Alleledbentity', foreign_keys=[allele_id])
    assay = relationship('Obi')
    dbentity = relationship('Dbentity')
    experiment = relationship('Apo', primaryjoin='Phenotypeannotation.experiment_id == Apo.apo_id')
    mutant = relationship('Apo', primaryjoin='Phenotypeannotation.mutant_id == Apo.apo_id')
    phenotype = relationship('Phenotype')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    reporter = relationship('Reporter')
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_main_dict(self):
        return {
            c.key: getattr(self, c.key)
            for c in inspect(self).mapper.column_attrs
        }

    @staticmethod
    def count_strains(phenotype_ids=None, annotations=None):
        strains_result = []

        if annotations is None:
            annotations = DBSession.query(Phenotypeannotation.taxonomy_id, Phenotypeannotation.annotation_id).filter(Phenotypeannotation.phenotype_id.in_(phenotype_ids)).all()

        annotation_ids = [a.annotation_id for a in annotations]

        number_conditions_tuples = DBSession.query(PhenotypeannotationCond.annotation_id, func.count(distinct(PhenotypeannotationCond.group_id))).filter(PhenotypeannotationCond.annotation_id.in_(annotation_ids)).group_by(PhenotypeannotationCond.annotation_id).all()

        number_conditions = {}
        for t in number_conditions_tuples:
            number_conditions[t[0]] = t[1]

        counts_dict = {}
        for annotation in annotations:
            add = 1

            if number_conditions.get(annotation.annotation_id, 0) > 1:
                add = number_conditions.get(annotation.annotation_id, 0)

            if annotation.taxonomy_id in counts_dict:
                counts_dict[annotation.taxonomy_id] += add
            else:
                counts_dict[annotation.taxonomy_id] = add

        counts = []
        for taxonomy in counts_dict:
            counts.append((taxonomy, counts_dict[taxonomy]))

        for count in counts:
            strains = Straindbentity.get_strains_by_taxon_id(count[0])

            if len(strains) > 1:
                strains_result.append(["Other", count[1]])
            elif len(strains) == 1:
                strains_result.append([strains[0].display_name, count[1]])
            else:
                continue

        return sorted(strains_result, key=lambda strain: (-1 * strain[1], strain[0]))

    @staticmethod
    def count_experiment_categories(phenotype_ids=None, annotations=None):
        if annotations is None:
            annotations = DBSession.query(Phenotypeannotation).filter(Phenotypeannotation.phenotype_id.in_(phenotype_ids)).all()

        annotation_ids = [a.annotation_id for a in annotations]

        number_conditions_tuples = DBSession.query(PhenotypeannotationCond.annotation_id, func.count(distinct(PhenotypeannotationCond.group_id))).filter(PhenotypeannotationCond.annotation_id.in_(annotation_ids)).group_by(PhenotypeannotationCond.annotation_id).all()

        number_conditions = {}
        for t in number_conditions_tuples:
            number_conditions[t[0]] = t[1]

        mt = {}
        for annotation in annotations:
            if annotation.mutant.display_name not in mt:
                mt[annotation.mutant.display_name] = {
                    "classical genetics": 0,
                    "large-scale survey": 0
                }

            add = 1

            if number_conditions.get(annotation.annotation_id, 0) > 1:
                add = number_conditions.get(annotation.annotation_id, 0)

            if annotation.experiment.namespace_group:
                mt[annotation.mutant.display_name][annotation.experiment.namespace_group] += add

        experiment_categories = []
        for key in list(mt.keys()):
            experiment_categories.append([key, mt[key]["classical genetics"], mt[key]["large-scale survey"]])

        return sorted(experiment_categories, key=lambda k: k[1] + k[2], reverse=True)

    # method for graphs counting annotations
    @staticmethod
    def create_count_overview(phenotype_ids, phenotype_annotations=None):
        if phenotype_annotations is None:
            return {
                "strains": [["Strain", "Annotations"]] + Phenotypeannotation.count_strains(phenotype_ids=phenotype_ids),
                "experiment_categories": [["Mutant Type", "classical genetics", "large-scale survey"]] +  Phenotypeannotation.count_experiment_categories(phenotype_ids=phenotype_ids)
            }
        else:
            return {
                "strains": [["Strain", "Annotations"]] + Phenotypeannotation.count_strains(annotations=phenotype_annotations),
                "experiment_categories": [["Mutant Type", "classical genetics", "large-scale survey"]] +  Phenotypeannotation.count_experiment_categories(annotations=phenotype_annotations)
            }

    def to_dict_lsp(self):
        if self.experiment.namespace_group == "classical genetics":
            experiment_category = "classical_phenotypes"
        else:
            experiment_category = "large_scale_phenotypes"

        return {
            "experiment_category": experiment_category,
            "mutant": self.mutant.display_name,
            "phenotype": {
                "display_name": self.phenotype.display_name,
                "link": self.phenotype.obj_url,
                "id": self.phenotype.phenotype_id
            }
        }

    def to_dict(self, reference=None, chemical=None, phenotype=None, locus=None, conditions=None, chebi_urls=None):
        if reference == None:
            reference = self.reference

        if locus == None:
            locus = self.dbentity

        if phenotype == None:
            phenotype = self.phenotype

        properties = []

        if self.reporter:
            properties.append({
                "class_type": "BIOITEM",
                "bioitem": {
                    "display_name": self.reporter.display_name
                },
                "note": self.reporter_comment,
                "role": "Reporter"
            })

        if self.allele:
            properties.append({
                "class_type": "BIOITEM",
                "bioitem": {
                    "display_name": self.allele.display_name
                },
                "note": self.allele_comment,
                "role": "Allele"
            })

        strain = Straindbentity.get_strains_by_taxon_id(self.taxonomy_id)

        strain_obj = None

        if len(strain) == 0 or len(strain) > 1:
            strain_obj = {
                "display_name": "Other",
                "link": "/strain/S000203479"
            }
        else:
            strain_obj = {
                "display_name": strain[0].display_name,
                "link": strain[0].obj_url
            }

        note = None
        if self.details and len(self.details) > 0:
            note = self.details

        experiment = Apo.get_apo_by_id(self.experiment_id)
        mutant = Apo.get_apo_by_id(self.mutant_id)

        experiment_obj = None

        if experiment:
            experiment_obj = {
                "display_name": experiment.display_name,
                "link": None, # self.experiment.obj_url -> no page yet
                "category": experiment.namespace_group,
                "note": self.experiment_comment
            }

        obj = {
            "id": self.annotation_id,
            "mutant_type": mutant.display_name,
            "locus": {
                "display_name": locus.display_name,
                "id": locus.dbentity_id,
                "link": locus.obj_url,
                "format_name": locus.format_name
            },
            "experiment": experiment_obj,
            "experiment_details": self.experiment_comment,
            "strain": strain_obj,
            "properties": properties,
            "note": note,
            "phenotype": {
                "display_name": self.phenotype.display_name,
                "link": self.phenotype.obj_url,
                "id": self.phenotype.phenotype_id
            },
            "reference": {
                "display_name": reference.display_name,
                "link": reference.obj_url,
                "pubmed_id": reference.pmid
            }
        }

        if conditions == None:
            conditions = DBSession.query(PhenotypeannotationCond).filter_by(
                annotation_id=self.annotation_id).order_by(
                    PhenotypeannotationCond.group_id).all()

        if len(conditions) == 0:
            return [obj]

        # groups = {}                                                                                         
        final_obj = []
        pre_group_id = None
        obj_with_cond = None
        for condition_item in conditions:
            if condition_item.condition_class == "chemical":    
                if chemical is not None and (chemical.display_name == condition_item.condition_name):
                    chebi_url = chemical.obj_url
                else:
                    if chebi_urls == None:
                        chemical = DBSession.query(Chebi).filter_by(display_name=condition_item.condition_name, is_obsolete=False).one_or_none()
                        if chemical:
                            chebi_url = chemical.obj_url
                        else:
                            chebi_url = None
                    else:
                        chebi_url = chebi_urls.get(
                            condition_item.condition_name)

                link = None
                if chebi_url:
                    link = chebi_url

                # if condition_item.group_id not in groups:
                #    groups[condition_item.group_id] = []

                # groups[condition_item.group_id].append({
                #    "class_type": "CHEMICAL",
                #    "concentration": condition_item.condition_value,
                #    "bioitem": {
                #        "link": link,
                #        "display_name": condition_item.condition_name
                #    },
                #    "note": None,
                #    "role": "CHEMICAL",
                #    "unit": condition_item.condition_unit
                # })
                group = {                                                     
                    "class_type": "CHEMICAL",
                    "concentration": condition_item.condition_value,
                    "bioitem": {
                        "link": link,
                        "display_name": condition_item.condition_name
                    },
                    "note": None,
                    "role": "CHEMICAL",
                    "unit": condition_item.condition_unit
                }
                if pre_group_id is None:
                    obj_with_cond = copy.deepcopy(obj)
                elif pre_group_id != condition_item.group_id:
                    final_obj.append(obj_with_cond)
                    obj_with_cond = copy.deepcopy(obj)
                obj_with_cond["properties"].append(group)                                                      
            else:
                note = condition_item.condition_name
                if condition_item.condition_value:
                    note += ", " + condition_item.condition_value
                    if condition_item.condition_unit:
                        note += " " + condition_item.condition_unit

                # if condition_item.group_id not in groups:
                #    groups[condition_item.group_id] = []

                # groups[condition_item.group_id].append({
                #    "class_type": condition_item.condition_class,
                #    "note": note,
                #    "unit": condition_item.condition_unit
                # })
                group = {
                    "class_type": condition_item.condition_class,
                    "note": note,
                    "unit": condition_item.condition_unit
                }
                if pre_group_id	is None:
                    obj_with_cond = copy.deepcopy(obj)
                elif pre_group_id != condition_item.group_id:
                    final_obj.append(obj_with_cond)
                    obj_with_cond = copy.deepcopy(obj)
                obj_with_cond["properties"].append(group)
            pre_group_id = condition_item.group_id
        if obj_with_cond:
            final_obj.append(obj_with_cond)
            
        # if chemical:
        #    groups_to_delete = []
        #    for group_id in groups:
        #        chemical_present_in_group = False
        #        for condition in groups[group_id]:
        #            if condition["class_type"] == "CHEMICAL" and condition["bioitem"]["display_name"] == chemical.display_name:
        #                chemical_present_in_group = True
        #        if not chemical_present_in_group:
        #            groups_to_delete.append(group_id)

        #    for group_id in groups_to_delete:
        #        del groups[group_id]

        # final_obj = []
        # for group_id in groups:
        #    obj_group = copy.deepcopy(obj)
        #    obj_group["properties"] += groups[group_id]
        #    final_obj.append(obj_group)
          
        # if len(final_obj) == 0:
        #    final_obj = [obj]

        return final_obj


class PhenotypeannotationCond(Base):
    __tablename__ = 'phenotypeannotation_cond'
    __table_args__ = (
        UniqueConstraint('annotation_id', 'condition_class', 'condition_name', 'condition_value'),
        {'schema': 'nex'}
    )

    condition_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.condition_seq'::regclass)"))
    annotation_id = Column(ForeignKey('nex.phenotypeannotation.annotation_id', ondelete='CASCADE'), nullable=False)
    condition_class = Column(String(40), nullable=False)
    condition_name = Column(String(500), nullable=False)
    condition_value = Column(String(150))
    condition_unit = Column(String(25))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    group_id = Column(Integer, nullable=False)

    annotation = relationship('Phenotypeannotation')


class Physinteractionannotation(Base):
    __tablename__ = 'physinteractionannotation'
    __table_args__ = (
        UniqueConstraint('dbentity1_id', 'dbentity2_id', 'bait_hit', 'biogrid_experimental_system', 'reference_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity1_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    dbentity2_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    psimod_id = Column(ForeignKey('nex.psimod.psimod_id', ondelete='CASCADE'), index=True)
    biogrid_experimental_system = Column(String(100), nullable=False)
    annotation_type = Column(String(20), nullable=False)
    bait_hit = Column(String(10), nullable=False)
    description = Column(String(1000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity1 = relationship('Dbentity', primaryjoin='Physinteractionannotation.dbentity1_id == Dbentity.dbentity_id')
    dbentity2 = relationship('Dbentity', primaryjoin='Physinteractionannotation.dbentity2_id == Dbentity.dbentity_id')
    psimod = relationship('Psimod')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict(self, reference=None):
        dbentity1 = self.dbentity1
        dbentity2 = self.dbentity2

        if reference is None:
            reference = self.reference

        modification = "No Modification"
        if self.psimod:
            modification = self.psimod.display_name

        return {
            "id": self.annotation_id,
            "note": self.description,
            "bait_hit": self.bait_hit,
            "locus1": {
                "id": self.dbentity1_id,
                "display_name": dbentity1.display_name,
                "link": dbentity1.obj_url,
                "format_name": dbentity1.format_name
            },
            "locus2": {
                "id": self.dbentity2_id,
                "display_name": dbentity2.display_name,
                "link": dbentity2.obj_url,
                "format_name": dbentity2.format_name
            },
            "experiment": {
                "display_name": self.biogrid_experimental_system,
                "link": None
            },
            "phenotype": None, # None for physical interactions
            "mutant_type": None, # None for physical interactions
            "modification": modification,
            "interaction_type": "Physical",
            "annotation_type": self.annotation_type,
            "source": {
                "display_name": self.source.display_name
            },
            "reference": {
                "display_name": reference.display_name,
                "pubmed_id": reference.pmid,
                "link": reference.obj_url
            }
        }


class Posttranslationannotation(Base):
    __tablename__ = 'posttranslationannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'psimod_id', 'site_residue', 'site_index', 'reference_id', 'modifier_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    site_index = Column(Integer, nullable=False)
    site_residue = Column(String(1), nullable=False)
    psimod_id = Column(ForeignKey('nex.psimod.psimod_id', ondelete='CASCADE'), nullable=False, index=True)
    modifier_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity', primaryjoin='Posttranslationannotation.dbentity_id == Dbentity.dbentity_id')
    modifier = relationship('Dbentity', primaryjoin='Posttranslationannotation.modifier_id == Dbentity.dbentity_id')
    psimod = relationship('Psimod')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict(self, locus=None, references=None):
        if references:
            reference = references[self.reference_id]
        else:
            reference = self.reference

        if locus is None:
            locus = self.dbentity

        properties = []
        if self.modifier:
            properties.append({
                "bioentity": {
                    "display_name": self.modifier.display_name,
                    "link": self.modifier.obj_url
                },
                "role": "Kinase",
                "note": None
            })

        return {
            "site_index": self.site_index,
            "site_residue": self.site_residue,
            "locus": {
                "id": self.dbentity_id,
                "display_name": locus.display_name,
                "format_name": locus.format_name,
                "link": locus.obj_url
            },
            "reference": {
                "display_name": reference.display_name,
                "link": reference.obj_url,
                "pubmed_id": reference.pmid
            },
            "properties": properties,
            "source": {
                "display_name": self.source.display_name
            },
            "aliases": [],
            "type": self.psimod.display_name,
            "id": self.annotation_id
        }

class Proteindomain(Base):
    __tablename__ = 'proteindomain'
    __table_args__ = {'schema': 'nex'}

    proteindomain_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    interpro_id = Column(String(20))
    description = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')

    def to_dict(self):
        urls = DBSession.query(ProteindomainUrl).filter_by(proteindomain_id=self.proteindomain_id).all()

        obj = {
            "id": self.proteindomain_id,
            "link": self.obj_url,
            "display_name": self.display_name,
            "urls": [u.to_dict() for u in urls],
            "source": {
                "display_name": self.source.display_name
            },
            "description": None
        }

        if self.description and len(self.description) > 0:
            obj["description"] = self.description
        else:
            obj["description"] = 'family not named'

        return obj

    def locus_details(self):
        annotations = DBSession.query(Proteindomainannotation).filter_by(proteindomain_id=self.proteindomain_id).all()
        return [a.to_dict(proteindomain=self) for a in annotations]

    def enrichment(self):
        dbentity_ids = []
        for x in DBSession.query(Proteindomainannotation).distinct(Proteindomainannotation.dbentity_id).filter_by(proteindomain_id=self.proteindomain_id).all():
            dbentity_ids.append(x.dbentity_id)

        format_names = DBSession.query(Dbentity.format_name).filter(Dbentity.dbentity_id.in_(dbentity_ids)).all()

        data = urllib.parse.urlencode({
            "genes": ",".join([f[0] for f in format_names]),
            "aspect": "P"
        })

        try:
            req = Request(url=os.environ['BATTER_URI'], data=data.encode('utf-8'))
            res = urlopen(req)
            response_json = json.loads(res.read().decode('utf-8'))
        except:
            return []

        obj = []
        for row in response_json:
            obj.append({
                "go": {
                    "display_name": row["term"],
                    "link": '/go/' + row["goid"],
                    "id": row["goid"]
                },
                "match_count": row["num_gene_annotated"],
                "pvalue": row["pvalue"]
            })
        return obj


class ProteindomainUrl(Base):
    __tablename__ = 'proteindomain_url'
    __table_args__ = (
        UniqueConstraint('proteindomain_id', 'display_name', 'url_type'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    proteindomain_id = Column(ForeignKey('nex.proteindomain.proteindomain_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    proteindomain = relationship('Proteindomain')
    source = relationship('Source')

    def to_dict(self):
        return {
            "link": self.obj_url,
            "display_name": self.display_name
        }


class Proteindomainannotation(Base):
    __tablename__ = 'proteindomainannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'proteindomain_id', 'start_index', 'end_index'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    proteindomain_id = Column(ForeignKey('nex.proteindomain.proteindomain_id', ondelete='CASCADE'), nullable=False, index=True)
    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)
    date_of_run = Column(DateTime, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity')
    proteindomain = relationship('Proteindomain')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict(self, locus=None, proteindomain=None):
        if locus is None:
            locus = self.dbentity

        if proteindomain is None:
            proteindomain = self.proteindomain

        count = DBSession.query(Proteindomainannotation).distinct(Proteindomainannotation.dbentity_id).filter_by(proteindomain_id=self.proteindomain_id).count()

        return {
            "id": self.annotation_id,
            "domain": {
                "id": proteindomain.proteindomain_id,
                "link": proteindomain.obj_url,
                "display_name": proteindomain.display_name,
                "count": count,
                "description": proteindomain.description
            },
            "start": self.start_index,
            "end": self.end_index,
            "locus": {
                "id": self.dbentity_id,
                "display_name": locus.display_name,
                "format_name": locus.format_name,
                "link": locus.obj_url
            },
            "source": {
                "id": proteindomain.source_id,
                "format_name": proteindomain.source.format_name,
                "display_name": proteindomain.source.display_name
            }
        }


class Proteinexptannotation(Base):
    __tablename__ = 'proteinexptannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'reference_id', 'experiment_type'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    experiment_type = Column(String(40), nullable=False)
    data_value = Column(String(25), nullable=False)
    data_unit = Column(String(25), nullable=False)
    assay_id = Column(ForeignKey('nex.obi.obi_id', ondelete='CASCADE'), index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    assay = relationship('Obi')
    dbentity = relationship('Dbentity')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict(self, locus=None, references=None):
        if references:
            reference = references[self.reference_id]
        else:
            reference = self.reference

        if locus is None:
            locus = self.dbentity

        return {
            "id": self.annotation_id,
            "experiment": {
                "display_name": self.experiment_type,
                "link": None
            },
            "reference": {
                "display_name": reference.display_name,
                "link": reference.obj_url
            },
            "locus": {
                "id": self.dbentity_id,
                "display_name": locus.display_name,
                "format_name": locus.format_name,
                "link": locus.obj_url
            },
            "data_value": self.data_value,
            "data_unit": self.data_unit
        }


class ProteinexptannotationCond(Base):
    __tablename__ = 'proteinexptannotation_cond'
    __table_args__ = (
        UniqueConstraint('annotation_id', 'condition_class', 'condition_name', 'condition_value'),
        {'schema': 'nex'}
    )

    condition_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.condition_seq'::regclass)"))
    annotation_id = Column(ForeignKey('nex.proteinexptannotation.annotation_id', ondelete='CASCADE'), nullable=False)
    condition_class = Column(String(40), nullable=False)
    condition_name = Column(String(500), nullable=False)
    condition_value = Column(String(25))
    condition_unit = Column(String(25))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    annotation = relationship('Proteinexptannotation')


class ProteinsequenceDetail(Base):
    __tablename__ = 'proteinsequence_detail'
    __table_args__ = {'schema': 'nex'}

    detail_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.detail_seq'::regclass)"))
    annotation_id = Column(ForeignKey('nex.proteinsequenceannotation.annotation_id', ondelete='CASCADE'), nullable=False, unique=True)
    molecular_weight = Column(Numeric, nullable=False)
    protein_length = Column(BigInteger, nullable=False)
    n_term_seq = Column(String(10), nullable=False)
    c_term_seq = Column(String(10), nullable=False)
    pi = Column(Numeric)
    cai = Column(Numeric)
    codon_bias = Column(Numeric)
    fop_score = Column(Numeric)
    gravy_score = Column(Numeric)
    aromaticity_score = Column(Numeric)
    aliphatic_index = Column(Numeric)
    instability_index = Column(Numeric)
    ala = Column(Integer, nullable=False)
    arg = Column(Integer, nullable=False)
    asn = Column(Integer, nullable=False)
    asp = Column(Integer, nullable=False)
    cys = Column(Integer, nullable=False)
    gln = Column(Integer, nullable=False)
    glu = Column(Integer, nullable=False)
    gly = Column(Integer, nullable=False)
    his = Column(Integer, nullable=False)
    ile = Column(Integer, nullable=False)
    leu = Column(Integer, nullable=False)
    lys = Column(Integer, nullable=False)
    met = Column(Integer, nullable=False)
    phe = Column(Integer, nullable=False)
    pro = Column(Integer, nullable=False)
    ser = Column(Integer, nullable=False)
    thr = Column(Integer, nullable=False)
    trp = Column(Integer, nullable=False)
    tyr = Column(Integer, nullable=False)
    val = Column(Integer, nullable=False)
    hydrogen = Column(Integer)
    sulfur = Column(Integer)
    nitrogen = Column(Integer)
    oxygen = Column(Integer)
    carbon = Column(Integer)
    no_cys_ext_coeff = Column(Integer)
    all_cys_ext_coeff = Column(Integer)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    annotation = relationship('Proteinsequenceannotation', uselist=False)

    def float_safe(self, attrname):
        val = getattr(self, attrname)
        return float(val) if val else None

    def to_dict_lsp(self):
        return {
            "length": int(self.protein_length),
            "molecular_weight": float(self.molecular_weight),
            "pi": self.float_safe('pi')
        }

    def to_dict(self): # I followed the NEX endpoint to convert floats to strings
        return {
            "molecular_weight": str(float(self.molecular_weight)),
            "protein_length": self.protein_length,
            "n_term_seq": self.n_term_seq,
            "c_term_seq": self.c_term_seq,
            "pi": str(self.float_safe('pi')),
            "cai": str(self.float_safe('cai')),
            "codon_bias": str(self.float_safe('codon_bias')),
            "fop_score": str(self.float_safe('fop_score')),
            "gravy_score": str(self.float_safe('gravy_score')),
            "aromaticity_score": str(self.float_safe('aromaticity_score')),
            "aliphatic_index": str(self.float_safe('aliphatic_index')),
            "instability_index": str(self.float_safe('instability_index')),
            "ala": self.ala,
            "arg": self.arg,
            "asn": self.asn,
            "asp": self.asp,
            "cys": self.cys,
            "gln": self.gln,
            "glu": self.glu,
            "gly": self.gly,
            "his": self.his,
            "ile": self.ile,
            "leu": self.leu,
            "lys": self.lys,
            "met": self.met,
            "phe": self.phe,
            "pro": self.pro,
            "ser": self.ser,
            "thr": self.thr,
            "trp": self.trp,
            "tyr": self.tyr,
            "val": self.val,
            "hydrogen": self.hydrogen,
            "sulfur": self.sulfur,
            "nitrogen": self.nitrogen,
            "oxygen": self.oxygen,
            "carbon": self.carbon,
            "no_cys_ext_coeff": str(self.float_safe('no_cys_ext_coeff')),
            "all_cys_ext_coeff": str(self.float_safe('all_cys_ext_coeff'))
        }

class Proteinsequenceannotation(Base):
    __tablename__ = 'proteinsequenceannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'taxonomy_id', 'contig_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    bud_id = Column(Integer)
    contig_id = Column(ForeignKey('nex.contig.contig_id', ondelete='CASCADE'), nullable=False, index=True)
    seq_version = Column(DateTime)
    genomerelease_id = Column(ForeignKey('nex.genomerelease.genomerelease_id', ondelete='CASCADE'), index=True)
    file_header = Column(String(200), nullable=False)
    download_filename = Column(String(100), nullable=False)
    file_id = Column(BigInteger)
    residues = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    contig = relationship('Contig')
    dbentity = relationship('Dbentity')
    genomerelease = relationship('Genomerelease')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict(self, locus=None):
        if locus is None:
            locus = DBSession.query(Locusdbentity).filter_by(dbentity_id=self.dbentity_id).one_or_none()

        strains = Straindbentity.get_strains_by_taxon_id(self.contig.taxonomy_id)

        if len(strains) == 0:
            return None

        details = DBSession.query(ProteinsequenceDetail).filter_by(annotation_id=self.annotation_id).one_or_none()
        if details:
            obj = details.to_dict()
        else:
            obj = {}

        obj["residues"] = self.residues
        obj["locus"] = locus.to_dict_sequence_widget()
        obj["strain"] = {
            "display_name": strains[0].display_name,
            "status": strains[0].strain_type,
            "format_name": strains[0].format_name,
            "description": strains[0].headline
        }

        return obj


class Psimod(Base):
    __tablename__ = 'psimod'
    __table_args__ = {'schema': 'nex'}

    psimod_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    psimodid = Column(String(20), nullable=False, unique=True)
    description = Column(String(2000))
    is_obsolete = Column(Boolean, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)


    source = relationship('Source')


class PsimodRelation(Base):
    __tablename__ = 'psimod_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.psimod.psimod_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.psimod.psimod_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Psimod', primaryjoin='PsimodRelation.child_id == Psimod.psimod_id')
    parent = relationship('Psimod', primaryjoin='PsimodRelation.parent_id == Psimod.psimod_id')
    ro = relationship('Ro')
    source = relationship('Source')


class PsimodUrl(Base):
    __tablename__ = 'psimod_url'
    __table_args__ = (
        UniqueConstraint('psimod_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    psimod_id = Column(ForeignKey('nex.psimod.psimod_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    psimod = relationship('Psimod')
    source = relationship('Source')


class Psimi(Base):
    __tablename__ = 'psimi'
    __table_args__ = {'schema': 'nex'}

    psimi_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    psimiid = Column(String(20), nullable=False, unique=True)
    description = Column(String(2000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    is_obsolete = Column(Boolean, nullable=False)

    source = relationship('Source')


class PsimiRelation(Base):
    __tablename__ = 'psimi_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.psimi.psimi_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.psimi.psimi_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Psimi', primaryjoin='PsimiRelation.child_id == Psimi.psimi_id')
    parent = relationship('Psimi', primaryjoin='PsimiRelation.parent_id == Psimi.psimi_id')
    ro = relationship('Ro')
    source = relationship('Source')


class PsimiUrl(Base):
    __tablename__ = 'psimi_url'
    __table_args__ = (
        UniqueConstraint('psimi_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    psimi_id = Column(ForeignKey('nex.psimi.psimi_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    psimi = relationship('Psimi')
    source = relationship('Source')


class PsimiAlias(Base):
    __tablename__ = 'psimi_alias'
    __table_args__ = (
        UniqueConstraint('alias_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False,index=True)
    psimi_id = Column(ForeignKey('nex.psimi.psimi_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    psimi = relationship('Psimi')
    source = relationship('Source')

class Efo(Base):
    __tablename__ = 'efo'
    __table_args__ = {'schema': 'nex'}

    efo_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    efoid = Column(String(20), nullable=False, unique=True)
    description = Column(String(2000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    is_obsolete = Column(Boolean, nullable=False)

    source = relationship('Source')


class EfoRelation(Base):
    __tablename__ = 'efo_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.efo.efo_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.efo.efo_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Efo', primaryjoin='EfoRelation.child_id == Efo.efo_id')
    parent = relationship('Efo', primaryjoin='EfoRelation.parent_id == Efo.efo_id')
    ro = relationship('Ro')
    source = relationship('Source')

class EfoUrl(Base):
    __tablename__ = 'efo_url'
    __table_args__ = (
        UniqueConstraint('efo_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    efo_id = Column(ForeignKey('nex.efo.efo_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    efo = relationship('Efo')
    source = relationship('Source')

class EfoAlias(Base):
    __tablename__ = 'efo_alias'
    __table_args__ = (
        UniqueConstraint('alias_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False,index=True)
    efo_id = Column(ForeignKey('nex.efo.efo_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    efo = relationship('Efo')
    source = relationship('Source')


class Proteinabundanceannotation(Base):
    __tablename__ = 'proteinabundanceannotation'
    __table_args__ = (
        UniqueConstraint('dbentity_id', 'original_reference_id', 'assay_id', 'media_id', 'taxonomy_id', 'chemical_id', 'process_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    original_reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    assay_id = Column(ForeignKey('nex.eco.eco_id', ondelete='CASCADE'), nullable=False, index=True)
    media_id = Column(ForeignKey('nex.efo.efo_id', ondelete='CASCADE'), nullable=False, index=True)
    data_value = Column(Integer)
    data_unit = Column(String)
    fold_change = Column(Float)
    chemical_id = Column(ForeignKey('nex.chebi.chebi_id', ondelete='CASCADE'), nullable=False, index=True)
    process_id = Column(ForeignKey('nex.go.go_id', ondelete='CASCADE'), nullable=False, index=True)
    concentration_value = Column(Float)
    concentration_unit = Column(String)
    time_value = Column(Integer)
    time_unit = Column(String)
    median_value = Column(Integer)
    median_abs_dev_value = Column(Integer)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    
    eco = relationship('Eco')
    efo = relationship('Efo')
    dbentity = relationship('Dbentity')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    original_reference = relationship('Referencedbentity', foreign_keys=[original_reference_id])
    chebi = relationship('Chebi')
    go = relationship('Go')
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')

    def to_dict(self, locus=None, chebi=None, references=None):

        if references:
            reference = references[self.reference_id]
            original_reference = references[self.original_reference_id]
        else:
            reference = self.reference
            original_reference = self.original_reference

        if locus is None:
            locus = self.dbentity
            
        if chebi is None:
            chebi = self.chebi
            
        process = ""
        chemical_name = ""
        p = '0'
        c = '0'
        if self.process_id:
            process = self.go.display_name
            p = '1'
        if self.chemical_id:
            chemical_name = chebi.display_name
            c = '1'
        order_by = original_reference.display_name + "_" + p + c + "_" + process + "_" + chemical_name 

        # strain = self.taxonomy.display_name.replace("Saccharomyces cerevisiae ", "").upper()
        # if strain == '':
        #    strain = "Other";

        strains = Straindbentity.get_strains_by_taxon_id(self.taxonomy_id)
        
        strain_name = None
        strain_link = None
        if len(strains) == 1:
            strain_name = strains[0].display_name
            strain_link = strains[0].obj_url
        else:
            for x in strains:
                if x.display_name == 'Other':
                    strain_name = x.display_name
                    strain_link = x.obj_url

        return {

            "id": self.annotation_id,
            "order_by": order_by,
            "reference": {
                "display_name": reference.display_name,
                "link": reference.obj_url
            },
            "original_reference": {
                "display_name": original_reference.display_name,
                "link": original_reference.obj_url
            },
            "locus": {
                "id": self.dbentity_id,
                "display_name": locus.display_name,
                "format_name": locus.format_name,
                "link": locus.obj_url
            },
            "media": {
                "display_name": self.efo.display_name
            },
            "treatment": {
                "chemical": chemical_name,
                "process": process,
                "time_value": self.time_value,
                "time_unit": self.time_unit,
                "conc_value": self.concentration_value,
                "conc_unit": self.concentration_unit,
            },
            "data_value": self.data_value,
            "data_unit": self.data_unit,
            "fold_change": self.fold_change,
            "visualization": {
                "display_name": self.eco.display_name
            },
            "strain": {
                "link": strain_link,
                "display_name": strain_name
            }
        }


class Tools(Base):
    __tablename__ = 'tools'
    __table_args__ = (
        UniqueConstraint('format_name'),
        {'schema': 'nex'}
    )

    tool_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    format_name = Column(String(200), nullable=False)
    display_name = Column(String(200), nullable=False)
    link_url = Column(String(200), nullable=False)
    index_key = Column(String(200), nullable=True)
    status = Column(String(200), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)


class Alleledbentity(Dbentity):
    __tablename__ = 'alleledbentity'
    __table_args__ = {'schema': 'nex'}
    __url_segment__ = '/allele/'

    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    so_id = Column(ForeignKey('nex.so.so_id', ondelete='CASCADE'), nullable=False, index=True)
    description = Column(String(500), nullable=True)

    so = relationship('So')
    
    def to_dict(self):

        reference_mapping = {}
        unique_references = []
        ref_order = 1
        obj = { "sgdid": self.sgdid }
        (obj["name"], ref_order) = self.get_basic_info(self.display_name, 'allele_name', reference_mapping, ref_order)
        (obj['aliases'], ref_order) = self.get_aliases(reference_mapping, ref_order)
        # obj['affected_gene'] = self.get_gene_name_info()
        obj['affected_gene'] = self.get_gene_name()  
        (obj['allele_type'], ref_order) = self.get_basic_info(self.so.display_name, 'so_term', reference_mapping, ref_order)
        (obj['description'], ref_order) = self.get_basic_info(self.description, 'allele_description', reference_mapping, ref_order)
        obj['phenotype'] = self.phenotype_to_dict()
        obj['interaction'] = self.interaction_to_dict()
        obj['network_graph'] = self.allele_network()
        obj['references'] = self.get_references()
        obj['phenotype_references'] = self.get_phenotype_references(unique_references)
        obj['interaction_references'] = self.get_interaction_references(unique_references)
        obj['primary_references'] = self.get_literatureannotation_references("Primary Literature", unique_references )
        obj['additional_references'] = self.get_literatureannotation_references("Additional Literature", unique_references)
        obj['review_references'] = self.get_literatureannotation_references("Reviews", unique_references)
        obj['urls'] = self.get_resource_urls()
        obj["reference_mapping"] = reference_mapping
        obj['unique_references'] = unique_references
        
        return obj

    def get_basic_info(self, display_text, reference_class, reference_mapping, ref_order):

        references = []
        alleleRefs = DBSession.query(AlleleReference).filter_by(allele_id=self.dbentity_id, reference_class=reference_class).all()
        for x in alleleRefs:
            reference = x.reference.to_dict_citation()
            references.append(reference)
            if reference["id"] not in reference_mapping:
                reference_mapping[reference["id"]] = ref_order
                ref_order = ref_order + 1

        return ({ "display_text": display_text,
                  "references": references }, ref_order)
    
    def get_resource_urls(self):
        
        gene_names = self.get_gene_name()
        gene_name = gene_names[0]
        
        locus = DBSession.query(Locusdbentity).filter(or_(Locusdbentity.gene_name == gene_name, Locusdbentity.systematic_name == gene_name)).one_or_none()
        if locus is None:
            return []

        obj = locus.to_dict()
        allUrls = obj['urls']
        urls = []
        for x in allUrls:
            if x['category'] in ['LOCUS_PHENOTYPE_RESOURCES_MUTANT_STRAINS', 'LOCUS_PHENOTYPE_RESOURCES_PHENOTYPE_RESOURCES', 'LOCUS_PHENOTYPE_RESOURCES_ONTOLOGY', 'LOCUS_INTERACTION']:
                urls.append(x)
        return urls

    def get_literatureannotation_references(self, topic, unique_references):
        reference_ids = set([])
        for x in DBSession.query(Literatureannotation).filter_by(dbentity_id=self.dbentity_id, topic=topic).all():
            if x.reference.dbentity_id not in unique_references:
                unique_references.append(x.reference.dbentity_id)
            # if x.reference.to_dict_citation() not in references:
            #    references.append(x.reference.to_dict_citation())
            reference_ids.add(x.reference_id)
        all_references = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(list(reference_ids))).all()
        all_references = sorted(sorted(all_references, key=lambda p: p.display_name), key=lambda p: p.year, reverse=True)
        references = []
        for x in all_references:
            if x.to_dict_citation() not in references:
                references.append(x.to_dict_citation())
        return references
        
    def get_phenotype_references(self, unique_references):
        reference_ids = set([])
        for x in DBSession.query(Phenotypeannotation).filter_by(allele_id=self.dbentity_id).all():
            if x.reference.dbentity_id not in unique_references:
                unique_references.append(x.reference.dbentity_id)
            # if x.reference.to_dict_citation() not in references:
            #    references.append(x.reference.to_dict_citation())
            reference_ids.add(x.reference_id)
        all_references = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(list(reference_ids))).all()
        all_references = sorted(sorted(all_references, key=lambda p: p.display_name), key=lambda p: p.year, reverse=True)
        references = []
        for x in all_references:
            if x.to_dict_citation() not in references:
                references.append(x.to_dict_citation())
        return references
                
    def get_interaction_references(self, unique_references):

        interaction_ids = []
        for x in DBSession.query(AlleleGeninteraction).distinct(AlleleGeninteraction.interaction_id).filter(or_(AlleleGeninteraction.allele1_id==self.dbentity_id, AlleleGeninteraction.allele2_id==self.dbentity_id)).all():
            interaction_ids.append(x.interaction_id)

        reference_ids = set([])
        for x in DBSession.query(Geninteractionannotation).filter(Geninteractionannotation.annotation_id.in_(interaction_ids)).all():
            if x.reference.dbentity_id not in unique_references:
                unique_references.append(x.reference.dbentity_id)
            # if x.reference.to_dict_citation() not in references:
            #    references.append(x.reference.to_dict_citation())
            reference_ids.add(x.reference_id)
        all_references = DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(list(reference_ids))).all()
        all_references = sorted(sorted(all_references, key=lambda p: p.display_name), key=lambda p: p.year, reverse=True)
        references = []
        for x in all_references:
            if x.to_dict_citation() not in references:
                references.append(x.to_dict_citation())
        return references
                    
    def get_references(self):

        references = []
        found = {}
        # allele_reference for allele_name
        alleleRefs = DBSession.query(AlleleReference).filter_by(allele_id=self.dbentity_id, reference_class='allele_name').all()
        for x in alleleRefs:
            if x.reference.dbentity_id in found:
                continue
            references.append(x.reference.to_dict_citation())
            found[x.reference.dbentity_id] = 1
            
        # allelealias_reference
        alleleAliases = DBSession.query(AlleleAlias).filter_by(allele_id=self.dbentity_id).all()
        for x in alleleAliases:
            allelealiasRefs = DBSession.query(AllelealiasReference).filter_by(allele_alias_id=x.allele_alias_id).all()
            for x in allelealiasRefs:
                if x.reference.dbentity_id not in found:
                    references.append(x.reference.to_dict_citation())
                    found[x.reference.dbentity_id] = 1

        # allele_reference for so term                                                                                                          
        alleleRefs = DBSession.query(AlleleReference).filter_by(allele_id=self.dbentity_id, reference_class='so_term').all()
        for x in alleleRefs:
            if x.reference.dbentity_id in found:
                continue
            references.append(x.reference.to_dict_citation())
            found[x.reference.dbentity_id] = 1
                 
        # allele_reference for allele_description
        if self.description:
            alleleRefs = DBSession.query(AlleleReference).filter_by(allele_id=self.dbentity_id, reference_class='allele_description').all()
            for x in alleleRefs:
                if x.reference.dbentity_id in found:
                    continue
                references.append(x.reference.to_dict_citation())
                found[x.reference.dbentity_id] = 1
                
        return references

    def interaction_to_dict(self):

        interaction_ids = []
        for x in DBSession.query(AlleleGeninteraction).distinct(AlleleGeninteraction.interaction_id).filter(or_(AlleleGeninteraction.allele1_id==self.dbentity_id, AlleleGeninteraction.allele2_id==self.dbentity_id)).all():
            interaction_ids.append(x.interaction_id)
        
        annotations = DBSession.query(Geninteractionannotation).filter(Geninteractionannotation.annotation_id.in_(interaction_ids)).all()
                    
        obj = []
        for annotation in annotations:
            obj.append(annotation.to_dict())

        return obj

    
    def phenotype_to_dict(self):
        
        annotations = DBSession.query(Phenotypeannotation).filter_by(allele_id=self.dbentity_id).all()
        
        obj = []
        for annotation in annotations:
            obj += annotation.to_dict()

        return obj


    def get_gene_name(self):

        names = []
        for x in DBSession.query(LocusAllele).filter_by(allele_id = self.dbentity_id).all():
            names.append(x.locus.display_name)
        return names
    
    def get_gene_name_info(self):

        data = []
        for x in DBSession.query(LocusAllele).filter_by(allele_id = self.dbentity_id).all():
            gene = x.locus.display_name
            references = []
            locusalleleRefs = DBSession.query(LocusalleleReference).filter_by(locus_allele_id=x.locus_allele_id).all()
            for y in locusalleleRefs:
                reference = y.reference.to_dict_citation()
                references.append(reference)
            data.append({ "display_name": gene,
                          "references": references })

        return data
    
    def get_aliases(self, reference_mapping, ref_order):

        alleleAliases = DBSession.query(AlleleAlias).filter_by(allele_id = self.dbentity_id, alias_type='Synonym').all()
        objs = []
        for x in alleleAliases:
            allelealiasRefs = DBSession.query(AllelealiasReference).filter_by(allele_alias_id=x.allele_alias_id).all()
            references = []
            for y in allelealiasRefs:
                reference = y.reference.to_dict_citation()
                references.append(reference)
                if reference["id"] not in reference_mapping:
                    reference_mapping[reference["id"]] = ref_order
                    ref_order += 1
            objs.append({ "display_name": x.display_name,
                          "references": references })
        return (objs, ref_order)

    
    def allele_network(self):

        network_nodes =[]
        network_edges =[]

        network_nodes_ids = {}
        network_edges_added = {}

        network_nodes.append({
            "name": self.display_name,
            "id": self.format_name,
            "href": "/allele/" + self.format_name,
            "category": "FOCUS",
        })
        network_nodes_ids[self.format_name] = True

        ## phenotype
                
        phenotype_annotations = DBSession.query(Phenotypeannotation).filter_by(allele_id=self.dbentity_id).all()
        allele_id_to_name = dict([(x.dbentity_id, x.display_name) for x in DBSession.query(Dbentity).filter_by(subclass='ALLELE').all()])

        allele_key_to_phenotype_list = {}
        
        for p in phenotype_annotations:
            if p.allele_id is None:
                continue

            ## one phenotype = combination of phenotype_id, experiment_id, mutant_id, taxonomy_id
            ## in order to show up in the diagram, other allele nodes have to share
            ## at least two phenotypes with the focus one

            pheno_id = "phenotype_" + str(p.phenotype_id) + "_"	+ str(p.experiment_id) + "_" + str(p.mutant_id) + "_" + str(p.taxonomy_id)

            other_annotations = DBSession.query(Phenotypeannotation).filter_by(phenotype_id=p.phenotype_id, experiment_id=p.experiment_id, mutant_id=p.mutant_id, taxonomy_id=p.taxonomy_id).all()
                
            for x in other_annotations:
                if x.allele_id is None:
                    continue
                if x.allele_id == self.dbentity_id:
                    continue
                allele_display_name = allele_id_to_name.get(x.allele_id)
                if allele_display_name is None:
                    continue
                allele_format_name = allele_display_name.replace(' ', '_')
                phenotype_list = []
                allele_key = (allele_display_name, allele_format_name, "/allele/" + allele_format_name)
                if allele_key in allele_key_to_phenotype_list:
                    phenotype_list = allele_key_to_phenotype_list[allele_key]
                phenotype_key = (p.phenotype.display_name, pheno_id, p.phenotype.obj_url)
                if phenotype_key not in phenotype_list:
                    phenotype_list.append(phenotype_key)
                    allele_key_to_phenotype_list[allele_key] = phenotype_list
                
        for key in allele_key_to_phenotype_list:
            phenotype_list = allele_key_to_phenotype_list[key]
            if len(phenotype_list) > 1:
                (allele_display_name, allele_format_name, allele_link) = key                
                if allele_format_name not in network_nodes_ids:
                    network_nodes.append({
                        "name": allele_display_name,
                        "id": allele_format_name,
                        "href": allele_link,
                        "category": "ALLELE",
                    })
                    network_nodes_ids[allele_format_name] = True
                for phenotype in phenotype_list:
                    (pheno_display_name, pheno_id, pheno_link) = phenotype
                    if pheno_id not in network_nodes_ids:
                        network_nodes.append({
                            "name": pheno_display_name,
                            "id": pheno_id,
                            "href": pheno_link,
                            "category": "PHENOTYPE",
                        })
                        network_nodes_ids[pheno_id] = True
                    if (self.format_name, pheno_id) not in network_edges_added:
                        network_edges.append({
                            "source": self.format_name,
                            "target": pheno_id
                        })
                        network_edges_added[(self.format_name, pheno_id)] = True
                    if (allele_format_name, pheno_id) not in network_edges_added:
                        network_edges.append({
                            "source": allele_format_name,
                            "target": pheno_id
                        })
                        network_edges_added[(allele_format_name, pheno_id)] = True
                                        
        ## interaction 

        allele_id_to_name = dict([(x.dbentity_id, x.display_name) for x in DBSession.query(Dbentity).filter_by(subclass='ALLELE').all()])

        curr_allele = self.display_name

        all_linked_allele_ids = []

        # network_nodes_ids = {}

        all_positives = DBSession.query(AlleleGeninteraction).filter(or_(AlleleGeninteraction.allele1_id==self.dbentity_id, AlleleGeninteraction.allele2_id==self.dbentity_id)).filter(AlleleGeninteraction.sga_score > 0).order_by(AlleleGeninteraction.sga_score.desc()).all()

        all_negatives = DBSession.query(AlleleGeninteraction).filter(or_(AlleleGeninteraction.allele1_id==self.dbentity_id, AlleleGeninteraction.allele2_id==self.dbentity_id)).filter(AlleleGeninteraction.sga_score < 0).order_by(AlleleGeninteraction.sga_score).all()
        
        for x in all_positives[0:30] + all_negatives[0:30]:
                
            if x.allele2_id is None:
                continue
            other_allele = None
            if x.allele1_id != self.dbentity_id:
                other_allele = allele_id_to_name.get(x.allele1_id)
                all_linked_allele_ids.append(x.allele1_id)
            else:
                other_allele = allele_id_to_name.get(x.allele2_id)
                all_linked_allele_ids.append(x.allele2_id)
            if other_allele is None:
                continue
            allele_format_name = other_allele.replace(' ', '_') 

            if allele_format_name not in network_nodes_ids:
                network_nodes.append({
                    "name": other_allele,
                    "id": allele_format_name,
                    "href": "/allele/" + allele_format_name,
                    "category": "ALLELE",
                })
                network_nodes_ids[allele_format_name] = True

                interaction_format_name = self.format_name + "_" + allele_format_name

                if x.sga_score > 0:
                    network_nodes.append({
                        "name": '',
                        "id": interaction_format_name,
                        "href": '',
                        "category": "POSITIVE INTERACTION",
                    })
                else:
                    network_nodes.append({
                        "name": '',
                        "id": interaction_format_name,
                        "href": '',
                        "category": "NEGATIVE INTERACTION",
                    })
                
                network_edges.append({
                    "source": self.format_name,
                    "target": interaction_format_name
                })
                
                network_edges.append({
                    "source": allele_format_name,
                    "target": interaction_format_name
                })
                
        # for x in DBSession.query(AlleleGeninteraction).filter(AlleleGeninteraction.allele1_id.in_(all_linked_allele_ids)).filter(AlleleGeninteraction.allele2_id.in_(all_linked_allele_ids)).all():
        #    allele1_format_name = allele_id_to_name.get(x.allele1_id, '').replace(' ', '_') 
        #    allele2_format_name = allele_id_to_name.get(x.allele2_id, '').replace(' ', '_') 
        #    network_edges.append({
        #        "source": allele1_format_name,
        #        "target": allele2_format_name
        #    })
                
        data = { "edges": network_edges, "nodes": network_nodes }

        return data

    
class AlleleReference(Base):
    __tablename__ = 'allele_reference'
    __table_args__ = (
        UniqueConstraint('allele_id', 'reference_id'),
        {'schema': 'nex'}
    )

    allele_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    allele_id = Column(ForeignKey('nex.alleledbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    reference_class = Column(String(100), nullable=True)
    
    allele = relationship('Alleledbentity')
    source = relationship('Source')
    reference = relationship('Referencedbentity')
    
class AlleleGeninteraction(Base):
    __tablename__ = 'allele_geninteraction'
    __table_args__ = (
        UniqueConstraint('allele1_id', 'allele2_id', 'interaction_id'),
        {'schema': 'nex'}
    )

    allele_geninteraction_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    allele1_id = Column(ForeignKey('nex.alleledbentity.dbentity_id', ondelete='CASCADE'), nullable=True)
    allele2_id = Column(ForeignKey('nex.alleledbentity.dbentity_id', ondelete='CASCADE'), nullable=True)
    interaction_id = Column(ForeignKey('nex.geninteractionannotation.annotation_id', ondelete='CASCADE'), nullable=False, index=True)
    sga_score = Column(Numeric, nullable=False)
    pvalue = Column(Numeric, nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    allele1 = relationship('Alleledbentity', primaryjoin='AlleleGeninteraction.allele1_id == Alleledbentity.dbentity_id')
    allele2 = relationship('Alleledbentity', primaryjoin='AlleleGeninteraction.allele2_id == Alleledbentity.dbentity_id')
    source = relationship('Source')
    interaction = relationship('Geninteractionannotation')

    
class AlleleAlias(Base):
    __tablename__ = 'allele_alias'
    __table_args__ = (
        UniqueConstraint('allele_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    allele_alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    allele_id = Column(ForeignKey('nex.alleledbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    allele = relationship('Alleledbentity')
    source = relationship('Source')

class AllelealiasReference(Base):
    __tablename__ = 'allelealias_reference'
    __table_args__ = (
        UniqueConstraint('allele_alias_id', 'reference_id'),
        {'schema': 'nex'}
    )

    allelealias_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    allele_alias_id = Column(ForeignKey('nex.allele_alias.allele_alias_id', ondelete='CASCADE'), nullable=False)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    alias = relationship('AlleleAlias')
    source = relationship('Source')
    reference = relationship('Referencedbentity')

class LocusAllele(Base):
    __tablename__ = 'locus_allele'
    __table_args__ = (
        UniqueConstraint('locus_id', 'allele_id'),
        {'schema': 'nex'}
    )

    locus_allele_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    allele_id = Column(ForeignKey('nex.alleledbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    locus = relationship('Locusdbentity')
    source = relationship('Source')
    allele = relationship('Alleledbentity')

class LocusalleleReference(Base):
    __tablename__ = 'locusallele_reference'
    __table_args__ = (
	UniqueConstraint('locus_allele_id', 'reference_id'),
        {'schema': 'nex'}
    )

    locusallele_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    locus_allele_id = Column(ForeignKey('nex.locus_allele.locus_allele_id', ondelete='CASCADE'), nullable=False)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    locusallele = relationship('LocusAllele')
    source = relationship('Source')
    reference = relationship('Referencedbentity')

class Transcriptdbentity(Dbentity):
    __tablename__ = 'transcriptdbentity'
    __table_args__ = {'schema': 'nex'}
    __url_segment__ = '/transcript/'

    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    in_gal = Column(Boolean, nullable=False)
    in_ypd = Column(Boolean, nullable=False)
    in_ncbi = Column(Boolean, nullable=False)

class TranscriptReference(Base):
    __tablename__ = 'transcript_reference'
    __table_args__ = (
        UniqueConstraint('transcript_id', 'reference_id'),
        {'schema': 'nex'}
    )

    transcript_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    transcript_id = Column(ForeignKey('nex.transcriptdbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    transcript = relationship('Transcriptdbentity')
    source = relationship('Source')
    reference = relationship('Referencedbentity')
    
class Complexdbentity(Dbentity):
    __tablename__ = 'complexdbentity'
    __table_args__ = {'schema': 'nex'}
    __url_segment__ = '/complex/'

    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    intact_id = Column(String(40), nullable=False)
    systematic_name = Column(String(500), nullable=False)
    eco_id = Column(ForeignKey('nex.eco.eco_id', ondelete='CASCADE'), nullable=False, index=True)
    description = Column(Text, nullable=True)
    properties = Column(Text, nullable=True)
    complex_accession = Column(String(40), nullable=False)

    eco = relationship('Eco')

    def protein_complex_details(self):

        data = {}
        data['complex_name'] = self.display_name
        data['complex_accession'] = self.format_name
        data['intact_id'] = self.intact_id
        data['systematic_name'] = self.systematic_name
        data['sgdid'] = self.sgdid
        data['source'] = self.source.display_name
        # data['description'] = link_gene_complex_names(self.description, {self.format_name: 1}, DBSession),
        # data['properties'] = link_gene_complex_names(self.properties, {self.format_name: 1}, DBSession),
        data['description'] = self.description
        data['go_overview'] = self.go_overview_to_dict()
        data['properties'] = self.properties
        data['eco'] = self.eco.format_name

        nodes_ids = {}
        network_nodes_ids = {}

        ## aliases                                                                                                                                    

        alias_objs = DBSession.query(ComplexAlias).filter_by(complex_id=self.dbentity_id).order_by(ComplexAlias.alias_type, ComplexAlias.display_name).all()

        aliases = []
        pdbs = []
        crossRefs = []
        if alias_objs:
            for ca in alias_objs:
                if ca.alias_type == 'Synonym':
                    aliases.append(ca.display_name)
                elif ca.alias_type == 'PDB':
                    pdbs.append({ "display_name": ca.display_name.upper() })
                else:
                    crossRefs.append({ "alias_type": ca.alias_type,
                                       "display_name": ca.display_name })
        data['aliases'] = sorted(aliases)
        data['pdbs'] = sorted(pdbs, key=lambda p: p['display_name'])
        crossRefs2 = sorted(crossRefs, key=lambda c: c['display_name'])
        data["cross_references"] = sorted(crossRefs2, key=lambda c: c['alias_type'])

        unique_references = []
        data['primary_references'] = self.get_literatureannotation_references("Primary Literature", unique_references )
        data['additional_references'] = self.get_literatureannotation_references("Additional Literature", unique_references)
        data['review_references'] = self.get_literatureannotation_references("Reviews", unique_references)
        data['unique_references'] = unique_references

        ## go
        
        network_nodes =[]
        network_edges =[]
                
        network_nodes.append({
            "name": self.display_name,
            "id": self.format_name,
            "href": "/complex/" + self.format_name,
            "category": "FOCUS",
        })
        
        network_nodes_ids[self.format_name] = True
        
        complex_ids = []
        for x in DBSession.query(Complexdbentity).all():
            complex_ids.append(x.dbentity_id)
        
        go_annots = DBSession.query(Goannotation).filter_by(dbentity_id=self.dbentity_id).all()

        process = []
        function = []
        component = []

        foundComplex = {}
        
        if go_annots:
            data['go'] = [g.go.to_dict() for g in go_annots]
            for x in go_annots:
                go = x.go
                if go.go_namespace == 'molecular function':
                    function.append(x.to_dict()[0])
                elif go.go_namespace == 'cellular component':
                    component.append(x.to_dict()[0])
                else:
                    process.append(x.to_dict()[0])
                    
                goComplexes = DBSession.query(Goannotation).filter_by(go_id=go.go_id).filter(Goannotation.dbentity_id.in_(complex_ids)).all()
                
                if len(goComplexes) == 1:
                    continue
                    
                if go.go_id not in network_nodes_ids:
                    network_nodes.append({
                            "name": go.display_name,
                            "id": go.go_id,
                            "href": go.obj_url,
                            "category": 'GO',
                    })
                    network_nodes_ids[go.go_id] = True
                
                for g2 in goComplexes:
                    complex = g2.dbentity
                    if complex.format_name == self.format_name:
                        continue
                    if complex.format_name in foundComplex:
                        if foundComplex[complex.format_name] != 1:
                            preGoid = foundComplex[complex.format_name]
                            ## this is 2nd time we see this complex, we want to keep this complex
                            ## in the network so need to link "self" to preGoid as well as current goid
                            network_edges.append({
                                    "source": self.format_name,
                                    "target": preGoid
                            })
                            network_edges.append({
                                    "source": self.format_name,
                                    "target": go.go_id
                            })
                            
                            ### also need to add this complex to the network

                            if complex.format_name not in network_nodes_ids:
                                network_nodes.append({
                                        "name": complex.display_name,
                                        "id": complex.format_name,
                                        "href": "/complex/" + complex.format_name,
                                        "category": "complex"
                                })
                                network_nodes_ids[complex.format_name] = True
                            
                            ### link this complex to preGoid as well as this goid
                            network_edges.append({
                                    "source": complex.format_name,
                                    "target": preGoid
                            })
                            network_edges.append({
                                    "source": complex.format_name,
                                    "target": go.go_id
                            })
                            foundComplex[complex.format_name] = 1
                        else:
                            ## this 3rd or 4th.. time see this complex
                            ## simply link this complex to current goid
                            network_edges.append({
                                "source": complex.format_name,
                                "target": go.go_id
                            })
                            network_edges.append({
                                "source": self.format_name,
                                "target": go.go_id
                            })
                            
                    else:
                        foundComplex[complex.format_name] = go.go_id

        
        foundId = {}
        for edge in network_edges:
            foundId[edge["source"]] = 1
            foundId[edge["target"]] = 1
            
        go_network_nodes = []
        for node in network_nodes:
            if node["id"] in foundId:
                go_network_nodes.append(node)
                
        data['go_network_graph'] = { "edges": network_edges, "nodes": go_network_nodes }
        
        data['process'] = sorted(process, key=lambda p: p['go']['display_name'])
        data['function'] = sorted(function, key=lambda f: f['go']['display_name'])
        data['component'] = sorted(component, key=lambda c: c['go']['display_name'])

        ## reference

        ref_objs = DBSession.query(ComplexReference).filter_by(complex_id=self.dbentity_id).all()

        refs = []
        if ref_objs:
            refs = [ref.reference.to_dict_citation() for ref in ref_objs]
        refs2 = sorted(refs, key=lambda r: r['display_name'])
        data["references"] = sorted(refs2, key=lambda r: r['year'], reverse=True)

        ## subunits

        rna_id_to_locus = dict([(x.display_name, x.locus) for x in DBSession.query(LocusAlias).filter_by(alias_type='RNAcentral ID').all()])
        chebi_to_link = dict([(x.format_name, x.obj_url) for x in DBSession.query(Chebi).all()])
        
        annot_objs = DBSession.query(Complexbindingannotation).filter_by(complex_id=self.dbentity_id).all()

        unique_interactors = []
        found = {}
        edges = []
        nodes = []
        stoichiometry4interactor = {}
        found_binding = {}
        found_node = {}
        name_list = {}
        for annot in annot_objs:
            interactor = annot.interactor
            binding_interactor = annot.binding_interactor

            display_name = interactor.display_name
            link = interactor.obj_url
            sgdid = None
            type = "other subunit"
            dbentity_id = None
            if interactor.locus_id:
                display_name = interactor.locus.display_name
                sgdid = interactor.locus.sgdid
                description = interactor.locus.headline
                link = interactor.locus.obj_url
                dbentity_id = interactor.locus_id
                type = "protein"
            elif interactor.format_name.startswith('CPX-'):
                type = 'subcomplex'
                link = '/complex/' + interactor.format_name
            elif interactor.format_name.startswith('CHEBI:'):
                type = "small molecule"
                if interactor.format_name in chebi_to_link:
                    link = chebi_to_link[interactor.format_name]
            elif interactor.format_name.startswith('URS') and 'rnacentral.org' in link:
                if interactor.format_name in rna_id_to_locus:
                    link = rna_id_to_locus[interactor.format_name].obj_url
                    
            count = 1
            if annot.stoichiometry and annot.stoichiometry > 1:
                count = annot.stoichiometry

            for i in range(count):
                node_id = interactor.format_name
                if i > 0:
                    node_id = node_id + "_" + str(i)
                names = []
                if interactor.format_name in name_list:
                    names = name_list[interactor.format_name]
                if node_id not in names:
                    names.append(node_id)
                name_list[interactor.format_name] = names

                if node_id not in found_node:
                    nodes.append({
                        "name": display_name,
                        "id": node_id,
                        "dbentity_id": dbentity_id,
                        "href": link,
                        "category": type
                    })
                    found_node[node_id] = 1

                if binding_interactor is not None:
                    binding_node_ids = []
                    if binding_interactor.format_name in name_list:
                        binding_node_ids = name_list[binding_interactor.format_name]
                    else:
                        binding_node_ids = [binding_interactor.format_name]
                    for binding_node_id in binding_node_ids:
                        if (node_id, binding_node_id) not in found_binding and (binding_node_id, node_id) not in found_binding:
                            edges.append({
                                "source": node_id,
                                "target": binding_node_id,
                                "category": "complex"
                            })
                            found_binding[(node_id, binding_node_id)] = 1

            stoichiometry4interactor[interactor.format_name] = annot.stoichiometry
            if interactor.format_name not in found:
                unique_interactors.append(interactor)
                found[interactor.format_name] = 1
            if binding_interactor is not None and binding_interactor.format_name not in found:
                unique_interactors.append(binding_interactor)
                found[binding_interactor.format_name] =1

        subunits = []
        for interactor in unique_interactors:
            display_name = interactor.display_name
            description = interactor.description
            link = interactor.obj_url
            sgdid = None
            type = "other subunit"
            dbentity_id = None
            if interactor.locus_id:
                display_name = interactor.locus.display_name
                sgdid = interactor.locus.sgdid
                description = interactor.locus.headline
                link = interactor.locus.obj_url
                dbentity_id = interactor.locus_id
                type = "protein"
            elif interactor.format_name.startswith('CPX-'):
                type = 'subcomplex'
                link = '/complex/' + interactor.format_name
            elif interactor.format_name.startswith('CHEBI:'):
                type = "small molecule"
                if interactor.format_name in chebi_to_link:
                    link = chebi_to_link[interactor.format_name]
            elif interactor.format_name.startswith('URS') and 'rnacentral.org' in link:
                if interactor.format_name in rna_id_to_locus:
                    link = rna_id_to_locus[interactor.format_name].obj_url
                    
            subunits.append({ "display_name": display_name,
                              "description": description,
                              "sgdid": sgdid,
                              "dbentity_id": dbentity_id,
                              "stoichiometry": stoichiometry4interactor.get(interactor.format_name),
                              "link": link })

            annot_objs2 = DBSession.query(Complexbindingannotation).filter_by(interactor_id=interactor.interactor_id).all()

            unique_complexes = {}
            for annot in annot_objs2:
                complex = annot.complex
                unique_complexes[complex.display_name] = 1
                
            if len(unique_complexes) == 1:
                continue

            if interactor.format_name not in network_nodes_ids:
                network_nodes.append({
                       "name": display_name,
                       "id": interactor.format_name,
                       "href": link,
                       "dbentity_id": dbentity_id,
                       "category": "subunit"
                })
                network_nodes_ids[interactor.format_name] = True

            found = {}
            for annot in annot_objs2:
                complex = annot.complex
                if complex.format_name in found:
                    continue
                found[complex.format_name] = 1

                if complex.format_name in foundComplex:

                    if foundComplex[complex.format_name] != 1:
                        preTarget = foundComplex[complex.format_name]
                        ## this is 2nd time we can see this complex, we want to keep this complex 
                        ## in the network so need to link "self" complex to preTarget (either goid or 
                        ## subunit) as well as this subunit (interactor) 
                        network_edges.append({
                                "source": self.format_name,
                                "target": preTarget
                        })
                        network_edges.append({
                                "source": self.format_name,
                                "target": interactor.format_name
                        })

                        ### also need to add this complex to the network 

                        if complex.format_name not in network_nodes_ids:
                            print((complex.format_name))
                            network_nodes.append({
                                "name": complex.display_name,
                                "id": complex.format_name,
                                "href": "/complex/" + complex.format_name,
                                "category": "complex"
                            })
                            network_nodes_ids[complex.format_name] = True
                            
                        

                        ### link this complex to preTarget (either goid or subunit) as well 
                        ### as this subunit
                        network_edges.append({
                                "source": complex.format_name,
                                "target": preTarget
                        })
                        network_edges.append({
                                "source": complex.format_name,
                                "target": interactor.format_name
                        })
                        foundComplex[complex.format_name] = 1
                    else:
                        ## this 3rd or 4th.. time see this complex
                        ## simply link this complex to current subunit
                        network_edges.append({
                                "source": complex.format_name,
                                "target": interactor.format_name
                        })
                else:
                    foundComplex[complex.format_name] = interactor.format_name

        data['subunit'] = sorted(subunits, key=lambda a: a['display_name'])
        data['graph'] = { "edges": edges, "nodes": nodes }
        data['network_graph'] = { "edges": network_edges, "nodes": network_nodes }

        return data

    def go_overview_to_dict(self):

        go_slims = DBSession.query(Goslimannotation).filter_by(dbentity_id=self.dbentity_id).all()
        process_go_slim_list = []
        function_go_slim_list = []
        component_go_slim_list = []
        complex_go_slim_list = []
        for go_slim in go_slims:
            go_slim_dict = go_slim.to_dict()
            if 'complex' in go_slim_dict['slim_name'].lower():
                if go_slim_dict not in complex_go_slim_list:
                    complex_go_slim_list.append(go_slim_dict)
            else:
                go = DBSession.query(Go).filter_by(go_id=go_slim_dict['go_id']).one_or_none()
                if go is None:
                    continue
                if 'component' in go.go_namespace:
                    if go_slim_dict not in component_go_slim_list:
                        component_go_slim_list.append(go_slim_dict)
                elif 'function' in go.go_namespace:
                    if go_slim_dict not in function_go_slim_list:
                        function_go_slim_list.append(go_slim_dict)
                elif go_slim_dict not in process_go_slim_list:
                    process_go_slim_list.append(go_slim_dict)

        obj = { 'date_last_reviewed': None,
                'go_slim_grouped': [] }
        
        ## sort goslim terms here
        process_go_slim_sorted_list = sorted(process_go_slim_list, key=lambda p: p['display_name'])
        function_go_slim_sorted_list = sorted(function_go_slim_list, key=lambda p: p['display_name'])
        component_go_slim_sorted_list = sorted(component_go_slim_list, key=lambda p: p['display_name'])
        complex_go_slim_sorted_list = sorted(complex_go_slim_list, key=lambda p: p['display_name'])
        obj['go_slim_grouped'] = function_go_slim_sorted_list + process_go_slim_sorted_list + component_go_slim_sorted_list + complex_go_slim_sorted_list

        go_annotations = DBSession.query(Goannotation).filter_by(dbentity_id=self.dbentity_id).all()
        for annotation in go_annotations:
            if obj["date_last_reviewed"] is None or annotation.date_assigned.strftime("%Y-%m-%d") > obj["date_last_reviewed"]:
                obj["date_last_reviewed"] = annotation.date_assigned.strftime("%Y-%m-%d")


        return obj

    
    def get_literatureannotation_references(self, topic, unique_references):

        references = []

        #for x in DBSession.query(Literatureannotation).filter_by(dbentity_id=self.dbentity_id, topic=topic).all():
        #    if x.reference.to_dict_citation() not in references:
        #        references.append(x.reference.to_dict_citation())
        #    if x.reference.dbentity_id not in unique_references:
        #        unique_references.append(x.reference.dbentity_id)

        ref_ids = []
        for x in DBSession.query(Literatureannotation).filter_by(dbentity_id=self.dbentity_id, topic=topic).all():
            ref_ids.append(x.reference_id)

        for x in DBSession.query(Referencedbentity).filter(Referencedbentity.dbentity_id.in_(ref_ids)).order_by(Referencedbentity.year.desc(), Referencedbentity.display_name.asc()).all():
            if x.to_dict_citation() not in references:
                references.append(x.to_dict_citation())  
            if x.dbentity_id not in unique_references:
                unique_references.append(x.dbentity_id)

        return references


class ComplexAlias(Base):
    __tablename__ = 'complex_alias'
    __table_args__ = (
        UniqueConstraint('complex_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    complex_id = Column(ForeignKey('nex.complexdbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    complex = relationship('Complexdbentity')
    source = relationship('Source')

class ComplexGo(Base):
    __tablename__ = 'complex_go'
    __table_args__ = (
        UniqueConstraint('complex_id', 'go_id'),
        {'schema': 'nex'}
    )

    complex_go_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    complex_id = Column(ForeignKey('nex.complexdbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    go_id = Column(ForeignKey('nex.go.go_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    complex = relationship('Complexdbentity')
    source = relationship('Source')
    go = relationship('Go')

class ComplexReference(Base):
    __tablename__ = 'complex_reference'
    __table_args__ = (
        UniqueConstraint('complex_id', 'reference_id'),
        {'schema': 'nex'}
    )

    complex_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    complex_id = Column(ForeignKey('nex.complexdbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    complex = relationship('Complexdbentity')
    source = relationship('Source')
    reference = relationship('Referencedbentity')


class Complexbindingannotation(Base):
    __tablename__ = 'complexbindingannotation'
    __table_args__ = (
        UniqueConstraint('complex_id', 'interactor_id', 'binding_interactor_id', 'reference_id', 'binding_type_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    complex_id = Column(ForeignKey('nex.complexdbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    interactor_id = Column(ForeignKey('nex.interactor.interactor_id', ondelete='CASCADE'), nullable=False, index=True)
    binding_interactor_id = Column(ForeignKey('nex.interactor.interactor_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    binding_type_id = Column(ForeignKey('nex.psimi.psimi_id', ondelete='CASCADE'), nullable=False, index=True)
    range_start = Column(Integer)
    range_end = Column(Integer)
    stoichiometry = Column(Integer)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    interactor = relationship('Interactor', foreign_keys=[interactor_id])
    binding_interactor = relationship('Interactor', foreign_keys=[binding_interactor_id])
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    source = relationship('Source')
    taxonomy = relationship('Taxonomy')
    complex = relationship('Complexdbentity')
    psimi = relationship('Psimi')
    

class Interactor(Base):
    __tablename__ = 'interactor'
    __table_args__ = {'schema': 'nex'}

    interactor_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False, index=True)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), nullable=True, index=True)
    description = Column(String(500))
    type_id = Column(ForeignKey('nex.psimi.psimi_id', ondelete='CASCADE'), nullable=False, index=True)
    role_id = Column(ForeignKey('nex.psimi.psimi_id', ondelete='CASCADE'), nullable=False, index=True)
    residues = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    locus = relationship('Locusdbentity')
    type = relationship('Psimi', foreign_keys=[type_id])
    role = relationship('Psimi', foreign_keys=[role_id])


class ReferenceAlias(Base):
    __tablename__ = 'reference_alias'
    __table_args__ = (
        UniqueConstraint('reference_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    reference = relationship('Referencedbentity')
    source = relationship('Source')


class ReferenceFile(Base):
    __tablename__ = 'reference_file'
    __table_args__ = (
        UniqueConstraint('reference_id', 'file_id'),
        {'schema': 'nex'}
    )

    reference_file_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    file_id = Column(ForeignKey('nex.filedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    file_type = Column(String(100), nullable=False)

    file = relationship('Filedbentity')
    reference = relationship('Referencedbentity')
    source = relationship('Source')


class ReferenceRelation(Base):
    __tablename__ = 'reference_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'relation_type'),
        {'schema': 'nex'}
    )

    reference_relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    child_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    relation_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Referencedbentity', primaryjoin='ReferenceRelation.child_id == Referencedbentity.dbentity_id')
    parent = relationship('Referencedbentity', primaryjoin='ReferenceRelation.parent_id == Referencedbentity.dbentity_id')
    source = relationship('Source')


class ReferenceUrl(Base):
    __tablename__ = 'reference_url'
    __table_args__ = (
        UniqueConstraint('reference_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    reference = relationship('Referencedbentity')
    source = relationship('Source')


class Referenceauthor(Base):
    __tablename__ = 'referenceauthor'
    __table_args__ = (
        UniqueConstraint('reference_id', 'display_name', 'author_order'),
        {'schema': 'nex'}
    )

    referenceauthor_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    orcid = Column(String(20))
    author_order = Column(SmallInteger, nullable=False)
    author_type = Column(String(10), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    reference = relationship('Referencedbentity')
    source = relationship('Source')


class Referencedeleted(Base):
    __tablename__ = 'referencedeleted'
    __table_args__ = {'schema': 'nex'}

    referencedeleted_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    pmid = Column(BigInteger, nullable=False, unique=True)
    sgdid = Column(String(20), unique=True)
    reason_deleted = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)


class Referencedocument(Base):
    __tablename__ = 'referencedocument'
    __table_args__ = (
        UniqueConstraint('reference_id', 'document_type'),
        {'schema': 'nex'}
    )

    referencedocument_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    document_type = Column(String(40), nullable=False)
    text = Column(Text, nullable=False)
    html = Column(Text, nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=FetchedValue())
    created_by = Column(String(12), nullable=False)

    reference = relationship('Referencedbentity')
    source = relationship('Source')


class Referencetriage(Base):
    __tablename__ = 'referencetriage'
    __table_args__ = {'schema': 'nex'}

    curation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.curation_seq'::regclass)"))
    pmid = Column(BigInteger, nullable=False, unique=True)
    citation = Column(String(500), nullable=False)
    fulltext_url = Column(String(500))
    abstract = Column(Text)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    json = Column(Text)
    abstract_genes = Column(String(500))

    def to_dict(self):
        return {
            "curation_id": self.curation_id,
            "basic": {
                "pmid": self.pmid,
                "citation": self.citation,
                "fulltext_url": self.fulltext_url,
                "abstract": self.abstract,
                "abstract_genes": self.abstract_genes,
                "date_created": self.date_created.strftime("%Y-%m-%d")
            },
            "data": json.loads(self.json or "{}")
        }

    def update_from_json(self, json_obj):
        if 'basic' in json_obj:
            if 'pmid' in json_obj['basic']:
                self.pmid = json_obj['basic']['pmid']
            if 'citation' in json_obj['basic']:
                self.citation = json_obj['basic']['citation']
            if 'fulltext_url' in json_obj['basic']:
                self.fulltext_url = json_obj['basic']['fulltext_url']
            if 'abstract' in json_obj['basic']:
                self.abstract = json_obj['basic']['abstract']
        if 'data' in json_obj:
            self.json = json.dumps(json_obj['data'])

class Referencetype(Base):
    __tablename__ = 'referencetype'
    __table_args__ = (
        UniqueConstraint('reference_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    referencetype_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    reference = relationship('Referencedbentity')
    source = relationship('Source')


class Referenceunlink(Base):
    __tablename__ = 'referenceunlink'
    __table_args__ = (
        UniqueConstraint('reference_id', 'dbentity_id'),
        {'schema': 'nex'}
    )

    referenceunlink_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    dbentity_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    dbentity = relationship('Dbentity')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])


class Regulationannotation(Base):
    __tablename__ = 'regulationannotation'
    __table_args__ = (
        UniqueConstraint('target_id', 'regulator_id', 'eco_id', 'reference_id'),
        {'schema': 'nex'}
    )

    annotation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.annotation_seq'::regclass)"))
    target_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    regulator_id = Column(ForeignKey('nex.dbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    eco_id = Column(ForeignKey('nex.eco.eco_id', ondelete='CASCADE'), nullable=False, index=True)
    regulator_type = Column(String(40), nullable=False)
    regulation_type = Column(String(100), nullable=False)
    direction = Column(String(10))
    happens_during = Column(ForeignKey('nex.go.go_id', ondelete='CASCADE'), index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    annotation_type = Column(String(40), nullable=False)

    eco = relationship('Eco')
    go = relationship('Go')
    reference = relationship('Referencedbentity', foreign_keys=[reference_id])
    regulator = relationship('Dbentity', primaryjoin='Regulationannotation.regulator_id == Dbentity.dbentity_id')
    source = relationship('Source')
    target = relationship('Dbentity', primaryjoin='Regulationannotation.target_id == Dbentity.dbentity_id')
    taxonomy = relationship('Taxonomy')

    def get_happens_during(self):
        item = DBSession.query(Go).filter(Go.go_id == self.happens_during).first()
        if(item != None):
            return item.display_name
        return None



    def to_dict(self, reference=None):
        if reference is None:
            reference = self.reference

        experiment = None
        if self.eco:
            experiment = {
                "display_name": self.eco.display_name,
                "link": None
            }

        strain = Straindbentity.get_strains_by_taxon_id(self.taxonomy_id)

        strain_obj = None
        if len(strain) == 0 or len(strain) > 1:
            strain_obj = {
                "display_name": "Other",
                "link": "/strain/S000203479"
            }
        else:
            strain_obj = {
                "display_name": strain[0].display_name,
                "link": strain[0].obj_url
            }

        return {
            "id": self.annotation_id,
            "locus1": {
                "display_name": self.regulator.display_name,
                "link": self.regulator.obj_url,
                "id": self.regulator.dbentity_id,
                "format_name": self.regulator.format_name
            },
            "locus2": {
                "display_name": self.target.display_name,
                "link": self.target.obj_url,
                "id": self.target.dbentity_id,
                "format_name": self.target.format_name
            },
            "evidence": experiment,
            "regulation_of": self.regulation_type,
            "happens_during": self.get_happens_during(),
            "direction": self.direction,
            "reference": reference.to_dict_citation(),
            "strain": strain_obj,
            "experiment": experiment,
            "annotation_type": self.annotation_type,
            "regulation_type": self.regulation_type,
            "regulator_type": self.regulator_type,
            # these are still here because of the old format. We should remove them after changes in the FE
            "properties": [],
            "assay": "",
            "construct": ""
        }


class Reporter(Base):
    __tablename__ = 'reporter'
    __table_args__ = {'schema': 'nex'}

    reporter_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    description = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')


class Reservedname(Base):
    __tablename__ = 'reservedname'
    __table_args__ = {'schema': 'nex'}

    reservedname_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    locus_id = Column(ForeignKey('nex.locusdbentity.dbentity_id', ondelete='CASCADE'), index=True)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), index=True)
    colleague_id = Column(ForeignKey('nex.colleague.colleague_id', ondelete='CASCADE'), nullable=False, index=True)
    reservation_date = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    expiration_date = Column(DateTime, nullable=False, server_default=text("(('now'::text)::timestamp without time zone + '365 days'::interval)"))
    description = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    name_description = Column(String(500))

    colleague = relationship('Colleague')
    locus = relationship('Locusdbentity')
    reference = relationship('Referencedbentity')
    source = relationship('Source')

    def to_dict(self):
        obj = {
            'id': self.reservedname_id,
            'display_name': self.display_name,
            'reservation_date': self.reservation_date.strftime('%Y-%m-%d'),
            'expiration_date': self.expiration_date.strftime('%Y-%m-%d'),
            'locus': None,
            'reference': None,
            'reservation_status': 'Reserved'
        }

        if self.locus:
            obj['locus'] = {
                'display_name': self.locus.display_name,
                'systematic_name': self.locus.systematic_name,
                'link': self.locus.obj_url
            }

        if self.reference:
            obj['reference'] = {
                'display_name': self.reference.display_name,
                'link': self.reference.obj_url,
                'pmid': self.reference.pmid
            }

        if self.name_description:
            obj['name_description'] = self.name_description

        return obj

    # extend to_dict with curator properties
    def to_curate_dict(self):
        obj = self.to_dict()
        # colleague info
        submitter = self.colleague
        obj['submitter_name'] = submitter.first_name + ' ' + submitter.last_name
        obj['submitter_email'] = submitter.email
        obj['submitter_phone'] = submitter.work_phone
        obj['notes'] = self.description
        if obj['locus']:
            obj['systematic_name'] = obj['locus']['systematic_name']
        return obj

    def is_ref_published(self):
        pub_status = self.reference.publication_status
        return (pub_status == 'Published' or pub_status == 'Epub ahead of print')

    # add rows to LOCUS_REFERENCE, LOCUSNOTE, and LOCUSNOTE_REFERENCE for associated changes to locus
    def associate_locus(self, systematic_name, username):
        curator_session = None
        try:
            curator_session = get_curator_session(username)
            self = curator_session.merge(self)
            locus_id = curator_session.query(Locusdbentity.dbentity_id).filter(Locusdbentity.systematic_name == systematic_name).scalar()
            if not locus_id:
                raise ValueError('Not a valid systematic name.')
            has_locusreferences = curator_session.query(LocusReferences).filter(and_(LocusReferences.locus_id == locus_id, LocusReferences.reference_class == 'gene_name')).count()
            if not has_locusreferences:
                personal_communication_ref = curator_session.query(Referencedbentity).filter(Referencedbentity.dbentity_id == self.reference_id).one_or_none()
                gene_name_locus_ref = LocusReferences(
                    locus_id = locus_id,
                    reference_id = personal_communication_ref.dbentity_id,
                    reference_class = 'gene_name',
                    source_id = SGD_SOURCE_ID,
                    created_by = username
                )
                curator_session.add(gene_name_locus_ref)
                name_description_locus_ref = LocusReferences(
                    locus_id = locus_id,
                    reference_id = personal_communication_ref.dbentity_id,
                    reference_class = 'name_description',
                    source_id = SGD_SOURCE_ID,
                    created_by = username
                )
                curator_session.add(name_description_locus_ref)
            # new locus_note and locusnote locusnote_reference
            has_locusnote = curator_session.query(Locusnote).filter(and_(Locusnote.locus_id == locus_id, Locusnote.note_type == 'Name', Locusnote.note_class == 'Locus')).count()
            if not has_locusnote:
                note_html_str = '<b>Name:</b> ' + self.display_name
                new_locusnote = Locusnote(
                    source_id = SGD_SOURCE_ID,
                    locus_id = locus_id,
                    note_class = 'Locus',
                    note_type = 'Name',
                    note = note_html_str,
                    created_by = username
                )
                curator_session.add(new_locusnote)
                curator_session.flush()
                curator_session.refresh(new_locusnote)
                new_locusnote_ref = LocusnoteReference(
                    note_id = new_locusnote.note_id,
                    reference_id = self.reference_id,
                    source_id = SGD_SOURCE_ID,
                    created_by = username
                )
                curator_session.add(new_locusnote_ref)
            transaction.commit()
            return locus_id
        except Exception as e:
            transaction.abort()
            traceback.print_exc()
            raise(e)
        finally:
            if curator_session:
                curator_session.remove()

    def associate_published_reference(self, ref_id, username, new_reference_class):
        if not self.locus_id:
            raise ValueError('Reserved name must be associated with a locus before adding published reference.')
        curator_session = None
        try:
            curator_session = get_curator_session(username)
            self = curator_session.merge(self)
            # see how many reserved name use this reference exist for personal communication, save for later
            ref_count = curator_session.query(Reservedname).filter(Reservedname.reference_id == self.reference_id).count()
            # delete old locusreferences
            curator_session.query(LocusReferences).filter(and_(LocusReferences.locus_id == self.locus_id, LocusReferences.reference_id == self.reference_id, LocusReferences.reference_class == new_reference_class)).delete(synchronize_session=False)
            has_ref_name = curator_session.query(LocusReferences).filter(and_(LocusReferences.locus_id == self.locus_id, LocusReferences.reference_id == ref_id, LocusReferences.reference_class == new_reference_class)).count()
            if not has_ref_name:
                new_locus_ref = LocusReferences(
                    locus_id = self.locus_id,
                    reference_id = ref_id,
                    reference_class = new_reference_class,
                    source_id = SGD_SOURCE_ID,
                    created_by = username
                )
                curator_session.add(new_locus_ref)
            if new_reference_class == 'gene_name':
                # update LocusnoteReference to have new ref id
                curator_session.query(LocusnoteReference).filter_by(reference_id=self.reference_id).update({ 'reference_id': ref_id })
                # finally change reference_id
                personal_communication_ref_id = self.reference_id
                personal_communication_ref = curator_session.query(Referencedbentity).filter(Referencedbentity.dbentity_id == personal_communication_ref_id).one_or_none()
                self.reference_id = ref_id
            transaction.commit()
            # if this is only one reference for personal communication, delete it
            if new_reference_class == 'gene_name' and ref_count == 1 and personal_communication_ref.publication_status != 'Published':
                personal_communication_ref = curator_session.query(Referencedbentity).filter(Referencedbentity.dbentity_id == personal_communication_ref_id).one_or_none()
                personal_communication_ref.delete_with_children(username)
        except Exception as e:
            transaction.abort()
            traceback.print_exc()
            raise(e)
        finally:
            if curator_session:
                curator_session.remove()

    def standardize(self, username):
        # a few validations
        if not self.is_ref_published():
            raise ValueError('Associated reference must be published before standardizing reservation.')
        if not self.locus_id:
            raise ValueError('Reserved name must be associated with an ORF before being standardized.')
        try:
            curator_session = get_curator_session(username)
            self = curator_session.merge(self)
            locus = curator_session.query(Locusdbentity).filter(Locusdbentity.dbentity_id == self.locus_id).one_or_none()
            locus.gene_name = self.display_name
            locus.display_name = self.display_name
            locus.name_description = self.name_description
            # archlocuschange update or add
            existing_archlocus = curator_session.query(ArchLocuschange).filter(and_(ArchLocuschange.dbentity_id == self.locus_id, ArchLocuschange.change_type == 'Gene name')).all()
            if len(existing_archlocus):
                existing_archlocus = existing_archlocus[0]
                existing_archlocus.date_name_standardized = datetime.now()
            else:
                new_archlocuschange = ArchLocuschange(
                    dbentity_id = self.locus_id,
                    change_type = 'Gene name',
                    new_value = self.display_name,
                    source_id = SGD_SOURCE_ID,
                    date_name_standardized = datetime.now(),
                    added_by = username
                )
                curator_session.add(new_archlocuschange)
            # add curator activity
            new_curate_activity = CuratorActivity(
                display_name = locus.display_name,
                obj_url = locus.obj_url,
                activity_category = 'locus',
                dbentity_id = locus.dbentity_id,
                message = 'standardized gene name',
                json = json.dumps({ 'keys': { 'gene_name': self.display_name }, 'modified_date': str(datetime.now())}),
                created_by = username
            )
            curator_session.add(new_curate_activity)
            curator_session.delete(self)
            transaction.commit()
            locus.ban_from_cache()
        except Exception as e:
            transaction.abort()
            traceback.print_exc()
            raise(e)
        finally:
            if curator_session:
                curator_session.remove()
        return True

    def update(self, new_info, username):
        try:
            curator_session = get_curator_session(username)
            self = curator_session.merge(self)
            if new_info['systematic_name']:
                res_systematic_name = new_info['systematic_name'].strip()
                is_locus = curator_session.query(Locusdbentity).filter(Locusdbentity.systematic_name == res_systematic_name).one_or_none()
                if not is_locus:
                    raise ValueError(res_systematic_name + ' is not a valid systematic_name.')
                if is_locus.gene_name:
                    raise ValueError(res_systematic_name + ' already has a standard name.')
                is_already_reserved = curator_session.query(Reservedname).filter(and_(Reservedname.locus_id == is_locus.dbentity_id, Reservedname.reservedname_id != self.reservedname_id)).one_or_none()
                if is_already_reserved:
                    raise ValueError(res_systematic_name + ' is already reserved for ' + is_already_reserved.display_name)
                new_locus_id = self.associate_locus(res_systematic_name, username)
                self = curator_session.merge(self)
                self.locus_id = new_locus_id
            elif self.locus_id:
                self.locus_id = None
            if new_info['display_name'] and new_info['display_name'] != self.display_name:
                potential_name = new_info['display_name'].upper().strip()
                if not Locusdbentity.is_valid_gene_name(potential_name):
                    raise ValueError(potential_name + ' does not follow gene name conventions.')
                exists_in_locus = curator_session.query(Locusdbentity).filter(Locusdbentity.gene_name == potential_name).one_or_none()
                if exists_in_locus:
                    raise ValueError(potential_name + ' is already a standard gene name.')
                exists_in_res = curator_session.query(Reservedname).filter(Reservedname.display_name == potential_name).one_or_none()
                if exists_in_res:
                    raise ValueError(potential_name + ' is a reserved gene name.')
                self.display_name = potential_name
            if new_info['name_description']:
                self.name_description = new_info['name_description']
            if new_info['notes']:
                self.description = new_info['notes']
            return_val = self.to_curate_dict()
            transaction.commit()
            return return_val
        except Exception as e:
            transaction.abort()
            traceback.print_exc()
            raise(e)
        finally:
            if curator_session:
                curator_session.remove()

    def extend(self, username):
        curator_session = None
        try:
            curator_session = get_curator_session(username)
            self = curator_session.merge(self)
            old_date = self.expiration_date
            self.expiration_date = old_date + timedelta(days=365)
            return_val = self.to_curate_dict()
            transaction.commit()
            return return_val
        except Exception as e:
            transaction.abort()
            traceback.print_exc()
            raise(e)
        finally:
            if curator_session:
                curator_session.remove()


class ReservednameTriage(Base):
    __tablename__ = 'reservednametriage'
    __table_args__ = {'schema': 'nex'}

    curation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    proposed_gene_name = Column(String(100), nullable=False)
    colleague_id = Column(ForeignKey('nex.colleague.colleague_id', ondelete='CASCADE'), index=True)
    json = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))

    def get_author_list(self):
        obj = json.loads(self.json)
        authors = obj['authors']
        author_list = []
        for x in authors:
            if x['first_name'] and x['last_name']:
                a_str = x['last_name'] + ' ' + x['first_name'][:1]
                author_list.append(a_str)
        if len(author_list) == 0:
            colleague = DBSession.query(Colleague).filter(Colleague.colleague_id == self.colleague_id).one_or_none()
            author_list = [colleague.last_name + ' ' + colleague.first_name[:1]]
        return author_list

    def to_citation(self):
        obj = json.loads(self.json)
        author_list = self.get_author_list()
        cit = get_author_etc(author_list) + ' ' + '(' + obj['year'] + ')'
        if 'publication_title' in list(obj.keys()):
            if obj['publication_title']:
                title = ' ' + str(obj['publication_title'])
                cit = cit + title
        return cit

    def to_dict(self):
        obj = json.loads(self.json)
        return_obj = {
            'id': self.curation_id,
            'display_name' : self.proposed_gene_name,
            'reservation_status': 'Unprocessed',
            'name_description': obj['description'],
            'notes': obj['notes'],
            'systematic_name': obj['systematic_name'],
            'reservation_date': self.date_created.strftime("%Y-%m-%d"),
            'reference': {
                'display_name': self.to_citation()
            }
        }
        colleague = DBSession.query(Colleague).filter(Colleague.colleague_id == self.colleague_id).one_or_none()
        return_obj['submitter_name'] = colleague.first_name + ' ' + colleague.last_name
        return_obj['submitter_email'] = colleague.email
        return_obj['submitter_phone'] = colleague.work_phone
        return return_obj

    def update(self, new_info, username):
        try:
            curator_session = get_curator_session(username)
            self = curator_session.merge(self)
            data = json.loads(self.json)
            if new_info['systematic_name']:
                res_systematic_name = new_info['systematic_name'].upper()
                is_locus = curator_session.query(Locusdbentity).filter(Locusdbentity.systematic_name == res_systematic_name).one_or_none()
                if not is_locus:
                    raise ValueError(res_systematic_name + ' is not a valid systematic_name.')
                is_already_reserved = curator_session.query(Reservedname).filter(Reservedname.locus_id == is_locus.dbentity_id).one_or_none()
                if is_already_reserved:
                    raise ValueError(res_systematic_name + ' is already reserved for ' + is_already_reserved.display_name)
                data['systematic_name'] = res_systematic_name
            if new_info['name_description']:
                data['description'] = new_info['name_description']
            if new_info['notes']:
                data['notes'] = new_info['notes']
            self.json = json.dumps(data)
            return_val = self.to_dict()
            transaction.commit()
            return return_val
        except Exception as e:
            transaction.abort()
            traceback.print_exc()
            raise(e)
        finally:
            if curator_session:
                curator_session.remove()

    def promote(self, username):
        try:
            obj = json.loads(self.json)
            curator_session = get_curator_session(username)
            self = curator_session.merge(self)
            # create personal communication
            citation = self.to_citation()
            # see if there is already personal communication for this and add if not yet added
            personal_communication_ref = curator_session.query(Referencedbentity).filter(Referencedbentity.citation == citation).one_or_none()
            if not personal_communication_ref:
                title = None
                if 'publication_title' in list(obj.keys()):
                    title = obj['publication_title']
                if title == '':
                    title = None
                journal_id = None
                if 'journal' in list(obj.keys()):
                    journal_name = obj['journal']
                    existing_journal = curator_session.query(Journal).filter(Journal.display_name == journal_name).all()
                    if len(existing_journal) > 0:
                        journal_id = existing_journal[0].journal_id
                personal_communication_ref = Referencedbentity(
                    display_name = citation,
                    source_id = DIRECT_SUBMISSION_SOURCE_ID,
                    subclass = 'REFERENCE',
                    dbentity_status = 'Active',
                    method_obtained = 'Gene registry',
                    publication_status = obj['status'],
                    fulltext_status = 'NAP',
                    citation = citation,
                    year = int(obj['year']),
                    title = title,
                    journal_id = journal_id,
                    created_by = username
                )
                curator_session.add(personal_communication_ref)
                curator_session.flush()
                curator_session.refresh(personal_communication_ref)
                author_list = self.get_author_list()
                for i, author in enumerate(author_list):
                    new_ref_author = Referenceauthor(
                        display_name = author,
                        obj_url = '/author/' + author.replace(' ', '_'),
                        source_id = DIRECT_SUBMISSION_SOURCE_ID,
                        reference_id = personal_communication_ref.dbentity_id,
                        author_order = i,
                        author_type = 'Author',
                        created_by = username
                    )
                    curator_session.add(new_ref_author)
                # add referencetype
                new_reftype = Referencetype(
                    display_name = 'Personal Communication to SGD',
                    obj_url = '/referencetype/Personal_Communication_to_SGD',
                    source_id = DIRECT_SUBMISSION_SOURCE_ID,
                    reference_id = personal_communication_ref.dbentity_id,
                    created_by = username
                )
                curator_session.add(new_reftype)
            # see if there is a locus
            locus_id = None
            if 'systematic_name' in list(obj.keys()):
                locus_id = curator_session.query(Locusdbentity.dbentity_id).filter(Locusdbentity.systematic_name == obj['systematic_name']).scalar()
            # actually add gene name reservation
            new_res = Reservedname(
                format_name = self.proposed_gene_name,
                display_name = self.proposed_gene_name,
                obj_url = '/reservedname/' + self.proposed_gene_name,
                source_id = DIRECT_SUBMISSION_SOURCE_ID,
                locus_id = locus_id,
                reference_id = personal_communication_ref.dbentity_id,
                colleague_id = self.colleague_id,
                name_description = obj['description'],
                description = obj['notes'],
                date_created = self.date_created,
                created_by = username
            )
            curator_session.add(new_res)
            curator_session.flush()
            curator_session.refresh(new_res)
            new_curate_activity = CuratorActivity(
                display_name = new_res.display_name,
                obj_url = new_res.obj_url,
                activity_category = 'reserved_name',
                json = json.dumps({'summary text': new_res.description , 'modified_date':str(datetime.now())}),
                message = 'gene name reservation added',
                created_by = username
            )
            curator_session.add(new_curate_activity)
            curator_session.delete(self)
            transaction.commit()
            if locus_id:
                new_res.associate_locus(obj['systematic_name'], username)
            return True
        except Exception as e:
            transaction.abort()
            traceback.print_exc()
            raise(e)
        finally:
            if curator_session:
                curator_session.remove()
        return True

class Ro(Base):
    __tablename__ = 'ro'
    __table_args__ = {'schema': 'nex'}

    ro_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    roid = Column(String(20), nullable=False, unique=True)
    description = Column(String(1000))
    is_obsolete = Column(Boolean, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')


class RoRelation(Base):
    __tablename__ = 'ro_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'relation_type'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    relation_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Ro', primaryjoin='RoRelation.child_id == Ro.ro_id')
    parent = relationship('Ro', primaryjoin='RoRelation.parent_id == Ro.ro_id')
    source = relationship('Source')


class RoUrl(Base):
    __tablename__ = 'ro_url'
    __table_args__ = (
        UniqueConstraint('ro_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    ro = relationship('Ro')
    source = relationship('Source')


class Sgdid(Base):
    __tablename__ = 'sgdid'
    __table_args__ = {'schema': 'nex'}

    sgdid_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    bud_id = Column(Integer)
    subclass = Column(String(40), nullable=False)
    sgdid_status = Column(String(40), nullable=False)
    description = Column(String(1000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')


class So(Base):
    __tablename__ = 'so'
    __table_args__ = {'schema': 'nex'}

    so_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    soid = Column(String(20), nullable=False, unique=True)
    description = Column(String(2000))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    is_obsolete = Column(Boolean, nullable=False)
    term_name = Column(String(500), nullable=False)
    
    source = relationship('Source')


class SoAlia(Base):
    __tablename__ = 'so_alias'
    __table_args__ = (
        UniqueConstraint('so_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    so_id = Column(ForeignKey('nex.so.so_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    so = relationship('So')
    source = relationship('Source')


class SoRelation(Base):
    __tablename__ = 'so_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.so.so_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.so.so_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('So', primaryjoin='SoRelation.child_id == So.so_id')
    parent = relationship('So', primaryjoin='SoRelation.parent_id == So.so_id')
    ro = relationship('Ro')
    source = relationship('Source')


class SoUrl(Base):
    __tablename__ = 'so_url'
    __table_args__ = (
        UniqueConstraint('so_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    so_id = Column(ForeignKey('nex.so.so_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    so = relationship('So')
    source = relationship('Source')


class Source(Base):
    __tablename__ = 'source'
    __table_args__ = {'schema': 'nex'}

    source_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    bud_id = Column(Integer)
    description = Column(String(500))
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    def to_dict(self):
        return {
            'id': self.source_id,
            'display_name': self.display_name,
            'format_name': self.format_name,
            'link': None
        }


class StrainUrl(Base):
    __tablename__ = 'strain_url'
    __table_args__ = (
        UniqueConstraint('strain_id', 'display_name', 'url_type'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    strain_id = Column(ForeignKey('nex.straindbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')
    strain = relationship('Straindbentity')


class Strainsummary(Base):
    __tablename__ = 'strainsummary'
    __table_args__ = (
        UniqueConstraint('strain_id', 'summary_type'),
        {'schema': 'nex'}
    )

    summary_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.summary_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    strain_id = Column(ForeignKey('nex.straindbentity.dbentity_id', ondelete='CASCADE'), nullable=False)
    summary_type = Column(String(40), nullable=False)
    text = Column(Text, nullable=False)
    html = Column(Text, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=FetchedValue())
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')
    strain = relationship('Straindbentity')


class StrainsummaryReference(Base):
    __tablename__ = 'strainsummary_reference'
    __table_args__ = (
        UniqueConstraint('summary_id', 'reference_id'),
        {'schema': 'nex'}
    )

    summary_reference_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.link_seq'::regclass)"))
    summary_id = Column(ForeignKey('nex.strainsummary.summary_id', ondelete='CASCADE'), nullable=False)
    reference_id = Column(ForeignKey('nex.referencedbentity.dbentity_id', ondelete='CASCADE'), nullable=False, index=True)
    reference_order = Column(SmallInteger, nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    reference = relationship('Referencedbentity')
    source = relationship('Source')
    summary = relationship('Strainsummary')


class Taxonomy(Base):
    __tablename__ = 'taxonomy'
    __table_args__ = {'schema': 'nex'}

    taxonomy_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.object_seq'::regclass)"))
    format_name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxid = Column(String(20), nullable=False, unique=True)
    common_name = Column(String(100))
    rank = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    is_obsolete = Column(Boolean, nullable=False)
    source = relationship('Source')


class TaxonomyAlia(Base):
    __tablename__ = 'taxonomy_alias'
    __table_args__ = (
        UniqueConstraint('taxonomy_id', 'display_name', 'alias_type'),
        {'schema': 'nex'}
    )

    alias_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.alias_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False)
    alias_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')
    taxonomy = relationship('Taxonomy')


class TaxonomyRelation(Base):
    __tablename__ = 'taxonomy_relation'
    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ro_id'),
        {'schema': 'nex'}
    )

    relation_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.relation_seq'::regclass)"))
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False)
    child_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False, index=True)
    ro_id = Column(ForeignKey('nex.ro.ro_id', ondelete='CASCADE'), nullable=False, index=True)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    child = relationship('Taxonomy', primaryjoin='TaxonomyRelation.child_id == Taxonomy.taxonomy_id')
    parent = relationship('Taxonomy', primaryjoin='TaxonomyRelation.parent_id == Taxonomy.taxonomy_id')
    ro = relationship('Ro')
    source = relationship('Source')


class TaxonomyUrl(Base):
    __tablename__ = 'taxonomy_url'
    __table_args__ = (
        UniqueConstraint('taxonomy_id', 'display_name', 'obj_url'),
        {'schema': 'nex'}
    )

    url_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.url_seq'::regclass)"))
    display_name = Column(String(500), nullable=False)
    obj_url = Column(String(500), nullable=False)
    source_id = Column(ForeignKey('nex.source.source_id', ondelete='CASCADE'), nullable=False, index=True)
    taxonomy_id = Column(ForeignKey('nex.taxonomy.taxonomy_id', ondelete='CASCADE'), nullable=False)
    url_type = Column(String(40), nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)

    source = relationship('Source')
    taxonomy = relationship('Taxonomy')


class Updatelog(Base):
    __tablename__ = 'updatelog'
    __table_args__ = {'schema': 'nex'}

    updatelog_id = Column(BigInteger, primary_key=True, server_default=text("nextval('nex.updatelog_seq'::regclass)"))
    bud_id = Column(Integer)
    tab_name = Column(String(60), nullable=False)
    col_name = Column(String(60), nullable=False)
    primary_key = Column(BigInteger, nullable=False)
    date_created = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp without time zone"))
    created_by = Column(String(12), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)


# should be valid genes (by standard name or systematic name) and should not be primary, additional, or review for same gene
def validate_tags(tags):
    extra_tag_list = ['regulation_information', 'ptm', 'homology_disease', 'gene_model', 'pathways', 'engineering', 'alleles']
    primary_obj = {}
    additional_obj = {}
    review_obj = {}
    extra_obj = {} # tracks if in extra topics and might add additional tag for that gene
    high_priority_obj = {}
    gene_ids = []
    has_reviews = False
    for tag in tags:
        name = tag['name']
        is_primary = Literatureannotation.is_primary_tag(name)
        is_additional = (name == 'additional_literature')
        is_reviews = (name == 'reviews')
        if is_reviews:
            has_reviews = True
        is_high_priority = (name == 'high_priority')
        genes = tag['genes'].strip()
        if len(genes):
            t_gene_ids = genes.split()
            for g in t_gene_ids:
                # try to uppercase gene names
                g = g.strip()
                if g == '':
                    continue
                if len(g) <= 6:
                    g = g.upper()
                if is_primary:
                    primary_obj[g] = True
                if is_additional:
                    additional_obj[g] = True
                if is_reviews:
                    review_obj[g] = True
                if name in extra_tag_list:
                    extra_obj[g] = True
                if is_high_priority:
                    high_priority_obj[g] = True
            gene_ids = gene_ids + t_gene_ids
        elif is_primary or is_additional:
            raise ValueError('Primary and additional tags must have genes.')
    # make sure no genes are repeated or shared among primary, additional, and review
    p_keys = list(primary_obj.keys())
    a_keys = list(additional_obj.keys())
    r_keys = list(review_obj.keys())
    if (has_reviews > 0 and (len(p_keys) + len(a_keys)) > 0):
        raise ValueError('Review tags are mutually exclusive with primary and additional tags.')
    unique_keys = set(p_keys + a_keys + r_keys)
    extra_keys = set(extra_obj.keys())
    high_priority_keys = set(high_priority_obj.keys())
    all_keys = list(set(list(unique_keys) + list(extra_keys) + list(high_priority_keys)))
    # upper_all_keys = [x.upper() for x in all_keys]
    if len(unique_keys) != (len(p_keys) + len(a_keys) + len(r_keys)):
        raise ValueError('The same gene can only be used as a primary tag, additional tag, or review.')
    # validate that all genes are proper identifiers
    valid_genes = DBSession.query(Locusdbentity.gene_name, Locusdbentity.systematic_name).filter(or_(Locusdbentity.display_name.in_(all_keys), (Locusdbentity.format_name.in_(all_keys)))).all()
    num_valid_genes = len(valid_genes)
    
    valid_identifiers = []
    for x in valid_genes:
        valid_identifiers.append(x[0])
        valid_identifiers.append(x[1])

    added = 0
    for x in all_keys:
        if x not in valid_identifiers:
            complex = DBSession.query(Dbentity).filter_by(subclass='COMPLEX', format_name=x).one_or_none()
            if complex is None:
                pathway = DBSession.query(Pathwaydbentity).filter_by(biocyc_id=x).one_or_none()
                if pathway is not None:
                    valid_identifiers.append(x)
                    added = added + 1
                else:
                    allele = DBSession.query(Alleledbentity).filter(Alleledbentity.display_name.ilike(x)).one_or_none()
                    if allele is not None:
                        valid_identifiers.append(x)
                        added = added + 1 
            else:
                valid_identifiers.append(x)
                added = added + 1
                
    num_valid_genes = num_valid_genes + added
    
    if num_valid_genes != len(all_keys):
        # get invalid gene identifiers
        try:
            invalid_identifiers = [x for x in all_keys if x not in valid_identifiers]
            invalid_identifiers = ', '.join(invalid_identifiers)
        except:
            invalid_identifiers = ''
        raise ValueError('Genes must be a space-separated list of valid genes by standard name or systematic name. Invalid identifier(s): ' + invalid_identifiers)
    # maybe modify "extra" tags: if homology/disease, PTM, or regulation for a gene and no public top for that gene, then add to additional information
    new_additional_genes = []
    for x in extra_keys:
        if x not in unique_keys:
            new_additional_genes.append(x)
    if len(new_additional_genes) and not has_reviews:
        new_additional_str = SEPARATOR.join(new_additional_genes)
        # see if additional tag exists, if not create it
        is_added_to_existing = False
        for x in tags:
            if x['name'] == 'additional_literature':
                x['genes'] = x['genes'] + SEPARATOR + new_additional_str
                is_added_to_existing = True
        if not is_added_to_existing:
            new_tag = {
                'name': 'additional_literature',
                'genes': new_additional_str,
                'comment': None
            }
            tags.append(new_tag)
    return tags

def convert_space_separated_pmids_to_list(str_pmids):
    if str_pmids == '' or str_pmids is None:
        return []
    str_pmids = ' '.join(str_pmids.split())# remove extra spaces
    str_list = str_pmids.split(SEPARATOR)
    int_list = [int(x) for x in str_list]
    return int_list

def get_transcript_so_id():
    so = DBSession.query(So).filter_by(display_name = 'primary transcript').one_or_none()
    return so.so_id

def map_id_species(id):
    if id.startswith('HGNC:'):
        return 'Homo sapiens'
    elif id.startswith('MGI:'):
        return 'Mus musculus'
    elif id.startswith('FB::'):
        return 'Drosophila melanogaster'
    elif id.startswith('RGD:'):
        return 'Rattus norvegicus'
    elif id.startswith('WB:'):
        return 'Caenorhabditis elegans'
    elif id.startswith('SGD:'):
        return 'Saccharomyces cerevisiae'
    elif id.startswith('ZFIN:'):
        return 'Danio rerio'
    else:
        return ''
