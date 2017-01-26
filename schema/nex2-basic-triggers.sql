-- Generated by Ora2Pg, the Oracle database Schema converter, version 17.4
-- Copyright 2000-2016 Gilles DAROLD. All rights reserved.
-- DATASOURCE: dbi:Oracle:host=sgd-nex2-db.stanford.edu;sid=SGD

SET client_encoding TO 'UTF8';

\set ON_ERROR_STOP ON

DROP TRIGGER IF EXISTS dbuser_aur ON nex.dbuser CASCADE;
CREATE OR REPLACE FUNCTION trigger_fct_dbuser_aur() RETURNS trigger AS $BODY$
BEGIN
  IF (TG_OP = 'UPDATE') THEN

    IF (OLD.username <> NEW.username) THEN
	PERFORM nex.insertupdatelog('DBUSER'::text, 'USERNAME'::text, OLD.dbuser_id, OLD.username, NEW.username, USER);
    END IF;

    IF (OLD.first_name <> NEW.first_name) THEN
        PERFORM nex.insertupdatelog('DBUSER'::text, 'FIRST_NAME'::text, OLD.dbuser_id, OLD.first_name, NEW.first_name, USER);
    END IF;

    IF (OLD.last_name <> NEW.last_name) THEN
	PERFORM nex.insertupdatelog('DBUSER'::text, 'LAST_NAME'::text, OLD.dbuser_id, OLD.last_name, NEW.last_name, USER);
    END IF;

    IF (OLD.status <> NEW.status) THEN
	PERFORM nex.insertupdatelog('DBUSER'::text, 'STATUS'::text, OLD.dbuser_id, OLD.status, NEW.status, USER);
    END IF;

    IF (OLD.is_curator <> NEW.is_curator) THEN
	PERFORM nex.insertupdatelog('DBUSER'::text, 'IS_CURATOR'::text, OLD.dbuser_id, OLD.is_curator::text, NEW.is_curator::text, USER);
    END IF;

    IF (OLD.email <> NEW.email) THEN
	PERFORM nex.insertupdatelog('DBUSER'::text, 'EMAIL'::text, OLD.dbuser_id, OLD.email, NEW.email, USER);
    END IF;

    RETURN NEW;
  END IF;

END;
$BODY$ LANGUAGE 'plpgsql';

CREATE TRIGGER dbuser_aur
AFTER UPDATE ON nex.dbuser FOR EACH ROW
EXECUTE PROCEDURE trigger_fct_dbuser_aur();

DROP TRIGGER IF EXISTS dbuser_biur ON nex.dbuser CASCADE;
CREATE OR REPLACE FUNCTION trigger_fct_dbuser_biur() RETURNS trigger AS $BODY$
BEGIN
  IF (TG_OP = 'INSERT') THEN

     NEW.username := UPPER(NEW.username);

     RETURN NEW;

  ELSIF (TG_OP = 'UPDATE') THEN

    IF (NEW.dbuser_id <> OLD.dbuser_id) THEN
            RAISE EXCEPTION 'Primary key cannot be updated';
    END IF;

    IF (NEW.date_created <> OLD.date_created) THEN
            RAISE EXCEPTION 'Audit columns cannot be updated.';
    END IF;

    RETURN NEW;
  END IF;

END;
$BODY$ LANGUAGE 'plpgsql';

CREATE TRIGGER dbuser_biur
BEFORE INSERT OR UPDATE ON nex.dbuser FOR EACH ROW
EXECUTE PROCEDURE trigger_fct_dbuser_biur();


DROP TRIGGER IF EXISTS source_audr ON nex.source CASCADE;
CREATE OR REPLACE FUNCTION trigger_fct_source_audr() RETURNS trigger AS $BODY$
DECLARE
    v_row       nex.deletelog.deleted_row%TYPE;
BEGIN
  IF (TG_OP = 'UPDATE') THEN

    IF (OLD.format_name <> NEW.format_name) THEN
        PERFORM nex.insertupdatelog('SOURCE'::text, 'FORMAT_NAME'::text, OLD.source_id, OLD.format_name, NEW.format_name, USER);
    END IF;

    IF (OLD.display_name <> NEW.display_name) THEN
        PERFORM nex.insertupdatelog('SOURCE'::text, 'DISPLAY_NAME'::text, OLD.source_id, OLD.display_name, NEW.display_name, USER);
    END IF;

    IF (((OLD.bud_id IS NULL) AND (NEW.bud_id IS NOT NULL)) OR ((OLD.bud_id IS NOT NULL) AND (NEW.bud_id IS NULL)) OR (OLD.bud_id <> NEW.bud_id)) THEN
        PERFORM nex.insertupdatelog('SOURCE'::text, 'BUD_ID'::text, OLD.source_id, OLD.bud_id::text, NEW.bud_id::text, USER);
    END IF;

    IF (((OLD.description IS NULL) AND (NEW.description IS NOT NULL)) OR ((OLD.description IS NOT NULL) AND (NEW.description IS NULL)) OR (OLD.description <> NEW.description)) THEN
        PERFORM nex.insertupdatelog('SOURCE'::text, 'DESCRIPTION'::text, OLD.source_id, OLD.description, NEW.description, USER);
    END IF;

    RETURN NEW;

  ELSIF (TG_OP = 'DELETE') THEN

    v_row := OLD.source_id || '[:]' || OLD.format_name || '[:]' ||
             OLD.display_name || '[:]' ||
             coalesce(OLD.bud_id,0) || '[:]' || coalesce(OLD.description,'') || '[:]' ||
             OLD.date_created || '[:]' || OLD.created_by;

    PERFORM nex.insertdeletelog('SOURCE'::text, OLD.source_id, v_row, USER);

    RETURN OLD;
  END IF;

END;
$BODY$ LANGUAGE 'plpgsql';

CREATE TRIGGER source_audr
AFTER UPDATE OR DELETE ON nex.source FOR EACH ROW
EXECUTE PROCEDURE trigger_fct_source_audr();

DROP TRIGGER IF EXISTS source_biur ON nex.source CASCADE;
CREATE OR REPLACE FUNCTION trigger_fct_source_biur() RETURNS trigger AS $BODY$
BEGIN
   IF (TG_OP = 'INSERT') THEN

       NEW.created_by := UPPER(NEW.created_by);
       PERFORM nex.checkuser(NEW.created_by);

       RETURN NEW;

   ELSIF (TG_OP = 'UPDATE') THEN

      IF (NEW.source_id <> OLD.source_id) THEN
          RAISE EXCEPTION 'Primary key cannot be updated';
      END IF;

      IF (NEW.date_created <> OLD.date_created) THEN
          RAISE EXCEPTION 'Audit columns cannot be updated.';
      END IF;

      IF (NEW.created_by <> OLD.created_by) THEN
          RAISE EXCEPTION 'Audit columns cannot be updated.';
      END IF;

      RETURN NEW;
   END IF;

END;
$BODY$ LANGUAGE 'plpgsql';

CREATE TRIGGER source_biur
BEFORE INSERT OR UPDATE ON nex.source FOR EACH ROW
EXECUTE PROCEDURE trigger_fct_source_biur();


DROP TRIGGER IF EXISTS sgdid_aur ON nex.sgdid CASCADE;
CREATE OR REPLACE FUNCTION trigger_fct_sgdid_aur() RETURNS trigger AS $BODY$
BEGIN
  IF (TG_OP = 'UPDATE') THEN

    IF (((OLD.bud_id IS NULL) AND (NEW.bud_id IS NOT NULL)) OR ((OLD.bud_id IS NOT NULL) AND (NEW.bud_id IS NULL)) OR (OLD.bud_id != NEW.bud_id)) THEN
        PERFORM nex.insertupdatelog('SGDID'::text, 'BUD_ID'::text, OLD.sgdid_id, OLD.bud_id::text, NEW.bud_id::text, USER);
    END IF;

    IF (OLD.sgdid_status != NEW.sgdid_status) THEN
        PERFORM nex.insertupdatelog('SGDID'::text, 'SGDID_STATUS'::text, OLD.sgdid_id, OLD.sgdid_status, NEW.sgdid_status, USER);
    END IF;

    IF (((OLD.description IS NULL) AND (NEW.description IS NOT NULL)) OR ((OLD.description IS NOT NULL) AND (NEW.description IS NULL)) OR (OLD.description != NEW.description)) THEN
        PERFORM nex.insertupdatelog('SGDID'::text, 'DESCRIPTION'::text, OLD.sgdid_id, OLD.description, NEW.description, USER);
    END IF;

    RETURN NEW;
  END IF;

END;
$BODY$ LANGUAGE 'plpgsql';

CREATE TRIGGER sgdid_aur
AFTER UPDATE ON nex.sgdid FOR EACH ROW
EXECUTE PROCEDURE trigger_fct_sgdid_aur();

DROP TRIGGER IF EXISTS sgdid_biur ON nex.sgdid CASCADE;
CREATE OR REPLACE FUNCTION trigger_fct_sgdid_biur() RETURNS trigger AS $BODY$
BEGIN
   IF (TG_OP = 'INSERT') THEN

       NEW.created_by := UPPER(NEW.created_by);
       PERFORM nex.checkuser(NEW.created_by);

       RETURN NEW;

  ELSIF (TG_OP = 'UPDATE') THEN

    IF (NEW.sgdid_id != OLD.sgdid_id) THEN
        RAISE EXCEPTION 'Primary key cannot be updated';
    END IF;

    IF (NEW.format_name != OLD.format_name) THEN
        RAISE EXCEPTION 'SGDID cannot be updated.';
    END IF;

    IF (NEW.display_name != OLD.display_name) THEN
        RAISE EXCEPTION 'SGDID cannot be updated.';
    END IF;

    IF (NEW.obj_url != OLD.obj_url) THEN
       RAISE EXCEPTION 'SGDID cannot be updated.';
    END IF;

    IF (NEW.source_id != OLD.source_id) THEN
        RAISE EXCEPTION 'SGDID cannot be updated.';
    END IF;

    IF (NEW.subclass != OLD.subclass) THEN
        RAISE EXCEPTION 'SGDID cannot be updated.';
    END IF;

    IF (NEW.date_created != OLD.date_created) THEN
        RAISE EXCEPTION 'Audit columns cannot be updated.';
    END IF;

    IF (NEW.created_by != OLD.created_by) THEN
        RAISE EXCEPTION 'Audit columns cannot be updated.';
    END IF;

    RETURN NEW;
  END IF;

END;
$BODY$ LANGUAGE 'plpgsql';

CREATE TRIGGER sgdid_biur
BEFORE INSERT OR UPDATE OR DELETE ON nex.sgdid FOR EACH ROW
EXECUTE PROCEDURE trigger_fct_sgdid_biur();
