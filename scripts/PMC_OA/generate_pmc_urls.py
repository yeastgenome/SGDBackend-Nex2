from urllib.request import Request, urlopen
import time

url = 'ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/'

index = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']

for a in index:   ## 16
    for b in index:  ## 16*16
        # fw = open(dataDir + a + b + '.lst', 'w')
        sub_url = url + a + b + '/'
        for c in index:    # 16*16*16
            for d in index:  # 16*16*16*16  => 16*16*16*80
                sub_sub_url = sub_url + c + d
                print (sub_sub_url)
  
