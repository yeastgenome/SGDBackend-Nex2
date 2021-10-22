from sqlalchemy import func, distinct
import sys
from src.models import Go, Goannotation, GoRelation, Goslim, Locusdbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

yeastGoSlimFile = 'scripts/loading/goslim/data/yeastGoSlimAnnot.txt'
genericGoSlimFile = 'scripts/loading/goslim/data/genericGoSlimAnnot.txt'
complexGoSlimFile = 'scripts/loading/goslim/data/complexGoSlimAnnot.txt'

datafile = 'scripts/loading/goslim/data/goslimannotation_data_all.txt'

def process_data():

    nex_session = get_session()

    goslim_id_to_go_id =  dict([(x.goslim_id, x.go_id) for x in nex_session.query(Goslim).all()])
    go_id_to_term_aspect =  dict([(x.go_id, (x.display_name, x.go_namespace)) for x in nex_session.query(Go).all()])

    nex_session.close()
    
    found_gene_go_pair = {}
    gene_to_root_process = {}
    gene_to_root_function = {}
    gene_to_root_component = {}
    found_gene_aspect = {}

    write_data('yeast', goslim_id_to_go_id, go_id_to_term_aspect, found_gene_go_pair,
               gene_to_root_process, gene_to_root_function, gene_to_root_component,
               found_gene_aspect)
    write_data('generic', goslim_id_to_go_id, go_id_to_term_aspect, found_gene_go_pair,
               gene_to_root_process, gene_to_root_function, gene_to_root_component,
               found_gene_aspect)

    write_data('complex', goslim_id_to_go_id, go_id_to_term_aspect, found_gene_go_pair,
               gene_to_root_process, gene_to_root_function, gene_to_root_component,
               found_gene_aspect)
    
def write_data(goSlimType, goslim_id_to_go_id, go_id_to_term_aspect, found_gene_go_pair, gene_to_root_process, gene_to_root_function, gene_to_root_component, found_gene_aspect):

    if goSlimType == 'yeast':
        f = open(yeastGoSlimFile)
        fw = open(datafile, 'w')
    elif goSlimType == 'generic':
        f = open(genericGoSlimFile)
        fw = open(datafile, 'a')
    else:
        f = open(complexGoSlimFile)
        fw = open(datafile, 'a')
        
    for line in f:
        items = line.strip().split("\t")
        gene = items[0]
        dbentity_id = items[1]
        goslim_id = int(items[2])
        go_id = goslim_id_to_go_id[goslim_id]
        display_name = items[4]
        line = "\t".join(items[0:4])
        if goSlimType == 'yeast':
            found_gene_go_pair[(dbentity_id, go_id)] = 1
        elif goSlimType == 'generic':
            if (dbentity_id, go_id) in found_gene_go_pair:
                continue
            else:
                found_gene_go_pair[(dbentity_id, go_id)] = 1
        else:
            if (dbentity_id, go_id) in found_gene_go_pair:
                continue
        if display_name in ['molecular_function', 'molecular function']:
            if dbentity_id not in gene_to_root_function:
                gene_to_root_function[dbentity_id] = line
        elif display_name in ['cellular_component', 'cellular component']:
            if dbentity_id not in gene_to_root_component:
                gene_to_root_component[dbentity_id] = line
        elif display_name in ['biological_process', 'biological process']:
            if dbentity_id not in gene_to_root_process:
                gene_to_root_process[dbentity_id] = line
        else:
            (go_term, aspect) = go_id_to_term_aspect[go_id]
            if aspect == 'molecular function':
                found_gene_aspect[(dbentity_id, 'F')] = 1
            elif aspect == 'cellular component':
                found_gene_aspect[(dbentity_id, 'C')] =	1
            else:
                found_gene_aspect[(dbentity_id, 'P')] = 1
            fw.write(line + "\t" + go_term + "\t" + aspect +  "\n")
                
    f.close()

    if goSlimType in ['yeast', 'generic']:
        fw.close()
        return
    
    for dbentity_id in gene_to_root_function:
        if (dbentity_id, 'F') not in found_gene_aspect:
            fw.write(gene_to_root_function[dbentity_id] + "\t" + "molecular function"  + "\n")

    for	dbentity_id in gene_to_root_process:
        if (dbentity_id, 'P') not in found_gene_aspect:
            fw.write(gene_to_root_process[dbentity_id] + "\t" + "biological process" + "\n")

    for	dbentity_id in gene_to_root_component:
        if (dbentity_id, 'C') not in found_gene_aspect:
            fw.write(gene_to_root_component[dbentity_id] + "\t" + "cellular component" + "\n")
            
    fw.close()
    
if __name__ == '__main__':

    process_data()
