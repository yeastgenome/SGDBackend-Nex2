import sys
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

# Dump every literature annotation in nex.literatureannotation:
# - references along with their associated gene, allele, complex, and pathway
#   entities -- the same entity set displayed on the /reference/{id} pages
#   (see Referencedbentity.annotations_to_dict and Literatureannotation.to_dict
#   in src/models.py), one row per (reference, entity), and
# - the annotations that have no entity at all (dbentity_id is null) -- e.g.
#   review papers and omics (HTP) papers tagged with just a literature topic --
#   one row per (reference, topic) with the entity columns left empty.
#
# Output format (tab-delimited):
#     reference_sgdid  entity_type  entity_name  entity_sgdid  date_created  created_by  topic
# where date_created (YYYY-MM-DD HH:MM:SS, in the SGD database's local
# Pacific time) and created_by are when the entity-reference association (the
# literature annotation) was curated and by whom -- NOT when the reference
# itself was added to SGD,
# entity_type is one of: gene, allele, complex, pathway -- or empty for a
# topic-only annotation (entity_name and entity_sgdid are then empty too),
# entity_name is, eg, ACT1 (gene), act1-1 (allele), CPX-2921 (complex),
# or PWY3O-46 (pathway biocyc id)
# and topic is the literature topic the annotation is under (the section of
# the reference page it appears in: Primary Literature, Additional
# Literature, Reviews, or Omics). An entity annotated under several topics for
# the same reference is written once with the highest-precedence topic
# (Primary Literature > Reviews > Omics > Additional Literature), carrying
# that annotation's date_created/created_by; topic-only annotations are never
# collapsed across topics (each one marks the paper for a different section).
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

topic_precedence = {
    'Primary Literature': 0,
    'Reviews': 1,
    'Omics': 2,
    'Additional Literature': 3
}


def dump_data():

    nex_session = get_session()

    rows = nex_session.execute("SELECT DISTINCT r.sgdid AS reference_sgdid, "
                               "       d.subclass, "
                               "       d.display_name, "
                               "       d.format_name, "
                               "       d.sgdid AS entity_sgdid, "
                               "       p.biocyc_id, "
                               "       to_char(la.date_created, 'YYYY-MM-DD HH24:MI:SS') AS date_created, "
                               "       la.created_by, "
                               "       la.topic "
                               "FROM nex.literatureannotation la "
                               "JOIN nex.dbentity r ON la.reference_id = r.dbentity_id "
                               "LEFT JOIN nex.dbentity d ON la.dbentity_id = d.dbentity_id "
                               "LEFT JOIN nex.pathwaydbentity p ON la.dbentity_id = p.dbentity_id "
                               "WHERE la.dbentity_id IS NULL "
                               "   OR d.subclass IN ('LOCUS', 'ALLELE', 'COMPLEX', 'PATHWAY') "
                               "ORDER BY r.sgdid, d.subclass, d.display_name").fetchall()

    # one output row per (reference, entity) -- an entity annotated under
    # several literature topics keeps the highest-precedence one -- plus one
    # row per (reference, topic) for the topic-only annotations
    key_order = []
    deduped = {}
    for x in rows:
        (reference_sgdid, subclass, display_name, format_name, entity_sgdid,
         biocyc_id, date_created, created_by, topic) = x
        if subclass is None:
            # topic-only annotation (no entity): the (reference, topic) pair
            # is unique in nex.literatureannotation, so no dedupe is needed
            key = (reference_sgdid, '', topic)
            key_order.append(key)
            deduped[key] = [reference_sgdid, '', '', '',
                            date_created, created_by, topic]
            continue
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
        key = (reference_sgdid, entity_sgdid, '')
        if key in deduped:
            previous = deduped[key]
            if topic_precedence.get(topic, len(topic_precedence)) < \
                    topic_precedence.get(previous[6], len(topic_precedence)):
                # keep the date/curator of the annotation whose topic wins
                previous[4] = date_created
                previous[5] = created_by
                previous[6] = topic
            continue
        key_order.append(key)
        deduped[key] = [reference_sgdid, entity_type, entity_name, entity_sgdid,
                        date_created, created_by, topic]

    fw = open(outfile, "w")
    fw.write("reference_sgdid\tentity_type\tentity_name\tentity_sgdid\tdate_created\tcreated_by\ttopic\n")

    count = 0
    for key in key_order:
        fw.write("\t".join(deduped[key]) + "\n")
        count = count + 1

    fw.close()
    nex_session.close()

    print("Done! " + str(count) + " rows written to " + outfile)


if __name__ == '__main__':

    dump_data()
