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
genome_release = '64-5-1'
datafile = 'scripts/loading/sequence/data/R64-5genomeUpdate050724.tsv'

# insert into nex.genomerelease (format_name, display_name, obj_url, source_id,
#                                sequence_release, annotation_release,
#                                curation_release, release_date, created_by)
# values ('64-5-1', '64-5-1', '/genomerelease/64-5-1', 834, 64, 5, 1, '2024-05-13', 'OTTO');


def add_data():

    nex_session = get_session()

    src = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = src.source_id
    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    genomerelease = nex_session.query(Genomerelease).filter_by(format_name=genome_release).one_or_none()
    genomerelease_id = genomerelease.genomerelease_id
    so = nex_session.query(So).filter_by(display_name='ORF').one_or_none()
    orf_so_id = so.so_id
    
    f = open(datafile)

    for line in f:
        if line.startswith('gene'):
            continue
        pieces = line.strip().split("\t")
        gene_name = pieces[0] if pieces[0] != 'None' else '' 
        systematic_name = pieces[1].strip()
        chr = pieces[2]
        strand = pieces[3]
        note = pieces[4].replace('"', "")                              
        coordinates = pieces[5].strip().replace('"', "")
        genomicSeq4check = pieces[6].replace('"', "")
        pmids = pieces[7].split("|")

        start = None
        stop = None
        coords = coordinates
        if coordinates.startswith("old chr") and " new chr" in coordinates:
            coords = coordinates.split(" new ")[1]
        if coords.startswith("chr"):
            coords = coords.split(":")[1].split("..")
            start = int(coords[0])
            stop = int(coords[1])

        # print("systematic_name=", systematic_name, ", gene_name=", gene_name, ", chr=", chr, ", strand=", strand, ", note=", note, ", coords=", coords, ", pmids=", pmids)
            
        if strand == 'C':
            strand = '-'
            if stop < start:
                (start, stop) = (stop, start)
        else:
            strand = '+'

        (contig_id, start, stop, oneKBstart, oneKBstop, genomicSeq, oneKBseq) = \
            extract_seqs(nex_session, chr, strand, start, stop)
    
        # print(chr, strand, start, stop)
    
        codingSeq = None
        proteinSeq = None
        if 'new ORF' in note or "move start" in note.lower():
            codingSeq = genomicSeq
            seqObj = Seq(codingSeq)
            proteinSeq = seqObj.translate()
            proteinSeq = str(proteinSeq)
            # print("proteinSeq=", proteinSeq)

        if genomicSeq != genomicSeq4check:
            print ("Error: genomic seq is different for ", systematic_name)
            print (systematic_name, "genomic_seq     =", genomicSeq)
            print (systematic_name, "genomicSeq4check=", genomicSeq4check)
            continue
            
        # print (systematic_name, "genomic_seq=", genomicSeq)
    
        coord_version = str(datetime.now()).split(' ')[0]
        seq_version = coord_version

        if 'new uORF' in note:        
            locus = nex_session.query(Locusdbentity).filter_by(systematic_name=systematic_name).one_or_none()        
            add_uORFs(nex_session, source_id, taxonomy_id, locus.dbentity_id,
                      locus.sgdid, systematic_name, gene_name, start, stop,
                      strand, genomicSeq, coord_version, seq_version, genomerelease_id)
        elif 'new ORF' in note:
            add_orfs(nex_session, source_id, taxonomy_id, start, stop,
                     systematic_name, gene_name, oneKBstart, oneKBstop,
                     orf_so_id, strand, genomicSeq, codingSeq,
                     proteinSeq, oneKBseq, coord_version,
                     seq_version, genomerelease_id, contig_id, chr)
        elif 'old chr' in coordinates and ' new chr' in coordinates:
            update_orf_sequences(nex_session, source_id, taxonomy_id, start, stop,
                                 systematic_name, gene_name, oneKBstart, oneKBstop,
                                 orf_so_id, strand, genomicSeq, codingSeq,
                                 proteinSeq, oneKBseq, coord_version, seq_version,
                                 genomerelease_id, contig_id, chr)
        
    # nex_session.rollback()
    nex_session.commit()
    
    f.close()


def insert_dnasequenceannotation(nex_session, source_id, dbentity_id, taxonomy_id, so_id, dna_type, coord_version, seq_version, genomerelease_id, start, stop, strand, file_header, download_filename, seq, contig_id):

    print(source_id, dbentity_id, taxonomy_id, so_id, dna_type, coord_version, seq_version, genomerelease_id, start, stop, strand, file_header, download_filename, seq, contig_id)
    
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


def insert_locusdbentity(nex_session, source_id, systematic_name, gene_name):
    
    display_name = gene_name
    if display_name == '':
        display_name = systematic_name
        gene_name = None
    
    has_summary = True
    has_sequence = True
    has_history = True
    has_literature = True
    has_go = True
    has_phenotype = True
    has_interaction = True
    has_expression = False
    has_regulation = True
    has_protein = True
    has_sequence_section  = True
    not_in_s288c = False
    has_disease = False
    has_homology = True
                                               
    x = Locusdbentity(format_name = systematic_name,
                      display_name = display_name,
                      source_id = source_id,
                      subclass = 'LOCUS',
                      dbentity_status = 'Active',
                      qualifier = 'Verified',
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


def update_orf_sequences(nex_session, source_id, taxonomy_id, start, stop, systematic_name, gene_name, oneKBstart, oneKBstop, so_id, strand, genomicSeq, codingSeq, proteinSeq, oneKBseq, coord_version, seq_version, genomerelease_id, contig_id, chr):

    ## no intron for updated ORF YIL064W
    
    locus = nex_session.query(Locusdbentity).filter_by(systematic_name=systematic_name).one_or_none()
    dbentity_id = locus.dbentity_id
    sgdid = locus.sgdid
        
    file_header0 = ">" + systematic_name + " " + gene_name + " SGDID:" + sgdid + ", " + "chr" + chr + ":"

    # update genomic seq
    file_header = file_header0 + str(start) + ".." + str(stop) + " [Genome Release 64-5-1]" 
    annotation_id = update_dnasequenceannotation(nex_session, dbentity_id, taxonomy_id,
                                                 'GENOMIC', coord_version, seq_version,
                                                 genomerelease_id, start, stop,
                                                 file_header, genomicSeq)
    # update coding seq
    coding_file_header = file_header
    annotation_id_coding = update_dnasequenceannotation(nex_session,
                                                        dbentity_id, taxonomy_id,
                                                        'CODING', coord_version, seq_version,
                                                        genomerelease_id, start, stop,
                                                        coding_file_header, codingSeq)

    ## update proteinsequenceannotation table
    update_proteinsequenceannotation(nex_session, dbentity_id, taxonomy_id,
                                     contig_id, seq_version, genomerelease_id,
                                     file_header, proteinSeq)

    # update 1KB seq
    file_header = file_header0 + str(oneKBstart) + ".." + str(oneKBstop) + " +/- 1kb [Genome Release 64-5-1]"
    annotation_id_1kb = update_dnasequenceannotation(nex_session, dbentity_id,
                                                     taxonomy_id, '1KB', coord_version, seq_version,
                                                     genomerelease_id, oneKBstart, oneKBstop,
                                                     file_header, oneKBseq)

    ## update dnasubsequence
    cds_start = start
    cds_stop = stop
    relative_start_index = 1
    relative_end_index = cds_stop - cds_start + 1
    if gene_name == '':
        gene_name = systematic_name
    
    file_header = ">" + systematic_name + " " + gene_name + " CDS:" + str(cds_start) + ".." + str(cds_stop)
    display_name = 'CDS'
    update_dnasubsequence(nex_session, dbentity_id, annotation_id,
                          display_name, genomerelease_id, coord_version,
                          seq_version, relative_start_index,
                          relative_end_index, cds_start, cds_stop,
                          file_header, codingSeq)
        

def update_proteinsequenceannotation(nex_session, dbentity_id, taxonomy_id, contig_id, seq_version, genomerelease_id, file_header, seq):

    print ("Update protein:", dbentity_id, taxonomy_id, contig_id, seq_version, genomerelease_id, file_header, seq)
    
    x = nex_session.query(Proteinsequenceannotation).filter_by(dbentity_id=dbentity_id, taxonomy_id=taxonomy_id, contig_id=contig_id).one_or_none()
    if x is None:
        print ("No Proteinsequenceannotation row found for dbentity_id=", dbentity_id, ", taxonomy_id=", taxonomy_id, ", contig_id=", contig_id)
    x.seq_version = seq_version
    x.genomerelease_id = genomerelease_id
    x.file_header = file_header
    x.residues = seq
    nex_session.add(x)


def update_dnasubsequence(nex_session, dbentity_id, annotation_id, display_name, genomerelease_id, coord_version, seq_version, relative_start_index, relative_end_index, contig_start_index, contig_end_index, file_header, seq):

    print ("Update dnasubsequence: ", dbentity_id, annotation_id, display_name, genomerelease_id, coord_version, seq_version, relative_start_index, relative_end_index, contig_start_index, contig_end_index, file_header, seq)

    x = nex_session.query(Dnasubsequence).filter_by(dbentity_id=dbentity_id, annotation_id=annotation_id, display_name=display_name).one_or_none()

    if x is None:
        perint ("No Dnasubsequence row found for dbentity_id=", dbentity_id, " annotation_id=", annotation_id, " display_name=", display_name)
        return

    x.genomerelease_id = genomerelease_id
    x.coord_version = coord_version
    x.seq_version = seq_version
    x.relative_start_index = relative_start_index
    x.relative_end_index = relative_end_index
    x.contig_start_index = contig_start_index
    x.contig_end_index = contig_end_index
    x.file_header = file_header
    x.residues = seq
    nex_session.add(x)
    

def update_dnasequenceannotation(nex_session, dbentity_id, taxonomy_id, dna_type, coord_version, seq_version, genomerelease_id, start, stop, file_header, seq):

    print ("Update dnasequenceannotation: ", dbentity_id, taxonomy_id, dna_type, coord_version, seq_version, genomerelease_id, start, stop, file_header, seq)
    
    x = nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id=taxonomy_id, dbentity_id=dbentity_id, dna_type=dna_type).one_or_none()
    if x is None:
        perint ("No Dnasequenceannotation row found for dbentity_id=", dbentity_id, " for ", dna_type)
        return -1
    x.coord_version = coord_version
    x.seq_version = seq_version
    x.genomerelease_id = genomerelease_id 
    x.start_index = start
    x.end_index = stop
    x.file_header = file_header
    x.residues = seq
    
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)
    
    return x.annotation_id

                
def add_orfs(nex_session, source_id, taxonomy_id, start, stop, systematic_name, gene_name, oneKBstart, oneKBstop, so_id, strand, genomicSeq, codingSeq, proteinSeq, oneKBseq, coord_version, seq_version, genomerelease_id, contig_id, chr):

    print ("Add ORF: ", source_id, taxonomy_id, contig_id, start, stop, systematic_name, gene_name, oneKBstart, oneKBstop, so_id, strand, genomicSeq, codingSeq, proteinSeq, oneKBseq, coord_version, seq_version, genomerelease_id)
    
    ## add ORF into dbentity and locusdbentity
    (dbentity_id, sgdid) = insert_locusdbentity(nex_session, source_id, systematic_name,
                                                gene_name)

    ## add GENOMIC seq into dnasequenceannotation table
    file_header0 = ">" + systematic_name + " " + gene_name + " SGDID:" + sgdid + ", " + "chr" + chr + ":"
    file_header = file_header0 + str(start) + ".." + str(stop) + " [Genome Release 64-5-1]"
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
    file_header = file_header0 + str(oneKBstart) + ".." + str(oneKBstop) + " +/- 1kb [Genome Release 64-5-1]"
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

       
def add_uORFs(nex_session, source_id, taxonomy_id, dbentity_id, sgdid, systematic_name, gene_name, uORF_start, uORF_stop, strand, seq, coord_version, seq_version, genomerelease_id):

    print ("Add uORF: ", source_id, taxonomy_id, dbentity_id, sgdid, uORF_start, uORF_stop, strand, seq, coord_version, seq_version, genomerelease_id)

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
    if strand == '-':
        relative_end_index = stop - uORF_start + 1
        relative_start_index = stop - uORF_stop + 1

    print(f"uORF for {systematic_name}: relative_start_index = {relative_start_index}, relative_end_index = {relative_end_index}")  
        
    if gene_name == '':
        gene_name = systematic_name
    file_header = ">" + systematic_name + " " + gene_name + " uORF:" + str(uORF_start) + ".." + str(uORF_stop)
    display_name = 'uORF'
    so = nex_session.query(So).filter_by(display_name=display_name).one_or_none()
    so_id = so.so_id
    download_filename = systematic_name + "_uORF.fsa"
    print("uORF:", systematic_name, file_header, download_filename)
    insert_dnasubsequence(nex_session, dbentity_id, x.annotation_id,
                          display_name, so_id, genomerelease_id,
                          coord_version, seq_version, relative_start_index,
                          relative_end_index, uORF_start, uORF_stop,
                          file_header, download_filename, seq)

   
        
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
    

def extract_seqs(nex_session, chr, strand, start, stop):

    contig = nex_session.query(Contig).filter_by(format_name='Chromosome_'+chr).one_or_none()

    chrSeq = contig.residues
    contig_id = contig.contig_id

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
