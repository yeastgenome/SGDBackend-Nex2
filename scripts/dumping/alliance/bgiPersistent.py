import os
import json
from sqlalchemy import create_engine, and_
import concurrent.futures
from src.models import Dnasequenceannotation, DBSession, Locusdbentity, LocusAlias, LocusReferences, Referencedbentity
from src.data_helpers import get_pers_output, get_locus_synonyms, get_locus_crossrefs, get_locus_secondaryids

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION')
LINKML_VERSION = os.getenv('LINKML_VERSION', 'v1.11.0')
DBSession.configure(bind=engine)
SUBMISSION_TYPE = 'gene_ingest_set'
local_dir = 'scripts/dumping/alliance/data/'
SO_TYPES_TO_EXCLUDE = [
    'SO:0000186', 'SO:0000577', 'SO:0000286', 'SO:0000296', 'SO:0005855',
    'SO:0001984', 'SO:0002026', 'SO:0001789', 'SO:0000436', 'SO:0000624',
    'SO:0000036', 'SO:0002059'
]


def get_basic_gene_information():

    combined_list = Locusdbentity.get_s288c_genes()

    print(("computing " + str(len(combined_list)) + " s288c genes"))
    result = []
    if (len(combined_list) > 0):

        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            for item in combined_list:
                obj = {
                    "taxon_curie": "NCBITaxon:559292",
                    "internal": False,
                    "obsolete" : False
                }
                dna_seq_annotation_obj = DBSession.query(
                    Dnasequenceannotation).filter(
                        Dnasequenceannotation.dbentity_id == item.dbentity_id,
                        Dnasequenceannotation.taxonomy_id == 274901,
                        Dnasequenceannotation.dna_type == "GENOMIC").all()
                # IF it is a SO ID to exclude, then skip ('continue')
                if dna_seq_annotation_obj[0].so.soid in SO_TYPES_TO_EXCLUDE:
                   continue
                if dna_seq_annotation_obj[0].so.so_id == 263757:  #change ORF to gene SO ID
                    obj["gene_type_curie"] = "SO:0001217"
                else:
                    obj["gene_type_curie"] = dna_seq_annotation_obj[0].so.soid

                pmids_results = DBSession.query(LocusReferences,Referencedbentity.pmid).filter(and_(LocusReferences.locus_id == item.dbentity_id,
                         LocusReferences.reference_class == 'gene_name')).outerjoin(Referencedbentity).all()

                gene_name_pmids = ["PMID:"+str(x[1]) for x in pmids_results if str(x[1]) != 'None']

                obj["data_provider_dto"] = {
                    "created_by_curie" : "SGD",
                    "updated_by_curie": "SGD",
                    "cross_reference_dto": {
                        "created_by_curie": "SGD",
                        "display_name": item.gene_name if item.gene_name is not None else item.systematic_name,
                        "internal": False,
                        "obsolete": False,
                        "page_area": "gene",
                        "prefix": "SGD",
                        "referenced_curie": "SGD:" + item.sgdid,
                        "updated_by_curie": "SGD"
                    },
                    "source_organization_abbreviation": "SGD",
                    "internal": False,
                    "obsolete": False
                }

                obj["gene_symbol_dto"] = {
                    "created_by_curie": "SGD",
                    "updated_by_curie": "SGD",
                    "name_type_name": "nomenclature_symbol",
                    "format_text": item.gene_name if item.gene_name is not None else item.systematic_name,
                    "display_text": item.gene_name if item.gene_name is not None else item.systematic_name,
                    "internal": False,
                    "obsolete": False,
                    "synonym_scope_name": "exact",
                }
                # if (len(gene_name_pmids) > 0):
                #     obj["gene_symbol_dto"].append({
                #         "evidence_curies": gene_name_pmids
                #     })

                obj["gene_full_name_dto"] = {
                    "name_type_name": "full_name",
                    "format_text": item.gene_name if item.gene_name is not None else item.systematic_name,
                    "display_text": item.gene_name if item.gene_name is not None else item.systematic_name,
                    "internal": False,
                    "obsolete": False,
                    "synonym_scope_name": "exact"
                }

                obj["gene_systematic_name_dto"] = {
                    "name_type_name": "systematic_name",
                    "format_text": item.systematic_name,
                    "display_text": item.systematic_name,
                    "internal": False
                }

                # get locus alias info
                locus_alias_data = DBSession.query(LocusAlias).filter(LocusAlias.locus_id == item.dbentity_id).all()

                if (len(locus_alias_data) > 0):
                    objAlias = get_locus_synonyms(locus_alias_data)
                    if(len(objAlias) > 0):
                        obj["gene_synonym_dtos"] = objAlias
                if (len(locus_alias_data) > 0):
                    objCrossRefs = get_locus_crossrefs(locus_alias_data)
                    if(len(objCrossRefs) > 0):
                        obj["cross_reference_dtos"] = objCrossRefs

                if (len(locus_alias_data) > 0):
                    objSecondary = get_locus_secondaryids(locus_alias_data)
                    if (len(objSecondary) > 0):
                        obj["gene_secondary_id_dtos"] = objSecondary

                obj["curie"] = "SGD:" + item.sgdid
                obj["date_created"] = item.date_created.strftime("%Y-%m-%dT%H:%m:%S-00:00")
                obj["date_updated"] = item.date_created.strftime("%Y-%m-%dT%H:%m:%S-00:00")
                obj["created_by_curie"] = "SGD"
                obj["updated_by_curie"] = "SGD"

                result.append(obj)

            if (len(result) > 0):
                print("# of bgi objects:" + str(len(result)))
                output_obj = get_pers_output(SUBMISSION_TYPE, result, LINKML_VERSION)
                file_name = 'SGD' + SUBMISSION_VERSION + 'bgiPersistent.json'
                json_file_str = os.path.join(local_dir, file_name)
                with open(json_file_str, 'w+') as res_file:
                    res_file.write(json.dumps(output_obj, indent=4, sort_keys=False))

    DBSession.close()

if __name__ == '__main__':
    get_basic_gene_information()
