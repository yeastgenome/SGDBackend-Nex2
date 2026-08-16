import os
from datetime import datetime
from scripts.loading.database_session import get_session
from scripts.dumping.tab_files_for_download_site import dbentity_id_to_data_mapping, \
    taxonomy_id_to_strain_mapping

__author__ = 'sweng66'

## Reconstructed 2026-08 (like generate_phenotype_file.py, the original was
## lost in the 2026-02 server migration: it only ever existed as an untracked
## file on the old host). Column layout follows
## posttranslational_modifications.README and was validated against the last
## file the old pipeline produced (2026-02-14, on sgd-archive).

ptmFile = "scripts/dumping/tab_files_for_download_site/data/posttranslational_modifications.tab"

## Refuse to publish a file that looks truncated (DB hiccup mid-run). The
## 2026-02-14 file has ~155k data rows; curation only adds to that.
MIN_ROWS = 140000

HEADER = "SGDID\tSystematic name\tGene name\tResidue\tCoordinate\tModification\t" + \
         "PSI-MOD ID\tModifier Systematic name\tModifier gene name\tStrain background\tPMID"


def dump_data():

    """
    1)  SGDID
    2)  Systematic name
    3)  Gene name
    4)  Residue                  - site_residue
    5)  Coordinate               - site_index
    6)  Modification             - psimod.display_name
    7)  PSI-MOD ID               - psimod.psimodid
    8)  Modifier Systematic name - locus systematic name, or complex accession (CPX-####)
    9)  Modifier gene name       - locus gene name, or the complex's aliases '|'-joined
    10) Strain background
    11) PMID                     - PMID:#### (SGD_REF:#### when a reference has no pmid)
    """

    print(datetime.now())
    print("Generating posttranslational_modifications.tab file...")

    nex_session = get_session()

    locus_id_to_data = dbentity_id_to_data_mapping(nex_session)
    taxonomy_id_to_strain = taxonomy_id_to_strain_mapping(nex_session)
    complex_id_to_names = complex_id_to_names_mapping(nex_session)
    reference_id_to_pmid = reference_id_to_pmid_mapping(nex_session)

    rows = nex_session.execute("SELECT pta.dbentity_id, pta.reference_id, pta.taxonomy_id, "
                               "       pta.site_residue, pta.site_index, pta.modifier_id, "
                               "       p.display_name AS modification, p.psimodid "
                               "FROM nex.posttranslationannotation pta "
                               "JOIN nex.psimod p ON pta.psimod_id = p.psimod_id").fetchall()

    print("Writing data to the temp file...")

    tmpFile = ptmFile + ".tmp"
    fw = open(tmpFile, "w")
    fw.write(HEADER + "\n")

    row_count = 0
    lines = []
    for x in rows:
        if x['dbentity_id'] not in locus_id_to_data:
            ## deleted/merged/inactive feature
            continue
        (sgdid, systematic_name, gene_name, _qualifier, _genetic_position, _desc) = \
            locus_id_to_data[x['dbentity_id']]
        if x['reference_id'] not in reference_id_to_pmid:
            continue
        reference = reference_id_to_pmid[x['reference_id']]
        strain = taxonomy_id_to_strain.get(x['taxonomy_id'], '')

        modifier_name = ''
        modifier_gene_name = ''
        if x['modifier_id']:
            if x['modifier_id'] in locus_id_to_data:
                (_m_sgdid, modifier_name, m_gene_name, _q, _g, _d) = locus_id_to_data[x['modifier_id']]
                modifier_gene_name = m_gene_name if m_gene_name else ''
            elif x['modifier_id'] in complex_id_to_names:
                (modifier_name, modifier_gene_name) = complex_id_to_names[x['modifier_id']]

        lines.append((systematic_name, x['site_index'],
                      sgdid + "\t" + systematic_name + "\t" +
                      (gene_name if gene_name else '') + "\t" +
                      x['site_residue'] + "\t" + str(x['site_index']) + "\t" +
                      x['modification'] + "\t" + x['psimodid'] + "\t" +
                      modifier_name + "\t" + modifier_gene_name + "\t" +
                      strain + "\t" + reference + "\n"))
        row_count += 1

    for (_name, _index, line) in sorted(lines):
        fw.write(line)
    fw.close()
    nex_session.close()

    if row_count < MIN_ROWS:
        print("ERROR: only " + str(row_count) + " rows generated (< " + str(MIN_ROWS) +
              "); keeping the previous " + ptmFile)
        os.remove(tmpFile)
        return

    os.replace(tmpFile, ptmFile)

    print("Total " + str(row_count) + " rows written to " + ptmFile)
    print(datetime.now())
    print("DONE!")


def complex_id_to_names_mapping(nex_session):

    """Map a complex dbentity_id to (complex_accession, aliases) where aliases
    are all of the complex's complex_alias display names '|'-joined in alias_id
    order -- e.g. ('CPX-1688', 'PHO80-PHO85 complex|2.7.11.22|2PK9|2PMI') --
    matching how the historical file rendered complex modifiers."""

    rows = nex_session.execute("SELECT cd.dbentity_id, cd.complex_accession, ca.display_name "
                               "FROM nex.complexdbentity cd "
                               "LEFT JOIN nex.complex_alias ca ON ca.complex_id = cd.dbentity_id "
                               "ORDER BY cd.dbentity_id, ca.alias_id").fetchall()
    complex_id_to_names = {}
    for x in rows:
        (accession, aliases) = complex_id_to_names.get(x['dbentity_id'], (x['complex_accession'], []))
        if x['display_name']:
            aliases.append(x['display_name'])
        complex_id_to_names[x['dbentity_id']] = (accession, aliases)
    return dict([(dbentity_id, (accession, "|".join(aliases)))
                 for dbentity_id, (accession, aliases) in complex_id_to_names.items()])


def reference_id_to_pmid_mapping(nex_session):

    """Map a reference dbentity_id to 'PMID:####' (every reference in the
    historical file has one), falling back to 'SGD_REF:<sgdid>' just in case."""

    rows = nex_session.execute("SELECT d.dbentity_id, d.sgdid, rd.pmid "
                               "FROM nex.dbentity d, nex.referencedbentity rd "
                               "WHERE d.subclass = 'REFERENCE' "
                               "AND d.dbentity_status = 'Active' "
                               "AND d.dbentity_id = rd.dbentity_id").fetchall()
    reference_id_to_pmid = {}
    for x in rows:
        if x['pmid']:
            reference_id_to_pmid[x['dbentity_id']] = "PMID:" + str(x['pmid'])
        else:
            reference_id_to_pmid[x['dbentity_id']] = "SGD_REF:" + x['sgdid']
    return reference_id_to_pmid


if __name__ == '__main__':

    dump_data()
