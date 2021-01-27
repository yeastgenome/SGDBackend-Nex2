from src.models import LocusUrl, Locusdbentity, So, Source, Taxonomy, Dnasequenceannotation 
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

def load_data():

    nex_session = get_session()

    so = nex_session.query(So).filter_by(display_name = 'ORF').one_or_none()
    so_id = so.so_id

    src = nex_session.query(Source).filter_by(display_name = 'YeastRGB').one_or_none()
    source_id = src.source_id

    taxonomy = nex_session.query(Taxonomy).filter_by(taxid= 'TAX:559292').one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    
    dbentity_id_to_url_id = dict([(x.locus_id, x.url_id) for x in nex_session.query(LocusUrl).filter_by(display_name='YeastRGB').all()])
    
    dbentity_id_to_name = dict([(x.dbentity_id, x.systematic_name) for x in nex_session.query(Locusdbentity).filter_by(dbentity_status='Active').all()])

    i = 0
    for x in nex_session.query(Dnasequenceannotation).filter_by(so_id=so_id, taxonomy_id=taxonomy_id, dna_type='GENOMIC').all():
        if x.dbentity_id not in dbentity_id_to_name:
            continue
        if x.dbentity_id in dbentity_id_to_url_id:
            continue
        orf = dbentity_id_to_name[x.dbentity_id]
        obj_url = "http://shmoo.weizmann.ac.il/elevy/YeastRGB/HTML/YeastRGB.html?search=" + orf
                
        y = LocusUrl(display_name = 'YeastRGB',
                     obj_url = obj_url,
                     source_id = source_id,
                     locus_id = x.dbentity_id,
                     url_type = 'Systematic name',
                     placement = 'LOCUS_PROTEIN_RESOURCES_LOCALIZATION',
                     created_by = 'OTTO')
        nex_session.add(y)
        
        i = i + 1
        print (i, obj_url)
        
        if i > 300:        
            # nex_session.rollback()
            nex_session.commit()
            i = 0
   
    # nex_session.rollback()
    nex_session.commit()
    
    nex_session.close()

    print ("DONE!")
        
if __name__ == "__main__":

    load_data()


    
        
