import os
import traceback
from src.models import Apo, Dbentity, Locusdbentity, Referencedbentity, Phenotypeannotation, \
    PhenotypeannotationCond, Taxonomy, Chebi, Phenotype, Source, Straindbentity, LocusAlias, \
    AlleleAlias, So, Alleledbentity, AlleleReference, LocusAllele, LocusalleleReference
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

infile = "scripts/loading/phenotype/data/HTPphenos4Shuai2loadPMID34663920.tsv"
logfile = "scripts/loading/phenotype/logs/HTPphenos4Shuai2loadPMID34663920.log"
pmid = 34663920
strain_background = "S288C"
strain_name = "BY4742"
experiment_type = "systematic mutation set"
mutant_type = "reduction of function"
allele_type = "gene variant"
CREATED_BY = os.environ['DEFAULT_USER']

batch_commit_size = 250


def load_phenotypes():
 
    nex_session = get_session()

    print("CREATED_BY=", CREATED_BY)
    
    allele_to_id = dict([(x.format_name.lower(), x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(
        subclass='ALLELE').all()])

    alias_name_to_allele_id = dict([(x.display_name.lower(), x.allele_id) for x in nex_session.query(AlleleAlias).all()])
    
    name_to_locus_id = {}
    for x in nex_session.query(Locusdbentity).all():
        name_to_locus_id[x.systematic_name.lower()] = x.dbentity_id
        if x.gene_name:
            name_to_locus_id[x.gene_name.lower()] = x.dbentity_id

    alias_name_to_locud_id = dict([(x.display_name.lower(), x.locus_id) for x in nex_session.query(LocusAlias).filter_by(
        alias_type='Uniform').all()])

    phenotype_to_phenotype_id = dict([(x.display_name.lower(), x.phenotype_id) for x in nex_session.query(Phenotype).all()])
    
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

    so = nex_session.query(So).filter_by(display_name=allele_type).one_or_none()
    so_id = so.so_id

    print("so_id=", so_id)
    
    f = open(infile)
    fw = open(logfile, "w")

    i = 0
    chemicals = []
    key_to_annotation_id = {}
    for line in f:
        if line.startswith("Systematic_name"):
            continue
        i += 1
        if i % batch_commit_size == 0:
            # nex_session.rollback()
            nex_session.commit()
        pieces = line.strip().split("\t")
        gene_name = pieces[0]
        dbentity_id = name_to_locus_id.get(gene_name.lower())
        if dbentity_id is None:
            dbentity_id = alias_name_to_locud_id.get(gene_name.lower())
            if dbentity_id:
                print("GENE:", gene_name, "is an alias name.")
            else:
                print("GENE:", gene_name, "is not in the database.")
                continue
        phenotype = pieces[4]
        if pieces[5]:
            phenotype = phenotype + ": " + pieces[5]
        phenotype_id = phenotype_to_phenotype_id.get(phenotype.lower())
        if phenotype_id is None:
            print("PHENOTYPE:", phenotype, "is not in the database.")
            continue
        allele_name = pieces[8]
        allele_id = allele_to_id.get(allele_name.lower())
        if allele_id is None:
            allele_id = alias_name_to_allele_id.get(allele_name.lower())
            if allele_id:
                allele_to_id[allele_name.lower()] = allele_id
                print("ALLELE:", allele_name, "is an alias name.")
            else:
                print("ALLELE:", allele_name, "is not in the database.")
                ## insert new allele into database
                allele_id = insert_allele(nex_session, allele_name, source_id, so_id)
                if allele_id is None:
                    print("ALLELE:", allele_name, "is not added into the database.")
                    continue
                nex_session.commit()
                allele_to_id[allele_name.lower()] = allele_id
                status = insert_allele_reference(nex_session, source_id, allele_id, reference_id, allele_name)
                if status:
                    nex_session.rollback()
                    continue
                locus_allele_id = insert_locus_allele(nex_session, source_id, dbentity_id,
                                                      allele_id, allele_name, gene_name)
                if locus_allele_id is None:
                    nex_session.rollback()
                    continue
                status = insert_locusallele_reference(nex_session, source_id, locus_allele_id,
                                                      reference_id, allele_name)
                if status:
                    nex_session.rollback()
                    continue

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
            nex_session.commit()
            key_to_annotation_id[key] = annotation_id

        chebiID = pieces[9]
        chebi = nex_session.query(Chebi).filter_by(format_name=chebiID).one_or_none()
        chemical_name = chebi.display_name
        chemical_value = None
        chemical_unit = None
        if len(pieces) > 10:
            chemical_value = pieces[10]
            if len(pieces) > 11:
                chemical_unit = pieces[11]
        group_id = 1
        insert_phenotypeannotation_cond(nex_session, annotation_id, group_id, chemical_name,
                                        chemical_value, chemical_unit, allele_name)

    f.close()
    fw.close()
    nex_session.commit()
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


def insert_locus_allele(nex_session, source_id, locus_id, allele_id, allele_name, gene_name):

    print("locus_allele:", source_id, locus_id, allele_id, allele_name, gene_name, CREATED_BY)
    try:
        x = LocusAllele(source_id = source_id,
                        locus_id = locus_id,
                        allele_id = allele_id,
                        created_by = CREATED_BY)
        nex_session.add(x)
        nex_session.flush()
        nex_session.refresh(x)
        print("Adding locus_allele for allele: " + allele_name + ", gene_name: " + gene_name + " into database.")
        return x.locus_allele_id
    except Exception as e:
        traceback.print_exc()
        print("An error occurred when inserting locus_allele for allele: " + allele_name + ", gene_name: " + gene_name + " into the database. error=" + str(e))
        return None

    
def insert_allele_reference(nex_session, source_id, allele_id, reference_id, allele_name):

    print("allele_reference:", source_id, allele_id, reference_id, allele_name, CREATED_BY)

    try:
        x = AlleleReference(source_id = source_id,
                            allele_id = allele_id,
                            reference_id = reference_id,
                            created_by = CREATED_BY)
        nex_session.add(x)
        print("Adding allele_reference for allele: " + allele_name + ", reference_id " + str(reference_id) + " into database.")
        return 0
    except Exception as e:
        traceback.print_exc()
        print("An error occurred when inserting allele_reference for allele: " + allele_name + ", reference_id " + str(reference_id) + " into the database. error=" + str(e))
        return 1


def insert_phenotypeannotation_cond(nex_session, annotation_id, group_id, condition_name, condition_value, condition_unit, allele_name):

    print("phenotypeannotation_cond:", annotation_id, group_id, condition_name, condition_value, condition_unit, allele_name, CREATED_BY)

    pc = nex_session.query(PhenotypeannotationCond).filter_by(
        annotation_id = annotation_id, group_id =  group_id, condition_class = 'chemical',
        condition_name = condition_name, condition_value = condition_value, condition_unit = condition_unit).one_or_none()
    if pc:
        return
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

    
def insert_allele(nex_session, allele_name, source_id, so_id):

    print("allele:", allele_name, source_id, so_id, CREATED_BY)
    try:
        x = Alleledbentity(format_name = allele_name.replace(' ', '_'),
                           display_name = allele_name,
                           subclass = 'ALLELE',
                           source_id = source_id,
                           dbentity_status = 'Active',
                           so_id = so_id,
                           created_by = CREATED_BY)
        nex_session.add(x)
        nex_session.flush()
        nex_session.refresh(x)
        print("Adding new allele: " + allele_name + " into database. NEW allele_id = " + str(x.dbentity_id))
        return x.dbentity_id
    except Exception as e:
        traceback.print_exc()
        print("An error occurred when inserting new allele " + allele_name + " into database. error=" + str(e))
        return None


if __name__ == '__main__':
    
    load_phenotypes()
