from datetime import datetime
import sys
import os
from src.models import Source, Proteindomain, ProteindomainUrl
from scripts.loading.database_session import get_session
                 
__author__ = 'sweng66'

## Created on June 2017
## This script is used to update protein domains in NEX2.

CREATED_BY = os.environ['DEFAULT_USER']

domain_file = 'scripts/loading/protein_domain/data/orf_trans_all.fasta.tsv'
log_file = 'scripts/loading/protein_domain/logs/protein_domain.log'

def load_domains():

    nex_session = get_session()

    fw = open(log_file, "w")
    
    read_data_and_update_database(nex_session, fw)

    nex_session.close()

    fw.close()


def read_data_and_update_database(nex_session, fw):
    
    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()])
    format_name_to_domain =  dict([(x.format_name, x) for x in nex_session.query(Proteindomain).all()])

    f = open(domain_file)

    found = {}
    count = 0
    for line in f:
        items = line.strip().split("\t")
        display_name = items[4]
        format_name = display_name.replace(' ', '_')
        domain_name = items[5]
        if format_name in found:
            continue
        found[format_name] = 1

        source = items[3]
        if source in ['ProSiteProfiles', 'ProSitePatterns']:
            source = 'PROSITE'
        if source in ['FunFam', 'GENE3D']:
            source = 'Gene3D'
        if source == 'NCBIfam':
            source = 'CDD'
        if source == 'Hamap':
            source = 'HAMAP'
        source_id = source_to_id.get(source)
        # if source_id is None:
        if source_id is None:
            print ("SOURCE:", source, " is not in the database.")
            continue
            
        interpro_id = ""
        desc = ""
        if len(items) > 11:
            interpro_id = items[11]
        if len(items) > 12:
            desc = items[12]
        if desc == '' or desc == '-':
            desc = domain_name

        x = format_name_to_domain.get(format_name)
        
        if x is None:
            print ("not in DB:", format_name, display_name, source, source_id)
            proteindomain_id = insert_new_domain(nex_session, fw, format_name,
                                                 display_name, source_id, 
                                                 interpro_id, desc)
            if proteindomain_id:
                status = insert_url(nex_session, fw, display_name, source,  proteindomain_id, 
                                    source_id)
                if status:
                    nex_session.commit()
                else:
                    nex_session.rollback()
        else:            
            print ("in DB:", format_name, display_name, source, source_id)
            if x.interpro_id != interpro_id or x.description != desc:
                x.interpro_id = interpro_id
                x.description = desc
                nex_session.add(x)
                count += 1
                if count % 250 == 0:
                    nex_session.commit()
                fw.write("Update domain: " + display_name + "\n")
                
    f.close()

def insert_new_domain(nex_session, fw, format_name, display_name, source_id, interpro_id, desc):

    proteindomain_id = None
    try:
        x = Proteindomain(display_name = display_name,
                          format_name = format_name,
                          source_id = source_id,
                          obj_url = '/domain/' + display_name.replace(' ', '_'),
                          interpro_id = interpro_id,
                          description = desc,
                          created_by = CREATED_BY)
        nex_session.add(x)
        nex_session.flush()
        nex_session.refresh(x)
        fw.write("Insert new domain: " + display_name + "\n")
        proteindomain_id = x.proteindomain_id
    except Exception as e:
        fw.write("Error inserting new domain: " + display_name + ". error = " + str(e) + "\n")
        
    return proteindomain_id

def insert_url(nex_session, fw, display_name, source, proteindomain_id, source_id):
    
    link = None
    if source == 'SMART':
        link = "http://smart.embl-heidelberg.de/smart/do_annotation.pl?DOMAIN=" + display_name
    elif source == 'Pfam':
        link = "http://pfam.xfam.org/family/" + display_name
    elif source in ['GENE3D', 'Gene3D', 'FunFam']:
        source = 'GENE3D'
        linkID = display_name[6:].split(':FF:')[0]
        link = "http://www.cathdb.info/version/latest/superfamily/" + display_name[6:]
    elif source == 'SUPERFAMILY':
        link = "http://supfam.org/SUPERFAMILY/cgi-bin/scop.cgi?ipid=" + display_name
    elif source == 'PANTHER':
        link = "http://www.pantherdb.org/panther/family.do?clsAccession=" + display_name
    elif source == 'TIGRFAM':
        link = "http://www.jcvi.org/cgi-bin/tigrfams/HmmReportPage.cgi?acc=" + display_name
    elif source == 'PRINTS':
        link = "http:////www.bioinf.man.ac.uk/cgi-bin/dbbrowser/sprint/searchprintss.cgi?display_opts=Prints&amp;category=None&amp;queryform=false&amp;prints_accn=" + display_name
    elif source == 'ProDom':
        link = "http://prodom.prabi.fr/prodom/current/cgi-bin/request.pl?question=DBEN&amp;query=" + display_name
    elif source == 'PIRSF':
        link = "http://pir.georgetown.edu/cgi-bin/ipcSF?id=" + display_name
    elif source in ['PROSITE', 'ProSiteProfiles', 'ProSitePatterns']:
        link = "http://prosite.expasy.org/cgi-bin/prosite/nicesite.pl?" + display_name 
    elif source == 'HAMAP':
        link = "http://hamap.expasy.org/profile/" + display_name
    elif source == 'CDD':
        link = "https://www.ncbi.nlm.nih.gov/Structure/cdd/" + display_name
    if link is not None:
        try:
            x = ProteindomainUrl(display_name = display_name,
                                 obj_url = link,
                                 source_id = source_id,
                                 proteindomain_id = proteindomain_id,
                                 url_type = source,
                                 created_by = CREATED_BY)
            nex_session.add(x)        
            fw.write("Add URL: " + link + " for " + display_name + "\n")
            return True
        except Exception as e:
            fw.write("Error adding " + link + " for " + display_name + ". error=" + str(e) + "\n")
            return False
    
if __name__ == "__main__":
        
    load_domains()


    
        
