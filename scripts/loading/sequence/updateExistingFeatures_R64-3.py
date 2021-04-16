import os
from datetime import datetime
import sys
from Bio.Seq import Seq
from src.models import Locusdbentity, Taxonomy, Dnasequenceannotation, \
     Dnasubsequence, Proteinsequenceannotation, Contig, Genomerelease, \
     So
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

TAXON = 'TAX:559292'
genome_release = '64-3-1'
datafile = 'scripts/loading/sequence/data/ExistingFeatures2update-Table1_processed.tsv'

def update_data():

    nex_session = get_session()

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    genomerelease = nex_session.query(Genomerelease).filter_by(format_name=genome_release).one_or_none()
    genomerelease_id = genomerelease.genomerelease_id
    so_to_id = dict([(x.display_name, x.so_id) for x in nex_session.query(So).all()])
    
    f = open(datafile)
    
    for line in f:
        if line.startswith('Chromosome'):
            continue
        line = line.replace('"', '')
        pieces = line.strip().split("\t")
        chr = pieces[0]
        gene_name = pieces[1]
        systematic_name = pieces[2]
        change = pieces[3]
        old_coords = pieces[4]
        new_coords = pieces[5]
        strand = pieces[6]
        genomicSeq4check = pieces[7]
        codingSeq4check = pieces[8]
        proteinSeq4check = pieces[9]

        if 'null' in gene_name:
            gene_name = ''
            
        locus = nex_session.query(Locusdbentity).filter_by(systematic_name=systematic_name).one_or_none()
        dbentity_id = locus.dbentity_id
        sgdid = locus.sgdid
        
        (contig_id, start, stop, oneKBstart, oneKBstop, genomicSeq, codingSeq, oneKBseq, cds_data, intron_data) = extract_seqs(nex_session, chr, strand, new_coords)

        seqObj = Seq(codingSeq)
        proteinSeq = seqObj.translate()
        
        print (systematic_name)
        
        # print (cds_data, intron_data)
        # print (start, stop, oneKBstart, oneKBstop)
        
        if genomicSeq != genomicSeq4check:
            print ("Error: genomic seq is different for ", systematic_name)
        if codingSeq != codingSeq4check:
            print ("Error: coding seq is different for ", systematic_name)
        if proteinSeq != proteinSeq4check:
            print ("Error: protein seq is different for ", systematic_name)

        
        # print ("genomic_seq=", genomicSeq)
        # print ("coding_seq=", codingSeq)
        # print ("oneKBseq=", oneKBseq)
        # print ("proteinSeq=", proteinSeq)
       
        ## update dnasequenceannotation table
        coord_version = str(datetime.now()).split(' ')[0]
        seq_version = coord_version
        file_header0 = ">" + systematic_name + " " + gene_name + " SGDID:" + sgdid + ", " + "chr" + chr + ":"
        
        # update genomic seq
        file_header = file_header0 + str(start) + ".." + str(stop) + " [Genome Release 64-3-1]" 
        annotation_id = update_dnasequenceannotation(nex_session, dbentity_id, taxonomy_id,
                                                 'GENOMIC', coord_version, seq_version,
                                                 genomerelease_id, start, stop,
                                                 file_header, genomicSeq)

        
        # update coding seq
        coding_file_header = file_header 
        if len(cds_data) > 1:
            (cds_start, cds_stop, cds_seq) = cds_data[0]
            (cds_start2, cds_stop2, cds_seq2) = cds_data[1]
            coding_file_header = file_header0 + str(cds_start) + ".." + str(cds_stop) + "," + str(cds_start2) + ".." + str(cds_stop2) + " intron sequence removed [Genome Release 64-3-1]"
        annotation_id_coding = update_dnasequenceannotation(nex_session,
                                                 dbentity_id, taxonomy_id,
                                                 'CODING', coord_version, seq_version,
                                                 genomerelease_id, start, stop,
                                                 coding_file_header, codingSeq)

        ## update proteinsequenceannotation table
        
        update_proteinsequenceannotation(nex_session, dbentity_id, taxonomy_id,
                                         contig_id, seq_version, genomerelease_id,
                                         file_header, proteinSeq4check)
      
        # update 1KB seq
        file_header = file_header0 + str(oneKBstart) + ".." + str(oneKBstop) + " +/- 1kb [Genome Release 64-3-1]"
        annotation_id_1kb = update_dnasequenceannotation(nex_session, dbentity_id,
                                                 taxonomy_id, '1KB', coord_version, seq_version,
                                                 genomerelease_id, oneKBstart, oneKBstop,
                                                 file_header, oneKBseq)
          

        ## update dnasubsequence
        ## update first cds
        (cds_start, cds_stop, cds_seq) = cds_data[0]
        relative_start_index = cds_start - start + 1
        relative_end_index = cds_stop - start + 1
        if gene_name == '':
            gene_name = systematic_name
        file_header = ">" + systematic_name + " " + gene_name + " CDS:" + str(cds_start) + ".." + str(cds_stop)
        display_name = 'CDS'
        update_dnasubsequence(nex_session, dbentity_id, annotation_id,
                              display_name, genomerelease_id, coord_version,
                              seq_version, relative_start_index,
                              relative_end_index, cds_start, cds_stop,
                              file_header, cds_seq)
        
        ## insert the second cds
        if len(cds_data) > 1:
            so_id = so_to_id.get(display_name)
            (cds_start, cds_stop, cds_seq) = cds_data[1]
            relative_start_index = cds_start - start + 1
            relative_end_index = cds_stop - start + 1
            if gene_name == '':
                gene_name = systematic_name
            file_header = ">" + systematic_name + " " + gene_name + " CDS:" + str(cds_start) + ".." + str(cds_stop)
            download_filename = systematic_name + "_CDS.fsa"
            insert_dnasubsequence(nex_session, dbentity_id, annotation_id,
                                  display_name, so_id, genomerelease_id,
                                  coord_version, seq_version, relative_start_index,
                                  relative_end_index, cds_start, cds_stop,
                                  file_header, download_filename, cds_seq)
            
            ## insert intron
            (intron_start, intron_stop, intron_seq) = intron_data
            display_name = 'intron'
            so_id = so_to_id.get(display_name)
            relative_start_index = intron_start - start + 1
            relative_end_index = intron_stop - start + 1
            file_header = ">" + systematic_name + " " + gene_name + " intron:" + str(intron_start) + ".." + str(intron_stop)
            download_filename = systematic_name + "_intron.fsa"
            insert_dnasubsequence(nex_session, dbentity_id, annotation_id,
                                  display_name, so_id, genomerelease_id,
                                  coord_version, seq_version, relative_start_index,
                                  relative_end_index, intron_start, intron_stop,
                                  file_header, download_filename, intron_seq)
                
    nex_session.rollback()
    # nex_session.commit()

    f.close()

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
    
def process_coords(new_coords):
    cds = []
    intron = ''
    new_coords = new_coords.replace(',', '').replace('new ', '')
    if 'intron' in new_coords:
        pieces = new_coords.split('intron at ')
        cds = pieces[0].split(' ')
        intron = pieces[1]     
    else:
        cds = [new_coords]
    return (cds, intron)
    
def extract_seqs(nex_session, chr, strand, new_coords):

    (cds_list, intron) = process_coords(new_coords)
    
    contig = nex_session.query(Contig).filter_by(format_name='Chromosome_'+chr).one_or_none()

    chrSeq = contig.residues
    contig_id = contig.contig_id
                                         
    start = None
    stop = None
    codingSeq = ''
    cds_data = []
    intron_data = ()

    if '..' in intron:
        [beg, end] = intron.split('..')
        beg = int(beg)
        end = int(end)
        intronSeq = chrSeq[beg-1:end]
        if strand == '-':
            intronSeq = reverse_complement(intronSeq)
        intron_data = (beg, end, intronSeq)
        
    for cds in cds_list:
        if '..' not in cds:
            continue
        [beg, end] = cds.split('..')
        beg = int(beg)
        end = int(end)
        cdsSeq = chrSeq[beg-1:end]
        if strand == '-':
            cdsSeq = reverse_complement(cdsSeq)
        cds_data.append((beg, end, cdsSeq))
        codingSeq = codingSeq + cdsSeq
        if start is None or start > beg:
            start = beg
        if stop is None or stop < end:
            stop = end

    genomicSeq = chrSeq[start-1:stop]
    
    oneKBstart = start - 1000
    oneKBstop = stop + 1000
    oneKBseq = chrSeq[oneKBstart-1:oneKBstop]

    if strand == '-':
        genomicSeq = reverse_complement(genomicSeq)
        codingSeq = reverse_complement(codingSeq)
        oneKBseq = reverse_complement(oneKBseq)

    if len(cds_data) == 1:
        codingSeq = genomicSeq
        
    return (contig_id, start, stop, oneKBstart, oneKBstop, genomicSeq, codingSeq, oneKBseq, cds_data, intron_data)

def reverse_complement(seq):

    complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
    bases = list(seq)
    bases = reversed([complement.get(base,base) for base in bases])
    bases = ''.join(bases)
    return bases

if __name__ == '__main__':

    update_data()
