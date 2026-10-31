import unittest
from collections import OrderedDict
from unittest import mock

import numpy as np

from src import gene_list_expression as gle


class ClusteringTest(unittest.TestCase):

    def test_groups_correlated_rows_together(self):
        rng = np.random.default_rng(1)
        a, b = rng.normal(size=20), rng.normal(size=20)
        rows = [a + 0.1 * rng.normal(size=20) for _ in range(4)] + [b + 0.1 * rng.normal(size=20) for _ in range(4)]
        shuffled = [rows[i] for i in [0, 4, 1, 5, 2, 6, 3, 7]]   # a b a b a b a b
        matrix = np.array(shuffled)
        matrix[2, 3] = np.nan                                  # missing values are tolerated
        order = gle._average_linkage_order(matrix)
        self.assertEqual(sorted(order), list(range(8)))
        groups = ['a' if i % 2 == 0 else 'b' for i in order]
        self.assertIn(''.join(groups), ('aaaabbbb', 'bbbbaaaa'))

    def test_small_inputs(self):
        self.assertEqual(gle._average_linkage_order(np.zeros((2, 3))), [0, 1])
        self.assertEqual(gle._average_linkage_order(np.zeros((0, 3))), [])


class CategoryTest(unittest.TestCase):

    def test_priority_and_default(self):
        self.assertEqual(gle._category(['transcription', 'heat shock']), 'Stress response')
        self.assertEqual(gle._category(['fermentation']), 'Nutrients & metabolism')
        self.assertEqual(gle._category(['evolution']), 'Other')
        self.assertEqual(gle._category([]), 'Other')


class RankDatasetsTest(unittest.TestCase):

    def setUp(self):
        self.datasets = OrderedDict([
            (1, {'id': 1, 'name': 'responsive', 'accession': 'GSE1', 'link': '/d1', 'category': 'Other',
                 'keywords': [], 'samples': [(11, 's1'), (12, 's2'), (13, 's3')]}),
            (2, {'id': 2, 'name': 'flat', 'accession': 'GSE2', 'link': '/d2', 'category': 'Other',
                 'keywords': [], 'samples': [(21, 's1'), (22, 's2'), (23, 's3')]}),
            (3, {'id': 3, 'name': 'one sample', 'accession': 'GSE3', 'link': '/d3', 'category': 'Other',
                 'keywords': [], 'samples': [(31, 's1')]}),
        ])
        self.values = {(100, 11): -2.0, (100, 12): 0.0, (100, 13): 2.0,
                       (200, 11): -1.0, (200, 12): 0.0, (200, 13): 1.0,
                       (100, 21): 0.1, (100, 22): 0.0, (100, 23): -0.1,
                       (100, 31): 5.0}

    def test_excess_spread_ranking(self):
        baseline = {1: {'sd': 0.5, 'zero_fraction': 0.0}, 2: {'sd': 0.01, 'zero_fraction': 0.0},
                    3: {'sd': 0.1, 'zero_fraction': 0.0}}
        with mock.patch.object(gle, 'get_baseline', return_value=baseline):
            ranked = gle.rank_datasets([100, 200], self.values, self.datasets)
        self.assertEqual([d['id'] for d in ranked], [1, 2])     # dataset 3 has < 2 samples
        top = ranked[0]
        self.assertEqual(top['genes_measured'], 2)
        expected_sd = (np.std([-2, 0, 2]) + np.std([-1, 0, 1])) / 2
        self.assertAlmostEqual(top['mean_sd'], round(expected_sd, 3))
        self.assertAlmostEqual(top['score'], round(expected_sd - 0.5, 2))
        # dataset 2 measures only 1 of 2 genes: still >= MIN_GENE_FRACTION
        self.assertEqual(ranked[1]['genes_measured'], 1)
        self.assertFalse(top['flattened'])

    def test_flattened_datasets_rank_last(self):
        baseline = {1: {'sd': 0.5, 'zero_fraction': 0.6}, 2: {'sd': 0.01, 'zero_fraction': 0.0}}
        with mock.patch.object(gle, 'get_baseline', return_value=baseline):
            ranked = gle.rank_datasets([100, 200], self.values, self.datasets)
        self.assertEqual([(d['id'], d['flattened']) for d in ranked], [(2, False), (1, True)])


class GetListExpressionTest(unittest.TestCase):

    def test_blocks_and_genes_without_data(self):
        loci = {g: {'display_name': 'G%d' % g, 'systematic_name': 'Y%d' % g, 'link': '/locus/%d' % g,
                    'description': ''} for g in (1, 2, 3, 4)}
        datasets = OrderedDict()
        for d_id, samples in ((10, [101, 102, 103, 104]), (20, [201, 202, 203])):
            datasets[d_id] = {'id': d_id, 'name': 'd%d' % d_id, 'accession': 'GSE%d' % d_id, 'link': '/d',
                              'category': 'Other', 'keywords': [], 'samples': [(s, 's%d' % s) for s in samples]}
        rng = np.random.default_rng(2)
        values = {(g, s): float(rng.normal()) for g in (1, 2, 3)
                  for d in datasets.values() for s, _ in d['samples']}
        values[(4, 999)] = 1.0          # gene 4 has data, but not in these datasets
        with mock.patch.object(gle, 'get_lookup', return_value=(loci, {}, {})), \
                mock.patch.object(gle, 'get_datasets', return_value=datasets), \
                mock.patch.object(gle, 'get_baseline', return_value={10: {'sd': 0.1, 'zero_fraction': 0.0},
                                                                     20: {'sd': 0.1, 'zero_fraction': 0.9}}), \
                mock.patch.object(gle, '_fetch_values', return_value=values):
            out = gle.get_list_expression({'bioent_ids': [1, 2, 3, 4, 5]})   # 5 is not an active locus
        # dataset 20 is flattened: kept in the ranking, left out of the default view
        self.assertEqual([d['id'] for d in out['shown_datasets']], [10])
        self.assertTrue(out['ranked_datasets'][-1]['flattened'])
        self.assertEqual(sorted(out['gene_order']), [0, 1, 2])
        self.assertEqual(out['genes_without_data'], [{'index': 3, 'reason': 'not measured in the datasets shown'}])
        order = [out['columns'][j]['dataset_id'] for j in out['column_order']]
        self.assertEqual(sorted(out['column_order']), list(range(4)))
        self.assertEqual(order, sorted(order, key=[d['id'] for d in out['shown_datasets']].index))


if __name__ == '__main__':
    unittest.main()
