import sys
import os
from src.models import Locusdbentity, Dnasequenceannotation, Dnasubsequence, Proteinsequenceannotation, \
                       Contig, LocusAlias, Source, Taxonomy, So
from scripts.loading.database_session import get_session
from scripts.loading.util import get_strain_taxid_mapping
                             
__author__ = 'sweng66'

log_file = "scripts/loading/NISS/logs/load_niss.log"
genomic_file = "scripts/loading/NISS/data/NISSpilotSet102119_genomic.fsa"
coding_file = "scripts/loading/NISS/data/NISSpilotSet102119_coding.fsa"
kb_file = "scripts/loading/NISS/data/NISSpilotSet102119_1KB.fsa"
protein_file = "scripts/loading/NISS/data/NISSpilotSet102119_protein.fsa"
cds_file = "scripts/loading/NISS/data/NISSpilotSet102119_cds.fsa"
gene_file = "scripts/loading/NISS/data/niss_genes.txt"

CREATED_BY = os.environ['DEFAULT_USER']

def load_data():

    nex_session = get_session()

    taxid_to_taxonomy_id = dict([(x.taxid, x.taxonomy_id) for x in nex_session.query(Taxonomy).all()]) 
    sgd = nex_session.query(Source).filter_by(display_name='SGD').one_or_none() 
    genBank = nex_session.query(Source).filter_by(display_name='GenBank/EMBL/DDBJ').one_or_none()
    uniprot = nex_session.query(Source).filter_by(display_name='UniProtKB').one_or_none()

    so_to_so_id = dict([(x.display_name, x.so_id) for x in nex_session.query(So).all()])
    name_to_locus_id = dict([(x.systematic_name, x.dbentity_id) for x in nex_session.query(Locusdbentity).all()])

    source_id = sgd.source_id
    genBank_src_id = genBank.source_id
    uniprot_src_id = uniprot.source_id

    strain_taxid_mapping = get_strain_taxid_mapping()

    fw = open(log_file, "w")

    for seq_file in [genomic_file, coding_file, kb_file]:

        f = open(seq_file)

        defline = ""
        seq = ""
        dna_type = None
        if 'coding' in seq_file:
            dna_type = 'CODING'
        elif 'genomic' in seq_file:
            dna_type = 'GENOMIC'
        else:
            dna_type = '1KB'

        for line in f:
            line = line.strip()
            if line.startswith('>'):
                if seq and defline:
                    insert_dnasequenceannotation(nex_session, fw, source_id, dna_type, defline, seq,
                                                 so_to_so_id, taxid_to_taxonomy_id, 
                                                 name_to_locus_id, strain_taxid_mapping)
                defline = line
                seq = ""
            else:                           
                seq = seq + line

        insert_dnasequenceannotation(nex_session, fw, source_id, dna_type, defline, seq,
                                     so_to_so_id, taxid_to_taxonomy_id, 
                                     name_to_locus_id, strain_taxid_mapping)
        f.close()
    
    ## protein sequences

    f = open(protein_file)

    defline = ""
    seq = ""
    for line in f:
        line = line.strip()
        if line.startswith('>'):
            if seq and defline:
                insert_proteinsequenceannotation(nex_session, fw, source_id, defline, seq,
                                                 taxid_to_taxonomy_id, name_to_locus_id, 
                                                 strain_taxid_mapping)
            defline = line
            seq = ""
        else:
            seq = seq + line

    insert_proteinsequenceannotation(nex_session, fw, source_id, defline, seq,
                                     taxid_to_taxonomy_id, name_to_locus_id, 
                                     strain_taxid_mapping)
    f.close()

    ## cds sequences
                                                                                                    
    f = open(cds_file)

    defline = ""
    seq = ""
    for line in f:
        line = line.strip()
        if line.startswith('>'):
            if seq and defline:
                insert_dnasubsequence(nex_session, fw, source_id, defline, seq,
                                      taxid_to_taxonomy_id, name_to_locus_id,
                                      strain_taxid_mapping, so_to_so_id)

            defline = line
            seq = ""
        else:
            seq = seq + line

    insert_dnasubsequence(nex_session, fw, source_id, defline, seq,
                          taxid_to_taxonomy_id, name_to_locus_id,
                          strain_taxid_mapping, so_to_so_id)

    f.close()

    ## locus_alias + locusdbentity
    f = open(gene_file)
    for line in f:
        if line.startswith('systematic_name'):
            continue
        [name, genBankID, uniprotID] = line.strip().split("\t")
        locus_id = name_to_locus_id.get(name)
        if locus_id is None:
            print (name + " is not in the database.")
            continue
        nex_session.query(Locusdbentity).filter_by(dbentity_id=locus_id).update({'has_sequence': '1', 'has_protein': '1', 'has_sequence_section': '1'})
        insert_locus_alias(nex_session, fw, locus_id, genBankID, genBank_src_id, 
                           'DNA accession ID', 'https://www.ncbi.nlm.nih.gov/nuccore/'+genBankID)
        insert_locus_alias(nex_session, fw, locus_id, uniprotID, uniprot_src_id, 
                           'UniProtKB ID', 'http://www.uniprot.org/uniprot/'+uniprotID)

    f.close()
    fw.close()

    # nex_session.rollback()
    nex_session.commit()


def get_contig_id(nex_session, contig):

    x = nex_session.query(Contig).filter_by(format_name=contig).one_or_none()

    return x.contig_id

def get_annotation_id(nex_session, locus_id, taxonomy_id):
    
    x = nex_session.query(Dnasequenceannotation).filter_by(dbentity_id=locus_id, taxonomy_id=taxonomy_id, dna_type='GENOMIC').one_or_none()

    return x.annotation_id

def parse_defline(nex_session, defline, taxid_to_taxonomy_id, name_to_locus_id, strain_taxid_mapping):
    
    pieces = defline.replace(">", "").split(" ")
    name = pieces[0]
    gene = pieces[1]
    locus_id = name_to_locus_id.get(name)
    if locus_id is None:
        print (name + " is not in the database.")
        return []

    strain = pieces[2]
    taxid = strain_taxid_mapping.get(strain)
    if taxid is None:
        print (strain + " is not in the mapping.")
        return []

    taxonomy_id = taxid_to_taxonomy_id.get(taxid)
    if taxonomy_id is None:
        print (taxid + " is not in the database.")
        return []

    contig = pieces[3]
    contig_id = get_contig_id(nex_session, contig)
    if contig_id is None:
        print (contig + " is not in the Contig table.")
        return []

    start = int(pieces[4])
    end = int(pieces[5])
    strand = pieces[6]
    
    return [name, gene, strain, contig, locus_id, taxonomy_id, contig_id, start, end, strand]


def insert_locus_alias(nex_session, fw, locus_id, display_name, source_id, alias_type, obj_url):

    print ("LOCUS_ALIAS: ", locus_id, display_name, source_id, alias_type, obj_url)

    x = LocusAlias(display_name = display_name,
                   obj_url = obj_url,
                   source_id = source_id,
                   locus_id = locus_id,
                   has_external_id_section = '1',
                   alias_type = alias_type,
                   created_by = CREATED_BY)

    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    fw.write("insert new locus_alias: " + display_name + "\n")

def insert_dnasubsequence(nex_session, fw, source_id, defline, seq, taxid_to_taxonomy_id, name_to_locus_id, strain_taxid_mapping, so_to_so_id):

    data = parse_defline(nex_session, defline, taxid_to_taxonomy_id, name_to_locus_id, strain_taxid_mapping)

    if data is None:
        return
    [name, gene, strain, contig, locus_id, taxonomy_id, contig_id, start, end, strand] = data
                          
    annotation_id = get_annotation_id(nex_session, locus_id, taxonomy_id)

    if annotation_id is None:
        print ("dbentity_id=" + str(locus_id) + " is not in the dnasequenceannotation table.")
        return

    so_id = so_to_so_id['CDS']

    file_header = name + "_" + strain + "_CDS.fsa"
    download_filename = ">" + name + " " + gene + " CDS:" + str(start) + ".." + str(end)

    relative_start = 1
    relative_end = end-start+1


    
    print ("DNASUBSEQUENCE: ", name, gene, strain, contig, locus_id, taxonomy_id, contig_id, start, end, strand, file_header, download_filename, relative_start, relative_end, seq)



    x = Dnasubsequence(annotation_id = annotation_id,
                       dbentity_id = locus_id,
                       display_name = 'CDS',
                       so_id = so_id,
                       relative_start_index = relative_start,
                       relative_end_index = relative_end,
                       contig_start_index = start,
                       contig_end_index = end,
                       file_header = file_header,
                       download_filename = download_filename,
                       residues = seq,
                       created_by = CREATED_BY)

    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    fw.write("insert new dnasebsequence: name=" + name + "\n")

def insert_dnasequenceannotation(nex_session, fw, source_id, dna_type, defline, seq, so_to_so_id, taxid_to_taxonomy_id, name_to_locus_id, strain_taxid_mapping):

    data = parse_defline(nex_session, defline, taxid_to_taxonomy_id, name_to_locus_id, strain_taxid_mapping)

    if data is None:
        return
    [name, gene, strain, contig, locus_id, taxonomy_id, contig_id, start, end, strand] = data

    file_header = ">" + name + " " + gene + " " + strain + " " + contig + ":" + str(start) + ".." + str(end)
    if dna_type == '1KB':
        file_header = file_header + " +/- 1kb"

    download_filename = name + "_" + strain + "_"
    if dna_type == 'CODING':
        download_filename = download_filename + 'coding.fsa'
    elif dna_type == 'GENOMIC':
        download_filename = download_filename +'genomic.fsa'
    else:
        download_filename = download_filename +'1kb.fsa'

    so_id = so_to_so_id['ORF']


    print ("DNASEQUENCEANNOTATION: ", name, gene, strain, contig, locus_id, taxonomy_id, contig_id, start, end, strand, file_header, download_filename, so_id, seq)


    x = Dnasequenceannotation(dbentity_id = locus_id,
                              source_id = source_id,
                              taxonomy_id = taxonomy_id,
                              so_id = so_id,
                              dna_type = dna_type,
                              contig_id = contig_id,
                              start_index = start,
                              end_index = end,
                              strand = strand,
                              file_header = file_header,
                              download_filename = download_filename,
                              residues = seq,
                              created_by = CREATED_BY)

    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    fw.write("insert new dnasequenceannotation: dna_type=" + dna_type + ", name=" + name + "\n")

def insert_proteinsequenceannotation(nex_session, fw, source_id, defline, seq, taxid_to_taxonomy_id, name_to_locus_id, strain_taxid_mapping):

    data = parse_defline(nex_session, defline, taxid_to_taxonomy_id, name_to_locus_id, strain_taxid_mapping)

    if data is None:
        return 
    [name, gene, strain, contig, locus_id, taxonomy_id, contig_id, start, end, strand] = data

    file_header = ">" + name + " " + gene + " " + contig + ":" + str(start) + ".." + str(end)

    download_filename = name + "-protein.fsa"



    print ("PROTEINSEQUENCEANNOTATION: ", name, gene, strain, contig, locus_id, taxonomy_id, contig_id, start, end, strand, file_header, download_filename, seq)



    x = Proteinsequenceannotation(dbentity_id = locus_id,
                                  source_id = source_id,
                                  taxonomy_id = taxonomy_id,
                                  contig_id = contig_id,
                                  file_header = file_header,
                                  download_filename = download_filename,
                                  residues = seq,
                                  created_by = CREATED_BY)
                              
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    fw.write("insert new proteinsequenceannotation: " + name + "\n")

if __name__ == "__main__":
        
    load_data()
    
