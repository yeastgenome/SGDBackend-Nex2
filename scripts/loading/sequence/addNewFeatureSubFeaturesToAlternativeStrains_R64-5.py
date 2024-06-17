import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Dbentity, Locusdbentity, Taxonomy, Dnasequenceannotation, \
     Dnasubsequence, Proteinsequenceannotation, Contig, Genomerelease, So, \
     Source, LocusAlias 
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

genome_release = '64-5-1'
datafile = 'scripts/loading/sequence/data/newORFsInAltRefs060324correctedAgainAgain.tsv'

"""
CENPK      275338
D273-10B   275315
FL100      274944
JK9-3d     275321
RM11-1a    274425
SEY6210    275326
Sigma1278b 274916
SK1        274909
W303       274910
X2180-1A   275329
Y55        275334
"""

def add_data():

    nex_session = get_session()

    src = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = src.source_id
    genomerelease = nex_session.query(Genomerelease).filter_by(format_name=genome_release).one_or_none()
    genomerelease_id = genomerelease.genomerelease_id
    so = nex_session.query(So).filter_by(display_name='ORF').one_or_none()
    orf_so_id = so.so_id
    
    rows = nex_session.execute("select display_name, taxonomy_id from nex.taxonomy where taxonomy_id in "
                               "(select distinct taxonomy_id from nex.proteinsequenceannotation)").fetchall()
    strain_to_taxonomy_id = {}
    for x in rows:
        strain = x['display_name'].replace("Saccharomyces cerevisiae ", "")
        strain_to_taxonomy_id[strain] = x['taxonomy_id']
    
    f = open(datafile)

    strains = []
    strain_to_data = {}
    for line in f:
        if line.startswith('\t'):
            strains = line.strip().split("\t")
            continue
        pieces = line.strip().split("\t")
        systematic_name = pieces[0].split(":")[0]
        gene_name = None
        if " / " in systematic_name:
            gene_name = systematic_name.split(" / ")[0]
            systematic_name = systematic_name.split(" / ")[1]
        featureCoords = pieces[1:]
        index = 0
        for featureCoord in featureCoords:
            strain = strains[index]
            index += 1
            # JRIT01000213.1:19470..19297
            if ':' in featureCoord and '..' in featureCoord:
                contig, coords = featureCoord.split(':')
                start, stop = coords.split('..')
                data = strain_to_data.get(strain, [])
                data.append((systematic_name, gene_name, contig, int(start), int(stop), featureCoord))
                strain_to_data[strain] = data

    for strain in strain_to_data:
        for row in strain_to_data[strain]:
            taxonomy_id = strain_to_taxonomy_id[strain]
            (systematic_name, gene_name, contig, start, stop, featureCoord) = row

            print("HELLO", strain, systematic_name, contig, featureCoord)
                
            if contig is None:
                continue
            strand = '+'
            if start > stop:
                strand = '-'
                (start, stop) = (stop, start)

            isCoordsError = False
            if (stop - start + 1) % 3 != 0:
                isCoordsError = True
                print("ERROR:", strain, systematic_name, featureCoord, "len(sequence) is not a multiple of three")
                # SK1 YHR054C-B NCSL01000007.1
                continue
            
            print(featureCoord, contig, strand, start, stop)

            (contig_id, start, stop, oneKBstart, oneKBstop, genomicSeq, oneKBseq) = \
                extract_seqs(nex_session, contig, strand, start, stop)

            if not genomicSeq.startswith('ATG'):
                print("ERROR:", strain, systematic_name, featureCoord, "The genomic/coding sequence is not starting with 'ATG'")
                continue

            if len(oneKBseq) == 0:
                print("ERROR:", strain, systematic_name, featureCoord, "1KB seq is None")
                continue
            
            codingSeq = None
            proteinSeq = None
            codingSeq = genomicSeq
            # print(strain, systematic_name, "codingSeq=", codingSeq)
            seqObj = Seq(codingSeq)
            proteinSeq = seqObj.translate()
            proteinSeq = str(proteinSeq)
            # print("proteinSeq=", proteinSeq)
            coord_version = str(datetime.now()).split(' ')[0]
            seq_version = coord_version

            if not proteinSeq.endswith('*'):
                print("ERROR:", strain, systematic_name, featureCoord, "protein sequence not ending in *")

            add_orf_sequences(nex_session, strain, source_id, taxonomy_id, start, stop,
                              systematic_name, gene_name, oneKBstart, oneKBstop,
                              orf_so_id, strand, genomicSeq, codingSeq,
                              proteinSeq, oneKBseq, coord_version,
                              seq_version, genomerelease_id, contig_id, featureCoord)
            
    # nex_session.rollback()
    nex_session.commit()
    
    f.close()


def insert_dnasequenceannotation(nex_session, source_id, dbentity_id, taxonomy_id, so_id, dna_type, coord_version, seq_version, genomerelease_id, start, stop, strand, file_header, download_filename, seq, contig_id):

    print("Insert dnasequenceannotation: ", source_id, dbentity_id, taxonomy_id, so_id, dna_type, coord_version, seq_version, genomerelease_id, start, stop, strand, file_header, download_filename, seq, contig_id)
    
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


def add_orf_sequences(nex_session, strain, source_id, taxonomy_id, start, stop, systematic_name, gene_name, oneKBstart, oneKBstop, so_id, strand, genomicSeq, codingSeq, proteinSeq, oneKBseq, coord_version, seq_version, genomerelease_id, contig_id, contigNameCoords):

    rows = nex_session.execute("SELECT dbentity_id FROM nex.dbentity "
                              "WHERE format_name = '" + systematic_name + "'").fetchall()
    dbentity_id = rows[0][0] 
    if gene_name is None:
        gene_name = systematic_name
    
    ## add GENOMIC seq into dnasequenceannotation table
    file_header = ">" + systematic_name + " " + gene_name + " "  + strain + " " + contigNameCoords
    download_filename = systematic_name + "_" + strain + "-genomic.fsa"
    annotation_id = insert_dnasequenceannotation(nex_session, source_id, dbentity_id,
                                                 taxonomy_id, so_id, 'GENOMIC', coord_version,
                                                 seq_version, genomerelease_id, start,
                                                 stop, strand, file_header,
                                                 download_filename, genomicSeq, contig_id)

    ## add CODING seq into dnasequenceannotation table
    download_filename =	systematic_name + "_" + strain + "-coding.fsa"
    annotation_id_coding = insert_dnasequenceannotation(nex_session, source_id, dbentity_id,
                                    taxonomy_id, so_id, 'CODING', coord_version, seq_version,
                                    genomerelease_id, start, stop, strand,
                                    file_header, download_filename, codingSeq, contig_id)

    ## add protein seq into proteinsequenceannotation table
    file_header = ">" + systematic_name + " " + gene_name + " " + contigNameCoords
    download_filename = systematic_name + "-protein.fsa"
    insert_proteinsequenceannotation(nex_session, source_id, dbentity_id, taxonomy_id,
                                         contig_id, seq_version, genomerelease_id,
                                         file_header, download_filename, proteinSeq)

    ## add 1KB seq into dnasequenceannotation table  
    contigNameCoords1KB = contigNameCoords.split(':')[0]
    if strand == '+':
        contigNameCoords1KB = contigNameCoords1KB + ":" + str(oneKBstart) + ".." + str(oneKBstop)
    else:
        contigNameCoords1KB = contigNameCoords1KB + ":" + str(oneKBstop) + ".." + str(oneKBstart)
    file_header = ">" + systematic_name + " " + gene_name + " "  + strain + " " + contigNameCoords1KB + " +/- 1kb"
    download_filename = systematic_name + "-1kb.fsa"
    annotation_id_1kb = insert_dnasequenceannotation(nex_session, source_id, dbentity_id,
                                                     taxonomy_id, so_id, '1KB', coord_version,
                                                     seq_version, genomerelease_id, oneKBstart,
                                                     oneKBstop, strand, file_header,
                                                     download_filename, oneKBseq, contig_id)

    ## add CDS into dnasubsequence
    relative_start_index = 1
    relative_end_index = stop - start + 1
    file_header = ">" + systematic_name + " " + gene_name + " CDS:" + str(start) + ".." + str(stop)
    display_name = 'CDS'
    so = nex_session.query(So).filter_by(display_name=display_name).one_or_none()
    so_id = so.so_id
    download_filename = systematic_name + "_" + strain + "_CDS.fsa"
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

    
def insert_proteinsequenceannotation(nex_session, source_id, dbentity_id, taxonomy_id, contig_id, seq_version, genomerelease_id, file_header, download_filename, seq):

    print("Insert proteinsequenceannotation: ", dbentity_id, taxonomy_id, contig_id, seq_version, genomerelease_id, file_header, download_filename, seq)
    
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
    

def extract_seqs(nex_session, contig, strand, start, stop):

    contig = nex_session.query(Contig).filter_by(format_name=contig).one_or_none()

    contigSeq = contig.residues
    contig_id = contig.contig_id

    genomicSeq = contigSeq[start-1:stop]

    oneKBstart = start - 1000
    if oneKBstart < 1:
        oneKBstart = 1
    oneKBstop = stop + 1000
    if oneKBstop > len(contigSeq):
        oneKBstop = len(contigSeq)
    oneKBseq = contigSeq[oneKBstart-1:oneKBstop]

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
