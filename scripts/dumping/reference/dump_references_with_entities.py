import sys
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

# Dump all references along with their associated gene, allele, complex, and
# pathway entities -- the same entity set displayed on the /reference/{id}
# pages (from literature annotations; see Referencedbentity.annotations_to_dict
# and Literatureannotation.to_dict in src/models.py). References that have no
# associated entities are not included in the output.
#
# Output format (tab-delimited):
#     reference_sgdid  entity_type  entity_name  entity_sgdid  date_created  created_by
# where date_created (YYYY-MM-DD) and created_by are when the reference was
# added to SGD and by whom,
# entity_type is one of: gene, allele, complex, pathway
# and entity_name is, eg, ACT1 (gene), act1-1 (allele), CPX-2921 (complex),
# or PWY3O-46 (pathway biocyc id)
#
# Usage: python scripts/dumping/reference/dump_references_with_entities.py [outfile]

outfile = 'scripts/dumping/reference/data/references_with_entities.tsv'
if len(sys.argv) > 1:
    outfile = sys.argv[1]

subclass_to_entity_type = {
    'LOCUS': 'gene',
    'ALLELE': 'allele',
    'COMPLEX': 'complex',
    'PATHWAY': 'pathway'
}


def dump_data():

    nex_session = get_session()

    rows = nex_session.execute("SELECT DISTINCT r.sgdid AS reference_sgdid, "
                               "       d.subclass, "
                               "       d.display_name, "
                               "       d.format_name, "
                               "       d.sgdid AS entity_sgdid, "
                               "       p.biocyc_id, "
                               "       to_char(r.date_created, 'YYYY-MM-DD') AS date_created, "
                               "       r.created_by "
                               "FROM nex.literatureannotation la "
                               "JOIN nex.dbentity r ON la.reference_id = r.dbentity_id "
                               "JOIN nex.dbentity d ON la.dbentity_id = d.dbentity_id "
                               "LEFT JOIN nex.pathwaydbentity p ON la.dbentity_id = p.dbentity_id "
                               "WHERE d.subclass IN ('LOCUS', 'ALLELE', 'COMPLEX', 'PATHWAY') "
                               "ORDER BY r.sgdid, d.subclass, d.display_name").fetchall()

    fw = open(outfile, "w")
    fw.write("reference_sgdid\tentity_type\tentity_name\tentity_sgdid\tdate_created\tcreated_by\n")

    count = 0
    for x in rows:
        (reference_sgdid, subclass, display_name, format_name, entity_sgdid, biocyc_id, date_created, created_by) = x
        entity_type = subclass_to_entity_type[subclass]
        if entity_type == 'gene' or entity_type == 'allele':
            entity_name = display_name
        elif entity_type == 'complex':
            entity_name = format_name
        else:
            entity_name = biocyc_id if biocyc_id else format_name
        # a couple of allele display names contain embedded tabs; collapse
        # any whitespace runs to a single space to keep the tsv well-formed
        entity_name = " ".join(entity_name.split())
        fw.write(reference_sgdid + "\t" + entity_type + "\t" + entity_name + "\t" +
                 entity_sgdid + "\t" + date_created + "\t" + created_by + "\n")
        count = count + 1

    fw.close()
    nex_session.close()

    print("Done! " + str(count) + " rows written to " + outfile)


if __name__ == '__main__':

    dump_data()
