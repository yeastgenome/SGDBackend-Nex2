#!/var/www/FlaskApp/FlaskApp/venv/bin/python3
import json
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0,"/var/www/FlaskApp/FlaskApp")
from gotermfinder import gtf_search, enrichment_search, set_download_file
from goslimmapper import gtm_search 

app = Flask(__name__)

## to solve Cross Origin Resource issue
CORS(app)  

@app.route('/')
def hello():
    return "Hello, we all love SGD!!"

@app.route('/gotermfinder', methods=['GET', 'POST'])
def gotermfinder():

    p = request.args
    if p.get('file'):
        response = set_download_file(p.get('file'))
        return response
    
    data = gtf_search(request)
    return jsonify(data)


@app.route('/termfinder', methods=['GET', 'POST'])
def goenrichment():

    data = enrichment_search(request)
    return jsonify(data)

@app.route('/goslimmapper', methods=['GET', 'POST'])
def goslimmapper():

    p = request.args
    if p.get('file'):
        response = set_download_file(p.get('file'))
        return response
    
    data = gtm_search(request)
    return jsonify(data)


if __name__ == '__main__':
    app.run()
