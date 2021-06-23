#!/var/www/FlaskApp/FlaskApp/venv/bin/python3
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/FlaskApp/")
    
from FlaskApp import app as application
application.secret_key = '@@!!ncbi-gotools-server-key!!@@'
