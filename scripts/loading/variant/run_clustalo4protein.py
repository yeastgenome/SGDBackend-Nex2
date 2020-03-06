import os
from os import path

seqDir = "./data/protein_seq/"
alignDir = "./data/protein_align/"
for filename in os.listdir(seqDir):
    alignfile = filename.replace(".seq", ".align")
    outfile = alignDir + alignfile
    infile = seqDir + filename
    if path.exists(outfile):
        continue
    cmd = "/usr/local/bin/clustalo -i " + infile + " --outfmt=clu -o " +  outfile
    os.system(cmd)
