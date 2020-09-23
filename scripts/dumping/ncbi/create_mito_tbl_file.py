from datetime import datetime
datestamp = str(datetime.now()).split(" ")[0].replace("-", "")

# chrmt.tbl file: newly dumped from database
# mito_ncbi.tbl: newly downloaded from NCBI https://www.ncbi.nlm.nih.gov/nuccore/KP263414.1/
# mito_ncbi.tbl_[datestamp]: updated file for ncbi submission
# mito_update.log: log file for changes

new = open("data/chrmt.tbl")
ncbi = open("data/mito_ncbi.tbl")
ncbi_new = open("data/mito_ncbi.tbl_" + datestamp, "w")
log = open("logs/mito_update.log_" + datestamp, "w")

key2lines = {}
curr_key = None
for line in new:
    pieces = line.split("\t")
    if len(pieces) == 3 and pieces[2].strip() in ['gene', 'rep_origin']:
        curr_key = line
        key2lines[curr_key] = line
    elif curr_key:
        key2lines[curr_key] = key2lines[curr_key] + line

new.close()

curr_key = None
ncbi_key2lines = {}
i = 0
for line in ncbi:
    if i == 0:
        ncbi_new.write(line)
        i = 1
    pieces = line.split("\t")
    if len(pieces) == 3 and pieces[2].strip() in ['gene', 'rep_origin']:
        curr_key = line
        ncbi_key2lines[curr_key] = line
    elif curr_key:
        ncbi_key2lines[curr_key] = ncbi_key2lines[curr_key] + line

ncbi.close()
        
for key in ncbi_key2lines:    
    if key not in key2lines:
        log.write("OLD: \n")
        log.write(ncbi_key2lines[key] + "\n")
    elif ncbi_key2lines[key] != key2lines[key]:
        log.write("CHANGED: \n")
        log.write(key2lines[key] + "\n")
        ncbi_new.write(key2lines[key])
    else:
        ncbi_new.write(ncbi_key2lines[key])
        
for key in key2lines:
    if key not in ncbi_key2lines[key]:
        log.write("NEW: \n")
        log.write(key2lines[key] + "\n")
        ncbi_new.write(key2lines[key])
    
ncbi_new.close()
