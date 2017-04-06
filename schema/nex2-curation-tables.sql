-- Generated by Ora2Pg, the Oracle database Schema converter, version 17.4
-- Copyright 2000-2016 Gilles DAROLD. All rights reserved.
-- DATASOURCE: dbi:Oracle:host=sgd-nex2-db.stanford.edu;sid=SGD

SET client_encoding TO 'UTF8';

\set ON_ERROR_STOP ON

-- Curation tables

DROP TABLE IF EXISTS nex.curation_locus CASCADE;
CREATE TABLE nex.curation_locus (
	curation_id bigint NOT NULL DEFAULT nextval('curation_seq'),
	locus_id bigint NOT NULL,
	source_id bigint NOT NULL,
	curation_tag varchar(40) NOT NULL,
	date_created timestamp NOT NULL DEFAULT LOCALTIMESTAMP,
	created_by varchar(12) NOT NULL,
    curator_comment varchar(2000),
    json text,
	CONSTRAINT curation_pk PRIMARY KEY (curation_id)
) ;
COMMENT ON TABLE nex.curation_locus IS 'Tags and notes associated with locus curation.';
COMMENT ON COLUMN nex.curation_locus.curator_comment IS 'Comment or note.';
COMMENT ON COLUMN nex.curation_locus.locus_id IS 'FK to LOCUSDBENTITY.DBENTITY_ID.';
COMMENT ON COLUMN nex.curation_locus.curation_id IS 'Unique identifier (serial number).';
COMMENT ON COLUMN nex.curation_locus.source_id IS 'FK to SOURCE.SOURCE_ID.';
COMMENT ON COLUMN nex.curation_locus.created_by IS 'Username of the person who entered the record into the database.';
COMMENT ON COLUMN nex.curation_locus.date_created IS 'Date the record was entered into the database.';
COMMENT ON COLUMN nex.curation_locus.curation_tag IS 'Type of curation tag (GO needs review, Headline reviewed, Paragraph not needed, Phenotype uncuratable).';
COMMENT ON COLUMN nex.curation_locus.json IS 'JSON object of locus curation data.'; 
CREATE UNIQUE INDEX curation_uk_index on nex.curation_locus (locus_id,curation_tag);
ALTER TABLE nex.curation_locus ADD CONSTRAINT curation_tag_ck CHECK (CURATION_TAG IN ('GO needs review','Headline reviewed','Paragraph not needed','Phenotype uncuratable'));
CREATE INDEX curation_source_fk_index ON nex.curation_locus (source_id);

DROP TABLE IF EXISTS nex.curation_reference CASCADE;
CREATE TABLE nex.curation_reference (
    curation_id bigint NOT NULL DEFAULT nextval('curation_seq'),
    reference_id bigint NOT NULL,
    source_id bigint NOT NULL,
    locus_id bigint,
    curation_tg varchar(40) NOT NULL,
    date_created timestamp NOT NULL DEFAULT LOCALTIMESTAMP,
    created_by varchar(12) NOT NULL,
    curator_comment varchar(2000),
    json text,
    CONSTRAINT curation_pk PRIMARY KEY (curation_id)
) ;
COMMENT ON TABLE nex.curation_reference IS 'Tags and notes associated with reference curation.';
COMMENT ON COLUMN nex.curation_reference.curator_comment IS 'Comment or note.';
COMMENT ON COLUMN nex.curation_reference.reference_id IS 'FK to REFERENCEDBENTITY.DBENTITY_ID.';
COMMENT ON COLUMN nex.curation_reference.locus_id IS 'FK to LOCUSDBENTITY.DBENTITY_ID.';
COMMENT ON COLUMN nex.curation_reference.curation_id IS 'Unique identifier (serial number).';
COMMENT ON COLUMN nex.curation_reference.source_id IS 'FK to SOURCE.SOURCE_ID.';
COMMENT ON COLUMN nex.curation_reference.created_by IS 'Username of the person who entered the record into the database.';
COMMENT ON COLUMN nex.curation_reference.date_created IS 'Date the record was entered into the database.';
COMMENT ON COLUMN nex.curation_reference.curation_task IS 'Type of curation task (Classical phenotype information,Delay,Fast Track,GO information,Gene model,Headline needs review,Headline information,High Priority,Homology/Disease,HTP phenotype,Non-phenotype HTP,Not yet curated,Paragraph needs review,Pathways,Phenotype needs review,Post-translational modifications,Regulation information).';
COMMENT ON COLUMN nex.curation_reference.json IS 'JSON object of reference curation data.';
CREATE UNIQUE INDEX curation_uk_index on nex.curation_reference (reference_id,curation_tag,coalesce(locus_id,0));
ALTER TABLE nex.curation_reference ADD CONSTRAINT curation_tag_ck CHECK (CURATION_TAG IN ('Classical phenotype information','Delay','Fast Track','GO information','Gene model','Headline needs review','Headline information','High Priority','Homology/Disease','HTP phenotype','Non-phenotype HTP','Not yet curated','Paragraph needs review','Pathways','Phenotype needs review','Post-translational modifications','Regulation information'));
CREATE INDEX curation_locus_fk_index ON nex.curation_reference (locus_id);
CREATE INDEX curation_source_fk_index ON nex.curation_reference (source_id);


DROP TABLE IF EXISTS nex.authorresponse CASCADE;
CREATE TABLE nex.authorresponse (
	curation_id bigint NOT NULL DEFAULT nextval('curation_seq'),
	reference_id bigint NOT NULL,
	source_id bigint NOT NULL,
	colleague_id bigint,
	author_email varchar(100) NOT NULL,
	has_novel_research boolean NOT NULL,
	has_large_scale_data boolean NOT NULL,
	has_fast_track_tag boolean NOT NULL,
	curator_checked_datasets boolean NOT NULL,
	curator_checked_genelist boolean NOT NULL,
	no_action_required boolean NOT NULL,
	research_results text,
	gene_list varchar(4000),
	dataset_description varchar(4000),
	other_description varchar(4000),
	date_created timestamp NOT NULL DEFAULT LOCALTIMESTAMP,
	created_by varchar(12) NOT NULL,
	CONSTRAINT authorresponse_pk PRIMARY KEY (curation_id)
) ;
COMMENT ON TABLE nex.authorresponse IS 'Replies from the Author Reponse System.';
COMMENT ON COLUMN nex.authorresponse.has_large_scale_data IS 'Whether there is large scale data in the paper.';
COMMENT ON COLUMN nex.authorresponse.created_by IS 'Username of the person who entered the record into the database.';
COMMENT ON COLUMN nex.authorresponse.no_action_required IS 'Whether any further action is needed.';
COMMENT ON COLUMN nex.authorresponse.gene_list IS 'List of gene names contained in the paper submitted by the author.';
COMMENT ON COLUMN nex.authorresponse.date_created IS 'Date the record was entered into the database.';
COMMENT ON COLUMN nex.authorresponse.has_novel_research IS 'Whether there is novel research in the paper.';
COMMENT ON COLUMN nex.authorresponse.has_fast_track_tag IS 'Whether a fast track tag has been attached to this paper.';
COMMENT ON COLUMN nex.authorresponse.curation_id IS 'Unique identifier (serial number).';
COMMENT ON COLUMN nex.authorresponse.author_email IS 'Email address of the author.';
COMMENT ON COLUMN nex.authorresponse.research_results IS 'Research results submitted by the author.';
COMMENT ON COLUMN nex.authorresponse.dataset_description IS 'Description of the dataset submitted by the author.';
COMMENT ON COLUMN nex.authorresponse.source_id IS 'FK to SOURCE.SOURCE_ID.';
COMMENT ON COLUMN nex.authorresponse.curator_checked_datasets IS 'Whether a curator has checked the datasets in the paper.';
COMMENT ON COLUMN nex.authorresponse.colleague_id IS 'FK to COLLEAGUE.COLLEAGUE_ID.';
COMMENT ON COLUMN nex.authorresponse.other_description IS 'Any other description submitted by the author.';
COMMENT ON COLUMN nex.authorresponse.reference_id IS 'FK to REFERENCEDBENTITY.DBENTITY_ID.';
COMMENT ON COLUMN nex.authorresponse.curator_checked_genelist IS 'Whether a curator has checked the submitted gene list.';
ALTER TABLE nex.authorresponse ADD CONSTRAINT authorresponse_uk UNIQUE (reference_id);
CREATE INDEX authorresponse_coll_fk_index ON nex.authorresponse (colleague_id);
CREATE INDEX authorresponse_source_fk_index ON nex.authorresponse (source_id);

DROP TABLE IF EXISTS nex.referencetriage CASCADE;
CREATE TABLE nex.referencetriage (
	curation_id bigint NOT NULL DEFAULT nextval('curation_seq'),
	pmid bigint NOT NULL,
	citation varchar(500) NOT NULL,
	fulltext_url varchar(500),
    abstract_genes varchar(500),
	abstract text,
    json text,
	date_created timestamp NOT NULL DEFAULT LOCALTIMESTAMP,
	created_by varchar(12) NOT NULL,
	CONSTRAINT referencetriage_pk PRIMARY KEY (curation_id)
) ;
COMMENT ON TABLE nex.referencetriage IS 'Papers obtained via the reference triage system.';
COMMENT ON COLUMN nex.referencetriage.abstract IS 'Paper abstract.';
COMMENT ON COLUMN nex.referencetriage.created_by IS 'Username of the person who entered the record into the database.';
COMMENT ON COLUMN nex.referencetriage.fulltext_url IS 'URL to the fulltext of the paper.';
COMMENT ON COLUMN nex.referencetriage.abstract_genes IS 'Comma separated list of gene or systematic names identified in the abstract.';
COMMENT ON COLUMN nex.referencetriage.date_created IS 'Date the record was entered into the database.';
COMMENT ON COLUMN nex.referencetriage.citation IS 'Full citation of the paper.';
COMMENT ON COLUMN nex.referencetriage.curation_id IS 'Unique identifier (serial number).';
COMMENT ON COLUMN nex.referencetriage.pmid IS 'Pubmed identifier for the paper.';
COMMENT ON COLUMN nex.referencetriage.json IS 'JSON object of the reference data.';
ALTER TABLE nex.referencetriage ADD CONSTRAINT referencetriage_uk UNIQUE (pmid);

DROP TABLE IF EXISTS nex.colleaguetriage CASCADE;
CREATE TABLE nex.colleaguetriage (
	curation_id bigint NOT NULL DEFAULT nextval('curation_seq'),
	triage_type varchar(10) NOT NULL,
    colleague_id bigint,
    json text NOT NULL,
    curator_comment varchar(500),
    date_created timestamp NOT NULL DEFAULT LOCALTIMESTAMP,
	created_by varchar(12) NOT NULL,
	CONSTRAINT colleaguetriage_pk PRIMARY KEY (curation_id)
) ;
COMMENT ON TABLE nex.colleaguetriage IS 'New and update colleague submissions.';
COMMENT ON COLUMN nex.colleaguetriage.colleague_id IS 'FK to COLLEAGUE.COLLEAGUE_ID.';
COMMENT ON COLUMN nex.colleaguetriage.triage_type IS 'Type of colleague submission (New, Update, Stalled).';
COMMENT ON COLUMN nex.colleaguetriage.created_by IS 'Username of the person who entered the record into the database.';
COMMENT ON COLUMN nex.colleaguetriage.json IS 'JSON object of the colleague data.';
COMMENT ON COLUMN nex.colleaguetriage.date_created IS 'Date the record was entered into the database.';
COMMENT ON COLUMN nex.colleaguetriage.curation_id IS 'Unique identifier (serial number).';
COMMENT ON COLUMN nex.colleaguetriage.curator_comment IS 'Notes or comments about this colleague entry by the curators.';
ALTER TABLE nex.colleaguetriage ADD CONSTRAINT colleagetriage_type_ck CHECK (TRIAGE_TYPE IN ('New', 'Update', 'Stalled'));
