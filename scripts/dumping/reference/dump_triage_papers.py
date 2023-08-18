from scripts.loading.database_session import get_session

nex_session = get_session()

rows = nex_session.execute(
    "SELECT rd.pmid, cr.curation_tag, " 
    "       cr.curator_comment, cr.created_by, cr.date_created, d.sgdid, "
    "       d2.subclass, d2.display_name, d2.sgdid "
    "FROM   nex.curation_reference cr "
    "JOIN   nex.dbentity d ON cr.reference_id = d.dbentity_id "
    "JOIN   nex.referencedbentity rd ON d.dbentity_id = rd.dbentity_id "
    "LEFT JOIN nex.dbentity d2 ON cr.dbentity_id = d2.dbentity_id").fetchall()

                           
print("reference_pmid\treference_sgdid\tcuration_tag\tentity_type\tentity_name\tentity_sgdid\tnote\tcreated_by\tdate_created")
for x in rows:
    pmid = "PMID:" + str(x[0]) if x[0] else ''
    curation_tag = x[1]
    note = x[2].replace("\n", "") if x[2] else ''    
    created_by = x[3]
    date_created = str(x[4]).split(" ")[0]
    sgdid = "SGD:" + x[5]
    entity_type = x[6].lower().replace("locus", "gene") if x[6] else ''
    entity_name = x[7] if x[7] else ''
    entity_sgdid = "SGD:" + x[8] if x[8] else ''
                     
    print(pmid + "\t" + sgdid + "\t" + curation_tag + "\t" +  entity_type + "\t" + entity_name + "\t" + entity_sgdid + "\t" + note  + "\t" + created_by + "\t" + date_created)
                           
                           

nex_session.close()

"""
curation_reference:

curation_id
reference_id
dbentity_id
curation_tag
date_created
created_by
curator_comment

literatureannotation:

dbentity_id
source_id
bud_id
taxonomy_id
reference_id
topic
date_created
created_by
"""
                      
