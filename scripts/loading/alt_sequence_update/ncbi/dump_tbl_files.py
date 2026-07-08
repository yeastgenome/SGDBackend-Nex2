from datetime import datetime
import logging
import tarfile
import os
import sys
from src.models import Taxonomy, Source, Contig, Edam, Path, Filedbentity, FilePath, So, \
                       Dnasequenceannotation, Dnasubsequence, Locusdbentity, \
                       Dbentity, Go, EcoAlias, Goannotation, Gosupportingevidence, \
                       LocusAlias, Referencedbentity, Ec
from scripts.loading.database_session import get_session
from src.helpers import check_for_non_ascii_characters

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

data_dir = "scripts/loading/alt_sequence_update/ncbi/"

TABS = "\t\t\t"

namespace_mapping = { 'biological process' : 'go_process',
                      'cellular component' : 'go_component',
                      'molecular function' : 'go_function' }

orf_to_tpa_acc = { "YEL066W": "DAA07588.2",   "YJR012C": "DAA08804.2",   "YMR147W": "DAA10043.2",
                   "YNL260C": "DAA10299.2",   "YHR052C-B": "DAD54801.1", "YHR054C-B": "DAD54802.1",
                   "YBR266C": "DAD54803.1",   "YEL059W": "DAD54804.1",   "YJL142C": "DAD54805.1",
                   "YJL075C": "DAD54806.1",   "YJR107C-A": "DAD54807.1", "YKL104W-A": "DAD54808.1",
                   "YLR379W-A": "DAD54809.1", "YMR008C-A": "DAD54810.1", "YMR075C-A": "DAD54811.1",
                   "YPR038W": "DAD54812.1",   "YGR227C-A": "DAF84567.1" } 

MITO_ID = "KP263414.1"

def dump_data():
 
    nex_session = get_session()

    datestamp = str(datetime.now()).split(" ")[0].replace("-", "")

    log.info(str(datetime.now()))
    log.info("Getting basic data from the database...")
    
    source_to_id = dict([(x.display_name, x.source_id) for x in nex_session.query(Source).all()]) 
    so_id_to_display_name = dict([(x.so_id, x.display_name) for x in nex_session.query(So).all()])
    dbentity_id_to_locus = dict([(x.dbentity_id, x) for x in nex_session.query(Locusdbentity).all()])
    edam_to_id = dict([(x.format_name, x.edam_id) for x in nex_session.query(Edam).all()])
    reference_id_to_pmid = dict([(x.dbentity_id, x.pmid) for x in nex_session.query(Referencedbentity).all()])
    dbentity_id_to_sgdid = dict([(x.dbentity_id, x.sgdid) for x in nex_session.query(Dbentity).filter_by(subclass='LOCUS').all()])
    dbentity_id_to_status = dict([(x.dbentity_id, x.dbentity_status) for x in nex_session.query(Dbentity).filter_by(subclass='LOCUS').all()])
    go_id_to_go = dict([(x.go_id, x) for x in nex_session.query(Go).all()])
    ec_id_to_display_name = dict([(x.ec_id, x.display_name) for x in nex_session.query(Ec).all()])
    contig_id_to_display_name = dict([(x.contig_id, x.display_name) for x in nex_session.query(Contig).all()])
    
    log.info(str(datetime.now()))
    log.info("Getting aliases from the database...")

    locus_id_to_uniform_names = {}
    locus_id_to_ncbi_protein_name = {}
    locus_id_to_protein_id = {}
    locus_id_to_ecnumbers = {}
    
    for x in  nex_session.query(LocusAlias).filter(LocusAlias.alias_type.in_(['Uniform', 'TPA protein version ID', 'Protein version ID', 'NCBI protein name', 'EC number'])).all():

        if x.alias_type == 'EC number':
            ecnumbers = []
            if x.locus_id in locus_id_to_ecnumbers:
                ecnumbers = locus_id_to_ecnumbers[x.locus_id]
            ecnumbers.append(x.display_name)
            locus_id_to_ecnumbers[x.locus_id] = ecnumbers
            continue

        if x.alias_type == 'Uniform':
            uniform_names = []
            if x.locus_id in locus_id_to_uniform_names:
                uniform_names = locus_id_to_uniform_names[x.locus_id]
            uniform_names.append(TABS + "gene_syn\t" + x.display_name)
            locus_id_to_uniform_names[x.locus_id] = uniform_names
        elif x.alias_type == 'NCBI protein name':
            locus_id_to_ncbi_protein_name[x.locus_id] = TABS + "product\t" + x.display_name.strip().replace('  ', ' ')
        elif x.alias_type == 'TPA protein version ID':
            locus_id_to_protein_id[x.locus_id] = TABS + "protein_id\t" + x.display_name
            
    log.info(str(datetime.now()))
    log.info("Getting GO data from the database...")

    [locus_id_to_go_section, go_to_pmid_list] = get_go_data(nex_session)

    ## get protein IDs for duplicate genes
    duplicate_gene_to_protein_id = get_protein_id_for_duplicate_gene()
    
    log.info(str(datetime.now()))
    log.info("Getting all features from the database...")

    strain_mapping = strain_to_taxon_id_filename()
    
    for strain in strain_mapping:

        log.info(str(datetime.now()))
        log.info("generating tbl file for " + strain)
    
        (taxon, filename, mapping_filename) = strain_mapping[strain]
        
        taxonomy = nex_session.query(Taxonomy).filter_by(taxid=taxon).one_or_none()
        taxonomy_id = taxonomy.taxonomy_id

        f = open(data_dir + 'seqID_contig_mapping_files/' + mapping_filename)
        contig_to_seqID = {}
        for line in f:
            pieces = line.strip().split('\t')
            contig_to_seqID[pieces[1]] = pieces[0]
        f.close()
                 
        fw = open(data_dir + 'data/' + filename, 'w')
        
        ## get all features with 'GENOMIC' sequence in given strain
        main_data = [] 
        annotation_id_to_strand = {}
        found = {}
        for x in nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id = taxonomy_id, dna_type='GENOMIC').order_by(Dnasequenceannotation.contig_id, Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all():

            if x.dbentity_id in found:
                continue
            found[x.dbentity_id] = 1
            
            locus = dbentity_id_to_locus.get(x.dbentity_id)
            if locus is None:
                ## transcript
                continue
            if dbentity_id_to_status[x.dbentity_id] != 'Active':
                continue
            if locus.qualifier == 'Dubious':
                continue

            desc = clean_up_desc(locus.description)
            
            non_ascii_characters = check_for_non_ascii_characters(desc)
            if len(non_ascii_characters) > 0:
                print ("non-ascii character(s) " + ', '.join(non_ascii_characters) + " in " + locus.systematic_name + "'s description: \n" + desc)
                break

            main_data.append((x.annotation_id, x.contig_id, x.dbentity_id, locus.systematic_name, locus.gene_name, so_id_to_display_name[x.so_id], x.start_index, x.end_index, x.strand, desc))
            annotation_id_to_strand[x.annotation_id] = x.strand    
    
        type_mapping = type_to_show()
        ncRNA_class_mapping = ncRNA_class()
    
        [annotation_id_to_cds_data, annotation_id_to_frameshift, annotation_id_to_cde_data, annotation_id_to_uorf_data] = get_cds_data(nex_session, annotation_id_to_strand, type_mapping)

        prev_contig_id = 0
        for row in main_data:

            (annotation_id, contig_id, locus_id, systematic_name, gene_name, feature_type, start, stop, strand, desc) = row

            if contig_id != prev_contig_id:
                 accession = contig_id_to_display_name[contig_id]
                 wgs = accession[0:6]
                 seqID = contig_to_seqID[accession.replace('.1', '')]
                 fw.write(">Feature gnl|WGS:" + wgs + "|" + seqID + "|gb|" + accession + "|\n")

            prev_contig_id = contig_id

            if strand == '-':
                (start, stop) = (stop, start)

            sgdid = dbentity_id_to_sgdid[locus_id]

            type = feature_type
            if type in type_mapping:
                type = type_mapping[type]
            if gene_name and "RDN37-" in gene_name:
                type = "misc_RNA"
        
            go_section = locus_id_to_go_section.get(locus_id, [])
            go_session = go_section.sort()

            if feature_type in ['ORF', 'transposable element gene']:

                locus_id_to_protein_id = locus_id_to_protein_id

                add_ORF_features(fw, annotation_id, locus_id, sgdid, systematic_name, 
                                 gene_name, start, stop, desc, annotation_id_to_cds_data,
                                 annotation_id_to_frameshift, locus_id_to_uniform_names, 
                                 locus_id_to_ncbi_protein_name, duplicate_gene_to_protein_id, 
                                 locus_id_to_protein_id, go_section, go_to_pmid_list, 
                                 locus_id_to_ecnumbers, type, annotation_id_to_uorf_data)
                continue

            if feature_type in ['pseudogene', 'blocked reading frame']:

                add_pseudogenes(fw, annotation_id, locus_id, sgdid,  
                                systematic_name, gene_name, start, stop, desc, 
                                annotation_id_to_cds_data, locus_id_to_uniform_names, 
                                type, feature_type, go_section, go_to_pmid_list)
                continue

            if systematic_name.startswith('NTS'):

                ## only four of them: NTS1-2, NTS2-1, NTS2-2, NTS1-1
                add_NTS_features(fw, systematic_name, sgdid, start, stop, desc)
                continue

            if feature_type.endswith('RNA gene'):
                
                add_RNA_genes(fw, annotation_id, locus_id, sgdid, systematic_name, 
                              gene_name, start, stop, desc, annotation_id_to_cds_data, 
                              go_section, go_to_pmid_list, type, feature_type, 
                              locus_id_to_ncbi_protein_name, ncRNA_class_mapping)
                continue

            if feature_type == 'centromere':
            
                add_centromeres(fw, locus_id, sgdid, systematic_name,
                                gene_name, start, stop, desc, type,
                                annotation_id_to_cde_data.get(annotation_id))
                continue

            if feature_type == 'LTR retrotransposon':

                add_retrotransposons(fw, sgdid, systematic_name, start, stop, desc, type)
                continue

            if feature_type == 'telomere':

                add_telomeres(fw, sgdid, systematic_name, start, stop, desc, type)
                continue

            if feature_type == 'long terminal repeat':

                add_LTR(fw, sgdid, start, stop, desc, type)
                continue

            if feature_type in ['ARS', 'origin of replication', 'silent mating type cassette array', 'mating type region', 'matrix attachment site']:
            
                add_ARS_etc(fw, sgdid, systematic_name, gene_name, start, stop, desc, type)
                continue
        
            if feature_type == 'recombination enhancer':

                desc = "RE (recombination enhancer); " + desc
            
                add_regulatory_features(fw, sgdid, start, stop, desc)

        fw.close()
        
    nex_session.close()

    log.info(str(datetime.now()))
    log.info("Done!")

def strain_to_taxon_id_filename():

    return { 'CEN.PK':     ('NTR:115', 'CEN.PK2-1Ca.tbl', 'JRIV01_accs'),
             'D273-10B':   ('NTR:101', 'D273-10B.tbl', 'JRIY01_accs'),
             'FL100':      ('TAX:947036', 'FL100.tbl', 'JRIT01_accs'),
             'JK9-3d':     ('NTR:104', 'JK9-3d.tbl', 'JRIZ01_accs'),
             'RM11-1a':    ('TAX:285006', 'RM11-1a.tbl', 'JRIP01_accs'),
             'SEY6210':    ('NTR:107', 'SEY6210.tbl', 'JRIW01_accs'),
             'Sigma1278b': ('TAX:658763', 'Sigma1278b-10560-6B.tbl', 'JRIQ01_accs'),
             'SK1':        ('TAX:580239', 'SK1.tbl', 'NCSL01_accs'),
             'W303':       ('TAX:580240', 'W303.tbl', 'JRIU01_accs'),
             'X2180-1A':   ('NTR:108', 'X2180-1A.tbl', 'JRIX01_accs'),
             'Y55':        ('NTR:112', 'Y55.tbl', 'JRIF01_accs')
    }

def add_regulatory_features(fw, sgdid, start, stop, desc):

    desc = desc.replace("RE;", "RE (recombination enhancer);")
    fw.write(str(start)+"\t"+str(stop)+"\tregulatory\n") 
    fw.write(TABS + "regulatory_class\tother\n")
    fw.write(TABS + "note\t" + desc + "\n")
    fw.write(TABS + "db_xref\tSGD:" + sgdid + "\n")

def add_LTR(fw, sgdid, start, stop, desc, type):

    fw.write(str(start)+"\t"+str(stop)+"\t" + type + "\n")
    fw.write(TABS + "note\t" + desc + "\n")
    fw.write(TABS + "db_xref\tSGD:" + sgdid + "\n")


def add_telomeres(fw, sgdid, systematic_name, start, stop, desc, type):
    
    fw.write(str(start)+"\t"+str(stop)+"\t" + type + "\n")
    fw.write(TABS + "note\t" + systematic_name + "; " + desc + "\n")
    fw.write(TABS + "db_xref\tSGD:" + sgdid + "\n")


def add_retrotransposons(fw, sgdid, systematic_name, start, stop, desc, type):

    fw.write(str(start)+"\t"+str(stop)+"\t" + type + "\n")
    fw.write(TABS + "mobile_element_type\tretrotransposon:" + systematic_name + "\n")
    fw.write(TABS + "note\t" + systematic_name + "; " + desc + "\n")
    fw.write(TABS + "db_xref\tSGD:" + sgdid + "\n")


def add_ARS_etc(fw, sgdid, systematic_name, gene_name, start, stop, desc, type):

    fw.write(str(start)+"\t"+str(stop)+"\t" + type + "\n")
    name = systematic_name
    if gene_name and gene_name != systematic_name:
        name = gene_name
    fw.write(TABS + "note\t" + name + "; " + desc + "\n")
    fw.write(TABS + "db_xref\tSGD:" + sgdid + "\n")


def add_centromeres(fw, locus_id, sgdid, systematic_name, gene_name, start, stop, desc, type, cde_data):

    fw.write(str(start)+"\t"+str(stop)+"\t" + type + "\n")
    fw.write(TABS + "note\t" + systematic_name + "; " + desc + "\n")
    fw.write(TABS + "db_xref\tSGD:" + sgdid + "\n")
    
    if cde_data is None:
        return

    for cde in cde_data:
        cde = cde.replace("REPLACE_THIS", systematic_name)
        fw.write(cde+"\n")


def add_pseudogenes(fw, annotation_id, locus_id, sgdid, systematic_name, gene_name, start, stop, desc, annotation_id_to_cds_data, locus_id_to_uniform_names, type, feature_type, go_section, go_to_pmid_list):

    fw.write(str(start)+"\t"+str(stop)+"\t" + type + "\n")

    mRNA_lines = ""

    if feature_type == 'pseudogene':
        mRNA_lines = str(start)+"\t"+str(stop)+"\tmRNA\n"

    if gene_name:
        fw.write(TABS + type + "\t" + gene_name + "\n")
        mRNA_lines += TABS + type + "\t"+ gene_name + "\n"

    if locus_id in locus_id_to_uniform_names:
        for uniform_name in locus_id_to_uniform_names[locus_id]:
            fw.write(uniform_name+"\n")
            mRNA_lines += uniform_name+"\n"
    fw.write(TABS + "locus_tag\t" + systematic_name + "\n")
    mRNA_lines += TABS + "locus_tag\t" + systematic_name + "\n"

    fw.write(TABS + "pseudo\n")

    if feature_type != 'pseudogene':
        for cds in  annotation_id_to_cds_data[annotation_id]:
            fw.write(cds + "\n")
        fw.write(TABS + "pseudo\n")
        
    if desc:
        fw.write(TABS + "note\t" + desc + "\n")

    for goline in go_section:
        pmid_list = format_pmid_list(go_to_pmid_list.get((locus_id, goline)))
        fw.write(goline + pmid_list + "\n")

    fw.write(TABS + "db_xref\tSGD:" + sgdid + "\n")

    if feature_type == 'pseudogene':
        fw.write(mRNA_lines)

def add_NTS_features(fw, systematic_name, sgdid, start, stop, desc):
    
    fw.write(str(start)+"\t"+str(stop)+"\tmisc_feature\n")
    if desc:
        fw.write(TABS + "note\t" + systematic_name + "; " + desc + "\n")
    else:
        fw.write(TABS + "note\t" + systematic_name + "\n") 
    fw.write(TABS + "db_xref\tSGD:" + sgdid + "\n")

def add_RNA_genes(fw, annotation_id, locus_id, sgdid, systematic_name, gene_name, start, stop, desc, annotation_id_to_cds_data, go_section, go_to_pmid_list, type, feature_type, locus_id_to_ncbi_protein_name, ncRNA_class_mapping):
    
    fw.write(str(start)+"\t"+str(stop)+"\tgene\n")

    if gene_name and gene_name.upper() != systematic_name.upper():
        fw.write(TABS + "gene\t" + gene_name + "\n")
        
    fw.write(TABS + "locus_tag\t" + systematic_name + "\n")

    product = systematic_name

    if feature_type != 'tRNA gene':
        if gene_name and (gene_name.startswith('ETS') or gene_name.startswith('ITS')):
            type = 'misc_RNA'
        fw.write(str(start)+"\t"+str(stop)+"\t" + type + "\n")
    else:
        if annotation_id not in annotation_id_to_cds_data:
            fw.write(str(start)+"\t"+str(stop)+"\ttRNA\n")
        else:
            for row in annotation_id_to_cds_data[annotation_id]:
                row = row.replace("noncoding_exon", "tRNA")
                fw.write(row + "\n")

    if type == 'ncRNA':
        type = feature_type.replace("_gene", "").replace(" gene", "")
        rna_class = ncRNA_class_mapping.get(gene_name)
        if rna_class is None:
            rna_class = ncRNA_class_mapping.get(systematic_name)
        if rna_class is None:
            if type == 'ncRNA':
                rna_class = 'other'
            else:
                rna_class = type
        fw.write(TABS + "ncRNA_class\t" + rna_class + "\n")
        product = gene_name if gene_name else systematic_name

    if locus_id in locus_id_to_ncbi_protein_name:
        fw.write(locus_id_to_ncbi_protein_name[locus_id]+"\n")
    elif not product.startswith('YNC'):
        fw.write(TABS + "product\t" + product + "\n")

    if desc:
        fw.write(TABS + "note\t" + desc + "\n")

    for goline in go_section:
        pmid_list = format_pmid_list(go_to_pmid_list.get((locus_id, goline)))
        fw.write(goline + pmid_list + "\n")

    fw.write(TABS + "db_xref\tSGD:" + sgdid + "\n")


def add_ORF_features(fw, annotation_id, locus_id, sgdid, systematic_name, gene_name, start, stop, desc, annotation_id_to_cds_data, annotation_id_to_frameshift, locus_id_to_uniform_names, locus_id_to_ncbi_protein_name, duplicate_gene_to_protein_id, locus_id_to_protein_id, go_section, go_to_pmid_list, locus_id_to_ecnumbers, type, annotation_id_to_uorf_data):

    fw.write(str(start)+"\t"+str(stop)+"\t" + type + "\n")

    mRNA_lines = ""
 
    if annotation_id in annotation_id_to_frameshift:
        mRNA_lines += str(start)+"\t"+str(stop)+"\tmRNA\n"
    else:
        for cds in  annotation_id_to_cds_data[annotation_id]:
            mRNA_lines += cds.replace('CDS', 'mRNA') +"\n"
    
    if gene_name:
        fw.write(TABS + type + "\t" + gene_name + "\n")
        mRNA_lines += TABS + type + "\t"+ gene_name + "\n"

    if locus_id in locus_id_to_uniform_names:
        for uniform_name in locus_id_to_uniform_names[locus_id]:
            fw.write(uniform_name+"\n")
            mRNA_lines += uniform_name+"\n"
    fw.write(TABS + "locus_tag\t" + systematic_name + "\n")
    mRNA_lines += TABS + "locus_tag\t" + systematic_name + "\n"

    for cds in  annotation_id_to_cds_data[annotation_id]:
        fw.write(cds + "\n")

    if annotation_id in annotation_id_to_frameshift:
        fw.write(TABS + "exception\tribosomal slippage\n")

    if locus_id in locus_id_to_ncbi_protein_name:
        fw.write(locus_id_to_ncbi_protein_name[locus_id]+"\n")
        mRNA_lines += locus_id_to_ncbi_protein_name[locus_id]+"\n"
    elif gene_name is None:
        fw.write(TABS + "product\thypothetical protein\n")
        mRNA_lines += TABS + "product\thypothetical protein\n"
    else:
        fw.write(TABS + "product\t" + gene_name.title() + "p\n")
        mRNA_lines += TABS + "product\t" + gene_name.title() + "p\n"

    if locus_id in locus_id_to_ecnumbers:
        for ec in locus_id_to_ecnumbers[locus_id]:
            ec = ec.replace("EC:", "")
            fw.write(TABS + "EC_number\t" + ec + "\n")
            
    protein_id = duplicate_gene_to_protein_id.get(sgdid)
    if protein_id is None:
        protein_id = orf_to_tpa_acc.get(systematic_name)
        if protein_id is None:
            protein_id = locus_id_to_protein_id.get(locus_id)
            if protein_id is None and systematic_name == 'YPR099C':
                protein_id = TABS + "protein_id\tDAC85312.1"
        else:
            protein_id = TABS + "protein_id\t" + protein_id
    else:
        protein_id = TABS + "protein_id\t" + protein_id
    if protein_id:
        fw.write(protein_id+"\n")

    if desc:
        fw.write(TABS + "note\t" + desc + "\n")

    for goline in go_section:
        pmid_list = format_pmid_list(go_to_pmid_list.get((locus_id, goline)))
        fw.write(goline + pmid_list + "\n")

    fw.write(TABS + "db_xref\tSGD:" + sgdid + "\n")

    fw.write(mRNA_lines)

    if annotation_id in annotation_id_to_uorf_data:
        uorfs = annotation_id_to_uorf_data[annotation_id]
        uorf_count = len(uorfs)
        if gene_name is None or gene_name == '':
            gene_name = systematic_name
        num2word = { 2 : 'two', 3 : 'three', 4 : 'four', 5 : 'five', 6: 'six', 7: 'seven' }
        for uorf in uorfs:
            fw.write(uorf + "\tregulatory\n")
            fw.write(TABS + "regulatory_class\tother\n")
            if uorf_count > 1:
                fw.write(TABS + "note\tOne of " + num2word[uorf_count] + " upstream open reading frames (uORFs) in 5' untranslated region of " + gene_name + " gene, regulate translation\n")
            else:
                fw.write(TABS + "note\tUpstream open reading frame (uORF) in 5' untranslated region of " + gene_name + " gene, regulate translation\n")
            
                    
def format_pmid_list(pmids):
    if pmids == "" or pmids is None:
        return ""
    return " [" + "|".join(pmids) + "]"


def type_to_show():

    return { 'ORF'                               : 'gene',
             'ARS'                               : 'rep_origin',
             'origin of replication'             : 'rep_origin',
             'ARS consensus sequence'            : 'rep_origin',
             'CDS'                               : 'CDS',
             'telomeric repeat'                  : 'repeat_region',
             'X element combinatorial repeat'    : 'repeat_region',
             'X element'                         : 'repeat_region',
             'Y prime element'                   : 'repeat_region',
             'telomere'                          : 'telomere',
             'centromere'                        : 'centromere',
             'centromere DNA Element I'          : 'centromere',
             'centromere DNA_Element II'         : 'centromere',
             'centromere DNA_Element III'        : 'centromere',
             'silent mating type cassette array' : 'misc_feature',
             'mating type region'                : 'misc_feature',
             'matrix attachment site'            : 'misc_feature',
             'long terminal repeat'              : 'LTR',
             'LTR retrotransposon'               : 'mobile_element',
             'snoRNA gene'                       : 'ncRNA',
             'snRNA gene'                        : 'ncRNA',
             'ncRNA gene'                        : 'ncRNA',
             'rRNA gene'                         : 'rRNA',
             'telomerase RNA gene'               : 'ncRNA',
             'transposable element gene'         : 'gene',
             'pseudogene'                        : 'gene',
             'blocked reading frame'             : 'gene',
             'tRNA gene'                         : 'tRNA',
             'noncoding exon'                    : 'tRNA' }


def rpt_to_show():
    
    return { 'telomeric repeat'                : 'Telomeric Repeat',
             'X element combinatorial repeat'  : 'X element Combinatorial Repeat',
             'X element'                       : 'X element',
             'Y prime_element'                 : "Y_prime_element",
             'telomere'                        : 'Telomeric Region',
             'LTR retrotransposon'             : 'Transposon' }


def ncRNA_class():

    return { 'TLC1' :     'telomerase_RNA',
             'RPR1' :     'RNase_P_RNA',
             'SCR1' :     'SRP_RNA',
             'RME2' :     'antisense_RNA',
             'RME3' :     'antisense_RNA',
             'YNCH0011W': 'antisense_RNA',
             'YNCM0001W': 'antisense_RNA',
             'YNCP0002W': 'antisense_RNA',
             'YNCB0008W': 'antisense_RNA',
             'YNCB0014W': 'antisense_RNA',
             'NME1' :     'RNase_MRP_RNA' }

def get_cds_data(nex_session, annotation_id_to_strand, type_mapping):
    
    annotation_id_to_cds_data = {}
    annotation_id_to_frameshift = {}
    annotation_id_to_cde_data = {}
    annotation_id_to_uorf_data = {}
    annotation_id_to_display_name = {}

    for x in nex_session.query(Dnasubsequence).all():

        if x.annotation_id not in annotation_id_to_strand:
            continue

        if x.display_name == 'plus_1_translational_frameshift':
            annotation_id_to_frameshift[x.annotation_id] = 1
            continue

        (start, end) = (x.contig_start_index, x.contig_end_index)
        if annotation_id_to_strand[x.annotation_id] == '-':
            (start, end) = (end, start)
            
        if x.display_name == 'uORF':
            uorfs = []
            if x.annotation_id in annotation_id_to_uorf_data:
                uorfs = annotation_id_to_uorf_data[x.annotation_id]
            uorfs.append(str(start)+"\t"+str(end))
            annotation_id_to_uorf_data[x.annotation_id] = uorfs
            continue
        
        if x.display_name in ['intron', 'intein_encoding_region', 'five_prime_UTR_intron', 'telomeric_repeat', 'uORF']:
            continue

        annotation_id_to_display_name[x.annotation_id] = x.display_name

        if x.display_name.startswith('centromere'):
            cde_data = []
            if x.annotation_id in annotation_id_to_cde_data:
                cde_data = annotation_id_to_cde_data[x.annotation_id]
            cde_data.append(str(start)+"\t"+str(end)+"\tcentromere")
            display_name = "REPLACE_THIS_CDE" + x.display_name.replace("centromere_DNA_Element_", "") + " of REPLACE_THIS"
            cde_data.append(TABS + "note\t" + display_name)
            annotation_id_to_cde_data[x.annotation_id] = cde_data

        # if x.display_name not in ['CDS']:
        #    continue

        cds_data = []
        if x.annotation_id in annotation_id_to_cds_data:
            cds_data = annotation_id_to_cds_data[x.annotation_id]
        cds_data.append(str(start)+"\t"+str(end))
        annotation_id_to_cds_data[x.annotation_id] = cds_data

    annotation_id_to_cds_data_sorted = {}
    
    for annotation_id in annotation_id_to_cds_data:
        cds_data = annotation_id_to_cds_data[annotation_id]
        cds_data.sort()
        if annotation_id_to_strand.get(annotation_id) is not None and annotation_id_to_strand.get(annotation_id) == '-':
            cds_data = list(reversed(cds_data))

        new_cds_data = []    
        i = 0
        for row in cds_data:
            if i == 0:
                display_name = annotation_id_to_display_name[annotation_id]
                if display_name in type_mapping:
                    display_name = type_mapping[display_name]
                new_cds_data.append(row + "\t" + display_name)
            else:
                new_cds_data.append(row)
            i = i + 1

        annotation_id_to_cds_data_sorted[annotation_id] = new_cds_data

    return [annotation_id_to_cds_data_sorted, annotation_id_to_frameshift, annotation_id_to_cde_data, annotation_id_to_uorf_data]


def get_go_data(nex_session):

    sgdid_to_locus_id = dict([(x.sgdid, x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='LOCUS').all()])

    locus_id_to_tpa_id = dict([(x.locus_id, x.display_name) for x in nex_session.query(LocusAlias).filter_by(alias_type='TPA protein version ID').all()])

    code_mapping = get_col4_5_for_code()

    reference_id_to_pmid = dict([(x.dbentity_id, x.pmid) for x in nex_session.query(Referencedbentity).all()])
    go_id_to_go = dict([(x.go_id, x) for x in nex_session.query(Go).all()])
    
    eco_id_to_eco = {}
    for x in nex_session.query(EcoAlias).all():
        if len(x.display_name) > 5:
            continue
        eco_id_to_eco[x.eco_id] = x.display_name

    annotation_id_to_panther = {}
    annotation_id_to_supportingevidence = {}

    for x in nex_session.query(Gosupportingevidence).all():
        if x.dbxref_id.startswith("UniProtKB:") or x.dbxref_id.startswith("SGD:") or x.dbxref_id.startswith("protein_id:"):
            if x.dbxref_id.startswith("SGD:"):
                sgdid = x.dbxref_id.replace("SGD:", "")
                locus_id = sgdid_to_locus_id.get(sgdid)
                if locus_id is None:
                    continue
                tpa_id = locus_id_to_tpa_id.get(locus_id)
                if tpa_id is None:
                    continue
                dbxref_id = "INSD:" + tpa_id
            else:
                dbxref_id = x.dbxref_id

            if x.annotation_id in annotation_id_to_supportingevidence:
                annotation_id_to_supportingevidence[x.annotation_id] = annotation_id_to_supportingevidence[x.annotation_id] + "," + dbxref_id
            else:
                annotation_id_to_supportingevidence[x.annotation_id] = dbxref_id
        
    locus_id_to_go_section = {}
    go_to_pmid_list = {}

    for x in nex_session.query(Goannotation).all():

        pmid = reference_id_to_pmid.get(x.reference_id)
        if pmid is None:
            pmid = ''
        else:
            pmid = "PMID:" + str(pmid)

        if x.eco_id not in eco_id_to_eco:
            continue
        
        eco = eco_id_to_eco[x.eco_id]

        if x.go_id not in go_id_to_go:
            continue
        
        go = go_id_to_go[x.go_id]

        if eco == 'ND' or eco not in code_mapping:
            continue

        (col4Text, col5Text) = code_mapping[eco]
        goline = TABS + col4Text + "\t" + col5Text + ":"
        if eco in ['ISS', 'ISM', 'ISA', 'ISO']:
            if x.annotation_id in annotation_id_to_supportingevidence:
                supportingevidence = annotation_id_to_supportingevidence[x.annotation_id]
                if 'protein_id' in supportingevidence:
                    supportingevidence = supportingevidence.replace("protein_id", "INSD")
                    goline = goline.replace(" DNA ", " AA ")
                goline = goline + supportingevidence
            else:
                continue
        else:
            goline = goline + go.goid + " " + go.display_name
            if eco != "IEA":
                pmid_list = []
                if (x.dbentity_id, goline) in go_to_pmid_list:
                    pmid_list = go_to_pmid_list[(x.dbentity_id, goline)]
                if pmid not in pmid_list:
                    pmid_list.append(pmid)
                go_to_pmid_list[(x.dbentity_id, goline)] = pmid_list

        go_section = []
        if x.dbentity_id in locus_id_to_go_section:
            go_section = locus_id_to_go_section[x.dbentity_id]
        if goline not in go_section:
            go_section.append(goline)

        locus_id_to_go_section[x.dbentity_id] = go_section

    return [locus_id_to_go_section, go_to_pmid_list]


def get_protein_id_for_duplicate_gene():

    return { 'S000000214' : 'DAA07131.1', # HHT1                   
             'S000004976' : 'DAA10514.1', # HHT2                   
             'S000000213' : 'DAA07130.1', # HHF1                   
             'S000004975' : 'DAA10515.1', # HHF2                   
             'S000000322' : 'DAA07236.1', # TEF2                   
             'S000006284' : 'DAA11498.1', # TEF1                   
             'S000003674' : 'DAA08662.1', # TIF2                   
             'S000001767' : 'DAA09210.1', # TIF1                   
             'S000002793' : 'DAA12229.1', # EFT2                   
             'S000005659' : 'DAA10907.1' }  # EFT1                   

    
def get_col4_5_for_code():
    
    return { "IDA": ("experiment", "EXISTENCE:direct assay"),
             "IMP": ("experiment", "EXISTENCE:mutant phenotype"),
             "HDA": ("experiment", "EXISTENCE:direct assay"),
             "IGI": ("experiment", "EXISTENCE:genetic interaction"),
             "IPI": ("experiment", "EXISTENCE:physical interaction"),
             "IC":  ("experiment", "EXISTENCE:curator inference"),
             "HMP": ("experiment", "EXISTENCE:mutant phenotype"),
             "IEP": ("experiment", "EXISTENCE:expression pattern"),
             "HGI": ("experiment", "EXISTENCE:genetic interaction") }

def clean_up_desc(desc):

    desc = desc.replace('“', "'").replace('"', "'").replace("’", "'")
    desc = desc.replace('”', "'").replace("<i>", "").replace("</i>", "")
    desc = desc.replace('δ', "delta")

    return desc.replace("Putative protein of unknown function", "hypothetical protein").replace("Protein of unknown function", "hypothetical protein").replace("protein of unknown function", "hypothetical protein").replace("Hypothetical protein", "hypothetical protein")
          
if __name__ == '__main__':
    
    dump_data()

    


