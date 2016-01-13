import hashlib
import werkzeug
import os
import shutil
import tempfile
from pyramid.httpexceptions import HTTPForbidden
from .models import DBSession, Dbuser

def md5(fname):
    hash = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), ""):
            hash.update(chunk)
    return hash.hexdigest()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[-1] in ['bed', 'bedgraph', 'bw', 'cdt', 'chain', 'cod', 'csv', 'cusp', 'doc', 'docx', 'fsa', 'gb', 'gcg', 'gff', 'gif', 'gz', 'html', 'jpg', 'pcl', 'pdf', 'pl', 'png', 'pptx', 'README', 'sql', 'sqn', 'tgz', 'txt', 'vcf', 'wig', 'wrl', 'xls', 'xlsx', 'xml', 'sql', 'txt', 'fsa', 'gff', 'html', 'gz', 'tsv']

def secure_save_file(file, filename):
    filename = werkzeug.secure_filename(filename)
    temp_file_path = os.path.join(tempfile.gettempdir(), filename)

    file.seek(0)
    with open(temp_file_path, 'wb') as output_file:
	shutil.copyfileobj(file, output_file)

    return temp_file_path

def curator_or_none(email):
    user = DBSession.query(Dbuser).filter(Dbuser.email == email).first()
    if (user and user.status == 'Current'):
        return user
    else:
        return None

def authenticate_decorator(view_callable):
    def inner(context, request):
        if 'email' not in request.session or 'username' not in request.session:
            return HTTPForbidden()
    return inner
