import os
import sys
from src.models import Source, Proteindomain, ProteindomainUrl, Proteindomainannotation
from scripts.loading.database_session import get_session
                 
__author__ = 'sweng66'

## Created on June 2017
## This script is used to update protein domains in NEX2.

# domain_file = 'scripts/loading/protein_domain/data/orf_trans_all.fasta_full.tvs'
domain_file = 'scripts/loading/protein_domain/data/unique_domain_data.txt'
log_file = 'scripts/loading/protein_domain/logs/protein_domain.log'

CREATED_BY = os.environ['DEFAULT_USER']

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

    inNew = {}
    for line in f:
        items = line.strip().split("\t")
        format_name = items[0]
        display_name = items[1]
        source = items[2]
        interpro_id = items[3]
        desc = items[4]                
        source_id = source_to_id.get(source)
        if source_id is None:
            print("SOURCE:", source, " is not in the database.")
            continue

        inNew[format_name] = 1
        
        x = format_name_to_domain.get(format_name)

        if x is None:
            proteindomain_id = insert_new_domain(nex_session, fw, format_name,
                                                 display_name, source_id, 
                                                 interpro_id, desc)
            insert_url(nex_session, fw, display_name, source, proteindomain_id, 
                       source_id)
            nex_session.commit()
        else:            
            if x.interpro_id != interpro_id or x.description != desc:
                x.interpro_id = interpro_id
                x.description = desc
                nex_session.add(x)
                nex_session.commit()
                fw.write("Update: " + format_name + "\n")

                
    f.close()

    ## comment out so it won't delete the domains for other strains
    # delete_old_domains(nex_session, fw, format_name_to_domain, inNew)


def delete_old_domains(nex_session, fw, format_name_to_domain, inNew):

    for key in format_name_to_domain:
        if key in inNew:
            continue
        x = format_name_to_domain[key]
        nex_session.query(ProteindomainUrl).filter_by(proteindomain_id=x.proteindomain_id).delete()
        nex_session.query(Proteindomainannotation).filter_by(proteindomain_id=x.proteindomain_id).delete()
        nex_session.delete(x)
        nex_session.commit()

        fw.write("Delete domain: " + key + "\n")


def insert_new_domain(nex_session, fw, format_name, display_name, source_id, interpro_id, desc):

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

    return x.proteindomain_id


def insert_url(nex_session, fw, display_name, source, proteindomain_id, source_id):
    
    link = None
    if source == 'SMART':
        link = "http://smart.embl-heidelberg.de/smart/do_annotation.pl?DOMAIN=" + display_name
    elif source == 'Pfam':
        link = "http://pfam.xfam.org/family/" + display_name
    elif source == 'GENE3D' or source == 'Gene3D':
        source = 'GENE3D'
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
    elif source == 'PROSITE':
        link = "http://prosite.expasy.org/cgi-bin/prosite/nicesite.pl?" + display_name 
    elif source == 'HAMAP':
        link = "http://hamap.expasy.org/profile/" + display_name
    if link is not None:
        x = ProteindomainUrl(display_name = display_name,
                             obj_url = link,
                             source_id = source_id,
                             proteindomain_id = proteindomain_id,
                             url_type = source,
                             created_by = CREATED_BY)
        nex_session.add(x)        
        
        fw.write("Add URL: " + link + " for " + display_name + "\n")

if __name__ == "__main__":
        
    load_domains()


    
        
