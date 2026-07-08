"""redmine_6631 / Functional Networks: load GO-CAM model links into nex.pathway_url.

The Locus Summary Page "Functional Networks" section shows GO-CAMs for a gene by
embedding the GO <go-gocam-viewer> web component. For yeast, the GO-CAM models are
the YeastPathways pathway imports, published by GO as YeastPathways_<biocyc_id>.json
files (see https://geneontology.org/docs/download-go-cams/).

This loader records, for each YeastPathways GO-CAM model, a row in nex.pathway_url
with url_type='GO-CAM' and obj_url='http://model.geneontology.org/<model_id>'. The
/locus/{id}/go_cams endpoint then joins pathwayannotation -> pathway_url('GO-CAM')
to return the models for a gene (title = pathway display_name, model id parsed from
the obj_url).

Only the set of pathways that actually have a GO-CAM model gets a row, so presence
of a 'GO-CAM' pathway_url row is what drives the show/hide of the GO-CAMs subsection.

The 'GO-CAM' url_type must already be allowed by the pathwayurl_type_ck constraint
(see scripts/loading/pathway/add_gocam_url_type.sql).

Usage:
    python -m scripts.loading.pathway.load_gocam_url [SOURCE] [--dryrun]

SOURCE is where the YeastPathways_*.json model ids are listed. It may be:
  - a directory of *.json GO-CAM files (uses the YeastPathways_*.json filenames)
  - a local text/HTML/JSON file that mentions the YeastPathways_*.json names
  - a URL to the GO go-cams json index (default)
The same defensive parser handles all three: it pulls every 'YeastPathways_...'
token out of the text, so it is robust to the exact HTML/JSON index format (which
GO has said will change). Override the default URL with the GOCAM_JSON_INDEX env var.
"""
import os
import re
import sys
from datetime import datetime

try:
    from urllib.request import urlopen, Request
except ImportError:  # py2
    from urllib2 import urlopen, Request

from src.models import Dbentity, Pathwaydbentity, PathwayUrl, Source
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

DEFAULT_INDEX_URL = os.environ.get(
    'GOCAM_JSON_INDEX', 'https://current.geneontology.org/go-cams/json/index.html')
MODEL_BASE_URL = 'http://model.geneontology.org/'
MODEL_PREFIX = 'YeastPathways_'
URL_TYPE = 'GO-CAM'
SOURCE = 'SGD'
CREATED_BY = os.environ.get('CREATED_BY', 'OTTO')
LOG_FILE = 'scripts/loading/pathway/logs/load_gocam_url.log'

# Matches model ids like YeastPathways_ARO-PWY or YeastPathways_ARO-PWY-1, with or
# without a trailing .json, however they appear in a directory listing or JSON index.
MODEL_ID_RE = re.compile(r'YeastPathways_[A-Za-z0-9._+\-]+')


def get_model_ids(source):
    """Return a sorted list of unique YeastPathways_* model ids found in `source`."""
    if os.path.isdir(source):
        names = os.listdir(source)
        text = '\n'.join(names)
    elif os.path.isfile(source):
        with open(source) as f:
            text = f.read()
    else:
        # GO's server 403s the default urllib User-Agent, so send a real one.
        req = Request(source, headers={'User-Agent': 'Mozilla/5.0 (SGD load_gocam_url)'})
        text = urlopen(req).read()
        if isinstance(text, bytes):
            text = text.decode('utf-8', 'replace')

    ids = set()
    for token in MODEL_ID_RE.findall(text):
        if token.endswith('.json'):
            token = token[:-len('.json')]
        ids.add(token)
    return sorted(ids)


def build_pathway_lookups(nex_session):
    """exact: biocyc_id -> pathway_id; base: biocyc_id without -<n> suffix -> [(biocyc_id, pathway_id)]."""
    exact = {}
    base = {}
    for p in nex_session.query(Pathwaydbentity).all():
        if not p.biocyc_id:
            continue
        exact[p.biocyc_id] = p.dbentity_id
        stripped = re.sub(r'-\d+$', '', p.biocyc_id)
        base.setdefault(stripped, []).append((p.biocyc_id, p.dbentity_id))
    return exact, base


def match_pathway_id(biocyc_part, exact, base):
    """Resolve a GO model's biocyc part to an SGD pathway_id, handling the -<n> suffix.

    Returns (pathway_id, note). pathway_id is None when no/ambiguous match.
    """
    if biocyc_part in exact:
        return exact[biocyc_part], 'exact'

    # GO id may drop the SGD numeric suffix (ARO-PWY vs ARO-PWY-1), or carry one we
    # already stripped -- compare on the suffix-normalized base either way.
    stripped = re.sub(r'-\d+$', '', biocyc_part)
    candidates = base.get(stripped)
    if not candidates:
        return None, 'unmatched'
    if len(candidates) == 1:
        return candidates[0][1], 'base:' + candidates[0][0]
    return None, 'ambiguous:' + ','.join(c[0] for c in candidates)


def load_gocam_url(source=None, dryrun=False):
    source = source or DEFAULT_INDEX_URL

    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    fw = open(LOG_FILE, 'w')

    def log(msg):
        fw.write(msg + '\n')
        print(msg)

    log('Started: ' + str(datetime.now()))
    log('Source: ' + source + ('  (DRYRUN)' if dryrun else ''))

    nex_session = get_session()

    source_row = nex_session.query(Source).filter_by(format_name=SOURCE).one_or_none()
    if source_row is None:
        log('ERROR: source %s not found' % SOURCE)
        fw.close()
        return
    source_id = source_row.source_id

    exact, base = build_pathway_lookups(nex_session)

    model_ids = get_model_ids(source)
    log('Found %d YeastPathways_* model id(s) in source' % len(model_ids))

    inserted = 0
    updated = 0
    skipped = 0
    unmatched = []
    ambiguous = []

    for model_id in model_ids:
        biocyc_part = model_id[len(MODEL_PREFIX):]
        pathway_id, note = match_pathway_id(biocyc_part, exact, base)
        if pathway_id is None:
            if note.startswith('ambiguous'):
                ambiguous.append('%s -> %s' % (model_id, note))
            else:
                unmatched.append(model_id)
            continue

        obj_url = MODEL_BASE_URL + model_id

        existing = nex_session.query(PathwayUrl).filter_by(
            pathway_id=pathway_id, url_type=URL_TYPE).one_or_none()

        if existing is not None:
            if existing.obj_url != obj_url:
                log('UPDATE pathway_id=%s %s -> %s' % (pathway_id, existing.obj_url, obj_url))
                if not dryrun:
                    existing.obj_url = obj_url
                    nex_session.add(existing)
                updated += 1
            else:
                skipped += 1
            continue

        log('INSERT pathway_id=%s url_type=%s obj_url=%s (%s)' % (
            pathway_id, URL_TYPE, obj_url, note))
        if not dryrun:
            row = PathwayUrl(
                display_name=URL_TYPE,
                obj_url=obj_url,
                source_id=source_id,
                pathway_id=pathway_id,
                url_type=URL_TYPE,
                created_by=CREATED_BY)
            nex_session.add(row)
            nex_session.flush()
        inserted += 1

    if dryrun:
        nex_session.rollback()
    else:
        nex_session.commit()
    nex_session.close()

    log('')
    log('Summary: inserted=%d updated=%d unchanged=%d matched=%d' % (
        inserted, updated, skipped, inserted + updated + skipped))
    if ambiguous:
        log('Ambiguous (skipped, base biocyc id maps to >1 pathway) [%d]:' % len(ambiguous))
        for a in ambiguous:
            log('  ' + a)
    if unmatched:
        log('Unmatched (no SGD pathway for this biocyc id) [%d]:' % len(unmatched))
        for u in unmatched:
            log('  ' + u)
    log('Finished: ' + str(datetime.now()))
    fw.close()


if __name__ == '__main__':
    args = [a for a in sys.argv[1:]]
    dryrun = '--dryrun' in args
    args = [a for a in args if a != '--dryrun']
    src = args[0] if args else None
    load_gocam_url(source=src, dryrun=dryrun)
