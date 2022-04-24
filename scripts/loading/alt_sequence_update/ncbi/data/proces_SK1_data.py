infile = 'SK1_SGD_2018_NCSL00000000.fsa'
outfile = 'SK1.fsa'
mappingfile = '../seqID_contig_mapping_files/NCSL01_accs'

f = open(mappingfile)

contig_to_seqID = {}

for line in f:
    pieces = line.strip().split('\t')
    contig_to_seqID[pieces[1]] = pieces[0]
f.close()

f = open(infile)
fw = open(outfile, 'w')

for line in f:
    if line.startswith('>'):
        pieces = line.split(' ')
        accession = pieces[0].replace('>', '').replace('.1', '')
        wgs = accession[0:6]
        seqID = contig_to_seqID[accession]
        fw.write(">gnl|WGS:" + wgs + "|" + seqID + "|gb|" + accession + "| Saccharomyces cerevisiae strain SK1 " + seqID + ", whole genome sequence\n") 
    else:
        fw.write(line)

f.close()
fw.close()
        
