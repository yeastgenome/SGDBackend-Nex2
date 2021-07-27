import sys
from src.models import Locussummary
from scripts.loading.database_session import get_session
import logging

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

def update_data():

    nex_session = get_session()

    ### text
    # <i>about autophagy...</i> <p> <go:6914>Autophagy</go> is a highly conserved eukaryotic pathway for sequestering and transporting bulk <go:5737>cytoplasm</go>, including proteins and organelle material, to the <go:5764>lysosome</go> for degradation (reviewed in <reference:S000121825>). Upon starvation for nutrients such as carbon, nitrogen, sulfur, and various amino acids, or upon endoplasmic reticulum stress, cells initiate formation of a double-membrane vesicle, termed an <go:5776>autophagosome</go>, that mediates this process (<reference:S000046080>, <reference:S000046735>, reviewed in <reference:S000120212>). Approximately 30 autophagy-related (Atg) proteins have been identified in S. cerevisiae, 17 of which are essential for formation of the autophagosome (reviewed in <reference:S000122113>). Null mutations in most of these genes prevent induction of autophagy, and cells do not survive nutrient starvation; however, these mutants are viable in rich medium. Some of the Atg proteins are also involved in a constitutive biosynthetic process termed the <go:32258>cytoplasm-to-vacuole targeting (Cvt) pathway</go>, which uses autophagosomal-like vesicles for selective transport of hydrolases aminopeptidase I (<feature:S000001586>Lap4p</feature>) and alpha-mannosidase (<feature:S000003124>Ams1p</feature>) to the vacuole (<reference:S000057871>, <reference:S000086257>). <p> Autophagy proceeds via a multistep pathway (a summary diagram (http://www.mcdb.lsa.umich.edu/labs/klionsky/Autophagy%20overview.pdf >download pdf</a>) kindly provided by Dan Klionsky). First, nutrient availability is sensed by the <go:31931>TORC1 complex</go> and also cooperatively by protein kinase A and <feature:S000001248>Sch9p</feature> (<reference:S000123817>, <reference:S000061632>). Second, signals generated by the sensors are transmitted to the autophagosome-generating machinery comprised of the 17 Atg gene products. These 17 proteins collectively form the <go:407>pre-autophagosomal structure/phagophore assembly site (PAS)</go>. The PAS generates an <go:34045>isolation membrane</go> (IM), which expands and eventually fuses along the edges to complete autophagosome formation. At the vacuole the outer membrane of the autophagosome fuses with the vacuolar membrane and autophagic bodies are released, disintegrated, and their contents degraded for reuse in biosynthesis (<reference:S000068967> and reviewed in <reference:S000122113>).

    ### html
    # g proteins are also involved in a constitutive biosynthetic process termed the <a href="/go/32258">cytoplasm-to-vacuole targeting (Cvt) pathway</a>, which uses autophagosomal-like vesicles for selective transport of hydrolases aminopeptidase I (<a href="/locus/S000001586">Lap4p</a>) and alpha-mannosidase (<a href="/locus/S000003124">Ams1p</a>) to the vacuole (<reference:S000057871>, <reference:S000086257>). <p> Autophagy proceeds via a multistep pathway (a summary diagram (<a href=http://www.mcdb.lsa.umich.edu/labs/klionsky/Autophagy%20overview.pdf >download pdf</a>) kindly provided by Dan Klionsky). First, nutrient availability is sensed by the <a href="/go/31931">TORC1 complex</a> and also cooperatively by protein kinase A and <a href="/locus/S000001248">Sch9p</a> (<reference:S000123817>, <reference:S000061632>). Second, signals generated by the sensors are transmitted to the autophagosome-generating machinery comprised of the 17 Atg gene products. These 17 proteins collectively form the <a href="/go/407">pre-autophagosomal structure/phagophore assembly site (PAS)</a>. The PAS generates an <a href="/go/34045">isolation membrane</a> (IM), which expands and eventually fuses along the edges to complete autophagosome formation. At the vacuole the outer membrane of the autophagosome fuses with the vacuolar membrane and autophagic bodies are released, disintegrated, and their contents degraded for reuse in biosynthesis (<reference:S000068967> and reviewed in <reference:S000122113>).

    obsolete_goids = obsolete_list()
    bad_goid_to_good_id = old_to_new()

    fw1 = open("scripts/checking/data/text_before.txt", "w")
    fw2 = open("scripts/checking/data/text_after.txt", "w")
    fw3 = open("scripts/checking/data/html_before.txt", "w")
    fw4 = open("scripts/checking/data/html_after.txt", "w")
    
    all = nex_session.query(Locussummary).filter_by(summary_type='Gene').all()

    i = 0
    for x in all:
        text = x.text
        html = x.html

        has_bad_goid = 0
        for bad_goid in bad_goid_to_good_id:
            if "<go:" + bad_goid + ">" in text:
                has_bad_goid = 1
                good_goid = bad_goid_to_good_id[bad_goid]
                text = text.replace("<go:" + bad_goid + ">", "<go:" + good_goid + ">")
                html = html.replace('<a href="/go/' + bad_goid + '">', '<a href="/go/' + good_goid + '">')
            
        has_obsolete_goid = 0
        for goid in obsolete_goids:
            if "<go:" + goid + ">" in text:
                has_obsolete_goid = 1
                text = text.replace("<go:" + goid + ">", '')
            if '<a href="/go/' + goid + '">' in html:
                html = html.replace('<a href="/go/' + goid + '">', '')

        if has_bad_goid == 0 and has_obsolete_goid == 0:
            continue
                                    
        ## remove extra </go> in text and </a> in html
        if has_obsolete_goid > 0:
            pieces = text.split('</go>')
            text = ''
            for section in pieces:
                text = text + section
                if '<go:' in section:
                    text = text + "</go>"

            pieces = html.split('</a>')
            html = ''
            for section	in pieces:
                html = html + section
                if '<a href=' in section:
                    html = html + "</a>"

        fw1.write(x.text + "\n\n")
        fw2.write(text + "\n\n")
        fw3.write(x.html + "\n\n")
        fw4.write(html + "\n\n")

        i = i + 1
        x.text = text
        x.html = html
        nex_session.add(x)
        print (i)
        nex_session.commit()
                                    
def obsolete_list():

    return [ '60',
             '185',
             '200',
             '1129',
             '1190',
             '1191',
             '1300',
             '1302',
             '1308',
             '1320',
             '5623',
             '5724',
             '6987',
             '7068',
             '7126',
             '8565',
             '30817',
             '30818',
             '50662',
             '52100' ]

def old_to_new():

    return { '40':        '34755',
             '42':        '34067',
             '501':       '128',
             '784':       '781',
             '788':       '786',
             '799':       '796',
             '944':       '19843',
             '982':       '981',
             '1077':      '1228',
             '1078':      '1227',
             '1103':      '61629',
             '1135':      '3712',
             '4003':      '3678',
             '4004':      '3724',
             '4012':      '140326',
             '5086':      '5085',
             '5087':      '5085',
             '5088':      '5085',
             '5089':      '5085',
             '5090':      '5085',
             '5720':      '792',
             '6343':      '31507',
             '6461':      '65003',
             '6827':      '34755',
             '6830':      '71578',
             '6831':      '71578',
             '7050':      '51726',
             '7067':      '278',
             '8026':      '4386',
             '8105':      '8104',
             '8599':      '19888',
             '10107':     '1990573',
             '15088':     '5375',
             '15266':     '8320',
             '15684':     '6826',
             '16023':     '31410',
             '17137':     '31267',
             '31572':     '7095',
             '32947':     '60090',
             '42623':     '16887',
             '42787':     '6511',
             '43142':     '17116',
             '43234':     '32991' }  
        
if __name__ == '__main__':

    update_data()
