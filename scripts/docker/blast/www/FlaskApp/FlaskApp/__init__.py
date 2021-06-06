#!/var/www/FlaskApp/FlaskApp/venv/bin/python3
import json
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0,"/var/www/FlaskApp/FlaskApp")
from blast import run_blast, get_seq, get_config

app = Flask(__name__)

## to solve Cross Origin Resource issue
CORS(app)  

@app.route('/')
def hello():
    return "Hello, we all love SGD!!"

@app.route('/blast_search', methods=['GET', 'POST'])
def blast_search():

    p = request.args
    
    if p.get('name') and p.get('program') is None:
        data = get_seq(p.get('name'), p.get('type'))
        return jsonify(data)
        # https://blast.dev.yeastgenome.org/blast_search?name=S000000001&type=protein
        # https://blast.dev.yeastgenome.org/blast_search?name=YFL039C
        
    if p.get('conf') and p.get('program') is None:
        data = get_config(p.get('conf'))
        return jsonify(data)
        # https://blast.dev.yeastgenome.org/blast_search?conf=blast-sgd
        # https://blast.dev.yeastgenome.org/blast_search?conf=blast-fungal

    # https://blast.dev.yeastgenome.org/blast_search?seq=CACCATCCCATTTAACTGTAAGAAGAATTGC&database=YeastORF-Genomic&program=blastn
    
    data = run_blast(request)
    return jsonify(data)
    
if __name__ == '__main__':
    app.run()
