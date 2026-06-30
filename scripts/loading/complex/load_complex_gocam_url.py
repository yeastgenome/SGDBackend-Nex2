"""redmine_6631 / Functional Networks: link complexes to their GO-CAM models.

The Complex GO tab shows a GO-CAMs section, mirroring the Locus Summary Page.
Unlike a gene, a complex has no pathway annotations of its own, so we cannot
reach its GO-CAMs through pathwayannotation. A complex belongs to a GO-CAM model
only when that model has an annotation to the complex itself -- the model carries
an object with id 'SGD:<complex_sgdid>' / label 'CPX-xxxx' (typically the
enabled_by of an activity). That membership lives only in the model JSON, so this
loader reads it from there.

For every GO-CAM model already recorded in nex.pathway_url (url_type='GO-CAM',
loaded by scripts/loading/pathway/load_gocam_url.py), this loader fetches the
model JSON, finds which SGD complexes it annotates, and records one
nex.complex_alias row per (complex, model) with:
    alias_type   = 'GO-CAM'
    display_name = the pathway/model title (pathway display_name)
    obj_url      = http://model.geneontology.org/YeastPathways_<biocyc_id>

The /complex/{id}/go_cams endpoint then returns these rows (model id parsed from
obj_url). Storing the GO-CAM link as a complex_alias mirrors the existing PDB /
EMDB external-resource aliases. The 'GO-CAM' alias_type must already be allowed by
the complexalias_type_ck constraint (see add_complex_gocam_alias_type.sql).

This loader is a full reconcile: it inserts missing (complex, model) links and
removes stale GO-CAM aliases that the models no longer support, so re-running it
keeps nex.complex_alias in sync with the published models.

Usage:
    python -m scripts.loading.complex.load_complex_gocam_url [--dryrun]

The model JSON base URL is overridable via the GOCAM_JSON_BASE env var.
"""
import os
import re
import sys
from datetime import datetime

try:
    from urllib.request import urlopen, Request
except ImportError:  # py2
    from urllib2 import urlopen, Request

from src.models import Complexdbentity, ComplexAlias, Dbentity, PathwayUrl, Source
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

# Each model's Minerva JSON lives next to the json index used by load_gocam_url.
GOCAM_JSON_BASE = os.environ.get(
    'GOCAM_JSON_BASE', 'https://current.geneontology.org/go-cams/json/')
ALIAS_TYPE = 'GO-CAM'
SOURCE = 'SGD'
CREATED_BY = os.environ.get('CREATED_BY', 'OTTO')
LOG_FILE = 'scripts/loading/complex/logs/load_complex_gocam_url.log'

# SGD complex SGDIDs all look like S000218158; reused to spot complex objects.
SGDID_RE = re.compile(r'S0\d{8}')


def fetch_model_json(model_id):
    """Return the model JSON text, or None on error. GO's server 403s the
    default urllib User-Agent, so send a real one (same as load_gocam_url)."""
    url = GOCAM_JSON_BASE + model_id + '.json'
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (SGD load_complex_gocam_url)'})
        text = urlopen(req, timeout=60).read()
        if isinstance(text, bytes):
            text = text.decode('utf-8', 'replace')
        return text
    except Exception as e:
        sys.stderr.write('WARN: could not fetch %s: %s\n' % (url, e))
        return None


def complexes_in_model(text, complex_sgdids):
    """Return the set of complex SGDIDs that this model annotates.

    A complex is annotated by the model when the model carries an object whose
    id is SGD:<complex_sgdid> (label 'CPX-xxxx'). Complex SGDIDs identify only
    complexes, so any SGD:<complex_sgdid> token in the model is a reference to
    that complex object -- we keep the tokens that are known complexes.
    """
    return set(s for s in SGDID_RE.findall(text) if s in complex_sgdids)


def load_complex_gocam_url(dryrun=False):
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    fw = open(LOG_FILE, 'w')

    def log(msg):
        fw.write(msg + '\n')
        print(msg)

    log('Started: ' + str(datetime.now()))
    log('Model JSON base: ' + GOCAM_JSON_BASE + ('  (DRYRUN)' if dryrun else ''))

    nex_session = get_session()

    source_row = nex_session.query(Source).filter_by(format_name=SOURCE).one_or_none()
    if source_row is None:
        log('ERROR: source %s not found' % SOURCE)
        fw.close()
        return
    source_id = source_row.source_id

    # complex sgdid -> complex dbentity_id
    complex_sgdid_to_id = {}
    for c in nex_session.query(Complexdbentity).all():
        complex_sgdid_to_id[c.sgdid] = c.dbentity_id
    complex_sgdids = set(complex_sgdid_to_id)
    log('Complexes in DB: %d' % len(complex_sgdids))

    # GO-CAM models from pathway_url, with their pathway title.
    gocam_rows = nex_session.query(PathwayUrl).filter_by(url_type='GO-CAM').all()
    log('GO-CAM models recorded in pathway_url: %d' % len(gocam_rows))

    # desired[(complex_id, obj_url)] = title
    desired = {}
    for url_row in gocam_rows:
        obj_url = url_row.obj_url
        model_id = obj_url.rstrip('/').split('/')[-1]
        pathway = nex_session.query(Dbentity).filter_by(dbentity_id=url_row.pathway_id).one_or_none()
        title = pathway.display_name if pathway else model_id

        text = fetch_model_json(model_id)
        if text is None:
            continue
        for sgdid in complexes_in_model(text, complex_sgdids):
            desired[(complex_sgdid_to_id[sgdid], obj_url)] = title

    log('Complex GO-CAM links found in models: %d' % len(desired))

    # existing GO-CAM aliases
    existing = nex_session.query(ComplexAlias).filter_by(alias_type=ALIAS_TYPE).all()
    existing_by_key = {(a.complex_id, a.obj_url): a for a in existing}

    inserted = 0
    updated = 0
    skipped = 0
    deleted = 0

    for key, title in desired.items():
        complex_id, obj_url = key
        row = existing_by_key.get(key)
        if row is not None:
            if row.display_name != title:
                log('UPDATE complex_id=%s %s title -> %s' % (complex_id, obj_url, title))
                if not dryrun:
                    row.display_name = title
                    nex_session.add(row)
                updated += 1
            else:
                skipped += 1
            continue
        log('INSERT complex_id=%s alias_type=%s obj_url=%s (%s)' % (
            complex_id, ALIAS_TYPE, obj_url, title))
        if not dryrun:
            nex_session.add(ComplexAlias(
                display_name=title,
                obj_url=obj_url,
                source_id=source_id,
                complex_id=complex_id,
                alias_type=ALIAS_TYPE,
                created_by=CREATED_BY))
            nex_session.flush()
        inserted += 1

    for key, row in existing_by_key.items():
        if key not in desired:
            log('DELETE stale complex_id=%s %s' % (row.complex_id, row.obj_url))
            if not dryrun:
                nex_session.delete(row)
            deleted += 1

    if dryrun:
        nex_session.rollback()
    else:
        nex_session.commit()
    nex_session.close()

    log('')
    log('Summary: inserted=%d updated=%d unchanged=%d deleted=%d' % (
        inserted, updated, skipped, deleted))
    log('Finished: ' + str(datetime.now()))
    fw.close()


if __name__ == '__main__':
    dryrun = '--dryrun' in sys.argv[1:]
    load_complex_gocam_url(dryrun=dryrun)
