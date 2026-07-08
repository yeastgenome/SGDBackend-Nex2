from sqlalchemy import or_
from datetime import datetime
from src.models import Locusdbentity, LocusAlias, Contig, Dnasequenceannotation, Taxonomy, \
                       Straindbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

taxid = "TAX:559292"

# ARS, CEN, tRNA, snRNA, snoRNA

inFile = "scripts/loading/alt_sequence_update/data/altRefGenomeUpdate4Shuai040222.tsv"

nameMappingFile = "scripts/loading/alt_sequence_update/data/altRefGenomeUpdate040222_name_mapping.data"

outFile = "scripts/loading/alt_sequence_update/data/altRefGenomeUpdate040222.data"

outFileWithSeq = "scripts/loading/alt_sequence_update/data/altRefGenomeUpdate040222_with_seq.data"

def process_data():
    
    f = open(inFile)
    fw = open(nameMappingFile, "w")
    fw2 = open(outFile, "w")
    fw3 = open(outFileWithSeq, "w")

    fw.write("gene_name/feature_name\tfeature_name/alias\tsystematic_name\tdbentity_id\n")
    fw2.write("systematic_name\tdbentity_id\tso_id\tcontig_id\ttaxonomy_id\tstrand\tgenomic_start_index\tgenomic_end_index\tgenomic_file_header\tgenomic_download_filename\toneKB_start\toneKB_end\toneKB_file_header\toneKB_download_filename\n")
    fw3.write("systematic_name\tdbentity_id\tso_id\tcontig_id\ttaxonomy_id\tstrand\tgenomic_start_index\tgenomic_end_index\tgenomic_file_header\tgenomic_download_filename\tgenomic_seq\toneKB_start\toneKB_end\toneKB_file_header\toneKB_download_filename\toneKB_seq\n")

    nex_session = get_session()

    gene_name_to_dbentity_id = {}
    dbentity_id_to_systematic_name = {}
    dbentity_id_to_gene_name = {}
    for x in nex_session.query(Locusdbentity).all():
        gene_name_to_dbentity_id[x.systematic_name] = x.dbentity_id
        if x.gene_name:
            dbentity_id_to_gene_name[x.dbentity_id] = x.gene_name
            gene_name_to_dbentity_id[x.gene_name] = x.dbentity_id
        else:
            dbentity_id_to_gene_name[x.dbentity_id] = x.systematic_name
        dbentity_id_to_systematic_name[x.dbentity_id] = x.systematic_name

    alias_display_name_to_locus_id = dict([(x.display_name, x.locus_id) for x in nex_session.query(LocusAlias).all()])

    ref_taxon = nex_session.query(Taxonomy).filter_by(taxid=taxid).one_or_none()

    ref_taxonomy_id = ref_taxon.taxonomy_id

    dbentity_id_to_so_id = dict([(x.dbentity_id, x.so_id) for x in nex_session.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC', taxonomy_id=ref_taxonomy_id).all()])

    contig_to_id_and_seq = dict([(x.display_name, (x.contig_id, x.residues)) for x in nex_session.query(Contig).all()])

    strain_to_taxonomy_id = {}
    for x in nex_session.query(Straindbentity).all():
        if x.display_name not in strain_to_taxonomy_id:
            strain_to_taxonomy_id[x.display_name.lower()] = x.taxonomy_id
        else:
            print ("duplicate taxonomy_id for ", x.display_name, ": ", x.taxonomy_id, strain_to_taxonomy_id[x.display_name])

    found = {}
    seen = {}
    strain_list = []
    for line in f:
        if "feature_name" in line.lower():
            continue
        pieces = line.strip().split("\t")
        systematic_name = None
        dbentity_id = None
        if pieces[1].startswith('('):
            pieces[1] = pieces[1][1:]
        if pieces[1].endswith(')'):
            pieces[1] = pieces[1][0:-1]

        if pieces[1] in gene_name_to_dbentity_id:
            dbentity_id = gene_name_to_dbentity_id[pieces[1]]
            systematic_name = dbentity_id_to_systematic_name[dbentity_id]
        else:
            dbentity_id = alias_display_name_to_locus_id.get(pieces[1])
            if dbentity_id is None:
                print (pieces[1], "is not in alias table.")
            else:
                systematic_name = dbentity_id_to_systematic_name[dbentity_id]

        so_id = dbentity_id_to_so_id.get(dbentity_id)
        if so_id is None:
            print ("dbentity_id =", dbentity_id, "is not in dnasequenceannotattion table.")

        contig = pieces[2]
        if contig not in contig_to_id_and_seq:
            print (contig, "is not in contig table.")
        (contig_id, contig_seq) = contig_to_id_and_seq.get(contig)
        
        strain = pieces[3]
        if strain.startswith('CEN'):
            strain = 'CEN.PK'
        if strain == '10560-6B':
            strain = 'Sigma1278b'
        if strain not in strain_list:
            strain_list.append(strain)
        taxonomy_id = strain_to_taxonomy_id.get(strain.lower())
        if taxonomy_id is None:
            print (pieces[3], "is not in straindbentity/dbentity table.")

        strand = '+'
        start_index = int(pieces[4])
        end_index = int(pieces[5])
        if start_index > end_index:
            strand = '-'
            (start_index, end_index) = (end_index, start_index)
            
        (genomic_seq, genomic_start, genomic_end) = _get_sequence_from_contig(contig_seq, start_index, end_index, strand)
        (oneKB_seq, oneKB_start, oneKB_end) = _get_sequence_from_contig(contig_seq, start_index - 1000, end_index + 1000, strand)

        file_header = ">" + systematic_name + " " + dbentity_id_to_gene_name[dbentity_id] + " " + strain + " " + contig + ":"
        genomic_file_header = file_header + str(start_index) + ".." + str(end_index)
        oneKB_file_header = file_header + str(oneKB_start) + ".." + str(oneKB_end) + " +/- 1kb"
        genomic_download_filename = systematic_name + "_" + strain + "_genomic.fsa"
        oneKB_download_filename = systematic_name + "_" + strain + "_1kb.fsa"

        key = (pieces[1], systematic_name, strain, contig)
        if key in seen:
            print ("duplicate rows:", key, seen[key], (start_index, end_index))
            continue
        seen[key] = (start_index, end_index)
        
        if systematic_name not in found:
            fw.write(pieces[0] + "\t" + pieces[1] + "\t" + systematic_name + "\t" + str(dbentity_id) + "\n")
            found[systematic_name] = 1
            
        fw2.write(systematic_name + "\t" + str(dbentity_id) + "\t" + str(so_id) + "\t" + str(contig_id) + "\t" + str(taxonomy_id)  + "\t" + strand + "\t" + str(start_index) + "\t" + str(end_index) + "\t" + genomic_file_header + "\t" + genomic_download_filename + "\t" + str(oneKB_start) + "\t" + str(oneKB_end) + "\t" + oneKB_file_header + "\t" + oneKB_download_filename + "\n")

        fw3.write(systematic_name + "\t" + str(dbentity_id) + "\t" + str(so_id) + "\t" + str(contig_id) + "\t" + str(taxonomy_id)  + "\t" + strand + "\t" + str(start_index) + "\t" + str(end_index) + "\t" + genomic_file_header + "\t" + genomic_download_filename + "\t" + genomic_seq + "\t" + str(oneKB_start) + "\t" + str(oneKB_end) + "\t" + oneKB_file_header + "\t" + oneKB_download_filename + "\t" + oneKB_seq + "\n")

    f.close()
    fw.close()
    fw2.close()
    fw3.close()

    print (', '.join(strain_list))
    

def _get_sequence_from_contig(contig_seq, start, end, strand):

    if start < 1:
        start = 1
    if end > len(contig_seq):
        end = len(contig_seq)
           
    seq = contig_seq[start-1:end]
    if strand == '-':
        seq = _reverse_complement(seq)

    return (seq, start, end)

def _reverse_complement(seq):

    complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
    bases = list(seq)
    bases = reversed([complement.get(base,base) for base in bases])
    bases = ''.join(bases)
    return bases

if __name__ == "__main__":

    process_data()
