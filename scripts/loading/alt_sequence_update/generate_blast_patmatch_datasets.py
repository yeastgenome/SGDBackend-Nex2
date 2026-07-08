indir = "data/"
blastOutDir = "data/blast/"
patmatchOutDir = "data/patmatch/"


def generate_files():
    
    for strain in ["CEN.PK2-1Ca_JRIV01000000", "D273-10B_JRIY00000000",
                   "FL100_JRIT00000000", "JK9-3d_JRIZ00000000",
                   "RM11-1a_JRIP00000000", "SEY6210_JRIW00000000",
                   "SK1_NCSL00000000", "Sigma1278b-10560-6B_JRIQ00000000",
                   "W303_JRIU00000000", "X2180-1A_JRIX00000000",
                   "Y55_JRIF00000000"]:

        cdsFile = indir + strain + "_SGD_orf_genomic.fsa"
        proteinFile = indir + strain + "_SGD_pep.fsa"
           
        blastCDSfile = blastOutDir + strain + "_SGD_cds.fsa"
        blastProteinFile = blastOutDir + strain + "_SGD_pep.fsa"
           
        patmatchCDSfile = patmatchOutDir + strain	+ "_SGD_cds.seq"
        patmatchProteinFile = blastOutDir + strain + "_SGD_pep.seq"

        generate_file(cdsFile, blastCDSfile, patmatchCDSfile)
        generate_file(proteinFile, blastProteinFile, patmatchProteinFile)
        
        
def generate_file(inFile, blastFile, patmatchFile):
    
    f = open(inFile)
    fw = open(blastFile, "w")
    fw2 = open(patmatchFile, "w")
    
    is_first = True
    for line in f:
        line = line.replace('"', '')
        fw.write(line)
        if line.startswith('>'):
            if is_first:
                fw2.write(line)
                is_first = False
            else:
                fw2.write("\n" + line)
        else:
            fw2.write(line.strip())
    f.close()
    fw.close()
    fw2.close()
    
             
if __name__ == "__main__":

    generate_files()
