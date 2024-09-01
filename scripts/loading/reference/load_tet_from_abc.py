import sys
import json
from urllib import request
from scripts.loading.database_session import get_session
from src.models import CurationReference, Literatureannotation

__author__ = 'sweng66'


url = "https://stage-literature-rest.alliancegenome.org/topic_entity_tag/by_mod/SGD"
json_file = "scripts/loading/reference/data/SGD_new_tet.json"
CREATED_BY = 'OTTO'


def load_data():

    nex_session = get_session()

    # download_json_file()
    tet_ids = fetch_all_tets_loaded_past_week(nex_session)

    sgdids = fetch_all_new_sgdids(nex_session)

    (newTags, reference_sgdids, dbentity_sgdids) = read_reference_data_from_abc(
        tet_ids,
        sgdids
    )

    sgdid_to_reference_id = fetch_dbentity_ids_for_sgdids(nex_session, reference_sgdids)
    sgdid_to_dbentity_id = fetch_dbentity_ids_for_sgdids(nex_session, dbentity_sgdids)
    source_id = get_source_id(nex_session)

    topic_atp_to_curation_tag = get_atp_to_curation_tag()
    display_tag_to_lit_topic = get_display_tag_to_lit_topic()

    ref_gene_to_topic = {}
    ref_to_topic = {}
    # all primary and additional display tags need an entity
    taxon_to_taxonomy_id = {}
    for tag in newTags:
        if not topic_atp_to_curation_tag.get(tag['topic']):
            print("The '" + tag['topic_name'] + "' is not allowed 'curation_tag'")
            continue
        taxon = tag['species'].replace("NCBITaxon:", "TAX:")
        taxonomy_id = taxon_to_taxonomy_id.get(taxon)
        if taxonomy_id is None:
            taxonomy_id = get_taxonomy_id(nex_session, taxon)
            taxon_to_taxonomy_id[taxon] = taxonomy_id
        reference_sgdid = tag['curie'].replace("SGD:", "")
        entity_sgdid = tag['entity'].replace("SGD:", "")
        reference_id = sgdid_to_reference_id.get(reference_sgdid)
        dbentity_id = None
        if entity_sgdid:
            dbentity_id = sgdid_to_dbentity_id.get(entity_sgdid)
        insert_into_curation_reference(
            nex_session,
            source_id,
            tag['topic_entity_tag_id'],
            topic_atp_to_curation_tag.get(tag['topic']),
            reference_id,
            dbentity_id,
            tag['note']
        )
        lit_topic = display_tag_to_lit_topic.get(tag['display_tag_name'])
        if lit_topic is None:
            print("ERROR no lit_topic found for " + str(tag['display_tag_name']))
            continue
        
        if dbentity_id:
            if (reference_id, dbentity_id, taxonomy_id) in ref_gene_to_topic:
                if lit_topic == 'Reviews':
                    ref_gene_to_topic[(reference_id, dbentity_id, taxonomy_id)] = lit_topic
                elif lit_topic == 'Primary Literature' and ref_gene_to_topic[(reference_id, dbentity_id, taxonomy_id)] != 'Reviews':
                    ref_gene_to_topic[(reference_id, dbentity_id, taxonomy_id)] = lit_topic
            else:
                ref_gene_to_topic[(reference_id, dbentity_id, taxonomy_id)] = lit_topic
        else:
            ref_to_topic[(reference_id, taxonomy_id)] = lit_topic

    for (reference_id, dbentity_id, taxonomy_id) in ref_gene_to_topic:
        annotation_id, topic_in_db = get_lit_topic(nex_session, reference_id,
                                                   dbentity_id, taxonomy_id)
        if annotation_id is None:
            insert_into_literatureannotation(nex_session, source_id, taxonomy_id,
                                             reference_id, dbentity_id, lit_topic)
        elif lit_topic == 'Reviews' and topic_in_db != 'Reviews':
            update_literatureannotation(nex_session, annotation_id, lit_topic)
        elif lit_topic == 'Primary Literature' and topic_in_db not in ['Primary Literature', 'Reviews']:
            update_literatureannotation(nex_session, annotation_id, lit_topic)

    for (reference_id, taxonomy_id) in ref_to_topic:
        annotation_id, topic_in_db = get_lit_topic(nex_session, reference_id,
                                                   None, taxonomy_id)
        if annotation_id is None:
            insert_into_literatureannotation(nex_session, source_id, taxonomy_id,
                                             reference_id, None, lit_topic)

        elif lit_topic == 'Reviews' and topic_in_db != 'Reviews':
            update_literatureannotation(nex_session, annotation_id, lit_topic)
        elif lit_topic == 'Omics' and topic_in_db not in ['Reviews', 'Omics']:
            update_literatureannotation(nex_session, annotation_id, lit_topic)

    # nex_session.rollback()
    nex_session.commit()
    nex_session.close()
    print("DONE!")

    
def update_literatureannotation(nex_session, annotation_id, lit_topic):

    print("update_literatureannotation: ", annotation_id, lit_topic)
    
    try:
        x = nex_session.query(Literatureannotation).filter_by(annotation_id=annotation_id).one_or_none()
        if x:
            x.topic = lit_topic
            nex_session.add(x)
        print("Updating literatureannotation.topic to '" + lit_topic + "' for annotation_id = " + str(annotation_id))
    except Exception as e:
        print("An error occurred when updating literatureannotation.topic to '" + lit_topic + "' for annotation_id = " + str(annotation_id) + " error = " + str(e))
        
                                            
def insert_into_literatureannotation(nex_session, source_id, taxonomy_id, reference_id, dbentity_id, lit_topic):

    print("insert_into_literatureannotation: ", reference_id, dbentity_id, lit_topic)

    try:
        x = Literatureannotation(dbentity_id = dbentity_id,
                                 source_id = source_id,
                                 taxonomy_id = taxonomy_id,
                                 reference_id = reference_id,
                                 topic = lit_topic,
                                 created_by = CREATED_BY)
        nex_session.add(x)
        print("Adding literatureannotation row for reference_id = " + str(reference_id) + ", dbentity_id = " + str(dbentity_id) + ", topic = " + lit_topic)
    except Exception as e:
        print("An error occurred when adding literatureannotation row for reference_id = " + str(reference_id) + ", dbentity_id = " + str(dbentity_id) + ", topic = '" + lit_topic + "' error = " + str(e))
        
                            
def get_lit_topic(nex_session, reference_id, dbentity_id, taxonomy_id):

    row = None
    if dbentity_id:
        row = nex_session.execute("SELECT annotation_id, topic FROM nex.literatureannotation "
                                  "WHERE reference_id = " + str(reference_id) + " "
                                  "AND taxonomy_id = " + str(taxonomy_id) + " "
                                  "AND dbentity_id = " + str(dbentity_id)).fetchone()
    else:
        row = nex_session.execute("SELECT annotation_id, topic FROM nex.literatureannotation "
                                  "WHERE reference_id = " + str(reference_id) + " "
                                  "AND taxonomy_id = " + str(taxonomy_id)).fetchone()
        
    if row:
        return row['annotation_id'], row['topic']
    return None, None

    
def insert_into_curation_reference(
    nex_session,
    source_id,
    tet_id,
    curation_tag,
    reference_id,
    dbentity_id,
    note
):

    print("insert_into_curation_reference:", source_id, tet_id, curation_tag, reference_id, dbentity_id, note)
    
    try:
        x = CurationReference(source_id = source_id,
                              topic_entity_tag_id = tet_id,
                              curation_tag = curation_tag,
                              reference_id = reference_id,
                              dbentity_id = dbentity_id,
                              curator_comment = note,
                              created_by = CREATED_BY)
        nex_session.add(x)
        print("Adding a new tag '" + curation_tag + "' for reference_id = " + str(reference_id) + " and dbentity_id = " + str(dbentity_id) + " curation_reference table")
    except Exception as e:
        print("An error occurred when adding a new tag '" + curation_tag + "' for reference_id = " + str(reference_id) + " and dbentity_id = " + str(dbentity_id) + " curation_reference table. error = " + str(e))
        
    
def fetch_dbentity_ids_for_sgdids(nex_session, sgdids):
        
    sgdid_list = ','.join(f"'{sgdid}'" for sgdid in sgdids)

    rows = nex_session.execute("SELECT sgdid, dbentity_id "
                               "FROM nex.dbentity "
                               "WHERE dbentity_status = 'Active' "
                               "AND sgdid in (" + sgdid_list + ")").fetchall()

    return {row[0]: row[1] for row in rows}


def download_json_file():

    try:
        print("Downloading " + url)
        req = request.urlopen(url)
        data = req.read()
        with open(json_file, 'wb') as fh:
            fh.write(data)
    except Exception as e:
        print("Error downloading the file: " + file + ". Error=" + str(e))

def get_source_id(nex_session):

    row = nex_session.execute("SELECT source_id FROM nex.source WHERE display_name = 'SGD'").fetchone()
    return row.source_id

def get_taxonomy_id(nex_session, taxon):

    row = nex_session.execute("SELECT taxonomy_id FROM nex.taxonomy WHERE taxid = '" + taxon + "'").fetchone()
    return row.taxonomy_id

def fetch_all_tets_loaded_past_week(nex_session):

    rows = nex_session.execute("SELECT topic_entity_tag_id "
                               "FROM nex.curation_reference "
                               "WHERE topic_entity_tag_id is not null "
                               "AND date_created >= CURRENT_DATE - INTERVAL '7 days'").fetchall()
    
    tet_ids_set = {row[0] for row in rows}


    rows = nex_session.execute("SELECT deleted_row "
                               "FROM nex.deletelog "
                               "WHERE tab_name = 'CURATION_REFERENCE' "
                               "AND date_created >= CURRENT_DATE - INTERVAL '7 days'").fetchall()
    """
    for x in rows:
        pieces = x[0].split("[:]")
        tet_ids_set.add(pieces[-1])
        # 55183[:]374151[:]834[:]1282521[:]Fast Track[:]2014-03-07 00:00:00[:]DIANE[:]Mutations in VMS1, which is a conserved but ill-defined cytoplasmic protein, compromise proteasome assembly and substrate delivery to the proteasome[:]
    """
    
    return tet_ids_set


def fetch_all_new_sgdids(nex_session):

    rows = nex_session.execute("SELECT sgdid FROM nex.dbentity "
                               "WHERE subclass = 'REFERENCE' "
                               "AND dbentity_status = 'Active' "
                               "AND sgdid like 'S1000%'").fetchall()

    return {row[0] for row in rows}


def read_reference_data_from_abc(tet_ids, sgdids):

    json_data = dict()
    with open(json_file) as f:
        json_str = f.read()
        json_data = json.loads(json_str)

    data = []
    reference_sgdids = set()
    locus_sgdids = set()
    tet_ids_from_abc = set()
    for x in json_data['data']:
        sgdid = x['curie'].replace("SGD:", "")
        tet_id = x['topic_entity_tag_id']
        if sgdid not in sgdids or tet_id in tet_ids:
            continue
        if tet_id in tet_ids_from_abc:
            continue
        tet_ids_from_abc.add(tet_id)
        reference_sgdids.add(sgdid)
        locus_sgdids.add(x['entity'].replace("SGD:", ""))
        data.append(x)

    return (data, reference_sgdids, locus_sgdids)


def get_atp_to_curation_tag():

    # "ATP:0000128": "Complexes",
    return {
        "ATP:0000012": "GO information",
        "ATP:0000079": "Classical phenotype information",
        "ATP:0000129": "Headline information",
        "other primary info": "other primary information",
        "review": "reviews",
        "ATP:0000085": "HTP phenotype",
        "ATP:0000150": "Non-phenotype HTP",
        "ATP:0000011": "Homology/Disease",
        "ATP:0000088": "Post-translational modifications",
        "ATP:0000070": "Regulation information",
        "ATP:0000022": "Pathways",
        "ATP:0000149": "Engineering",
        "ATP:0000054": "Gene model",
        "ATP:0000006": "Alleles",
        "other additional literature": "other additional literature"
    }


def get_display_tag_to_lit_topic():

    # display_tag_name": "primary display"
    
    return {
        "OMICs display": "Omics",
        "review display": "Reviews",
        "additional display": "Additional Literature",
        "primary display": "Primary Literature"
    }


"""
"curie": "SGD:S100000038",
"topic_entity_tag_id": 197578,
"reference_id": 1043450,
"topic": "ATP:0000129",
"entity_type": "ATP:0000005",
"date_created": "2024-08-30T17:41:37.411955",
"date_updated": "2024-08-30T17:41:37.411970",
"created_by": "00u4tk5hnbgct5lQm5d7",
"updated_by": "00u4tk5hnbgct5lQm5d7",
"entity": "SGD:S000002592",
"entity_published_as": null,
"species": "NCBITaxon:559292",
"display_tag": "ATP:0000147",
"confidence_level": null,
"negated": false,
"note": null,
"topic_entity_tag_source_id": 157,
"novel_topic_data": false,
"entity_id_validation": "alliance",
"validation_by_author": "not_validated",
"validation_by_professional_biocurator": "validated_right_self",
"email": "sweng@stanford.edu",
"topic_name": "headline",
"entity_type_name": "gene",
"entity_name": "ATC1",
"species_name": "Saccharomyces cerevisiae S288C",
"display_tag_name": "primary display"
"""


if __name__ == '__main__':

    load_data()
