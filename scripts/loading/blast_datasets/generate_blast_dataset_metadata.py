infile = "data/blast_dataset.lst"

f = open(infile)

for line in f:
    dataset = line.strip()
    if dataset.startswith('Sc_nuclear'):
        print (dataset + "\tS288C reference nuclear chromosome sequences")
    elif dataset.startswith('Sc_mito'):
        print (dataset + "\tS288C reference mitochrondrial chromosome sequence")
    elif dataset.startswith('2-micron'):
        print (dataset + "\tS288C reference 2-micron plasmid DNA sequence")
    elif dataset.startswith('YeastORF'):
        if 'pep' in dataset:
            print (dataset + "\tS288C reference protein sequences")
        elif 'Genomic-1K' in dataset:
            print (dataset + "\tS288C reference ORF genomic sequences +/- 1kb")
        elif 'Genomic' in dataset:
            print (dataset + "\tS288C reference ORF genomic sequences")
        else:
            print (dataset + "\tS288C reference ORF coding sequences")
    elif dataset.startswith('YeastRNA'):
        if 'coding' in dataset:
            print (dataset + "\tS288C reference RNA coding sequences")
        elif 'genomic-1K' in dataset:
            print (dataset + "\tS288C reference RNA genomic sequences +/- 1kb")
        else:
            print (dataset + "\tS288C reference RNA genomic sequences")
    elif dataset.startswith('NotFeature'):
        print (dataset + "\tS288C reference non-genic sequences (intergenic regions)")
    elif dataset.startswith('YeastVectorDB'):
        print (dataset + "\tYeast cloning vector sequences from Vector DB")
    else:
        pieces = dataset.split('_')
        if len(pieces) < 3:
            continue
        strain = pieces[0]
        src = pieces[1]
        if 'SGD' in dataset:
            src = 'SGD'
        if '_cds' in dataset:
            print (dataset + "\t" + strain + " (" + src + ") strain ORF coding sequences")
        elif '_pep' in dataset:
            print (dataset + "\t" + strain + " (" + src + ") strain protein sequences")
        else:
            print (dataset + "\t" + strain + " (" + src + ") strain contig genomic sequences")

f.close()
