import os
from src.models import Dbentity, Referencedbentity, Referencedocument, Referenceauthor,\
    Referencetype, Source
from scripts.loading.database_session import get_session

CREATED_BY = os.environ['DEFAULT_USER']

__author___ = 'sweng66'


def add_paper():

    nex_session = get_session()

    src = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = src.source_id
    
    data = get_data()
    
    reference_id = insert_referencedbentity(nex_session, source_id, data)

    insert_author(nex_session, source_id, reference_id, data)

    insert_abstract(nex_session, source_id, reference_id, data)

    insert_referencetype(nex_session, source_id, reference_id, data)

    # nex_session.rollback()
    nex_session.commit()

    nex_session.close()

    
def insert_referencetype(nex_session, source_id, reference_id, data):

    x = Referencetype(display_name = data['referencetype.display_name'],
                      obj_url = data['referencetype.obj_url'],
                      source_id = source_id,
                      reference_id = reference_id,
                      created_by = CREATED_BY)

    nex_session.add(x)
    
def insert_abstract(nex_session, source_id, reference_id, data):

    x = Referencedocument(document_type = data['referencedocument.document_type'],
                          text = data['referencedocument.text'],
                          html = data['referencedocument.text'],
                          source_id = source_id,
                          reference_id = reference_id,
                          created_by = CREATED_BY)

    nex_session.add(x)

def insert_author(nex_session, source_id, reference_id, data):

    x = Referenceauthor(display_name = data['referenceauthor.display_name'],
                        obj_url = data['referenceauthor.obj_url'],
                        source_id = source_id,
                        reference_id = reference_id,
                        author_order = 1,
                        author_type = 'Author',
                        created_by = CREATED_BY)

    nex_session.add(x)
    
def insert_referencedbentity(nex_session, source_id, data):

    x = Referencedbentity(display_name = data['dbentity.display_name'],
                          source_id = source_id,
                          subclass = 'REFERENCE',
                          dbentity_status = 'Active',
                          method_obtained = data['referencedbentity.method_obtained'],
                          publication_status = data['referencedbentity.publication_status'],
                          fulltext_status = data['referencedbentity.fulltext_status'],
                          citation = data['referencedbentity.citation'],
                          year = data['referencedbentity.year'],
                          title = data['referencedbentity.title'],
                          created_by = CREATED_BY)
    nex_session.add(x)
    nex_session.flush()
    nex_session.refresh(x)

    return x.dbentity_id

def get_data():

    return { "dbentity.display_name": "Sclafani R (2021)",
             "referencedbentity.method_obtained": "Curator non-PubMed reference",
             "referencedbentity.publication_status": "Unpublished",
             "referencedbentity.fulltext_status": "NAP",
             "referencedbentity.citation": "Sclafani R (2021) Personal communication to SGD regarding cdc8 alleles",
             "referencedbentity.year": 2021,
             "referencedbentity.title": "Personal communication to SGD regarding cdc8 alleles",
             "referencedocument.document_type": "Abstract",
             "referencedocument.text": "All 5 cdc8 alleles (cdc8-1 to -5) are the same and are G223A (GAA to AAA) in DNA and Glu75Lys in protein. The sequences are found in my student’s Ph.D. thesis (Jin-Yuan Su, 1991). Also all these alleles are suppressed by the SOE1 missense tRNA3(Glu) suppressor (Su et al., 1990, PMID:2155851), which reads mutant AAA codons and inserts the wild-type Glu amino acid in place of the mutant Lys amino acid.",
             "referencetype.display_name": "Personal Communication to SGD",
             "referencetype.obj_url": "/referencetype/Personal_Communication_to_SGD",
             "referenceauthor.display_name": "Sclafani R",
             "referenceauthor.obj_url": "/author/Sclafani_R"
        }

if __name__ == '__main__':
    
    add_paper()

    
