infile = 'Y55_SGD_2015_JRIF00000000.fsa'
outfile = 'Y55.fsa'

f = open(infile)
fw = open(outfile, 'w')

for line in f:
    if line.startswith('>'):
        pieces = line.split(' ')
        ids = pieces[0].split('|')
        accession = ids[3]
        wgs = accession[0:6]
        seqId = pieces[5].replace(',', '')
        ID = "gnl|WGS:" + wgs + "|" + seqId + "|gb|" + accession + "|"
        fw.write(">" + ID + " " + " ".join(pieces[1:]))
    else:
        fw.write(line)

f.close()
fw.close()
