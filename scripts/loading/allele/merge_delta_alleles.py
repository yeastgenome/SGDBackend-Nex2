import logging
import os
from datetime import datetime
import sys
from src.models import Source, Dbentity, Alleledbentity, AlleleReference, LocusAllele, LocusalleleReference, \
                       AlleleAlias, AllelealiasReference, Phenotypeannotation
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

def update_data():

    nex_session = get_session()

    log.info(str(datetime.now()))
    log.info("Getting data from database...")

    allele_to_allele_id = dict([(x.display_name.upper(), (x.dbentity_id, x.sgdid)) for x in nex_session.query(Dbentity).filter_by(subclass='ALLELE').all()])
    
    all = nex_session.query(Alleledbentity).filter(Alleledbentity.display_name.like('%-delta%')).all()

    for x in all:
        allele_name = x.display_name.replace("-delta", "-Δ")
        if allele_name.upper() in allele_to_allele_id:
            (new_allele_id, sgdid) = allele_to_allele_id[allele_name.upper()]
            print (x.display_name, allele_name, new_allele_id)

            print ("getting old locus_allele_id for allele_id = x.dbentity_id")
            
            old_la = nex_session.query(LocusAllele).filter_by(allele_id=x.dbentity_id).one_or_none()

            if old_la:
                
                old_locus_allele_id = old_la.locus_allele_id

                print ("old_locus_allele_id =", old_la.locus_allele_id)
            
                print ("getting new locus_allele_id for allele_id = new_allele_id")
            
                new_la = nex_session.query(LocusAllele).filter_by(allele_id=new_allele_id).one_or_none()
                new_locus_allele_id = new_la.locus_allele_id

                print ("new_locus_allele_id=", new_locus_allele_id)
            
                print ("updating locusallele_reference to set locus_allele_id to new locus_allele_id where locus_allele_id = old locus_allele_id")
            
                nex_session.query(LocusalleleReference).filter_by(locus_allele_id=old_locus_allele_id).update({"locus_allele_id": new_locus_allele_id})
            
                print ("deleting old locus_allele where allele_id = x.dbentity_id")
            
                nex_session.delete(old_la)
                
            print ("getting old reference_ids from allele_reference where allele_id = x.dbentity_id")
            
            old_reference_ids = nex_session.query(AlleleReference.reference_id).filter_by(allele_id=x.dbentity_id).all()

            print ("old_reference_ids=", old_reference_ids)
            
            print ("deleting allele_reference rows where allele_id = x.dbentity_id")

            old_ar = nex_session.query(AlleleReference).filter_by(allele_id=x.dbentity_id).all()
            for x in old_ar:
                nex_session.delete(x)
            
            print ("updating allele_alias to set allele_id to new allele_id where allele_id = x.dbentity_id")
            
            nex_session.query(AlleleAlias).filter_by(allele_id=x.dbentity_id).update({"allele_id": new_allele_id})
            
            print ("adding x.display_name to allele_alias and associate it with allele_id = new_allele_id and alias_type = 'Synonym'")
            
            src = nex_session.query(Source).filter_by(display_name = 'SGD').one_or_none()
            aa = AlleleAlias(display_name = x.display_name,
                             allele_id = new_allele_id,
                             alias_type = 'Synonym',
                             source_id = src.source_id,
                             created_by = 'OTTO')
            nex_session.add(aa)
            nex_session.flush()
            nex_session.refresh(aa)
            new_allele_alias_id = aa.allele_alias_id

            print (" new_allele_alias_id=",  new_allele_alias_id)
            
            print ("adding newly created allele_alias_id to locusalias_referece and link the row with old reference_ids")
            
            for reference_id in old_reference_ids:
                aar = AllelealiasReference(allele_allele_id = new_allele_alias_id,
                                           reference_id = reference_id,
                                           source_id = src.source_id,
                                           created_by = 'OTTO')
                
            print ("adding old sgdid to allele_alias and associate it with allele_id = new_allele_id and alias_type = 'SGDID Secondary'")
            
            aa = AlleleAlias(display_name = x.sgdid,
                             allele_id = new_allele_id,
                             alias_type = 'SGD Secondary',
                             source_id = src.source_id,
                             created_by = 'OTTO')
            nex_session.add(aa)
            nex_session.flush()
            nex_session.refresh(aa)
            
            print ("updating phenotypeannotation to point allele_id to new_allele_id where allele_id=x.dbentity_id")

            nex_session.query(Phenotypeannotation).filter_by(allele_id=x.dbentity_id).update({"allele_id": new_allele_id})
            
            print ("deleting row from alleledbentity and dbentity tables for dbentity_id = x.dbentity_id")
            
            allele_id = x.dbentity_id
            nex_session.query(Alleledbentity).filter_by(dbentity_id=allele_id).delete()
            
            nex_session.query(Dbentity).filter_by(dbentity_id=allele_id).delete()
            
            
    # nex_session.rollback()
    nex_session.commit()
    nex_session.close()

    
if __name__ == "__main__":
    
    update_data()
