import os
from datetime import datetime
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import dbentity_id_to_data_mapping, \
    dbentity_id_feature_type_mapping, reference_id_to_data_mapping, \
    phenotype_id_to_phenotype_mapping, taxonomy_id_to_strain_mapping, \
    annotation_id_to_conds_mapping

__author__ = 'sweng66'

## Reconstructed 2026-08 (the original was lost in the 2026-02 server migration:
## it was only ever an untracked file on the old host, though its helpers --
## annotation_id_to_conds_mapping, phenotype_id_to_phenotype_mapping,
## reference_id_to_data_mapping, taxonomy_id_to_strain_mapping -- were committed
## in this package's __init__.py). Column layout follows phenotype_data.README
## and was validated against the last file the old pipeline produced
## (phenotype_data.tab, 2026-02-14, on sgd-archive).

phenotypeFile = "scripts/dumping/tab_files_for_download_site/data/phenotype_data.tab"

## Refuse to publish a file that looks truncated (DB hiccup mid-run). The
## 2026-02-14 file has 200,084 rows; curation only adds to that.
MIN_ROWS = 180000


def dump_data():

    """
    1)  Feature Name (Mandatory)                    - systematic name
    2)  Feature Type (Mandatory)
    3)  Gene Name (Optional)                        - standard (gene) name
    4)  SGDID (Mandatory)
    5)  Reference (SGD_REF required, PMID optional) - SGD_REF: ####|PMID: ####
    6)  Experiment Type (Mandatory)                 - apo (experiment)
    7)  Mutant Type (Mandatory)                     - apo (mutant)
    8)  Allele (Optional)
    9)  Strain Background (Optional)
    10) Phenotype (Mandatory)                       - observable: qualifier
    11) Chemical (Optional)
    12) Condition (Optional)
    13) Details (Optional)
    14) Reporter (Optional)

    One row per reference per condition group: an annotation whose conditions
    fall into several group_ids describes several experiments and becomes
    several rows (matching the website's phenotype details display).
    """

    print(datetime.now())
    print("Generating phenotype_data.tab file...")

    nex_session = get_session()

    locus_id_to_data = dbentity_id_to_data_mapping(nex_session)
    locus_id_to_feature_type = dbentity_id_feature_type_mapping(nex_session)
    reference_id_to_data = reference_id_to_data_mapping(nex_session)
    phenotype_id_to_phenotype = phenotype_id_to_phenotype_mapping(nex_session)
    taxonomy_id_to_strain = taxonomy_id_to_strain_mapping(nex_session)
    annotation_id_to_conds = annotation_id_to_conds_mapping(nex_session)

    rows = nex_session.execute("SELECT pa.annotation_id, pa.dbentity_id, pa.reference_id, "
                               "       pa.phenotype_id, pa.taxonomy_id, pa.details, "
                               "       e.display_name AS experiment, m.display_name AS mutant, "
                               "       ad.display_name AS allele, r.display_name AS reporter "
                               "FROM nex.phenotypeannotation pa "
                               "JOIN nex.apo e ON pa.experiment_id = e.apo_id "
                               "JOIN nex.apo m ON pa.mutant_id = m.apo_id "
                               "LEFT JOIN nex.dbentity ad ON pa.allele_id = ad.dbentity_id "
                               "LEFT JOIN nex.reporter r ON pa.reporter_id = r.reporter_id").fetchall()

    print("Writing data to the temp file...")

    tmpFile = phenotypeFile + ".tmp"
    fw = open(tmpFile, "w")

    row_count = 0
    lines = []
    for x in rows:
        if x['dbentity_id'] not in locus_id_to_data:
            ## deleted/merged/inactive feature
            continue
        (sgdid, systematic_name, gene_name, _qualifier, _genetic_position, _desc) = \
            locus_id_to_data[x['dbentity_id']]
        feature_type = locus_id_to_feature_type.get(x['dbentity_id'], '')
        if x['reference_id'] not in reference_id_to_data:
            continue
        (reference, _citation) = reference_id_to_data[x['reference_id']]
        phenotype = phenotype_id_to_phenotype.get(x['phenotype_id'], '')
        strain = taxonomy_id_to_strain.get(x['taxonomy_id'], '')

        prefix = [systematic_name, feature_type, gene_name if gene_name else '',
                  sgdid, reference, x['experiment'], x['mutant'],
                  x['allele'] if x['allele'] else '', strain, phenotype]
        suffix = [x['details'] if x['details'] else '',
                  x['reporter'] if x['reporter'] else '']

        for (chemical, condition) in group_conditions(annotation_id_to_conds.get(x['annotation_id'])):
            fields = [clean_field(field) for field in prefix + [chemical, condition] + suffix]
            lines.append("\t".join(fields) + "\n")
            row_count += 1

    ## the historical file is ordered by feature name; keep rows for a gene together
    for line in sorted(lines):
        fw.write(line)
    fw.close()
    nex_session.close()

    if row_count < MIN_ROWS:
        print("ERROR: only " + str(row_count) + " rows generated (< " + str(MIN_ROWS) +
              "); keeping the previous " + phenotypeFile)
        os.remove(tmpFile)
        return

    os.replace(tmpFile, phenotypeFile)

    print("Total " + str(row_count) + " rows written to " + phenotypeFile)
    print(datetime.now())
    print("DONE!")


def clean_field(text):

    """A handful of details/condition values in the database contain literal
    newlines or tabs; the original (lost) script wrote them through, breaking
    the row structure for ~77 rows. Collapse them to single spaces instead."""

    return " ".join(text.split()) if text else ''


def format_condition(cond):

    """A condition renders as 'name (value+unit)' -- e.g. 'doxycycline (10ug/ml)',
    'elevated temperature (37°C)', value and unit concatenated without a space,
    matching the historical file -- or just 'name' when it carries no value."""

    name = cond.condition_name.strip()
    if cond.condition_value:
        value = cond.condition_value.strip()
        if cond.condition_unit:
            value = value + cond.condition_unit.strip()
        return name + " (" + value + ")"
    return name


def group_conditions(conds):

    """Turn an annotation's conditions into [(chemical, condition)] per condition
    group: chemicals (condition_class 'chemical') go to the Chemical column, all
    other classes to the Condition column, each ' | '-joined within the group.
    An annotation without conditions yields one row with both columns empty."""

    if not conds:
        return [("", "")]

    by_group = {}
    for cond in conds:
        by_group.setdefault(cond.group_id, []).append(cond)

    columns = []
    for group_id in sorted(by_group.keys()):
        chemicals = []
        others = []
        for cond in by_group[group_id]:
            if cond.condition_class == 'chemical':
                chemicals.append(format_condition(cond))
            else:
                others.append(format_condition(cond))
        columns.append((" | ".join(chemicals), " | ".join(others)))
    return columns


if __name__ == '__main__':

    dump_data()
