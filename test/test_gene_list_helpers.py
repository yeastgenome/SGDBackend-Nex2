import threading
import unittest
from fractions import Fraction
from math import comb
from unittest import mock

from src import gene_list_helpers as glh


def _locus(locus_id, systematic_name, gene_name):
    return {'id': locus_id, 'sgdid': 'S%09d' % locus_id, 'systematic_name': systematic_name,
            'gene_name': gene_name, 'display_name': gene_name or systematic_name, 'qualifier': 'Verified',
            'description': '', 'link': '/locus/S%09d' % locus_id}


LOCI = {1: _locus(1, 'YFL039C', 'ACT1'), 2: _locus(2, 'YBR160W', 'CDC28'),
        3: _locus(3, 'YJL030W', 'MAD2'), 4: _locus(4, 'YBR098W', 'MMS4'),
        5: _locus(5, 'YAR000W', None)}
INDEX = {
    'YFL039C': {(1, 'systematic name')}, 'ACT1': {(1, 'gene name')}, 'S000000001': {(1, 'SGDID')},
    'ACT1P': {(1, 'protein name')}, 'P60010': {(1, 'UniProtKB ID')},
    'CDC28': {(2, 'gene name')}, 'CDK1': {(2, 'alias')},
    'MAD2': {(3, 'gene name'), (2, 'alias')},
    'SHARED': {(1, 'alias'), (3, 'alias')},
    'YBR100W': {(4, 'alias'), (4, 'merged into')},
}
RETIRED = {'YCR029C': {'status': 'deleted', 'systematic_name': 'YCR029C', 'sgdid': 'S000000624'}}


def exact_sf(k, N, K, n):
    return float(sum(Fraction(comb(K, i) * comb(N - K, n - i), comb(N, n)) for i in range(k, min(K, n) + 1)))


class StatsTest(unittest.TestCase):

    def test_hypergeom_sf_matches_exact(self):
        for args in [(15, 6550, 333, 34), (2, 1868, 2, 21), (1, 100, 10, 10), (5, 50, 20, 10)]:
            self.assertAlmostEqual(glh.hypergeom_sf(*args) / exact_sf(*args), 1.0, places=9)

    def test_hypergeom_sf_edges(self):
        self.assertEqual(glh.hypergeom_sf(0, 10, 3, 3), 1.0)
        self.assertEqual(glh.hypergeom_sf(4, 10, 3, 3), 0.0)

    def test_benjamini_hochberg(self):
        self.assertEqual(glh.benjamini_hochberg([0.01, 0.04, 0.03, 0.005], 4), [0.02, 0.04, 0.04, 0.02])
        # untested terms count toward the number of tests
        self.assertEqual(glh.benjamini_hochberg([0.01], 10), [0.1])


class ResolveTest(unittest.TestCase):

    def setUp(self):
        patcher = mock.patch.object(glh, 'get_lookup', return_value=(LOCI, INDEX, RETIRED))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_split_identifiers(self):
        self.assertEqual(glh.split_identifiers(['ACT1, cdc28;act1', '"MAD2"\nYFL039C']),
                         ['ACT1', 'cdc28', 'MAD2', 'YFL039C'])

    def test_statuses(self):
        out = glh.resolve_identifiers('act1 SGD:S000000001 Act1p P60010 CDK1 SHARED YBR100W YCR029C NOPE')
        by_input = {r['input']: r for r in out['results']}
        self.assertEqual(by_input['act1']['match_type'], 'gene name')
        self.assertEqual(by_input['SGD:S000000001']['loci'][0]['id'], 1)
        self.assertEqual(by_input['Act1p']['match_type'], 'protein name')
        self.assertEqual(by_input['CDK1']['loci'][0]['id'], 2)
        self.assertEqual(by_input['SHARED']['status'], 'ambiguous')
        self.assertEqual(len(by_input['SHARED']['loci']), 2)
        self.assertEqual(by_input['YBR100W']['match_type'], 'merged into')
        self.assertEqual(by_input['YCR029C']['status'], 'retired')
        self.assertEqual(by_input['NOPE']['status'], 'not_found')
        self.assertEqual(out['resolved_ids'], [1, 2, 4])
        self.assertEqual(out['summary']['matched'], 6)

    def test_gene_name_beats_alias_but_is_flagged(self):
        row = glh.resolve_identifiers(['MAD2'])['results'][0]
        self.assertEqual(row['status'], 'matched')
        self.assertEqual(row['loci'][0]['id'], 3)
        self.assertEqual([x['id'] for x in row['also_alias_of']], [2])

    def test_too_many_identifiers(self):
        with self.assertRaises(ValueError):
            glh.resolve_identifiers(['G%d' % i for i in range(glh.MAX_INPUT_IDENTIFIERS + 1)])


class EnrichmentTest(unittest.TestCase):

    def setUp(self):
        terms = {'T1': {'id': 'T1', 'display_name': 'term one', 'link': '/t1'},
                 'T2': {'id': 'T2', 'display_name': 'term two', 'link': '/t2'}}
        term_genes = {'T1': frozenset([1, 2, 3]), 'T2': frozenset([4, 5])}
        sets = (terms, term_genes, frozenset([1, 2, 3, 4, 5]))
        for target, value in [('get_lookup', (LOCI, INDEX, RETIRED)), ('get_annotation_sets', sets)]:
            patcher = mock.patch.object(glh, target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_counts_and_pvalue(self):
        out = glh.enrich_category('phenotype', [1, 2, 3], fdr_cutoff=1.0)
        self.assertEqual(out['list_annotated'], 3)
        self.assertEqual(out['background_total'], 5)
        self.assertEqual(out['terms_tested'], 2)
        row = out['results'][0]
        self.assertEqual(row['term']['id'], 'T1')
        self.assertEqual((row['list_count'], row['background_count']), (3, 3))
        self.assertAlmostEqual(row['pvalue'], exact_sf(3, 5, 3, 3))
        self.assertEqual([g['display_name'] for g in row['genes']], ['ACT1', 'CDC28', 'MAD2'])

    def test_custom_background_restricts_universe(self):
        out = glh.enrich_category('phenotype', [1, 2], background_ids=frozenset([1, 2, 3, 4]), fdr_cutoff=1.0)
        self.assertEqual(out['background_total'], 4)
        self.assertEqual(out['results'][0]['background_count'], 3)

    def test_go_rows_are_numeric_and_filtered(self):
        rows = [{'go': {'id': 'GO:2', 'display_name': 'b', 'link': '/go/GO:2'}, 'match_count': '3', 'pvalue': '0.2'},
                {'go': {'id': 'GO:1', 'display_name': 'a', 'link': '/go/GO:1'}, 'match_count': '14',
                 'pvalue': '9.35e-31'}]
        with mock.patch.object(glh, 'run_batter_enrichment', return_value=rows) as batter:
            out = glh.enrich_go('go_function', [1, 2], fdr_cutoff=0.05)
        self.assertEqual(batter.call_args[1]['aspect'], 'F')
        self.assertEqual(batter.call_args[0][0], ['YFL039C', 'YBR160W'])
        self.assertEqual([(r['term']['id'], r['list_count'], r['pvalue']) for r in out['results']],
                         [('GO:1', 14, 9.35e-31)])

    def test_run_list_enrichment_validates_input(self):
        with self.assertRaises(ValueError):
            glh.run_list_enrichment({})
        with self.assertRaises(ValueError):
            glh.run_list_enrichment({'bioent_ids': [1], 'categories': ['bogus']})
        out = glh.run_list_enrichment({'genes': 'ACT1 CDC28 MAD2', 'categories': ['phenotype'], 'fdr_cutoff': 1})
        self.assertEqual(out['resolution_summary']['unique_loci'], 3)
        self.assertEqual(out['categories'][0]['results'][0]['term']['id'], 'T1')


class CachedTest(unittest.TestCase):

    def setUp(self):
        patcher = mock.patch.dict(glh._cache, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_builds_once_and_rebuilds_after_ttl(self):
        calls = []
        builder = lambda: calls.append(1) or len(calls)  # noqa: E731
        self.assertEqual(glh._cached('k', builder), 1)
        self.assertEqual(glh._cached('k', builder), 1)
        glh._cache['k'] = (0, 1)  # expired
        self.assertEqual(glh._cached('k', builder), 2)

    def test_slow_build_does_not_block_other_keys(self):
        started, release = threading.Event(), threading.Event()

        def slow():
            started.set()
            release.wait(5)
            return 'slow'

        worker = threading.Thread(target=glh._cached, args=('slow', slow))
        worker.start()
        self.assertTrue(started.wait(5))
        # another table builds while 'slow' is still building
        self.assertEqual(glh._cached('fast', lambda: 'fast'), 'fast')
        release.set()
        worker.join(5)
        self.assertEqual(glh._cache['slow'][1], 'slow')

    def test_expired_value_served_while_rebuilding(self):
        glh._cache['k'] = (0, 'old')
        started, release = threading.Event(), threading.Event()

        def rebuild():
            started.set()
            release.wait(5)
            return 'new'

        worker = threading.Thread(target=glh._cached, args=('k', rebuild))
        worker.start()
        self.assertTrue(started.wait(5))
        self.assertEqual(glh._cached('k', lambda: 'unused'), 'old')
        release.set()
        worker.join(5)
        self.assertEqual(glh._cached('k', lambda: 'unused'), 'new')


if __name__ == '__main__':
    unittest.main()
