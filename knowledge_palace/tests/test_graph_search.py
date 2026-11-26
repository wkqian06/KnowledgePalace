"""Global keyword search is independent of graph overview selection."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from knowledge_palace.graph.builder import write_index
from knowledge_palace.graph.network import build_network
from knowledge_palace.graph.search import search_nodes
from .test_viewer_export import make_vault


class TestGraphSearch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.vault = make_vault(self.root, works=6)
        self.state = self.root / 'state'
        write_index(self.vault, self.state)

    def test_global_search_finds_work_omitted_from_overview(self):
        overview = build_network(self.state, max_nodes=1)
        omitted = next('work:work-%s' % i for i in range(6)
                       if 'work:work-%s' % i not in {n['id'] for n in overview['nodes']})
        self.assertEqual(search_nodes(self.state, omitted.upper())['nodes'][0]['id'], omitted)

    def test_bounded_total_and_deterministic_order(self):
        result = search_nodes(self.state, 'WORK:WORK-', 2)
        self.assertEqual(result['total'], 6)
        self.assertEqual([n['id'] for n in result['nodes']], ['work:work-0', 'work:work-1'])
        self.assertEqual(result, search_nodes(self.state, 'WORK:WORK-', 2))
        self.assertEqual(search_nodes(self.state, 'not present')['total'], 0)

    def test_label_alias_casefold_and_all_kinds(self):
        doc = {'snapshot': {}, 'payload': {'nodes': {
            'z': {'kind': 'claim', 'label': 'Visible Label', 'attrs': {'aliases': ['Straße']}},
            'a': {'kind': 'work', 'label': 'other'},
        }}}
        with mock.patch('knowledge_palace.graph.search.load_index', return_value=doc):
            self.assertEqual(search_nodes(self.state, 'LABEL')['nodes'][0]['id'], 'z')
            self.assertEqual(search_nodes(self.state, 'STRASSE')['nodes'][0]['id'], 'z')

    def test_invalid_inputs_and_missing_index(self):
        for query, limit in [('', 1), ('  ', 1), ('x', 0), ('x', 101), ('x', True)]:
            with self.assertRaises(ValueError):
                search_nodes(self.state, query, limit)
        with self.assertRaises(FileNotFoundError):
            search_nodes(self.root / 'missing', 'x')


if __name__ == '__main__':
    unittest.main()
