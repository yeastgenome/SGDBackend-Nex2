from scripts.loading.database_session import get_session
from src.models import Dbentity, Locusdbentity, LocusAlias, Dnasequenceannotation, \
                       Dnasubsequence, So, Contig, Go, Goannotation, Taxonomy

from datetime import datetime
import logging
import os
import sys
import re

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

dataDir = "scripts/loading/alt_sequence_update/data/"

def dump_data(strain, taxon, gff_file_name):

    nex_session = get_session()
    
    gff_file = dataDir + gff_file_name
    
    fw = open(gff_file, "w")

    # write_header(fw, strain, contigNum, str(datetime.now())):
    
    log.info(str(datetime.now()))
    log.info("Getting taxonomy, so & sgdid data from the database...")

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid=taxon).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    
    so_id_to_term_name = dict([(x.so_id, x.term_name)
                               for x in nex_session.query(So).all()])
    so = nex_session.query(So).filter_by(display_name='gene').one_or_none()

    gene_soid = so.soid

    locus_id_to_sgdid = dict([(x.dbentity_id, x.sgdid) for x in nex_session.query(
        Dbentity).filter_by(subclass='LOCUS', dbentity_status='Active').all()])

    log.info(str(datetime.now()))
    log.info("Getting alias data from the database...")

    alias_data = nex_session.query(LocusAlias).filter(LocusAlias.alias_type.in_(
        ['Uniform', 'Non-uniform', 'NCBI protein name'])).all()

    locus_id_to_aliases = {}
    for x in alias_data:
        aliases = []
        if x.locus_id in locus_id_to_aliases:
            aliases = locus_id_to_aliases[x.locus_id]
        aliases.append(do_escape(x.display_name))
        locus_id_to_aliases[x.locus_id] = aliases

    log.info(str(datetime.now()))
    log.info("Getting locus data from the database...")

    locus_id_to_info = dict([(x.dbentity_id, (x.systematic_name, x.gene_name, x.qualifier, x.headline, x.description))
                             for x in nex_session.query(Locusdbentity).filter_by(has_summary='1').all()])

    log.info(str(datetime.now()))
    log.info("Getting go annotation data from the database...")

    go_id_to_goid = dict([(x.go_id, x.goid)
                          for x in nex_session.query(Go).all()])

    go_data = nex_session.query(Goannotation).filter(
        Goannotation.annotation_type != 'computational').all()

    locus_id_to_goids = {}
    for x in go_data:
        goid = go_id_to_goid[x.go_id]
        goids = []
        if x.dbentity_id in locus_id_to_goids:
            goids = locus_id_to_goids[x.dbentity_id]
        goids.append(goid)
        locus_id_to_goids[x.dbentity_id] = goids

    log.info(str(datetime.now()))
    log.info("Getting contig data from the database...")

    contig_id_to_contig = dict([(x.contig_id, (x.format_name, x.residues, x.file_header)) for x in nex_session.query(Contig).filter_by(taxonomy_id=taxonomy_id).all()])

    log.info(str(datetime.now()))
    log.info("Getting dnasequenceannotation/dnasubsequence data from the database...")

    subfeature_data = nex_session.query(Dnasubsequence).order_by(
        Dnasubsequence.contig_start_index, Dnasubsequence.contig_end_index).all()

    write_header(fw, strain, len(contig_id_to_contig.keys()), str(datetime.now()))
    
    ## output contigs and their features for the given strain in order
    for contig_id in sorted(contig_id_to_contig):

        ## output contig
                                
        (contig_name, seq, file_header) = contig_id_to_contig[contig_id]
        contig_identifier = file_header[1:].split(' ')[0]
        fw.write(contig_identifier + "\tSGD\tcontig\t1\t" + str(len(seq)) + "\t.\t.\t.\tID=" + contig_identifier + ";dbxref=" + contig_name + ";Name=" + contig_name + "\n")

        ## output features in the given contig in order of coordinates
                    
        gene_data = nex_session.query(Dnasequenceannotation).filter_by(contig_id=contig_id, dna_type='GENOMIC').order_by(
            Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all()

        annotation_id_to_subfeatures = {}
        UTRs = {}
        for x in subfeature_data:
            subfeatures = []
            if x.annotation_id in annotation_id_to_subfeatures:
                subfeatures = annotation_id_to_subfeatures[x.annotation_id]
            subfeatures.append(
                (x.display_name, x.contig_start_index, x.contig_end_index))
            annotation_id_to_subfeatures[x.annotation_id] = subfeatures
            if x.display_name == 'five_prime_UTR_intron':
                UTRs[x.annotation_id] = (
                    x.contig_start_index, x.contig_end_index)

        for x in gene_data:
                                
            if x.dbentity_id not in locus_id_to_sgdid:
                # deleted or merged
                continue

            sgdid = "SGD:" + locus_id_to_sgdid[x.dbentity_id]

            type = so_id_to_term_name[x.so_id]
            if type == 'ORF':
                type = 'gene'
            if type == 'gene_group':
                continue

            strand = x.strand
            if strand == '0':
                strand = '.'
                
            (systematic_name, gene_name, qualifier, headline,
             description) = locus_id_to_info[x.dbentity_id]

            alias_list = None
            if x.dbentity_id in locus_id_to_aliases:
                aliases = sorted(locus_id_to_aliases[x.dbentity_id])
                alias_list = ",".join(aliases)
            if gene_name:
                gene_name = do_escape(gene_name)
                if alias_list:
                    alias_list = gene_name + "," + alias_list
                else:
                    alias_list = gene_name
            systematic_name = do_escape(systematic_name)
            start_index = x.start_index
            end_index = x.end_index
            if x.annotation_id in UTRs:
                (utrStart, utrEnd) = UTRs[x.annotation_id]
                if utrStart < start_index:
                    start_index = utrStart
                else:
                    end_index = utrEnd

            fw.write(contig_identifier + "\tSGD\t" + type + "\t" + str(start_index) + "\t" + str(end_index) +
                     "\t.\t" + strand + "\t.\tID=" + systematic_name + ";Name=" + systematic_name)

            if gene_name:
                fw.write(";gene=" + gene_name)
            if alias_list:
                fw.write(";Alias=" + alias_list)
            if x.dbentity_id in locus_id_to_goids:
                goids = sorted(locus_id_to_goids[x.dbentity_id])
                goid_list = ",".join(goids)
                fw.write(";Ontology_term=" + goid_list + "," + gene_soid)
            if description:
                fw.write(";Note=" + do_escape(description))
            if headline:
                fw.write(";display=" + do_escape(headline))

            fw.write(";dbxref=" + sgdid)

            if qualifier:
                fw.write(";orf_classification=" + qualifier)

            fw.write(";curie=" + sgdid + "\n")

            if x.annotation_id not in annotation_id_to_subfeatures or type in ['pseudogene']:
                continue

            subfeatures = annotation_id_to_subfeatures.get(x.annotation_id)

            start2phase = get_phase(subfeatures, x.strand)

            telomeric_repeat_index = {}

            has_subfeature = 0
            for (display_name, contig_start_index, contig_end_index) in subfeatures:

                if display_name == 'non_transcribed_region':
                    continue

                name = systematic_name + "_" + display_name

                if systematic_name.startswith("TEL") and display_name == 'telomeric_repeat':
                    index = 1
                    if name in telomeric_repeat_index:
                        index = telomeric_repeat_index[name] + 1
                    telomeric_repeat_index[name] = index
                    name = name + "_" + str(index)

                phase = "."
                if display_name == 'CDS':
                    phase = start2phase[contig_start_index]

                parent = systematic_name
                if type.endswith('_gene'):
                    parent = systematic_name + "_" + type.replace("_gene", "")

                has_subfeature = 1

                fw.write(contig_identifier + "\tSGD\t" + display_name + "\t" + str(contig_start_index) + "\t" + str(
                    contig_end_index) + "\t.\t" + strand + "\t" + str(phase) + "\tParent=" + parent + ";Name=" + name)
                if type == 'gene' and qualifier:
                    fw.write(";orf_classification=" + qualifier)
                fw.write("\n")
            
    # output contig sequences at the end

    fw.write("###\n")
    fw.write("##FASTA\n")

    for contig_id in sorted(contig_id_to_contig):
        (contig_name, seq, header) = contig_id_to_contig[contig_id]                        
        fw.write(header + "\n")
        formattedSeq = formated_seq(seq)
        fw.write(formattedSeq + "\n")

    fw.close()

    nex_session.close()

    log.info(str(datetime.now()))
    log.info("Done!")


def strain_to_taxon_id_filename():

    return { 'CEN.PK':     ('NTR:115', 'CEN.PK2-1Ca_JRIV01000000_SGD'),
             'D273-10B':   ('NTR:101', 'D273-10B_JRIY00000000_SGD'),
             'FL100':      ('TAX:947036', 'FL100_JRIT00000000_SGD'),
             'JK9-3d':     ('NTR:104', 'JK9-3d_JRIZ00000000_SGD'),
             'RM11-1a':    ('TAX:285006', 'RM11-1a_JRIP00000000_SGD'),
             'SEY6210':    ('NTR:107', 'SEY6210_JRIW00000000_SGD'),
             'Sigma1278b': ('TAX:658763', 'Sigma1278b-10560-6B_JRIQ00000000_SGD'),
             'SK1':        ('TAX:580239', 'SK1_NCSL00000000_SGD'),
             'W303':       ('TAX:580240', 'W303_JRIU00000000_SGD'),
             'X2180-1A':   ('NTR:108', 'X2180-1A_JRIX00000000_SGD'),
             'Y55':        ('NTR:112', 'Y55_JRIF00000000_SGD')
    }

def write_header(fw, strain, contigNum, datestamp):

    fw.write("##gff-version 3\n")
    fw.write("#!date-produced " + datestamp.split(".")[0] + "\n")
    fw.write("#!data-source SGD\n")
    fw.write("#\n")
    fw.write("# Saccharomyces cerevisiae " + strain + " genome\n")
    fw.write("#\n")
    fw.write("# Features from " + str(contigNum) + " contigs\n")
    fw.write("#\n")
    fw.write("# Created by Saccharomyces Genome Database (http://www.yeastgenome.org/)\n")
    fw.write("#\n")
    fw.write("# Please send comments and suggestions to sgd-helpdesk@lists.stanford.edu\n")
    fw.write("#\n")
    fw.write("# SGD is funded as a National Human Genome Research Institute Biomedical Informatics Resource from\n")
    fw.write("# the U. S. National Institutes of Health to Stanford University.\n")
    fw.write("#\n")
    
def formated_seq(sequence):

    return "\n".join([sequence[i:i+80] for i in range(0, len(sequence), 80)])

def get_phase(subfeatures, strand):

    if strand == '-':
        subfeatures.reverse()

    length = 0
    start2phase = {}
    for (display_name, contig_start_index, contig_end_index) in subfeatures:
        if display_name != 'CDS':
            continue
        phase = length % 3
        if phase != 0:
            phase = 3 - phase
        start2phase[contig_start_index] = phase
        length += contig_end_index - contig_start_index + 1

    return start2phase

def do_escape(text):

    text = text.replace(" ", "%20").replace("(", "%28").replace(")", "%29")
    text = text.replace(",", "%2C")
    text = text.replace(";", "%3B")
    text = text.replace('“', '"').replace('”', '"').replace("’", "'")
    text = text.replace('α', 'alpha').replace('β', 'beta')
    text = text.replace('=', '%3D')
    text = text.rstrip()
    return text

if __name__ == '__main__':

    strain = None
    gff_file_name = None
    if len(sys.argv) >= 3:
        strain = sys.argv[1]
        gff_file_name = sys.argv[2]
    if len(sys.argv) >= 2:
        strain = sys.argv[1]
    else:
        print("Usage:         python scripts/loading/alt_sequence_update/dump_gff_for_nonRef_genome.py strainName gffFileName")
        print("Usage example: python scripts/loading/alt_sequence_update/dump_gff_for_nonRef_genome.py W303 W303_JRIU00000000_SGD.gff")
        print("Usage example: python scripts/loading/alt_sequence_update/dump_gff_for_nonRef_genome.py CEN.PK")
        exit()

    strain_mapping = strain_to_taxon_id_filename()
    if strain not in strain_mapping:
        print ("Strain:", strain, "is not in mapping list")
        exit()
    (taxon, filename) =	strain_mapping[strain]
    if gff_file_name is None:
        gff_file_name = filename + ".gff"

    dump_data(strain, taxon, gff_file_name)
