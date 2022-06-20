import hashlib
import gzip
from pathlib import Path



fasta_file = Path(str("./Sc_nuclear_chr.fsa.20220427.gz"))
with fasta_file.open(mode="rb") as fh:
    actual_checksum = hashlib.md5(fh.read()).hexdigest()
    print ("actual_checksum=", actual_checksum)

## actual_checksum= d223aa4e2a13da4a145eca5224de108f    


exit

## d223aa4e2a13da4a145eca5224de108f  from Josh

## 0365b4c2dcaf8f913c6e3f9e0681aaa6 from metadata file




