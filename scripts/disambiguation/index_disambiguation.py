from src.models import DBSession, Base, Colleague, ColleagueLocus, Locusdbentity, LocusAlias, Dnasequenceannotation, \
    So, Locussummary, Phenotypeannotation, PhenotypeannotationCond, Phenotype, Goannotation, Go, Goslimannotation, \
    Goslim, Apo, Straindbentity, Strainsummary, Reservedname, GoAlias, Goannotation, Referencedbentity, Referencedocument, \
    Referenceauthor, ReferenceAlias, Chebi, Proteindomain, Contig, Dataset, Keyword, Ec, Disease, Alleledbentity, \
    AlleleAlias, Complexdbentity, ComplexAlias

from sqlalchemy import create_engine, and_
import os
import redis

engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
DBSession.configure(bind=engine)
Base.metadata.bind = engine

# disambiguation = redis.Redis()
disambiguation = redis.Redis(os.environ['REDIS_WRITE_HOST'], os.environ['REDIS_PORT'])

ignoring = []

def table_set(key, value, prefix):
    key = str("/" + prefix + "/" + str(key)).upper()

    disambiguation.set(key, value)

def load_locus():
    print("Loading genes into Redis...")

    genes = DBSession.query(Locusdbentity).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    gene_data = [(gene.dbentity_id, gene.sgdid, gene.systematic_name, gene.display_name) for gene in genes]

    aliases = DBSession.query(LocusAlias.locus_id, LocusAlias.display_name).filter(LocusAlias.alias_type.in_(['Uniform', 'Non-uniform'])).all()
    ids_to_aliases = {}
    for alias in aliases:
        if alias.locus_id in ids_to_aliases:
            ids_to_aliases[alias.locus_id].append(alias.display_name)
        else:
            ids_to_aliases[alias.locus_id] = [alias.display_name]
    DBSession.rollback()

    # in case of collisions, the table_set will overwrite the value
    # indexing each name separately assures priority

    for dbentity_id, sgdid, systematic_name, display_name in gene_data:
        for alias in ids_to_aliases.get(dbentity_id, []):
            table_set(str(alias).upper(), dbentity_id, "locus")

    for dbentity_id, sgdid, systematic_name, display_name in gene_data:
        table_set(str(sgdid.upper()), dbentity_id, "locus")

    for dbentity_id, sgdid, systematic_name, display_name in gene_data:
        table_set(str(systematic_name.upper()), dbentity_id, "locus")

    for dbentity_id, sgdid, systematic_name, display_name in gene_data:
        table_set(str(display_name.upper()), dbentity_id, "locus")

    for dbentity_id, sgdid, systematic_name, display_name in gene_data:
        table_set(str(dbentity_id), dbentity_id, "locus")

def load_alleles():

    print("Loading alleles into Redis...")

    alleles = DBSession.query(Alleledbentity).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    allele_data = [(allele.dbentity_id, allele.sgdid, allele.display_name) for allele in alleles]

    aliases = DBSession.query(AlleleAlias.allele_id, AlleleAlias.display_name).all()
    ids_to_aliases = {}
    for alias in aliases:
        if alias.allele_id in ids_to_aliases:
            ids_to_aliases[alias.allele_id].append(alias.display_name)
        else:
            ids_to_aliases[alias.allele_id] = [alias.display_name]
    DBSession.rollback()

    for dbentity_id, sgdid, display_name in allele_data:
        for alias in ids_to_aliases.get(dbentity_id, []):
            table_set(str(alias).upper(), dbentity_id, "allele")

    for dbentity_id, sgdid, display_name in allele_data:
        table_set(str(sgdid.upper()), dbentity_id, "allele")
        table_set(str(display_name.upper()), dbentity_id, "allele")
        table_set(str(dbentity_id), dbentity_id, "allele")

def load_complexes():

    print("Loading complexes into Redis...")

    complexes = DBSession.query(Complexdbentity).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    complex_data = [(c.dbentity_id, c.sgdid, c.systematic_name, c.display_name, c.intact_id, c.complex_accession) for c in complexes]

    aliases = DBSession.query(ComplexAlias.complex_id, ComplexAlias.display_name).filter_by(alias_type='Synonym').all()
    ids_to_aliases = {}
    for alias in aliases:
        if alias.complex_id in ids_to_aliases:
            ids_to_aliases[alias.complex_id].append(alias.display_name)
        else:
            ids_to_aliases[alias.complex_id] = [alias.display_name]
    DBSession.rollback()

    for dbentity_id, sgdid, systematic_name, display_name, intact_id, complex_accession in complex_data:
        for alias in ids_to_aliases.get(dbentity_id, []):
            table_set(str(alias).upper(), dbentity_id, "complex")

    for dbentity_id, sgdid, systematic_name, display_name, intact_id, complex_accession in complex_data:
        table_set(str(sgdid.upper()), dbentity_id, "complex")
        table_set(str(systematic_name.upper()), dbentity_id, "complex")
        table_set(str(display_name.upper()), dbentity_id, "complex")
        table_set(str(intact_id.upper()), dbentity_id, "complex")
        table_set(str(complex_accession.upper()), dbentity_id, "complex")
        table_set(str(dbentity_id), dbentity_id, "complex")
    

def load_reserved_names():
    print("Loading reserve names into Redis...")

    reserved_names = DBSession.query(Reservedname).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    name_data = [(name.reservedname_id, name.format_name) for name in reserved_names]
    DBSession.rollback()

    for reservedname_id, format_name in name_data:
        table_set(str(reservedname_id), reservedname_id, "reservedname")
        table_set(str(format_name).upper(), reservedname_id, "reservedname")

def load_references():
    print("Loading references into Redis...")

    references = DBSession.query(Referencedbentity).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    ref_data = [(ref.dbentity_id, ref.sgdid, ref.pmid) for ref in references]
    DBSession.rollback()

    for dbentity_id, sgdid, pmid in ref_data:
        table_set(dbentity_id, dbentity_id, "reference")
        table_set(sgdid, dbentity_id, "reference")
        table_set(pmid, dbentity_id, "reference")

def load_author():
    print("Loading authors into Redis...")

    authors = DBSession.query(Referenceauthor).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    author_data = [(author.obj_url, author.referenceauthor_id) for author in authors]
    DBSession.rollback()

    ignoring = []

    for obj_url, referenceauthor_id in author_data:
        format_name = obj_url.encode().strip().decode().split("/")[2]

        try:
            table_set(format_name.upper(), format_name, "author")
            table_set(str(referenceauthor_id), format_name, "author")
        except UnicodeEncodeError:
            ignoring.append(format_name)

    print("Ignoring for special characters: " + ",".join(ignoring))

def load_chemical():
    print("Loading chemicals into Redis...")

    chemicals = DBSession.query(Chebi).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    chemical_data = [(chemical.chebi_id, chemical.display_name, chemical.format_name) for chemical in chemicals]
    DBSession.rollback()

    ignoring = []

    for chebi_id, display_name, format_name in chemical_data:
        try:
            table_set(str(display_name.encode().strip().decode().replace(" ", "_")).upper(), chebi_id, "chebi")
            table_set(format_name.encode().strip().decode().upper(), chebi_id, "chebi")
            table_set(chebi_id, chebi_id, "chebi")
        except UnicodeEncodeError:
            ignoring.append(display_name)

    print("Ignoring for special characters: " + ",".join(ignoring))

def load_phenotype():
    print("Loading phenotypes into Redis...")

    phenotypes = DBSession.query(Phenotype).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    phenotype_data = [(p.phenotype_id, p.format_name) for p in phenotypes]
    DBSession.rollback()

    for phenotype_id, format_name in phenotype_data:
        table_set(format_name.upper(), phenotype_id, "phenotype")
        table_set(phenotype_id, phenotype_id, "phenotype")

def load_observables():
    print("Loading observables into Redis...")

    apos = DBSession.query(Apo).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    apo_data = [(a.apo_id, a.format_name, a.display_name) for a in apos]
    DBSession.rollback()

    for apo_id, format_name, display_name in apo_data:
        table_set(apo_id, apo_id, "apo")
        table_set(format_name.upper(), apo_id, "apo")
        table_set(display_name.replace(" ", "_").upper(), apo_id, "apo")

def load_go():
    print("Loading go into Redis...")

    gos = DBSession.query(Go).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    go_data = [(g.go_id, g.goid, g.format_name, g.display_name) for g in gos]
    DBSession.rollback()

    for go_id, goid, format_name, display_name in go_data:
        numerical_id = goid.split(":")

        table_set(format_name.upper(), go_id, "go")
        table_set(go_id, go_id, "go")
        table_set(display_name.replace(" ", "_").upper(), go_id, "go")
        table_set(str(int(numerical_id[1])), go_id, "go")


def load_disease():
    print("Loading disease into Redis...")

    diseases = DBSession.query(Disease).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    disease_data = [(d.doid, d.format_name, d.display_name) for d in diseases]
    DBSession.rollback()

    for doid, format_name, display_name in disease_data:
        if doid == 'derives_from':
            continue
        numerical_id = doid.split(":")
        table_set(format_name.upper(), doid, "disease")
        table_set(doid, doid, "disease")
        table_set(display_name.replace(" ", "_").upper(), doid, "disease")
        table_set(str(int(numerical_id[1])), doid, "disease")

def load_protein_domain():
    print("Loading protein domains into Redis...")

    pds = DBSession.query(Proteindomain).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    pd_data = [(pd.proteindomain_id, pd.format_name) for pd in pds]
    DBSession.rollback()

    for proteindomain_id, format_name in pd_data:
        table_set(proteindomain_id, proteindomain_id, "proteindomain")
        table_set(format_name.upper(), proteindomain_id, "proteindomain")

def load_contigs():
    print("Loading contigs into Redis...")

    contigs = DBSession.query(Contig).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    contig_data = [(c.contig_id, c.format_name) for c in contigs]
    DBSession.rollback()

    for contig_id, format_name in contig_data:
        table_set(format_name.upper(), contig_id, "contig")
        table_set(contig_id, contig_id, "contig")

def load_dataset():
    print("Loading datasets into Redis...")

    datasets = DBSession.query(Dataset).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    dataset_data = [(d.dataset_id, d.format_name) for d in datasets]
    DBSession.rollback()

    for dataset_id, format_name in dataset_data:
        table_set(format_name.upper(), dataset_id, "dataset")
        table_set(dataset_id, dataset_id, "dataset")

def load_keyword():
    print("Loading Keywords into Redis...")

    keywords = DBSession.query(Keyword).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    keyword_data = [(k.keyword_id, k.format_name) for k in keywords]
    DBSession.rollback()

    for keyword_id, format_name in keyword_data:
        table_set(keyword_id, keyword_id, "keyword")
        table_set(format_name.upper(), keyword_id, "keyword")

def load_strains():
    print("Loading strains into Redis...")

    strains = DBSession.query(Straindbentity).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    strain_data = [(s.dbentity_id, s.sgdid, s.display_name) for s in strains]
    DBSession.rollback()

    for dbentity_id, sgdid, display_name in strain_data:
        table_set(dbentity_id, dbentity_id, "strain")
        table_set(sgdid, dbentity_id, "strain")
        table_set(display_name.replace(" ", "_"), dbentity_id, "strain")

def load_ec_numbers():
    print("Loading ec numbers into Redis...")

    ecnumbers = DBSession.query(Ec).all()
    # Extract data before closing session to avoid idle-in-transaction timeout
    ec_data = [(e.ec_id, e.display_name, e.format_name) for e in ecnumbers]
    DBSession.rollback()

    for ec_id, display_name, format_name in ec_data:
        table_set(display_name.replace("EC:", ""), ec_id, "ec")
        table_set(format_name, ec_id, "ec")
        table_set(ec_id, ec_id, "ec")

if __name__ == "__main__":
    load_references()
    DBSession.rollback()
    load_locus()
    DBSession.rollback()
    load_alleles()
    DBSession.rollback()
    load_complexes()
    DBSession.rollback()
    load_reserved_names()
    DBSession.rollback()
    load_author()
    DBSession.rollback()
    load_chemical()
    DBSession.rollback()
    load_phenotype()
    DBSession.rollback()
    load_observables()
    DBSession.rollback()
    load_go()
    DBSession.rollback()
    load_disease()
    DBSession.rollback()
    load_protein_domain()
    DBSession.rollback()
    load_contigs()
    DBSession.rollback()
    load_dataset()
    DBSession.rollback()
    load_keyword()
    DBSession.rollback()
    load_strains()
    DBSession.rollback()
    load_ec_numbers()
    DBSession.rollback()
