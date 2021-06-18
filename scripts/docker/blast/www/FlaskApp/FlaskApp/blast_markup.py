import string

rootUrl = 'https://www.yeastgenome.org/'

LOCUS = rootUrl + 'locus/'
SEQ = rootUrl + 'seqTools?chr='
SEQAN = rootUrl + 'seqTools?seqname='
GBROWSE = 'https://browse.yeastgenome.org/?loc='
NCBI_URL = 'https://www.ncbi.nlm.nih.gov/nuccore/'

def number2roman():

    num2rom = {}
    i = 0
    for roman in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI',
                  'XII', 'XIII', 'XIV', 'XV', 'XVI', 'mt']:
        i = i + 1
        num2rom[str(i)] = roman
    num2rom['2-micron'] = '2-micron'
    return num2rom

def roman2number():

    num2rom = number2roman()
    rom2num = {}
    for num in num2rom:
        rom = num2rom[num]
        if num == '17':
            rom = 'Mito'
        rom2num[rom] = num
    return rom2num

def letter2number():

    letter2num = {}
    for letter in list(string.ascii_uppercase):
         if letter == 'Q':
             break
         letter2num[letter] = str(ord(letter)-64)
    letter2num['Q'] = 'MT'
    letter2num['R'] = '2-micron'
    return letter2num

def record_line(line):
    pieces = line.split("|")
    ncbiID = pieces[1]
    url = NCBI_URL + ncbiID
    return "<a href='" + url + "' target='_new'>" + pieces[0] + "|" + pieces[1] + "</a>|" + "|".join(pieces[2:]) 
    
def link_out(chr, chrnum, beg, end):

    GSR_link = "<a href='" + SEQ + chrnum + "&start=" + beg + "&end=" + end + "&submit2=Submit+Form" + "' target='_new'>Retrieve Sequence</a>"

    beg = int(beg)
    end = int(end)
    if beg > end:
        (beg, end) = (end, beg)
    start = beg	- 5000
    if start < 1:
        start =	1
    stop = end + 5000

    JBROWSE_link = "<a href='" + GBROWSE + "chr" + chr + "%3A" + str(start) + ".." + str(stop) + "&tracks=DNA%2CAll%20Annotated%20Sequence%20Features&highlight=chr" + chr + "%3A" + str(beg) + ".." + str(end) + "'  target='_new'>Genome Browser</a>"

    return "  [ " + GSR_link + " / " + JBROWSE_link + " ]"
             
def markupChromosomalCoord(blastOutput):

    lines = blastOutput.split('\n')

    rom2num = roman2number()    
    # letter2num = letter2number()
    # num2rom = number2roman()
    newoutput = ''
    startRecord = 0
    recordBeforeScore = ''
    scoreline = ''
    recordAfterScore = ''
    chr = ''
    chrnum = ''
    beg = ''
    end = ''

    for line in lines:        
        if line.startswith('>'):
            startRecord = 1
        if startRecord == 0:
            if "ref|NC_" in line or "gi|" in line:
                newline = record_line(line)
                newoutput = newoutput + newline + "\n"
            else:
                newoutput = newoutput + line + "\n"
        else:            
            if line.startswith('>'):
                if recordBeforeScore != '':
                    scoreline = scoreline + link_out(chr, chrnum, beg, end) + "\n" 
                    newoutput = newoutput + recordBeforeScore + "\n" + scoreline + "\n" + recordAfterScore+ "\n"
                chr = ''
                chrnum = ''
                beg = ''
                end = ''
                newline = record_line(line)
                recordBeforeScore = newline + "\n"
                recordAfterScore = ''
            elif " Score = " in line:
                scoreline = line
            elif "[chromosome=" in line:
                recordBeforeScore = recordBeforeScore + line + "\n"
                pieces = line.split("[chromosome=")
                chr = pieces[-1].replace(']', '')
                chrnum = rom2num.get(chr)
            elif scoreline == '':
                recordBeforeScore = recordBeforeScore + line + "\n"
            else:
                recordAfterScore = recordAfterScore + line + "\n"
                if line.startswith('Sbjct '):
                    pieces = line.split(' ')
                    tmp_beg = ''
                    tmp_end = ''
                    for item in pieces:
                        if item.isdigit():
                            if tmp_beg == '':
                                tmp_beg = item
                            else:
                                tmp_end = item
                    if beg == '':
                        beg = tmp_beg
                    end = tmp_end
            
    if recordBeforeScore != '':
        scoreline = scoreline + link_out(chr, chrnum, beg, end) + "\n"
        newoutput = newoutput + recordBeforeScore + "\n" + scoreline + "\n" + recordAfterScore+ "\n"

    return newoutput


def markupOutput(dataset, blastOutput):
    
    output_lines = blastOutput.split('\n')

    blastOutput = ''
    end = 0
    databases = ''
    finish_db_line = 0
    prevLine = ''
    for line in output_lines:
        if line.startswith('BLAST'):
            continue
        if prevLine == '' and line == '':
            continue
        prevLine = line
        if "Sequences producing significant alignment" in line:
            end = 1
        if end == 0:
            if '/data/blast/' in line:
                if finish_db_line == 1:
                    continue
                line = line.strip().replace("/data/blast/fungi/", "").replace("/data/blast/", "")
                if databases == '':
                    databases = line
                else:
                    databases = databases + " " + line
                    if databases.endswith(';'):
                        databases = databases + " etc"
                    finish_db_line = 1
                continue
            if " sequences; " in line and " total letters" in line:
                line = databases.strip() + "\n" + line 
            if 'Query=' in line:
                continue
            if 'Length=' in line:
                line = 'Query ' + line
        if ".fsa" in line and "Database:" not in line:
            continue
        blastOutput = blastOutput + "\n" + line
        
    if "Sc_nuclear" in dataset or "Sc_mito" in dataset:
        blastOutput = markupChromosomalCoord(blastOutput)
    else:
        if "NotFeature" not in dataset:
            data = []
            lines = blastOutput.split("\n")
            link_list = ''
            for line in lines:
                if line.startswith('>') and "SGDID:" in line:
                    isDef = 1
                    data.append("<hr><p>")
                    words = line.split(' ')
                    sgdid = ''
                    for word in words:
                        if word.startswith('SGDID:'):
                            sgdid = word.replace('SGDID:', '')
                            sgdid = sgdid.replace(',', '')
                            break
                    data.append(line)
                    link_list = "<b>[ <a href='" + SEQAN + sgdid + "' target='_blastout'>Retrieve Sequence</a> / <a href='" + GBROWSE + sgdid + "' target='_blastout'>Genome Browser</a> / <a href='" + LOCUS + sgdid + "' target='_blastout'>SGD Locus page</a> ]</b>"
                elif line.startswith('>gi') or line.startswith('gi|'):
                    newline = record_line(line)
                    data.append(newline)
                elif line.startswith("Length="):
                    data.append("<br>" + link_list)
                    data.append("<br>" + line)
                    link_list = ''
                else:
                    data.append(line)
            blastOutput = "\n".join(data)
                        
            blastOutput = blastOutput.replace(" Verified ORF", " <font color='green'>Verified ORF</font>")
            blastOutput = blastOutput.replace(" Uncharacterized ORF", " <font color='green'>Uncharacterized ORF</font>")
            blastOutput = blastOutput.replace(" Dubious ORF", "<br> <font color='red'>** Dubious ORF **</font>")

    return blastOutput
            
