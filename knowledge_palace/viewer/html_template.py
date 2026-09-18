"""The static HTML shell: hand-rolled CSS/JS, zero outbound network calls.

No CDN links, no charting library, no ``<script src=`` — everything the
page needs is inlined. Introducing any vendored JS/CSS dependency is
a named dependency-gate trigger; the default stays
hand-rolled to avoid it.

Two views over the same embedded payload, toggled in the top bar:

- **Network** (default) — a Connected-Papers-style force-directed map on a
  canvas: hand-rolled simulation, color by kind, work nodes sized by
  citation count and shaded by year (newer = darker; both parsed from the
  card frontmatter already embedded in the payload), work-to-work citation
  edges from the export-time Bibliographic Cache overlay, labels only on
  the selected/hovered/search-matched node,
  hover highlights the neighborhood, click selects into the detail pane,
  wheel zoom / drag pan / node drag, per-kind filter chips. Map links are
  the typed edges PLUS the hierarchy ``parents`` relation (stored outside
  ``edges`` by the index) and derived work-work "similar" links (>= 2
  shared non-domain concept tags — clustering only, no degree credit,
  toggleable via the similarity chip). Claim nodes
  (quote leaves, the bulk of the vault) are excluded from the map to keep
  it readable — they remain reachable in the detail pane. Map links come
  from the port's single-page edge envelopes, so a truncated hub context
  can undercount degree — inherited from the frozen contract, mitigated
  by deduping across both endpoints' contexts.
- **Layers** — one column per hierarchy level (Domains | Concepts | Works
  and gaps) with click-to-focus neighborhood dimming and SVG wires.
"""

_STYLE = """
* { box-sizing: border-box; }
body { font-family: -apple-system, system-ui, sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; color: #1a1a1a; background: #fff; }
#topbar { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-bottom: 1px solid #ddd; flex: none; flex-wrap: wrap; }
#topbar h1 { font-size: 1em; margin: 0 8px 0 0; }
#search { flex: 0 1 220px; padding: 4px 8px; border: 1px solid #bbb; border-radius: 4px; background: inherit; color: inherit; }
button { padding: 4px 10px; border: 1px solid #bbb; border-radius: 4px; background: inherit; color: inherit; cursor: pointer; }
button.active { background: #46a; color: #fff; border-color: #46a; }
#clear-focus { display: none; }
#hint { font-size: 0.8em; color: #888; }
.chip { font-size: 0.78em; padding: 2px 8px; border-radius: 10px; border: 1px solid #bbb; cursor: pointer; user-select: none; color: #fff; opacity: 0.9; }
.chip.off { opacity: 0.25; }
#main { display: flex; flex: 1; min-height: 0; }
#board { position: relative; display: none; flex: 1; min-width: 0; }
#board.visible { display: flex; }
#network { position: relative; display: none; flex: 1; min-width: 0; }
#network.visible { display: block; }
#net-canvas { position: absolute; inset: 0; width: 100%; height: 100%; cursor: grab; }
#wires { position: absolute; inset: 0; pointer-events: none; z-index: 1; }
.column { flex: 1; min-width: 0; display: flex; flex-direction: column; border-right: 1px solid #ddd; }
.column-head { flex: none; padding: 6px 10px; font-weight: 600; color: #555; border-bottom: 1px solid #eee; font-size: 0.85em; }
.column-list { flex: 1; overflow-y: auto; padding: 4px; }
.node-row { cursor: pointer; padding: 2px 6px; border-radius: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 0.9em; }
.node-row:hover { background: #eef; }
.node-row.selected { background: #cd6; outline: 1px solid #9a3; }
.node-row.related { background: #e8f0e8; }
.node-row.dimmed { opacity: 0.25; }
.node-row.hidden-row { display: none; }
.kind-tag { display: inline-block; font-size: 0.7em; color: #fff; border-radius: 3px; padding: 0 4px; margin-right: 4px; background: #789; }
.kind-domain { background: #46a; } .kind-concept { background: #297; }
.kind-work { background: #778; } .kind-gap { background: #c72; }
.kind-transfer { background: #85a; } .kind-claim { background: #999; }
#detail { flex: 0 0 30%; overflow-y: auto; padding: 14px; border-left: 1px solid #ddd; }
#detail h2 { margin-top: 0; font-size: 1.05em; }
.section-title { font-weight: 600; margin-top: 14px; color: #444; }
.content-block { white-space: pre-wrap; background: #f7f7f7; padding: 8px; border-radius: 4px; font-size: 0.85em; }
.truncated-note { color: #a60; font-size: 0.85em; }
a.edge-link { cursor: pointer; color: #06c; text-decoration: none; }
a.edge-link:hover { text-decoration: underline; }
.wire { fill: none; stroke: #7a5; stroke-width: 1.4; opacity: 0.75; }
.wire.typed { stroke: #a7c; stroke-dasharray: 4 3; }
@media (prefers-color-scheme: dark) {
  body { background: #1a1a1a; color: #e6e6e6; }
  #topbar, .column, .column-head, #detail { border-color: #333; }
  .section-title { color: #aaa; }
  .column-head { color: #999; }
  #search, button { border-color: #444; }
  button.active { background: #46a; border-color: #46a; }
  .node-row:hover { background: #333; }
  .node-row.selected { background: #563; outline-color: #684; }
  .node-row.related { background: #263026; }
  .content-block { background: #262626; }
  a.edge-link { color: #6af; }
}
"""

_SCRIPT = """
const DATA = JSON.parse(document.getElementById('palace-data').textContent);
let focusedId = null;
let focusedSet = null;
const rowsById = new Map();

const KIND_COLORS = {
  domain: '#4466aa', concept: '#229977', work: '#777788',
  gap: '#cc7722', transfer: '#8855aa',
};

function el(tag, props, children) {
  const node = document.createElement(tag);
  Object.assign(node, props || {});
  (children || []).forEach(c => node.appendChild(c));
  return node;
}

function ctxOf(id) { return DATA.contexts[id] || null; }

function rowFor(id) {
  return rowsById.get(id) || null;
}

/* ---------------- layered board view ---------------- */

function renderBoard() {
  const board = document.getElementById('board');
  const hierarchy = DATA.hierarchies[0];
  if (!hierarchy) return;
  hierarchy.levels.forEach(level => {
    const list = el('div', {className: 'column-list'});
    level.node_ids.forEach(id => {
      const node = DATA.nodes[id];
      if (!node) return;
      const row = el('div', {className: 'node-row', title: node.label});
      row.setAttribute('data-id', id);
      rowsById.set(id, row);
      row.appendChild(el('span', {className: 'kind-tag kind-' + node.kind, textContent: node.kind}));
      row.appendChild(document.createTextNode(node.label));
      row.onclick = () => focusNode(id);
      list.appendChild(row);
    });
    const column = el('div', {className: 'column'}, [
      el('div', {className: 'column-head',
        textContent: level.label + ' (' + level.node_ids.length + ')'}),
      list,
    ]);
    board.appendChild(column);
    list.addEventListener('scroll', scheduleWires);
  });
}

function ancestorsOf(id, seen) {
  const ctx = ctxOf(id);
  (ctx ? ctx.parents : []).forEach(p => {
    if (!seen.has(p.id)) { seen.add(p.id); ancestorsOf(p.id, seen); }
  });
}

function descendantsOf(id, seen, depth) {
  if (depth <= 0) return;
  const ctx = ctxOf(id);
  (ctx ? ctx.children.items : []).forEach(c => {
    if (!seen.has(c.id)) { seen.add(c.id); descendantsOf(c.id, seen, depth - 1); }
  });
}

function relatedSet(id) {
  const seen = new Set([id]);
  ancestorsOf(id, seen);
  descendantsOf(id, seen, 3);
  const ctx = ctxOf(id);
  (ctx ? ctx.edges.items : []).forEach(e => { seen.add(e.from); seen.add(e.to); });
  return seen;
}

function focusNode(id) {
  focusedId = id;
  focusedSet = relatedSet(id);
  document.getElementById('clear-focus').style.display = 'inline-block';
  const related = focusedSet;
  document.querySelectorAll('.node-row').forEach(row => {
    const rid = row.getAttribute('data-id');
    row.classList.toggle('selected', rid === id);
    row.classList.toggle('related', rid !== id && related.has(rid));
    row.classList.toggle('dimmed', !related.has(rid));
  });
  if (boardVisible()) {
    document.querySelectorAll('.column-list').forEach(list => {
      const hit = list.querySelector('.node-row.selected, .node-row.related');
      if (hit) hit.scrollIntoView({block: 'center'});
    });
  }
  renderDetail(id);
  scheduleWires();
  NET.selected = id;
  netDraw();
}

function clearFocus() {
  focusedId = null;
  focusedSet = null;
  document.getElementById('clear-focus').style.display = 'none';
  document.querySelectorAll('.node-row').forEach(row => {
    row.classList.remove('selected', 'related', 'dimmed');
  });
  document.getElementById('wires').replaceChildren();
  document.getElementById('detail').replaceChildren(
    el('p', {textContent: 'Click a node to focus its neighborhood.'}));
  NET.selected = null;
  netDraw();
}

function applySearch() {
  const query = document.getElementById('search').value.trim().toLowerCase();
  document.querySelectorAll('.node-row').forEach(row => {
    const node = DATA.nodes[row.getAttribute('data-id')];
    const miss = query && node.label.toLowerCase().indexOf(query) === -1 &&
      node.id.toLowerCase().indexOf(query) === -1;
    row.classList.toggle('hidden-row', !!miss);
  });
  scheduleWires();
  NET.query = query;
  netDraw();
}

let wireQueued = false;
function scheduleWires() {
  if (wireQueued) return;
  wireQueued = true;
  requestAnimationFrame(() => { wireQueued = false; drawWires(); });
}

function visibleAnchor(id, boardRect) {
  const row = rowFor(id);
  if (!row || row.classList.contains('hidden-row')) return null;
  const rect = row.getBoundingClientRect();
  const list = row.parentElement.getBoundingClientRect();
  if (rect.bottom < list.top || rect.top > list.bottom) return null;
  return {
    left: {x: rect.left - boardRect.left, y: rect.top + rect.height / 2 - boardRect.top},
    right: {x: rect.right - boardRect.left, y: rect.top + rect.height / 2 - boardRect.top},
  };
}

function wirePath(a, b, typed) {
  const from = a.right.x <= b.left.x ? a.right : a.left;
  const to = a.right.x <= b.left.x ? b.left : b.right;
  const bend = (to.x - from.x) / 2;
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', 'M' + from.x + ',' + from.y +
    ' C' + (from.x + bend) + ',' + from.y + ' ' + (to.x - bend) + ',' + to.y +
    ' ' + to.x + ',' + to.y);
  path.setAttribute('class', typed ? 'wire typed' : 'wire');
  return path;
}

function boardVisible() {
  return document.getElementById('board').classList.contains('visible');
}

function drawWires() {
  const svg = document.getElementById('wires');
  svg.replaceChildren();
  if (!focusedId || !boardVisible()) return;
  const board = document.getElementById('board');
  const boardRect = board.getBoundingClientRect();
  svg.setAttribute('width', boardRect.width);
  svg.setAttribute('height', boardRect.height);
  const related = focusedSet;
  const drawn = new Set();
  related.forEach(id => {
    const anchor = visibleAnchor(id, boardRect);
    if (!anchor) return;
    const ctx = ctxOf(id);
    (ctx ? ctx.parents : []).forEach(p => {
      if (!related.has(p.id) || drawn.has(p.id + '>' + id)) return;
      const parentAnchor = visibleAnchor(p.id, boardRect);
      if (parentAnchor) {
        drawn.add(p.id + '>' + id);
        svg.appendChild(wirePath(parentAnchor, anchor, false));
      }
    });
  });
  const ctx = ctxOf(focusedId);
  const selfAnchor = visibleAnchor(focusedId, boardRect);
  if (ctx && selfAnchor) {
    ctx.edges.items.forEach(e => {
      const other = e.from === focusedId ? e.to : e.from;
      const otherAnchor = visibleAnchor(other, boardRect);
      if (otherAnchor && !drawn.has(focusedId + '>' + other) && !drawn.has(other + '>' + focusedId)) {
        drawn.add(focusedId + '>' + other);
        svg.appendChild(wirePath(selfAnchor, otherAnchor, true));
      }
    });
  }
}

/* ---------------- network view (Connected-Papers style) ---------------- */

const NET = {
  nodes: [], links: [], byId: new Map(), adj: new Map(), simAdj: new Map(),
  view: {x: 0, y: 0, k: 1}, kindOn: {}, selected: null, hovered: null,
  query: '', ticksLeft: 0, running: false, similarOn: true, userMoved: false,
};
// ponytail: O(n^2) repulsion each tick — fine to ~1500 nodes; grid-bucket
// approximation is the upgrade path if the vault outgrows that.
const SIM = {repulsion: 1200, spring: 0.03, restLen: 60, center: 0.0004, damping: 0.85, maxSpeed: 30};

function hashAngle(id) {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return [h % 6283 / 1000, 120 + h % 400];
}

function workMeta(id) {
  const record = DATA.contents[id];
  if (!record || !record.content) return {year: null, cited: null};
  const front = '\\n' + record.content.split('\\n---', 1)[0];  // frontmatter only
  const year = /\\nyear:\\s*(\\d{4})/.exec(front);
  const cited = /\\ncitations:\\s*(\\d+)/.exec(front);
  return {year: year ? +year[1] : null, cited: cited ? +cited[1] : null};
}

function buildNetwork() {
  Object.keys(KIND_COLORS).forEach(k => { NET.kindOn[k] = true; });
  Object.values(DATA.nodes).forEach(node => {
    if (!(node.kind in KIND_COLORS)) return;  // claims and briefs stay out
    const [angle, radius] = hashAngle(node.id);
    const meta = node.kind === 'work' ? workMeta(node.id) : {year: null, cited: null};
    const item = {
      id: node.id, kind: node.kind, label: node.label, degree: 0,
      year: meta.year, cited: meta.cited,
      x: Math.cos(angle) * radius, y: Math.sin(angle) * radius, vx: 0, vy: 0,
    };
    NET.nodes.push(item);
    NET.byId.set(node.id, item);
    NET.adj.set(node.id, new Set());
  });
  const years = NET.nodes.filter(n => n.year !== null).map(n => n.year);
  NET.yearMin = years.length ? Math.min.apply(null, years) : 0;
  NET.yearMax = years.length ? Math.max.apply(null, years) : 0;
  const seen = new Set();
  function addLink(fromId, toId, kind, key) {
    if (seen.has(key)) return;
    seen.add(key);
    const a = NET.byId.get(fromId), b = NET.byId.get(toId);
    if (!a || !b || a === b) return;  // an endpoint outside the map (e.g. a claim)
    NET.links.push({a: a, b: b, kind: kind});
    a.degree++; b.degree++;
    NET.adj.get(a.id).add(b.id);
    NET.adj.get(b.id).add(a.id);
  }
  const contexts = Object.values(DATA.contexts);
  contexts.forEach(ctx => {
    ctx.edges.items.forEach(e => addLink(e.from, e.to, e.kind, e.id));
  });
  // work-to-work citation edges from the export-time Bibliographic Cache
  // overlay (references and, symmetrically, cited-by)
  ((DATA.citations || {}).edges || []).forEach(pair => {
    const key = [pair[0], pair[1]].sort().join('|cites|');
    addLink(pair[0], pair[1], 'cites', key);
  });
  // hierarchy parent links live in `parents`, not `edges` — without them
  // concept-to-concept (and node-to-placement) structure is invisible.
  // Second pass so the edge-backed skip sees the full adjacency.
  contexts.forEach(ctx => {
    ctx.parents.forEach(p => {
      const adjacent = NET.adj.get(ctx.node.id);
      if (adjacent && adjacent.has(p.id)) return;  // placement already edge-backed
      const key = [ctx.node.id, p.id].sort().join('|parent|');
      addLink(ctx.node.id, p.id, 'parent', key);
    });
  });

  // Connected-Papers-style similarity: works sharing >= 2 distinct
  // non-domain concept tags get a derived link — clustering only, no
  // degree credit, separate adjacency so the chip toggle is honest.
  const tagged = new Map();  // concept id -> Set(work items)
  NET.links.forEach(link => {
    if (link.kind.indexOf('tag:') !== 0 || link.kind === 'tag:domain') return;
    const work = link.a.kind === 'work' ? link.a : (link.b.kind === 'work' ? link.b : null);
    const concept = link.a.kind === 'work' ? link.b : link.a;
    if (!work || concept.kind === 'domain') return;
    if (!tagged.has(concept.id)) tagged.set(concept.id, new Set());
    tagged.get(concept.id).add(work);
  });
  const shared = new Map();  // "idA|idB" -> {a, b, n: distinct shared concepts}
  tagged.forEach(workSet => {
    const works = Array.from(workSet);
    for (let i = 0; i < works.length; i++) {
      for (let j = i + 1; j < works.length; j++) {
        const key = [works[i].id, works[j].id].sort().join('|');
        const entry = shared.get(key) || {a: works[i], b: works[j], n: 0};
        entry.n++;
        shared.set(key, entry);
      }
    }
  });
  function simAdjAdd(fromId, toId) {
    if (!NET.simAdj.has(fromId)) NET.simAdj.set(fromId, new Set());
    NET.simAdj.get(fromId).add(toId);
  }
  // ponytail: every qualifying pair gets a link — a dense topical vault can
  // approach a work clique; top-k similar links per work is the upgrade path.
  shared.forEach(entry => {
    if (entry.n < 2) return;
    NET.links.push({a: entry.a, b: entry.b, kind: 'similar'});
    simAdjAdd(entry.a.id, entry.b.id);
    simAdjAdd(entry.b.id, entry.a.id);
  });
}

function netRadius(node) {
  if (node.kind === 'work') {
    return 3.5 + Math.log10(1 + (node.cited || 0)) * 2.5;  // size = citation count
  }
  return 3 + Math.sqrt(node.degree) * 1.4;
}

function nodeAlpha(node) {
  if (node.kind !== 'work') return 0.9;
  if (node.year === null || NET.yearMax <= NET.yearMin) return 0.55;
  // newer work = darker
  return 0.3 + 0.7 * (node.year - NET.yearMin) / (NET.yearMax - NET.yearMin);
}

function simTick() {
  const nodes = NET.nodes;
  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    for (let j = i + 1; j < nodes.length; j++) {
      const b = nodes[j];
      let dx = a.x - b.x, dy = a.y - b.y;
      let d2 = dx * dx + dy * dy;
      if (d2 < 1) { d2 = 1; dx = (i % 2 ? 1 : -1); dy = (j % 2 ? 1 : -1); }
      const force = SIM.repulsion / d2;
      const d = Math.sqrt(d2);
      dx /= d; dy /= d;
      a.vx += dx * force; a.vy += dy * force;
      b.vx -= dx * force; b.vy -= dy * force;
    }
  }
  NET.links.forEach(link => {
    const dx = link.b.x - link.a.x, dy = link.b.y - link.a.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 1;
    const pull = SIM.spring * (d - SIM.restLen) / d;
    link.a.vx += dx * pull; link.a.vy += dy * pull;
    link.b.vx -= dx * pull; link.b.vy -= dy * pull;
  });
  nodes.forEach(node => {
    node.vx -= node.x * SIM.center;
    node.vy -= node.y * SIM.center;
    node.vx *= SIM.damping; node.vy *= SIM.damping;
    const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
    if (speed > SIM.maxSpeed) {
      node.vx *= SIM.maxSpeed / speed;
      node.vy *= SIM.maxSpeed / speed;
    }
    if (node !== dragNode) { node.x += node.vx; node.y += node.vy; }
  });
}

function fitView() {
  const holder = document.getElementById('network');
  const width = holder.clientWidth, height = holder.clientHeight;
  if (!width || !height) return;
  let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9, any = false;
  NET.nodes.forEach(node => {
    if (!netVisible(node)) return;
    any = true;
    if (node.x < minX) minX = node.x;
    if (node.x > maxX) maxX = node.x;
    if (node.y < minY) minY = node.y;
    if (node.y > maxY) maxY = node.y;
  });
  if (!any) return;
  const spanX = Math.max(maxX - minX, 50), spanY = Math.max(maxY - minY, 50);
  const k = Math.min(8, Math.max(0.05, Math.min(width / (spanX * 1.15), height / (spanY * 1.15))));
  NET.view.k = k;
  NET.view.x = -k * (minX + maxX) / 2;
  NET.view.y = -k * (minY + maxY) / 2;
}

function startSim(ticks) {
  NET.ticksLeft = ticks;
  if (NET.running) return;
  NET.running = true;
  (function loop() {
    if (NET.ticksLeft <= 0) {
      NET.running = false;
      if (!NET.userMoved) fitView();
      netDraw();
      return;
    }
    const batch = Math.min(4, NET.ticksLeft);
    for (let i = 0; i < batch; i++) simTick();
    NET.ticksLeft -= batch;
    // camera follows the settling layout until the user takes over
    if (!NET.userMoved) fitView();
    netDraw();
    requestAnimationFrame(loop);
  })();
}

function netVisible(node) {
  if (!NET.kindOn[node.kind]) return false;
  return true;
}

function netMatches(node) {
  if (!NET.query) return false;
  return node.label.toLowerCase().indexOf(NET.query) !== -1 ||
    node.id.toLowerCase().indexOf(NET.query) !== -1;
}

function netDraw() {
  const canvas = document.getElementById('net-canvas');
  if (!canvas || !document.getElementById('network').classList.contains('visible')) return;
  const holder = document.getElementById('network');
  const width = holder.clientWidth, height = holder.clientHeight;
  const g = canvas.getContext('2d');
  const view = NET.view;
  const dpr = window.devicePixelRatio || 1;
  if (canvas.width !== width * dpr) canvas.width = width * dpr;
  if (canvas.height !== height * dpr) canvas.height = height * dpr;
  const dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.clearRect(0, 0, canvas.width, canvas.height);
  g.setTransform(view.k * dpr, 0, 0, view.k * dpr,
    (width / 2 + view.x) * dpr, (height / 2 + view.y) * dpr);

  // resolve focus only to nodes actually on the map (claims/briefs and
  // chip-filtered kinds must not dim the whole map with nothing lit)
  const onMap = id => !!id && NET.byId.has(id) && netVisible(NET.byId.get(id));
  const focusId = onMap(NET.hovered) ? NET.hovered : (onMap(NET.selected) ? NET.selected : null);
  const neighborhood = focusId ? NET.adj.get(focusId) : null;
  const simNeighbors = focusId && NET.similarOn ? NET.simAdj.get(focusId) : null;
  function emphasis(id) {
    if (!focusId) return 1;
    if (id === focusId || (neighborhood && neighborhood.has(id)) ||
        (simNeighbors && simNeighbors.has(id))) return 1;
    return 0.12;
  }

  g.lineWidth = 1 / view.k;
  NET.links.forEach(link => {
    if (link.kind === 'similar' && !NET.similarOn) return;
    if (!netVisible(link.a) || !netVisible(link.b)) return;
    let alpha = 0.12;
    if (focusId && (link.a.id === focusId || link.b.id === focusId)) alpha = 0.7;
    else if (focusId) alpha = 0.03;
    if (link.kind === 'similar') {
      g.strokeStyle = 'rgba(204,120,40,' + alpha * 0.8 + ')';
    } else {
      g.strokeStyle = (dark ? 'rgba(200,210,220,' : 'rgba(60,70,80,') + alpha + ')';
    }
    g.beginPath();
    g.moveTo(link.a.x, link.a.y);
    g.lineTo(link.b.x, link.b.y);
    g.stroke();
  });

  NET.nodes.forEach(node => {
    if (!netVisible(node)) return;
    const r = netRadius(node);
    // focus dim wins uniformly; year shading applies only to lit nodes
    // (multiplying both would make dimmed old works invisible)
    const em = emphasis(node.id);
    g.globalAlpha = em < 1 ? em : nodeAlpha(node);
    g.fillStyle = KIND_COLORS[node.kind];
    g.beginPath();
    g.arc(node.x, node.y, r, 0, 6.2832);
    g.fill();
    if (node.id === NET.selected) {
      g.globalAlpha = 1;
      g.strokeStyle = dark ? '#fff' : '#000';
      g.lineWidth = 2 / view.k;
      g.stroke();
    }
    if (netMatches(node)) {
      g.globalAlpha = 1;  // search hits stay visible even outside a focused neighborhood
      g.strokeStyle = '#dd3';
      g.lineWidth = 2.5 / view.k;
      g.beginPath();
      g.arc(node.x, node.y, r + 3 / view.k, 0, 6.2832);
      g.stroke();
    }
  });

  g.globalAlpha = 1;
  g.fillStyle = dark ? '#e6e6e6' : '#1a1a1a';
  g.font = (12 / view.k) + 'px system-ui, sans-serif';
  NET.nodes.forEach(node => {
    if (!netVisible(node)) return;
    // labels only on explicit selection: clicked, hovered, or search-matched
    const show = node.id === NET.selected || node.id === NET.hovered || netMatches(node);
    if (!show) return;
    const label = node.label.length > 42 ? node.label.slice(0, 40) + '\\u2026' : node.label;
    g.fillText(label, node.x + netRadius(node) + 3 / view.k, node.y + 4 / view.k);
  });
}

function netNodeAt(clientX, clientY) {
  const holder = document.getElementById('network');
  const rect = holder.getBoundingClientRect();
  const view = NET.view;
  const x = (clientX - rect.left - rect.width / 2 - view.x) / view.k;
  const y = (clientY - rect.top - rect.height / 2 - view.y) / view.k;
  let best = null, bestD = 1e9;
  NET.nodes.forEach(node => {
    if (!netVisible(node)) return;
    const dx = node.x - x, dy = node.y - y;
    const d = Math.sqrt(dx * dx + dy * dy);
    if (d < netRadius(node) + 4 / view.k && d < bestD) { best = node; bestD = d; }
  });
  return best ? {node: best, x: x, y: y} : {node: null, x: x, y: y};
}

let dragNode = null;
let dragOffset = null;
let panning = null;
let moved = false;
let downAt = null;

function netEvents() {
  const canvas = document.getElementById('net-canvas');
  canvas.addEventListener('mousedown', e => {
    moved = false;
    downAt = {x: e.clientX, y: e.clientY};
    const hit = netNodeAt(e.clientX, e.clientY);
    if (hit.node) {
      dragNode = hit.node;
      dragOffset = {dx: hit.node.x - hit.x, dy: hit.node.y - hit.y};
    } else {
      panning = {x: e.clientX - NET.view.x, y: e.clientY - NET.view.y};
    }
  });
  canvas.addEventListener('mousemove', e => {
    if (downAt && Math.abs(e.clientX - downAt.x) + Math.abs(e.clientY - downAt.y) > 3) {
      moved = true;
    }
    if (dragNode) {
      if (!moved) return;
      const hit = netNodeAt(e.clientX, e.clientY);
      dragNode.x = hit.x + dragOffset.dx; dragNode.y = hit.y + dragOffset.dy;
      dragNode.vx = 0; dragNode.vy = 0;
      if (!NET.running) netDraw();
      return;
    }
    if (panning) {
      NET.userMoved = true;
      NET.view.x = e.clientX - panning.x;
      NET.view.y = e.clientY - panning.y;
      netDraw();
      return;
    }
    const hit = netNodeAt(e.clientX, e.clientY);
    const id = hit.node ? hit.node.id : null;
    if (id !== NET.hovered) {
      NET.hovered = id;
      canvas.style.cursor = id ? 'pointer' : 'grab';
      netDraw();
    }
  });
  window.addEventListener('mouseup', e => {
    if (dragNode && !moved) focusNode(dragNode.id);
    dragNode = null;
    dragOffset = null;
    panning = null;
    downAt = null;
  });
  canvas.addEventListener('mouseleave', () => {
    if (NET.hovered) {
      NET.hovered = null;
      canvas.style.cursor = 'grab';
      netDraw();
    }
  });
  canvas.addEventListener('wheel', e => {
    e.preventDefault();
    NET.userMoved = true;
    const holder = document.getElementById('network');
    const rect = holder.getBoundingClientRect();
    const mx = e.clientX - rect.left - rect.width / 2;
    const my = e.clientY - rect.top - rect.height / 2;
    const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
    const k = Math.min(8, Math.max(0.15, NET.view.k * factor));
    NET.view.x = mx - (mx - NET.view.x) * (k / NET.view.k);
    NET.view.y = my - (my - NET.view.y) * (k / NET.view.k);
    NET.view.k = k;
    netDraw();
  }, {passive: false});
}

function renderChips() {
  const holder = document.getElementById('chips');
  Object.keys(KIND_COLORS).forEach(kind => {
    const chip = el('span', {className: 'chip', textContent: kind});
    chip.style.background = KIND_COLORS[kind];
    chip.onclick = () => {
      NET.kindOn[kind] = !NET.kindOn[kind];
      chip.classList.toggle('off', !NET.kindOn[kind]);
      netDraw();
    };
    holder.appendChild(chip);
  });
  const similar = el('span', {className: 'chip', textContent: 'similarity'});
  similar.style.background = '#cc7828';
  similar.onclick = () => {
    NET.similarOn = !NET.similarOn;
    similar.classList.toggle('off', !NET.similarOn);
    netDraw();
  };
  holder.appendChild(similar);
}

/* ---------------- shared detail pane and view toggle ---------------- */

function showView(name) {
  document.getElementById('board').classList.toggle('visible', name === 'board');
  document.getElementById('network').classList.toggle('visible', name === 'network');
  document.getElementById('view-board').classList.toggle('active', name === 'board');
  document.getElementById('view-network').classList.toggle('active', name === 'network');
  document.getElementById('relayout').style.display = name === 'network' ? 'inline-block' : 'none';
  if (name === 'network') netDraw(); else scheduleWires();
}

function nodeLink(id) {
  const node = DATA.nodes[id];
  const a = el('a', {className: 'edge-link', textContent: node ? node.label : id});
  a.setAttribute('tabindex', '0');
  a.onclick = () => focusNode(id);
  a.onkeydown = e => { if (e.key === 'Enter') focusNode(id); };
  return a;
}

function renderDetail(id) {
  const detail = document.getElementById('detail');
  detail.replaceChildren();
  const node = DATA.nodes[id];
  const ctx = ctxOf(id);
  const content = DATA.contents[id];

  detail.appendChild(el('h2', {textContent: node.label}));
  detail.appendChild(el('div', {textContent: 'kind: ' + node.kind}));
  Object.entries(node.attrs || {}).forEach(pair => {
    if (typeof pair[1] === 'string') {
      detail.appendChild(el('div', {textContent: pair[0] + ': ' + pair[1]}));
    }
  });
  if (!ctx) return;

  if (ctx.parents.length) {
    detail.appendChild(el('div', {className: 'section-title', textContent: 'Parents'}));
    ctx.parents.forEach(p => detail.appendChild(el('div', {}, [nodeLink(p.id)])));
  }

  detail.appendChild(el('div', {className: 'section-title',
    textContent: 'Children (' + ctx.children.returned + ' of ' + ctx.children.total + ')'}));
  if (ctx.children.truncated) {
    detail.appendChild(el('div', {className: 'truncated-note',
      textContent: 'showing the first page only — the port does not paginate this field further'}));
  }
  ctx.children.items.forEach(c => detail.appendChild(el('div', {}, [nodeLink(c.id)])));

  detail.appendChild(el('div', {className: 'section-title',
    textContent: 'Edges (' + ctx.edges.returned + ' of ' + ctx.edges.total + ')'}));
  if (ctx.edges.truncated) {
    detail.appendChild(el('div', {className: 'truncated-note',
      textContent: 'showing the first page only — the port does not paginate this field further'}));
  }
  ctx.edges.items.forEach(e => {
    const other = e.from === id ? e.to : e.from;
    detail.appendChild(el('div', {}, [
      document.createTextNode(e.kind + ' \\u2192 '),
      nodeLink(other),
    ]));
  });

  if (content) {
    detail.appendChild(el('div', {className: 'section-title', textContent: 'Content'}));
    detail.appendChild(el('div', {className: 'content-block', textContent: content.content}));
    if (content.truncated) {
      detail.appendChild(el('div', {className: 'truncated-note', textContent: 'content truncated'}));
    }
  }
}

document.getElementById('search').addEventListener('input', applySearch);
document.getElementById('clear-focus').addEventListener('click', clearFocus);
document.getElementById('view-board').addEventListener('click', () => showView('board'));
document.getElementById('view-network').addEventListener('click', () => showView('network'));
document.getElementById('relayout').addEventListener('click', () => {
  NET.userMoved = false;  // re-layout hands the camera back to auto-fit
  startSim(300);
});
window.addEventListener('resize', () => { scheduleWires(); netDraw(); });
if (window.matchMedia) {
  const scheme = window.matchMedia('(prefers-color-scheme: dark)');
  if (scheme.addEventListener) scheme.addEventListener('change', () => netDraw());
}
renderBoard();
renderChips();
buildNetwork();
netEvents();
clearFocus();
showView('network');
startSim(300);
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
        "<div id=\"topbar\">"
        "<h1>Palace Viewer</h1>"
        "<button id=\"view-network\">Network</button>"
        "<button id=\"view-board\">Layers</button>"
        "<input id=\"search\" type=\"search\" placeholder=\"filter nodes…\">"
        "<span id=\"chips\"></span>"
        "<button id=\"relayout\">re-layout</button>"
        "<button id=\"clear-focus\">clear focus</button>"
        "<span id=\"hint\">click a node to focus; wheel = zoom, drag = pan</span>"
        "</div>"
        "<div id=\"main\">"
        "<div id=\"network\"><canvas id=\"net-canvas\"></canvas></div>"
        "<div id=\"board\"><svg id=\"wires\"></svg></div>"
        "<div id=\"detail\"></div>"
        "</div>"
        "<script type=\"application/json\" id=\"palace-data\">" + safe_json + "</script>"
        "<script>" + _SCRIPT + "</script>"
        "</body></html>\n"
    )
    return html.encode("utf-8")
