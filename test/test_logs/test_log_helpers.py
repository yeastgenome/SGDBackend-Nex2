
import unittest
import os
from pathlib import Path
from custom_logger import setup_logger
from twisted.internet import reactor, defer


from src.loading.scrapy.pages.spiders.pages_spider import crawl_test
FORMAT = '%(asctime)s: %(levelname)s: %(name)s: %(funcName)s: %(message)s'


class TestLogHelpers(unittest.TestCase):

    def test_single_log_file(self):
        custom_format = FORMAT
        file_path = os.environ.get("TEST_LOG_FILE", "/test.log")
        mod_path = os.path.join(Path.cwd().parent.parent, file_path[1:])
        test_logger = setup_logger(
            'test_logger', mod_path, custom_format, "DEBUG", False)
        msg = "Test single log"
        test_logger.info("Test single log")
        test_logger.debug("Debug the bug")
        test_logger.error("err found")

    def test_worker_log_file(self):
        custom_format = FORMAT
        file_path = os.environ.get("WORKER_LOG_FILE", "/worker.log")
        mod_path = os.path.join(Path.cwd().parent.parent, file_path[1:])
        worker_logger = setup_logger(
            'worker_logger', mod_path, custom_format, "DEBUG", False)
        msg = "Test single log"
        worker_logger.info("Test single log")
        worker_logger.error("Test error log")

        '''
        with open(mod_path) as test_file:
            for line in test_file:
                self.assertIn(msg, line, "line not found in file")
                break
        '''
    
    def test_app_log_file(self):
        custom_format = FORMAT
        file_path = os.environ.get("APP_LOG_FILE", "/app.log")
        mod_path = os.path.join(Path.cwd().parent.parent, file_path[1:])
        app_logger = setup_logger(
            'app_logger', mod_path, custom_format, "DEBUG", False)
        msg = "Test single log"
        app_logger.info("Test single log")
        app_logger.error("Test error log")

    def test_script_log_file(self):
        custom_format = FORMAT
        file_path = os.environ.get(
            "SCRIPT_LOG_FILE", "/python_custom_script.log")
        mod_path = os.path.join(Path.cwd().parent.parent, file_path[1:])
        script_logger = setup_logger(
            'script_logger', mod_path, custom_format, "DEBUG", False)
        msg = "Test single log"
        script_logger.info("Test single log")
        script_logger.error("Test error log")

    def test_stream_log(self):
        custom_format = FORMAT
        file_path = os.environ.get(
            "SCRIPT_LOG_FILE", "/python_custom_script.log")
        mod_path = os.path.join(Path.cwd().parent.parent, file_path[1:])
        script_logger = setup_logger(
            'script_logger', mod_path, custom_format, "DEBUG", False)
        script_logger.info("Stream information")
        script_logger.error("Stream error")
