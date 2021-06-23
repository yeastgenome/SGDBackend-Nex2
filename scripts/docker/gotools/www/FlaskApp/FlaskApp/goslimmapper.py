import json
import os
import socket
from flask import send_from_directory, Response
from os import path
from gotermfinder import get_param, parse_gaf_file, create_gene_list, get_download_url

dataDir = '/var/www/data/'
binDir = '/var/www/bin/'
tmpDir = '/var/www/tmp/'
rootUrl = 'https://' + socket.gethostname().replace('-2a', '') + '/'
# rootUrl = 'https://gotermfinder.dev.yeastgenome.org/'

gaf = dataDir + 'gene_association.sgd'
gaf4C = dataDir + 'slim_component_gene_association.sgd'
gaf4F = dataDir + 'slim_function_gene_association.sgd'
gaf4P = dataDir + 'slim_process_gene_association.sgd'

gtmScript = binDir + 'GOTermMapper.pl'

genefileNmRoot = "mapper_genes_" + str(os.getpid())
slimInputFile =	"mapper_terms_" + str(os.getpid())
geneList = tmpDir + genefileNmRoot + '.lst'
termList = tmpDir + slimInputFile
tmpTab = tmpDir + genefileNmRoot + '_slimTab.txt'

def create_term_list(terms):

    fw = open(termList, 'w')
    
    slimTerms = terms.split('|')
    preTerm = ""
    for term in slimTerms:
        term = term.replace(';GO:', '; GO:')
        if ' ; GO:' not in term:
            if preTerm: 
                preTerm = preTerm + ','
            preTerm = preTerm + term
            continue
        if preTerm:
            term = preTerm  + ","  + term
            preTerm = ""
        fw.write(term + "\n")
    fw.close()

def get_html_content(htmlFile):

    htmlFile = tmpDir + htmlFile
    f = open(htmlFile, encoding="utf-8")
    html = f.read()
    f.close()
    
    html = html.replace("<html><body>", "").replace("</body></html>", "")
    html = html.replace("<br><b>", "").replace("</b><br><br><center>", "<center>")
    html = html.replace("color=red", "color=maroon")
    html = html.replace("<td colspan=5>", "<td colspan=5 bgcolor='#FFCC99'>")
    html = html.replace("<font color=#FFFFFF>", "").replace("</font>", "")
    html = html.replace("<th align=center nowrap>", "<th bgcolor='#CCCCFF' align=center nowrap>")
    html = html.replace("<th align=center>", "<th bgcolor='#CCCCFF' align=center nowrap>")
    html = html.replace('<tr bgcolor="FFE4C4">', '')
    html = html.replace(' nowrap=""', '')
    html = html.replace('( ', '(')
    html = html.replace(' )', ')')
    html = html.replace("infowin", "_extwin")
    return html
    
def set_gaf_file(aspect):
    if aspect == 'P':
        return gaf4P
    if aspect == 'F':
       return gaf4F
    return gaf4C

def gtm_search(request):

    genes = get_param(request, 'genes')
    if genes == '':
        return { " ERROR": "NO GENE NAME PASSED IN" }
    genes = genes.upper().replace('SGD:', '')

    aspect = get_param(request, 'aspect')
    if aspect is None:
        return { " ERROR": "NO GO ASPECT PASSED IN" }

    terms = get_param(request, 'terms')
    if terms is None:
        return { " ERROR": "NO SLIM TERMS PASSED IN" }

    (namemapping, aliasmapping) = parse_gaf_file(gaf)
    create_gene_list(geneList, genes, namemapping, aliasmapping)
    create_term_list(terms)
    thisGAF = set_gaf_file(aspect)
    
    cmd = gtmScript + " -h -d " + tmpDir + " -a " + aspect + " -o " + termList + " -g " + thisGAF + " " + geneList 
    output = os.popen(cmd).read()

    # if path.exists(tmpTab):
    #    return  { "output": "<pre>" + output + "</pre>" }

    html = get_html_content(genefileNmRoot + '_slimTerms.html')
    
    return { "html": html,
             "table_page": get_download_url(genefileNmRoot + '_slimTerms.html'),
	     "tab_page": get_download_url(genefileNmRoot + '_slimTab.txt'),
	     "term_page": get_download_url(genefileNmRoot + '_slimTerms.txt'),
	     "gene_input_page": get_download_url(genefileNmRoot + '.lst'),
	     "slim_input_page": get_download_url(slimInputFile) }

    



