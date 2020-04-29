from datetime import datetime
import os
import sys
from src.models import Source, Locusdbentity, Taxonomy, Proteinsequenceannotation, \
                       ProteinsequenceDetail, Contig
from scripts.loading.database_session import get_session
from scripts.loading.util import get_strain_taxid_mapping

__author__ = 'sweng66'

CREATED_BY = os.environ['DEFAULT_USER']

data_file = 'scripts/loading/NISS/data/NISSpilotSet102119_protparam.txt'
log_file = 'scripts/loading/NISS/logs/NISSpilotSet102119_protparam.log'

def load_data():

    nex_session = get_session()

    fw = open(log_file, "w")
    
    read_data_and_update_database(nex_session, fw)

    nex_session.close()

    fw.close()

def read_data_and_update_database(nex_session, fw):

    taxon_to_taxonomy_id = dict([(x.taxid, x.taxonomy_id) for x in nex_session.query(Taxonomy).all()])
    name_to_dbentity_id = dict([(x.systematic_name, x.dbentity_id) for x in nex_session.query(Locusdbentity).all()])
    contig_to_contig_id = dict([(x.format_name, x.contig_id) for x in nex_session.query(Contig).all()])
    key_to_annotation_id =  dict([((x.dbentity_id, x.taxonomy_id, x.contig_id), x.annotation_id) for x in nex_session.query(Proteinsequenceannotation).all()])

    f = open(data_file)

    strain_to_taxon_mapping = get_strain_taxid_mapping()
    
    header = None
    for line in f:
        pieces = line.strip().split("\t")
        if pieces[0] == 'name':
            header = pieces[3:]
            continue
        name = pieces[0]
        dbentity_id = name_to_dbentity_id.get(name)
        if dbentity_id is None:
            print (name + " is not in the database")
        strain = pieces[1]
        taxon = strain_to_taxon_mapping.get(strain)
        if taxon is None:
            print ("The strain = " + strain + " is not in the mapping module.")
            continue
        taxonomy_id = taxon_to_taxonomy_id.get(taxon)
        if taxonomy_id is None:
            print ("The taxid = " + taxon + " is not in the database.")
            continue
        contig = pieces[2]
        contig_id = contig_to_contig_id.get(contig)
        if contig_id is None:
            print (contig + " is not in the database.")
            continue
        annotation_id = key_to_annotation_id.get((dbentity_id, taxonomy_id, contig_id))
        if annotation_id is None:
            print ((dbentity_id, taxonomy_id, contig_id) + " is not in the database.")
            continue
           
        data = pieces[3:]

        insert_proteinsequence_detail(nex_session, fw, annotation_id, data, header)

    f.close()
    
    # nex_session.rollback()
    nex_session.commit()

def insert_proteinsequence_detail(nex_session, fw, annotation_id, data, header):
    
    i = 0
    mapping = {}
    for name in header:
        mapping[header[i]] = data[i]
        i = i + 1

    x = ProteinsequenceDetail(annotation_id = annotation_id,
                              molecular_weight = mapping['MW'],
                              protein_length = mapping['protein_length'],
                              n_term_seq = mapping['n_term_seq'],
                              c_term_seq = mapping['c_term_seq'],
                              pi = mapping['pI'],
                              cai = mapping['cai'],
                              codon_bias = mapping['codon_bias'],
                              fop_score = mapping['fop_score'],
                              gravy_score = mapping['gravy_score'],
                              aromaticity_score = mapping['aromaticity_score'],
                              aliphatic_index = mapping['aliphatic_index'],
                              instability_index = mapping['instability_index'],
                              ala = mapping['ala'],
                              arg = mapping['arg'],
                              asn = mapping['asn'],
                              asp = mapping['asp'],
                              cys = mapping['cys'],
                              gln = mapping['gln'],
                              glu = mapping['glu'],
                              gly = mapping['gly'],
                              his = mapping['his'],
                              ile = mapping['ile'],
                              leu = mapping['leu'],
                              lys = mapping['lys'],
                              met = mapping['met'],
                              phe = mapping['phe'],
                              pro = mapping['pro'],
                              ser = mapping['ser'],
                              thr = mapping['thr'],
                              trp = mapping['trp'],
                              tyr = mapping['tyr'],
                              val = mapping['val'],
                              hydrogen = mapping['Hydrogen'],
                              sulfur = mapping['Sulfur'],
                              nitrogen = mapping['Nitrogen'],
                              oxygen = mapping['Oxygen'],
                              carbon = mapping['Carbon'],
                              no_cys_ext_coeff = mapping['no_cys_ext_coeff'],
                              all_cys_ext_coeff = mapping['all_cys_ext_coeff'],
                              created_by = CREATED_BY)

    nex_session.add(x)

    fw.write("Insert new protein detail for annotation_id=" + str(annotation_id) + "\n")
    
if __name__ == "__main__":
        
    load_data()


    
        
