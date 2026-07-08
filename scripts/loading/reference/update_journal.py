import urllib.request
from src.models import Journal
from scripts.loading.database_session import get_session

def update_data(medline_file):

    key_to_journal_data = read_medline_file(medline_file)
    
    nex_session = get_session()

    key_to_id = dict([((x.med_abbr, x.display_name), x.journal_id) for x in nex_session.query(Journal).all()])
    
    for x in nex_session.query(Journal).all():
        journal_data = None
        if x.issn_print and x.issn_print in key_to_journal_data:
            journal_data = key_to_journal_data[x.issn_print]
        elif x.issn_electronic and x.issn_electronic in key_to_journal_data:
            journal_data = key_to_journal_data[x.issn_electronic]
        if journal_data:
            # print("DATABASE: ", (x.issn_print, x.issn_electronic, x.title, x.med_abbr))
            # print("MEDLINE : ", journal_data)
            (issn_print, issn_online, journalTitle, medAbbr, isoAbbr) = journal_data
            key = (medAbbr, journalTitle)
            if key in key_to_id:
                continue
            issn_print_db = x.issn_print if x.issn_print else ''
            issn_online_db = x.issn_electronic if x.issn_electronic else ''
            title_db = x.title if x.title else ''
            med_abbr_db = x.med_abbr if x.med_abbr else ''
            if issn_print_db != issn_print or \
               issn_online_db != issn_online or \
               title_db != journalTitle or \
               med_abbr_db != medAbbr:
                # print("DATABASE: ", (issn_print_db, issn_online_db, title_db, med_abbr_db))
                # print("MEDLINE : ", journal_data)
                if title_db.lower().replace(".", '') != journalTitle.lower().replace('.', '') and \
                   med_abbr_db.lower().replace(".", '') != medAbbr.lower().replace(".", ''):
                    # print("DATABASE: ", (issn_print_db, issn_online_db, title_db, med_abbr_db))
                    # print("MEDLINE : ", journal_data)
                    continue
                updated = 0
                if issn_print and issn_print != issn_print_db:
                    x.issn_print = issn_print
                    updated += 1
                if issn_online and issn_online != issn_online_db:
                    x.issn_electronic = issn_online
                    updated += 1
                if journalTitle and journalTitle != title_db:
                    x.title = journalTitle
                    updated += 1
                if medAbbr and medAbbr != med_abbr_db:
                    x.med_abbr = medAbbr
                    updated += 1
                if updated > 0:
                    try:
                        nex_session.add(x)
                        # nex_session.rollback()
                        nex_session.commit()
                        print("Journal row updated FROM ", (issn_print_db, issn_online_db, title_db, med_abbr_db))
                        print("Journal row updated TO   ", (issn_print, issn_online, journalTitle, medAbbr))
                        key_to_id[key] = 1
                    except Exception as e:
                        nex_session.rollback()
                        print("Error when updating row FROM ", (issn_print_db, issn_online_db, title_db, med_abbr_db), " TO ", (issn_print, issn_online, journalTitle, medAbbr), "ERROR=", e)
                        # pass
                        continue
        # else:
        #    print("NOT Found:", (x.issn_print, x.issn_electronic, x.title, x.med_abbr))
            
def read_medline_file(medline_file):

    f = open(medline_file)

    issn_print = None
    issn_online = None
    journalTitle = None
    medAbbr = None
    isoAbbr = None
    key_to_data = {}
    for line in f:
        if line.startswith("JrId:"):
            if journalTitle:
                for key in [issn_print, issn_online]:
                    if key:
                        key_to_data[key] = (issn_print, issn_online, journalTitle, medAbbr, isoAbbr)
            issn_print = None
            issn_online = None
            journalTitle = None
            medAbbr = None
            isoAbbr = None
        else:
            if line.startswith('JournalTitle:'):
                journalTitle = line.strip().replace("JournalTitle: ", '')
            elif line.startswith('MedAbbr:'):
                medAbbr = line.strip().replace("MedAbbr:", '').strip()
            elif line.startswith('IsoAbbr:'):
                isoAbbr = line.strip().replace("IsoAbbr:", '').strip()
            elif line.startswith('ISSN (Print):'):
                issn_print = line.strip().replace("ISSN (Print):", '').strip()
            elif line.startswith('ISSN (Online):'):
                issn_online = line.strip().replace("ISSN (Online):", '').strip()

    if journalTitle:
        for key	in [issn_print, issn_online]:
            if key:
                key_to_data[key] = (issn_print, issn_online, journalTitle, medAbbr, isoAbbr)

    return key_to_data

                
if __name__ == "__main__":
        
    url_path = 'https://ftp.ncbi.nih.gov/pubmed/'
    medline_file = 'J_Medline.txt'
    urllib.request.urlretrieve(url_path + medline_file, medline_file)
    urllib.request.urlcleanup()

    update_data(medline_file)


    
        
