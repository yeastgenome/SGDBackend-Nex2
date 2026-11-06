import datetime
import json
import unittest
from collections import namedtuple

import mock
from pyramid import testing

from src.views import references_created_in_sgd

Row = namedtuple('Row', ['sgdid', 'pmid', 'doi', 'display_name', 'date_created', 'created_by'])


class ReferencesCreatedInSgdTest(unittest.TestCase):
    # /references/created_in_sgd?days=N lists the S000 references SGD created
    # itself, so ABC can add them with the same SGD ID (SCRUM-6830 follow-up)

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @mock.patch('src.models.DBSession.query')
    def test_lists_references_created_in_sgd(self, mock_query):
        created = datetime.datetime(2026, 3, 1, 16, 13, 6)
        mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            Row('S000382006', 39322276, '10.1000/x', 'Smith J, et al. (2024)', created, 'OTTO'),
            Row('S000390001', None, None, 'Personal communication', created, 'CURATOR1'),
        ]
        request = testing.DummyRequest(params={'days': '30'})
        response = references_created_in_sgd(request)

        self.assertEqual(response['days'], 30)
        self.assertEqual(response['references'], [
            {'sgdid': 'SGD:S000382006', 'pmid': 'PMID:39322276', 'doi': '10.1000/x',
             'display_name': 'Smith J, et al. (2024)', 'date_created': '2026-03-01 16:13:06',
             'created_by': 'OTTO'},
            {'sgdid': 'SGD:S000390001', 'pmid': None, 'doi': None,
             'display_name': 'Personal communication', 'date_created': '2026-03-01 16:13:06',
             'created_by': 'CURATOR1'},
        ])
        # the window starts `days` days back and only S000 IDs are selected
        criteria = [str(c) for c in mock_query.return_value.filter.call_args[0]]
        self.assertTrue(any('like' in c.lower() for c in criteria))
        start = datetime.datetime.strptime(response['start'], '%Y-%m-%d')
        self.assertEqual((datetime.datetime.today() - start).days, 30)

    @mock.patch('src.models.DBSession.query')
    def test_days_defaults_to_seven(self, mock_query):
        mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        response = references_created_in_sgd(testing.DummyRequest())
        self.assertEqual(response['days'], 7)
        self.assertEqual(response['references'], [])

    def test_rejects_a_bad_days_value(self):
        for days in ('0', '-3', 'week'):
            response = references_created_in_sgd(testing.DummyRequest(params={'days': days}))
            self.assertEqual(response.status_code, 400)
            self.assertIn('days must be a positive integer', json.loads(response.body)['error'])
