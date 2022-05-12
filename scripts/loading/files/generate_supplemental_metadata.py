from src.models import Referencedbentity
from scripts.loading.database_session import get_session

date = "2022-05-12"

outfile = "scripts/loading/files/data/supplemental_file_metadata_2022-05-12.txt"
pmidfile = "scripts/loading/files/data/supplemental_pmid_2022-05-12.lst"

nex_session = get_session()

pmid_to_year = dict([(x.pmid, x.year) for x in nex_session.query(Referencedbentity).all()])
      
fw = open(outfile, "w")
    
# fw.write("bun_path\tpath.path\tfiledbentity.previous_file_name\tdbentity.display_name\tdbentity.status\tdbentity.source\ttopic term name\ttopic edam_id\tdata term name\tdata edam_id\tformat term name\tformat edam_id\tfiledbentity.file_extension\tfiledbentity.file_date\tfiledbentity.year\tfiledbentity.is_public\tfiledbentity.is_in_spell\tfiledbentity.is_in_browser\treadme name\tfiledbentity.description\tpmids (|)\tkeywords (|)\n")

f = open(pmidfile)
for line in f:
    pmid = int(line.strip())
    year = pmid_to_year.get(pmid)
    if year is None:
        # print ("The PMID ", pmid, " is not in the database")
        continue
    filename = str(pmid) + ".zip"
    fw.write("/Users/shuai/supplemental_files/\t/supplemental_data\t" + filename + "\t" + filename + "\tActive\tSGD\tBiology\ttopic:3070\tText data\tdata:2526\tTextual format\tformat:2330\tzip\t" + date + "\t" + str(year) + "\t1\t0\t0\tNone\tSupplemental Materials\t"+ str(pmid) +"\tNone\n")
    
f.close()
fw.close()
