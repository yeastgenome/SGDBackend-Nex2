-- redmine_6631 / Functional Networks: allow alias_type = 'GO-CAM' in
-- nex.complex_alias so a complex can be linked to the GO-CAM model(s) that
-- annotate it (object SGD:<complex_sgdid>, label 'CPX-xxxx'). Stored the same
-- way as the existing PDB / EMDB external-resource links: alias_type='GO-CAM',
-- obj_url='http://model.geneontology.org/YeastPathways_<biocyc_id>'.
--
-- Run as the owner of nex.complex_alias (the application/otto role cannot ALTER
-- it). Source of truth for this constraint is the nex2 schema definition.

BEGIN;

ALTER TABLE nex.complex_alias DROP CONSTRAINT complexalias_type_ck;
ALTER TABLE nex.complex_alias ADD CONSTRAINT complexalias_type_ck
    CHECK (alias_type IN ('Synonym', 'IntEnz', 'PDB', 'EMDB', 'GO-CAM'));

COMMIT;

-- verify:
-- SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'complexalias_type_ck';
