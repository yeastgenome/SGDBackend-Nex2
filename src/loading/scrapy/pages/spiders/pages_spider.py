import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor, defer
from sqlalchemy import create_engine, and_
import os
import traceback
from custom_logger import setup_logger
from pathlib import Path

from src.models import Apo, DBSession, Dnasequenceannotation, Go, Locusdbentity, Phenotype, Referencedbentity, Straindbentity

HEADER_OBJ = {'X-Forwarded-Proto': 'https'}

engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600, pool_size=2)
DBSession.configure(bind=engine)

# setup logs
format_str = '%(asctime)s: %(levelname)-5.5s: %(name)s: %(funcName)s: %(message)s'
file_path = os.environ.get("WORKER_LOG_FILE", "/worker.log")
dev_env = os.environ.get("ENV", "prod")
mod_path = file_path
if dev_env == "dev" or dev_env == "test":
    mod_path = os.path.join(Path.cwd(), file_path[1:])
    
spider_logger = setup_logger('spider_logger', mod_path, format_str)


# init spiders
class BaseSpider(scrapy.Spider):
    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'CONCURRENT_REQUESTS': 16
    }

    def get_entities(self):
        return []

    def start_requests(self):
        entities = self.get_entities()
        for entity in entities:
            index = entities.index(entity)
            if (index % 100 == 0):
                percent_done = str(float(index) / float(len(entities)) * 100)
                spider_logger.info('CHECKIN STATS: ' + percent_done + '% of current index complete')
            urls = entity.get_all_cache_urls(True)
            for url in urls:
                yield scrapy.Request(url=url, headers=HEADER_OBJ, method='PURGE', callback=self.parse)

    def parse(self, response):
        url = response.request.url
        # # to debug latency
        # latency = response.request.meta['download_latency']
        if response.status != 200:
            spider_logger.error('error on ' + response.url)


class GenesSpider(BaseSpider):
    name = 'genes'

    def get_entities(self):
        spider_logger.info('getting genes')
        attempts = 0
        while attempts < 3:
            try:
                # get S288C genes
                gene_ids_so = DBSession.query(Dnasequenceannotation.dbentity_id, Dnasequenceannotation.so_id).filter(Dnasequenceannotation.taxonomy_id == 274901).all()
                dbentity_ids_to_so = {}
                dbentity_ids = set([])
                so_ids = set([])
                for gis in gene_ids_so:
                    dbentity_ids.add(gis[0])
                    so_ids.add(gis[1])
                    dbentity_ids_to_so[gis[0]] = gis[1]
                all_genes = DBSession.query(Locusdbentity).filter(Locusdbentity.dbentity_id.in_(list(dbentity_ids)), Locusdbentity.dbentity_status == 'Active').all()
                break
            except Exception:
                spider_logger.error('DB Error', exc_info=True)
                DBSession.rollback()
                attempts += 1
        return all_genes


class GoSpider(BaseSpider):
    name = 'go'

    def get_entities(self):
        spider_logger.info('getting gos')
        attempts = 0
        while attempts < 3:
            try:
                gos = DBSession.query(Go).all()
                break
            except Exception:
                spider_logger.error('DB Error', exc_info=True)
                DBSession.rollback()
                attempts += 1
        return gos


class ObservableSpider(BaseSpider):
    name = 'observable'

    def get_entities(self):
        spider_logger.info('getting observables')
        attempts = 0
        while attempts < 3:
            try:
                observables = DBSession.query(Apo).filter_by(apo_namespace="observable").all()
                break
            except Exception:
                spider_logger.error('DB Error', exc_info=True)
                DBSession.rollback()
                attempts += 1
        return observables


class PhenotypeSpider(BaseSpider):
    name = 'phenotype'

    def get_entities(self):
        spider_logger.info('getting phenotypes')
        attempts = 0
        while attempts < 3:
            try:
                phenotypes = DBSession.query(Phenotype).all()
                break
            except Exception:
                spider_logger.error('DB Error', exc_info=True)
                DBSession.rollback()
                attempts += 1
        return phenotypes


class YeastgenomeSite(BaseSpider):

    def get_entities(self):
       return ['https://www.yeastgenome.org/locus/S000001855']
    

runner = CrawlerRunner()


def crawl_test():
    # yield runner.crawl(YeastgenomeSite)
    # reactor.stop
    spider_logger.info('Crawler is logging')


@defer.inlineCallbacks
def crawl():
    yield runner.crawl(GoSpider)
    yield runner.crawl(ObservableSpider)
    yield runner.crawl(PhenotypeSpider)
    yield runner.crawl(GenesSpider)
    reactor.stop()


if __name__ == '__main__':
    crawl()
    reactor.run()
