"""Read-only complete visualization lookup, independent of the canonical index."""
import argparse
import json
import sys
from collections import defaultdict

from .builder import load_index
from .network import MAP_KINDS, _work_bundle, _work_metrics
from ..tools.config_resolver import resolve_roots
from ..viewer.export import citation_overlay


def build_visualization(state, vault):
    document = load_index(state)
    if document is None:
        raise FileNotFoundError('Graph Index is missing')
    payload = document['payload']
    selected = {node_id for node_id, node in payload['nodes'].items() if node.get('kind') in MAP_KINDS}
    bundle = _work_bundle(vault, payload, selected)
    nodes = {}
    for node_id in sorted(selected):
        node = payload['nodes'][node_id]
        attrs = node.get('attrs') or {}
        year = str(attrs.get('year') or '')
        nodes[node_id] = {'id': node_id, 'kind': node['kind'], 'label': node.get('label') or node_id,
                          'year': int(year) if year.isdigit() else None,
                          'citations': _work_metrics(bundle, node_id) if node['kind'] == 'work' else None}
    edges = {}
    def add(kind, source, target, edge_id=None):
        if source in nodes and target in nodes and source != target:
            key = edge_id or f'{kind}|{source}|{target}'
            edges[key] = {'id': key, 'kind': kind, 'from': source, 'to': target}
    for child, parents in payload['parents'].items():
        for parent in parents:
            add('parent', parent, child)
    for edge in payload['edges']:
        add(edge['kind'], edge['from'], edge['to'], edge['id'])
    for source, target in citation_overlay(bundle, state)['edges']:
        add('cites', source, target)
    neighbors = defaultdict(set)
    for edge in edges.values():
        neighbors[edge['from']].add(edge['to'])
        neighbors[edge['to']].add(edge['from'])
    for node_id, node in nodes.items():
        node['degree'] = len(neighbors[node_id])
    return {'snapshot': document['snapshot'], 'nodes': nodes, 'edges': list(edges.values()),
            'citation_scope': 'local OpenAlex cache; matched works only'}


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    args = parser.parse_args(argv)
    roots = resolve_roots(args.config)
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(build_visualization(roots['state_dir'], roots['vault_dir']), ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    run()
