import logging
import os
from datetime import datetime
import sys
from src.models import Tools
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

CREATED_BY = os.environ['DEFAULT_USER']
STATUS = 'Current'

def load_data():

    nex_session = get_session()

    all_links = get_links()
    
    for link in all_links:
        (display_name, link_url, index_key) = link
        insert_tools(nex_session, display_name, link_url, index_key)

    nex_session.commit()
    
    nex_session.close()

    
def insert_tools(nex_session, display_name, link_url, index_key):

    x = Tools(format_name = display_name.replace(' ', '_'),
              display_name = display_name,
              link_url = link_url,
              index_key = index_key,
              status = STATUS,
              created_by = CREATED_BY)

    nex_session.add(x)

    
def get_links():

    return [
        ("Gene List", "https://yeastmine.yeastgenome.org/yeastmine/bag.do", ''),
        ("Yeastmine", "https://yeastmine.yeastgenome.org", "yeastmine"),
        ("Submit Data", "/submitData", ''),
        ("SPELL", "https://spell.yeastgenome.org", "spell"),
        ("BLAST", "/blast-sgd", "blast"),
        ("Fungal BLAST", "/blast-fungal", "blast"),
        ("Pattern Matching", "/nph-patmatch", ''),
        ("Design Primers", "/primer3", ''),
        ("Restriction Mapper", "/restrictionMapper", ''),
        ("Genome Browser", "https://browse.yeastgenome.org", ''),
        ("Gene/Sequence Resources", "/seqTools", ''),
        ("Download Genome", "https://downloads.yeastgenome.org/sequence/S288C_reference/genome_releases/", "download"),
        ("Genome Snapshot", "/genomesnapshot", ''),
        ("Chromosome History", "https://wiki.yeastgenome.org/index.php/Summary_of_Chromosome_Sequence_and_Annotation_Updates", ''),
        ("Systematic Sequencing Table", "/cache/chromosomes.shtml", ''),
        ("Original Sequence Papers",
         "http://wiki.yeastgenome.org/index.php/Original_Sequence_Papers", ''),
        ("Variant Viewer", "/variant-viewer", ''),
        ("GO Term Finder", "/goTermFinder", "go"),
        ("GO Slim Mapper", "/goSlimMapper", "go"),
        ("GO Slim Mapping File",
         "https://downloads.yeastgenome.org/curation/literature/go_slim_mapping.tab", "go"),
        ("Expression", "https://spell.yeastgenome.org/#", ''),
        ("Biochemical Pathways", "http://pathway.yeastgenome.org/", ''),
        ("Browse All Phenotypes", "/ontology/phenotype/ypo", ''),
        ("Interactions", "/interaction-search", ''),
        ("YeastGFP", "https://yeastgfp.yeastgenome.org/", "yeastgfp"),
        ("Full-text Search", "http://textpresso.yeastgenome.org/", "texxtpresso"),
        ("New Yeast Papers", "/reference/recent", ''),
        ("Genome-wide Analysis Papers",
         "https://yeastmine.yeastgenome.org/yeastmine/loadTemplate.do?name=GenomeWide_Papers&scope=all&method=results&format=tab", ''),
        ("Find a Colleague", "/search?q=&category=colleague", ''),
        ("Add or Update Info", "/colleague_update", ''),
        ("Career Resources", "http://wiki.yeastgenome.org/index.php/Career_Resources", ''),
        ("Future", "http://wiki.yeastgenome.org/index.php/Meetings#Upcoming_Conferences_.26_Courses", ''),
        ("Yeast Genetics", "http://wiki.yeastgenome.org/index.php/Meetings#Past_Yeast_Meetings", ''),
        ("Submit a Gene Registration", "/reserved_name/new", ''),
        ("Nomenclature Conventions",
         "https://sites.google.com/view/yeastgenome-help/community-help/nomenclature-conventions", ''),
        ("Strains and Constructs", "http://wiki.yeastgenome.org/index.php/Strains", ''),
        ("Reagents", "http://wiki.yeastgenome.org/index.php/Reagents", ''),
        ("Protocols and Methods", "http://wiki.yeastgenome.org/index.php/Methods", ''),
        ("Physical & Genetic Maps",
         "http://wiki.yeastgenome.org/index.php/Combined_Physical_and_Genetic_Maps_of_S._cerevisiae", ''),
        ("Genetic Maps", "http://wiki.yeastgenome.org/index.php/Yeast_Mortimer_Maps_-_Edition_12", ''),
        ("Sequence", "http://wiki.yeastgenome.org/index.php/Historical_Systematic_Sequence_Information", ''),
        ("Wiki", "http://wiki.yeastgenome.org/index.php/Main_Page", "wiki"),
        ("Resources", "http://wiki.yeastgenome.org/index.php/External_Links", '')
    ]


if __name__ == "__main__":

    load_data()
