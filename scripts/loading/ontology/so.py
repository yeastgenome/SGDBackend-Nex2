from datetime import datetime
import sys
import os
import urllib
import importlib
importlib.reload(sys)  # Reload does the trick!
from src.models import Source, So, SoUrl, SoAlia, SoRelation, Ro
from scripts.loading.database_session import get_session
from scripts.loading.ontology import read_owl
                 
__author__ = 'sweng66'

## Created on May 2017
## This script is used to update SO ontology in NEX2.

# ontology_file = 'data/so.owl'
log_file = 'scripts/loading/ontology/logs/so.log'
ontology = 'SO'
src = 'SO'

CREATED_BY = os.environ['DEFAULT_USER']

def load_ontology(ontology_file):

    nex_session = get_session()

    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()])
    soid_to_so =  dict([(x.soid, x) for x in nex_session.query(So).all()])
    term_to_ro_id = dict([(x.display_name, x.ro_id) for x in nex_session.query(Ro).all()])
    
    so_id_to_alias = {}
    for x in nex_session.query(SoAlia).all():
        aliases = []
        if x.so_id in so_id_to_alias:
            aliases = so_id_to_alias[x.so_id]
        aliases.append((x.display_name, x.alias_type))
        so_id_to_alias[x.so_id] = aliases

    so_id_to_parent = {}
    for x in nex_session.query(SoRelation).all():
        parents = []
        if x.child_id in so_id_to_parent:
            parents = so_id_to_parent[x.child_id]
        parents.append(x.parent_id)
        so_id_to_parent[x.child_id] = parents


    ####################################
    fw = open(log_file, "w")
    
    is_sgd_term = {}
    data = read_owl(ontology_file, ontology)
    
    [update_log, to_delete_list] = load_new_data(nex_session, data, 
                                                 source_to_id, 
                                                 soid_to_so, 
                                                 term_to_ro_id['is a'],
                                                 so_id_to_alias,
                                                 so_id_to_parent,
                                                 fw)
    
    write_summary_and_send_email(fw, update_log, to_delete_list)
    
    nex_session.close()

    fw.close()


def load_new_data(nex_session, data, source_to_id, soid_to_so, ro_id, so_id_to_alias, so_id_to_parent, fw):

    active_soid = []
    update_log = {}
    for count_name in ['updated', 'added', 'deleted']:
        update_log[count_name] = 0

    relation_just_added = {}
    alias_just_added = {}
    for x in data:
        so_id = None
        if "SO:" not in x['id']:
            continue
        if x['id'] in soid_to_so:
            ## in database
            y = soid_to_so[x['id']]
            so_id = y.so_id
            if y.is_obsolete is True:
                y.is_obsolete = False
                nex_session.add(y)
                nex_session.flush()
                update_log['updated'] = update_log['updated'] + 1
                fw.write("The is_obsolete for " + x['id'] + " has been updated from " + str(y.is_obsolete) + " to " + 'False' + "\n")
            if x['term'] != y.display_name.strip():
                ## update term
                fw.write("The display_name for " + x['id'] + " has been updated from " + y.display_name + " to " + x['term'] + "\n")
                y.display_name = x['term']
                nex_session.add(y)
                nex_session.flush()
                update_log['updated'] = update_log['updated'] + 1
            if y.term_name is None or x['term_orig'] != y.term_name.strip():
                ## update term
                fw.write("The term_name for " + x['id'] + " has been updated from " + str(y.term_name) + " to " + x['term_orig'] + "\n")
                y.term_name = x['term_orig']
                nex_session.add(y)
                nex_session.flush()
                update_log['updated'] = update_log['updated'] + 1
            active_soid.append(x['id'])
        else:
            fw.write("NEW entry = " + x['id'] + " " + x['term'] + "\n")
            this_x = So(source_id = source_to_id[src],
                         format_name = x['id'],
                         soid = x['id'],
                         display_name = x['term'],
                         term_name = x['term_orig'],
                         description = x['definition'],
                         obj_url = '/so/' + x['id'],
                         is_obsolete = False,
                         created_by = CREATED_BY)
            nex_session.add(this_x)
            nex_session.flush()
            so_id = this_x.so_id
            update_log['added'] = update_log['added'] + 1

            ## add three URLs
            link_id = x['id'].replace(':', '_')
            insert_url(nex_session, source_to_id['MISO'], 'MISO', so_id,
                       'http://www.sequenceontology.org/miso/current_svn/term/'+x['id'],
                       fw)
            insert_url(nex_session, source_to_id['Ontobee'], 'Ontobee', so_id, 
                       'http://www.ontobee.org/ontology/SO?iri=http://purl.obolibrary.org/obo/'+link_id,
                       fw)
            insert_url(nex_session, source_to_id['BioPortal'], 'BioPortal', so_id,
                       'http://bioportal.bioontology.org/ontologies/SO/?p=classes&conceptid=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2F' + link_id,
                       fw)
            insert_url(nex_session, source_to_id['OLS'], 'OLS', so_id, 
                       'http://www.ebi.ac.uk/ols/ontologies/so/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2F' + link_id,
                       fw)

            ## add RELATIONS                                                                      
            for parent_soid in x['parents']:
                parent = soid_to_so.get(parent_soid)
                if parent is not None:
                    parent_id = parent.so_id
                    child_id = so_id
                    insert_relation(nex_session, source_to_id[src], parent_id, 
                                    child_id, ro_id, relation_just_added, fw)
            
            ## add ALIASES
            for (alias, alias_type) in x['aliases']:
                insert_alias(nex_session, source_to_id[src], alias, 
                             alias_type, so_id, alias_just_added, fw)

        ## update RELATIONS

        update_relations(nex_session, so_id, so_id_to_parent.get(so_id), x['parents'], 
                         source_to_id[src], soid_to_so, ro_id, relation_just_added, fw)
                    
        ## update ALIASES

        update_aliases(nex_session, so_id, so_id_to_alias.get(so_id), x['aliases'],
                       source_to_id[src], soid_to_so, alias_just_added, fw)
    
    to_delete = []
    for soid in soid_to_so:
        if soid in active_soid:
            continue
        x = soid_to_so[soid]
        if soid.startswith('NTR'):
            continue
        to_delete.append((soid, x.display_name))
        if x.is_obsolete is False:
            x.is_obsolete = True
            nex_session.add(x)
            nex_session.flush()
            update_log['updated'] = update_log['updated'] + 1
            fw.write("The is_obsolete for " + x.soid + " has been updated from " + str(x.is_obsolete) +" to " + 'True' + "\n")

    nex_session.commit()
 
    return [update_log, to_delete]


def update_aliases(nex_session, so_id, curr_aliases, new_aliases, source_id, soid_to_so, alias_just_added, fw):

    # print "ALIAS: ", curr_aliases, new_aliases
    # return

    if curr_aliases is None:
        curr_aliases = []
     
    for (alias, type) in new_aliases:
        if (alias, type) not in curr_aliases:
            insert_alias(nex_session, source_id, alias, type, so_id, alias_just_added, fw)

    for (alias, type) in curr_aliases:
        if(alias, type) not in new_aliases:
            ## remove the old one                                                             
            to_delete = nex_session.query(SoAlia).filter_by(so_id=so_id, display_name=alias, alias_type=type).first()
            nex_session.delete(to_delete) 
            fw.write("The old alias = " + alias + " has been deleted for so_id = " + str(so_id) + "\n")
             

def update_relations(nex_session, child_id, curr_parent_ids, new_parents, source_id, soid_to_so, ro_id, relation_just_added, fw):

    # print "RELATION: ", curr_parent_ids, new_parents
    # return 

    if curr_parent_ids is None:
        curr_parent_ids = []
    
    new_parent_ids = []
    for parent_soid in new_parents:
        parent = soid_to_so.get(parent_soid)
        if parent is not None:
            parent_id = parent.so_id
            new_parent_ids.append(parent_id)
            if parent_id not in curr_parent_ids:
                insert_relation(nex_session, source_id, parent_id, child_id, 
                                ro_id, relation_just_added, fw)

    for parent_id in curr_parent_ids:
        if parent_id not in new_parent_ids:
            ## remove the old one
            to_delete = nex_session.query(SoRelation).filter_by(child_id=child_id, parent_id=parent_id).first()
            nex_session.delete(to_delete)
            fw.write("The old parent: parent_id = " + str(parent_id) + " has been deleted for so_id = " + str(child_id)+ "\n")

def insert_url(nex_session, source_id, display_name, so_id, url, fw):
    
    # print url
    # return

    x = SoUrl(display_name = display_name,
               url_type = display_name,
               source_id = source_id,
               so_id = so_id,
               obj_url = url,
               created_by = CREATED_BY)
    nex_session.add(x)
    nex_session.flush()
    fw.write("Added new URL: " + url + " for so_id = " + str(so_id) + "\n")
    

def insert_alias(nex_session, source_id, display_name, alias_type, so_id, alias_just_added, fw):

    # print display_name
    # return

    if (so_id, display_name, alias_type) in alias_just_added:
        return

    alias_just_added[(so_id, display_name, alias_type)] = 1

    x = SoAlia(display_name = display_name,
                alias_type = alias_type,
                source_id = source_id,
                so_id = so_id,
                created_by = CREATED_BY)
    nex_session.add(x)
    nex_session.flush()
    fw.write("Added new ALIAS: " + display_name + " for so_id = " + str(so_id) + "\n")


def insert_relation(nex_session, source_id, parent_id, child_id, ro_id, relation_just_added, fw):
    
    # print "PARENT/CHILD: ", parent_id, child_id
    # return

    if (parent_id, child_id) in relation_just_added:
        return

    relation_just_added[(parent_id, child_id)] = 1

    x = SoRelation(parent_id = parent_id,
                    child_id = child_id,
                    source_id = source_id,
                    ro_id = ro_id,
                    created_by = CREATED_BY)
    nex_session.add(x)
    nex_session.flush()
    fw.write("Added new PARENT: parent_id = " + str(parent_id) + " for so_id = " + str(child_id) + "\n")
    

def write_summary_and_send_email(fw, update_log, to_delete_list):

    summary = "Updated: " + str(update_log['updated'])+ "\n"
    summary = summary + "Added: " + str(update_log['added']) + "\n"
    if len(to_delete_list) > 0:
        summary = summary + "The following SO terms are not in the current release:\n"
        for (soid, term) in to_delete_list:
            summary = summary + "\t" + soid + " " + term + "\n"
                                          
    fw.write(summary)

if __name__ == "__main__":
        
    url_path = 'https://raw.githubusercontent.com/The-Sequence-Ontology/SO-Ontologies/master/Ontology_Files/'
    owl_file = 'so.owl'
    urllib.request.urlretrieve(url_path + owl_file, owl_file)

    load_ontology(owl_file)


    
        
