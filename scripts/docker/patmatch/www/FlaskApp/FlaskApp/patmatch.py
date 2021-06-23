import json
import os
import socket

from flask import send_from_directory, Response

MAX_BUFFER_SIZE = 1600000
MIN_TOKEN = 3
MINHITS = 500
MAXHITS = 100000
DEFAULT_MAXHITS = 500
 
binDir = '/var/www/bin/'
dataDir = '/data/patmatch/'
tmpDir = '/var/www/tmp/'
config_dir = '/var/www/conf/'
seqIndexCreateScript = binDir + 'generate_sequence_index.pl'
patternConvertScript = binDir + 'patmatch_to_nrgrep.pl'
searchScript = binDir + 'nrgrep_coords'
tmpFile = "patmatch." + str(os.getpid())
downloadFile = tmpDir + tmpFile
rootUrl = 'https://' + socket.gethostname().replace('-2a', '') + '/'

def set_download_file(filename):

    return send_from_directory(tmpDir, filename, as_attachment=True, mimetype='application/text', attachment_filename=(str(filename)))

def get_downloadUrl():

    return rootUrl + "patmatch?file=" + tmpFile

def get_config(conf):

    if conf is None:
        conf = 'patmatch'
    if not conf.endswith('.json'):
        conf = conf + '.json'
    f = open(config_dir + conf, encoding="utf-8")
    data = ''
    for line in f:
        data = data + line.strip()
    f.close()
    return json.loads(data)


def get_record_offset(datafile):

    recordOffSetList = []
    seqNm4offSet = {}
    
    cmd = seqIndexCreateScript + " < " + datafile 

    out = os.popen(cmd).read()
    
    for line in out.split('\n'):
        pieces = line.strip().split('\t')
        if len(pieces) < 2:
            continue
        offSet = int(pieces[0])
        seqNm = pieces[1]
        recordOffSetList.append(offSet)
        seqNm4offSet[offSet] = seqNm
        
    return (recordOffSetList, seqNm4offSet)


def get_name_offset(offSet, recordOffSetList):

    ### perform binary search                                                                          
    low = 0
    high = len(recordOffSetList) - 1
    while high > low:
        ### pre-condition: offSet is in recordOffSetList[$low .. $high]
        middle = int((low+high)/2)
        if recordOffSetList[middle] == offSet:
            return offSet
        elif high - low == 1:
            if offSet >= recordOffSetList[high]:
                return recordOffSetList[high]
            else:
                return recordOffSetList[low]
        elif recordOffSetList[middle] < offSet:
            low = middle
        elif recordOffSetList[middle] > offSet:
            high = middle - 1

    return recordOffSetList[low]
                     
            
def check_pattern(pattern, seqtype):

    if seqtype in ['pep', 'protein']:
        if 'u' in pattern.lower():
            return 'Invalid peptide character found in pattern.'
    else:
        if any(x in pattern.upper() for x in ('E', 'F', 'I', 'J', 'L', 'O', 'P', 'Q', 'Z')):
            return 'Invalid nucleotide character found in pattern.'

    tokens = 0
    countingMode = 1
    for x in pattern:
        if x in ['(', '[', '{']:
            if countingMode:
                tokens = tokens + 1
            countingMode = 0
        elif x in [')', ']', '}']:
            countingMode = 1
        elif countingMode:
            tokens = tokens + 1

    if '{' in pattern or '{' in pattern:
        return ''

    if tokens < MIN_TOKEN:
        return "Your pattern is shorter than the minimum number of " + str(MIN_TOKEN) + " residues."
    return ''
    
def process_pattern(pattern, seqtype, strand, insertion, deletion, substitution, mismatch):

    mismatch_option = ""

    match_characters = ['{', '}', '[', ']', '(', ')']
    for x in match_characters:
        if x in pattern:
            check_pattern(pattern, seqtype)
            break
    
    option = ''

    if seqtype is None:
        seqtype = 'pep'
    if seqtype in ['pep', 'protein']:
        option = '-p'
    elif strand and 'complement' in strand.lower():
        option = '-c'
    else:
        option = '-n'
        
    cmd = patternConvertScript + " " + option + " '" + pattern + "'"
    pattern = os.popen(cmd).read()
    
    comp_pattern = ""    
    if seqtype.lower() in ['dna', 'nuc'] and (strand is None or strand.startswith('Both')):
        cmd2 = patternConvertScript + " -c " + "'" + pattern + "'"
        comp_pattern = os.popen(cmd2).read()
    
    if insertion and insertion.startswith('insertion'): 
        mismatch_option = mismatch_option + 'i'

    if deletion and deletion.startswith('deletion'):
        mismatch_option = mismatch_option + 'd'

    if substitution and substitution.startswith('substitution'):
        mismatch_option = mismatch_option + 's'

    if mismatch_option == '':
        mismatch_option = 'ids'

    if mismatch is None:
        mismatch = 0
    
    mismatch_option = str(mismatch) + mismatch_option

    return (pattern, comp_pattern, mismatch_option)


def get_sequence(dataset, seqname):
        
    f = open(dataset, encoding="utf-8")
    
    found = 0
    seq = ""
    defline = ""

    for line in f:
        line = line.strip()
        if line.lower().startswith('>'+seqname.lower()):
            found = 1
            defline = line
            continue
        if found == 0:
            continue
        if found == 1 and line.startswith('>'):
            break
        seq = seq + line
    
    f.close()

    defline = defline.replace('"', "'")

    return { 'defline': defline,
             'seq': seq }


def get_param(request, name):

    p = request.args
    f = request.form

    return f.get(name) if f.get(name) else p.get(name)

def cleanup_pattern(pattern):
    
    pattern = pattern.replace('%28', '(').replace('%29', ')')
    pattern = pattern.replace('%7B', '{').replace('%7D', '}')
    pattern = pattern.replace('%5B', '[').replace('%5D', ']')
    patteern = pattern.replace('%2C', ',')
    
    return pattern

def set_seq_length(seqNm2length, datafile):

    f = open(datafile, encoding="utf-8")
    seq = ''
    preSeqNm = ''
    for line in f:
        if line.startswith('>'):
            seqNm = line.replace('>', '').split(' ')[0]
            if preSeqNm != '':
                if seq.endswith('*'):
                    seq = seq.rstrip(seq[-1])
                seqNm2length[preSeqNm] = len(seq)
            preSeqNm = seqNm
            seq = ''
        else:
            seq = seq + line.strip()
            
    if preSeqNm != '' and seq != '':
        if seq.endswith('*'):
            seq = seq.rstrip(seq[-1])
        seqNm2length[preSeqNm] = len(seq)
    f.close()
    
def process_output(recordOffSetList, seqNm4offSet, output, datafile, maxhits, begMatch, endMatch):

    seqNm2length = {}
    if endMatch == 1:
        set_seq_length(seqNm2length, datafile)
    
    name2data = {}
    if 'orf_' in datafile:
        f = open(dataDir + "locus.txt", encoding="utf-8")
        for line in f:
            pieces = line.strip().split('\t')
            seqName = pieces[0]
            geneName = pieces[1]
            sgdid = pieces[2]
            desc = ''
            if len(pieces) > 3:
                desc = pieces[3]
            name2data[seqName] = (geneName, sgdid, desc)
        f.close()

    seqNm2chr = {}
    seqNm2orfs = {}
    if 'Not' in datafile:
        f = open(datafile, encoding="utf-8")
        for line in f:
            if line.startswith('>'):
                # >A:2170-2479, Chr I from 2170-2479, Genome Release 64-3-1, between YAL068C and YAL067W-A
                # /^>([^ ]+)\, Chr ([^ ]+) from .+ between ([^ ]+ and [^ ]+)/)
                pieces = line.strip().replace('>', '').split(' ')
                seqName = pieces[0].replace(',', '')
                chr = pieces[2]
                orfs = line.strip().split('between ')[1]
                seqNm2chr[seqName] = chr
                orfs = orfs.replace('and', '-')
                seqNm2orfs[seqName] = orfs;
        f.close()


    
    data = []

    totalHits = 0
    uniqueHits = 0
    hitCount4seqNm = {}

    if maxhits is None:
        maxhits = DEFAULT_MAXHITS
    if 'no limit' in str(maxhits) or (str(maxhits).isdigit() and int(maxhits) < MINHITS):
        maxhits = MAXHITS;
    maxhits = int(maxhits)
    
    for line in output.split('\n'):
        
        if line.startswith('['):

            line = line.replace('[', '').replace(']', '')
            line = line.replace(':', '').replace(',', '')
            pieces = line.split(' ')
            if len(pieces) < 3:
                continue
            beg = int(pieces[0])
            end = int(pieces[1])
            matchingPattern = pieces[2]
        
            offSet = get_name_offset(beg, recordOffSetList);
            seqBeg = beg - offSet + 1
            seqEnd = end - offSet
            seqNm = seqNm4offSet[offSet]
            
            if begMatch == 1 and seqBeg != 1:
                continue
            if endMatch == 1 and seqEnd != seqNm2length[seqNm]:
                continue
            if seqNm.startswith('>'):
                ## match to the fasta header line 
                continue

            if seqNm.endswith(','):
                seqNm = seqNm.rstrip(seqNm[-1])
                
            if 'Not' in datafile:
                num = int(seqNm.split(':')[1].split('-')[0])
                seqBeg = seqBeg + num -1
                seqEnd = seqEnd + num -1
                if seqNm not in seqNm2chr or seqNm not in seqNm2orfs:
                    continue

                row = str(seqNm2orfs.get(seqNm)) + "\t" + str(seqBeg) +  "\t" + str(seqEnd) + "\t" + matchingPattern + "\t" + str(seqNm2chr.get(seqNm)) + "\t" + seqNm
                
            else:
                (gene, sgdid, desc) = name2data.get(seqNm, ('', '', ''))
                row = seqNm + "\t" + str(seqBeg) + "\t" + str(seqEnd) + "\t" + matchingPattern + "\t" + gene + "\t" + sgdid + "\t" + desc

            if seqNm not in hitCount4seqNm:
                uniqueHits = uniqueHits + 1
            if totalHits >= maxhits:
                break

            if seqNm in hitCount4seqNm:
                hitCount4seqNm[seqNm] = hitCount4seqNm[seqNm] + 1
            else:
                hitCount4seqNm[seqNm] = 1
            totalHits = totalHits + 1

            data.append(row)
            
    fw = open(downloadFile, "w")

    if 'Not' in datafile:
        fw.write("Chromosome\tBetweenORFtoORF\tHitNumber\tMatchPattern\tMatchStartCoord\tMatchStopCoord\n")    
    elif 'orf_' in datafile:
        fw.write("Feature Name\tGene Name\tHitNumber\tMatchPattern\tMatchStartCoord\tMatchStopCoord\tLocusInfo\n")
    else:
        fw.write("Sequence Name\tHitNumber\tMatchPattern\tMatchStartCoord\tMatchStopCoord\n")
    
    newData = []

    data.sort()

    for row in data:
        
        if 'Not' in datafile:
            [orfs, beg, end, matchPattern, chr, seqNm] = row.split('\t')
            count = hitCount4seqNm[seqNm]
            orfs = orfs.strip()
            newData.append({ 'orfs': orfs,
                             'chr': chr,
                             'beg': beg,
                             'end': end,
                             'count': count,
                             'seqname': seqNm,
                             'matchingPattern': matchPattern })
            fw.write(chr + "\t" + orfs + "\t" + str(count) + "\t" + matchPattern + "\t" + beg + "\t" + end + "\n")
            continue

        [seqNm, beg, end, matchPattern, gene, sgdid, desc] = row.split('\t')
        
        count = hitCount4seqNm.get(seqNm, 0)
        
        if sgdid != "":
            if gene == seqNm:
                gene = ""
            newData.append({ 'seqname': seqNm,
                             'beg': beg,
                             'end': end,
                             'count': count,
                             'matchingPattern': matchPattern,
                             'gene_name': gene,
                             'sgdid': sgdid,
                             'desc': desc })
            fw.write(seqNm + "\t" + gene + "\t" + str(count) + "\t" + matchPattern + "\t" + beg + "\t" + end + "\t" + desc + "\n")
        else:
            newData.append({ 'seqname': seqNm,
                             'gene_name': gene,
                             'sgdid': sgdid,
                             'beg': beg,
                             'end': end,
                             'count': count,
                             'matchingPattern': matchPattern,
                             'desc': desc })
            fw.write(seqNm + "\t" + str(count) + "\t" + matchPattern + "\t" + beg + "\t" + end + "\n")

    fw.close()

    return (newData, uniqueHits, totalHits)


def run_patmatch(request):

    p = request.args
    f = request.form
    
    dataset = get_param(request, 'dataset')
    seqtype = get_param(request, 'seqtype')
    seqname = get_param(request, 'seqname')

    if seqtype is None:
        seqtype = 'pep'
    
    if dataset:
        dataset = dataset + ".seq"
    else:
        if seqtype and seqtype in ['dna', 'nuc']:
            dataset = "orf_dna.seq"
        else:
            dataset = "orf_pep.seq"
	
    datafile = dataDir + dataset

    if seqname:
        data = get_sequence(datafile, seqname)
        return data

    pattern = cleanup_pattern(get_param(request, 'pattern'))

    begMatch = 0
    endMatch = 0
    if pattern.startswith('<'):
        begMatch = 1
        pattern = pattern.replace('<', '')
    elif pattern.endswith('>'):
        endMatch = 1
        pattern = pattern.replace('>', '')
    
    error = check_pattern(pattern, seqtype)
    if error:
        return { "error": error }
    
    (pattern, comp_pattern, option) = process_pattern(pattern,
                                                      get_param(request, 'seqtype'),
                                                      get_param(request, 'strand'),
                                                      get_param(request, 'insertion'),
                                                      get_param(request, 'deletion'),
                                                      get_param(request, 'substitution'),
                                                      get_param(request, 'mismatch'))

    maxBufferSize = MAX_BUFFER_SIZE
    
    nrgrep = searchScript + " -i -b " + str(maxBufferSize) + " -k " + option + " '" + pattern + "' '" + datafile + "'"
    output = os.popen(nrgrep).read()

    nrgrep2 = ''
    output2 = ''
    if comp_pattern:
        nrgrep2 = searchScript + " -i -b " +str( maxBufferSize) + " -k " + option + " '" + comp_pattern +"' '" + datafile + "'"
        output2 = os.popen(nrgrep2).read()
        output = output + "\n" + output2

    # return { "nrgrep": nrgrep,
    #         "nrgrep2": nrgrep2,
    #         "output": output }
        
    (recordOffSetList, seqNm4offSet) = get_record_offset(datafile)

    # return { "nrgrep": nrgrep,
    #         "nrgrep2": nrgrep2,
    #         "recordOffSetlist": recordOffSetList,
    #         "seqNm4offSet": seqNm4offSet }
    
    (data, uniqueHits, totalHits) = process_output(recordOffSetList, seqNm4offSet, output,
                                                   datafile, get_param(request, 'max_hits'),
                                                   begMatch, endMatch)

    downloadUrl = ''
    if uniqueHits > 0:
        downloadUrl = get_downloadUrl()
        
    return { "hits": data,
             "uniqueHits": uniqueHits,
             "totalHits": totalHits,
             "downloadUrl": downloadUrl }
    
    

















