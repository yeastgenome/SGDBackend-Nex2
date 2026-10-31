import json
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'loading', 'dataset'))
import compute_coexpression as cc  # noqa: E402


class DatasetZscoresTest(unittest.TestCase):

    def test_correlated_genes_score_high_and_sparse_genes_are_dropped(self):
        rng = np.random.default_rng(0)
        base = rng.normal(size=12)
        matrix = np.vstack([base, base * 2 + 0.01 * rng.normal(size=12), -base,
                            rng.normal(size=(20, 12))])
        sparse = np.full(12, np.nan)
        sparse[:3] = 1.0                          # 25% coverage -> filtered out
        matrix = np.vstack([matrix, sparse])
        kept, z = cc.dataset_zscores(matrix, min_coverage=0.7)
        self.assertNotIn(len(matrix) - 1, kept)
        self.assertGreater(z[0, 1], 3)            # near-identical profiles
        self.assertLess(z[0, 2], -3)              # anti-correlated
        self.assertEqual(z[0, 0], 0)              # diagonal cleared
        upper = z[np.triu_indices(len(kept), k=1)]
        self.assertAlmostEqual(float(upper.mean()), 0, places=4)
        self.assertAlmostEqual(float(upper.std()), 1, places=3)

    def test_zero_fraction(self):
        matrix = np.array([[0.0, 0.0, 1.0], [np.nan, 0.0, 2.0]])
        self.assertAlmostEqual(cc.zero_fraction(matrix), 0.6)
        self.assertEqual(cc.zero_fraction(np.full((2, 2), np.nan)), 1.0)


class ScoringTest(unittest.TestCase):

    def setUp(self):
        # genes 0..3; gene 3 is only measured in 5 datasets
        self.counts = np.array([[100, 100, 30, 5],
                                [100, 100, 30, 5],
                                [30, 30, 30, 5],
                                [5, 5, 5, 5]], dtype=np.uint16)
        self.sums = np.array([[0, 150, 60, 50],
                              [150, 0, 30, 0],
                              [60, 30, 0, 0],
                              [50, 0, 0, 0]], dtype=np.float32)

    def test_min_datasets_and_min_shared(self):
        scores = cc.score_matrix(self.sums, self.counts, min_datasets=20, min_shared=0.3, prior=0)
        self.assertAlmostEqual(float(scores[0, 1]), 1.5)
        self.assertAlmostEqual(float(scores[0, 2]), 2.0)
        shrunk = cc.score_matrix(self.sums, self.counts, min_datasets=20, min_shared=0.3, prior=50)
        self.assertAlmostEqual(float(shrunk[0, 1]), 1.0)     # 150 / (100 + 50)
        self.assertAlmostEqual(float(shrunk[0, 2]), 0.75)    # 60 / (30 + 50): less evidence, ranks lower
        self.assertEqual(scores[0, 3], -np.inf)   # only 5 shared datasets
        self.assertEqual(scores[0, 0], -np.inf)
        # required = max(min_datasets, min_shared * datasets of the less-measured gene)
        strict = cc.score_matrix(self.sums, self.counts, min_datasets=20, min_shared=1.1, prior=0)
        self.assertEqual(strict[0, 2], -np.inf)   # 30 shared < 1.1 * 30
        self.assertEqual(strict[0, 1], -np.inf)   # 100 shared < 1.1 * 100
        self.assertTrue(np.isfinite(cc.score_matrix(self.sums, self.counts, 20, 0.5, 0)[0, 2]))

    def test_gene_json(self):
        scores = cc.score_matrix(self.sums, self.counts, min_datasets=20, min_shared=0.3, prior=0)
        ids = np.array([11, 12, 13, 14])
        active = {g: ('S%09d' % g, 'Y%d' % g, 'G%d' % g, 'G%d' % g, 'headline %d' % g) for g in ids}
        data = cc.gene_json(0, ids, scores, self.counts, active, top=10, network_size=1, metadata={})
        self.assertEqual([p['systematic_name'] for p in data['partners']], ['Y13', 'Y12'])
        self.assertEqual(data['partners'][0]['rank'], 1)
        self.assertEqual(data['partners'][0]['description'], 'headline 13')
        self.assertEqual(data['locus']['dataset_count'], 100)
        self.assertEqual([n['sgdid'] for n in data['network']['nodes']], ['S000000011', 'S000000013'])
        self.assertTrue(data['network']['nodes'][0]['focus'])
        self.assertEqual(data['network']['edges'], [{'source': 'S000000011', 'target': 'S000000013', 'score': 2.0}])
        self.assertEqual(json.loads(json.dumps(data)), data)   # plain Python types only


if __name__ == '__main__':
    unittest.main()
