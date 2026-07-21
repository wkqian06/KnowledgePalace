"""The static HTML shell: hand-rolled CSS/JS, zero outbound network calls.

No CDN links, no charting library, no ``<script src=`` — everything the
page needs is inlined. Introducing any vendored JS/CSS dependency is
a named dependency-gate trigger; the default stays
hand-rolled to avoid it.
"""

_STYLE = """
body { font-family: -apple-system, system-ui, sans-serif; margin: 0; display: flex; height: 100vh; color: #1a1a1a; background: #fff; }
#tree { width: 34%; overflow-y: auto; border-right: 1px solid #ddd; padding: 8px; box-sizing: border-box; }
#detail { flex: 1; overflow-y: auto; padding: 16px; box-sizing: border-box; }
.level-label { font-weight: 600; margin: 10px 0 4px; color: #555; }
.node-row { cursor: pointer; padding: 2px 4px; border-radius: 3px; white-space: nowrap; }
.node-row:hover { background: #eef; }
.node-row.selected { background: #dde; }
.kind-tag { display: inline-block; font-size: 0.7em; color: #fff; background: #789; border-radius: 3px; padding: 0 4px; margin-right: 4px; }
.section-title { font-weight: 600; margin-top: 14px; color: #444; }
.content-block { white-space: pre-wrap; background: #f7f7f7; padding: 8px; border-radius: 4px; font-size: 0.9em; }
.truncated-note { color: #a60; font-size: 0.85em; }
a.edge-link { cursor: pointer; color: #06c; text-decoration: none; }
a.edge-link:hover { text-decoration: underline; }
@media (prefers-color-scheme: dark) {
  body { background: #1a1a1a; color: #e6e6e6; }
  #tree { border-color: #333; }
  .node-row:hover, .node-row.selected { background: #333; }
  .content-block { background: #262626; }
}
"""

_SCRIPT = """
const DATA = JSON.parse(document.getElementById('palace-data').textContent);

function el(tag, props, children) {
  const node = document.createElement(tag);
  Object.assign(node, props || {});
  (children || []).forEach(c => node.appendChild(c));
  return node;
}

function renderTree() {
  const root = document.getElementById('tree');
  root.innerHTML = '';
  DATA.hierarchies.forEach(h => {
    root.appendChild(el('div', {className: 'level-label', textContent: h.label}));
    h.levels.forEach(level => {
      root.appendChild(el('div', {className: 'level-label', textContent: '  ' + level.label}));
      level.node_ids.forEach(id => {
        const node = DATA.nodes[id];
        const row = el('div', {className: 'node-row', dataset: {id: id}});
        row.appendChild(el('span', {className: 'kind-tag', textContent: node.kind}));
        row.appendChild(document.createTextNode(node.label));
        row.onclick = () => selectNode(id);
        root.appendChild(row);
      });
    });
  });
}

function nodeLink(id) {
  const node = DATA.nodes[id];
  const a = el('a', {className: 'edge-link', textContent: node ? node.label : id});
  a.onclick = () => selectNode(id);
  return a;
}

function selectNode(id) {
  document.querySelectorAll('.node-row.selected').forEach(n => n.classList.remove('selected'));
  const row = document.querySelector('.node-row[data-id="' + CSS.escape(id) + '"]');
  if (row) row.classList.add('selected');

  const detail = document.getElementById('detail');
  detail.innerHTML = '';
  const node = DATA.nodes[id];
  const ctx = DATA.contexts[id];
  const content = DATA.contents[id];

  detail.appendChild(el('h2', {textContent: node.label}));
  detail.appendChild(el('div', {textContent: 'kind: ' + node.kind}));

  if (ctx.parents.length) {
    detail.appendChild(el('div', {className: 'section-title', textContent: 'Parents'}));
    const p = el('div', {}, ctx.parents.map(pn => nodeLink(pn.id)));
    detail.appendChild(p);
  }

  const childItems = ctx.children.items;
  detail.appendChild(el('div', {className: 'section-title',
    textContent: 'Children (' + ctx.children.returned + ' of ' + ctx.children.total + ')'}));
  if (ctx.children.truncated) {
    detail.appendChild(el('div', {className: 'truncated-note',
      textContent: 'showing the first page only — the port does not paginate this field further'}));
  }
  childItems.forEach(c => {
    const row = el('div', {}, [nodeLink(c.id)]);
    detail.appendChild(row);
  });

  detail.appendChild(el('div', {className: 'section-title',
    textContent: 'Edges (' + ctx.edges.returned + ' of ' + ctx.edges.total + ')'}));
  if (ctx.edges.truncated) {
    detail.appendChild(el('div', {className: 'truncated-note',
      textContent: 'showing the first page only — the port does not paginate this field further'}));
  }
  ctx.edges.items.forEach(e => {
    const other = e.from === id ? e.to : e.from;
    const row = el('div', {}, [
      document.createTextNode(e.kind + ' → '),
      nodeLink(other),
    ]);
    detail.appendChild(row);
  });

  if (content) {
    detail.appendChild(el('div', {className: 'section-title', textContent: 'Content'}));
    detail.appendChild(el('div', {className: 'content-block', textContent: content.content}));
    if (content.truncated) {
      detail.appendChild(el('div', {className: 'truncated-note', textContent: 'content truncated'}));
    }
  }
}

renderTree();
"""


def render(payload_json_bytes):
    """payload_json_bytes: canonical UTF-8 JSON bytes → complete HTML bytes."""
    # Standard safe-embedding escape: HTML's script-data tokenizer reacts to
    # ANY bare "<" (not just a literal "</script" — "<!--" followed by an
    # unclosed "<script" also perturbs the parser's escape state). Escaping
    # every "<" to its JSON unicode-escape form removes every such trigger;
    # JSON.parse decodes it back to "<" losslessly.
    safe_json = payload_json_bytes.decode("utf-8").replace("<", "\\u003c")
    html = (
        "<!doctype html>\n"
        "<html><head><meta charset=\"utf-8\">"
        "<title>Palace Viewer</title>"
        "<style>" + _STYLE + "</style>"
        "</head><body>"
        "<div id=\"tree\"></div><div id=\"detail\"></div>"
        "<script type=\"application/json\" id=\"palace-data\">" + safe_json + "</script>"
        "<script>" + _SCRIPT + "</script>"
        "</body></html>\n"
    )
    return html.encode("utf-8")
