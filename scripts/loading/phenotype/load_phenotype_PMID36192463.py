import os
import traceback
from src.models import Apo, Dbentity, Locusdbentity, Referencedbentity, Phenotypeannotation, \
    PhenotypeannotationCond, Taxonomy, Chebi, Phenotype, Source, Straindbentity, LocusAlias, \
    AlleleAlias, So, Alleledbentity, LocusAllele, LocusalleleReference
from scripts.loading.database_session import get_session

infile = "scripts/loading/phenotype/data/PMID36192463HTPpheno021424.tsv"
logfile = "scripts/loading/phenotype/logs/PMID36192463HTPpheno021424.log"
pmid = 36192463
observable_val = "resistance to chemicals"
strain_background = "S288C"
strain_name = "Y7092"
experiment_type = "systematic mutation set"
mutant_type = "conditional"
allele_type = "gene variant"
CREATED_BY = os.environ['DEFAULT_USER']

batch_commit_size = 250


def load_phenotypes():
 
    nex_session = get_session()

    allele_to_id = dict([(x.format_name.lower(), x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(
        subclass='ALLELE').all()])

    alias_name_to_allele_id = dict([(x.display_name.lower(), x.allele_id) for x in nex_session.query(AlleleAlias).all()])

    locus_id_alias_id_to_locus_allele_id = dict([((x.locus_id, x.allele_id), x.locus_allele_id) for x in nex_session.query(LocusAllele).all()])
    
    name_to_locus_id = {}
    for x in nex_session.query(Locusdbentity).all():
        name_to_locus_id[x.systematic_name.lower()] = x.dbentity_id
        if x.gene_name:
            name_to_locus_id[x.gene_name.lower()] = x.dbentity_id

    alias_name_to_locud_id = dict([(x.display_name.lower(), x.locus_id) for x in nex_session.query(LocusAlias).filter_by(
        alias_type='Uniform').all()])
    
    sgd = nex_session.query(Source).filter_by(format_name='SGD').one_or_none()
    source_id = sgd.source_id

    print("source_id=", source_id)
    
    strain = nex_session.query(Straindbentity).filter_by(display_name='S288C').one_or_none()
    taxonomy_id = strain.taxonomy_id

    print("taxonomy_id=", taxonomy_id)
    
    ref = nex_session.query(Referencedbentity).filter_by(pmid=pmid).one_or_none()
    reference_id = ref.dbentity_id

    print("ref_id=", reference_id)
    
    mutant = nex_session.query(Apo).filter_by(apo_namespace='mutant_type', display_name=mutant_type).one_or_none()
    mutant_id = mutant.apo_id

    print("mutant_id=", mutant_id)
    
    expt = nex_session.query(Apo).filter_by(apo_namespace='experiment_type', display_name=experiment_type).one_or_none()
    experiment_id = expt.apo_id

    print("experiment_id=", experiment_id)

    phenotype = nex_session.query(Phenotype).filter_by(display_name=observable_val).one_or_none()
    pheno_id = phenotype.phenotype_id

    print("pheno_id=", pheno_id)
    
    phenotype_d = nex_session.query(Phenotype).filter_by(display_name=observable_val + ": decreased").one_or_none()
    decreased_pheno_id = phenotype_d.phenotype_id 

    print("decreased_pheno_id=", decreased_pheno_id)
    
    phenotype_i = nex_session.query(Phenotype).filter_by(display_name=observable_val + ": increased").one_or_none()
    increased_pheno_id = phenotype_i.phenotype_id

    print("increased_pheno_id=", increased_pheno_id)

    so = nex_session.query(So).filter_by(display_name=allele_type).one_or_none()
    so_id = so.so_id

    print("so_id=", so_id)
    
    f = open(infile)
    fw = open(logfile, "w")

    i = 0
    chemicals = []
    key_to_annotation_id = {}
    for line in f:
        pieces = line.strip().split("\t")
        if pieces[0].lower() == 'allele':
            for chemical in pieces[1:]:
                items = chemical.split("_")
                chebi = nex_session.query(Chebi).filter_by(format_name=items[0]).one_or_none()
                chemicals.append((chebi.display_name, items[1], items[2]))
            continue
        allele_name = pieces[0]
        allele_id = allele_to_id.get(allele_name.lower())
        if allele_id is None:
            allele_id = alias_name_to_allele_id.get(allele_name.lower())
            if allele_id:
                # arp3-g302y, arp3-h161a, cdc2-1, cdc2-2, cdc2-7, cdc46-1, sec26-f856aw860a
                print("ALLELE:", allele_name, "is an alias name.")
            else:
                print("ALLELE:", allele_name, "is not in the database.")
                ## insert new allele into database
                allele_id = insert_dbentity(nex_session, allele_name, source_id)
                if allele_id is None:
                    print("ALLELE:", allele_name, "is not added into the DBENTITY table.")
                    continue
                allele_id = insert_alleledbentity(nex_session, allele_id, so_id, allele_name)
                if allele_id is None:
                    print("ALLELE:", allele_name, "is not added into the ALLELEDBENTITY table.")
                    continue
        gene_name = allele_name.split("-")[0]
        dbentity_id = name_to_locus_id.get(gene_name.lower())
        if dbentity_id is None:
            dbentity_id = alias_name_to_locud_id.get(gene_name.lower())
            if dbentity_id:
                # cdc1, cdc46, hys2,
                print("GENE:", gene_name, "is an alias name.")
            else:
                print("GENE:", gene_name, "is not in the database.")
                continue
        locus_allele_id = locus_id_alias_id_to_locus_allele_id.get((dbentity_id, allele_id))
        if locus_allele_id is None:
            locus_allele_id = insert_locus_allele(nex_session, source_id, dbentity_id,
                                                  allele_id, allele_name)
        if locus_allele_id is None:
            nex_session.rollback()
            continue
        status = insert_locusallele_reference(nex_session, source_id, locus_allele_id,
                                              reference_id, allele_name)
        if status:
            nex_session.rollback()
            continue
        values = pieces[1:]
        for index in range(3):
            (chemical_name, chemical_value, chemical_unit) = chemicals[index]
            phenotype_id = None
            if values[index] == 'NA':
                phenotype_id = pheno_id
            elif float(values[index]) < 0:
                phenotype_id = decreased_pheno_id
            elif float(values[index]) > 0:
                phenotype_id = increased_pheno_id
            else:
                phenotype_id = pheno_id
            i += 1
            key = (allele_id, dbentity_id, phenotype_id)
            annotation_id = key_to_annotation_id.get(key)
            if annotation_id is None:
                annotation_id = insert_phenotypeannotation(nex_session, dbentity_id, source_id,
                                                           taxonomy_id, reference_id, phenotype_id,
                                                           experiment_id, mutant_id, allele_id,
                                                           strain_name, allele_name)
            if annotation_id is None:
                nex_session.rollback()
                continue
            key_to_annotation_id[key] = annotation_id
            insert_phenotypeannotation_cond(nex_session, annotation_id, 1, chemical_name, chemical_value, chemical_unit, allele_name)
            if i % batch_commit_size == 0:
                nex_session.rollback()
                # nex_session.commit()

    f.close()
    fw.close()
    nex_session.rollback()
    # nex_session.commit()
    nex_session.close()


def insert_locusallele_reference(nex_session, source_id, locus_allele_id, reference_id, allele_name):

    print("locusallele_reference:", source_id, locus_allele_id, reference_id, allele_name, CREATED_BY)

    try:
        x = LocusalleleReference(source_id = source_id,
                                 locus_allele_id = locus_allele_id,
                                 reference_id = reference_id,
                                 created_by = CREATED_BY)
        nex_session.add(x)
        print("Adding locusallele_reference for allele: " + allele_name + ", reference_id " + str(reference_id) + " into database.")
        return 0
    except Exception as e:
        traceback.print_exc()
        print("An error occurred when inserting locusallele_reference for allele: " + allele_name + ", reference_id " + str(reference_id) + " into the database. error=" + str(e))
        return 1


def insert_locus_allele(nex_session, source_id, locus_id, allele_id, allele_name):

    print("locus_allele:", source_id, locus_id, allele_id, allele_name, CREATED_BY)
    try:
        x = LocusAllele(source_id = source_id,
                        locus_id = locus_id,
                        allele_id = allele_id,
                        created_by = CREATED_BY)
        nex_session.add(x)
        nex_session.flush()
        nex_session.refresh(x)
        print("Adding locus_allele for allele: " + allele_name + " into database.")
        return x.locus_allele_id
    except Exception as e:
        traceback.print_exc()
        print("An error occurred when inserting locus_allele for allele: " + allele_name + " into the database. error=" + str(e))
        return None
    

def insert_phenotypeannotation_cond(nex_session, annotation_id, group_id, condition_name, condition_value, condition_unit, allele_name):

    print("phenotypeannotation_cond:", annotation_id, group_id, condition_name, condition_value, condition_unit, allele_name, CREATED_BY)
    
    try:
        x = PhenotypeannotationCond(annotation_id = annotation_id,
                                    group_id =  group_id,   
                                    condition_class = 'chemical',
                                    condition_name = condition_name,
                                    condition_value = condition_value,
                                    condition_unit = condition_unit,
                                    created_by = CREATED_BY)
        nex_session.add(x)
        print("Adding phenotypeannotation_cond for allele: " + allele_name + ", chemical: " + condition_name + " into database.")
    except Exception as e:
        traceback.print_exc()
        print("An error occurred when inserting phenotypeannotation_cond for allele: " + allele_name + ", chemical: " + condition_name + " into the database. error=" + str(e))
        
    
def insert_phenotypeannotation(nex_session, dbentity_id, source_id, taxonomy_id, reference_id, phenotype_id, experiment_id, mutant_id, allele_id, strain_name, allele_name):

    print("phenotypeannotation:", dbentity_id, source_id, taxonomy_id, reference_id, phenotype_id, experiment_id, mutant_id, allele_id, strain_name, allele_name, CREATED_BY)
    
    try:
        x = Phenotypeannotation(dbentity_id = dbentity_id,
                                source_id = source_id,
                                taxonomy_id = taxonomy_id,
                                reference_id = reference_id,
                                phenotype_id = phenotype_id,
                                experiment_id = experiment_id,
                                mutant_id = mutant_id,
                                allele_id = allele_id,
                                strain_name = strain_name,
                                created_by = CREATED_BY)
        nex_session.add(x)
        nex_session.flush()
        nex_session.refresh(x)
        print("Adding phenotypeannotation for allele: " + allele_name + " into database.")
        return x.annotation_id
    except Exception as e:
        traceback.print_exc()
        print("An error occurred when inserting phenotypeannotation for allele: " + allele_name + " into the database. error=" + str(e))
        return None


def insert_alleledbentity(nex_session, dbentity_id, so_id, allele_name):

    print("alleledbentity:", dbentity_id, so_id, allele_name)
    
    try:
        x = Alleledbentity(dbentity_id = dbentity_id,
                           so_id = so_id)
        nex_session.add(x)
        print("Adding new allele: " + allele_name + " into ALLELEDBENTITY table. NEW allele_id = " + str(dbentity_id))
        return dbentity_id
    except Exception as e:
        print("An error occurred when inserting new allele " + allele_name + " into ALLELEDBENTITY table. error=" + str(e))
        return None

    
def insert_dbentity(nex_session, allele_name, source_id):

    print("dbentity:", allele_name, source_id, CREATED_BY)
    try:
        x = Dbentity(format_name = allele_name.replace(' ', '_'),
                     display_name = allele_name,
                     subclass = 'ALLELE',
                     source_id = source_id,
                     dbentity_status = 'Active',
                     created_by = CREATED_BY)
        nex_session.add(x)
        nex_session.flush()
        nex_session.refresh(x)
        print("Adding new allele: " + allele_name + " into DBENTITY table. NEW allele_id = " + str(x.dbentity_id))
        return x.dbentity_id
    except Exception as e:
        traceback.print_exc()
        print("An error occurred when inserting new allele " + allele_name + " into DBENTITY. error=" + str(e))
        return None


if __name__ == '__main__':
    
    load_phenotypes()



