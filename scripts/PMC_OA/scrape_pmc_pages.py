from urllib.request import Request, urlopen
import time

searched = "data/pmc_oa_tar_ball_url.lst_BK"
urlFile = 'data/pmc_oa_url.lst'

f = open(searched)

found = {}
for line in f:
    pieces = line.strip().split("\t")
    if len(pieces) < 2:
        continue
    pmc_oa_url = pieces[1]
    pmc_oa_url_root = pmc_oa_url.split("/PMC")[0]
    found[pmc_oa_url_root] = 1
f.close()

f = open(urlFile)

i = 0
# start = 0
for url in f:
    url = url.strip()
    if url in found:
        continue
    # if url.startswith('ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/1f/14'):
    #     start = 1
    # if start == 0:
    #    continue
    i = i + 1
    if i > 100:
        time.sleep(1)
        i = 0
    try:
        res = urlopen(url)
        page = res.read().decode('utf-8')
        lines = page.split("\n")
        for line in lines:
            pieces = line.strip().split(' ')
            pmc_file = pieces[-1]
            if pmc_file == '':
                continue
            print (pmc_file.replace('.tar.gz', '') + "\t" + url + "/" + pmc_file)
    except:
        exit
