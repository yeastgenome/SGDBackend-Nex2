import os

indir = "data/blast_datasets_for_sgd"
outdir = "data/blast_datasets_for_alliance"


for filename in os.listdir(indir):
    infile = os.path.join(indir, filename)
    outfile = os.path.join(outdir, filename)
    if os.path.isfile(infile):
        # print(infile)
        # print(outfile)
        f = open(infile)
        fw = open(outfile, 'w')
        found = {}
        good_header = 1
        for line in f:
            if line.startswith('>'):
                pieces = line.split(' ')
                if pieces[0] in found:
                    print (infile, " Duplicate row-1:", found[pieces[0]])
                    print (infile, " Duplicate row-2:", line)
                    good_header = 0
                else:
                    good_header = 1
                found[pieces[0]] = line
            if good_header == 1:
                fw.write(line)
        f.close()
        fw.close()
        
