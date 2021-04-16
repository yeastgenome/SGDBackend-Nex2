import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Dbentity, Locusdbentity, Taxonomy, Dnasequenceannotation, \
     Dnasubsequence, Proteinsequenceannotation, Contig, Genomerelease, So, \
     Source, LocusAlias 
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

TAXON = 'TAX:559292'
genome_release = '64-3-1'
datafile = 'scripts/loading/sequence/data/newFeaturesOrSubfeatures-Table1_processed.tsv'

def add_data():

    nex_session = get_session()

    src = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = src.source_id
    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    genomerelease = nex_session.query(Genomerelease).filter_by(format_name=genome_release).one_or_none()
    genomerelease_id = genomerelease.genomerelease_id
    soid_to_id = dict([(x.soid, x.so_id) for x in nex_session.query(So).all()])
    
    f = open(datafile)
    
    for line in f:
        if line.startswith('Chromosome'):
            continue
        line = line.replace('"', '')
        pieces = line.strip().split("\t")
        chr = pieces[0]
        gene_name = pieces[1]
        systematic_name = pieces[2]
        feature_type = pieces[3]
        soid = pieces[4]
        coords = pieces[5]
        strand = pieces[6]
        aliases = pieces[7]
        genomicSeq4check = pieces[8]
        codingSeq4check = pieces[9]
        proteinSeq4check = pieces[10]

        if 'null' in gene_name:
            gene_name = ''
            

        (contig_id, start, stop, oneKBstart, oneKBstop, genomicSeq, oneKBseq) =	extract_seqs(nex_session, chr, strand, coords)

        codingSeq = None
        proteinSeq = None
        if feature_type == 'ORF':
            codingSeq = genomicSeq
            seqObj = Seq(codingSeq)
            proteinSeq = seqObj.translate()
        elif feature_type.startswith('ncRNA'):
            codingSeq = genomicSeq
            
        print (">"+systematic_name)
                
        if genomicSeq != genomicSeq4check:
            print ("Error: genomic seq is different for ", systematic_name)
        if codingSeq is not None and codingSeq != codingSeq4check:
            print ("Error: coding seq is different for ", systematic_name)
        if proteinSeq is not None and proteinSeq != proteinSeq4check:
            print ("Error: protein seq is different for ", systematic_name)

        print (systematic_name, "genomic_seq=", genomicSeq)
        print (systematic_name, "coding_seq=", codingSeq)
        print (systematic_name, "oneKBseq=", oneKBseq)
        print (systematic_name, "proteinSeq=", proteinSeq)

        coord_version = str(datetime.now()).split(' ')[0]
        seq_version = coord_version
    
        if feature_type == 'ORF':
            add_orfs(nex_session, source_id, taxonomy_id, start, stop,
                     systematic_name, gene_name, oneKBstart, oneKBstop,
                     soid_to_id[soid], strand, genomicSeq, codingSeq,
                     proteinSeq4check, oneKBseq, coord_version,
                     seq_version, genomerelease_id, feature_type,
                     contig_id, chr)
        elif 'uORF' in feature_type:        
            locus = nex_session.query(Locusdbentity).filter_by(systematic_name=systematic_name).one_or_none()        
            add_uORFs(nex_session, source_id, taxonomy_id, locus.dbentity_id,
                      locus.sgdid, systematic_name, gene_name, start, stop,
                      soid_to_id[soid], strand, genomicSeq,
                      coord_version, seq_version, genomerelease_id)
        elif feature_type.startswith('ncRNA'):
            add_ncRNAs(nex_session, source_id, taxonomy_id, start, stop,
                       systematic_name, gene_name, oneKBstart, oneKBstop,
                       soid_to_id[soid], strand, genomicSeq, codingSeq, oneKBseq,
                       coord_version, seq_version, genomerelease_id,
                       feature_type, aliases, contig_id, chr)
        elif feature_type in ['recombination enhancer', 'long terminal repeat']:
            add_other_features(nex_session, source_id, taxonomy_id, start,
                               stop, systematic_name, gene_name, oneKBstart,
                               oneKBstop, soid_to_id[soid], strand, genomicSeq,
                               oneKBseq, coord_version, seq_version,
                               genomerelease_id, feature_type, contig_id, chr)

    # nex_session.rollback()
    nex_session.commit()
    
    f.close()

def insert_proteinsequenceannotation(nex_session, source_id, dbentity_id, taxonomy_id, contig_id, seq_version, genomerelease_id, file_header, download_filename, seq):

    x = Proteinsequenceannotation(dbentity_id = dbentity_id,
                                  source_id = source_id,
                                  taxonomy_id = taxonomy_id,
                                  contig_id = contig_id,
                                  seq_version = seq_version,
                                  genomerelease_id = genomerelease_id,
                                  file_header = file_header,
                                  download_filename = download_filename,
                                  residues = seq,
                                  created_by = 'OTTO')
    
    nex_session.add(x)

    
def insert_dnasequenceannotation(nex_session, source_id, dbentity_id, taxonomy_id, so_id, dna_type, coord_version, seq_version, genomerelease_id, start, stop, strand, file_header, download_filename, seq, contig_id):

    x = Dnasequenceannotation(dbentity_id = dbentity_id,
                              source_id = source_id,
                              taxonomy_id = taxonomy_id,
                              so_id = so_id,
                              dna_type = dna_type,
                              contig_id = contig_id,
                              seq_version = seq_version,
                              coord_version = coord_version,
                              genomerelease_id = genomerelease_id,
                              start_index = start,
                              end_index = stop,
                              strand = strand,
                              file_header = file_header,
                              download_filename = download_filename,
                              residues = seq,
                              created_by = 'OTTO')
    
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)
    
    return x.annotation_id


def insert_locusdbentity(nex_session, source_id, systematic_name, gene_name, feature_type):
    
    display_name = gene_name
    if display_name == '':
        display_name = systematic_name
        gene_name = None
    
    has_summary = '1'
    has_sequence = '1'
    has_history = '1'
    has_literature = '1'
    has_go = '1'
    has_phenotype = '1'
    has_interaction = '1'
    has_expression = '0'
    has_regulation = '1'
    has_protein = '1'
    has_sequence_section  = '1'
    not_in_s288c = '0'
    has_disease = '0'
    has_homology = '1'
                             
    if feature_type.startswith('ncRNA'):
        has_protein = '0'
        has_homology = '0'
    elif feature_type != 'ORF':
        has_history = '0'
        has_go = '0'
        has_phenotype = '0'
        has_interaction = '0'
        has_regulation = '0'
        has_protein = '0'
        has_homology = '0'
                          
    x = Locusdbentity(format_name = systematic_name,
                      display_name = display_name,
                      source_id = source_id,
                      subclass = 'LOCUS',
                      dbentity_status = 'Active',
                      systematic_name = systematic_name,
                      gene_name = gene_name,
                      has_summary = has_summary,
                      has_sequence = has_sequence,
                      has_history = has_history,
                      has_literature = has_literature,
                      has_go = has_go,
                      has_phenotype = has_phenotype,
                      has_interaction = has_interaction,
                      has_expression = has_expression,
                      has_regulation = has_regulation,
                      has_protein = has_protein,
                      has_sequence_section  = has_sequence_section,
                      not_in_s288c = not_in_s288c,
                      has_disease = has_disease,
                      has_homology = has_homology,
                      created_by = 'OTTO')    

    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)
    
    return (x.dbentity_id, x.sgdid)

    
def insert_locus_alias(nex_session, source_id, locus_id, alias):

    x = LocusAlias(display_name = alias,
                   source_id = source_id,
                   locus_id = locus_id,
                   has_external_id_section = '0',
                   alias_type = 'Uniform',
                   created_by = 'OTTO')

    nex_session.add(x)

    
def add_uORFs(nex_session, source_id, taxonomy_id, dbentity_id, sgdid, systematic_name, gene_name, uORF_start, uORF_stop, so_id, strand, seq, coord_version, seq_version, genomerelease_id):

    print ("Add uORF: ", source_id, taxonomy_id, dbentity_id, sgdid, uORF_start, uORF_stop, so_id, strand, seq, coord_version, seq_version, genomerelease_id)

    ## get parent's coords
    x = nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id=taxonomy_id, dbentity_id=dbentity_id, dna_type='GENOMIC').one_or_none()
    if x is None:
        print ("Could not find genomic seq row for ", systematic_name)
        return
    start = x.start_index
    stop = x.end_index
    
    ## add uORF into dnasubsequence
    relative_start_index = uORF_start - start + 1 
    relative_end_index = uORF_stop - start + 1
    if gene_name == '':
        gene_name = systematic_name
    file_header = ">" + systematic_name + " " + gene_name + " uORF:" + str(uORF_start) + ".." + str(uORF_stop)
    display_name = 'uORF'
    so = nex_session.query(So).filter_by(display_name=display_name).one_or_none()
    so_id = so.so_id
    download_filename = systematic_name + "_uORF.fsa"
    insert_dnasubsequence(nex_session, dbentity_id, x.annotation_id,
                          display_name, so_id, genomerelease_id,
                          coord_version, seq_version, relative_start_index,
                          relative_end_index, uORF_start, uORF_stop,
                          file_header, download_filename, seq)

    
def add_other_features(nex_session, source_id, taxonomy_id, start, stop, systematic_name, gene_name, oneKBstart, oneKBstop, so_id, strand, genomicSeq, oneKBseq, coord_version, seq_version, genomerelease_id, feature_type, contig_id, chr):
                               
    print ("Add other feature: ", source_id, taxonomy_id, start, stop, systematic_name, gene_name, oneKBstart, oneKBstop, so_id, strand, genomicSeq, oneKBseq, coord_version, seq_version, genomerelease_id, feature_type)
    
    ## add ORF into dbentity and locusdbentity
    (dbentity_id, sgdid) = insert_locusdbentity(nex_session, source_id, systematic_name,
                                                gene_name, feature_type)
    
    ## add GENOMIC seq into dnasequenceannotation table
    if gene_name == '':
        gene_name = systematic_name
    print (">>", systematic_name, gene_name, sgdid, chr)
    file_header0 = ">" + systematic_name + " " + gene_name + " SGDID:" + sgdid + ", " + "chr" + chr + ":"
    file_header = file_header0 + str(start) + ".." + str(stop) + " [Genome Release 64-3-1]"
    download_filename = systematic_name + "-genomic.fsa"
    annotation_id = insert_dnasequenceannotation(nex_session, source_id, dbentity_id,
                                                 taxonomy_id, so_id, 'GENOMIC', coord_version,
                                                 seq_version, genomerelease_id, start,
                                                 stop, strand, file_header,
                                                 download_filename, genomicSeq, contig_id)
    
    ## add 1KB seq into dnasequenceannotation table
    file_header = file_header0 + str(oneKBstart) + ".." + str(oneKBstop) + " +/- 1kb [Genome Release 64-3-1]"
    download_filename = systematic_name + "-1kb.fsa"
    annotation_id_1kb = insert_dnasequenceannotation(nex_session, source_id, dbentity_id,
                                                     taxonomy_id, so_id, '1KB', coord_version,
                                                     seq_version, genomerelease_id, oneKBstart,
                                                     oneKBstop, strand, file_header,
                                                     download_filename, oneKBseq, contig_id)


def add_ncRNAs(nex_session, source_id, taxonomy_id, start, stop, systematic_name, gene_name, oneKBstart, oneKBstop, so_id, strand, genomicSeq, codingSeq, oneKBseq, coord_version, seq_version, genomerelease_id, feature_type, aliases, contig_id, chr):
    
    print ("Add ncRNA: ", source_id, taxonomy_id, start, stop, systematic_name, gene_name, oneKBstart, oneKBstop, so_id, strand, genomicSeq, oneKBseq, coord_version, seq_version, genomerelease_id, feature_type)
    
    ## add ORF into dbentity and locusdbentity
    (dbentity_id, sgdid) = insert_locusdbentity(nex_session, source_id, systematic_name,
                                                gene_name, feature_type)
    
    ## add aliases into locus_alias table
    for alias in aliases.split(' '):
        insert_locus_alias(nex_session, source_id, dbentity_id, alias)
    
    ## add GENOMIC seq into dnasequenceannotation table
    file_header0 = ">" + systematic_name + " " + gene_name + " SGDID:" + sgdid + ", " + "chr" + chr + ":"
    file_header = file_header0 + str(start) + ".." + str(stop) + " [Genome Release 64-3-1]"
    download_filename = systematic_name + "-genomic.fsa"
    annotation_id = insert_dnasequenceannotation(nex_session, source_id, dbentity_id,
                                                 taxonomy_id, so_id, 'GENOMIC', coord_version,
                                                 seq_version, genomerelease_id, start,
                                                 stop, strand, file_header,
                                                 download_filename, genomicSeq, contig_id)

    ## add CODING seq into dnasequenceannotation table
    download_filename = systematic_name + "-coding.fsa"
    annotation_id_coding = insert_dnasequenceannotation(nex_session, source_id, dbentity_id,
                                    taxonomy_id, so_id, 'CODING', coord_version, seq_version,
                                    genomerelease_id, start, stop, strand,
                                    file_header, download_filename, codingSeq, contig_id)

    ## add 1KB seq into dnasequenceannotation table
    file_header = file_header0 + str(oneKBstart) + ".." + str(oneKBstop) + " +/- 1kb [Genome Release 64-3-1]"
    download_filename = systematic_name + "-1kb.fsa"
    annotation_id_1kb = insert_dnasequenceannotation(nex_session, source_id, dbentity_id,
                                                     taxonomy_id, so_id, '1KB', coord_version,
                                                     seq_version, genomerelease_id, oneKBstart,
                                                     oneKBstop, strand, file_header,
                                                     download_filename, oneKBseq, contig_id)
    


    
    ## add noncoding_exon into dnasubsequence
    relative_start_index = 1
    relative_end_index = stop - start + 1
    if gene_name == '':
        gene_name = systematic_name
    file_header = ">" + systematic_name + " " + gene_name + " noncoding_exon:" + str(start) + ".." + str(stop)
    display_name = 'noncoding_exon'
    so = nex_session.query(So).filter_by(term_name=display_name).one_or_none()
    so_id = so.so_id
    download_filename = systematic_name + "_noncoding_exon.fsa"
    insert_dnasubsequence(nex_session, dbentity_id, annotation_id,
                          display_name, so_id, genomerelease_id,
                          coord_version, seq_version, relative_start_index,
                          relative_end_index, start, stop, file_header,
                          download_filename, genomicSeq)

    
def add_orfs(nex_session, source_id, taxonomy_id, start, stop, systematic_name, gene_name, oneKBstart, oneKBstop, so_id, strand, genomicSeq, codingSeq, proteinSeq, oneKBseq, coord_version, seq_version, genomerelease_id, feature_type, contig_id, chr):

    print ("Add ORF: ", source_id, taxonomy_id, contig_id, start, stop, systematic_name, gene_name, oneKBstart, oneKBstop, so_id, strand, genomicSeq, codingSeq, proteinSeq, oneKBseq, coord_version, seq_version, genomerelease_id, feature_type)
    
    ## add ORF into dbentity and locusdbentity
    (dbentity_id, sgdid) = insert_locusdbentity(nex_session, source_id, systematic_name,
                                                gene_name, feature_type)


    
    ## add GENOMIC seq into dnasequenceannotation table
    file_header0 = ">" + systematic_name + " " + gene_name + " SGDID:" + sgdid + ", " + "chr" + chr + ":"
    file_header = file_header0 + str(start) + ".." + str(stop) + " [Genome Release 64-3-1]"
    download_filename = systematic_name + "-genomic.fsa"
    annotation_id = insert_dnasequenceannotation(nex_session, source_id, dbentity_id,
                                                 taxonomy_id, so_id, 'GENOMIC', coord_version,
                                                 seq_version, genomerelease_id, start,
                                                 stop, strand, file_header,
                                                 download_filename, genomicSeq, contig_id)
    
    ## add CODING seq into dnasequenceannotation table
    download_filename =	systematic_name + "-coding.fsa"
    annotation_id_coding = insert_dnasequenceannotation(nex_session, source_id, dbentity_id,
                                    taxonomy_id, so_id, 'CODING', coord_version, seq_version,
                                    genomerelease_id, start, stop, strand,
                                    file_header, download_filename, codingSeq, contig_id)

    ## add protein seq into proteinsequenceannotation table
    download_filename = systematic_name + "-protein.fsa"
    insert_proteinsequenceannotation(nex_session, source_id, dbentity_id, taxonomy_id,
                                         contig_id, seq_version, genomerelease_id,
                                         file_header, download_filename, proteinSeq)
      
    ## add 1KB seq into dnasequenceannotation table
    file_header = file_header0 + str(oneKBstart) + ".." + str(oneKBstop) + " +/- 1kb [Genome Release 64-3-1]"
    download_filename = systematic_name + "-1kb.fsa"
    annotation_id_1kb = insert_dnasequenceannotation(nex_session, source_id, dbentity_id,
                                                     taxonomy_id, so_id, '1KB', coord_version,
                                                     seq_version, genomerelease_id, oneKBstart,
                                                     oneKBstop, strand, file_header,
                                                     download_filename, oneKBseq, contig_id)

    ## add CDS into dnasubsequence
    relative_start_index = 1
    relative_end_index = stop - start + 1
    if gene_name == '':
        gene_name = systematic_name
    file_header = ">" + systematic_name + " " + gene_name + " CDS:" + str(start) + ".." + str(stop)
    display_name = 'CDS'
    so = nex_session.query(So).filter_by(display_name=display_name).one_or_none()
    so_id = so.so_id
    download_filename = systematic_name + "_CDS.fsa"
    insert_dnasubsequence(nex_session, dbentity_id, annotation_id,
                          display_name, so_id, genomerelease_id,
                          coord_version, seq_version, relative_start_index,
                          relative_end_index, start, stop, file_header, 
                          download_filename, codingSeq)

    
def insert_dnasubsequence(nex_session, dbentity_id, annotation_id, display_name, so_id, genomerelease_id, coord_version, seq_version, relative_start_index, relative_end_index, contig_start_index, contig_end_index, file_header, download_filename, seq):

    print ("Insert dnasubsequence: ", dbentity_id, annotation_id, display_name, so_id, genomerelease_id, coord_version, seq_version, relative_start_index, relative_end_index, contig_start_index, contig_end_index, file_header, download_filename, seq)
    
    x = Dnasubsequence(dbentity_id = dbentity_id,
                       annotation_id = annotation_id,
                       display_name = display_name,
                       so_id = so_id,
                       genomerelease_id = genomerelease_id,
                       coord_version = coord_version,
                       seq_version = seq_version,
                       relative_start_index = relative_start_index,
                       relative_end_index = relative_end_index,
                       contig_start_index = contig_start_index,
                       contig_end_index = contig_end_index,
                       file_header = file_header,
                       download_filename = download_filename,
                       residues = seq,
                       created_by = 'OTTO')
    nex_session.add(x)
    
def extract_seqs(nex_session, chr, strand, new_coords):

    contig = nex_session.query(Contig).filter_by(format_name='Chromosome_'+chr).one_or_none()

    chrSeq = contig.residues
    contig_id = contig.contig_id

    [start, stop] = new_coords.split('..')
    start = int(start)
    stop = int(stop)
    genomicSeq = chrSeq[start-1:stop]
    oneKBstart = start - 1000
    oneKBstop = stop + 1000
    oneKBseq = chrSeq[oneKBstart-1:oneKBstop]

    if strand == '-':
        genomicSeq = reverse_complement(genomicSeq)
        oneKBseq = reverse_complement(oneKBseq)
    
    return (contig_id, start, stop, oneKBstart, oneKBstop, genomicSeq, oneKBseq)

def reverse_complement(seq):

    complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
    bases = list(seq)
    bases = reversed([complement.get(base,base) for base in bases])
    bases = ''.join(bases)
    return bases

if __name__ == '__main__':

    add_data()
