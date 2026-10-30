"""Batch annotation download for a gene list.

get_list_annotations() returns one data type (GO, phenotype, interaction,
regulation, ...) for a set of genes as {columns, rows}. Where SGD publishes a
genome-wide download file for the data type, the columns follow that file
(scripts/dumping/tab_files_for_download_site), so a gene-list download is a
filtered version of a file researchers already know.
"""
import datetime
from collections import OrderedDict
from decimal import Decimal

from sqlalchemy import text

from .gene_list_helpers import MAX_INPUT_IDENTIFIERS, _cached, get_lookup, resolve_identifiers
from .models import DBSession

MAX_ROWS = 200000
S288C_TAXID = 'TAX:559292'

# Each data type: label, the download file it mirrors (if any), columns, and a
# builder(ids, options) -> list of rows. Builders get the list as a Python list
# of active locus ids and bind it as a Postgres array.
ANNOTATION_TYPES = OrderedDict()


def _register(key, label, columns, source_file=None, description=''):
    def wrap(builder):
        ANNOTATION_TYPES[key] = {'label': label, 'columns': columns, 'source_file': source_file,
                                 'description': description, 'builder': builder}
        return builder
    return wrap


def _rows(sql, ids, **params):
    params['ids'] = list(ids)
    return DBSession.execute(text(sql), params).fetchall()


def _clean(value):
    """Make a cell JSON- and TSV-safe: None -> '', whitespace collapsed,
    numeric (Decimal) columns -> float, dates -> ISO strings."""
    if value is None:
        return ''
    if isinstance(value, str):
        return ' '.join(value.split())
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


def _names(locus_id):
    """(systematic_name, gene_name, sgdid) for an active locus, else blanks."""
    locus = get_lookup()[0].get(locus_id)
    if not locus:
        return ('', '', '')
    return (locus['systematic_name'], locus['gene_name'] or '', locus['sgdid'])


def _reference(sgdid, pmid):
    ref = 'SGD_REF:' + sgdid if sgdid else ''
    if pmid:
        ref = ref + '|PMID:' + str(pmid) if ref else 'PMID:' + str(pmid)
    return ref


def _pmid(pmid, sgdid=None):
    if pmid:
        return 'PMID:' + str(pmid)
    return 'SGD_REF:' + sgdid if sgdid else ''


def _build_strain_names():
    """taxonomy_id -> strain name. One generic S. cerevisiae taxonomy is shared
    by several minor strains; those annotations are reported as 'Other'."""
    by_taxonomy = {}
    for taxonomy_id, name in DBSession.execute(text(
            "SELECT sd.taxonomy_id, d.display_name FROM nex.straindbentity sd "
            "JOIN nex.dbentity d ON d.dbentity_id = sd.dbentity_id")):
        by_taxonomy.setdefault(taxonomy_id, []).append(name)
    return {t: names[0] if len(names) == 1 else ('Other' if 'Other' in names else '')
            for t, names in by_taxonomy.items()}


def _strain(taxonomy_id):
    return _cached('strain_names', _build_strain_names).get(taxonomy_id, '')


def _complex_names():
    """complex dbentity_id -> (complex accession, '|'-joined aliases)."""
    rows = DBSession.execute(text(
        "SELECT cd.dbentity_id, cd.complex_accession, ca.display_name "
        "FROM nex.complexdbentity cd LEFT JOIN nex.complex_alias ca ON ca.complex_id = cd.dbentity_id "
        "ORDER BY cd.dbentity_id, ca.alias_id")).fetchall()
    out = {}
    for complex_id, accession, alias in rows:
        names = out.setdefault(complex_id, (accession, []))[1]
        if alias:
            names.append(alias)
    return {k: (acc, '|'.join(aliases)) for k, (acc, aliases) in out.items()}


@_register('gene_info', 'Gene information',
           ['Systematic Name', 'Gene Name', 'SGDID', 'Feature Type', 'Qualifier', 'Aliases', 'Chromosome',
            'Start', 'End', 'Strand', 'Name Description', 'Description'],
           description='One row per gene: names, feature type, S288C coordinates and description')
def _gene_info(ids, options):
    aliases = {}
    for locus_id, alias in _rows(
            "SELECT locus_id, display_name FROM nex.locus_alias "
            "WHERE locus_id = ANY(:ids) AND alias_type IN ('Uniform', 'Non-uniform') "
            "ORDER BY display_name", ids):
        aliases.setdefault(locus_id, []).append(alias)
    coords = {}
    for row in _rows(
            "SELECT dsa.dbentity_id, so.display_name AS feature_type, c.display_name AS contig, "
            "       dsa.start_index, dsa.end_index, dsa.strand "
            "FROM nex.dnasequenceannotation dsa "
            "JOIN nex.so so ON so.so_id = dsa.so_id "
            "JOIN nex.contig c ON c.contig_id = dsa.contig_id "
            "JOIN nex.taxonomy t ON t.taxonomy_id = dsa.taxonomy_id "
            "WHERE dsa.dbentity_id = ANY(:ids) AND dsa.dna_type = 'GENOMIC' AND t.taxid = :taxid",
            ids, taxid=S288C_TAXID):
        coords[row.dbentity_id] = row
    details = {row.dbentity_id: row for row in _rows(
        "SELECT dbentity_id, name_description, description FROM nex.locusdbentity "
        "WHERE dbentity_id = ANY(:ids)", ids)}
    loci = get_lookup()[0]
    out = []
    for locus_id in ids:
        locus = loci[locus_id]
        c = coords.get(locus_id)
        d = details.get(locus_id)
        out.append([locus['systematic_name'], locus['gene_name'] or '', locus['sgdid'],
                    c.feature_type if c else '', locus['qualifier'] or '',
                    '|'.join(aliases.get(locus_id, [])),
                    c.contig.replace('Chromosome ', '') if c else '',
                    c.start_index if c else '', c.end_index if c else '', c.strand if c else '',
                    d.name_description if d else '', d.description if d else ''])
    return out


@_register('go', 'GO annotations',
           ['Systematic Name', 'Gene Name', 'SGDID', 'Qualifier', 'GO ID', 'GO Term', 'Aspect',
            'Evidence Code', 'ECO ID', 'Annotation Type', 'Source', 'Reference', 'Date Assigned'],
           description='Gene Ontology annotations, including high-throughput and computational ones')
def _go(ids, options):
    out = []
    for r in _rows(
            "SELECT ga.dbentity_id, ga.go_qualifier, g.goid, g.display_name AS term, g.go_namespace, "
            "       e.ecoid, (SELECT a.display_name FROM nex.eco_alias a WHERE a.eco_id = e.eco_id "
            "                 AND a.alias_type = 'EXACT' ORDER BY length(a.display_name) LIMIT 1) AS code, "
            "       ga.annotation_type, s.display_name AS source, d.sgdid AS ref_sgdid, rd.pmid, ga.date_assigned "
            "FROM nex.goannotation ga "
            "JOIN nex.go g ON g.go_id = ga.go_id "
            "JOIN nex.eco e ON e.eco_id = ga.eco_id "
            "JOIN nex.source s ON s.source_id = ga.source_id "
            "JOIN nex.dbentity d ON d.dbentity_id = ga.reference_id "
            "JOIN nex.referencedbentity rd ON rd.dbentity_id = ga.reference_id "
            "WHERE ga.dbentity_id = ANY(:ids)", ids):
        aspect = {'biological process': 'P', 'molecular function': 'F',
                  'cellular component': 'C'}.get(r.go_namespace, r.go_namespace)
        out.append(list(_names(r.dbentity_id)) + [
            r.go_qualifier, r.goid, r.term, aspect, r.code or '', r.ecoid, r.annotation_type, r.source,
            _reference(r.ref_sgdid, r.pmid), r.date_assigned.strftime('%Y-%m-%d') if r.date_assigned else ''])
    return out


@_register('phenotype', 'Phenotypes',
           ['Feature Name', 'Feature Type', 'Gene Name', 'SGDID', 'Reference', 'Experiment Type',
            'Mutant Type', 'Allele', 'Strain Background', 'Phenotype', 'Chemical', 'Condition', 'Details',
            'Reporter'],
           source_file='phenotype_data.tab',
           description='Mutant phenotypes; one row per reference per condition group')
def _phenotype(ids, options):
    feature_types = {r.dbentity_id: r.display_name for r in _rows(
        "SELECT dsa.dbentity_id, so.display_name FROM nex.dnasequenceannotation dsa "
        "JOIN nex.so so ON so.so_id = dsa.so_id "
        "WHERE dsa.dbentity_id = ANY(:ids) AND dsa.dna_type = 'GENOMIC'", ids)}
    conds = {}
    for r in _rows(
            "SELECT c.annotation_id, c.group_id, c.condition_class, c.condition_name, "
            "       c.condition_value, c.condition_unit "
            "FROM nex.phenotypeannotation_cond c "
            "JOIN nex.phenotypeannotation pa ON pa.annotation_id = c.annotation_id "
            "WHERE pa.dbentity_id = ANY(:ids) ORDER BY c.annotation_id, c.group_id", ids):
        conds.setdefault(r.annotation_id, []).append(r)
    out = []
    for r in _rows(
            "SELECT pa.annotation_id, pa.dbentity_id, pa.details, p.display_name AS phenotype, "
            "       e.display_name AS experiment, m.display_name AS mutant, ad.display_name AS allele, "
            "       rp.display_name AS reporter, pa.taxonomy_id, d.sgdid AS ref_sgdid, rd.pmid "
            "FROM nex.phenotypeannotation pa "
            "JOIN nex.phenotype p ON p.phenotype_id = pa.phenotype_id "
            "JOIN nex.apo e ON e.apo_id = pa.experiment_id "
            "JOIN nex.apo m ON m.apo_id = pa.mutant_id "
            "JOIN nex.dbentity d ON d.dbentity_id = pa.reference_id "
            "JOIN nex.referencedbentity rd ON rd.dbentity_id = pa.reference_id "
            "LEFT JOIN nex.dbentity ad ON ad.dbentity_id = pa.allele_id "
            "LEFT JOIN nex.reporter rp ON rp.reporter_id = pa.reporter_id "
            "WHERE pa.dbentity_id = ANY(:ids)", ids):
        systematic_name, gene_name, sgdid = _names(r.dbentity_id)
        prefix = [systematic_name, feature_types.get(r.dbentity_id, ''), gene_name, sgdid,
                  _reference(r.ref_sgdid, r.pmid), r.experiment, r.mutant, r.allele or '', _strain(r.taxonomy_id),
                  r.phenotype]
        for chemical, condition in _group_conditions(conds.get(r.annotation_id)):
            out.append(prefix + [chemical, condition, r.details or '', r.reporter or ''])
    out.sort(key=lambda row: [str(x) for x in row])
    return out


def _format_condition(cond):
    # Same rendering as the phenotype_data.tab generator: 'name (value+unit)'
    name = cond.condition_name.strip()
    if cond.condition_value:
        value = cond.condition_value.strip()
        if cond.condition_unit:
            value = value + cond.condition_unit.strip()
        return name + ' (' + value + ')'
    return name


def _group_conditions(conds):
    if not conds:
        return [('', '')]
    by_group = OrderedDict()
    for cond in conds:
        by_group.setdefault(cond.group_id, []).append(cond)
    columns = []
    for group in by_group.values():
        chemicals = [_format_condition(c) for c in group if c.condition_class == 'chemical']
        others = [_format_condition(c) for c in group if c.condition_class != 'chemical']
        columns.append((' | '.join(chemicals), ' | '.join(others)))
    return columns


@_register('interaction', 'Interactions',
           ['Feature Name (Bait)', 'Standard Gene Name (Bait)', 'Feature Name (Hit)', 'Standard Gene Name (Hit)',
            'Experiment Type', 'Genetic or Physical Interaction', 'Source', 'Manually curated or High-throughput',
            'Notes', 'Phenotype', 'Reference', 'Citation'],
           source_file='interaction_data.tab',
           description='Physical and genetic interactions (from BioGRID) involving the genes; '
                       'option interaction_scope="within" keeps only interactions between list genes')
def _interaction(ids, options):
    within = options.get('interaction_scope') == 'within'
    member = set(ids)
    out = []
    for kind, table, phenotype in (('physical interactions', 'physinteractionannotation', 'NULL'),
                                   ('genetic interactions', 'geninteractionannotation', 'p.display_name')):
        join = 'LEFT JOIN nex.phenotype p ON p.phenotype_id = a.phenotype_id ' if phenotype != 'NULL' else ''
        for r in _rows(
                "SELECT a.dbentity1_id, a.dbentity2_id, a.bait_hit, a.biogrid_experimental_system, "
                "       a.annotation_type, a.description, " + phenotype + " AS phenotype, "
                "       d.sgdid AS ref_sgdid, rd.pmid, rd.citation "
                "FROM nex." + table + " a " + join +
                "JOIN nex.dbentity d ON d.dbentity_id = a.reference_id "
                "JOIN nex.referencedbentity rd ON rd.dbentity_id = a.reference_id "
                "WHERE a.dbentity1_id = ANY(:ids) OR a.dbentity2_id = ANY(:ids)", ids):
            if within and not (r.dbentity1_id in member and r.dbentity2_id in member):
                continue
            bait, hit = r.dbentity1_id, r.dbentity2_id
            if r.bait_hit == 'Hit-Bait':
                bait, hit = hit, bait
            bait_names, hit_names = _names(bait), _names(hit)
            if not bait_names[0] or not hit_names[0]:
                continue
            out.append([bait_names[0], bait_names[1], hit_names[0], hit_names[1], r.biogrid_experimental_system,
                        kind, 'BioGRID', r.annotation_type, r.description or '', r.phenotype or '',
                        _reference(r.ref_sgdid, r.pmid), r.citation or ''])
    return out


@_register('regulation', 'Regulation',
           ['Regulator Standard Name', 'Regulator Systematic Name', 'Target Standard Name',
            'Target Systematic Name', 'Evidence', 'Regulator Type', 'Regulation Type', 'Direction',
            'Happens During', 'Strain Background', 'Reference'],
           source_file='regulation file',
           description='Regulator-target relationships where a list gene is the regulator or the target')
def _regulation(ids, options):
    complexes = _complex_names()
    out = []

    def names(dbentity_id):
        systematic_name, gene_name, _ = _names(dbentity_id)
        if systematic_name:
            return systematic_name, gene_name
        return complexes.get(dbentity_id, ('', ''))

    for r in _rows(
            "SELECT DISTINCT ON (ra.annotation_id) ra.regulator_id, ra.target_id, e.display_name AS evidence, "
            "       ra.regulator_type, ra.regulation_type, ra.direction, g.display_name AS happens_during, "
            "       ra.taxonomy_id, d.sgdid AS ref_sgdid, rd.pmid "
            "FROM nex.regulationannotation ra "
            "JOIN nex.eco e ON e.eco_id = ra.eco_id "
            "JOIN nex.dbentity d ON d.dbentity_id = ra.reference_id "
            "JOIN nex.referencedbentity rd ON rd.dbentity_id = ra.reference_id "
            "LEFT JOIN nex.go g ON g.go_id = ra.happens_during "
            "WHERE ra.regulator_id = ANY(:ids) OR ra.target_id = ANY(:ids) "
            "ORDER BY ra.annotation_id", ids):
        regulator, target = names(r.regulator_id), names(r.target_id)
        if not regulator[0] or not target[0]:
            continue
        out.append([regulator[1], regulator[0], target[1], target[0], r.evidence, r.regulator_type,
                    r.regulation_type, r.direction or '', r.happens_during or '', _strain(r.taxonomy_id),
                    _pmid(r.pmid, r.ref_sgdid)])
    return out


@_register('disease', 'Human disease',
           ['SGDID', 'Systematic Name', 'Gene Name', 'DOID', 'Disease Ontology Term', 'Evidence Code',
            'With', 'Reference'],
           source_file='yeast_human_disease file',
           description='Disease Ontology annotations of yeast genes with human disease models')
def _disease(ids, options):
    with_ids = {}
    for annotation_id, dbxref_id in _rows(
            "SELECT se.annotation_id, se.dbxref_id FROM nex.diseasesupportingevidence se "
            "JOIN nex.diseaseannotation da ON da.annotation_id = se.annotation_id "
            "WHERE da.dbentity_id = ANY(:ids)", ids):
        with_ids.setdefault(annotation_id, []).append(dbxref_id)
    out = []
    for r in _rows(
            "SELECT da.annotation_id, da.dbentity_id, dis.doid, dis.display_name AS term, e.ecoid, "
            "       d.sgdid AS ref_sgdid, rd.pmid "
            "FROM nex.diseaseannotation da "
            "JOIN nex.disease dis ON dis.disease_id = da.disease_id "
            "JOIN nex.eco e ON e.eco_id = da.eco_id "
            "JOIN nex.dbentity d ON d.dbentity_id = da.reference_id "
            "JOIN nex.referencedbentity rd ON rd.dbentity_id = da.reference_id "
            "WHERE da.dbentity_id = ANY(:ids)", ids):
        systematic_name, gene_name, sgdid = _names(r.dbentity_id)
        out.append([sgdid, systematic_name, gene_name, r.doid, r.term, r.ecoid,
                    '|'.join(with_ids.get(r.annotation_id, [])), _pmid(r.pmid, r.ref_sgdid)])
    return out


@_register('ptm', 'Post-translational modifications',
           ['SGDID', 'Systematic Name', 'Gene Name', 'Residue', 'Coordinate', 'Modification', 'PSI-MOD ID',
            'Modifier Systematic Name', 'Modifier Gene Name', 'Strain Background', 'Reference'],
           source_file='posttranslational_modifications.tab',
           description='Modification sites (phosphorylation, ubiquitination, ...) on the proteins')
def _ptm(ids, options):
    complexes = _complex_names()
    out = []
    for r in _rows(
            "SELECT pta.dbentity_id, pta.site_residue, pta.site_index, pta.modifier_id, "
            "       p.display_name AS modification, p.psimodid, pta.taxonomy_id, "
            "       d.sgdid AS ref_sgdid, rd.pmid "
            "FROM nex.posttranslationannotation pta "
            "JOIN nex.psimod p ON p.psimod_id = pta.psimod_id "
            "JOIN nex.dbentity d ON d.dbentity_id = pta.reference_id "
            "JOIN nex.referencedbentity rd ON rd.dbentity_id = pta.reference_id "
            "WHERE pta.dbentity_id = ANY(:ids)", ids):
        systematic_name, gene_name, sgdid = _names(r.dbentity_id)
        modifier = ('', '')
        if r.modifier_id:
            m = _names(r.modifier_id)
            modifier = (m[0], m[1]) if m[0] else complexes.get(r.modifier_id, ('', ''))
        out.append([sgdid, systematic_name, gene_name, r.site_residue, r.site_index, r.modification,
                    r.psimodid, modifier[0], modifier[1], _strain(r.taxonomy_id), _pmid(r.pmid, r.ref_sgdid)])
    out.sort(key=lambda row: (row[1], row[4]))
    return out


PROTEIN_PROPERTY_FIELDS = [
    ('Mw', 'molecular_weight'), ('PI', 'pi'), ('Protein Length', 'protein_length'),
    ('N_term_seq', 'n_term_seq'), ('C_term_seq', 'c_term_seq'), ('GRAVY Score', 'gravy_score'),
    ('Aromaticity Score', 'aromaticity_score'), ('CAI', 'cai'), ('Codon Bias', 'codon_bias'),
    ('FOP Score', 'fop_score')] + [
    (aa.capitalize(), aa) for aa in ['ala', 'cys', 'asp', 'glu', 'phe', 'gly', 'his', 'ile', 'lys', 'leu',
                                     'met', 'asn', 'pro', 'gln', 'arg', 'ser', 'thr', 'val', 'trp', 'tyr']] + [
    ('CARBON', 'carbon'), ('HYDROGEN', 'hydrogen'), ('NITROGEN', 'nitrogen'), ('OXYGEN', 'oxygen'),
    ('SULPHUR', 'sulfur'), ('INSTABILITY INDEX (II)', 'instability_index'),
    ('ASSUMING ALL CYS RESIDUES APPEAR AS HALF CYSTINES', 'all_cys_ext_coeff'),
    ('ASSUMING NO CYS RESIDUES APPEAR AS HALF CYSTINES', 'no_cys_ext_coeff'),
    ('ALIPHATIC INDEX', 'aliphatic_index')]


@_register('protein_properties', 'Protein properties',
           ['ORF', 'Gene Name'] + [label for label, _ in PROTEIN_PROPERTY_FIELDS],
           source_file='protein_properties.tab',
           description='Physico-chemical properties of the S288C reference proteins')
def _protein_properties(ids, options):
    out = []
    for r in _rows(
            "SELECT psa.dbentity_id, psd.* "
            "FROM nex.proteinsequenceannotation psa "
            "JOIN nex.proteinsequence_detail psd ON psd.annotation_id = psa.annotation_id "
            "JOIN nex.taxonomy t ON t.taxonomy_id = psa.taxonomy_id "
            "WHERE psa.dbentity_id = ANY(:ids) AND t.taxid = :taxid", ids, taxid=S288C_TAXID):
        systematic_name, gene_name, _ = _names(r.dbentity_id)
        row = r._mapping
        out.append([systematic_name, gene_name] + [row[field] for _, field in PROTEIN_PROPERTY_FIELDS])
    out.sort(key=lambda row: row[0])
    return out


@_register('protein_abundance', 'Protein abundance',
           ['Systematic Name', 'Gene Name', 'SGDID', 'Abundance', 'Unit', 'Median', 'Median Absolute Deviation',
            'Fold Change', 'Assay', 'Media', 'Chemical', 'Chemical Concentration', 'Time', 'Process',
            'Strain Background', 'Original Reference', 'Reference'],
           description='Protein abundance measurements (unified dataset of Ho et al. 2018 and others)')
def _protein_abundance(ids, options):
    out = []
    for r in _rows(
            "SELECT pa.dbentity_id, pa.data_value, pa.data_unit, pa.median_value, pa.median_abs_dev_value, "
            "       pa.fold_change, e.display_name AS assay, m.display_name AS media, c.display_name AS chemical, "
            "       pa.concentration_value, pa.concentration_unit, pa.time_value, pa.time_unit, "
            "       g.display_name AS process, pa.taxonomy_id, "
            "       od.sgdid AS orig_sgdid, ord.pmid AS orig_pmid, d.sgdid AS ref_sgdid, rd.pmid "
            "FROM nex.proteinabundanceannotation pa "
            "JOIN nex.eco e ON e.eco_id = pa.assay_id "
            "JOIN nex.efo m ON m.efo_id = pa.media_id "
            "JOIN nex.dbentity d ON d.dbentity_id = pa.reference_id "
            "JOIN nex.referencedbentity rd ON rd.dbentity_id = pa.reference_id "
            "JOIN nex.dbentity od ON od.dbentity_id = pa.original_reference_id "
            "JOIN nex.referencedbentity ord ON ord.dbentity_id = pa.original_reference_id "
            "LEFT JOIN nex.chebi c ON c.chebi_id = pa.chemical_id "
            "LEFT JOIN nex.go g ON g.go_id = pa.process_id "
            "WHERE pa.dbentity_id = ANY(:ids)", ids):
        concentration = ('%s %s' % (r.concentration_value, r.concentration_unit or '')).strip() \
            if r.concentration_value is not None else ''
        time = ('%s %s' % (r.time_value, r.time_unit or '')).strip() if r.time_value is not None else ''
        out.append(list(_names(r.dbentity_id)) + [
            r.data_value, r.data_unit, r.median_value, r.median_abs_dev_value, r.fold_change, r.assay,
            r.media, r.chemical or '', concentration, time, r.process or '', _strain(r.taxonomy_id),
            _pmid(r.orig_pmid, r.orig_sgdid), _pmid(r.pmid, r.ref_sgdid)])
    return out


@_register('complex', 'Complexes',
           ['Systematic Name', 'Gene Name', 'SGDID', 'Complex Accession', 'Complex Name', 'Stoichiometry'],
           description='Macromolecular complexes (Complex Portal) that the gene products belong to')
def _complex(ids, options):
    out = []
    for r in _rows(
            "SELECT DISTINCT i.locus_id, cd.complex_accession, d.display_name AS complex, cba.stoichiometry "
            "FROM nex.complexbindingannotation cba "
            "JOIN nex.interactor i ON i.interactor_id = cba.interactor_id "
            "JOIN nex.complexdbentity cd ON cd.dbentity_id = cba.complex_id "
            "JOIN nex.dbentity d ON d.dbentity_id = cba.complex_id "
            "WHERE i.locus_id = ANY(:ids)", ids):
        out.append(list(_names(r.locus_id)) + [r.complex_accession, r.complex,
                                               r.stoichiometry if r.stoichiometry is not None else ''])
    out.sort(key=lambda row: (row[0], row[3]))
    return out


@_register('pathway', 'Pathways',
           ['Systematic Name', 'Gene Name', 'SGDID', 'Pathway', 'BioCyc ID', 'EC Number', 'Reference'],
           description='YeastPathways (BioCyc) metabolic pathways the gene products participate in')
def _pathway(ids, options):
    out = []
    for r in _rows(
            "SELECT pa.dbentity_id, d.display_name AS pathway, pd.biocyc_id, ec.display_name AS ec, "
            "       rd.pmid, rdb.sgdid AS ref_sgdid "
            "FROM nex.pathwayannotation pa "
            "JOIN nex.dbentity d ON d.dbentity_id = pa.pathway_id "
            "JOIN nex.pathwaydbentity pd ON pd.dbentity_id = pa.pathway_id "
            "LEFT JOIN nex.ec ec ON ec.ec_id = pa.ec_id "
            "LEFT JOIN nex.referencedbentity rd ON rd.dbentity_id = pa.reference_id "
            "LEFT JOIN nex.dbentity rdb ON rdb.dbentity_id = pa.reference_id "
            "WHERE pa.dbentity_id = ANY(:ids)", ids):
        out.append(list(_names(r.dbentity_id)) + [r.pathway, r.biocyc_id, r.ec or '',
                                                  _pmid(r.pmid, r.ref_sgdid) if r.ref_sgdid else ''])
    out.sort(key=lambda row: (row[0], row[3]))
    return out


@_register('homolog', 'Homologs',
           ['Systematic Name', 'Gene Name', 'SGDID', 'Homolog ID', 'Homolog Name', 'Species', 'Source',
            'Description', 'URL'],
           description='Homologs in human, model organisms (Alliance), fission yeast (PomBase), '
                       'Candida (CGD) and other fungi (FungiDB); option homolog_species filters by species')
def _homolog(ids, options):
    species = options.get('homolog_species')
    out = []
    for r in _rows(
            "SELECT h.locus_id, h.gene_id, h.gene_name, t.display_name AS species, s.display_name AS source, "
            "       h.homolog_desc, h.obj_url "
            "FROM nex.locus_homology h "
            "JOIN nex.taxonomy t ON t.taxonomy_id = h.taxonomy_id "
            "JOIN nex.source s ON s.source_id = h.source_id "
            "WHERE h.locus_id = ANY(:ids)", ids):
        if species and r.species not in species:
            continue
        homolog_id = r.gene_id
        # Alliance rows store the bare number (1722); the URL has the prefixed ID (HGNC:1722)
        if r.source == 'Alliance' and r.obj_url and '/gene/' in r.obj_url:
            homolog_id = r.obj_url.rsplit('/gene/', 1)[1]
        out.append(list(_names(r.locus_id)) + [homolog_id, r.gene_name or '', r.species, r.source,
                                               r.homolog_desc or '', r.obj_url or ''])
    out.sort(key=lambda row: (row[0], row[5], row[3]))
    return out


@_register('literature', 'Literature',
           ['PubMed ID', 'Citation', 'Gene Name', 'Feature', 'Literature Topic', 'SGDID'],
           source_file='gene_literature.tab',
           description='Papers about the genes from the SGD Literature Guide, by topic')
def _literature(ids, options):
    out = []
    for r in _rows(
            "SELECT la.dbentity_id, rd.pmid, rd.citation, la.topic, rd.year "
            "FROM nex.literatureannotation la "
            "JOIN nex.referencedbentity rd ON rd.dbentity_id = la.reference_id "
            "WHERE la.dbentity_id = ANY(:ids)", ids):
        systematic_name, gene_name, sgdid = _names(r.dbentity_id)
        out.append([r.pmid or '', r.citation or '', gene_name, systematic_name, r.topic, sgdid,
                    r.year or 0])
    # newest first within each gene; the year is only used for sorting
    out.sort(key=lambda row: (row[3], -row[6], str(row[0])))
    return [row[:6] for row in out]


def list_annotation_types():
    return [{'key': key, 'label': t['label'], 'description': t['description'], 'columns': t['columns'],
             'source_file': t['source_file']} for key, t in ANNOTATION_TYPES.items()]


def get_list_annotations(body):
    """Entry point for POST /gene_list/annotations. body keys: data_type
    (required); bioent_ids or genes; interaction_scope ('any' or 'within');
    homolog_species (list of species names)."""
    data_type = body.get('data_type')
    if data_type not in ANNOTATION_TYPES:
        raise ValueError('data_type must be one of: %s' % ', '.join(ANNOTATION_TYPES))

    resolution = None
    if body.get('genes'):
        resolution = resolve_identifiers(body['genes'])
        gene_ids = resolution['resolved_ids']
    else:
        gene_ids = [int(x) for x in body.get('bioent_ids') or []]
    loci = get_lookup()[0]
    gene_ids = [i for i in OrderedDict.fromkeys(gene_ids) if i in loci]
    if not gene_ids:
        raise ValueError('No genes given: pass "bioent_ids" or "genes"')
    if len(gene_ids) > MAX_INPUT_IDENTIFIERS:
        raise ValueError('At most %d genes are allowed' % MAX_INPUT_IDENTIFIERS)
    if body.get('interaction_scope') not in (None, 'any', 'within'):
        raise ValueError('interaction_scope must be "any" or "within"')
    species = body.get('homolog_species')
    if species is not None and not isinstance(species, list):
        raise ValueError('homolog_species must be a list of species names')

    spec = ANNOTATION_TYPES[data_type]
    rows = spec['builder'](gene_ids, body)
    truncated = len(rows) > MAX_ROWS
    rows = [[_clean(v) for v in row] for row in rows[:MAX_ROWS]]
    out = {
        'data_type': data_type,
        'label': spec['label'],
        'source_file': spec['source_file'],
        'gene_count': len(gene_ids),
        'columns': spec['columns'],
        'row_count': len(rows),
        'truncated': truncated,
        'rows': rows,
    }
    if resolution is not None:
        out['resolution_summary'] = resolution['summary']
    return out


def annotations_to_tsv(result):
    lines = ['\t'.join(result['columns'])]
    for row in result['rows']:
        lines.append('\t'.join(str(v) for v in row))
    return '\n'.join(lines) + '\n'
