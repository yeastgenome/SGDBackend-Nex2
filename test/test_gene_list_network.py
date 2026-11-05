import unittest
from unittest import mock

from src import gene_list_network as gln


def _locus(locus_id, name):
    return {'id': locus_id, 'sgdid': 'S%09d' % locus_id, 'systematic_name': 'Y%03d' % locus_id,
            'gene_name': name, 'display_name': name, 'qualifier': 'Verified', 'description': name + ' desc',
            'link': '/locus/S%09d' % locus_id}


LOCI = {i: _locus(i, n) for i, n in enumerate(['A', 'B', 'C', 'D', 'X', 'Y'], start=1)}


def _edge(kind, a, b, evidence):
    return {'type': kind, 'source': a, 'target': b, 'weight': evidence, 'evidence': evidence, 'references': 1,
            'detail': ['Two-hybrid'], 'high_throughput_only': False}


# list = A B C D (1-4); X (5) touches A, B and C; Y (6) touches only D
PHYSICAL = {(1, 2): _edge('physical', 1, 2, 3), (2, 3): _edge('physical', 2, 3, 1),
            (1, 5): _edge('physical', 1, 5, 2), (2, 5): _edge('physical', 2, 5, 1),
            (3, 5): _edge('physical', 3, 5, 1), (4, 6): _edge('physical', 4, 6, 5)}
REGULATION = {(4, 1): dict(_edge('regulation', 4, 1, 2), direction='positive')}


def _interactions(kind, ids, both_in_list):
    edges = PHYSICAL if kind == 'physical' else {}
    members = set(ids)
    return {k: e for k, e in edges.items()
            if (e['source'] in members and e['target'] in members) or
            (not both_in_list and (e['source'] in members or e['target'] in members))}


GO_TERMS = {10: {'id': 'GO:1', 'display_name': 'specific process'},
            11: {'id': 'GO:2', 'display_name': 'another process'},
            12: {'id': 'GO:3', 'display_name': 'broad process'}}
GO_ANNOTATIONS = {10: {'manually curated': {1, 2}},
                  11: {'high-throughput': {1, 2, 3}, 'computational': {4}},
                  12: {'manually curated': set(range(1, 200))}}


class NetworkTest(unittest.TestCase):

    def setUp(self):
        patchers = [mock.patch.object(gln, 'get_lookup', return_value=(LOCI, {}, {})),
                    mock.patch.object(gln, '_interaction_edges', side_effect=_interactions),
                    mock.patch.object(gln, '_regulation_edges', side_effect=lambda ids, both: dict(REGULATION)),
                    mock.patch.object(gln, 'get_go', return_value=(GO_TERMS, {}, {}, GO_ANNOTATIONS)),
                    mock.patch.dict(gln._coexpression, clear=True)]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def pairs(self, network, kind=None):
        names = {n['id']: n['name'] for n in network['nodes']}
        return sorted((names[e['source']], names[e['target']]) for e in network['edges']
                      if kind is None or e['type'] == kind)

    def test_defaults_physical_and_regulation_within_list(self):
        net = gln.get_list_network({'bioent_ids': [1, 2, 3, 4]})
        self.assertEqual(net['edge_types'], ['physical', 'regulation'])
        self.assertEqual(net['min_evidence'], 1)  # small list
        self.assertEqual(self.pairs(net, 'physical'), [('A', 'B'), ('B', 'C')])
        self.assertEqual(self.pairs(net, 'regulation'), [('D', 'A')])  # regulator -> target
        self.assertEqual([n['name'] for n in net['nodes']], ['A', 'B', 'C', 'D'])
        self.assertEqual({n['name']: n['degree'] for n in net['nodes']}, {'A': 2, 'B': 2, 'C': 1, 'D': 1})

    def test_min_evidence(self):
        net = gln.get_list_network({'bioent_ids': [1, 2, 3, 4], 'min_evidence': 2})
        self.assertEqual(self.pairs(net), [('A', 'B'), ('D', 'A')])
        self.assertEqual(gln.default_min_evidence(99), 1)
        self.assertEqual(gln.default_min_evidence(100), 2)

    def test_neighbors_need_two_list_genes(self):
        net = gln.get_list_network({'bioent_ids': [1, 2, 3, 4], 'edge_types': ['physical'], 'neighbors': 10})
        self.assertEqual(net['neighbors_added'], 1)
        self.assertEqual([(n['name'], n['in_list']) for n in net['nodes']][-1], ('X', False))
        self.assertIn(('C', 'X'), self.pairs(net))
        self.assertNotIn('Y', [n['name'] for n in net['nodes']])

    def test_shared_go_skips_broad_terms(self):
        net = gln.get_list_network({'bioent_ids': [1, 2, 3, 4], 'edge_types': ['shared_go']})
        # A-B share GO:1 and GO:2; B-C and A-C only GO:2; D only has a computational annotation
        self.assertEqual(self.pairs(net), [('A', 'B')])
        # most specific (fewest genes) first
        self.assertEqual(net['edges'][0]['detail'], ['specific process', 'another process'])
        net = gln.get_list_network({'bioent_ids': [1, 2, 3, 4], 'edge_types': ['shared_go'], 'go_min_shared': 1})
        self.assertEqual(self.pairs(net), [('A', 'B'), ('A', 'C'), ('B', 'C')])

    def test_coexpression(self):
        files = {'S000000001': [('S000000002', 0.8, 1), ('S000000005', 0.7, 2)],
                 'S000000002': [('S000000001', 0.8, 3)], 'S000000003': [], 'S000000004': None}
        with mock.patch.object(gln, '_fetch_coexpression', side_effect=lambda s: (s, files[s])) as fetch:
            net = gln.get_list_network({'bioent_ids': [1, 2, 3, 4], 'edge_types': ['coexpression']})
            self.assertEqual(self.pairs(net), [('A', 'B')])
            self.assertEqual(net['edges'][0]['rank'], 1)
            gln.get_list_network({'bioent_ids': [1, 2, 3, 4], 'edge_types': ['coexpression']})
        # cached except the failed fetch, which is retried
        self.assertEqual(sorted(c.args[0] for c in fetch.call_args_list),
                         ['S000000001', 'S000000002', 'S000000003', 'S000000004', 'S000000004'])

    def test_limit_edges(self):
        edges = [_edge('physical', i, i + 1, ev) for i, ev in enumerate([1, 1, 2, 2, 3, 5])]
        kept, used, notes = gln._limit_edges(edges, 3, 1)
        self.assertEqual((len(kept), used), (2, 3))
        self.assertEqual(len(notes), 1)
        go = [{'type': 'shared_go', 'source': i, 'target': i + 1, 'weight': i} for i in range(10)]
        kept, used, notes = gln._limit_edges(go, 4, 1)
        self.assertEqual(sorted(e['weight'] for e in kept), [6, 7, 8, 9])
        self.assertEqual(notes, ['only the strongest edges of each type are shown'])

    def test_gene_names(self):
        with mock.patch.object(gln, 'resolve_identifiers', return_value={'resolved_ids': [1, 2]}) as resolve:
            net = gln.get_list_network({'genes': 'A B'})
        resolve.assert_called_once_with('A B')
        self.assertEqual(self.pairs(net), [('A', 'B')])

    def test_validation(self):
        with self.assertRaises(ValueError):
            gln.get_list_network({'bioent_ids': []})
        with self.assertRaises(ValueError):
            gln.get_list_network({'bioent_ids': [1], 'edge_types': ['nope']})
        with self.assertRaises(ValueError):
            gln.get_list_network({'bioent_ids': [999]})
        with self.assertRaises(ValueError):
            gln.get_list_network({'bioent_ids': [1], 'neighbors': 1000})


if __name__ == '__main__':
    unittest.main()
