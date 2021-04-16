from datetime import datetime
import os
import sys
from src.models import Source, Locusdbentity, Taxonomy, Proteinsequenceannotation, \
                       ProteinsequenceDetail, Contig
from scripts.loading.database_session import get_session
from scripts.loading.util import get_strain_taxid_mapping

__author__ = 'sweng66'

CREATED_BY = os.environ['DEFAULT_USER']

data_file = 'scripts/loading/sequence/data/newUpdated_protparam_R64-3.txt'
log_file = 'scripts/loading/sequence/logs/newUpdated_protparam_R64-3.log'

taxid = "TAX:559292"

def load_data():

    nex_session = get_session()

    fw = open(log_file, "w")
    
    read_data_and_update_database(nex_session, fw)

    nex_session.close()

    fw.close()

def read_data_and_update_database(nex_session, fw):

    taxon = nex_session.query(Taxonomy).filter_by(taxid=taxid).one_or_none()
    taxonomy_id = taxon.taxonomy_id
    name_to_dbentity_id = dict([(x.systematic_name, x.dbentity_id) for x in nex_session.query(Locusdbentity).all()])
    key_to_annotation_id =  dict([((x.dbentity_id, x.taxonomy_id), x.annotation_id) for x in nex_session.query(Proteinsequenceannotation).all()])

    f = open(data_file)
    
    header = None
    for line in f:
        pieces = line.strip().split("\t")
        if pieces[0] == 'name':
            header = pieces[1:]
            continue
        name = pieces[0]
        dbentity_id = name_to_dbentity_id.get(name)
        if dbentity_id is None:
            print (name + " is not in the database")
        annotation_id = key_to_annotation_id.get((dbentity_id, taxonomy_id))
        if annotation_id is None:
            print ((dbentity_id, taxonomy_id) + " is not in the database.")
            continue
           
        data = pieces[1:]

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

    psd = nex_session.query(ProteinsequenceDetail).filter_by(annotation_id=annotation_id).one_or_none()
    if psd is not None:
        psd.molecular_weight = mapping['MW']
        psd.protein_length = mapping['protein_length']
        psd.n_term_seq = mapping['n_term_seq']
        psd.c_term_seq = mapping['c_term_seq']
        psd.pi = mapping['pI']
        psd.cai = mapping['cai']
        psd.codon_bias = mapping['codon_bias']
        psd.fop_score = mapping['fop_score']
        psd.gravy_score = mapping['gravy_score']
        psd.aromaticity_score = mapping['aromaticity_score']
        psd.aliphatic_index = mapping['aliphatic_index']
        psd.instability_index = mapping['instability_index']
        psd.ala = mapping['ala']
        psd.arg = mapping['arg']
        psd.asn = mapping['asn']
        psd.asp = mapping['asp']
        psd.cys = mapping['cys']
        psd.gln = mapping['gln']
        psd.glu = mapping['glu']
        psd.gly = mapping['gly']
        psd.his = mapping['his']
        psd.ile = mapping['ile']
        psd.leu = mapping['leu']
        psd.lys = mapping['lys']
        psd.met = mapping['met']
        psd.phe = mapping['phe']
        psd.pro = mapping['pro']
        psd.ser = mapping['ser']
        psd.thr = mapping['thr']
        psd.trp = mapping['trp']
        psd.tyr = mapping['tyr']
        psd.val = mapping['val']
        psd.hydrogen = mapping['Hydrogen']
        psd.sulfur = mapping['Sulfur']
        psd.nitrogen = mapping['Nitrogen']
        psd.oxygen = mapping['Oxygen']
        psd.carbon = mapping['Carbon']
        psd.no_cys_ext_coeff = mapping['no_cys_ext_coeff']
        psd.all_cys_ext_coeff = mapping['all_cys_ext_coeff']
                              
        nex_session.add(psd)
        fw.write("Update protein detail for annotation_id=" + str(annotation_id) + "\n")
        
    else:
        
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


    
        
