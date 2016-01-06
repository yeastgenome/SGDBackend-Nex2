from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from sqlalchemy import engine_from_config
import os

from .models import DBSession, Base


def main(global_config, **settings):
    engine = os.environ['NEX2_URI']
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings)

    config.add_route('home', '/')
    config.add_route('upload', '/upload')
    config.add_route('colleagues', '/colleagues')

    config.add_route('authorize', '/authorize')

    config.scan()
    config.add_static_view(name='static', path='../static')

    config.configure_celery(global_config['__file__'])

    return config.make_wsgi_app()
