import os
import requests

SUBMISSION_VERSION = os.getenv('SUBMISSION_VERSION')
LINKML_VERSION = os.getenv('LINKML_VERSION')
CURATION_API_TOKEN = os.getenv('CURATION_API_TOKEN')

local_dir = '/Users/kkarra/Dev/SGDBackend-Nex2/scripts/dumping/alliance/data/'

headers = {
    'Authorization': 'Bearer '+ CURATION_API_TOKEN + ''
}

def upload_allele_information():

    print("uploading Alleles file to persistent store")

    file_name = 'SGD' + SUBMISSION_VERSION + 'allelesPersistent.json'
    json_file_str = os.path.join(local_dir, file_name)

    files = {
        'ALLELE_SGD': open(json_file_str, 'rb'),
    }
    try:
        response = requests.post(
        'https://curation.alliancegenome.org/api/data/submit',
        files=files, headers=headers)

        if response.status_code == 200:
            print('File uploaded successfully')
        else:
            print('Failed to upload file. Status code:', response.status_code)
            print('Response:', response.text)

    except Exception as e:
        print('An error occurred:', str(e))

if __name__ == '__main__':
    upload_allele_information()
