import sys
from src.models import Referencedbentity, Referenceauthor, ReferenceUrl, Referencetype, \
                       Journal, Referencedocument
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

pmidFile = 'scripts/dumping/paper/data/pmid_for_new_pdf_2021-06-23.lst'
outfile = 'scripts/dumping/paper/data/bibliograph_2021-06-23.txt'

month_mapping = { "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
                  "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12" }

def dump_data():

    nex_session = get_session()

    allAuthors = nex_session.query(Referenceauthor).order_by(Referenceauthor.reference_id, Referenceauthor.author_order).all()
    reference_id_to_authors = {}
    for x in allAuthors:
        authors = []
        if x.reference_id in reference_id_to_authors:
            authors = reference_id_to_authors[x.reference_id]
        authors.append(x.display_name)
        reference_id_to_authors[x.reference_id] = authors
        print (x.reference_id, authors)

        
    allUrls = nex_session.query(ReferenceUrl).filter_by(display_name='DOI full text').all()
    reference_id_to_doi = {}
    for x in allUrls:
        # example obj_url = http://dx.doi.org/10.1098/rstb.2015.0540
        doi = "doi:" + x.obj_url.replace('http://dx.doi.org/', '').replace('/', '\/')
        reference_id_to_doi[x.reference_id] = doi
        print (x.reference_id, doi)

        
    allTypes = nex_session.query(Referencetype).all()
    reference_id_to_types = {}
    for x in allTypes:
        types = []
        if x.reference_id in reference_id_to_types:
            types = reference_id_to_types[x.reference_id]
        types.append(x.display_name.replace(' ', '_'))
        reference_id_to_types[x.reference_id] = types
        print (x.reference_id, types)

        
    journal_id_to_name = dict([(x.journal_id, x.display_name) for x in nex_session.query(Journal).all()]) 

    print (journal_id_to_name)

    print ("getting abstract")

    
    # reference_id_abstract = dict([(x.reference, x.text) for x in nex_session.query(Referencedocument).filter_by(document_type='Abstract').all()])
    i = 0
    reference_id_to_abstract = {}
    for x in nex_session.query(Referencedocument).filter_by(document_type='Abstract').all():
        reference_id_to_abstract[x.reference_id] = x.text
        i = i + 1
        print (i, x.reference_id, "abstract")

    nex_session.close()
        
    ## author|Feng H ; Reece-Hoyes JS ; Walhout AJ ; Hope IA
    ## accession| Other:doi:10.1016\/j.gene.2011.11.042 PMID:22207033 WBPaper00040555
    ## type|Journal_article
    # title|A regulatory cascade of three transcription factors in a single specific neuron, DVC, in Caenorhabditis elegans.
    ## journal|Gene
    # citation|V: 494P: 73-84
    # year|2012-02-15
    ## abstracy|Homeobox proteins are critical regulators of developmental ...

    # date_published: "2016 Jul", "2015 Nov 5", "2016"

    print ("reading pmid file")
    
    valid_pmid = {}
    f = open(pmidFile)
    i = 0
    for pmid in f:
        pmid = int(pmid.strip())
        valid_pmid[pmid] = 1
        i = i + 1
        print (i, pmid)
    f.close()

    nex_session = get_session()
    
    print ("getting data from reference table")

    fw = open(outfile, "w")

    i = 0
    allRefs = nex_session.query(Referencedbentity).all()
    for x in allRefs:
        if x.pmid is None or x.pmid not in valid_pmid:
            continue
        reference_id = x.dbentity_id
        
        i = i + 1
        print (i, reference_id)
        
        fw.write("PMID:" + str(x.pmid) + "\n")
        if reference_id in reference_id_to_authors:
            fw.write("author|" + " ; ".join(reference_id_to_authors[reference_id]) + "\n")
        accession = ""
        if reference_id in reference_id_to_doi:
            accession = "Other:" + reference_id_to_doi[reference_id] + " PMID:" + str(x.pmid)
        else:
            accession = "PMID:" + str(x.pmid)
        fw.write("accession|" + accession + "\n")
        if reference_id in reference_id_to_types:
            fw.write("type|" + " ; ".join(reference_id_to_types[reference_id]) + "\n")
        if x.title:
            fw.write("title|" + x.title + "\n")
        if x.journal_id and x.journal_id in journal_id_to_name:
            fw.write("journal|" + journal_id_to_name[x.journal_id] + "\n")
        citation = x.volume
        if citation is None:
            citation = ""
        if x.issue:
            citation = citation + "(" + x.issue + ")"
        if citation:
            citation = "V: " + citation
        if x.page:
            citation = citation + " P: " + x.page
        if citation:
            fw.write("citation|" + citation + "\n")
        date_str = x.date_published
        if date_str is None:
            date_str = str(x.year)
        date = date_str.split(' ')
        year = date[0]
        if year is None:
            year = str(x.year)
        if len(date) > 1:
            mon = month_mapping.get(date[1])
            if mon is None:
                mon = "01"
            if len(date) > 2:
                day = date[2]
                if day is None:
                    day = "01"
                if len(day) == 1:
                    day = '0' + day
                year = year + "-" + mon + "-" + day 
            else:
                year = year + "-" + mon + "-01"
        else:
            year = year + "-01-01"
        fw.write("year|" + year + "\n")
        if reference_id in reference_id_to_abstract:
            fw.write("abstract|" + reference_id_to_abstract[reference_id]+ "\n")
        fw.write("\n")

    fw.close()
    
    print ("DONE!")
    
if __name__ == '__main__':

    dump_data()
