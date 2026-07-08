"""Update Candida albicans orf19 identifiers to Assembly 22 (A22) systematic names.

The historical C. albicans Assembly 19 identifiers (orf19.xxxx) are stored in
several SGD tables, both as the identifier itself and embedded in CGD obj_url
links of the old form:

    http://www.candidagenome.org/cgi-bin/locus.pl?locus=orf19.5908

This script uses the orf19 -> A22 mapping file produced from the CGD database
(scripts/loading/CGD/data/orf19_to_a22_mapping.txt) to:

  1. Rewrite every CGD obj_url to the current form, e.g.
        http://www.candidagenome.org/cgi-bin/locus.pl?locus=orf19.5908
     becomes
        https://www.candidagenome.org/locus/C3_04530C_A
  2. Replace the orf19.xxxx identifier with its A22 systematic name everywhere
     it is stored as an identifier:
        - nex.locus_url.obj_url                       (External id / CGD link)
        - nex.locus_alias.display_name + obj_url      (alias_type 'Gene ID')
        - nex.locus_homology.gene_id + obj_url        (Homologs tab)
        - nex.functionalcomplementannotation.dbxref_id + obj_url

The mapping covers every orf19 ID that appears in the SGD database (the union
across all four tables). Each table update checks the relevant unique
constraint before writing so an already-existing A22 row is not duplicated;
such rows are logged and skipped. The script is idempotent: rows whose obj_url
is already in the new /locus/ form (or whose identifier is already an A22 name)
are left untouched.

Usage:
    python scripts/loading/CGD/update_orf19_to_a22.py [mapping_file]

By default the script commits its changes. Set DRY_RUN = True (or pass the
--dry-run flag) to roll back instead and only write the log file.

__author__ = 'sweng66'
"""
import logging
import os
import re
import sys

from sqlalchemy import text, bindparam

from src.models import LocusUrl, LocusAlias, Functionalcomplementannotation
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

DEFAULT_MAPPING_FILE = "scripts/loading/CGD/data/orf19_to_a22_mapping.txt"
LOGFILE = "scripts/loading/CGD/logs/update_orf19_to_a22.log"

# New CGD locus link, e.g. https://www.candidagenome.org/locus/C3_04530C_A
NEW_URL_PREFIX = "https://www.candidagenome.org/locus/"

# Matches the orf19 identifier embedded in an old CGD obj_url, e.g.
# .../locus.pl?locus=orf19.5908  or  .../locus.pl?locus=orf19.1082.1
ORF19_URL_RE = re.compile(r"locus=(orf19\.[0-9]+(?:\.[0-9]+)?)")

# Commit changes when False; roll back (log only) when True.
DRY_RUN = False

# Commit every COMMIT_EVERY processed rows to keep transactions small.
COMMIT_EVERY = 500

# Print a progress line every PROGRESS_EVERY scanned rows within a table.
PROGRESS_EVERY = 1000


def load_mapping(mapping_file):
    """Return {orf19_id: a22_systematic_name} from the tab-delimited file."""
    mapping = {}
    with open(mapping_file) as fh:
        header = fh.readline()  # orf19_id  a22_systematic_name  gene_name  other_alleles
        if not header.lower().startswith("orf19"):
            # No header line - rewind and treat the first line as data.
            fh.seek(0)
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            pieces = line.split("\t")
            orf19_id = pieces[0].strip()
            a22_name = pieces[1].strip() if len(pieces) > 1 else ""
            if orf19_id and a22_name:
                mapping[orf19_id] = a22_name
    return mapping


def new_obj_url(old_url, mapping, fw):
    """Rewrite an old CGD locus.pl obj_url to the new /locus/<A22> form.

    Returns the new URL, or None if the URL has no mappable orf19 identifier
    (already converted, points to a non-orf19 feature, or unmapped orf19).
    """
    if old_url is None:
        return None
    match = ORF19_URL_RE.search(old_url)
    if not match:
        return None
    orf19_id = match.group(1)
    a22_name = mapping.get(orf19_id)
    if a22_name is None:
        fw.write("SKIP url - orf19 id not in mapping: %s (%s)\n" % (orf19_id, old_url))
        return None
    return NEW_URL_PREFIX + a22_name


def update_locus_url(nex_session, mapping, fw, counter):
    """Rewrite obj_url for the CGD 'External id' links on locus pages."""
    log.info("locus_url: loading candidate rows ...")
    rows = nex_session.query(LocusUrl).filter(
        LocusUrl.obj_url.like('%candidagenome.org%locus=orf19.%')
    ).all()
    log.info("locus_url: %d candidate rows; preloading existing keys ...", len(rows))

    # Preload the unique-constraint keys (locus_id, display_name, obj_url,
    # placement) once, so the per-row duplicate check is an in-memory lookup
    # instead of a query round-trip. Only rows whose obj_url is already in the
    # new /locus/ form can collide with a target, so restrict the preload.
    existing = set(nex_session.query(
        LocusUrl.locus_id, LocusUrl.display_name, LocusUrl.obj_url, LocusUrl.placement
    ).filter(LocusUrl.obj_url.like(NEW_URL_PREFIX + '%')).all())

    updated = skipped = 0
    for i, x in enumerate(rows, 1):
        url = new_obj_url(x.obj_url, mapping, fw)
        if url is None or url == x.obj_url:
            skipped += 1
        else:
            key = (x.locus_id, x.display_name, url, x.placement)
            if key in existing:
                fw.write("SKIP locus_url url_id=%s - target already exists: %s\n"
                         % (x.url_id, url))
                skipped += 1
            else:
                fw.write("locus_url url_id=%s: %s -> %s\n" % (x.url_id, x.obj_url, url))
                x.obj_url = url
                nex_session.add(x)
                existing.add(key)
                updated += 1
                counter[0] += 1
                if counter[0] % COMMIT_EVERY == 0:
                    _checkpoint(nex_session)
        if i % PROGRESS_EVERY == 0:
            log.info("locus_url: %d/%d scanned (%d updated, %d skipped)",
                     i, len(rows), updated, skipped)
    log.info("locus_url: DONE - %d updated, %d skipped (of %d candidate rows)",
             updated, skipped, len(rows))
    fw.write("locus_url: %d updated, %d skipped (of %d candidate rows)\n\n"
             % (updated, skipped, len(rows)))


def update_locus_alias(nex_session, mapping, fw, counter):
    """Replace orf19 display_name with the A22 name and rewrite obj_url."""
    log.info("locus_alias: loading candidate rows ...")
    rows = nex_session.query(LocusAlias).filter(
        LocusAlias.display_name.like('orf19.%')
    ).all()
    log.info("locus_alias: %d candidate rows; preloading existing keys ...", len(rows))

    # Preload the unique-constraint keys (locus_id, display_name, alias_type).
    # Only existing aliases whose display_name is one of the A22 target names
    # can collide, so restrict the preload to those.
    targets = list(set(mapping.values()))
    existing = set(nex_session.query(
        LocusAlias.locus_id, LocusAlias.display_name, LocusAlias.alias_type
    ).filter(LocusAlias.display_name.in_(targets)).all())

    updated = skipped = 0
    for i, x in enumerate(rows, 1):
        a22_name = mapping.get(x.display_name)
        if a22_name is None:
            fw.write("SKIP locus_alias alias_id=%s - display_name not in mapping: %s\n"
                     % (x.alias_id, x.display_name))
            skipped += 1
        elif (x.locus_id, a22_name, x.alias_type) in existing:
            fw.write("SKIP locus_alias alias_id=%s - target already exists: %s\n"
                     % (x.alias_id, a22_name))
            skipped += 1
        else:
            old_display = x.display_name
            old_url = x.obj_url
            url = new_obj_url(x.obj_url, mapping, fw) if x.obj_url else None
            fw.write("locus_alias alias_id=%s: display_name %s -> %s; obj_url %s -> %s\n"
                     % (x.alias_id, old_display, a22_name, old_url, url if url else old_url))
            x.display_name = a22_name
            if url is not None:
                x.obj_url = url
            nex_session.add(x)
            existing.add((x.locus_id, a22_name, x.alias_type))
            updated += 1
            counter[0] += 1
            if counter[0] % COMMIT_EVERY == 0:
                _checkpoint(nex_session)
        if i % PROGRESS_EVERY == 0:
            log.info("locus_alias: %d/%d scanned (%d updated, %d skipped)",
                     i, len(rows), updated, skipped)
    log.info("locus_alias: DONE - %d updated, %d skipped (of %d candidate rows)",
             updated, skipped, len(rows))
    fw.write("locus_alias: %d updated, %d skipped (of %d candidate rows)\n\n"
             % (updated, skipped, len(rows)))


def update_locus_homology(nex_session, mapping, fw, counter):
    """Replace orf19 gene_id with the A22 name and rewrite obj_url (Homologs tab).

    nex.locus_homology has no ORM model, so raw SQL is used. Unique constraint:
    (locus_id, gene_id, taxonomy_id).
    """
    log.info("locus_homology: loading candidate rows ...")
    rows = nex_session.execute(text(
        "SELECT homology_id, locus_id, gene_id, taxonomy_id, obj_url "
        "FROM nex.locus_homology WHERE gene_id LIKE 'orf19.%'"
    )).fetchall()
    log.info("locus_homology: %d candidate rows; preloading existing keys ...", len(rows))

    # Preload the unique-constraint keys (locus_id, gene_id, taxonomy_id).
    # Only existing rows whose gene_id is one of the A22 target names can
    # collide, so restrict the preload to those.
    targets = list(set(mapping.values()))
    preload_stmt = text(
        "SELECT locus_id, gene_id, taxonomy_id FROM nex.locus_homology "
        "WHERE gene_id IN :names"
    ).bindparams(bindparam("names", expanding=True))
    existing = set(nex_session.execute(preload_stmt, {"names": targets}).fetchall())

    updated = skipped = 0
    for i, (homology_id, locus_id, gene_id, taxonomy_id, obj_url) in enumerate(rows, 1):
        a22_name = mapping.get(gene_id)
        if a22_name is None:
            fw.write("SKIP locus_homology homology_id=%s - gene_id not in mapping: %s\n"
                     % (homology_id, gene_id))
            skipped += 1
        elif (locus_id, a22_name, taxonomy_id) in existing:
            fw.write("SKIP locus_homology homology_id=%s - target already exists: %s\n"
                     % (homology_id, a22_name))
            skipped += 1
        else:
            url = new_obj_url(obj_url, mapping, fw) if obj_url else None
            fw.write("locus_homology homology_id=%s: gene_id %s -> %s; obj_url %s -> %s\n"
                     % (homology_id, gene_id, a22_name, obj_url, url if url else obj_url))
            if url is not None:
                nex_session.execute(text(
                    "UPDATE nex.locus_homology SET gene_id = :gene_id, obj_url = :obj_url "
                    "WHERE homology_id = :homology_id"
                ), {"gene_id": a22_name, "obj_url": url, "homology_id": homology_id})
            else:
                nex_session.execute(text(
                    "UPDATE nex.locus_homology SET gene_id = :gene_id "
                    "WHERE homology_id = :homology_id"
                ), {"gene_id": a22_name, "homology_id": homology_id})
            existing.add((locus_id, a22_name, taxonomy_id))
            updated += 1
            counter[0] += 1
            if counter[0] % COMMIT_EVERY == 0:
                _checkpoint(nex_session)
        if i % PROGRESS_EVERY == 0:
            log.info("locus_homology: %d/%d scanned (%d updated, %d skipped)",
                     i, len(rows), updated, skipped)
    log.info("locus_homology: DONE - %d updated, %d skipped (of %d candidate rows)",
             updated, skipped, len(rows))
    fw.write("locus_homology: %d updated, %d skipped (of %d candidate rows)\n\n"
             % (updated, skipped, len(rows)))


def update_functionalcomplement(nex_session, mapping, fw, counter):
    """Replace 'CGD:orf19.x' dbxref_id with 'CGD:<A22>' and rewrite obj_url."""
    log.info("functionalcomplementannotation: loading candidate rows ...")
    rows = nex_session.query(Functionalcomplementannotation).filter(
        Functionalcomplementannotation.dbxref_id.like('CGD:orf19.%')
    ).all()
    log.info("functionalcomplementannotation: %d candidate rows", len(rows))

    updated = skipped = 0
    for x in rows:
        orf19_id = x.dbxref_id.split("CGD:", 1)[1]
        a22_name = mapping.get(orf19_id)
        if a22_name is None:
            fw.write("SKIP functionalcomplementannotation annotation_id=%s - "
                     "dbxref_id not in mapping: %s\n" % (x.annotation_id, x.dbxref_id))
            skipped += 1
            continue
        new_dbxref = "CGD:" + a22_name
        url = new_obj_url(x.obj_url, mapping, fw) if x.obj_url else None
        fw.write("functionalcomplementannotation annotation_id=%s: dbxref_id %s -> %s; "
                 "obj_url %s -> %s\n" % (x.annotation_id, x.dbxref_id, new_dbxref,
                                         x.obj_url, url if url else x.obj_url))
        x.dbxref_id = new_dbxref
        if url is not None:
            x.obj_url = url
        nex_session.add(x)
        updated += 1
        counter[0] += 1
        if counter[0] % COMMIT_EVERY == 0:
            _checkpoint(nex_session)
    log.info("functionalcomplementannotation: DONE - %d updated, %d skipped (of %d candidate rows)",
             updated, skipped, len(rows))
    fw.write("functionalcomplementannotation: %d updated, %d skipped (of %d candidate rows)\n\n"
             % (updated, skipped, len(rows)))


def _checkpoint(nex_session):
    """Flush a batch to the database (commit, or rollback in dry-run mode)."""
    if DRY_RUN:
        nex_session.flush()
    else:
        nex_session.commit()


def update_data(mapping_file):

    mapping = load_mapping(mapping_file)
    log.info("Loaded %d orf19 -> A22 mappings from %s", len(mapping), mapping_file)

    logdir = os.path.dirname(LOGFILE)
    if logdir and not os.path.exists(logdir):
        os.makedirs(logdir)
    fw = open(LOGFILE, "w")
    fw.write("Loaded %d orf19 -> A22 mappings from %s\n" % (len(mapping), mapping_file))
    fw.write("DRY_RUN = %s\n\n" % DRY_RUN)

    log.info("Connecting to the database ...")
    nex_session = get_session()
    counter = [0]  # mutable shared counter for batch commits across tables
    log.info("Connected. Mode: %s", "DRY-RUN (no commit)" if DRY_RUN else "APPLY (will commit)")

    update_locus_url(nex_session, mapping, fw, counter)
    update_locus_alias(nex_session, mapping, fw, counter)
    update_locus_homology(nex_session, mapping, fw, counter)
    update_functionalcomplement(nex_session, mapping, fw, counter)

    if DRY_RUN:
        nex_session.rollback()
        log.info("DRY_RUN: rolled back all changes (%d rows would have changed)", counter[0])
        fw.write("\nDRY_RUN: rolled back all changes (%d rows would have changed)\n" % counter[0])
    else:
        nex_session.commit()
        log.info("Committed all changes (%d rows changed)", counter[0])
        fw.write("\nCommitted all changes (%d rows changed)\n" % counter[0])

    nex_session.close()
    fw.close()


if __name__ == '__main__':

    mapping_file = DEFAULT_MAPPING_FILE
    args = [a for a in sys.argv[1:] if a != '--dry-run']
    if '--dry-run' in sys.argv[1:]:
        DRY_RUN = True
    if args:
        mapping_file = args[0]

    if not os.path.exists(mapping_file):
        print("Mapping file not found:", mapping_file)
        print("Usage:         python scripts/loading/CGD/update_orf19_to_a22.py [mapping_file] [--dry-run]")
        print("Usage example: python scripts/loading/CGD/update_orf19_to_a22.py %s" % DEFAULT_MAPPING_FILE)
        exit()

    update_data(mapping_file)
