from scripts.loading.database_session import get_session

nex_session = get_session()

## S288C
taxonomy_id = 274901

"""
alliance non gene soid list:
'SO:0000186', 'SO:0000577', 'SO:0000286', 'SO:0000296', 
'SO:0005855', 'SO:0001984', 'SO:0002026', 'SO:0001789', 
'SO:0000436', 'SO:0000624', 'SO:0000036', 'SO:0002059'

allinance non gene feature_type list:

matrix attachment site
LTR retrotransposon
long terminal repeat
origin of replication
ARS
centromere
telomere
mating type region
silent mating type cassette array
intein encoding region
recombination enhancer
gene group

alliance gene feature_type list:

ORF
snRNA gene
snoRNA gene
rRNA gene
tRNA gene
ncRNA gene
transposable element gene
pseudogene
blocked reading frame

"""

allianceNonGeneSOIDs = [
    'SO:0000186', 'SO:0000577', 'SO:0000286', 'SO:0000296',
    'SO:0005855', 'SO:0001984', 'SO:0002026', 'SO:0001789',
    'SO:0000436', 'SO:0000624', 'SO:0000036', 'SO:0002059' 
]

rows = nex_session.execute(
    f"SELECT d.dbentity_id, s.soid "
    f"FROM   nex.dnasequenceannotation d, nex.so s "
    f"WHERE  d.taxonomy_id = {taxonomy_id} "
    f"AND    d.dna_type = 'GENOMIC' "
    f"AND    d.so_id = s.so_id").fetchall()

dbentity_id_to_entity_type = {}

for x in rows:
    entity_type = 'gene'
    if x[1] in allianceNonGeneSOIDs:
        entity_type = 'genomic region'
    dbentity_id_to_entity_type[x[0]] = entity_type

rows = nex_session.execute(
    "SELECT rd.pmid, cr.curation_tag, " 
    "       cr.curator_comment, cr.created_by, cr.date_created, d.sgdid, "
    "       d2.dbentity_id, d2.subclass, d2.display_name, d2.sgdid "
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
    dbentity_id = x[6]
    entity_type = x[7].lower() if x[7] else ''
    if entity_type == 'locus':
        entity_type = dbentity_id_to_entity_type[dbentity_id]
    entity_name = x[8] if x[8] else ''
    entity_sgdid = "SGD:" + x[9] if x[9] else ''
                     
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
                      
