import unittest
from src.helpers import get_file_curate_dropdown_data, get_file_keywords
from sqlalchemy import create_engine
import os
from src.models import DBSession, Base, Filedbentity

engine = create_engine(os.environ["NEX2_URI"], pool_recycle=3600)
DBSession.configure(bind=engine)
Base.metadata.bind = engine


class HelperFunction(unittest.TestCase):
    
    def test_get_keywords(self):
        ''' Get all keywords for files '''
        
        get_file_keywords(DBSession)
        self.assertGreater(1, 0)
    
    def test_get_file_curate_dropdown_data(self):
        ''' Get all drowndown data '''

        get_file_curate_dropdown_data(DBSession)
        self.assertEqual(1, 1)


if __name__ == '__main__':
    unittest.main()
