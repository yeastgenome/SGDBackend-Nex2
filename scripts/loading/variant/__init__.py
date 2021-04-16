from scripts.loading.util import codon_table

def calculate_block_data(aligned_dna_seq, introns):

    seq = aligned_dna_seq.replace('-', '')
    length = len(seq)
    # example introns = [] 
    # example introns = [{ 'start': 11, 'end': 319 }]
    # example introns = [{ 'start': 11, 'end': 319 }, { 'start': 521, 'end': 560 }] 
    block_starts = [0]
    block_sizes = []
    prevEnd = 1 
    for intron in introns:
        block_starts.append(intron['end'])
        block_size = intron['start'] - prevEnd
        prevEnd = intron['end']
        block_sizes.append(block_size)
    block_sizes.append(length - prevEnd)

    return (block_starts, block_sizes)

def aligned_sequence_to_snp_sequence(strain, strain_id, aligned_sequence, variants):

    snp_sequence = ''
    # add SNP chars to snp_sequence
    for var in variants:
        if var['variant_type'] == 'SNP':
            start = int(var['start']) - 1
            end = int(var['end']) - 1
            snp = aligned_sequence[start:end]
            snp_sequence = snp_sequence + snp
        else:
            start = int(var['start']) - 1
            end = start + 1
            snp = aligned_sequence[start:end]
            snp_sequence = snp_sequence + snp

    obj = {
        'name': strain,
        'id': strain_id,
        'snp_sequence': snp_sequence
    }
    return obj

def translate(codon):

    codons = codon_table()
    
    if codon in codons:
        return codons[codon]
    else:
        return None

def check_snp_type(name, strain, index, intron_indices, ref_seq, aligned_seq): 
    #Check if SNP is in intron
    pre_introns = []
    post_introns = []
    aligned_seq_coding = ''
    ref_seq_coding = ''
    seq_index = 0
    for start, end in intron_indices:
        aligned_seq_coding += aligned_seq[seq_index:start]
        ref_seq_coding += ref_seq[seq_index:start]
        seq_index = end+1
        if index < start:
            post_introns.append((start, end))
        elif index > end:
            pre_introns.append((start, end))
        else:
            return 'Intron SNP'
    aligned_seq_coding += aligned_seq[seq_index:len(aligned_seq)]
    ref_seq_coding += ref_seq[seq_index:len(ref_seq)]
    index_coding = index - sum([end-start+1 for start, end in pre_introns])

    index_to_frame = {}
    codon = []
    for i, letter in enumerate(ref_seq_coding):
        if letter == '-':
            pass
        else:
            codon.append(i)
        if len(codon) == 3:
            for index in codon:
                index_to_frame[index] = codon
            codon = []

    codon = index_to_frame.get(index_coding)
    if codon is None:
        print ("Warning: KeyError:" + str(index_coding), "=>name, strain, index, intron_indices=", name, strain, index, intron_indices)
        return "Unknown SNP"

    try:
        ref_amino_acid = translate(''.join([ref_seq_coding[i] for i in codon]))
        aligned_amino_acid = translate(''.join([aligned_seq_coding[i] for i in codon]))
    except:
        print ("BAD translate: ", name, strain, index, intron_indices, ref_seq, aligned_seq)
               
    if ref_amino_acid is None or aligned_amino_acid is None:
        return 'Untranslatable SNP'
    elif ref_amino_acid == aligned_amino_acid:
        return 'Synonymous SNP'
    else:
        return 'Nonsynonymous SNP'

def calculate_variant_data(name, type, strain_to_seq, introns):
    intron_indices = [(int(x['start']), int(x['end'])) for x in introns]
    variants = dict()
    reference_alignment = strain_to_seq['S288C']
    for strain in strain_to_seq:
        aligned_sequence = strain_to_seq[strain]
        state = 'No difference'
        state_start_index = 0
        for i, letter in enumerate(reference_alignment):
            #Figure out new state
            new_state = 'No difference'
            # if len(aligned_sequence) > i and aligned_sequence[i] != letter:
            if i >= len(aligned_sequence):
                print ("BAD: ", name, type, strain_to_seq, introns)
                continue
            if aligned_sequence[i] != letter: 
                if letter == '-':
                    new_state = 'Insertion'
                elif aligned_sequence[i] == '-':
                    new_state = 'Deletion'
                else:
                    if type == 'DNA':
                        new_state = check_snp_type(name, strain, i, intron_indices, reference_alignment, aligned_sequence)
                    else:
                        new_state = 'SNP'

            if state != new_state and new_state != 'Unknown SNP':
                if state != 'No difference':
                    variant_key = (state_start_index+1, i+1, state)
                    if variant_key not in variants:
                        variants[variant_key] = 0
                    variants[variant_key] += 1

                state = new_state
                state_start_index = i

        if state != 'No difference':
            variant_key = (state_start_index+1, i+1, state)
            if variant_key not in variants:
                variants[variant_key] = 0
            variants[variant_key] += 1

    variant_data = []
    for variant, score in variants.items():
        obj_json = {
            'start': variant[0],
            'end': variant[1],
            'score': score,
            'variant_type': 'SNP' if variant[2].endswith('SNP') else variant[2]
        }
        if variant[2].endswith('SNP'):
            obj_json['snp_type'] = variant[2][0:-4]

        variant_data.append(obj_json)

    return variant_data

def strain_to_id():

    return { 'S288C': 1,
             'W303': 2,
             'FL100': 3,
             'CEN.PK': 4,
             'Sigma1278b': 5,
             'SK1': 6,
             'D273-10B': 7,
             'X2180-1A': 8,
             'Y55': 9,
             'JK9-3d': 10,
             'SEY6210': 11,
             'RM11-1a': 12  }

