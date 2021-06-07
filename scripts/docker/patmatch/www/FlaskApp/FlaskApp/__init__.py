#!/var/www/FlaskApp/FlaskApp/venv/bin/python3
import json
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

sys.path.insert(0,"/var/www/FlaskApp/FlaskApp")
from patmatch import run_patmatch, get_config, get_sequence, set_download_file
from restrictionmapper import run_restriction_site_search 

app = Flask(__name__)

## to solve Cross Origin Resource issue
CORS(app)  

@app.route('/')
def hello():
    return "Hello, we all love SGD!!"

@app.route('/patmatch', methods=['GET', 'POST'])
def patmatch():

    p = request.args
            
    if p.get('conf'):
        data = get_config(p.get('conf'))
        return jsonify(data)

    if p.get('file'):
        response = set_download_file(p.get('file'))
        return response
    
    if p.get('seqname'):
        data = get_sequence(p.get('dataset'), p.get('seqname'))
        return jsonify(data)
    
    data = run_patmatch(request)
    return jsonify(data)


@app.route('/restrictionmapper', methods=['GET', 'POST'])
def restrictionmapper():

    p = request.args
    
    if p.get('file'):
        response = set_download_file(p.get('file'))
        return response
    
    data = run_restriction_site_search(request)
    return jsonify(data)


if __name__ == '__main__':
    app.run()
