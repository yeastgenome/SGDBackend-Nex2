from datetime import datetime
import logging
import tarfile
import os
import sys
import json
from src.models import Taxonomy, Source, Edam, Path, Filedbentity, FilePath, So, Dbentity,\
                       Dnasequenceannotation, Locusdbentity, LocusAlias, Referencedbentity,\
                       Literatureannotation, Contig                          
from scripts.loading.database_session import get_session
from src.helpers import upload_file

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

data_file = "scripts/dumping/ncbi/data/SGD_RNA.json"

taxonId = "NCBITaxon:559292"
TAXON = "TAX:559292"
assembly = "R64-2-1"

def dump_data():
 
    nex_session = get_session()

    datestamp = str(datetime.now()).split(" ")[0]

    log.info(str(datetime.now()))
    log.info("Getting basic data from the database...")
    
    taxon = nex_session.query(Taxonomy).filter_by(taxid = TAXON).one_or_none()
    taxonomy_id = taxon.taxonomy_id
    so_id_to_so = dict([(x.so_id, (x.soid, x.display_name)) for x in nex_session.query(So).all()])
    dbentity_id_to_locus = dict([(x.dbentity_id, x) for x in nex_session.query(Locusdbentity).all()])
    reference_id_to_pmid = dict([(x.dbentity_id, x.pmid) for x in nex_session.query(Referencedbentity).all()])
    dbentity_id_to_sgdid = dict([(x.dbentity_id, x.sgdid) for x in nex_session.query(Dbentity).filter_by(subclass='LOCUS').all()])
    dbentity_id_to_status = dict([(x.dbentity_id, x.dbentity_status) for x in nex_session.query(Dbentity).filter_by(subclass='LOCUS').all()])
    contig_id_to_name = dict([(x.contig_id, x.display_name) for x in nex_session.query(Contig).filter_by(taxonomy_id=taxonomy_id).all()])

    log.info(str(datetime.now()))
    log.info("Getting aliases from the database...")

    locus_id_to_alias_names = {}
    locus_id_to_ncbi_protein_name = {}
 
    for x in nex_session.query(LocusAlias).filter(LocusAlias.alias_type.in_(['Uniform', 'Non-uniform', 'NCBI protein name'])).all():

        if x.alias_type in ['Uniform', 'Non-uniform']:
            alias_names = []
            if x.locus_id in locus_id_to_alias_names:
                alias_names = locus_id_to_alias_names[x.locus_id]
            alias_names.append(x.display_name)
            locus_id_to_alias_names[x.locus_id] = alias_names
        elif x.alias_type == 'NCBI protein name':
            locus_id_to_ncbi_protein_name[x.locus_id] = x.display_name

    dbentity_id_to_pmid_list = {}
    for x in nex_session.query(Literatureannotation).all():
        pmid_list = []
        if x.dbentity_id in dbentity_id_to_pmid_list:
            pmid_list = dbentity_id_to_pmid_list[x.dbentity_id]
        pmid = reference_id_to_pmid[x.reference_id]
        if pmid:
            pmid_list.append(pmid)
        dbentity_id_to_pmid_list[x.dbentity_id] = pmid_list
             
    log.info("Getting all features from the database...")

    metaData = { "dateProduced": datestamp,
                 "dataProvider": 'SGD',
                 "release": datestamp,
                 "schemaVersion": "0.4.0",
                 "publications": [
                        "PMID:22110037"
                 ] }

    data = []
    ## get all features with 'GENOMIC' sequence in S288C
    for x in nex_session.query(Dnasequenceannotation).filter_by(taxonomy_id = taxonomy_id, dna_type='GENOMIC').order_by(Dnasequenceannotation.contig_id, Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all():
        locus = dbentity_id_to_locus[x.dbentity_id]
        (soid, soTerm) = so_id_to_so[x.so_id]
        if 'RNA' not in soTerm:
            continue
        if dbentity_id_to_status[x.dbentity_id] != 'Active':
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
            
        sgdid = dbentity_id_to_sgdid[x.dbentity_id]

        row = { "primaryId": "SGD:" + sgdid,
                "taxonId": taxonId,
                "symbol": name }
        
        if x.dbentity_id in locus_id_to_alias_names:
            row["symbolSynonyms"] = locus_id_to_alias_names[x.dbentity_id]

        row["soTermId"] = soid
        row["sequence"] = x.residues
        row["genomeLocations"] = [{ "assembly": assembly,
                                    "exons": [{ "chromosome": chr,
                                                "strand": x.strand,
                                                "startPosition": x.start_index,
                                                "endPosition": x.end_index }]
        }]
        if x.dbentity_id in locus_id_to_ncbi_protein_name:
            row["name"] = locus_id_to_ncbi_protein_name[x.dbentity_id]
        row["url"] = "https://www.yeastgenome.org/locus/" + sgdid
        if x.dbentity_id in dbentity_id_to_pmid_list:
            row["publications"] = dbentity_id_to_pmid_list[x.dbentity_id]
        data.append(row)

    jsonData = { "data": data,
                 "metaData": metaData }

    f = open(data_file, "w")
    f.write(json.dumps(jsonData, indent=4, sort_keys=True))
    f.close()


if __name__ == '__main__':
    
    dump_data()

    


