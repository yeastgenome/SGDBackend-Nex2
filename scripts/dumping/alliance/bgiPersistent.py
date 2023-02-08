import os
import json
from sqlalchemy import create_engine
import concurrent.futures
from src.models import Dnasequenceannotation, DBSession, Locusdbentity
from src.data_helpers import get_pers_output

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600)
SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION', '_1.5.0_')
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
                    "internal": False
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

                obj["gene_synopsis"] = item.description
                obj["gene_symbol_dto"] = item.gene_name if item.gene_name is not None else item.systematic_name
                #obj["note_dto"] = [ {"free_text": disSumObj.text, "note_type_name": "disease_summary", "internal": False}]
                obj["curie"] = "SGD:" + item.sgdid

                result.append(obj)

            if (len(result) > 0):
                print("# of bgi objects:" + str(len(result)))

                output_obj = get_pers_output(SUBMISSION_TYPE, result)

                file_name = 'SGD' + SUBMISSION_VERSION + 'bgiPersistent.json'
                json_file_str = os.path.join(local_dir, file_name)
                with open(json_file_str, 'w+') as res_file:
                    res_file.write(json.dumps(output_obj, indent=4, sort_keys=True))
if __name__ == '__main__':
    get_basic_gene_information()
