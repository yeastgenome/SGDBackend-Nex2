import re

col_file = 'data/pathways.col'
dat_file = 'data/pathways.dat'
out_file = 'data/processed_pathways.txt'

name_mapping = { "krieger": "CINDY", "hong": "EURIE" }

f = open(col_file)
f2 = open(dat_file)
fw = open(out_file, 'w')

id_to_display_name = {}
id_to_genes = {}

for line in f:
    if line.startswith('#') or line.startswith('UNIQUE-ID'):
        continue
    pieces = line.split('\t')[0:48]
    id = pieces[0]
    id_to_display_name[id] = pieces[1]
    pieces = pieces[2:48]
    
    genes = []
    for gene in pieces:
        if gene:
            genes.append(gene)
    id_to_genes[id] = genes

f.close()

id = None
id_to_pmids = {}
id_to_pmids4summary = {}
id_to_synonyms = {}
id_to_created_by = {}
id_to_summary = {}
summary = ''
id_list = []
for line in f2:
    line = line.strip()
    if line.startswith('UNIQUE-ID - '):
        id = line.replace('UNIQUE-ID - ', '')
        id_list.append(id)
        continue
    if id is None:
        continue
    if line.startswith("CITATIONS - "):
        pmid = line.replace("CITATIONS - ", "")
        if pmid.isdigit():
            pmids = []
            if id in id_to_pmids:
                pmids = id_to_pmids[id]
            pmids.append(pmid)
            id_to_pmids[id] = pmids
        continue
    if line.startswith("SYNONYMS - "):
        synonym = line.replace("SYNONYMS - ", "")
        synonyms = []
        if id in id_to_synonyms:
            synonyms = id_to_synonyms[id]
        synonyms.append(synonym)
        id_to_synonyms[id] = synonyms
        continue
    if line.startswith("COMMENT - "):
        summary = line.replace("COMMENT - ", "")
        continue
    if summary != '':        
        if line.startswith('/'):
            summary = summary + " " + line.replace('/', '')
        else:
            pmids = []
            summary_text = ''
            pieces = summary.split('|CITS:')
            for piece in pieces:
                piece = piece.replace(']|.', ']|').replace(']|).', ']|')
                items = []
                if ']|' in piece:
                    items = piece.split(']|')
                else:
                    items = piece.split('|')
                text = ''
                if len(items) == 1:
                    text = items[0]
                else:
                    pmid_text = items[0].replace(' ', '').replace('[', ' ').replace(']', ' ')
                    pmid_text = pmid_text.replace(', ', ' ')
                    for pmid in pmid_text.split(' '):
                        if pmid and pmid.isdigit() and int(pmid) not in pmids:
                            pmids.append(pmid)
                    text = items[1].replace('^).', '').replace('^.', '').replace('^ ', '')
                    re.sub(' +.', '.', text)
                    # re.sub(' +', ' ', text)
                    # text = text.replace("  ", " ").replace("  ", " ").replace("  ", " ")
                    text = text.replace("))", ")")

                text = text.strip()
                if text:
                    if summary_text == '':
                        summary_text = text
                    else:
                        summary_text = summary_text + " " + text
            id_to_summary[id] = summary_text
            id_to_pmids4summary[id] = pmids
            summary = ''
        continue
    if line.startswith("CREDITS - "):
        credit = line.strip().replace("CREDITS - ", '')
        if id not in id_to_created_by:
            id_to_created_by[id] = name_mapping.get(credit, "OTTO")
        elif name_mapping.get(credit):
            id_to_created_by[id] = name_mapping[credit]

        print (id, id_to_created_by.get(id, "OTTO"))

f2.close()    

fw.write("pathwayID\tpathwayName\tgeneList\tpmidList\tsummary\tpmidList4summary\tsynonyms\tcreatedBy\n")

for id in id_list:    
    genes = ""
    if id in id_to_genes:
        genes = "|".join(id_to_genes[id])

    pmids = ""
    if id in id_to_pmids:
        pmids = "|".join(id_to_pmids[id])
        
    pmids4summary = ""
    if id in id_to_pmids4summary:
        pmids4summary ="|".join(id_to_pmids4summary[id])

    summary = id_to_summary.get(id, '')

    synonyms = ""

    if id in id_to_synonyms:
        synonyms = "|".join(id_to_synonyms[id])
    
    fw.write(id + "\t" + id_to_display_name[id] + "\t" + genes + "\t" + pmids + "\t" + summary + "\t" + pmids4summary + "\t" + synonyms + "\t" + id_to_created_by.get(id, "OTTO") + "\n")

fw.close()
