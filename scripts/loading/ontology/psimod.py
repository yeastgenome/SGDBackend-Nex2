import urllib.request, urllib.parse, urllib.error
from datetime import datetime
import sys
import importlib
importlib.reload(sys)  # Reload does the trick!
import os

from src.models import Source, Psimod, PsimodUrl, PsimodRelation, Ro
from scripts.loading.database_session import get_session
from scripts.loading.ontology import read_obo
                 
__author__ = 'sweng66'

## Created on May 2017
## This script is used to update PSIMOD ontology in NEX2.

# ontology_file = 'data/PSI-MOD.obo'
log_file = 'scripts/loading/ontology/logs/psimod.log'
src = 'PSI'

CREATED_BY = os.environ['DEFAULT_USER']

def load_ontology(ontology_file):

    nex_session = get_session()

    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()])
    psimodid_to_psimod =  dict([(x.psimodid, x) for x in nex_session.query(Psimod).all()])
    term_to_ro_id = dict([(x.display_name, x.ro_id) for x in nex_session.query(Ro).all()])
    
    psimod_id_to_parent = {}
    for x in nex_session.query(PsimodRelation).all():
        parents = []
        if x.child_id in psimod_id_to_parent:
            parents = psimod_id_to_parent[x.child_id]
        parents.append(x.parent_id)
        psimod_id_to_parent[x.child_id] = parents


    ####################################
    fw = open(log_file, "w")
    
    data = read_obo(ontology_file)
    
    [update_log, to_delete_list] = load_new_data(nex_session, data, 
                                                 source_to_id, 
                                                 psimodid_to_psimod, 
                                                 term_to_ro_id['is a'],
                                                 psimod_id_to_parent,
                                                 fw)
    
    write_summary_and_send_email(fw, update_log, to_delete_list)
    
    nex_session.close()

    fw.close()


def load_new_data(nex_session, data, source_to_id, psimodid_to_psimod, ro_id, psimod_id_to_parent, fw):

    active_psimodid = []
    update_log = {}
    for count_name in ['updated', 'added', 'deleted']:
        update_log[count_name] = 0

    relation_just_added = {}
    for x in data:
        psimod_id = None
        if "MOD:" not in x['id']:
            continue
        if x['id'] in psimodid_to_psimod:
            ## in database
            y = psimodid_to_psimod[x['id']]
            psimod_id = y.psimod_id
            if y.is_obsolete is True:
                y.is_obsolete = 'false'
                nex_session.add(y)
                nex_session.flush()
                update_log['updated'] = update_log['updated'] + 1
                fw.write("The is_obsolete for " + x['id'] + " has been updated from " + y.is_obsolete + " to " + 'False' + "\n")
            if x['term'] != y.display_name:
                ## update term
                fw.write("The display_name for " + x['id'] + " has been updated from " + y.display_name + " to " + x['term'] + "\n")
                y.display_name = x['term']
                nex_session.add(y)
                nex_session.flush()
                update_log['updated'] = update_log['updated'] + 1
                # print "UPDATED: ", y.psimodid, y.display_name, x['term']
            # else:
            #    print "SAME: ", y.psimodid, y.display_name, x['definition'], x['aliases'], x['parents']
            active_psimodid.append(x['id'])
        else:
            fw.write("NEW entry = " + x['id'] + " " + x['term'] + "\n")
            this_x = Psimod(source_id = source_to_id[src],
                            format_name = x['id'],
                            psimodid = x['id'],
                            display_name = x['term'],
                            description = x['definition'],
                            obj_url = '/psimod/' + x['id'],
                            is_obsolete = 'false',
                            created_by = CREATED_BY)
            nex_session.add(this_x)
            nex_session.flush()
            psimod_id = this_x.psimod_id
            update_log['added'] = update_log['added'] + 1
            # print "NEW: ", x['id'], x['term'], x['definition']

            ## add three URLs
            link_id = x['id'].replace(':', '_')
            insert_url(nex_session, source_to_id['Ontobee'], 'Ontobee', psimod_id, 
                       'http://www.ontobee.org/ontology/PSIMOD?iri=http://purl.obolibrary.org/obo/'+link_id,
                       fw)
            insert_url(nex_session, source_to_id['BioPortal'], 'BioPortal', psimod_id,
                       'http://bioportal.bioontology.org/ontologies/PSIMOD/?p=classes&conceptid=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2F' + link_id,
                       fw)
            insert_url(nex_session, source_to_id['OLS'], 'OLS', psimod_id, 
                       'http://www.ebi.ac.uk/ols/ontologies/psimod/terms?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2F' + link_id,
                       fw)

            ## add RELATIONS                                                                      
            for parent_psimodid in x['parents']:
                parent = psimodid_to_psimod.get(parent_psimodid)
                if parent is not None:
                    parent_id = parent.psimod_id
                    child_id = psimod_id
                    insert_relation(nex_session, source_to_id[src], parent_id, 
                                    child_id, ro_id, relation_just_added, fw)
            
        ## update RELATIONS
        # print x['id'], "RELATION", psimod_id_to_parent.get(psimod_id), x['parents']

        update_relations(nex_session, psimod_id, psimod_id_to_parent.get(psimod_id), x['parents'], 
                         source_to_id[src], psimodid_to_psimod, ro_id, relation_just_added, fw)
                        
    to_delete = []
    for psimodid in psimodid_to_psimod:
        if psimodid in active_psimodid:
            continue
        x = psimodid_to_psimod[psimodid]
        if psimodid.startswith('NTR'):
            continue
        to_delete.append((psimodid, x.display_name))
        if x.is_obsolete is False:
            x.is_obsolete = 'true'
            nex_session.add(x)
            nex_session.flush()
            update_log['updated'] = update_log['updated'] + 1
            fw.write("The is_obsolete for " + x.psimodid + " has been updated from " + x.is_obsolete +" to " + 'True' + "\n")

    nex_session.commit()
 
    return [update_log, to_delete]


def update_relations(nex_session, child_id, curr_parent_ids, new_parents, source_id, psimodid_to_psimod, ro_id, relation_just_added, fw):

    # print "RELATION: ", curr_parent_ids, new_parents
    # return 

    if curr_parent_ids is None:
        curr_parent_ids = []
    
    new_parent_ids = []
    for parent_psimodid in new_parents:
        parent = psimodid_to_psimod.get(parent_psimodid)
        if parent is not None:
            parent_id = parent.psimod_id
            new_parent_ids.append(parent_id)
            if parent_id not in curr_parent_ids:
                insert_relation(nex_session, source_id, parent_id, child_id, 
                                ro_id, relation_just_added, fw)

    for parent_id in curr_parent_ids:
        if parent_id not in new_parent_ids:
            ## remove the old one
            to_delete = nex_session.query(PsimodRelation).filter_by(child_id=child_id, parent_id=parent_id).first()
            nex_session.delete(to_delete)
            fw.write("The old parent: parent_id = " + str(parent_id) + " has been deleted for psimod_id = " + str(child_id)+ "\n")

def insert_url(nex_session, source_id, display_name, psimod_id, url, fw):
    
    # print url
    # return

    x = PsimodUrl(display_name = display_name,
               url_type = display_name,
               source_id = source_id,
               psimod_id = psimod_id,
               obj_url = url,
               created_by = CREATED_BY)
    nex_session.add(x)
    nex_session.flush()
    fw.write("Added new URL: " + url + " for psimod_id = " + str(psimod_id) + "\n")
    

def insert_relation(nex_session, source_id, parent_id, child_id, ro_id, relation_just_added, fw):
    
    # print "PARENT/CHILD: ", parent_id, child_id
    # return

    if (parent_id, child_id) in relation_just_added:
        return

    relation_just_added[(parent_id, child_id)] = 1

    x = PsimodRelation(parent_id = parent_id,
                    child_id = child_id,
                    source_id = source_id,
                    ro_id = ro_id,
                    created_by = CREATED_BY)
    nex_session.add(x)
    nex_session.flush()
    fw.write("Added new PARENT: parent_id = " + str(parent_id) + " for psimod_id = " + str(child_id) + "\n")
    

def write_summary_and_send_email(fw, update_log, to_delete_list):

    summary = "Updated: " + str(update_log['updated'])+ "\n"
    summary = summary + "Added: " + str(update_log['added']) + "\n"
    if len(to_delete_list) > 0:
        summary = summary + "The following PSIMOD terms are not in the current release:\n"
        for (psimodid, term) in to_delete_list:
            summary = summary + "\t" + psimodid + " " + term + "\n"
                                          
    fw.write(summary)
    print(summary)


if __name__ == "__main__":
        
    url_path = 'https://raw.githubusercontent.com/HUPO-PSI/psi-mod-CV/master/'
    obo_file = 'PSI-MOD.obo'
    urllib.request.urlretrieve(url_path + obo_file, obo_file)
    
    load_ontology(obo_file)


    
        
