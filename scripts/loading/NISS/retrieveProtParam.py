from urllib.request import urlopen

protein_seq_file = 'data/NISSpilotSet102119_protein.fsa'
protparam_file = 'data/NISSpilotSet102119_protparam.txt'
codonw_file = 'data/NISSpilotSet102119_codonw.out'

protparam_root_url = 'https://web.expasy.org/cgi-bin/protparam/protparam?sequence='

aaList = ['ala', 'arg', 'asn', 'asp', 'cys', 'gln', 'glu', 'gly', 'his', 'ile', 'leu', 'lys', 'met', 'phe', 'pro', 'ser', 'thr', 'trp', 'tyr','val']

def retrieve_data():

    f = open(codonw_file)
    key2codonw = {}
    for line in f:
        if line.startswith('title'):
            continue
        pieces = line.strip().split('\t')
        ids = pieces[0].split('_')
        if len(pieces) > 14:
            key = (ids[0], ids[2])
            key2codonw[key] = (pieces[5], pieces[6], pieces[7], pieces[13], pieces[14])
    f.close()

    f = open(protein_seq_file)
    fw = open(protparam_file, "w")

    strain = None
    name = None
    seq = ''
    contig = None
    isFirst = 1
    for line in f:
        line = line.strip()
        if line.startswith('>'):
            if name and seq:
                process_data(fw, name, strain, contig, seq, key2codonw.get((name, strain)), 
                             isFirst)
                seq = ''
                isFirst = 0
            pieces = line.split(' ')
            name = pieces[0].replace('>', '')
            strain = pieces[2]
            contig = pieces[3]
        else:
            seq = seq + line

    process_data(fw, name, strain, contig, seq, key2codonw.get((name, strain)), isFirst)

    f.close()
    fw.close()

def process_data(fw, name, strain, contig, seq, key, isFirst):
    
    seq = seq.replace('*', '')
    protein_length = len(seq)
    n_term_seq = seq[0:7]
    c_term_seq = seq[-7:]

    url = protparam_root_url+seq

    (cai, cbi, fop, gravy, aromo) = key
    
    response = urlopen(url)
    html = response.read().decode('utf-8')

    lines = html.split("\n")
    mw = None
    pI = None
    aa2value = {}
    atom2composition = {}
    formStart = 0
    no_cys_ext_coeff = 0
    all_cys_ext_coeff = 0
    ext_coeff = None
    instability_index = None
    aliphatic_index = None
    for line in lines:
        if line.startswith("<B>Molecular weight:</B> "):
            mw = line.replace("<B>Molecular weight:</B> ", '')
            continue
        if line.startswith("<B>Theoretical pI:</B> "):
            pI = line.replace("<B>Theoretical pI:</B> ", '')
            continue
        if "<form " in line:
            formStart = 1
        if "</form>" in line:
            formStart = 0
        if formStart == 1:
            pieces = line.split('>')[-1].split(' ')
            aa = pieces[0].lower()
            for x in pieces:
                if x == '':
                    continue
                x = x.replace("\t", "")
                if x.isdigit():
                    aa2value[aa] = x
        for atom in ['Carbon', 'Hydrogen', 'Nitrogen', 'Oxygen', 'Sulfur']:
            if line.startswith(atom):
                pieces = line.split(' ')
                atom2composition[atom] = pieces[-1]
        if line.startswith('Ext. coefficient'):
            pieces = line.split(' ')
            ext_coeff = pieces[-1]
            continue
        if "assuming all pairs of Cys residues form cystines" in line:
            all_cys_ext_coeff = ext_coeff
            continue
        if "assuming all Cys residues are reduced" in line:
            no_cys_ext_coeff = ext_coeff
            continue
        if line.startswith("The instability index (II) is computed to be "):
            instability_index = line.replace("The instability index (II) is computed to be ", '')
            continue
        if line.startswith("<B>Aliphatic index:</B> "):
            aliphatic_index = line.replace("<B>Aliphatic index:</B> ", '')

    if isFirst == 1:
        # print header
        fw.write("name\tstrain\tcontig\tprotein_length\tn_term_seq\tc_term_seq\tMW\tpI\t")
        for aa in aaList:
            fw.write(aa+"\t")
        for atom in ['Carbon', 'Hydrogen', 'Nitrogen', 'Oxygen', 'Sulfur']:
            fw.write(atom+"\t")
        fw.write("instability_index\taliphatic_index\tcai\tcodon_bias\tfop_score\tgravy_score\taromaticity_score\tno_cys_ext_coeff\tall_cys_ext_coeff\n")
    
        protein_length = len(seq)
    n_term_seq = seq[0:7]
    c_term_seq = seq[-7:]

    cai = str(round(float(cai), 2))
    cbi = str(round(float(cbi), 2))
    fop = str(round(float(fop), 2))
    gravy = str(round(float(gravy), 2))
    aromo = str(round(float(aromo), 2))

    # print data 
    fw.write(name +"\t" + strain + "\t" + contig + "\t" +  str(protein_length) + "\t")
    fw.write(n_term_seq + "\t" + c_term_seq + "\t" + mw + "\t" + pI + "\t")
    for aa in aaList:
        fw.write(str(aa2value.get(aa))+"\t")
    for atom in ['Carbon', 'Hydrogen', 'Nitrogen', 'Oxygen', 'Sulfur']:
        fw.write(str(atom2composition.get(atom))+"\t")
    fw.write(instability_index + "\t" + aliphatic_index + "\t" + cai + "\t" + cbi + "\t" + fop + "\t" + gravy + "\t" + aromo + "\t" + no_cys_ext_coeff + "\t" + all_cys_ext_coeff + "\n")

if __name__ == "__main__":
        
    retrieve_data()
