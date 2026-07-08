# CGD orf19 -> A22 systematic name update

C. albicans genes were historically identified by Assembly 19 ids (`orf19.xxxx`)
and linked to CGD with the old CGI url, e.g.:

    http://www.candidagenome.org/cgi-bin/locus.pl?locus=orf19.5908

These ids/links are migrated to the current Assembly 22 (A22) systematic names
and the current CGD locus url, e.g.:

    orf19.5908  ->  C3_04530C_A
    http://www.candidagenome.org/cgi-bin/locus.pl?locus=orf19.5908
        -> https://www.candidagenome.org/locus/C3_04530C_A

## Files

- `data/orf19_to_a22_mapping.txt` - tab-delimited mapping
  (`orf19_id`, `a22_systematic_name`, `gene_name`, `other_alleles`).
- `update_orf19_to_a22.py` - applies the mapping to the SGD (nex) database.

## What the script updates

The mapping covers every orf19 id found in the SGD database (the union across
all of the tables below). The script rewrites both the embedded CGD obj_url and
the orf19 identifier itself where it is stored:

| Table                              | Identifier column        | obj_url |
|------------------------------------|--------------------------|---------|
| `nex.locus_url`                    | (link only)              | yes     |
| `nex.locus_alias`                  | `display_name`           | yes     |
| `nex.locus_homology` (Homologs tab)| `gene_id`                | yes     |
| `nex.functionalcomplementannotation` | `dbxref_id` (`CGD:...`)| yes     |

Each update checks the table's unique constraint first; if an A22 row already
exists it is logged and skipped. Re-running is safe (rows already in the new
form are left untouched).

## How the mapping file was generated

The orf19 -> A22 relationship lives in the CGD Oracle database (not in SGD),
in the `feat_relationship` table:

    relationship_type = 'Assembly 21 Primary Allele'  and  rank = 3
    parent_feature_no -> A22 feature (systematic name, the primary _A allele)
    child_feature_no  -> orf19 feature

This is the same relationship the cgd-backend uses (see
`cgd/api/services/locus_service.py` and
`cgd/api/services/ortholog_converter_service.py`). The mapping was produced by
collecting the union of orf19 ids from the SGD tables above and resolving each
against that relationship in the CGD database.

## Running

    # default: applies and commits the changes
    python scripts/loading/CGD/update_orf19_to_a22.py

    # log only, no changes committed
    python scripts/loading/CGD/update_orf19_to_a22.py --dry-run

A detailed per-row log is written to `scripts/loading/CGD/logs/`.
