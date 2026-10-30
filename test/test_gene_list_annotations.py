import datetime
import unittest
from collections import namedtuple
from decimal import Decimal
from unittest import mock

from src import gene_list_annotations as gla

Cond = namedtuple('Cond', 'group_id condition_class condition_name condition_value condition_unit')

LOCI = {1: {'id': 1, 'sgdid': 'S000001855', 'systematic_name': 'YFL039C', 'gene_name': 'ACT1'},
        2: {'id': 2, 'sgdid': 'S000000364', 'systematic_name': 'YBR160W', 'gene_name': None}}


class FormattingTest(unittest.TestCase):

    def test_reference_and_pmid(self):
        self.assertEqual(gla._reference('S000057660', 12345), 'SGD_REF:S000057660|PMID:12345')
        self.assertEqual(gla._reference('S000057660', None), 'SGD_REF:S000057660')
        self.assertEqual(gla._pmid(12345, 'S000057660'), 'PMID:12345')
        self.assertEqual(gla._pmid(None, 'S000057660'), 'SGD_REF:S000057660')

    def test_clean_collapses_whitespace(self):
        self.assertEqual(gla._clean('a\tb\n c'), 'a b c')
        self.assertEqual(gla._clean(None), '')
        self.assertEqual(gla._clean(3.5), 3.5)
        self.assertEqual(gla._clean(Decimal('34064.8')), 34064.8)
        self.assertEqual(gla._clean(datetime.date(2013, 8, 7)), '2013-08-07')

    def test_group_conditions_matches_download_file(self):
        conds = [Cond(1, 'chemical', 'doxycycline', '10', 'ug/ml'), Cond(1, 'temperature', 'heat', '37', '°C'),
                 Cond(2, 'chemical', 'rapamycin', None, None)]
        self.assertEqual(gla._group_conditions(conds),
                         [('doxycycline (10ug/ml)', 'heat (37°C)'), ('rapamycin', '')])
        self.assertEqual(gla._group_conditions(None), [('', '')])

    def test_names(self):
        with mock.patch.object(gla, 'get_lookup', return_value=(LOCI, {}, {})):
            self.assertEqual(gla._names(1), ('YFL039C', 'ACT1', 'S000001855'))
            self.assertEqual(gla._names(2), ('YBR160W', '', 'S000000364'))
            self.assertEqual(gla._names(99), ('', '', ''))


class GetListAnnotationsTest(unittest.TestCase):

    def setUp(self):
        patcher = mock.patch.object(gla, 'get_lookup', return_value=(LOCI, {}, {}))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.builder = mock.Mock(return_value=[['YFL039C', 'a\tb'], ['YBR160W', None]])
        spec = dict(gla.ANNOTATION_TYPES['go'], columns=['Name', 'Value'], builder=self.builder)
        patcher = mock.patch.dict(gla.ANNOTATION_TYPES, {'go': spec})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_rows_are_cleaned_and_unknown_ids_dropped(self):
        out = gla.get_list_annotations({'data_type': 'go', 'bioent_ids': [1, 2, 2, 99]})
        self.assertEqual(self.builder.call_args[0][0], [1, 2])
        self.assertEqual(out['rows'], [['YFL039C', 'a b'], ['YBR160W', '']])
        self.assertEqual(out['gene_count'], 2)
        self.assertFalse(out['truncated'])
        self.assertEqual(gla.annotations_to_tsv(out), 'Name\tValue\nYFL039C\ta b\nYBR160W\t\n')

    def test_truncation(self):
        with mock.patch.object(gla, 'MAX_ROWS', 1):
            out = gla.get_list_annotations({'data_type': 'go', 'bioent_ids': [1]})
        self.assertEqual(out['row_count'], 1)
        self.assertTrue(out['truncated'])

    def test_validation(self):
        for body in [{'data_type': 'bogus', 'bioent_ids': [1]},
                     {'data_type': 'go'},
                     {'data_type': 'go', 'bioent_ids': [99]},
                     {'data_type': 'go', 'bioent_ids': [1], 'interaction_scope': 'all'},
                     {'data_type': 'go', 'bioent_ids': [1], 'homolog_species': 'Homo sapiens'}]:
            with self.assertRaises(ValueError):
                gla.get_list_annotations(body)

    def test_every_type_is_listed(self):
        keys = [t['key'] for t in gla.list_annotation_types()]
        self.assertEqual(keys[:3], ['gene_info', 'go', 'phenotype'])
        self.assertIn('interaction', keys)


if __name__ == '__main__':
    unittest.main()
