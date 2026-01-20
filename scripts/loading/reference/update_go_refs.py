import re
import requests
import yaml
from sqlalchemy import text
from src.models import Dbentity, Referencedbentity, Source, Referenceauthor, \
    Referencetype, Referencedocument, ReferenceAlias
from scripts.loading.database_session import get_session


# -------------------------
# Regex helpers
# -------------------------

_AUTHOR_YEAR_TRAILING_RE = re.compile(r"(?:,\s*|\s+)\(?\b(19|20)\d{2}\)?\s*$")
_AFFILIATION_BLOCK_RE = re.compile(r"\(\s*1\.\s.*$", re.DOTALL)
_AUTHOR_FOOTNOTE_RE = re.compile(r"\s*\(\s*\d+(?:\s*,\s*\d+)*\s*\)")
_AUTHOR_SPLIT_RE = re.compile(r"\s*,\s*")
CREATED_BY = 'OTTO'


def update_go_refs():

    db = get_session()

    source_to_id = dict([(x.display_name, x.source_id) for x in db.query(Source).all()])
    source_id = source_to_id['SGD']
    go_ref_id_to_ref_id = dict([(x.display_name, x.reference_id) for x in db.query(
        ReferenceAlias).filter_by(alias_type = 'GO reference ID').all()])
        
    go_ref_id_to_data = parse_gorefs_yaml(
        "https://github.com/geneontology/go-site/blob/master/metadata/gorefs.yaml",
        from_url=True,
        max_authors=1
    )
    
    for go_ref_id in go_ref_id_to_data:
        row = go_ref_id_to_data[go_ref_id]
        authors = row['authors']
        year = row['year']
        title = row['title']
        citation = row['citation']
        abstract = row['description']
        display_name = authors + "(" + str(year) + ")"
        if go_ref_id not in go_ref_id_to_ref_id:
            reference_id = insert_new_reference(
                db, go_ref_id, year, title, citation, display_name, source_id
            )
            insert_reference_alias(db, reference_id, go_ref_id, source_id)
            insert_authors(db, reference_id, go_ref_id, source_id, authors)
            insert_abstract(db, reference_id, go_ref_id, source_id,
                            abstract, authors, title, 1, 1)
            insert_referencetype(db, reference_id, go_ref_id, source_id)
        else:
            reference_id = go_ref_id_to_ref_id[go_ref_id]
            update_reference_data(
                db, reference_id, go_ref_id, authors, year,
                title, citation, abstract, display_name, source_id
            )

    # db.rollback()
    db.commit()
    db.close()


def insert_new_reference(db, go_ref_id, year, title, citation, display_name, source_id):

    if year:
        x = Referencedbentity(display_name = display_name,
                              source_id = source_id,
                              subclass = 'REFERENCE',
                              dbentity_status = 'Active',
                              method_obtained = 'Curator non-PubMed reference',
                              publication_status = 'Unpublished',
                              fulltext_status = 'NAP',
                              citation = citation,
                              year = year,
                              title = title,
                              created_by = CREATED_BY)
    else:
        x = Referencedbentity(display_name = display_name,
                              source_id = source_id,
                              subclass = 'REFERENCE',
                              dbentity_status = 'Active',
                              method_obtained = 'Curator non-PubMed reference',
                              publication_status = 'Unpublished',
                              fulltext_status = 'NAP',
                              citation = citation,
                              title = title,
                              created_by = CREATED_BY)
    db.add(x)
    db.flush()
    db.refresh(x)
    print(go_ref_id + ": adding a new reference")
    return x.dbentity_id


def insert_reference_alias(db, reference_id, go_ref_id, source_id):

    x = ReferenceAlias(display_name = go_ref_id,
                       reference_id = reference_id,
                       source_id = source_id,
                       alias_type = 'GO reference ID',
                       created_by = 'OTTO'
    )
    db.add(x)
    print(go_ref_id + ": adding into reference_alias")

        
def insert_authors(db, reference_id, go_ref_id, source_id, authors):

    x = Referenceauthor(reference_id = reference_id,
                        display_name = authors,
                        source_id = source_id,
                        author_type = 'Author',
                        author_order = 1,
                        obj_url = '/author/' + authors.replace(' ', '_'),
                        created_by = CREATED_BY
    )
    db.add(x)
    print(go_ref_id + ": adding authors: '" + authors + "'")

    
def insert_abstract(db, reference_id, go_ref_id, source_id, abstract, authors, title, add_abstract, add_medline):

    if add_abstract:
        x = Referencedocument(reference_id = reference_id,
                              document_type = 'Abstract',
                              source_id = source_id,
                              text = abstract,
                              html = abstract,
                              created_by = CREATED_BY
        )
        db.add(x)
        print(go_ref_id + ": adding abstract")
        
    if add_medline:
        entries = []
        entries.append(('STAT', 'Active'))
        entries.append(('TI', title))
        entries.append(('SO', 'SGD'))
        entries.append(('AU', authors))
        entries.append(('PT', 'Personal Communication to SGD'))
        entries.append(('AB', abstract))
        y = Referencedocument(reference_id = reference_id,
                              document_type = 'Medline',
                              source_id = source_id,
                              text = '\n'.join([key + ' - ' + str(value) for key, value in entries if value is not None]),
                              html = '\n'.join([key + ' - ' + str(value) for key, value in entries if value is not None]),
                              created_by = CREATED_BY
        )
        db.add(y)
        print(go_ref_id + ": adding medline")
    

def insert_referencetype(db, reference_id, go_ref_id, source_id):
    
    x = Referencetype(reference_id = reference_id,
                      source_id = source_id,
                      display_name = 'Personal Communication to SGD',
                      obj_url = '/referencetype/Personal_Communication_to_SGD',
                      created_by = CREATED_BY
    )
    db.add(x)
    print(go_ref_id + ": adding referencetype")

    
def update_reference_data(db, reference_id, go_ref_id, authors, year, title, citation, abstract, display_name, source_id):

    # update dbentity.display_name
    x = db.query(Dbentity).filter_by(dbentity_id = reference_id).one_or_none()
    if x.display_name != display_name:
        print(go_ref_id + ": updating dbentity.display_name from '" + str(x.display_name) + "' to '" + str(display_name + "'"))
        x.display_name = display_name
 
    db.add(x)

    # update referencedbentity
    x = db.query(Referencedbentity).filter_by(dbentity_id = reference_id).one_or_none()
    if x.year != year:
        print(go_ref_id + ": updating year from " + str(x.year) + " to " + str(year))
        x.year = year
    if x.title != title:
        print(go_ref_id + ": updating title from '" + str(x.title) + "' to '" + str(title) + "'")
        x.title = title
    if x.citation != citation:
        print(go_ref_id + ": updating citation from '" + str(x.citation) + "' to '" + str(citation) + "'")
        x.citation = citation
    db.add(x)

    # update referencedocument
    if abstract:
        x = db.query(Referencedocument).filter_by(reference_id = reference_id, document_type = 'Abstract').one_or_none()
        add_abstract = 0
        add_medline = 0
        if not x:
            add_abstract = 1
        else:
            if x.text != abstract:
                print(go_ref_id + ": updating abstract")
                x.text = abstract
                x.html = abstract
                db.add(x)
        y = db.query(Referencedocument).filter_by(reference_id = reference_id, document_type = 'Medline').one_or_none()
        if not y:
            add_medline = 1
        else:
            if abstract not in y.text:
                new_text = y.text.split("AB -")[0] + "AB -" + abstract
                y.text = new_text
                y.html = new_text
                db.add(y)
        if add_abstract or add_medline:
            insert_abstract(
                db, reference_id, go_ref_id, source_id, abstract, authors, title,
                add_abstract, add_medline
            )

    # update authors
    if authors:
        rows = db.query(Referenceauthor).filter_by(reference_id = reference_id).order_by(Referenceauthor.author_order).all()
        if len(rows) > 0:
            x = rows[0]
            if x.display_name != authors:
                x.display_name = authors
                db.add(x)
            if len(rows) > 1:
                for y in rows[1:]:
                    db.delete(y)
        else:
            insert_authors(db, reference_id, go_ref_id, source_id, authors)

    # update rerferencetype
    x = db.query(Referencetype).filter_by(reference_id = reference_id).one_or_none()
    if not x:
        insert_referencetype(db, reference_id, go_ref_id, source_id)


# -------------------------
# URL helper
# -------------------------

def _github_blob_to_raw(url):
    m = re.match(
        r"^https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)$",
        url
    )
    if not m:
        return url
    owner, repo, branch, path = m.groups()
    return "https://raw.githubusercontent.com/{}/{}/{}/{}".format(
        owner, repo, branch, path
    )


# -------------------------
# Author parsing
# -------------------------

def _authors_to_list(authors_raw):
    if authors_raw is None:
        s = ""
    elif isinstance(authors_raw, list):
        s = ", ".join(str(a).strip() for a in authors_raw if str(a).strip())
    else:
        s = str(authors_raw).strip()

    # remove affiliation block
    s = _AFFILIATION_BLOCK_RE.sub("", s)

    # remove numeric footnotes
    s = _AUTHOR_FOOTNOTE_RE.sub("", s)

    # remove trailing year
    s = _AUTHOR_YEAR_TRAILING_RE.sub("", s)

    # normalize whitespace
    s = re.sub(r"\s+", " ", s).strip(" ,")

    if not s:
        return []

    return [p.strip() for p in _AUTHOR_SPLIT_RE.split(s) if p.strip()]


def _format_authors(authors_raw, max_authors=1):
    parts = _authors_to_list(authors_raw)

    if not parts:
        return ""

    if len(parts) <= max_authors:
        return ", ".join(parts)

    return parts[0] + ", et al."


# -------------------------
# Main parser
# -------------------------

def parse_gorefs_yaml(src, from_url=False, timeout=30, max_authors=1):
    """
    Parse GO gorefs.yaml and return non-obsolete records.

    Returns list of dicts:
      id, title, year, authors, description, citation
    """
    # Load YAML
    if from_url:
        url = _github_blob_to_raw(src)
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        text = r.text
    else:
        if isinstance(src, bytes):
            text = src.decode("utf-8")
        else:
            text = src

    data = yaml.safe_load(text)
    if not isinstance(data, list):
        raise ValueError("Expected a list of GO_REF records")

    results = {}

    for rec in data:
        if not isinstance(rec, dict):
            continue

        if rec.get("is_obsolete") is not False:
            continue

        gid = rec.get("id")
        title = rec.get("title")
        year = rec.get("year")
        description = rec.get("description", "")

        if not gid or not title or not year:
            continue

        authors = _format_authors(rec.get("authors"), max_authors=max_authors)
        citation = "{} ({}) {}".format(authors, year, title)

        results[str(gid)] = {
            "title": str(title).strip(),
            "year": int(year),
            "authors": authors,
            "description": description.strip() if isinstance(description, str) else "",
            "citation": citation,
        }

    return results


if __name__ == "__main__":
    update_go_refs()

