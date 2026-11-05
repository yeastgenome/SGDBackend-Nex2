import unittest
from unittest import mock

from src import gene_list_terms as glt


def _locus(locus_id, systematic_name, gene_name):
    return {'id': locus_id, 'sgdid': 'S%09d' % locus_id, 'systematic_name': systematic_name,
            'gene_name': gene_name, 'display_name': gene_name or systematic_name, 'qualifier': 'Verified',
            'description': '', 'link': '/locus/S%09d' % locus_id}


LOCI = {1: _locus(1, 'YFL039C', 'ACT1'), 2: _locus(2, 'YBR160W', 'CDC28'),
        3: _locus(3, 'YJL030W', 'MAD2'), 4: _locus(4, 'YAR000W', None)}


def _go(goid, name):
    return {'id': goid, 'display_name': name, 'namespace': 'biological process', 'link': '/go/' + goid}


# 10 trehalose metabolic process
#   11 trehalose biosynthetic process
#     12 trehalose biosynthetic process, unannotated child
#   13 trehalose catabolic process
# 20 unrelated process (no annotations)
GO_TERMS = {10: _go('GO:0005991', 'trehalose metabolic process'),
            11: _go('GO:0005992', 'trehalose biosynthetic process'),
            12: _go('GO:0000001', 'trehalose biosynthetic process, child'),
            13: _go('GO:0005993', 'trehalose catabolic process'),
            20: _go('GO:0000002', 'unrelated process')}
GO_BY_ID = {t['id']: i for i, t in GO_TERMS.items()}
GO_CHILDREN = {10: [11, 13], 11: [12]}
GO_ANNOTATIONS = {10: {'manually curated': {1}},
                  11: {'manually curated': {2}, 'computational': {3}},
                  13: {'high-throughput': {4}}}

# 100 observable (root) -> 101 cell morphology -> 102 cell shape; 100 -> 103 growth
APO_TERMS = {100: {'id': 'APO:0000017', 'display_name': 'observable', 'link': '/ontology/phenotype/ypo'},
             101: {'id': 'APO:0000063', 'display_name': 'cell morphology', 'link': '/observable/APO:0000063'},
             102: {'id': 'APO:0000064', 'display_name': 'cell shape', 'link': '/observable/APO:0000064'},
             103: {'id': 'APO:0000106', 'display_name': 'growth', 'link': '/observable/APO:0000106'}}
APO_CHILDREN = {100: [103, 101], 101: [102]}
APO_ANNOTATIONS = {101: {'abnormal': {1}, None: {2}},
                   102: {'decreased': {3}, 'normal': {4}},
                   103: {'normal rate': {1}}}

# 200 cancer -> 201 carcinoma; 202 unannotated disease
DISEASES = {200: {'id': 'DOID:162', 'display_name': 'cancer', 'link': '/disease/DOID:162'},
            201: {'id': 'DOID:305', 'display_name': 'carcinoma', 'link': '/disease/DOID:305'},
            202: {'id': 'DOID:4', 'display_name': 'disease', 'link': '/disease/DOID:4'}}
DISEASE_CHILDREN = {200: [201]}
DISEASE_ANNOTATIONS = {200: {1}, 201: {2, 3}}

# regulator sets keyed by regulator dbentity id, domains by InterPro id
REGULATORS = ({50: {'id': 50, 'display_name': 'GCN4', 'link': '/locus/GCN4'},
               51: {'id': 51, 'display_name': 'GCR1', 'link': '/locus/GCR1'}},
              {50: frozenset({1, 2}), 51: frozenset({4})}, frozenset({1, 2, 4}))
DOMAINS = ({'IPR000001': {'id': 'IPR000001', 'display_name': 'Kringle', 'link': 'https://www.ebi.ac.uk/'}},
           {'IPR000001': frozenset({3})}, frozenset({3}))


class TermGenesTest(unittest.TestCase):

    def setUp(self):
        patchers = [mock.patch.object(glt, 'get_lookup', return_value=(LOCI, {}, {})),
                    mock.patch.object(glt, 'get_go', return_value=(GO_TERMS, GO_BY_ID, GO_CHILDREN, GO_ANNOTATIONS)),
                    mock.patch.object(glt, 'get_observables', return_value=(APO_TERMS, APO_CHILDREN, APO_ANNOTATIONS)),
                    mock.patch.object(glt, 'get_diseases',
                                      return_value=(DISEASES, DISEASE_CHILDREN, DISEASE_ANNOTATIONS)),
                    mock.patch.object(glt, 'get_annotation_sets',
                                      side_effect=lambda c: {'regulator': REGULATORS, 'domain': DOMAINS}[c]),
                    mock.patch.object(glt, '_cached', side_effect=lambda key, builder: builder())]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def names(self, result):
        return [g['systematic_name'] for g in result['genes']]

    def test_go_with_descendants(self):
        result = glt.go_term_genes('GO:0005991')
        self.assertEqual(result['term']['display_name'], 'trehalose metabolic process')
        self.assertEqual(result['term_count'], 4)
        # gene names first (alphabetical), then unnamed genes
        self.assertEqual(self.names(result), ['YFL039C', 'YBR160W', 'YJL030W', 'YAR000W'])

    def test_go_without_descendants_and_by_name(self):
        result = glt.go_term_genes('Trehalose Metabolic Process', include_descendants=False)
        self.assertEqual(result['term_count'], 1)
        self.assertEqual(self.names(result), ['YFL039C'])

    def test_go_annotation_types(self):
        result = glt.go_term_genes('GO0005991', annotation_types=['manually curated'])
        self.assertEqual(self.names(result), ['YFL039C', 'YBR160W'])
        with self.assertRaises(ValueError):
            glt.go_term_genes('GO:0005991', annotation_types=['IEA'])

    def test_go_unknown_term(self):
        with self.assertRaises(LookupError):
            glt.go_term_genes('GO:9999999')

    def test_go_too_many_genes(self):
        with mock.patch.object(glt, 'MAX_INPUT_IDENTIFIERS', 2):
            with self.assertRaises(ValueError):
                glt.go_term_genes('GO:0005991')

    def test_search_go_terms(self):
        # terms with no annotations at or below them are left out
        self.assertEqual([t['id'] for t in glt.search_go_terms('trehalose b')], ['GO:0005992'])
        self.assertEqual([t['id'] for t in glt.search_go_terms('process')], ['GO:0005993', 'GO:0005991', 'GO:0005992'])
        # exact match first, then names starting with the query, shorter first, then the rest
        self.assertEqual([t['id'] for t in glt.search_go_terms('trehalose metabolic process')], ['GO:0005991'])
        self.assertEqual([t['id'] for t in glt.search_go_terms('trehalose')],
                         ['GO:0005993', 'GO:0005991', 'GO:0005992'])
        self.assertEqual([t['id'] for t in glt.search_go_terms('catabolic')], ['GO:0005993'])
        self.assertEqual(glt.search_go_terms('go:0005993')[0]['id'], 'GO:0005993')
        self.assertEqual(glt.search_go_terms('tr'), [])

    def test_phenotype_excludes_normal_by_default(self):
        result = glt.phenotype_genes('cell morphology')
        self.assertEqual(result['term_count'], 2)
        self.assertEqual(self.names(result), ['YFL039C', 'YBR160W', 'YJL030W'])

    def test_phenotype_options(self):
        self.assertEqual(self.names(glt.phenotype_genes('APO:0000063', include_normal=True)),
                         ['YFL039C', 'YBR160W', 'YJL030W', 'YAR000W'])
        self.assertEqual(self.names(glt.phenotype_genes('cell morphology', qualifier='decreased')), ['YJL030W'])
        self.assertEqual(self.names(glt.phenotype_genes('cell morphology', include_descendants=False)),
                         ['YFL039C', 'YBR160W'])
        self.assertEqual(self.names(glt.phenotype_genes('growth')), [])
        with self.assertRaises(LookupError):
            glt.phenotype_genes('no such phenotype')

    def test_phenotype_terms_tree(self):
        tree = glt.phenotype_terms()
        self.assertEqual([(t['display_name'], t['depth'], t['gene_count']) for t in tree['terms']],
                         [('cell morphology', 0, 3), ('cell shape', 1, 1), ('growth', 0, 0)])
        self.assertEqual(tree['qualifiers'], ['abnormal', 'decreased', 'normal', 'normal rate'])


    def test_disease_with_and_without_descendants(self):
        result = glt.category_term_genes('disease', 'DOID:162')
        self.assertEqual(result['term']['display_name'], 'cancer')
        self.assertEqual(result['term_count'], 2)
        self.assertEqual(self.names(result), ['YFL039C', 'YBR160W', 'YJL030W'])
        self.assertEqual(self.names(glt.category_term_genes('disease', 'Cancer', include_descendants=False)),
                         ['YFL039C'])
        self.assertEqual(self.names(glt.category_term_genes('disease', 'doid162', include_descendants=False)),
                         ['YFL039C'])

    def test_flat_categories(self):
        result = glt.category_term_genes('regulator', 'gcn4')
        self.assertFalse(result['include_descendants'])
        self.assertEqual(self.names(result), ['YFL039C', 'YBR160W'])
        # the frontend sends back the suggestion key (the term id)
        self.assertEqual(self.names(glt.category_term_genes('regulator', '51')), ['YAR000W'])
        self.assertEqual(self.names(glt.category_term_genes('domain', 'ipr000001')), ['YJL030W'])
        with self.assertRaises(LookupError):
            glt.category_term_genes('regulator', 'nope')
        with self.assertRaises(ValueError):
            glt.category_term_genes('go', 'GO:0005991')

    def test_search_category_terms(self):
        hits = glt.search_category_terms('disease', 'c')
        self.assertEqual(hits, [])
        hits = glt.search_category_terms('disease', 'ca')
        # unannotated terms are left out; counts include descendants
        self.assertEqual([(t['display_name'], t['gene_count']) for t in hits], [('cancer', 3), ('carcinoma', 2)])
        self.assertEqual(hits[0]['key'], '200')
        self.assertEqual(glt.search_category_terms('disease', 'doid:305')[0]['display_name'], 'carcinoma')
        self.assertEqual([t['accession'] for t in glt.search_category_terms('domain', 'IPR000001')], ['IPR000001'])
        self.assertEqual([t['accession'] for t in glt.search_category_terms('regulator', 'gc')], [None, None])


if __name__ == '__main__':
    unittest.main()
