import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Locusdbentity, LocusUrl, Source
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

new_orfs = ['YLR379W-A', 'YMR008C-A', 'YJR107C-A', 'YKL104W-A', 'YGR227C-A', 'YHR052C-B', 'YHR054C-B']

other_new_features = ['RE301', 'YELWdelta27', 'YNCP0002W', 'YNCM0001W', 'YNCB0008W', 'YNCH0011W', 'YNCB0014W']

def update_data():

    nex_session = get_session()

    src = nex_session.query(Source).filter_by(display_name = 'SGD').one_or_none()
    source_id = src.source_id

    for name in new_orfs:
        locus = nex_session.query(Locusdbentity).filter_by(systematic_name=name).one_or_none()
        if locus is None:
            print ("The ORF: ", name, " is not in the database.")
            continue
        locus_id = locus.dbentity_id
        add_internal_common_links(nex_session, name, source_id, locus_id)
        add_orf_internal_links(nex_session, name, source_id, locus_id, locus.sgdid)
        add_external_links(nex_session, locus_id)

    for name in other_new_features:
        locus = nex_session.query(Locusdbentity).filter_by(systematic_name=name).one_or_none()
        if locus is None:
            print ("The ORF: ", name, " is not in the database.")
            continue
        add_internal_common_links(nex_session, name, source_id, locus.dbentity_id)
        
    nex_session.rollback()
    # nex_session.commit()

    nex_session.close()

    
def insert_locus_url(nex_session, display_name, obj_url, source_id, locus_id, url_type, placement):

    x = LocusUrl(display_name = display_name,
                 obj_url = obj_url,
                 source_id = source_id,
                 locus_id = locus_id,
                 url_type = url_type,
                 placement = placement,
                 created_by = 'OTTO')
    nex_session.add(x)

def add_internal_common_links(nex_session, name, source_id, locus_id):

    insert_locus_url(nex_session, 'BLASTN', '/blast-sgd?name=' + name,
                     source_id, locus_id, 'Systematic name', 'LOCUS_SEQUENCE_S288C')

    insert_locus_url(nex_session, 'BLASTN vs. fungi', '/blast-fungal?name=' + name,
                     source_id, locus_id, 'Systematic name', 'LOCUS_SEQUENCE_OTHER_SPECIES')

    insert_locus_url(nex_session, 'Design Primers', '/primer3?name=' + name,
                     source_id, locus_id, 'Systematic name', 'LOCUS_SEQUENCE_S288C')

    insert_locus_url(nex_session, 'Restriction Fragment Map', '/restrictionMapper?seqname=' + name,
                     source_id, locus_id, 'Systematic name', 'LOCUS_SEQUENCE_S288C')

    insert_locus_url(nex_session, 'Restriction Fragment Sizes', '/seqTools?seqname=' + name + '&emboss=restrict',
                     source_id, locus_id, 'Systematic name', 'LOCUS_SEQUENCE_S288C')

    insert_locus_url(nex_session, 'Yeast Phenotype Ontology', '/ontology/phenotype/ypo',
                     source_id, locus_id, 'Internal web service', 'LOCUS_PHENOTYPE_RESOURCES_ONTOLOGY')
    
def add_orf_internal_links(nex_session, name, source_id, locus_id, sgdid):

    insert_locus_url(nex_session, 'BLASTP', '/blast-sgd?name=' + name + '&type=protein',
                     source_id, locus_id, 'Systematic name', 'LOCUS_SEQUENCE_S288C')

    insert_locus_url(nex_session, 'BLASTP vs. fungi', '/blast-fungal?name=' + name + '&type=protein',
                     source_id, locus_id, 'Systematic name', 'LOCUS_SEQUENCE_OTHER_SPECIES')

    insert_locus_url(nex_session, 'Six-Frame Translation', '/seqTools?seqname=' + name + '&emboss=remap',
                     source_id, locus_id, 'Systematic name', 'LOCUS_SEQUENCE_S288C')

    # insert_locus_url(nex_session, 'Strain Alignment', '/strainAlignment?locus=' + name,
    #                source_id, locus_id, 'Systematic name', 'LOCUS_SEQUENCE_OTHER_SPECIES')

    insert_locus_url(nex_session, 'Variant Viewer', '/variant-viewer#/' + sgdid,
                     source_id, locus_id, 'SGDID', 'LOCUS_SEQUENCE_OTHER_STRAINS')

def add_external_links(nex_session, locus_id):

    insert_locus_url(nex_session, 'dHITS', 'https://www.dhitsmayalab.tk/firstPage.php',
                     1977606, locus_id, 'Systematic name', 'LOCUS_EXPRESSION_RESOURCES')

    insert_locus_url(nex_session, 'dHITS', 'https://www.dhitsmayalab.tk/firstPage.php',
                     1977606, locus_id,	'Systematic name', 'LOCUS_PHENOTYPE_RESOURCES_PHENOTYPE_RESOURCES')

    insert_locus_url(nex_session, 'dHITS', 'https://www.dhitsmayalab.tk/firstPage.php',
                     1977606, locus_id,	'Systematic name', 'LOCUS_PROTEIN_RESOURCES_LOCALIZATION')

    insert_locus_url(nex_session, 'DNASU Plasmids', 'https://dnasu.org/DNASU/Home.do',
                     760, locus_id, 'Systematic name', 'LOCUS_PHENOTYPE_RESOURCES_MUTANT_STRAINS')

    insert_locus_url(nex_session, 'ScreenTroll', 'http://www.rothsteinlab.com/tools/screenTroll',
                     833, locus_id, 'Systematic name', 'LOCUS_PHENOTYPE_RESOURCES_PHENOTYPE_RESOURCES')

    insert_locus_url(nex_session, 'YGRC', 'http://yeast.lab.nig.ac.jp/yeast/byPlasmidAllItemsList.jsf',
                     861, locus_id, 'Systematic name', 'LOCUS_PHENOTYPE_RESOURCES_MUTANT_STRAINS')
    
if __name__ == '__main__':

    update_data()
