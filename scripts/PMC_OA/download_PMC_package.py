import urllib.request
import gzip
import shutil
import tarfile
import os

working_directory ='pdf_download/'
pdf_directory = '../pdf/'

infile = '../data/pmcid_to_oa_url_for_new_papers.lst'

def download_pdf():

    os.chdir(working_directory)
    
    f = open(infile)
    for line in f:
        download_one_pdf(line)
    
def download_one_pdf(line):

    ## PMC5695854 29167799  2017  ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/00/33/PMC5695854.tar.gz
    ## PMC7332886 32670337  2020  ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/00/3c/PMC7332886.tar.gz

    [pmc, pmid, year, url] = line.strip().split('\t')
    [url_path, file_name] = url.split('/PMC')
    url_path = url_path	+ '/'
    file_name = 'PMC' + file_name
    
    # url_path = 'ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/00/33/'
    # file_name = 'PMC5695854.tar.gz'
    file_dir = file_name.replace('.tar.gz', '')
    pdf_file = pdf_directory + pmid + '.pdf'

    if os.path.isfile(pdf_file):
        print ("PDF is alresdy downloaded: ", line)
        return

    try:
        urllib.request.urlretrieve(url_path + file_name, file_name)
        urllib.request.urlcleanup()
    except:
        print ("ERROR downloading gzipped tar file: ", line)
        return
    try:
        tf = tarfile.open(file_name)
        tf.extractall()
    except:
        print ("ERROR found when untaring file: ", line)
        return
    
    pdf_files = []

    to_exclude_list = ["supplement", "_supp", ".sapp.pdf"]
    to_exclude_starter = ["supp_", "presentation", "image_", "table_", "datasheet", "data_sheet"]
    for filename in os.listdir(file_dir):
        if filename == 'main.pdf':
            pdf_files = [filename]
            break
        if filename.endswith(".pdf"):
            found = 0
            for keyword in to_exclude_list:
                if keyword in filename.lower():
                    found = 1
                    break
            if found == 1:
                continue
            found = 0
            for keyword in to_exclude_starter:
                if filename.lower().startswith(keyword):
                    found = 1
                    break
            if found == 1:
                continue
            pdf_files.append(filename)
    if len(pdf_files) == 1:
        filename = pdf_files[0]
        shutil.copy(file_dir + '/' + filename, pdf_file)
        print ("FOUND one PDF: ", line)
    elif len(pdf_files) > 1:
        right_pdf = ''
        print (pdf_files)
        for file in pdf_files:
            if right_pdf == '':
                right_pdf = file
            elif len(file) < len(right_pdf):
                right_pdf = file
        if right_pdf != '':
            print ("right_pdf="+right_pdf)
            right_pdf_root = right_pdf.replace('.pdf', '').replace('_Article', '').lower()
            bad = 0
            for file in pdf_files:
                if file == right_pdf:
                    continue
                if not file.lower().startswith(right_pdf_root):
                   bad = 1
                   break
            if bad == 0:
                shutil.copy(file_dir + '/' + right_pdf, pdf_file)
                print ("Picked one good PDF: ", line)
            else:
                print (pdf_files)
                print ("Need manual check/pick PDF: ", line)
        else:
            print ("No good PDF found: ", line)
    else:
        print ("NO PDF FOUND: ", line)

if __name__ == "__main__":
        
    download_pdf()

    
        
