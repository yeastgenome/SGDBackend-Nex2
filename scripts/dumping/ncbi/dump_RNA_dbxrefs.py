from datetime import datetime
import logging
from src.models import Taxonomy, Dnasequenceannotation, Locusdbentity, LocusAlias, \
     Contig, So
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

datafile = "scripts/dumping/ncbi/data/SGD_ncRNA_xref.txt"

# s3_archive_dir = "curation/chromosomal_feature/"

TAXON = "TAX:559292"
mito_accession = 'KP263414.1'


def dump_data(rna_file):

    nex_session = get_session()

    datestamp = str(datetime.now()).split(" ")[0]

    log.info(str(datetime.now()))
    log.info("Getting basic data from the database...")

    taxon = nex_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxon.taxonomy_id
    so_id_to_so = dict([(x.so_id, (x.soid, x.display_name))
                        for x in nex_session.query(So).all()])
    dbentity_id_to_locus = dict([(x.dbentity_id, x)
                                 for x in nex_session.query(Locusdbentity).all()])

    contig_id_to_name = dict([(x.contig_id, x.display_name) for x in nex_session.query(
        Contig).filter_by(taxonomy_id=taxonomy_id).all()])

    num2rom = number2roman()
    chr2accession = {}
    for x in nex_session.query(LocusAlias).filter_by(alias_type = 'TPA accession ID').all():
        locus = dbentity_id_to_locus.get(x.locus_id)
        if locus and locus.systematic_name.isdigit():
            chr = num2rom[locus.systematic_name]
            chr2accession[chr] = x.display_name
    chr2accession['Mito'] = mito_accession

    sgdid2accession = {}
    
    f =	open(rna_file)
    for line in f:
        pieces = line.split("\t")
        sgdid2accession[pieces[2]] = pieces[0]
    f.close()

    log.info("Getting all features from the database...")

    fw = open(datafile, "w")
    
    data = []
    for x in nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id=taxonomy_id, dna_type='GENOMIC').order_by(Dnasequenceannotation.contig_id, Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all():
        locus = dbentity_id_to_locus.get(x.dbentity_id)
        if locus is None:
            continue

        (soid, soTerm) = so_id_to_so[x.so_id]
        if 'RNA' not in soTerm:
            continue
        if locus.dbentity_status != 'Active':
            continue
        if locus.qualifier == 'Dubious':
            continue

        name = None
        if locus.gene_name and locus.gene_name != locus.systematic_name:
            name = locus.gene_name
        else:
            name = locus.systematic_name

        chromosome = contig_id_to_name.get(x.contig_id)
        chr = None
        if chromosome:
            chr = chromosome.split(' ')[1]
        accession4chr = chr2accession[chr]
        
        sgdid = locus.sgdid
        accession = sgdid2accession.get(sgdid)
        if accession is None:
            continue
        fw.write(accession4chr + "\t" + sgdid + "\t" + name + "\t" + soTerm + "\t" + accession + "\n")
    
    fw.close()

    log.info(str(datetime.now()))
    log.info("Done!")
    
def number2roman():

    num2rom = {}
    i = 0
    for roman in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI',
                  'XII', 'XIII', 'XIV', 'XV', 'XVI', 'Mito']:
        i = i + 1
        num2rom[str(i)] = roman
    return num2rom

if __name__ == '__main__':

    # http://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/id_mapping/database_mappings/sgd.tsv
    url_path = 'http://ftp.ebi.ac.uk/pub/databases/RNAcentral/current_release/id_mapping/database_mappings/'
    rna_file = 'sgd.tsv'
    
    import urllib.request

    urllib.request.urlretrieve(url_path + rna_file, rna_file)

    dump_data(rna_file)
