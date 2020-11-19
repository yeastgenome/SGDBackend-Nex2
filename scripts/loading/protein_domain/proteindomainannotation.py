import os
import sys
from src.models import Source, Proteindomain, Locusdbentity, Taxonomy, \
                       Proteindomainannotation
from scripts.loading.database_session import get_session
                 
__author__ = 'sweng66'


domain_file = 'scripts/loading/protein_domain/data/orf_trans_all.fasta_full.tvs'
log_file = 'scripts/loading/protein_domain/logs/protein_domain_annotation.log'

CREATED_BY = os.environ['DEFAULT_USER']

## This script is used to update protein domains and their annotations in NEX2 for reference genome.

taxid = "TAX:559292"
today = "2020-11-18"

def load_domain_annotations():

    nex_session = get_session()

    fw = open(log_file, "w")
    
    read_data_and_update_database(nex_session, fw)

    nex_session.close()

    fw.close()

def read_data_and_update_database(nex_session, fw):

    ipr = nex_session.query(Source).filter_by(format_name='InterPro').one_or_none()
    taxon = nex_session.query(Taxonomy).filter_by(taxid=taxid).one_or_none() 
    name_to_dbentity_id = dict([(x.systematic_name, x.dbentity_id) for x in nex_session.query(Locusdbentity).all()])
    format_name_to_id =  dict([(x.format_name, x.proteindomain_id) for x in nex_session.query(Proteindomain).all()])
    
    source_id = ipr.source_id
    taxonomy_id = taxon.taxonomy_id

    key_to_annotation = {}
    for x in nex_session.query(Proteindomainannotation).filter_by(taxonomy_id=taxonomy_id).all():
        key = (x.dbentity_id, x.proteindomain_id, x.start_index, x.end_index)
        key_to_annotation[key] = x

    f = open(domain_file)

    key_in_new = {}
    
    i = 0
    for line in f:
        items = line.strip().split("\t")
        dbentity_id = name_to_dbentity_id.get(items[0])
        if dbentity_id is None:
            print("The systematic_name: ", items[0], " is not in the database.")
            continue
        format_name = items[4].replace(' ', '_')
        proteindomain_id = format_name_to_id.get(format_name)
        if proteindomain_id is None:
            print("The domain name:", format_name, " is not in the PROTEINDOMAIN table.")
            continue
        start = int(items[6])
        end = int(items[7])
        key = (dbentity_id, proteindomain_id, start, end)
        if key not in key_to_annotation:
            print ("NEW: ", items[0], format_name, (dbentity_id, proteindomain_id, start, end))
            i = i + 1
            insert_annotation(nex_session, fw, dbentity_id, proteindomain_id,
                              source_id, taxonomy_id, start, end)
            if i > 500:
                nex_session.commit()
                i = 0

        key_in_new[key] = 1
        
    f.close()

    
    delete_annotations(nex_session, fw, key_to_annotation, key_in_new)

    nex_session.commit()


def delete_annotations(nex_session, fw, key_to_annotation, key_in_new):

    i = 0
    for key in key_to_annotation:
        if key in key_in_new:
            continue
        i = i + 1
        x = key_to_annotation[key]
        nex_session.delete(x)
        if i > 500:
            nex_session.commit()
            i = 0
        fw.write("Delete old annotation for dbentity_id=" + str(x.dbentity_id) + ", proteindomain_id=" + str(x.proteindomain_id) + ", start_index=" + str(x.start_index) + ", end_index=" + str(x.end_index) + "\n")

    nex_session.commit()


def insert_annotation(nex_session, fw, dbentity_id, proteindomain_id, source_id, taxonomy_id, start, end):

    x = Proteindomainannotation(dbentity_id = dbentity_id,
                                taxonomy_id = taxonomy_id,
                                source_id = source_id,
                                proteindomain_id = proteindomain_id,
                                start_index = start, 
                                end_index = end,
                                date_of_run = today,
                                created_by = CREATED_BY)

    nex_session.add(x)
    # nex_session.commit()

    fw.write("Insert new annotation for dbentity_id=" + str(dbentity_id) + ", proteindomain_id=" + str(proteindomain_id) + ", start_index=" + str(start) + ", end_index=" + str(end) + "\n")

    
if __name__ == "__main__":
        
    load_domain_annotations()


    
        
