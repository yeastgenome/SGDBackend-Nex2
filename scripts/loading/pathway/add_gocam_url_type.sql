-- redmine_6631 / Functional Networks: allow url_type = 'GO-CAM' in nex.pathway_url
-- so GO-CAM model links (http://model.geneontology.org/YeastPathways_<biocyc_id>)
-- can be stored alongside the existing BioCyc / YeastPathways links.
--
-- Run as the owner of nex.pathway_url (the application/otto role cannot ALTER it).
-- Source of truth for this constraint is schema/nex2-dbentity-tables.sql.

BEGIN;

ALTER TABLE nex.pathway_url DROP CONSTRAINT pathwayurl_type_ck;
ALTER TABLE nex.pathway_url ADD CONSTRAINT pathwayurl_type_ck
    CHECK (url_type IN ('BioCyc', 'YeastPathways', 'GO-CAM'));

COMMIT;

-- verify:
-- SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'pathwayurl_type_ck';
