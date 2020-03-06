# loop through each fasta seq row from all 12 strains and create a file for each feature if there are two or more strains have the seq for the given feature

inDir = "data/not_feature_fasta/"
outDir = "data/not_feature_seq/"

ref_strain_file = inDir + "not_feature_S288C.fsa"

alt_strains = [ "W303", "FL100", "CEN.PK", "Sigma1278b", "SK1", "D273-10B",
                "X2180-1A", "Y55", "JK9-3d", "SEY6210", "RM11-1a" ]

altSeqID2seq = {}
for strain in alt_strains:
    file = inDir + "not_feature_" + strain + ".fsa"
    f = open(file)
    seqID = None
    for line in f:
        if line.startswith(">"):
            seqID = line.split(' ')[0]
        else:
            altSeqID2seq[seqID] = line
    f.close()
    
f = open(ref_strain_file)

seqID = None

for line in f:

    if line.startswith(">"):

        seqID = line.split(' ')[0]

    else:

        seq = line

        count = 0
        for strain in alt_strains:
            altSeqID = seqID.replace('S288C', strain)
            if altSeqID in altSeqID2seq:
                count = count + 1
                
        if count > 0:
            outfile = outDir + seqID.replace("|S288C", "").replace(">", "").replace("|", "_") + ".seq"
            fw = open(outfile, "w")
            fw.write(seqID.replace("|", "_") + "\n")
            fw.write(seq)
            for strain in alt_strains:
                altSeqID = seqID.replace('S288C', strain)
                if altSeqID in altSeqID2seq:
                    fw.write(altSeqID.replace("|", "_") + "\n")
                    fw.write(altSeqID2seq[altSeqID])
            fw.close()
