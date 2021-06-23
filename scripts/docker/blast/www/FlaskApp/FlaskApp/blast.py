import logging
import json
import os
from blast_markup import markupOutput

DATASET_PATH = '/data/blast/'
BIN_PATH = '/tools/blast/bin/'
TMP_PATH = '/var/tmp/'
MAX_GRAPH_HITS = 50
LINE_WIDTH = 70

protein_lookup_file = '/data/blast/YeastORF.pep'
dna_lookup_file = '/data/blast/YeastORF-Genomic.fsa'
config_dir = '/var/www/conf/'
pvalue_cutoff = 0.05

def set_dataset_mapping(conf_file):

    dataset_mapping = {}
    datasetList4labelNm = {}
    groupLabel2groupNm = {}
    conf_data = get_config(conf_file)
    dataset_mapping['databasedef'] = conf_data['databasedef']
    datagroup = conf_data['datagroup']    
    for label in datagroup:
        dataset_list = datagroup[label].split(',')
        datasetList4labelNm[label] = dataset_list
    database = conf_data['database']
    for d in database:
        db = d['dataset']
        type = d['type']
        desc = d['label']
        mapping = []
        if 'dbList' in dataset_mapping:
            mapping = dataset_mapping['dbList']
            mapping.append(db)
            dataset_mapping['dbList'] = mapping
        if 'dbType' not in  dataset_mapping:
             dataset_mapping['dbType'] = {}
        dataset_mapping['dbType'][db] = type
        if db.startswith('label'):
            desc = '...' + desc
        if 'dbLabel' not in dataset_mapping:
            dataset_mapping['dbLabel'] = {}
        dataset_mapping['dbLabel'][db] = desc
        if db.startswith('label'):
            label = db.strip()
            groupNm = desc.lower()
            groupLabel2groupNm[label]= groupNm

    dataset_mapping['groupLabel2name'] = groupLabel2groupNm
    dataset_mapping['groupLabel2datasets'] = datasetList4labelNm

    return dataset_mapping
    
def combine_datasets(dataset_list, program, conf_file):

    dataset_mapping = set_dataset_mapping(conf_file)

    dataset_passed_in = {}
    for dataset in dataset_list:
        dataset_passed_in[dataset] = 1

    groupLabel2group = dataset_mapping['groupLabel2name']
    groupLabel2datasets = dataset_mapping['groupLabel2datasets']

    notFound = 0
    for label in groupLabel2datasets:
        dataset4label = groupLabel2datasets[label]
        for dataset in dataset4label:
            if dataset not in dataset_list:
                notFound = 1
                break
        if notFound == 1:
            continue
        
        ## if all datasets in this group are passed in so we can just use this group
        ## dataset instead of using the individual ones 

        groupNm = groupLabel2groupNm[label]
        dataset_passed_in[groupNm] = 1 ## add group name to the passed in dataset list

        for dataset in dataset4label:
            # remove each individual one in the list
            del dataset_passed_in[dataset]

    processed_datasets = ''
    processed_dataset_list = []
    
    for dataset in sorted (dataset_passed_in.keys()):
        if program in ['blastp', 'blastx']:
            dataset = dataset + ".pep";
        else:
            dataset = dataset + ".fsa"
        processed_dataset_list.append(dataset)
        processed_datasets = processed_datasets + ' ' + DATASET_PATH + "fungi/" + dataset

    return (processed_datasets.strip(), processed_dataset_list)
    
        
def prepare_datasets(datasets, program, conf_file):

    datasetsa = datasets.replace(',', ' ').replace('+', ' ').replace('  ', ' ')
    dataset_list = datasets.split(' ')
    
    if "fungal" in conf_file and len(dataset_list) > 20:
        ## return (processed_datasets, processed_dataset_list)
        return combine_datasets(dataset_list, program, conf_file)


    
    processed_datasets = ''
    processed_dataset_list = []
    for dataset in dataset_list:
        if 'fungal' in conf_file:
            if program in ['blastp', 'blastx']:
                if '.pep' not in dataset:
                    dataset = dataset + '.pep'
            elif '.fsa' not in dataset:
                dataset = dataset + '.fsa'
        else:
            if program in ['blastp', 'blastx']:
                if '_cds' in dataset:
                    dataset = dataset.replace('_cds', '_pep')
                elif dataset.endswith('fsa'):
                    dataset = dataset.replace('.fsa', '.pep')
                elif '.pep' not in dataset:
                    dataset = dataset + ".pep"
            elif '.fsa' not in dataset:
                dataset = dataset + '.fsa'
                    
        processed_dataset_list.append(dataset)
        if 'fungal' in conf_file:
            processed_datasets = processed_datasets + ' ' + DATASET_PATH + 'fungi/' + dataset
        else:
            processed_datasets = processed_datasets + ' ' + DATASET_PATH + dataset
    return (processed_datasets.strip(), processed_dataset_list)

def test_dna_seq():

    ## part of yeast act1 genome sequence
    return "ATGGATTCTGGTATGTTCTAGCGCTTGCACCATCCCATTTAACTGTAAGAAGAATTGCACGGTCCCAATTGCTCGAGAGATTTCTCTTTTACCTTTTTTTACTATTTTTCACTCTCCCATAACCTCCTATATTGACTGATCTGTAATAACCACGATATTATTGGAATAAATAGGGGCTTGAAATTTGGAAAAAAAAAAAAAACTGAAATATTTTCGTGATAAGTGATAGTGATATTCTTCTTTTATTTGCTACTGTTACTAAGTCTCATGTACTAACATCGATTGCTTCATTCTTTTTGTTGCTATATTATATGTTTAGAGGTTGCTGCTTTGGTTATTGATAACGGTTCTGGTATGTGTAAAGCCGGTTTTGCCGGTGACGACGCTCCTCGTGCTGTCTTCCCATCTATCGTCGGTAGACCAAGACACCAAGGTATCATGGTCGGTATGGGTCAAAAAGACTCCTACGTTGGTGATGAAGCTCAATCCAAGAGAGGTATCTTGACTTTACGTTACCCAATTGAACACGGTATTGT"

def test_dna_seq2():

    ## yeast act1 coding sequence
    return "ATGGATTCTGAGGTTGCTGCTTTGGTTATTGATAACGGTTCTGGTATGTGTAAAGCCGGTTTTGCCGGTGACGACGCTCCTCGTGCTGTCTTCCCATCTATCGTCGGTAGACCAAGACACCAAGGTATCATGGTCGGTATGGGTCAAAAAGACTCCTACGTTGGTGATGAAGCTCAATCCAAGAGAGGTATCTTGACTTTACGTTACCCAATTGAACACGGTATTGTCACCAACTGGGACGATATGGAAAAGATCTGGCATCATACCTTCTACAACGAATTGAGAGTTGCCCCAGAAGAACACCCTGTTCTTTTGACTGAAGCTCCAATGAACCCTAAATCAAACAGAGAAAAGATGACTCAAATTATGTTTGAAACTTTCAACGTTCCAGCCTTCTACGTTTCCATCCAAGCCGTTTTGTCCTTGTACTCTTCCGGTAGAACTACTGGTATTGTTTTGGATTCCGGTGATGGTGTTACTCACGTCGTTCCAATTTACGCTGGTTTCTCTCTACCTCACGCCATTTTGAGAATCGATTTGGCCGGTAGAGATTTGACTGACTACTTGATGAAGATCTTGAGTGAACGTGGTTACTCTTTCTCCACCACTGCTGAAAGAGAAATTGTCCGTGACATCAAGGAAAAACTATGTTACGTCGCCTTGGACTTCGAACAAGAAATGCAAACCGCTGCTCAATCTTCTTCAATTGAAAAATCCTACGAACTTCCAGATGGTCAAGTCATCACTATTGGTAACGAAAGATTCAGAGCCCCAGAAGCTTTGTTCCATCCTTCTGTTTTGGGTTTGGAATCTGCCGGTATTGACCAAACTACTTACAACTCCATCATGAAGTGTGATGTCGATGTCCGTAAGGAATTATACGGTAACATCGTTATGTCCGGTGGTACCACCATGTTCCCAGGTATTGCCGAAAGAATGCAAAAGGAAATCACCGCTTTGGCTCCATCTTCCATGAAGGTCAAGATCATTGCTCCTCCAGAAAGAAAGTACTCCGTCTGGATTGGTGGTTCTATCTTGGCTTCTTTGACTACCTTCCAACAAATGTGGATCTCAAAACAAGAATACGACGAAAGTGGTCCATCTATCGTTCACCACAAGTGTTTCTAA"

def test_protein_seq():

    ## yeast act1 protein_sequence
    return "MDSEVAALVIDNGSGMCKAGFAGDDAPRAVFPSIVGRPRHQGIMVGMGQKDSYVGDEAQSKRGILTLRYPIEHGIVTNWDDMEKIWHHTFYNELRVAPEEHPVLLTEAPMNPKSNREKMTQIMFETFNVPAFYVSIQAVLSLYSSGRTTGIVLDSGDGVTHVVPIYAGFSLPHAILRIDLAGRDLTDYLMKILSERGYSFSTTAEREIVRDIKEKLCYVALDFEQEMQTAAQSSSIEKSYELPDGQVITIGNERFRAPEALFHPSVLGLESAGIDQTTYNSIMKCDVDVRKELYGNIVMSGGTTMFPGIAERMQKEITALAPSSMKVKIIAPPERKYSVWIGGSILASLTTFQQMWISKQEYDESGPSIVHHKCF"

def create_tmp_seq_file(query_file, seq, seqname):
    
    fw = open(query_file, 'w')
    while (len(seq) > LINE_WIDTH):
        if seq.startswith('>'):
            seq = ''
        else:
            fw.write(seq[0:LINE_WIDTH] + "\n")
            seq = seq[LINE_WIDTH:]

    fw.write(seq + "\n")    
    fw.close()


def _pvalue_to_exp(pvalue):

    if pvalue == 0:
        return -500
    elif '-' in str(pvalue):
        return 0 - int(str(pvalue).split('-')[1])
    else:
        return pvalue

def _get_id_desc(line):
    
    pieces = line.replace('>', '').strip().split(' ')
    id = pieces[0]
    desc = pieces[1]
    if len(pieces) > 2:
        desc = desc + ' ' + pieces[2].replace(',', '')
    return (id, desc)

def _get_coords(start, end):
    
    if start > end:
        (start, end) = (end, start)
    len = end - start + 1

    return (start, end, len)

def _set_name(id, pvalue, score, desc):

    return id + ': p=' + str(pvalue) + ' s=' + score + ' ' + desc

def _set_strand(line):

    pieces = line.replace('Sbjct ', '').strip().split(' ')
    if int(pieces[0]) > int(pieces[-1]):
        return - 1
    return 1

def parse_hits(blastOutfile):

    records = []
    totalHits = 0
    showHits = 0
    
    start = None
    end = None
    id = None
    query_length = None
    strand = None
    same_row = 0
    pvalue = ''
    score = ''
    desc = ''

    f = open(blastOutfile)
    for line in f:
        if line.startswith('Length=') and query_length is None:
            query_length = int(line.strip().replace('Length=', ''))
        if line.startswith('>'):
            totalHits = totalHits + 1
            if id and start and end:
                exp = _pvalue_to_exp(pvalue)
                (start, end, len) = _get_coords(start, end)
                if pvalue <= pvalue_cutoff and showHits < MAX_GRAPH_HITS:
                    showHits = showHits + 1
                    records.append({ 'query_length': query_length,
                                     'name': _set_name(id, pvalue, score, desc),
                                     'value': len,
                                     'start': start,
                                     'end': end,
                                     'strand': strand,
                                     'exp': exp,
                                     'same_row': same_row })
                    start = None
                    end = None
                    id = None
                    strand = None
                    same_row = 0
                    pvalue = ''
                    score = ''
                    desc = ''
            (id, desc) = _get_id_desc(line)
        elif "Score = " in line:
            if start and end:
                exp = _pvalue_to_exp(pvalue)
                (start, end, len) = _get_coords(start, end)
                if pvalue <= pvalue_cutoff:
                    records.append({ 'query_length': query_length,
                                     'name': _set_name(id, pvalue, score, desc),
                                     'value': len,
                                     'start': start,
                                     'end': end,
                                     'strand': strand,
                                     'exp': exp,
                                     'same_row': same_row })
                    same_row = 1
                start = None
                end = None
                strand = None
            score = line.split('Score = ')[1].split(' ')[0]
            pvalue = float(line.split('Expect = ')[1].split(' ')[0].replace(',', ''))
        elif line.startswith("Query "):
            pieces = line.replace('Query ', '').strip().split(' ')
            if start is None:
                start = int(pieces[0])
            end = int(pieces[-1])
        elif line.startswith("Sbjct ") and strand is None:
            strand = _set_strand(line)
            
    exp = _pvalue_to_exp(pvalue)
    (start, end, len) = _get_coords(start, end)
    if pvalue <= pvalue_cutoff and showHits < MAX_GRAPH_HITS:
        showHits = showHits+ 1
        records.append({ 'query_length': query_length,
                         'name': _set_name(id, pvalue, score, desc),
                         'value': len,
                         'start': start,
                         'end': end,
                         'strand': strand,
                         'exp': exp,
                         'same_row': same_row })
                
    return (totalHits, showHits, records)
    
def get_config(conf):
    f = open(config_dir + conf + '.json')
    data = ''
    for line in f:
        data = data + line.strip()
    f.close()
    return json.loads(data)

def get_seq(name, type=None):

    lookup_file = dna_lookup_file
    if type and type in ['protein', 'pep']:
        lookup_file = protein_lookup_file
    f = open(lookup_file)
    seq = ''
    found = 0
    for line in f:
        if line.startswith('>'):
            if found == 1:
                break
            pieces = line.replace('>', '').split(' ')
            name_list = [pieces[0].upper()]
            if pieces[1]:
                name_list.append(pieces[1].upper())
            name_list.append(pieces[2].replace('SGDID:', '').replace(',', ''))
            if name.upper() in name_list:
                found = 1
        elif found == 1:
            seq = seq + line.strip()            
    f.close()

    return { 'seq': seq }

def get_blast_options(request):

    p = request.args
    f = request.form
    
    program = p.get('program') if p.get('program') else f.get('program')
    database = p.get('database') if p.get('database') else f.get('database')
    outFormat = p.get('outFormat') if p.get('outFormat') else f.get('outFormat')
    matrix = p.get('matrix') if p.get('matrix') else f.get('matrix')
    threshold = p.get('threshold') if p.get('threshold') else f.get('threshold')
    cutoffScore = p.get('cutoffScore') if p.get('cutoffScore') else f.get('cutoffScore')
    alignToShow = p.get('alignToShow') if p.get('alignToShow') else f.get('alignToShow')
    wordLength = p.get('wordLength') if p.get('wordLength') else f.get('wordLength') 
    filter = p.get('filter') if p.get('filter') else f.get('filter') 

    options = ''
    if cutoffScore:
        options = "-evalue " + cutoffScore
    if alignToShow:
        options = options + " -num_alignments " + alignToShow

    if (database == 'Sc_mito_chr' and (program == 'blastn' or program == 'tblastx')):
        # default is 1
        options = options + " -query_genetic_code 3"
    if program != 'blastn' and threshold and threshold != 'default':
        options = options + " -threshold " + threshold

    if program != 'blastn' and matrix and matrix != "BLOSUM62":
        options = options + " -matrix " + matrix

    if wordLength:
        if wordLength != 'default':
            options = options + " -word_size " + wordLength
        else:
            if program == 'blastn':
                options = options + " -word_size 11"
            else:
                options = options + " -word_size 3"

    # options = options + " -outfmt 0 -html"
    options = options + " -outfmt 0"

    if outFormat and outFormat.startswith("ungapped"):
        options = options + " -ungapped"

    # lastn: DUST and is on by default
    # blastp: SEG and is off by default
    # blastx: SEG and is on by default
    # tblastx: SEG and is on by default
    # tblastn: SEG and is on by default

    if filter:
        if filter == 'on':
            if program == 'blastp':
                options = options + " -seg yes"
        else:
            if program == 'blastn':
                options = options + " -dust 'no'"
            elif program != 'blastp':
                options = options + " -seg 'no'"

    return options
    
def run_blast(request):

    p = request.args
    f = request.form
    
    datasets = f.get('database') if f.get('database') else p.get('database')
    program = f.get('program') if f.get('database') else p.get('program')
    seq = f.get('seq') if f.get('seq') else p.get('seq')
    confFile = 'blast-sgd'
    if f.get('blastType') == 'fungal' or p.get('blastType') == 'fungal':
        confFile = 'blast-fungal'

    ## processed_datasets: a list of dataset names
    ## processed_dataset_list: a space separated dataset file names with full pass
    
    (processed_datasets, processed_dataset_list) = prepare_datasets(datasets, program, confFile)

    program = BIN_PATH + program

    # filtering = 0
    # if p.get(filter) == 'on':
    #    filtering = 1

    options = get_blast_options(request)
    
    pid = os.getpid()
    query_file = TMP_PATH + 'tmp.fsa.' + str(pid)
    seqname = request.form.get('seqname', 'unknown')
    create_tmp_seq_file(query_file, seq, seqname);

    blastoutfile = TMP_PATH + 'blast.out.' + str(pid)
    
    cmd = program + " -query " + query_file + " -db '" + processed_datasets + "' -out " + blastoutfile + " " + options
    
    os.system(cmd)

    f = open(blastoutfile)
    output = ''
    for line in f:
        output = output + line
    f.close()
    
    if "** No hits found **" in output:
        return  { "cmd": cmd,
                  "result": "<font size=+1><pre>" + output + "</pre></font>",
                  "hits":   [],
                  "totalHits": 0,
                  "showHits": 0 }
    
    output = markupOutput(datasets, output)

    (totalHits, showHits, records) = parse_hits(blastoutfile)

    # "<font size=+1><pre>" + output + "</pre></font>",
    
    return { "cmd": cmd,
             "result": "<pre><p font-size='11px'>" + output + "</p></pre>",
             "hits":   records,
             "totalHits": totalHits,
             "showHits": showHits }
