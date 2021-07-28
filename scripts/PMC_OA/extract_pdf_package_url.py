infile = '../dumping/paper/data/pmcid_2021.txt'
infile2 = 'data/pmc_oa_tar_ball_url.lst'

f = open(infile)

pmc2pmidEtc = {}
for line in f:
    pieces = line.strip().split('\t')
    pmc2pmidEtc[pieces[1]] = (pieces[0], pieces[2])
f.close()

f = open(infile2)

for line in f:
    pieces = line.strip().split('\t')
    if pieces[0] not in pmc2pmidEtc:
        continue
    pmc = pieces[0]
    (pmid, year) = pmc2pmidEtc[pmc]
    print (pmc + "\t" + pmid + "\t" + year + "\t" + pieces[1])
f.close()


