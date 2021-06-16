import json
import os
import re
import socket

binDir = '/var/www/bin/'
dataDir = '/data/restriction_mapper/'
tmpDir = "/var/www/tmp/"

scan4matches = binDir + "scan_for_matches"
fastafile = dataDir + "orf_genomic.seq"

patfile = tmpDir + "patfile." + str(os.getpid()) + ".txt"
outfile = tmpDir + "outfile." + str(os.getpid()) + ".txt"
seqfile = tmpDir + "seqfile." + str(os.getpid()) + ".txt"

rootUrl = 'https://' + socket.gethostname().replace('-2a', '') + '/'
cutSiteFile = "restrictionmapper." + str(os.getpid())
notCutFile = "restrictionmapper_not_cut_enzyme." + str(os.getpid())
downloadfile4cutSite = tmpDir + cutSiteFile 
downloadfile4notCut = tmpDir + notCutFile

def get_downloadURLs():

    return (rootUrl + "restrictionmapper?file=" + cutSiteFile, rootUrl + "restrictionmapper?file=" + notCutFile) 

def get_sequence(name):

    name = name.replace('SGD:', '')

    f = open(fastafile, encoding="utf-8")
    
    seq = ""
    defline = ""
    for line in f:
        line = line.strip()
        if line.startswith('>'):
            pieces = line.split(' ')
            if pieces[0].replace('>', '').lower() == name.lower() or pieces[1].lower() == name.lower() or pieces[2].replace('SGDID:', '').replace(',', '').lower() == name.lower():
                defline = line
            continue
        elif defline != '':
            seq = line
        if seq != '':
            break

    f.close()

    defline = defline.replace('"', "'")
    
    return (defline, seq)

def write_seqfile(defline, seq):
    
    fw = open(seqfile, "w")

    ## remove all non-alphabet chars from seq string
    regex = re.compile('[^a-zA-Z]')
    seq = regex.sub('', seq)
        
    fw.write(defline + "\n")
    fw.write(seq + "\n")
    fw.close()

    seqNm = "Unnamed"
    chrCoords = ""
    # >YAL067C SEO1 SGDID:S000000062, Chr I from 9016-7235, Genome Release ...
    if "SGDID:" in defline and 'Genome Release' in defline:
        pieces = defline.replace('>', '').split(' ')
        systematic_name = pieces[0]
        gene_name = pieces[1]
        chrCoords = defline.split(', ')[1]
        seqNm = systematic_name
        if gene_name:
            seqNm = gene_name + "/" + systematic_name

    return (seqNm, chrCoords, len(seq))

def set_enzyme_file(enzymetype):

    if enzymetype is None:
        return dataDir + 'rest_enzymes'

    if "Six-base" in enzymetype:
        return dataDir + 'rest_enzymes.6base'

    if "blunt" in enzymetype:
        return dataDir + 'rest_enzymes.blunt'
    
    if "3" in enzymetype:
        return dataDir + 'rest_enzymes.3'

    if "5" in enzymetype:
        return dataDir + 'rest_enzymes.5'
    
    return dataDir + 'rest_enzymes'

def do_search(enzymefile):

    f = open(enzymefile, encoding="utf-8")

    error_msg = ""
    for line in f:

        pieces = line.strip().split(' ')
        enzyme = pieces[0]
        offset = pieces[1]
        pat = pieces[2]
        overhang = pieces[3]
        fw = open(patfile, "w")
        fw.write(pat + "\n")
        fw.close()
        fw = open(outfile, "a")
        fw.write(">>" + enzyme + ": " + str(offset) + " " + overhang + " " + pat + "\n")
        fw.close()

        cmd = scan4matches + " -c " + patfile + " < " + seqfile + " >> " + outfile
        err = os.system(cmd)
        
        if err < 0: 
            error_msg = "RestrmictionMapper: problem running " + scan4matches + " returned " + str(err)
            break
        
    f.close()

    if error_msg:
        return error_msg
    
    if os.path.isfile(outfile):
        return ""
    else:
        return "No " + outfile + " generated in do_search!"

def set_enzyme_types(enzymeHash, enzymeType):

    enzymeFile = "rest_enzymes.blunt"
    if '3' in enzymeType:
        enzymeFile = "rest_enzymes.3"
    elif '5' in enzymeType:
        enzymeFile = "rest_enzymes.5"

    f = open(dataDir + enzymeFile, encoding="utf-8")
    for line in f:
        pieces = line.strip().split(' ')
        enzymeHash[pieces[0]] = enzymeType
    f.close()
    
def process_data(seqLen, enzymetype):

    dataHash = {}
    offset = {}
    overhang = {}
    recognition_seq = {}
    notCutEnzyme = []
    
    f = open(outfile, encoding="utf-8") 
    preLine = ''
    enzyme = ''
    
    for line in f:
        if line.startswith('>>'):
            pieces = line.strip().split(' ')
            enzyme = pieces[0].replace('>>', '').replace(':', '')
            offset[enzyme] = pieces[1]
            overhang[enzyme] = pieces[2]
            recognition_seq[enzyme] = pieces[3]
            if enzymetype.lower() == 'all' or enzymetype == '' or enzymetype.lower().startswith('enzymes that do not'):
                if preLine.startswith('>>'):
                    pieces = preLine.replace('>>', '').replace(':', '').split(' ')
                    if pieces[0] not in notCutEnzyme:
                        notCutEnzyme.append(pieces[0])
        elif line.startswith('>'):
            # (/\>.+\[([0-9]+\,[0-9]+)\]$/) {
            coords = line.strip().split(':')[1].replace('[', '').replace(']', '')
            if enzyme in dataHash:
                dataHash[enzyme] = dataHash[enzyme] + ':' + coords
            else:
                dataHash[enzyme] = coords 
        preLine = line.strip()
    
    f.close()

    if enzymetype.lower() == 'all' or enzymetype == '' or enzymetype.lower().startswith('enzymes that do not'):
        if preLine.startswith('>>'):
            pieces = preLine.replace('>>', '').replace(':', '').split(' ')
            if pieces[0] not in	notCutEnzyme:
                notCutEnzyme.append(pieces[0])
                
    fw = open(downloadfile4notCut, 'w')
    notCutEnzyme.sort()
    for enzyme in notCutEnzyme:
        fw.write(enzyme + "\n")
    fw.close()

    if enzymetype.startswith('enzymes that do not'):
         return ({}, notCutEnzyme)

    if "cut" in enzymetype:
         
        cutLimit = 1
        if 'twice' in enzymetype:
            cutLimit = 2
        
        newDataHash = {}
        for key in dataHash:
            coords = dataHash[key].split(':')
            wCut = 0
            cCut = 0
            for coordPair in coords:
                [beg, end] = coordPair.split(',')
                beg = int(beg)
                end = int(end)
                if beg < end: 
                    wCut = wCut + 1
                else:
                    cCut = cCut + 1
            if (cCut == cutLimit and wCut <= cutLimit) or (wCut == cutLimit and cCut <= cutLimit):
                newDataHash[key] = dataHash[key]
        dataHash = newDataHash
    
    enzyme_type = {}

    set_enzyme_types(enzyme_type, "3' overhang")
    set_enzyme_types(enzyme_type, "5' overhang")
    set_enzyme_types(enzyme_type, "blunt end")

    data = {}

    fw = open(downloadfile4cutSite, 'w')
    fw.write("Enzyme\toffset (bp)\toverhang (bp)\trecognition sequence\tenzyme type\tnumber of cuts\tordered fragment size\tsorted fragment size\tcut site on watson strand\tcut site on crick strand\n")

    for enzyme in sorted (dataHash):
        if ("overhang" in enzymetype or "blunt" in enzymetype) and enzyme_type[enzyme] != enzymetype:
            continue
        cutW = []
        cutC = []
        cutPositions = dataHash[enzyme].split(':')
        cutAll = []
        for position in cutPositions:
            [beg, end] = position.split(',')
            cutSite = None
            beg = int(beg)
            end = int(end)
            if beg < end: # watson strand
                cutSite = beg + int(offset[enzyme]) - 1
                if cutSite not in cutW:
                    cutW.append(cutSite)
            else:  # crick strand
                [beg, end] = [end, beg]            
                # enzymeType = enzyme_type[enzyme]
                cutSite = beg + int(offset[enzyme]) + int(overhang[enzyme]) - 1
                if cutSite not in cutC:
                    cutC.append(cutSite)
            if cutSite not in cutAll:
                cutAll.append(cutSite)
        cutAll.append(seqLen)
        
        preCutSite = 0
        found = {}
        cutFragments = []

        for cutSite in sorted(cutAll, key=int):
            cutSize = cutSite - preCutSite
            if cutSize != 0 and cutSize not in found:
                cutFragments.append(cutSize)
                found[cutSize] = 1
            preCutSite = cutSite

        cutSiteW = ", ".join([str(x) for x in sorted(cutW, key=int)])
        cutSiteC = ", ".join([str(x) for x in sorted(cutC, key=int)])
        fragmentsReal = ", ".join([str(x) for x in cutFragments])
        fragments = ", ".join([str(x) for x in sorted(cutFragments, key=int, reverse=True)])
        cutNum = len(cutFragments) - 1

        fw.write(enzyme + "\t" + str(offset[enzyme]) + "\t" + str(overhang[enzyme]) + "\t" + recognition_seq[enzyme] + "\t" + enzyme_type[enzyme] + "\t" + str(cutNum) + "\t" + fragmentsReal + "\t" + fragments + "\t" + cutSiteW + "\t" + cutSiteC + "\n")

        data[enzyme] =  {  "cut_site_on_watson_strand": cutSiteW,
                           "cut_site_on_crick_strand": cutSiteC,
                           "fragment_size": fragments,
                           "fragment_size_in_real_order": fragmentsReal,
                           "offset": offset[enzyme],
                           "overhang": overhang[enzyme],
                           "recognition_seq": recognition_seq[enzyme],
                           "enzyme_type": enzyme_type[enzyme]  }
    
    fw.close()
    
    return (data, notCutEnzyme)


def run_restriction_site_search(request):

    p = request.args
    f = request.form

    seq = f.get('seq') if f.get('seq') else p.get('seq')
    name = f.get('name') if f.get('name') else p.get('name')
    enzymetype = f.get('type') if f.get('type') else p.get('type', 'ALL')
    enzymetype = enzymetype.replace('+', ' ').replace("%27", "'")

    defline = None
    if seq:
        defline = ">Unnamed sequence"
    else:
        (defline, seq) = get_sequence(name)

    (seqNm, chrCoords, seqLen) = write_seqfile(defline, seq)
    
    enzymefile = set_enzyme_file(enzymetype)
    
    err = do_search(enzymefile)

    if err == '':
        ## key is the enzyme
        (data, notCutEnzymeList) = process_data(seqLen, enzymetype)
        (downloadUrl4cutSite, downloadUrl4notCut) = get_downloadURLs()
        
        return { "data": data,
                 "seqName": seqNm,
                 "chrCoords": chrCoords,
                 "seqLength": seqLen,
                 "notCutEnzyme": notCutEnzymeList,
                 "downloadUrl": downloadUrl4cutSite,
                 "downloadUrl4notCutEnzyme": downloadUrl4notCut }
    else:
        return { "ERROR": err,
                 "seqName": seqNm,
                 "chrCoords": chrCoords,
                 "seqLength": seqLen,
                 "notCutEnzyme": [],
                 "downloadUrl": '',
                 "downloadUrl4notCutEnzyme": '' }
    
