import json
import os
import socket
from flask import send_from_directory, Response

dataDir = '/var/www/data/'
binDir = '/var/www/bin/'
tmpDir = '/var/www/tmp/'
rootUrl = 'https://' + socket.gethostname().replace('-2a', '') + '/'
# rootUrl = 'https://gotermfinder.dev.yeastgenome.org/'

gaf = dataDir + 'gene_association.sgd'
gtfScript = binDir + 'GOTermFinder.pl'    

geneList = tmpDir + str(os.getpid()) + '.lst'
gene4bgList = tmpDir + str(os.getpid()) + '_4bg.lst'
tmpTab = tmpDir + str(os.getpid()) + '_tab.txt'

def set_download_file(filename):

    if filename.endswith('.ps'): # or filename.endswith('.svg'):
        return send_from_directory(tmpDir, filename, as_attachment=True, mimetype='application/text', attachment_filename=(str(filename)))

    if filename.endswith('.png') or filename.endswith('.svg'):
        return send_from_directory(tmpDir, filename, as_attachment=True, mimetype='image/png+svg', attachment_filename=(str(filename)))
        
    f = open(tmpDir + filename, encoding="utf-8")
    content = f.read()
    f.close()
    return "<pre>" + content + "</pre>"
    
def get_download_url(filename):

    return rootUrl + "gotermfinder?file=" + filename

def get_param(request, name):

    p = request.args
    f = request.form
    return f.get(name) if f.get(name) else p.get(name)

def parse_gaf_file(gaf_file):
    
    f = open(gaf_file, encoding="utf-8")
    namemapping = {}
    aliasmapping = {}
    found = {}
    for line in f:
        pieces = line.strip().split('\t')
        if pieces[0].startswith('!'):
            continue
        if pieces[1] in found:
            continue
        found[pieces[1]] = 1
        names = pieces[10].split('|')
        i = 0
        for name in names:
            namemapping[name] = pieces[2]
            if i > 0:
                aliasmapping[name] = pieces[2]
            
            i = i + 1
        namemapping[pieces[1]] = pieces[2]
        aliasmapping[pieces[1]] = pieces[2]
    
    f.close()

    return (namemapping, aliasmapping)

def create_gene_list(genelist_file, genes, namemapping, aliasmapping):

    fw = open(genelist_file, 'w')
    
    genes = genes.split('|')
    found = {}
    for gene in genes:
        name = gene
        if gene in namemapping:
            name = namemapping[gene]
        if name in found:
            continue
        found[name] = 1
        if gene in aliasmapping:
            gene = aliasmapping[gene]
        fw.write(gene + "\n")
    fw.close()
    
def get_html_content():

    htmlFile = tmpDir + str(os.getpid()) + '.html'
    imageHtmlFile = tmpDir + str(os.getpid()) + '_ImageHtml.html'
    imageFile = tmpDir + str(os.getpid()) + '_Image.html'

    ## get rid of html and body tags in html file
    f = open(htmlFile, encoding="utf-8")
    html = f.read()
    f.close()
    
    html = html.replace("<html><body>", "").replace("</body></html>", "")
    html = html.replace("color=red", "color=maroon")
    html = html.replace('<a name="table" />', '')
    html = html.replace("infowin", "_extwin")

    ## fix image URL in image file and get rid of html and body tags
    f = open(imageFile, encoding="utf-8")
    image = f.read()
    f.close()

    image = image.replace("<img src='./", "<img src='" + rootUrl + "gotermfinder?file=")

    fw = open(imageFile, "w")
    fw.write(image)
    fw.close()
    
    image = image.replace("<html><body>", "").replace("</body></html>", "")
    image = "<b>Nodes" + image.split("</font><br><br><b>Nodes")[1]

    ## fix image URL in imageHtml file
    f = open(imageHtmlFile, encoding="utf-8")
    imageHtml = f.read()
    f.close()

    imageHtml = imageHtml.replace("<img src='./", "<img src='" + rootUrl + "gotermfinder?file=")

    fw = open(imageHtmlFile, "w")
    fw.write(imageHtml)
    fw.close()
    
    return (html, image)

def enrichment_search(request):
    
    genes = get_param(request, 'genes')
    genes = genes.upper().replace('SGD:', '')
    aspect = get_param(request, 'aspect')
    if aspect is None:
        aspect = 'P'
    (namemapping, aliasmapping) = parse_gaf_file(gaf)
    create_gene_list(geneList, genes, namemapping, aliasmapping)

    cmd = gtfScript + ' -a ' + aspect + ' -g ' + gaf + ' -t ' + tmpDir + ' ' + geneList + ' -F'
    output = os.popen(cmd).read()
    
    f = open(tmpTab)
    data = []
    for line in f:
        if line.startswith('GOID'):
            continue
        pieces = line.strip().split('\t')
        pvalue = ''
        if 'e-' in pieces[2]:
            ## if it is in scientific notation, we want up to two of the decimal places 
            # 6.036693772627e-26
            pvalue_raw = pieces[2].split('.')
            pvalue = pvalue_raw[0] + '.' + pvalue_raw[1][0:2] + 'e-' + pvalue_raw[1].split('e-')[1]
        elif '.' in pieces[2]:
            # otherwise, we'll take up to five decimal places
            pvalue_raw = pieces[2].split('.')
            pvalue = pvalue_raw[0] + '.' + pvalue_raw[1][0:5]
        else:
            pvalue = pieces[2]
        data.append({ 'goid': pieces[0],
                      'term': pieces[1],
                      'pvalue': pvalue,
                      'num_gene_annotated': pieces[4] })
    f.close()

    return data

def gtf_search(request):

    # 'COR5|CYT1|Q0105|QCR2|S000001929|S000002937|S000003809|YEL024W|YEL039C|YGR183C|YHR001W-A'

    genes = get_param(request, 'genes')
    if genes is None:
        return { " ERROR": "NO GENE NAME PASSED IN" }
    genes = genes.upper().replace('SGD:', '')
    
    aspect = get_param(request, 'aspect')
    if aspect is None:
        aspect = 'F'        
    (namemapping, aliasmapping) = parse_gaf_file(gaf)
    create_gene_list(geneList, genes, namemapping, aliasmapping)

    genes4bg = get_param(request, 'genes4bg')
    evidence = get_param(request, 'evidence')
    FDR = get_param(request, 'PDR')
    pvalue = get_param(request, 'pvalue')
    if pvalue is None:
        pvalue = 0.01
        
    option = ""
    if pvalue == "" and pvalue != 0.01:
        option = " -p " + pvalue

    if genes4bg:
        genes4bg = genes4bg.replace('|', '\n')
        fw = open(gene4bgList, 'w')
        fw.write(genes4bg + "\n")
        fw.close()
        option = option + " -b " + gene4bgList
    
    if evidence:
        if evidence.endswith('|'):
            evidence = evidence[0:-1]
        if evidence.startswith('|'):
            evidence = evidence[1:]
        evidence = evidence.replace('|', ',')
        option = option + " -e " + evidence
    
    if FDR == 1:
        option = option + " -F"
        
    # only create html page
    # my $cmd = "$gtfScript -a $aspect -g $gaf -t $tmpDir $geneList -h";
    # create image plus html page
    cmd = gtfScript + ' -a ' + aspect + ' -g ' + gaf + ' -t ' + tmpDir + ' ' + geneList + ' -v'
    if option != '':
    	cmd = cmd + option

    output = os.popen(cmd).read()

    # return { "cmd": cmd,
    #         "output": output }
    
    if 'No significant GO terms' in output:
        if 'were found for your input list of genes.' in output:
            output = output.split('were found for your input list of genes')[0] + ' were found for your input list of genes.'
        else:
            output = "No significant GO terms were found for your input list of genes."
        return { "output": output }
    # elif os.path.exists(tmpTab):
    #    return  { "output": "<pre>" + output + "</pre>" }
    else:
        (html, imageHtml) = get_html_content()        
        return { "html": html,
                 "image_html": imageHtml,
		 "image_page": get_download_url(str(os.getpid())+'_Image.html'),
		 "tab_page": get_download_url(str(os.getpid())+'_tab.txt'),
		 "term_page": get_download_url(str(os.getpid())+'_terms.txt'),
                 "table_page": get_download_url(str(os.getpid())+'.html'),
		 "png_page": get_download_url(str(os.getpid())+'.png'),
		 "svg_page": get_download_url(str(os.getpid())+'.svg'),
		 "ps_page": get_download_url(str(os.getpid())+'.ps'),
		 "input_page": get_download_url(str(os.getpid())+'.lst') }
    
    




