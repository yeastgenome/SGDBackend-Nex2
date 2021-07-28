from src.models import AlleleGeninteraction, Alleledbentity, Complexdbentity, CurationReference, Dnasequenceannotation, Functionalcomplementannotation, Literatureannotation, Locusdbentity, Pathwaydbentity, Proteinabundanceannotation, Referencedbentity
from . import fixtures as factory
from mock import Mock

class MockQueryFilter(object):
    def __init__(self, query_params, query_result):
        self._return = query_result
        self._params = query_params

    def one_or_none(self):
        if self._return.__class__ == list:
            return self._return[0]
        else:
            return self._return

    def first(self):
        return self._return

    def order_by(self, *args, **kwargs):
        return self

    def group_by(self, *args, **kwargs):
        return self

    def asc(self, *args, **kwargs):
        return self

    def all(self):
        if self._return is None:
            return []
        elif self._return.__class__ == list:
            return self._return
        else:
            return [self._return]

    def count(self):
        return 7

    def query_params(self):
        return self._params

    def distinct(self, *args, **kwargs):
        return self

    def outerjoin(self, *args, **kwargs):
        return self
    
    def scalar(self,*args,**kwargs):
        return 7
        
    def join(self, *args, **kwargs):
        return self
    
    def join(self, *args, **kwargs):
        return self
    
    def join(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self
    
    def filter(self, *args, **kwargs):
        return self
    

class MockQuery(object):
    def __init__(self, query_result):
        self._query_result = query_result

    def filter_by(self, **query_params):
        self._query_filter = MockQueryFilter(query_params, self._query_result)
        self._full_params = query_params
        return self._query_filter

    def filter(self, *query_params):
        self._query_filter = MockQueryFilter(query_params[0], self._query_result)
        self._full_params = query_params
        return self._query_filter

    def all(self):
        return self._query_result

    def distinct(self, *query_params):
        if len(query_params) == 0 and self._query_result:
            return self._query_result
        else:
            return self

    def outerjoin(self,query_params):
        return self
    
    def join(self,  *args, **kwargs):
        return self
    
    def join(self,  *args, **kwargs):
        return self

    def count(self):
        return 1
    def join(self,  *args, **kwargs):
        return self

    def order_by(self, query_params):
        return self

    def limit(self, query_params):
        return self
        
class MockFileStorage(object):
    pass


def go_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Go'>":
        go = factory.GoFactory()
        return MockQuery(go)
    if len(args) == 2 and str(args[0]) == 'Goannotation.dbentity_id' and str(args[1]) == 'count(nex.goannotation.dbentity_id)':
        go = factory.GoFactory()
        goannot = factory.GoannotationFactory()
        goannot.go = go
        return MockQuery(goannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.GoRelation'>":
        gochild = factory.GoFactory()
        goparent = factory.GoFactory()
        gorel = factory.GoRelationFactory()
        ro = factory.RoFactory()
        gorel.child = gochild
        gorel.parent = goparent
        gorel.ro = ro
        return MockQuery(gorel)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.GoUrl'>":
        gourl = factory.GoUrlFactory()
        return MockQuery(gourl)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.GoAlias'>":
        goalias = factory.GoAliasFactory()
        return MockQuery(goalias)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Locusdbentity'>":
        locus = factory.LocusdbentityFactory()
        return MockQuery(locus)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Goannotation'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        dbent = factory.DbentityFactory()
        go = factory.GoFactory()
        goannot = factory.GoannotationFactory()
        goannot.go = go
        goannot.dbentity = dbent
        goannot.reference = refdbentity
        goannot.source = source
        return MockQuery(goannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.EcoAlias'>":
        ecoalias = factory.EcoAliasFactory()
        return MockQuery(ecoalias)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.EcoUrl'>":
        ecourl = factory.EcoUrlFactory()
        return MockQuery(ecourl)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Goextension'>":
        ro = factory.RoFactory()
        goext = factory.GoextensionFactory()
        goext.ro = ro
        return MockQuery(goext)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Dbentity'>":
        dbent = factory.DbentityFactory()
        return MockQuery(dbent)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Chebi'>":
        chebi = factory.ChebiFactory()
        return MockQuery(chebi)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Gosupportingevidence'>":
        goevd = factory.GosupportingevidenceFactory()
        return MockQuery(goevd)

def locus_expression_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Locusdbentity'>":
        locus = factory.LocusdbentityFactory()
        return MockQuery(locus)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Expressionannotation'>":
        expannot = factory.ExpressionannotationFactory()
        return MockQuery(expannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Dataset'>":
        dataset = factory.DatasetFactory()
        return MockQuery(dataset)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Referencedbentity'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        return MockQuery(refdbentity)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.DatasetKeyword'>":
        dskw = factory.DatasetKeywordFactory()
        return MockQuery(dskw)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.DatasetReference'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        dsref = factory.DatasetReferenceFactory()
        dsref.reference = refdbentity
        ds = factory.DatasetFactory()
        dsref.dataset = ds
        return MockQuery((dsref,))
    elif len(args) == 1 and str(args[0]) == 'Referencedocument.html':
        refdoc = factory.ReferencedocumentFactory()
        return MockQuery(refdoc.html)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Datasetsample'>":
        dss = factory.DatasetsampleFactory()
        return MockQuery(dss)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.DatasetUrl'>":
        dsurl = factory.DatasetUrlFactory()
        return MockQuery(dsurl)

def complex_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Complexdbentity'>":
        complex = factory.ComplexdbentityFactory()
        return MockQuery(complex)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Complexbindingannotation'>":
        bind = factory.ComplexbindingannotationFactory()
        interactor = factory.InteractorFactory()
        locus =factory.LocusdbentityFactory()
        interactor.locus = locus
        bind.interactor = interactor
        bindingInteractor = factory.InteractorFactory()
        locus2 =factory.LocusdbentityFactory()
        bindingInteractor.locus = locus2
        bind.binding_interactor = bindingInteractor
        return MockQuery(bind)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ComplexAlias'>":
        alias = factory.ComplexAliasFactory()
        return MockQuery(alias)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ComplexGo'>":
        complexGo = factory.ComplexGoFactory()
        go = factory.GoFactory()
        complexGo.go = go
        return MockQuery(complexGo)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ComplexReference'>":
        complexRef = factory.ComplexReferenceFactory()
        ref = factory.ReferencedbentityFactory()
        complexRef.reference = ref
        return MockQuery(complexRef)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ReferenceUrl'>":
        refUrl = factory.ReferenceUrlFactory()
        return MockQuery(refUrl)
    elif len(args) == 2 and str(args[0]) == 'Goannotation.dbentity_id' and str(args[1]) == 'count(nex.goannotation.dbentity_id)':
        goAnnot = factory.GoannotationFactory()
        return MockQuery(goAnnot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.GoRelation'>":
        goRel = factory.GoRelationFactory()
        return MockQuery(goRel)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.GoUrl'>":
        goUrl = factory.GoUrlFactory()
        return MockQuery(goUrl)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.GoAlias'>":
        goAlias = factory.GoAliasFactory()
        return MockQuery(goAlias)

def locus_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Locusdbentity'>":
        locus = factory.LocusdbentityFactory()
        return MockQuery(locus)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Proteinabundanceannotation'>":
        protein_abundance_annotation = factory.ProteinabundanceAnnotationFactory()
        eco = factory.EcoFactory()
        protein_abundance_annotation.eco = eco
        efo = factory.EfoFactory()
        protein_abundance_annotation.efo = efo
        db_entity = factory.DbentityFactory()
        protein_abundance_annotation.dbentity = db_entity
        ref = factory.ReferencedbentityFactory()
        protein_abundance_annotation.reference = ref
        orig_ref = factory.ReferencedbentityFactory()
        protein_abundance_annotation.original_reference = orig_ref
        chebi = factory.ChebiFactory()
        protein_abundance_annotation.chebi = chebi
        go = factory.GoFactory()
        protein_abundance_annotation.go = go
        src = factory.SourceFactory()
        protein_abundance_annotation.src = src
        tax = factory.TaxonomyFactory()
        protein_abundance_annotation.tax = tax
        return MockQuery(protein_abundance_annotation)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Bindingmotifannotation'>":
        bind = factory.BindingmotifannotationFactory()
        return MockQuery(bind)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Complexbindingannotation'>":
        bind = factory.ComplexbindingannotationFactory()
        return MockQuery(bind)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Go'>":
        go = factory.GoFactory()
        return MockQuery(go)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Phenotypeannotation'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        mut = factory.ApoFactory()
        exp = factory.ApoFactory()
        pheno = factory.PhenotypeFactory()
        db = factory.DbentityFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.mutant = mut
        phenoannot.experiment = exp
        phenoannot.phenotype = pheno
        phenoannot.dbentity = db
        phenoannot.reference = refdbentity
        return MockQuery(phenoannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Straindbentity'>":
        s_name = factory.StraindbentityFactory()
        return MockQuery(s_name)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Apo'>":
        apo = factory.ApoFactory()
        return MockQuery(apo)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Interactor'>":
        interactor = factory.InteractorFactory()
        return MockQuery(interactor)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.PhenotypeannotationCond'>":
        phenocond = factory.PhenotypeannotationCondFactory()
        return MockQuery(phenocond)
    elif len(args) == 2 and str(args[0]) == 'Chebi.display_name' and str(args[1]) == 'Chebi.obj_url':
        chebi = factory.ChebiFactory()
        return MockQuery((chebi.display_name, chebi.obj_url))
    elif len(args) == 2 and str(args[0]) == 'Dbentity.display_name' and str(args[1]) == 'Dbentity.format_name':
        db = factory.DbentityFactory()
        return MockQuery(db.format_name)
    elif len(args) == 1 and str(args[0]) == 'Proteinsequenceannotation.annotation_id':
        prtseq = factory.ProteinsequenceannotationFactory()
        return MockQuery((prtseq.annotation_id,))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Proteinsequenceannotation'>":
        prtseq = factory.ProteinsequenceannotationFactory()
        return MockQuery(prtseq)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ProteinsequenceDetail'>":
        prtseq = factory.ProteinsequenceannotationFactory()
        prtseqdetail = factory.ProteinsequenceDetailFactory()
        prtseqdetail.annotation = prtseq
        return MockQuery(prtseqdetail)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Goslimannotation'>":
        goslimannot = factory.GoslimannotationFactory()
        goslim = factory.GoslimFactory()
        goslimannot.goslim = goslim
        return MockQuery(goslimannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Goannotation'>":
        go = factory.GoFactory()
        goannot = factory.GoannotationFactory()
        goannot.go = go
        return MockQuery(goannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Disease'>":
        do = factory.DiseaseFactory()
        return MockQuery(do)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Diseaseannotation'>":
        do = factory.DiseaseFactory()
        doannot = factory.DiseaseannotationFactory()
        doannot.do = do
        dbentity = factory.DbentityFactory()
        doannot.dbentity = dbentity
        eco = factory.EcoFactory()
        doannot.eco = eco
        ref = factory.ReferencedbentityFactory()
        doannot.reference = ref
        src = factory.SourceFactory()
        doannot.source = src
        taxonomy = factory.TaxonomyFactory()
        doannot.taxonomy = taxonomy
        return MockQuery(doannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.EcoAlias'>":
        ecoalias = factory.EcoAliasFactory()
        return MockQuery(ecoalias)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.EcoUrl'>":
        ecourl = factory.EcoUrlFactory()
        return MockQuery(ecourl)
    elif len(args) == 1 and str(args[0]) == 'Locussummary.html':
        ls = factory.LocussummaryFactory()
        return MockQuery(ls.html)
    elif len(args) == 2 and str(args[0]) == 'Phenotypeannotation.taxonomy_id' and str(
            args[1]) == 'count(nex.phenotypeannotation.taxonomy_id)':
        pheno = factory.PhenotypeFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.phenotype = pheno
        return MockQuery((phenoannot.taxonomy_id, 20))
    elif len(args) == 2 and str(args[0]) == 'Phenotypeannotation.taxonomy_id' and str(
            args[1]) == 'Phenotypeannotation.annotation_id':
        pheno = factory.PhenotypeFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.phenotype = pheno
        return MockQuery(phenoannot)
    elif len(args) == 2 and str(args[0]) == 'PhenotypeannotationCond.annotation_id' and str(args[1]) == 'count(DISTINCT nex.phenotypeannotation_cond.group_id)':
        phenocond = factory.PhenotypeannotationCondFactory()
        return MockQuery((phenocond.annotation_id, 20))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Straindbentity'>":
        s_name = factory.StraindbentityFactory()
        return MockQuery(s_name)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Phenotypeannotation'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        mut = factory.ApoFactory()
        exp = factory.ApoFactory()
        pheno = factory.PhenotypeFactory()
        db = factory.DbentityFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.mutant = mut
        phenoannot.experiment = exp
        phenoannot.phenotype = pheno
        phenoannot.dbentity = db
        phenoannot.reference = refdbentity
        return MockQuery(phenoannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.PhenotypeannotationCond'>":
        phenocond = factory.PhenotypeannotationCondFactory()
        return MockQuery(phenocond)
    elif len(args) == 2 and str(args[0]) == 'Chebi.display_name' and str(args[1]) == 'Chebi.obj_url':
        chebi = factory.ChebiFactory()
        return MockQuery((chebi.display_name, chebi.obj_url))
    elif len(args) == 2 and str(args[0]) == 'Goannotation.dbentity_id' and str(args[1]) == 'count(nex.goannotation.dbentity_id)':
        goannot = factory.GoannotationFactory()
        return MockQuery(goannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Apo'>":
        apo = factory.ApoFactory()
        return MockQuery(apo)
    elif len(args) == 2 and str(args[0]) == 'Physinteractionannotation.biogrid_experimental_system' and str(args[1]) == 'count(nex.physinteractionannotation.annotation_id)':
        physannot = factory.PhysinteractionannotationFactory()
        return MockQuery((physannot.biogrid_experimental_system, 20))
    elif len(args) == 2 and str(args[0]) == 'Geninteractionannotation.biogrid_experimental_system' and str(args[1]) == 'count(nex.geninteractionannotation.annotation_id)':
        genannot = factory.GeninteractionannotationFactory()
        return MockQuery((genannot.biogrid_experimental_system, 20))
    elif len(args) == 1 and str(args[0]) == 'Physinteractionannotation.dbentity2_id':
        physannot = factory.PhysinteractionannotationFactory()
        return MockQuery(physannot.dbentity2_id)
    elif len(args) == 1 and str(args[0]) == 'Physinteractionannotation.dbentity1_id':
        physannot = factory.PhysinteractionannotationFactory()
        return MockQuery(physannot.dbentity1_id)
    elif len(args) == 1 and str(args[0]) == 'Geninteractionannotation.dbentity2_id':
        genannot = factory.GeninteractionannotationFactory()
        return MockQuery(genannot.dbentity2_id)
    elif len(args) == 1 and str(args[0]) == 'Geninteractionannotation.dbentity1_id':
        genannot = factory.GeninteractionannotationFactory()
        return MockQuery(genannot.dbentity1_id)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Regulationannotation'>":
        regannot = factory.RegulationannotationFactory()
        eco = factory.EcoFactory()
        go = factory.GoFactory()
        reference = factory.ReferencedbentityFactory()
        regulator = factory.DbentityFactory()
        source = factory.SourceFactory()
        target = factory.DbentityFactory()
        taxonomy = factory.TaxonomyFactory()
        regannot.eco = eco
        regannot.go = go
        regannot.reference = reference
        regannot.regulator = regulator
        regannot.source = source
        regannot.target = target
        regannot.taxonomy = taxonomy
        return MockQuery(regannot)
    elif len(args) == 2 and str(args[0]) == 'Regulationannotation.target_id' and str(args[1]) == 'Regulationannotation.regulator_id':
        regannot = factory.RegulationannotationFactory()
        return MockQuery((regannot.target_id, regannot.regulator_id))
    elif len(args) == 2 and str(args[0]) == 'Literatureannotation.topic' and str(args[1]) == 'count(nex.literatureannotation.annotation_id)':
        litannot = factory.LiteratureannotationFactory()
        return MockQuery((litannot.topic, 20))
    elif len(args) == 1 and str(args[0]) == 'Literatureannotation.reference_id':
        litannot = factory.LiteratureannotationFactory()
        return MockQuery(litannot.reference_id)
    elif len(args) == 1 and str(args[0]) == 'Geninteractionannotation.reference_id':
        genannot = factory.GeninteractionannotationFactory()
        return MockQuery(genannot.reference_id)
    elif len(args) == 1 and str(args[0]) == 'Physinteractionannotation.reference_id':
        physannot = factory.PhysinteractionannotationFactory()
        return MockQuery(physannot.reference_id)
    elif len(args) == 1 and str(args[0]) == 'Regulationannotation.reference_id':
        regannot = factory.RegulationannotationFactory()
        return MockQuery(regannot.reference_id)
    elif len(args) == 1 and str(args[0]) == 'Regulationannotation.target_id':
        regannot = factory.RegulationannotationFactory()
        return MockQuery(regannot.target_id)
    elif len(args) == 1 and str(args[0]) == 'Literatureannotation.reference_id':
        litannot = factory.LiteratureannotationFactory()
        return MockQuery(litannot.reference_id)
    elif len(args) == 1 and str(args[0]) == 'Phenotypeannotation.reference_id':
        phenannot = factory.PhenotypeannotationFactory()
        return MockQuery(phenannot.reference_id)
    elif len(args) == 1 and str(args[0]) == 'Goannotation.reference_id':
        goannot = factory.GoannotationFactory()
        return MockQuery(goannot.reference_id)
    elif len(args) == 1 and str(args[0]) == 'ReferenceAlias.reference_id':
        refalias = factory.ReferenceAliasFactory()
        return MockQuery(refalias.reference_id)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.LocusAlias'>":
        localias = factory.LocusAliasFactory()
        source = factory.SourceFactory()
        localias.source = source
        return MockQuery(localias)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.LocusAliasReferences'>":
        localiasref = factory.LocusAliasReferencesFactory()
        source = factory.SourceFactory()
        ref = factory.ReferencedbentityFactory()
        localiasref.reference = ref
        localiasref.source = source
        return MockQuery(localiasref)
    elif len(args) == 1 and str(args[0]) == 'Apo.apo_id':
        apo = factory.ApoFactory()
        return MockQuery(apo.apo_id)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ReferenceUrl'>":
        refurl = factory.ReferenceUrlFactory()
        return MockQuery(refurl)
    elif len(args) == 1 and str(args[0]) == 'Dnasequenceannotation.so_id':
        dnaseq = factory.DnasequenceannotationFactory()
        return MockQuery((dnaseq.so_id,))
    elif len(args) == 1 and str(args[0]) == 'So.display_name':
        so = factory.SoFactory()
        return MockQuery(so.display_name)
    elif len(args) == 3 and str(args[0]) == 'Locussummary.summary_id' and str(args[1]) == 'Locussummary.html' and str(args[2]) == 'Locussummary.date_created':
        ls = factory.LocussummaryFactory()
        return MockQuery((ls.summary_id, ls.html, ls.date_created))
    elif len(args) == 5 and str(args[0]) == 'Locussummary.summary_id' \
        and str(args[1]) == 'Locussummary.html' and str(args[2]) == 'Locussummary.date_created' \
        and str(args[3]) == 'Locussummary.summary_order' and str(args[4]) == 'Locussummary.summary_type':
        ls = factory.LocussummaryFactory()
        return MockQuery((ls.summary_id, ls.html, ls.date_created, ls.summary_order, ls.summary_type))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.LocusReferences'>":
        lref = factory.LocusReferencesFactory()
        ref = factory.ReferencedbentityFactory()
        lref.reference = ref
        return MockQuery(lref)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.LocusRelation'>":
        lrel = factory.LocusRelationFactory()
        parent = factory.LocusdbentityFactory()
        child = factory.LocusdbentityFactory()
        source = factory.SourceFactory()
        ro = factory.RoFactory()
        lrel.parent = parent
        lrel.child = child
        lrel.source = source
        lrel.ro = ro
        return MockQuery(lrel)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.LocusRelationReference'>":
        lrel_ref = factory.LocusRelationReferenceFactory()
        ref = factory.ReferencedbentityFactory()
        lrel_ref.reference = ref
        return MockQuery(lrel_ref)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.LocussummaryReference'>":
        lsref = factory.LocussummaryReferenceFactory()
        ref = factory.ReferencedbentityFactory()
        source = factory.SourceFactory()
        summary = factory.LocussummaryFactory()
        lsref.source = source
        lsref.reference = ref
        lsref.summary = summary
        return MockQuery(lsref)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Locusnote'>":
        lnote = factory.LocusnoteFactory()
        source = factory.SourceFactory()
        lnote.source = source
        return MockQuery(lnote)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.LocusnoteReference'>":
        lnote_ref = factory.LocusnoteFactory()
        note = factory.LocusnoteFactory()
        ref = factory.ReferencedbentityFactory()
        source = factory.SourceFactory()
        lnote_ref.note = note
        lnote_ref.reference = ref
        lnote_ref.source = source
        return MockQuery(lnote_ref)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.LocusUrl'>":
        lurl = factory.LocusUrlFactory()
        return MockQuery(lurl)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Locusnoteannotation'>":
        laf = factory.LocusnoteannotationFactory()
        return MockQuery(laf)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Pathwayannotation'>":
        paf = factory.PathwayannotationFactory()
        dbentity = factory.DbentityFactory()
        ec = factory.EcFactory()
        pathway = factory.PathwaydbentityFactory()
        ref = factory.ReferencedbentityFactory()
        src = factory.SourceFactory()
        tax = factory.TaxonomyFactory()
        paf.dbentity = dbentity
        paf.ec = ec
        paf.pathway = pathway
        paf.reference = ref
        paf.source = src
        paf.taxonomy = tax
        return MockQuery(paf)
    elif len(args) == 1 and str(args[0]) == 'PathwayUrl.obj_url':
        path_url = factory.PathwayUrlFactory()
        return MockQuery(path_url.obj_url)
    elif len(args) == 1 and str(args[0]) == 'Dbentity.display_name':
        dbentity = factory.DbentityFactory()
        return MockQuery(dbentity.display_name)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Reservedname'>":
        rname = factory.ReservednameFactory()
        return MockQuery(rname)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Posttranslationannotation'>":
        pta = factory.PosttranslationannotationFactory()
        source = factory.SourceFactory()
        psi = factory.PsimodFactory()
        pta.source = source
        pta.psimod = psi
        return MockQuery(pta)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Referencedbentity'>":
        refdb = factory.ReferencedbentityFactory()
        return MockQuery(refdb)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Proteinexptannotation'>":
        prt = factory.ProteinexptannotationFactory()
        return MockQuery(prt)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Proteindomainannotation'>":
        pda = factory.ProteindomainannotationFactory()
        pd = factory.ProteindomainFactory()
        source = factory.SourceFactory()
        db = factory.DbentityFactory()
        pd.source = source
        pda.proteindomain = pd
        pda.dbentity = db
        return MockQuery(pda)
    elif len(args) == 3 and str(args[0]) == 'Dbentity.display_name' and str(args[1]) == 'Dbentity.format_name' and str(args[2]) == 'Dbentity.obj_url':
        db = factory.DbentityFactory()
        return MockQuery((db.display_name, db.format_name, db.obj_url))
    elif len(args) == 4 and str(args[0]) == 'Dbentity.dbentity_id' and str(args[1]) == 'Dbentity.display_name' and str(args[2]) == 'Dbentity.format_name' and str(args[3]) == 'Dbentity.obj_url':
        db = factory.DbentityFactory()
        return MockQuery((db.dbentity_id, db.display_name, db.format_name, db.obj_url))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Proteindomain'>":
        pd = factory.ProteindomainFactory()
        source = factory.SourceFactory()
        pd.source = source
        return MockQuery(pd)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ProteindomainUrl'>":
        pdurl = factory.ProteindomainUrlFactory()
        pd = factory.ProteindomainFactory()
        source = factory.SourceFactory()
        pd.source = source
        return MockQuery(pdurl)
    elif len(args) == 1 and str(args[0]) == 'Proteindomainannotation.dbentity_id':
        pda = factory.ProteindomainannotationFactory()
        return MockQuery((pda.dbentity_id))
    elif len(args) == 1 and str(args[0]) == 'Dbentity.format_name':
        db = factory.DbentityFactory()
        return MockQuery((db.format_name,))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Locussummary'>":
        locus_summary = factory.LocussummaryFactory()
        return MockQuery(locus_summary)
    elif len(args) == 1 and str(args[0]) == "LocussummaryReference.reference_id":
        locus_summary_reference = factory.LocussummaryReferenceFactory()
        return MockQuery(locus_summary_reference.reference_id)
    elif len(args) == 1 and str(args[0]) == "Referencedbentity.pmid":
        reference = factory.ReferencedbentityFactory()
        reference.pmid = []
        return MockQuery(reference.pmid)
    elif len(args) == 2 and str(args[0]) == "<class 'src.models.LocusAliasReferences'>" and str(args[1]) == "Referencedbentity.pmid":
        locus_alias_reference = factory.LocusAliasReferencesFactory()
        reference = factory.ReferencedbentityFactory()
        return MockQuery((locus_alias_reference,reference.pmid))
    elif len(args) == 2 and str(args[0]) == "<class 'src.models.LocusReferences'>" and str(args[1]) == "Referencedbentity.pmid":
        locus_reference = factory.LocusReferencesFactory()
        reference = factory.ReferencedbentityFactory()
        return MockQuery((locus_reference, reference.pmid))
    elif len(args) == 1 and str(args[0]) == "LocusAlias.display_name":
        locus_alias = factory.LocusAliasFactory()
        return MockQuery(locus_alias)
        return MockQuery((db.format_name))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Expressionannotation'>":
        exp = factory.ExpressionannotationFactory()
        return MockQuery(exp)
    elif len(args) == 3 and str(args[0]) == 'Expressionannotation.dbentity_id' and str(args[1]) == 'Expressionannotation.datasetsample_id' and str(args[2]) == 'Expressionannotation.normalized_expression_value':
        exp = factory.ExpressionannotationFactory()
        return MockQuery(exp)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Literatureannotation'>":
        lit_annot = factory.LiteratureannotationFactory()
        return MockQuery(lit_annot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Diseasesupportingevidence'>":
        dis_evidence = factory.DiseasesupportingevidenceFactory()
        do_annot = factory.DiseaseannotationFactory()
        dis_evidence.annotation = do_annot
        return MockQuery(dis_evidence)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Dbentity'>":
        dbentity = factory.DbentityFactory()
        src = factory.SourceFactory()
        dbentity.source = src
        return MockQuery(dbentity)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Physinteractionannotation'>":
        phys_annot = factory.PhysinteractionannotationFactory()
        dbentity1 = factory.DbentityFactory()
        phys_annot.dbentity1 = dbentity1
        dbentity2 = factory.DbentityFactory()
        phys_annot.dbentity2 = dbentity2
        psimod = factory.PsimodFactory()
        phys_annot.psimod = psimod
        ref = factory.ReferencedbentityFactory()
        phys_annot.reference = ref
        src = factory.SourceFactory()
        phys_annot.source = src
        taxonomy = factory.TaxonomyFactory()
        phys_annot.taxonomy = taxonomy
        return MockQuery(phys_annot)
    elif len(args) == 1 and args[0] == Functionalcomplementannotation:
        complement = factory.FunctionalcomplementannotationFactory()
        
        complement.dbentity = factory.DbentityFactory()
        complement.reference = factory.ReferencedbentityFactory()
        complement.source = factory.SourceFactory()
        complement.eco = factory.EcoFactory()
        complement.ro = factory.RoFactory()
        complement.taxonomy = factory.TaxonomyFactory()
        return MockQuery(complement)
    elif len(args) == 1 and args[0] == Dnasequenceannotation:
        sequence = factory.DnasequenceannotationFactory()

        sequence.config = factory.ContigFactory()
        sequence.dbentity = factory.DbentityFactory()
        sequence.file = factory.FiledbentityFactory()
        sequence.genomerelease = factory.GenomereleaseFactory()
        sequence.reference = factory.ReferencedbentityFactory()
        sequence.so = factory.SoFactory()
        sequence.source = factory.SourceFactory()
        sequence.taxonomy = factory.TaxonomyFactory()
        return MockQuery(sequence)

    else:
        print("Locus side effect condition not handled!!!!")
        print(args[0])

def phenotype_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Phenotype'>":
        obs = factory.ApoFactory()
        qual = factory.ApoFactory()
        pheno = factory.PhenotypeFactory()
        pheno.observable = obs
        pheno.qualifier = qual
        return MockQuery(pheno)
    elif len(args) == 2 and str(args[0]) == 'Phenotypeannotation.taxonomy_id' and str(args[1]) == 'count(nex.phenotypeannotation.taxonomy_id)':
        pheno = factory.PhenotypeFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.phenotype = pheno
        return MockQuery((phenoannot.taxonomy_id, 20))
    elif len(args) == 2 and str(args[0]) == 'Phenotypeannotation.taxonomy_id' and str(args[1]) == 'Phenotypeannotation.annotation_id':
        pheno = factory.PhenotypeFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.phenotype = pheno
        return MockQuery(phenoannot)
    elif len(args) == 2 and str(args[0]) == 'PhenotypeannotationCond.annotation_id' and str(args[1]) == 'count(DISTINCT nex.phenotypeannotation_cond.group_id)':
        phenocond = factory.PhenotypeannotationCondFactory()
        return MockQuery((phenocond.annotation_id, 20))
    elif len(args) == 2 and str(args[0]) == 'PhenotypeannotationCond.annotation_id' and str(args[1]) == ' func.count(distinct(PhenotypeannotationCond.group_id))':
        phenocond = factory.PhenotypeannotationCondFactory()
        return MockQuery((phenocond.annotation_id, 20))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Straindbentity'>":
        s_name = factory.StraindbentityFactory()
        return MockQuery(s_name)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Phenotypeannotation'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        mut = factory.ApoFactory()
        exp = factory.ApoFactory()
        pheno = factory.PhenotypeFactory()
        db = factory.DbentityFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.mutant = mut
        phenoannot.experiment = exp
        phenoannot.phenotype = pheno
        phenoannot.dbentity = db
        phenoannot.reference = refdbentity
        return MockQuery(phenoannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.PhenotypeannotationCond'>":
        phenocond = factory.PhenotypeannotationCondFactory()
        return MockQuery(phenocond)
    elif len(args) == 2 and str(args[0]) == 'Chebi.display_name' and str(args[1]) == 'Chebi.obj_url':
        chebi = factory.ChebiFactory()
        return MockQuery((chebi.display_name, chebi.obj_url))
    elif len(args) == 2 and str(args[0]) == 'Goannotation.dbentity_id' and str(args[1]) == 'count(nex.goannotation.dbentity_id)':
        goannot = factory.GoannotationFactory()
        return MockQuery(goannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Apo'>":
        apo = factory.ApoFactory()
        return MockQuery(apo)

def observable_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Apo'>":
        apo = factory.ApoFactory()
        return MockQuery(apo)
    elif len(args) == 3 and str(args[0]) == 'Phenotype.obj_url' and str(args[1]) == 'Phenotype.qualifier_id' and str(args[2]) == 'Phenotype.phenotype_id':
        pheno = factory.PhenotypeFactory()
        return MockQuery((pheno.obj_url, pheno.qualifier_id, pheno.phenotype_id,))
    elif len(args) == 2 and str(args[0]) == 'Phenotypeannotation.dbentity_id' and str(args[1]) == 'count(nex.phenotypeannotation.dbentity_id)':
        pheno = factory.PhenotypeFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.phenotype = pheno
        return MockQuery((phenoannot.dbentity_id, 20))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ApoRelation'>":
        parent = factory.ApoFactory()
        child = factory.ApoFactory()
        ro = factory.RoFactory()
        aporel = factory.ApoRelationFactory()
        aporel.parent = parent
        aporel.child = child
        aporel.ro = ro
        return MockQuery(aporel)
    elif len(args) == 1 and str(args[0]) == 'Phenotype.phenotype_id':
        pheno = factory.PhenotypeFactory()
        return MockQuery((pheno.phenotype_id,))
    elif len(args) == 1 and str(args[0]) == 'Apo.display_name':
        apo = factory.ApoFactory()
        return MockQuery(apo.display_name)
    elif len(args) == 2 and str(args[0]) == 'Phenotypeannotation.taxonomy_id' and str(args[1]) == 'count(nex.phenotypeannotation.taxonomy_id)':
        pheno = factory.PhenotypeFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.phenotype = pheno
        return MockQuery((phenoannot.taxonomy_id, 20))
    elif len(args) == 2 and str(args[0]) == 'Phenotypeannotation.taxonomy_id' and str(args[1]) == 'Phenotypeannotation.annotation_id':
        pheno = factory.PhenotypeFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.phenotype = pheno
        return MockQuery((phenoannot),)
    elif len(args) == 2 and str(args[0]) == 'PhenotypeannotationCond.annotation_id' and str(args[1]) == 'count(DISTINCT nex.phenotypeannotation_cond.group_id)':
        phenocond = factory.PhenotypeannotationCondFactory()
        return MockQuery((phenocond.annotation_id, 20))
    elif len(args) == 1 and str(args[0]) == 'Chebi.obj_url':
        chebi = factory.ChebiFactory()
        return MockQuery(chebi.obj_url)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Straindbentity'>":
        s_name = factory.StraindbentityFactory()
        return MockQuery(s_name)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Phenotypeannotation'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        mut = factory.ApoFactory()
        exp = factory.ApoFactory()
        pheno = factory.PhenotypeFactory()
        db = factory.DbentityFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.mutant = mut
        phenoannot.experiment = exp
        phenoannot.phenotype = pheno
        phenoannot.dbentity = db
        phenoannot.reference = refdbentity
        return MockQuery(phenoannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Phenotype'>":
        pheno = factory.PhenotypeFactory()
        return MockQuery(pheno)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.PhenotypeannotationCond'>":
        phenocond = factory.PhenotypeannotationCondFactory()
        return MockQuery(phenocond)
    elif len(args) == 2 and str(args[0]) == 'Chebi.display_name' and str(args[1]) == 'Chebi.obj_url':
        chebi = factory.ChebiFactory()
        return MockQuery((chebi.display_name, chebi.obj_url))
    elif len(args) == 2 and str(args[0]) == 'Goannotation.dbentity_id' and str(args[1]) == 'count(nex.goannotation.dbentity_id)':
        goannot = factory.GoannotationFactory()
        return MockQuery(goannot)
    else:
        print("the problem is the condition!!!!")
        print(args[0])
        print(args[1])


def disease_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Disease'>":
        dis = factory.DiseaseFactory()
        return MockQuery(dis)
    if len(args) == 2 and str(args[0]) == 'Diseaseannotation.dbentity_id' and str(args[1]) == 'count(nex.diseaseannotation.dbentity_id)':
        dis = factory.DiseaseFactory()
        disannot = factory.DiseaseannotationFactory()
        disannot.dis = dis
        return MockQuery(disannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.DiseaseRelation'>":
        dischild = factory.DiseaseFactory()
        disparent = factory.DiseaseFactory()
        disrel = factory.DiseaseRelationFactory()
        ro = factory.RoFactory()
        disrel.child = dischild
        disrel.parent = disparent
        disrel.ro = ro
        return MockQuery(disrel)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.DiseaseUrl'>":
        disurl = factory.DiseaseUrlFactory()
        return MockQuery(disurl)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.DiseaseAlias'>":
        disalias = factory.DiseaseAliasFactory()
        return MockQuery(disalias)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Locusdbentity'>":
        locus = factory.LocusdbentityFactory()
        return MockQuery(locus)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Diseaseannotation'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        dbent = factory.DbentityFactory()
        dis = factory.DiseaseFactory()
        disannot = factory.DiseaseannotationFactory()
        disannot.disease = dis
        disannot.dbentity = dbent
        disannot.reference = refdbentity
        disannot.source = source
        return MockQuery(disannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.EcoAlias'>":
        ecoalias = factory.EcoAliasFactory()
        return MockQuery(ecoalias)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.EcoUrl'>":
        ecourl = factory.EcoUrlFactory()
        return MockQuery(ecourl)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Dbentity'>":
        dbent = factory.DbentityFactory()
        return MockQuery(dbent)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Diseasesupportingevidence'>":
        disevd = factory.DiseasesupportingevidenceFactory()
        return MockQuery(disevd)
    elif len(args) == 3 and str(args[0]) == "<class 'src.models.Diseaseannotation'>" and str(args[1]) == 'Diseasesupportingevidence.dbxref_id' and str(args[2]) ==  'Diseasesupportingevidence.obj_url':
        dis = factory.DiseaseFactory()
        disannot = factory.DiseaseannotationFactory()
        disannot.dis = dis
        return MockQuery(disannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Referencedbentity'>":
        refdb = factory.ReferencedbentityFactory()
        return MockQuery(refdb)
    




def chemical_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Chebi'>":
        chem = factory.ChebiFactory()
        return MockQuery(chem)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ChebiAlia'>":
        chebi_alias = factory.ChebiAliaFactory()
        return MockQuery(chebi_alias)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ChebiUrl'>":
        url = factory.ChebiUrlFactory()
        return MockQuery(url)
    elif len(args) == 1 and str(args[0]) == 'PhenotypeannotationCond.annotation_id':
        phenocond = factory.PhenotypeannotationCondFactory()
        return MockQuery([(phenocond.annotation_id,)])
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Phenotypeannotation'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        db_entity = factory.DbentityFactory()
        pheno = factory.PhenotypeFactory()
        phenoannot = factory.Phenotypeannotation()
        phenoannot.phenotype = pheno
        phenoannot.dbentity = db_entity
        phenoannot.reference = refdbentity
        return MockQuery(phenoannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.PhenotypeannotationCond'>":
        phenocond = factory.PhenotypeannotationCondFactory()
        return MockQuery(phenocond)
    elif len(args) == 1 and str(args[0]) == 'Chebi.obj_url':
        chebi = factory.ChebiFactory()
        return MockQuery(chebi.obj_url)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Straindbentity'>":
        s_name = factory.StraindbentityFactory()
        return MockQuery(s_name)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Apo'>":
        apo = factory.ApoFactory()
        return MockQuery(apo)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Interactor'>":
        interactor = factory.InteractorFactory()
        return MockQuery(interactor)
    elif len(args) == 1 and str(args[0]) == "Interactor.interactor_id":
        interactor = factory.InteractorFactory()
        return MockQuery(interactor)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Complexbindingannotation'>":
        bind = factory.ComplexbindingannotationFactory()
        return MockQuery(bind)
    elif len(args) == 1 and str(args[0]) == "Goextension.annotation_id":
        ro = factory.RoFactory()
        goext = factory.GoextensionFactory()
        goext.ro = ro
        return MockQuery(goext)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Goannotation'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        dbent = factory.DbentityFactory()
        go = factory.GoFactory()
        goannot = factory.GoannotationFactory()
        goannot.go = go
        goannot.dbentity = dbent
        goannot.reference = refdbentity
        goannot.source = source
        return MockQuery(goannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.EcoAlias'>":
        ecoalias = factory.EcAliasFactory()
        return MockQuery(ecoalias)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.EcoUrl'>":
        ecourl = factory.EcoUrlFactory()
        return MockQuery(ecourl)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Goextension'>":
        ro = factory.RoFactory()
        goext = factory.GoextensionFactory()
        goext.ro = ro
        return MockQuery(goext)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Dbentity'>":
        db = factory.DbentityFactory()
        return MockQuery(db)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Gosupportingevidence'>":
        goev = factory.GosupportingevidenceFactory()
        return MockQuery(goev)
    elif len(args) == 1 and args[0] == Proteinabundanceannotation:
        prot = factory.ProteinabundanceAnnotationFactory()

        prot.eco = factory.EcoFactory()
        prot.efo = factory.EfoFactory()
        prot.dbentity = factory.DbentityFactory()
        prot.reference = factory.ReferencedbentityFactory()
        prot.original_reference = factory.ReferencedbentityFactory()
        prot.chebi = factory.ChebiFactory()
        prot.go = factory.GoFactory()
        prot.source = factory.SourceFactory()
        prot.taxonomy = factory.TaxonomyFactory()
        return MockQuery(prot)
    elif len(args) == 1 and args[0] == Referencedbentity:
        ref = factory.ReferencedbentityFactory()

        ref.book = factory.BookFactory()
        ref.journal = factory.JournalFactory()
        return MockQuery(ref)
    elif len(args) == 1 and args[0] == Pathwaydbentity:
        pathway = factory.PathwaydbentityFactory()
        return MockQuery(pathway)
    elif len(args) == 1:
        cheb = factory.ChebiAliaFactory()
        return MockQuery(cheb)
    else:
        print("COULDN'T FIND ANYTHING CHEMICAL SIDE EFFECT")
        print("args = {}, type is {}".format(args[0], type(args[0])))
        return None


def author_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Referenceauthor'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdb = factory.ReferencedbentityFactory()
        refauth = factory.ReferenceauthorFactory()
        refauth.reference = refdb
        return MockQuery(refauth)
    elif len(args) == 1 and str(args[0]) == 'Referencedocument.html':
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdb = factory.ReferencedbentityFactory()
        refdb.journal = journal
        refdoc = factory.ReferencedocumentFactory()
        return MockQuery(refdoc.html)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ReferenceUrl'>":
        refurl = factory.ReferenceUrlFactory()
        return MockQuery(refurl)
    elif len(args) == 1 and str(args[0]) == 'Referencetype.display_name':
        reftype = factory.ReferencetypeFactory()
        return MockQuery((reftype.display_name))

def keywords_side_effect(*args, **kwargs):
    
    if len(args) == 1 and str(args[0]) == 'DISTINCT nex.dataset_keyword.keyword_id':
        dskw = factory.DatasetKeywordFactory()
        kw = factory.KeywordFactory()
        dskw.keyword = kw
        return MockQuery((dskw.keyword_id))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.DatasetKeyword'>":
        dskw = factory.DatasetKeywordFactory()
        return MockQuery([dskw])
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Dataset'>":
        ds = factory.DatasetFactory()
        return MockQuery([ds])
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Keyword'>":
        kw = factory.KeywordFactory()
        return MockQuery([kw])

def dataset_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Dataset'>":
        ds_name = factory.DatasetFactory()
        return MockQuery(ds_name)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.DatasetKeyword'>":
        dskw = factory.DatasetKeywordFactory()
        kw = factory.KeywordFactory()
        dskw.keyword = kw
        return MockQuery(dskw)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Keyword'>":
        kw = factory.KeywordFactory()
        return MockQuery(kw)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.DatasetReference'>":
        dsref = factory.DatasetReferenceFactory()
        return MockQuery((dsref),)
    elif len(args) == 1 and str(args[0]) == 'Referencedocument.html':
        refdoc = factory.ReferencedocumentFactory()
        return MockQuery(refdoc.html)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Datasetsample'>":
        dss = factory.DatasetsampleFactory()
        return MockQuery(dss)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.DatasetUrl'>":
        dsurl = factory.DatasetUrlFactory()
        return MockQuery(dsurl)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.DatasetFile'>":
        dsf = factory.DatasetFileFactory()
        f = factory.FiledbentityFactory()
        dsf.file = f
        return MockQuery(dsf)


def side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Straindbentity'>":
        s_name = factory.StraindbentityFactory()
        return MockQuery(s_name)
    if len(args) == 3 and str(args[0]) == 'StrainUrl.display_name' and str(args[1]) == 'StrainUrl.url_type' and str(
            args[2]) == 'StrainUrl.obj_url':
        strain_url = factory.StrainUrlFactory()
        return MockQuery((strain_url.display_name, strain_url.url_type, strain_url.obj_url))
    elif len(args) == 2 and str(args[0]) == 'Strainsummary.summary_id' and str(args[1]) == 'Strainsummary.html':
        strain_summary = factory.StrainsummaryFactory()
        return MockQuery((strain_summary.summary_id, strain_summary.html))
    elif len(args) == 1 and str(args[0]) == 'StrainsummaryReference.reference_id':
        strain_ref = factory.StrainsummaryReferenceFactory()
        return MockQuery([(strain_ref.reference_id,)])
    elif len(args) == 1 and str(args[0]) == 'ReferenceUrl.reference_id':
        refurl = factory.ReferenceUrlFactory()
        return MockQuery(refurl.obj_url)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Referencedbentity'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        return MockQuery(refdbentity)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ReferenceUrl'>":
        refurl = factory.ReferenceUrlFactory()
        return MockQuery(refurl)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Contig'>":
        c_name = factory.ContigFactory()
        return MockQuery(c_name)
    elif len(args) == 2 and str(args[0]) == 'Contig.format_name' and str(args[1]) == 'Contig.obj_url':
        c_name = factory.ContigFactory()
        return MockQuery((c_name.format_name, c_name.obj_url))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Ec'>":
        ec = factory.EcFactory()
        return MockQuery(ec)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.EcUrl'>":
        ecurl = factory.EcUrlFactory()
        return MockQuery(ecurl)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Psimod'>":
        psimod = factory.PsimodFactory()
        return MockQuery([psimod])
    elif len(args) == 1 and str(args[0]) == "Posttranslationannotation.psimod_id":
        ptm = factory.PsimodFactory()
        return MockQuery([ptm])
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Dbentity'>":
        dbentity = factory.DbentityFactory()
        return MockQuery(dbentity)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Posttranslationannotation'>":
        ptm = factory.PosttranslationannotationFactory()
        dbentity = factory.DbentityFactory()
        reference = factory.ReferencedbentityFactory()
        source = factory.SourceFactory()
        psimod = factory.PsimodFactory()
        ptm.dbentity = dbentity
        ptm.reference = reference
        ptm.source = source
        ptm.psimod = psimod
        return MockQuery(ptm)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Colleague'>":
        colleague = factory.ColleagueFactory()
        return MockQuery([colleague,colleague])
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Colleaguetriage'>":
        colleague_triage = factory.ColleaguetriageFactory()
        return MockQuery([colleague_triage])
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.CuratorActivity'>":
        curator_activity = factory.CuratorActivityFactory()
        return MockQuery([curator_activity])
# def mock_extract_id_request(request, classname):
#      return 'S000203483'

def locus_reference_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Locusdbentity'>":
        locus = factory.LocusdbentityFactory()
        return MockQuery(locus)
    elif len(args) == 1 and str(args[0]) == "Literatureannotation.reference_id":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        litannot = factory.LiteratureannotationFactory()
        db = factory.DbentityFactory()
        litannot.reference = refdbentity
        litannot.dbentity = db
        return MockQuery((litannot.reference_id,))
    elif len(args) == 1 and str(args[0]) == "Geninteractionannotation.reference_id":
        gen = factory.GeninteractionannotationFactory()
        return MockQuery((gen.reference_id,))
    elif len(args) == 1 and str(args[0]) == "Physinteractionannotation.reference_id":
        gen = factory.PhysinteractionannotationFactory()
        return MockQuery((gen.reference_id,))
    elif len(args) == 1 and str(args[0]) == "Regulationannotation.reference_id":
        reg = factory.RegulationannotationFactory()
        return MockQuery((reg.reference_id,))
    elif len(args) == 1 and str(args[0]) == "Phenotypeannotation.reference_id":
        pheno = factory.PhenotypeannotationFactory()
        return MockQuery((pheno.reference_id,))
    elif len(args) == 1 and str(args[0]) == "Goannotation.reference_id":
        go = factory.GoannotationFactory()
        return MockQuery((go.reference_id,))
    elif len(args) == 1 and str(args[0]) == "Diseaseannotation.reference_id":
        do = factory.DiseaseannotationFactory()
        return MockQuery((do.reference_id,))
    elif len(args) == 1 and str(args[0]) == "ReferenceAlias.reference_id":
        refalias = factory.ReferenceAliasFactory()
        return MockQuery(refalias.reference_id)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Referencedbentity'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        return MockQuery(refdbentity)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ReferenceUrl'>":
        refurl = factory.ReferenceUrlFactory()
        return MockQuery(refurl)
    elif len(args) == 1 and str(args[0]) == "Apo.apo_id":
        apo = factory.ApoFactory()
        return MockQuery(apo.apo_id)
    elif len(args) == 2 and str(args[0]) == "Phenotypeannotation.reference_id" and str(args[1]) == "Phenotypeannotation.experiment_id":
        phen = factory.PhenotypeannotationFactory()
        return MockQuery((phen.reference_id, phen.experiment_id))
    elif len(args) == 2 and str(args[0]) == "Literatureannotation.reference_id" and str(args[1]) == "Literatureannotation.topic":
        lit = factory.LiteratureannotationFactory()
        return MockQuery((lit.reference_id, lit.topic))
    else:
        print("the problem is the condition!!!!")
        print(args[0])
        print(args[1])


def protein_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Posttranslationannotation'>":
        pta = factory.PosttranslationannotationFactory()
        return MockQuery(pta)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Referencedbentity'>":
        refdb = factory.ReferencedbentityFactory()
        return MockQuery(refdb)

def sequence_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Locusdbentity'>":
        locus = factory.LocusdbentityFactory()
        return MockQuery(locus)
    elif len(args) == 1 and str(args[0]) == 'Locusdbentity.dbentity_id':
        locus = factory.LocusdbentityFactory()
        return MockQuery((locus.dbentity_id,))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Dnasequenceannotation'>":
        dnaseq = factory.DnasequenceannotationFactory()
        contig = factory.ContigFactory()
        locus = factory.LocusdbentityFactory()
        dnaseq.contig = contig
        dnaseq.dbentity = locus
        return MockQuery(dnaseq)
    elif len(args) == 1 and str(args[0]) == 'Dnasequenceannotation.so_id':
        dnaseq = factory.DnasequenceannotationFactory()
        return MockQuery([(dnaseq.so_id,)])
    elif len(args) == 1 and str(args[0]) == 'So.display_name':
        so = factory.SoFactory()
        return MockQuery(so.display_name)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Proteinsequenceannotation'>":
        prtseq = factory.ProteinsequenceannotationFactory()
        contig = factory.ContigFactory()
        prtseq.contig = contig
        return MockQuery(prtseq)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Dnasubsequence'>":
        dnasubseq = factory.DnasubsequenceFactory()
        return MockQuery(dnasubseq)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Straindbentity'>":
        s_name = factory.StraindbentityFactory()
        return MockQuery(s_name)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Contig'>":
        c_name = factory.ContigFactory()
        return MockQuery(c_name)
    elif len(args) == 2 and str(args[0]) == 'Dnasequenceannotation.so_id' and str(args[1]) == 'count(nex.dnasequenceannotation.annotation_id)':
        dnaseq = factory.DnasequenceannotationFactory()
        return MockQuery((dnaseq.so_id, 20))
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.So'>":
        so = factory.SoFactory()
        return MockQuery(so)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ContigUrl'>":
        ctgurl = factory.ContigUrlFactory()
        return MockQuery(ctgurl)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.ProteinsequenceDetail'>":
        prtseq = factory.ProteinsequenceDetailFactory()
        return MockQuery(prtseq)


def reference_side_effect(*args, **kwargs):
            if len(args) == 1 and str(args[0]) == "<class 'src.models.Referencedbentity'>":
                source = factory.SourceFactory()
                journal = factory.JournalFactory()
                book = factory.BookFactory()
                refdbentity = factory.ReferencedbentityFactory()
                refdbentity.journal = journal
                return MockQuery(refdbentity)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Locusdbentity'>":
                locus = factory.LocusdbentityFactory()
                return MockQuery(locus)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.DatasetReference'>":
                datasetref = factory.DatasetReferenceFactory()
                datasetf = factory.DatasetFactory()
                datasetref.dataset = datasetf
                return MockQuery(datasetref)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Dataset'>":
                dataset = factory.DatasetFactory()
                return MockQuery(dataset)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.DatasetKeyword'>":
                datasetkw = factory.DatasetKeywordFactory()
                datasetkw.keyword = factory.KeywordFactory()
                return MockQuery(datasetkw)
            elif len(args) == 1 and str(args[0]) == 'Referencedocument.html':
                source = factory.SourceFactory()
                journal = factory.JournalFactory()
                book = factory.BookFactory()
                refdb = factory.ReferencedbentityFactory()
                refdb.journal = journal
                refdoc = factory.ReferencedocumentFactory()
                return MockQuery(refdoc.html)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.ReferenceUrl'>":
                refurl = factory.ReferenceUrlFactory()
                return MockQuery(refurl)
            elif len(args) == 1 and str(args[0]) == 'Referencetype.display_name':
                reftype = factory.ReferencetypeFactory()
                return MockQuery((reftype.display_name))
            elif len(args) == 2 and str(args[0]) == 'Referenceauthor.display_name' and str(args[1]) == 'Referenceauthor.obj_url':
                refauthor = factory.ReferenceauthorFactory()
                return MockQuery((refauthor.display_name, refauthor.obj_url))
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.ReferenceRelation'>":
                refrel = factory.ReferenceRelationFactory()
                refrel.child = factory.ReferencedbentityFactory()
                refrel.parent = factory.ReferencedbentityFactory()
                return MockQuery((refrel))
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.ReferenceUrl'>":
                refurl = factory.ReferenceUrlFactory()
                return MockQuery(refurl)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Physinteractionannotation'>":
                source = factory.SourceFactory()
                journal = factory.JournalFactory()
                book = factory.BookFactory()
                refdbentity = factory.ReferencedbentityFactory()
                refdbentity.journal = journal
                intannot = factory.PhysinteractionannotationFactory()
                intannot.reference = refdbentity
                intannot.source = source
                db1 = factory.DbentityFactory(dbentity_id=1)
                db2 = factory.DbentityFactory(dbentity_id=2)
                intannot.dbentity1 = db1
                intannot.dbentity2= db2
                return MockQuery((intannot))
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Geninteractionannotation'>":
                source = factory.SourceFactory()
                journal = factory.JournalFactory()
                book = factory.BookFactory()
                refdbentity = factory.ReferencedbentityFactory()
                refdbentity.journal = journal
                db1 = factory.DbentityFactory(dbentity_id=1)
                db2 = factory.DbentityFactory(dbentity_id=2)
                genannot = factory.GeninteractionannotationFactory()
                genannot.dbentity1 = db1
                genannot.dbentity2= db2
                genannot.reference = refdbentity
                genannot.source = source
                return MockQuery((genannot))
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Goannotation'>":
                source = factory.SourceFactory()
                journal = factory.JournalFactory()
                book = factory.BookFactory()
                refdbentity = factory.ReferencedbentityFactory()
                refdbentity.journal = journal
                ecof = factory.EcoFactory()
                go = factory.GoFactory()
                db = factory.DbentityFactory()
                goannot = factory.GoannotationFactory()
                goannot.reference = refdbentity
                goannot.dbentity = db
                goannot.eco = ecof
                goannot.go = go
                goannot.source = source
                return MockQuery(goannot)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.EcoAlias'>":
                # ecof = factory.EcoFactory()
                ecoalias = factory.EcoAliasFactory()
                # ecoalias.eco = ecof
                return MockQuery(ecoalias)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.EcoUrl'>":
                ecourl = factory.EcoUrlFactory()
                return MockQuery(ecourl)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Goextension'>":
                ro = factory.RoFactory()
                goext = factory.GoextensionFactory()
                goext.ro = ro
                return MockQuery(goext)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Dbentity'>":
                db = factory.DbentityFactory()
                return MockQuery(db)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Gosupportingevidence'>":
                goev = factory.GosupportingevidenceFactory()
                return MockQuery(goev)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Phenotypeannotation'>":
                source = factory.SourceFactory()
                journal = factory.JournalFactory()
                book = factory.BookFactory()
                refdbentity = factory.ReferencedbentityFactory()
                refdbentity.journal = journal
                pheno = factory.PhenotypeFactory()
                db = factory.DbentityFactory()
                phenoannot = factory.PhenotypeannotationFactory()
                phenoannot.reference = refdbentity
                phenoannot.phenotype = pheno
                phenoannot.dbentity = db
                return MockQuery(phenoannot)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Diseaseannotation'>":
                source = factory.SourceFactory()
                journal = factory.JournalFactory()
                book = factory.BookFactory()
                refdbentity = factory.ReferencedbentityFactory()
                refdbentity.journal = journal
                disease = factory.DiseaseFactory()
                db = factory.DbentityFactory()
                diseaseannot = factory.PhenotypeannotationFactory()
                diseaseannot.reference = refdbentity
                diseaseannot.disease = disease
                diseaseannot.dbentity = db
                return MockQuery(diseaseannot)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.PhenotypeannotationCond'>":
                cond = factory.PhenotypeannotationCondFactory()
                return MockQuery(cond)
            elif len(args) == 1 and str(args[0]) == 'Chebi.obj_url':
                chebi = factory.ChebiFactory()
                return MockQuery(chebi.obj_url)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Straindbentity'>":
                s_name = factory.StraindbentityFactory()
                return MockQuery(s_name)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Apo'>":
                apo = factory.ApoFactory()
                return MockQuery(apo)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Regulationannotation'>":
                target = factory.DbentityFactory()
                regulator = factory.DbentityFactory()
                regannot = factory.RegulationannotationFactory()
                regannot.target = target
                regannot.regulator = regulator
                return MockQuery((regannot))
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Literatureannotation'>":
                source = factory.SourceFactory()
                journal = factory.JournalFactory()
                book = factory.BookFactory()
                refdbentity = factory.ReferencedbentityFactory()
                refdbentity.journal = journal
                dbentity = factory.DbentityFactory()
                litannot = factory.LiteratureannotationFactory()
                litannot.dbentity = dbentity
                litannot.reference = refdbentity
                return MockQuery(litannot)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Straindbentity'>":
                s_name = factory.StraindbentityFactory()
                return MockQuery(s_name)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.ReferenceFile'>":
                file = factory.FiledbentityFactory()
                referencefile = factory.ReferenceFileFactory()
                referencefile.file = file
                return MockQuery(referencefile)
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Referencetriage'>":
                reference_triage = factory.ReferencetriageFactory()
                return MockQuery([reference_triage])
            elif len(args) == 2 and str(args[0]) == "<class 'src.models.CurationReference'>" and str(args[1]) == "<class 'src.models.Locusdbentity'>":
                curator_reference = factory.CurationReferenceFactory()
                locus_dbentity = factory.LocusdbentityFactory()
                mock = Mock()
                mock.Locusdbentity = locus_dbentity
                mock.CurationReference = curator_reference
                return MockQuery([mock])
            elif len(args) == 2 and str(args[0]) == "<class 'src.models.Literatureannotation'>" and str(args[1]) == "<class 'src.models.Locusdbentity'>":
                literature_annotation = factory.LiteratureannotationFactory()
                locus_dbentity = factory.LocusdbentityFactory()
                mock = Mock()
                mock.Locusdbentity = locus_dbentity
                mock.Literatureannotation = literature_annotation
                return MockQuery([mock])
            elif len(args) == 1 and str(args[0]) == "<class 'src.models.Posttranslationannotation'>":
                ptm = factory.PosttranslationannotationFactory()
                return MockQuery(ptm)
            elif len(args) == 1 and args[0] == AlleleGeninteraction:
                allelegen = factory.AlleleGeninteractionFactory()

                allelegen.allele1 = factory.AlleledbentityFactory()
                allelegen.allele2 = factory.AlleledbentityFactory()
                allelegen.soruce = factory.SourceFactory()
                allelegen.interaction = factory.GeninteractionannotationFactory()
                return MockQuery(allelegen)
            elif len(args) == 1 and args[0] == Functionalcomplementannotation:
                func = factory.FunctionalcomplementannotationFactory()
                return MockQuery(func)
            elif len(args) == 2 and args[0] == CurationReference and args[1] == Complexdbentity:
                mock = Mock()
                mock.CurationReference = factory.CurationReferenceFactory()
                mock.ComplexdbentityFactory = factory.ComplexdbentityFactory()
                return MockQuery([mock])
            elif len(args) == 2 and args[0] == CurationReference and args[1] == Pathwaydbentity:
                mock = Mock()
                mock.CurationReference = factory.CurationReferenceFactory()
                mock.Pathwaydbentity = factory.PathwaydbentityFactory()
                return MockQuery([mock])
            elif len(args) == 2 and args[0] == CurationReference and args[1] == Alleledbentity:
                mock = Mock()
                mock.CurationReference = factory.CurationReferenceFactory()
                mock.Alleledbentity = factory.AlleledbentityFactory()
                return MockQuery([mock])
            elif len(args) == 2 and args[0] == Literatureannotation and args[1] == Complexdbentity:
                mock = Mock()
                mock.Literatureannotation = factory.LiteratureannotationFactory()
                mock.Complexdbentity = factory.ComplexdbentityFactory()
                return MockQuery([mock])
            elif len(args) == 2 and args[0] == Literatureannotation and args[1] == Pathwaydbentity:
                lit = factory.LiteratureannotationFactory()
                pathway = factory.ComplexdbentityFactory()
                mock = Mock()
                mock.Literatureannotation = lit
                mock.Complexdbentity = pathway
                return MockQuery([mock])
            elif len(args) == 2 and args[0] == Literatureannotation and args[1] == Alleledbentity:
                mock = Mock()
                mock.Literatureannotation = factory.LiteratureannotationFactory()
                mock.Complexdbentity = factory.AlleledbentityFactory()
                return MockQuery([mock])
            else:
                print("the problem is the condition!!!!")
                print(args)

def reference_phenotype_side_effect(*args, **kwargs):
    
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Referencedbentity'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        return MockQuery(refdbentity)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Phenotypeannotation'>":
        source = factory.SourceFactory()
        journal = factory.JournalFactory()
        book = factory.BookFactory()
        refdbentity = factory.ReferencedbentityFactory()
        refdbentity.journal = journal
        #pheno = factory.PhenotypeFactory()
        db = factory.DbentityFactory()
        phenoannot = factory.PhenotypeannotationFactory()
        phenoannot.reference = refdbentity
        #phenoannot.phenotype = pheno
        phenoannot.dbentity = db
        return MockQuery(phenoannot)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.PhenotypeannotationCond'>":
        cond = factory.PhenotypeannotationCondFactory()
        return MockQuery(cond)
    elif len(args) == 1 and str(args[0]) == 'Chebi.obj_url':
        chebi = factory.ChebiFactory()
        return MockQuery(chebi.obj_url)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Straindbentity'>":
        s_name = factory.StraindbentityFactory()
        return MockQuery(s_name)
    elif len(args) == 1 and str(args[0]) == "<class 'src.models.Apo'>":
        apo = factory.ApoFactory()
        return MockQuery(apo)

def strain_side_effect(*args, **kwargs):
    if len(args) == 1 and str(args[0]) == "<class 'src.models.Straindbentity'>":
        s_name = factory.StraindbentityFactory()
        return MockQuery([s_name])
