"""The argument graph of a section as one self-contained, editable page.

The page is a canvas in the manner of papergraph (design reference, see
workflows/SOURCES.md): paragraphs are boxes stacked in reading order, nodes are
short phrases placed inside them, and relations are arrows whose head shows the
relation. The author drags nodes, draws arrows from a node's handle, picks a
relation on an arrow, edits phrases in place and saves. Hand-rolled CSS/JS, no
outbound call, nothing to install.

The page embeds two JSON blocks: ``graph``, which the author edits, and
``written``, the graph the current text was written from. It marks every
paragraph whose content differs between the two and writes itself back to disk
on Save.

A graph is ``{"title", "section", "paragraphs", "nodes", "edges"}``.
``paragraphs`` are ``{"id", "role", "point"}`` in reading order; ``nodes`` are
``{"id", "text", "evidence", "paragraph", "x", "y"}`` with ``x``/``y`` local to
their paragraph's box and absent until the page has placed them; ``edges`` are
``{"id", "from", "to", "label"}`` whose endpoints are node or paragraph ids.
Positions are presentation only: nothing below compares them.
"""

import html
import json
import re

LINKS = ("supports", "opposes", "infers", "qualifies", "defines", "associates")
ROLES = ("opening", "middle", "closing")

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root { --ink: #1a1a1a; --soft: #6b6b68; --line: #cfcfcb; --paper: #fff; --chip: #f6f6f3; --box: #fff; --accent: #b4532a; --glow: rgba(180, 83, 42, 0.18); }
@media (prefers-color-scheme: dark) {
  :root { --ink: #e8e8e6; --soft: #9a9a96; --line: #44443f; --paper: #1b1b1a; --chip: #232322; --box: #2c2c2a; --accent: #e08a5b; --glow: rgba(224, 138, 91, 0.25); }
}
html, body { height: 100%; margin: 0; }
body { font-family: -apple-system, system-ui, sans-serif; color: var(--ink); background: var(--paper); display: flex; flex-direction: column; overflow: hidden; }
header { display: flex; align-items: center; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
h1 { font-size: 17px; margin: 0; flex: 1; min-width: 12em; }
#status { color: var(--soft); font-size: 13px; }
button, select { font: inherit; color: var(--ink); background: var(--chip); border: 1px solid var(--line); border-radius: 6px; cursor: pointer; padding: 3px 10px; }
#save { font-weight: 600; }
.legend { color: var(--soft); font-size: 12.5px; padding: 6px 16px; border-bottom: 1px solid var(--line); line-height: 1.5; }
.legend b { color: var(--ink); font-weight: 600; }
.legend .sym { font-family: ui-monospace, monospace; }
#canvas { flex: 1; width: 100%; touch-action: none; cursor: grab; color: var(--ink); }
#canvas.busy { cursor: grabbing; }
.region > rect { fill: var(--chip); stroke: var(--line); stroke-width: 1.2; }
.region.selected > rect { stroke: var(--soft); stroke-width: 1.6; }
.region.changed > rect { stroke: var(--accent); stroke-width: 2; }
.head { display: flex; align-items: center; gap: 8px; padding: 7px 12px; font-size: 14px; color: var(--ink); }
.head .mark { font-weight: 700; }
.region.changed .head .mark::after { content: " \25CF"; color: var(--accent); }
.head .point { flex: 1; font-weight: 600; outline: none; border-radius: 4px; padding: 0 3px; min-width: 6em; }
.head .point:focus { box-shadow: 0 0 0 2px var(--accent); }
.head .point:empty::before { content: "the paragraph's point, in a few words"; color: var(--soft); font-weight: 400; font-style: italic; }
.head select { padding: 1px 6px; font-size: 13px; }
.head button { padding: 0 6px; border: none; background: none; color: var(--soft); font-size: 14px; }
.head button:hover { color: var(--accent); }
.node { cursor: move; }
.box { box-sizing: border-box; background: var(--box); border: 1px solid var(--line); border-radius: 9px; padding: 6px 10px; font-size: 13.5px; line-height: 1.35; color: var(--ink); }
.node.selected .box { border-color: var(--accent); box-shadow: 0 0 0 3px var(--glow); }
.phrase { outline: none; min-height: 1.3em; word-wrap: break-word; }
.phrase:empty::before { content: "phrase"; color: var(--soft); font-style: italic; }
.evidence { color: var(--soft); font-size: 11.5px; outline: none; margin-top: 2px; word-wrap: break-word; }
.evidence:not(:empty)::before { content: "["; }
.evidence:not(:empty)::after { content: "]"; }
.evidence:empty { display: none; }
.node:hover .evidence:empty, .node.selected .evidence:empty { display: block; }
.evidence:empty::before { content: "evidence"; font-style: italic; }
foreignObject { overflow: visible; }
.box { position: relative; }
.tools { display: none; position: absolute; right: 2px; top: 100%; margin-top: 3px; gap: 2px; background: var(--box); border: 1px solid var(--line); border-radius: 6px; padding: 1px 2px; white-space: nowrap; }
.node:hover .tools, .node.selected .tools { display: flex; }
.tools button { border: none; background: none; color: var(--soft); padding: 0 5px; font-size: 12px; line-height: 1.4; }
.tools button:hover { color: var(--accent); }
[contenteditable="true"] { cursor: text; box-shadow: 0 0 0 2px var(--accent); border-radius: 4px; }
.handle { fill: var(--paper); stroke: var(--accent); stroke-width: 1.5; cursor: crosshair; opacity: 0; }
.node:hover .handle, .node.selected .handle { opacity: 1; }
.edge .hit { stroke: transparent; stroke-width: 22; cursor: pointer; }
.edge .line { stroke: currentColor; stroke-width: 1.4; fill: none; }
.edge:hover .line { stroke-width: 2.2; }
.edge.selected .line { stroke: var(--accent); stroke-width: 2.4; }
.edge .label { font-size: 11.5px; fill: var(--accent); paint-order: stroke; stroke: var(--paper); stroke-width: 4; display: none; pointer-events: none; }
.edge:hover .label, .edge.selected .label { display: block; }
.ghost { stroke: var(--accent); stroke-width: 1.5; stroke-dasharray: 5 4; pointer-events: none; }
#pop { position: absolute; display: none; background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 4px; box-shadow: 0 4px 16px rgba(0,0,0,0.18); gap: 2px; font-size: 13px; z-index: 2; }
#pop button { border: none; background: none; padding: 3px 7px; }
#pop button.on { background: var(--accent); color: #fff; border-radius: 5px; }
#pop button:hover:not(.on) { color: var(--accent); }
</style>
</head>
<body>
<header>
  <h1 id="title"></h1>
  <span id="status"></span>
  <button id="fit" type="button" title="show everything">Fit</button>
  <button id="addp" type="button">+ paragraph</button>
  <button id="save" type="button">Save</button>
</header>
<div class="legend">
  Arrow heads: <span class="sym">&#9650;</span> <b>supports</b> &nbsp; <span class="sym">&#9475;</span> <b>opposes</b> &nbsp; <span class="sym">&#187;</span> <b>infers</b> &nbsp; <span class="sym">&#9670;</span> <b>qualifies</b> &nbsp; <span class="sym">&#9651;</span> <b>defines</b> &nbsp; <span class="sym">&#9675;</span> <b>associates</b>.
  <b>Node:</b> point at it for its buttons &mdash; <b>&rarr; next</b> adds a node joined by an arrow, <b>link</b> starts an arrow you drop on another node or paragraph, <b>&times;</b> deletes it; double-click to edit, drag to move (also into another paragraph).
  <b>Arrow:</b> click it to pick its relation, turn it round or delete it.
  <b>Paragraph:</b> <b>+ node</b> adds a node, <b>arrange</b> lays it out, &uarr;&darr; reorder.
  Wheel scrolls, Ctrl+wheel zooms. A dot after &para; marks a paragraph whose graph changed since its text was written.
</div>
<svg id="canvas" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="m-supports" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker>
    <marker id="m-opposes" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="10" markerHeight="10" orient="auto"><path d="M6,0 L6,10" stroke="currentColor" stroke-width="2.5"/></marker>
    <marker id="m-infers" viewBox="0 0 12 10" refX="11" refY="5" markerWidth="12" markerHeight="10" orient="auto"><path d="M0,0 L5,5 L0,10 M6,0 L11,5 L6,10" fill="none" stroke="currentColor" stroke-width="1.8"/></marker>
    <marker id="m-qualifies" viewBox="0 0 12 10" refX="11" refY="5" markerWidth="12" markerHeight="10" orient="auto"><path d="M1,5 L6,0 L11,5 L6,10 z" fill="currentColor"/></marker>
    <marker id="m-defines" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" markerHeight="10" orient="auto"><path d="M1,1 L9,5 L1,9 z" fill="var(--paper)" stroke="currentColor" stroke-width="1.5"/></marker>
    <marker id="m-associates" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" markerHeight="10" orient="auto"><circle cx="5" cy="5" r="3.6" fill="var(--paper)" stroke="currentColor" stroke-width="1.5"/></marker>
  </defs>
  <g id="world"></g>
</svg>
<div id="pop"></div>
<script type="application/json" id="graph">__GRAPH__</script>
<script type="application/json" id="written">__WRITTEN__</script>
<script>
const LINKS = ["supports", "opposes", "infers", "qualifies", "defines", "associates"];
const ROLES = ["opening", "middle", "closing"];
const NS = "http://www.w3.org/2000/svg";
const NODE_W = 210, PAD = 16, HEAD = 40, GAP = 14, REGION_W = 960, REGION_GAP = 36;
const graph = JSON.parse(document.getElementById("graph").textContent);
const written = JSON.parse(document.getElementById("written").textContent);
const svg = document.getElementById("canvas"), world = document.getElementById("world");
const pop = document.getElementById("pop"), status = document.getElementById("status");
const view = {x: 24, y: 24, k: 1};
const heights = new Map();
let selected = null, mode = null, dirty = false, handle = null, lastLabel = "supports";

const uid = prefix => prefix + Math.random().toString(36).slice(2, 8);
const byId = (list, id) => list.find(item => item.id === id);
const members = p => graph.nodes.filter(n => n.paragraph === p.id);
const nodeH = n => heights.get(n.id) || 44;
const clampX = x => Math.max(PAD, Math.min(REGION_W - NODE_W - PAD, x));

function svgEl(tag, attrs) {
  const node = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, value);
  return node;
}
function el(tag, attrs, ...kids) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  }
  node.append(...kids);
  return node;
}

// ---- geometry ----
function stack() {
  let y = 0;
  for (const p of graph.paragraphs) {
    const bottom = Math.max(0, ...members(p).map(n => n.y + nodeH(n)));
    p.x = 0; p.w = REGION_W; p.h = Math.max(110, bottom + PAD); p.y = y;
    y += p.h + REGION_GAP;
  }
}
function rectOf(id) {
  const n = byId(graph.nodes, id);
  if (n) { const p = byId(graph.paragraphs, n.paragraph); return {x: n.x, y: (p ? p.y : 0) + n.y, w: NODE_W, h: nodeH(n)}; }
  const p = byId(graph.paragraphs, id);
  return p && {x: p.x, y: p.y, w: p.w, h: p.h};
}
const centre = r => ({x: r.x + r.w / 2, y: r.y + r.h / 2});
function border(r, toward) {
  const c = centre(r), dx = toward.x - c.x, dy = toward.y - c.y;
  if (!dx && !dy) return c;
  const t = Math.min(dx ? (r.w / 2) / Math.abs(dx) : Infinity, dy ? (r.h / 2) / Math.abs(dy) : Infinity);
  return {x: c.x + dx * t, y: c.y + dy * t};
}
function worldPoint(event) {
  const r = svg.getBoundingClientRect();
  return {x: (event.clientX - r.left - view.x) / view.k, y: (event.clientY - r.top - view.y) / view.k};
}
function screenPoint(pt) {
  const r = svg.getBoundingClientRect();
  return {x: r.left + view.x + pt.x * view.k, y: r.top + view.y + pt.y * view.k};
}

// ---- drawing ----
function draw() {
  world.replaceChildren();
  stack();
  graph.paragraphs.forEach((p, index) => world.append(region(p, index)));
  for (const e of graph.edges) { const g = edge(e); if (g) world.append(g); }
  for (const n of graph.nodes) world.append(node(n));
  world.setAttribute("transform", `translate(${view.x} ${view.y}) scale(${view.k})`);
  mark();
  popover();
}
function measure() {
  let changed = false;
  for (const g of world.querySelectorAll("g.node")) {
    const h = Math.max(36, g.querySelector(".box").scrollHeight + 2);
    if (heights.get(g.dataset.id) !== h) { heights.set(g.dataset.id, h); changed = true; }
  }
  return changed;
}
function render() { draw(); if (measure()) draw(); }

function region(p, index) {
  const g = svgEl("g", {class: "region" + (selected && selected.id === p.id ? " selected" : ""), "data-id": p.id});
  g.append(svgEl("rect", {x: p.x, y: p.y, width: p.w, height: p.h, rx: 10}));
  const fo = svgEl("foreignObject", {x: p.x, y: p.y, width: p.w, height: HEAD});
  const role = el("select", {title: "role in the section"});
  for (const option of ROLES) role.append(el("option", {value: option, text: option}));
  role.value = p.role || "middle";
  role.addEventListener("change", () => { p.role = role.value; touch(); });
  const point = el("span", {class: "point", contenteditable: "true", spellcheck: "false", text: p.point || ""});
  point.addEventListener("input", () => { p.point = point.textContent.trim(); touch(); });
  point.addEventListener("keydown", event => { if (event.key === "Enter") { event.preventDefault(); point.blur(); } });
  point.addEventListener("paste", plainPaste);
  const act = (label, title, run) => el("button", {type: "button", title, onclick: () => { run(); render(); touch(); }, text: label});
  fo.append(el("div", {class: "head"},
    el("span", {class: "mark", text: "¶" + (index + 1)}), role, point,
    act("+ node", "add a node to this paragraph", () => addNode(p, {x: PAD, y: Math.max(HEAD + 6, ...members(p).map(n => n.y + nodeH(n) + GAP))})),
    act("↑", "move this paragraph up", () => swap(index, -1)),
    act("↓", "move this paragraph down", () => swap(index, 1)),
    act("arrange", "lay out the nodes of this paragraph along its arrows", () => arrange(p)),
    act("×", "delete this paragraph with its nodes", () => {
      if (!confirm("Delete this paragraph and its nodes from the graph?")) return;
      const ids = new Set(members(p).map(n => n.id));
      graph.nodes = graph.nodes.filter(n => !ids.has(n.id));
      graph.edges = graph.edges.filter(e => !ids.has(e.from) && !ids.has(e.to) && e.from !== p.id && e.to !== p.id);
      graph.paragraphs.splice(index, 1);
      selected = null;
    })));
  g.append(fo);
  return g;
}
function swap(index, step) {
  const target = index + step;
  if (target < 0 || target >= graph.paragraphs.length) return;
  const list = graph.paragraphs;
  [list[index], list[target]] = [list[target], list[index]];
}
function node(n) {
  const p = byId(graph.paragraphs, n.paragraph);
  const g = svgEl("g", {class: "node" + (selected && selected.id === n.id ? " selected" : ""), "data-id": n.id,
                        transform: `translate(${n.x} ${(p ? p.y : 0) + n.y})`});
  const fo = svgEl("foreignObject", {width: NODE_W, height: nodeH(n)});
  const tools = el("div", {class: "tools"},
    el("button", {type: "button", title: "add a node after this one, joined by an arrow", text: "→ next",
                  onclick: () => { const next = addNode(p, {x: n.x + NODE_W + GAP, y: n.y}, n); edit(world.querySelector(`g.node[data-id="${next.id}"] .phrase`)); }}),
    el("button", {type: "button", class: "link", title: "press and drag onto another node or paragraph to draw an arrow", text: "link"}),
    el("button", {type: "button", title: "delete this node and its arrows", text: "×", onclick: () => removeNode(n)}));
  fo.append(el("div", {class: "box"}, textField(n, "text", "phrase"), textField(n, "evidence", "evidence"), tools));
  g.append(fo, svgEl("circle", {class: "handle", cx: NODE_W, cy: nodeH(n) / 2, r: 7}));
  return g;
}
function addNode(p, at, after) {
  if (at.x + NODE_W > REGION_W - PAD) { at = {x: PAD, y: Math.max(HEAD + 6, ...members(p).map(m => m.y + nodeH(m) + GAP))}; }
  const n = {id: uid("n"), text: "", evidence: "", paragraph: p.id, x: clampX(at.x), y: Math.max(HEAD + 6, at.y)};
  graph.nodes.push(n);
  if (after) graph.edges.push({id: uid("e"), from: after.id, to: n.id, label: lastLabel});
  selected = {kind: "node", id: n.id};
  render(); touch();
  return n;
}
function removeNode(n) {
  graph.nodes = graph.nodes.filter(m => m.id !== n.id);
  graph.edges = graph.edges.filter(e => e.from !== n.id && e.to !== n.id);
  if (selected && selected.id === n.id) selected = null;
  render(); touch();
}
function textField(holder, key, cls) {
  const div = el("div", {class: cls, spellcheck: "false", text: holder[key] || ""});
  const commit = () => {
    if (div.contentEditable !== "true") return;   // blur and focusout both arrive; commit once
    div.contentEditable = "false";
    const value = div.textContent.replace(/\s+/g, " ").trim();
    if (value !== (holder[key] || "")) { holder[key] = value; touch(); }
    render();
  };
  div.addEventListener("blur", commit);
  div.addEventListener("focusout", commit);
  div.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === "Escape") { event.preventDefault(); commit(); div.blur(); } });
  div.addEventListener("paste", plainPaste);
  return div;
}
function plainPaste(event) {
  event.preventDefault();
  document.execCommand("insertText", false, event.clipboardData.getData("text/plain").replace(/\s+/g, " "));
}
function edit(div) {
  if (!div) return;
  div.contentEditable = "true";
  div.focus();
  const range = document.createRange();
  range.selectNodeContents(div);
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
}
function edge(e) {
  const a = rectOf(e.from), b = rectOf(e.to);
  if (!a || !b) return null;
  const s = border(a, centre(b)), t = border(b, centre(a));
  const g = svgEl("g", {class: "edge" + (selected && selected.id === e.id ? " selected" : ""), "data-id": e.id});
  g.append(svgEl("line", {class: "hit", x1: s.x, y1: s.y, x2: t.x, y2: t.y}),
           svgEl("line", {class: "line", x1: s.x, y1: s.y, x2: t.x, y2: t.y, "marker-end": `url(#m-${e.label})`}));
  const label = svgEl("text", {class: "label", x: (s.x + t.x) / 2, y: (s.y + t.y) / 2 - 7, "text-anchor": "middle"});
  label.textContent = e.label;
  g.append(label);
  return g;
}

// ---- layout ----
function arrange(p) {
  const inner = members(p), ids = new Set(inner.map(n => n.id)), layer = new Map(inner.map(n => [n.id, 0]));
  const local = graph.edges.filter(e => ids.has(e.from) && ids.has(e.to));
  for (let round = 0; round < inner.length; round++)
    for (const e of local) if (layer.get(e.from) + 1 > layer.get(e.to) && layer.get(e.from) < inner.length) layer.set(e.to, layer.get(e.from) + 1);
  const columns = Math.max(0, ...layer.values()) + 1;
  if (columns * (NODE_W + GAP) <= REGION_W - PAD) {
    // arrows run left to right: a column per layer, each chain kept on its own row
    const row = new Map(), taken = new Set();
    for (const n of inner) {
      const into = local.find(e => e.to === n.id && row.has(e.from));
      let r = into ? row.get(into.from) : 0;
      while (taken.has(layer.get(n.id) + ":" + r)) r++;
      row.set(n.id, r); taken.add(layer.get(n.id) + ":" + r);
    }
    const rowH = [];
    for (const n of inner) rowH[row.get(n.id)] = Math.max(rowH[row.get(n.id)] || 0, nodeH(n));
    const top = rowH.map((h, i) => HEAD + 6 + rowH.slice(0, i).reduce((sum, v) => sum + v + GAP, 0));
    for (const n of inner) { n.x = PAD + layer.get(n.id) * (NODE_W + GAP); n.y = top[row.get(n.id)]; }
    return;
  }
  const order = inner.map((n, i) => [layer.get(n.id), i, n]).sort((a, b) => a[0] - b[0] || a[1] - b[1]).map(row => row[2]);
  let x = PAD, y = HEAD + 6, rowH = 0;
  for (const n of order) {
    if (x + NODE_W > REGION_W - PAD && x > PAD) { x = PAD; y += rowH + GAP; rowH = 0; }
    n.x = x; n.y = y;
    x += NODE_W + GAP; rowH = Math.max(rowH, nodeH(n));
  }
}
function placeMissing() {
  const fresh = new Set();
  for (const n of graph.nodes) {
    if (!byId(graph.paragraphs, n.paragraph) && graph.paragraphs.length) n.paragraph = graph.paragraphs[0].id;
    if (n.x == null || n.y == null) { n.x = PAD; n.y = HEAD + 6; fresh.add(n.paragraph); }
  }
  render();
  for (const p of graph.paragraphs) if (fresh.has(p.id)) arrange(p);
  render();
}
function fit() {
  // fit the width: paragraphs stay readable and the wheel scrolls down the stack
  const r = svg.getBoundingClientRect();
  view.k = Math.min((r.width - 48) / REGION_W, 1.2);
  view.x = (r.width - REGION_W * view.k) / 2; view.y = 24;
  draw();
}

// ---- selection and changes ----
function choose(next) { selected = next; draw(); }
function touch() { dirty = true; status.textContent = "unsaved changes"; mark(); }
function canon(value) {
  if (Array.isArray(value)) return "[" + value.map(canon).join(",") + "]";
  if (value && typeof value === "object") return "{" + Object.keys(value).sort().map(k => JSON.stringify(k) + ":" + canon(value[k])).join(",") + "}";
  return JSON.stringify(value);
}
function signature(g, p) {
  const names = new Map([...g.nodes.map(n => [n.id, n.text || ""]), ...g.paragraphs.map(q => [q.id, "¶" + (q.point || "")])]);
  const ids = new Set(g.nodes.filter(n => n.paragraph === p.id).map(n => n.id));
  const nodes = g.nodes.filter(n => ids.has(n.id)).map(n => [n.text || "", n.evidence || ""]).map(canon).sort();
  const edges = g.edges.filter(e => ids.has(e.from) || ids.has(e.to) || e.from === p.id || e.to === p.id)
    .map(e => [names.get(e.from) || "", e.label, names.get(e.to) || ""]).map(canon).sort();
  return canon([p.role || "", p.point || "", nodes, edges]);
}
function mark() {
  const before = new Map(written.paragraphs.map(p => [p.id, signature(written, p)]));
  for (const g of world.querySelectorAll("g.region")) {
    const p = byId(graph.paragraphs, g.dataset.id);
    g.classList.toggle("changed", before.get(p.id) !== signature(graph, p));
  }
}
function popover() {
  const e = selected && selected.kind === "edge" && byId(graph.edges, selected.id);
  if (!e) { pop.style.display = "none"; return; }
  const a = rectOf(e.from), b = rectOf(e.to);
  const at = screenPoint({x: (border(a, centre(b)).x + border(b, centre(a)).x) / 2, y: (border(a, centre(b)).y + border(b, centre(a)).y) / 2});
  pop.replaceChildren(...LINKS.map(label => el("button", {type: "button", class: label === e.label ? "on" : "", text: label,
      onclick: () => { e.label = label; lastLabel = label; touch(); draw(); }})),
    el("button", {type: "button", title: "turn the arrow round", text: "⇄", onclick: () => { [e.from, e.to] = [e.to, e.from]; touch(); draw(); }}),
    el("button", {type: "button", title: "delete this arrow", text: "×", onclick: () => { graph.edges = graph.edges.filter(x => x !== e); selected = null; touch(); draw(); }}));
  pop.style.display = "flex";
  pop.style.left = Math.max(4, at.x - pop.offsetWidth / 2) + "px";
  pop.style.top = (at.y + 12) + "px";
}

// ---- pointer ----
svg.addEventListener("pointerdown", event => {
  if (event.button !== 0 || event.target.closest("button:not(.link), select, [contenteditable='true']")) return;
  const pt = worldPoint(event);
  const nodeEl = event.target.closest("g.node"), edgeEl = event.target.closest("g.edge"), regionEl = event.target.closest("g.region");
  if (event.target.closest(".handle, button.link")) {
    mode = {kind: "connect", from: nodeEl.dataset.id, line: svgEl("line", {class: "ghost"})};
    world.append(mode.line);
  } else if (nodeEl) {
    const n = byId(graph.nodes, nodeEl.dataset.id), r = rectOf(n.id);
    mode = {kind: "node", node: n, dx: pt.x - r.x, dy: pt.y - r.y, moved: false};
    choose({kind: "node", id: n.id});
  } else if (edgeEl) {
    choose({kind: "edge", id: edgeEl.dataset.id});
    return;
  } else {
    mode = {kind: "pan", sx: event.clientX, sy: event.clientY, vx: view.x, vy: view.y, region: regionEl && regionEl.dataset.id};
    svg.classList.add("busy");
  }
  svg.setPointerCapture(event.pointerId);
});
svg.addEventListener("pointermove", event => {
  if (!mode) return;
  const pt = worldPoint(event);
  if (mode.kind === "pan") {
    view.x = mode.vx + event.clientX - mode.sx; view.y = mode.vy + event.clientY - mode.sy;
    world.setAttribute("transform", `translate(${view.x} ${view.y}) scale(${view.k})`);
    popover();
  } else if (mode.kind === "node") {
    const n = mode.node, p = byId(graph.paragraphs, n.paragraph);
    n.x = pt.x - mode.dx; n.y = pt.y - mode.dy - (p ? p.y : 0); mode.moved = true;
    draw();
  } else if (mode.kind === "connect") {
    const s = border(rectOf(mode.from), pt);
    for (const [key, value] of Object.entries({x1: s.x, y1: s.y, x2: pt.x, y2: pt.y})) mode.line.setAttribute(key, value);
  }
});
svg.addEventListener("pointerup", event => {
  if (!mode) return;
  if (mode.kind === "node" && mode.moved) {
    const n = mode.node, from = byId(graph.paragraphs, n.paragraph);
    const c = {x: n.x + NODE_W / 2, y: (from ? from.y : 0) + n.y + nodeH(n) / 2};
    const target = graph.paragraphs.find(p => c.x >= p.x && c.x <= p.x + p.w && c.y >= p.y && c.y <= p.y + p.h);
    if (target && target.id !== n.paragraph) { n.y = c.y - nodeH(n) / 2 - target.y; n.paragraph = target.id; }
    n.x = clampX(n.x); n.y = Math.max(HEAD + 6, n.y);
    touch();
  } else if (mode.kind === "connect") {
    mode.line.remove();
    const under = document.elementFromPoint(event.clientX, event.clientY);
    const target = under && (under.closest("g.node") || under.closest("g.region"));
    const to = target && target.dataset.id;
    if (to && to !== mode.from && !graph.edges.some(e => e.from === mode.from && e.to === to)) {
      const e = {id: uid("e"), from: mode.from, to, label: lastLabel};
      graph.edges.push(e); selected = {kind: "edge", id: e.id}; touch();
    }
  } else if (mode.kind === "pan" && event.clientX === mode.sx && event.clientY === mode.sy) {
    selected = mode.region ? {kind: "region", id: mode.region} : null;
  }
  svg.classList.remove("busy");
  mode = null;
  try { svg.releasePointerCapture(event.pointerId); } catch (error) {}
  render();
});
svg.addEventListener("dblclick", event => {
  const nodeEl = event.target.closest("g.node");
  if (nodeEl) { edit(nodeEl.querySelector(event.target.closest(".evidence") ? ".evidence" : ".phrase")); return; }
  const regionEl = event.target.closest("g.region");
  if (!regionEl || event.target.closest(".head")) return;
  const p = byId(graph.paragraphs, regionEl.dataset.id), pt = worldPoint(event);
  const n = addNode(p, {x: pt.x - NODE_W / 2, y: pt.y - p.y - 18});
  edit(world.querySelector(`g.node[data-id="${n.id}"] .phrase`));
});
svg.addEventListener("wheel", event => {
  event.preventDefault();
  if (event.ctrlKey || event.metaKey) {
    const r = svg.getBoundingClientRect(), px = event.clientX - r.left, py = event.clientY - r.top;
    const k = Math.min(2.5, Math.max(0.25, view.k * Math.exp(-event.deltaY * 0.0015)));
    view.x = px - (px - view.x) * k / view.k; view.y = py - (py - view.y) * k / view.k; view.k = k;
  } else { view.x -= event.deltaX; view.y -= event.deltaY; }
  world.setAttribute("transform", `translate(${view.x} ${view.y}) scale(${view.k})`);
  popover();
}, {passive: false});
document.addEventListener("keydown", event => {
  if ((event.ctrlKey || event.metaKey) && event.key === "s") { event.preventDefault(); save(); return; }
  if (event.target.closest("[contenteditable='true'], select")) return;
  if (event.key === "Escape") { choose(null); return; }
  if ((event.key === "Delete" || event.key === "Backspace") && selected) {
    if (selected.kind === "node") removeNode(byId(graph.nodes, selected.id));
    else if (selected.kind === "edge") { graph.edges = graph.edges.filter(e => e.id !== selected.id); selected = null; touch(); render(); }
  }
});

// ---- save ----
function serialize() {
  return {title: graph.title, section: graph.section,
    paragraphs: graph.paragraphs.map(p => ({id: p.id, role: p.role || "middle", point: p.point || ""})),
    nodes: graph.nodes.map(n => ({id: n.id, text: n.text || "", evidence: n.evidence || "", paragraph: n.paragraph, x: Math.round(n.x), y: Math.round(n.y)})),
    edges: graph.edges.map(e => ({id: e.id, from: e.from, to: e.to, label: e.label}))};
}
function source() {
  const copy = document.documentElement.cloneNode(true);
  copy.querySelector("#world").replaceChildren();
  copy.querySelector("#pop").replaceChildren();
  copy.querySelector("#status").textContent = "";
  copy.querySelector("#title").textContent = "";
  copy.querySelector("#graph").textContent = JSON.stringify(serialize(), null, 1).replace(/<\//g, "<\\/");
  return "<!doctype html>\n" + copy.outerHTML + "\n";
}
async function save() {
  const page = source();
  const name = decodeURIComponent(location.pathname.split("/").pop()) || "argument-graph.html";
  const done = text => { dirty = false; status.textContent = text; };
  if (window.showSaveFilePicker) {
    try {
      if (!handle) handle = await window.showSaveFilePicker({suggestedName: name, types: [{description: "HTML", accept: {"text/html": [".html"]}}]});
      const stream = await handle.createWritable();
      await stream.write(page);
      await stream.close();
      return done("saved " + new Date().toLocaleTimeString());
    } catch (error) {
      if (error.name === "AbortError") return;
    }
  }
  el("a", {href: URL.createObjectURL(new Blob([page], {type: "text/html"})), download: name}).click();
  done("downloaded a copy: put it in place of this file");
}

document.getElementById("title").textContent = graph.title;
document.getElementById("save").addEventListener("click", save);
document.getElementById("fit").addEventListener("click", fit);
document.getElementById("addp").addEventListener("click", () => {
  graph.paragraphs.push({id: uid("p"), role: "middle", point: ""});
  render(); touch();
});
window.addEventListener("beforeunload", event => { if (dirty) event.preventDefault(); });
window.addEventListener("resize", () => draw());
placeMissing();
fit();
</script>
</body>
</html>
"""


def render_view(graph, written=None):
    """The page for ``graph``. ``written`` is the graph the current text was
    written from; left out, the text counts as written from ``graph`` itself."""
    page = PAGE.replace("__TITLE__", html.escape(graph["title"]))
    for slot, data in (("__GRAPH__", graph), ("__WRITTEN__", graph if written is None else written)):
        # "</" would end the script element that carries the JSON
        page = page.replace(slot, json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/"))
    return page


def read_view(page):
    """``(graph, written)`` from a page, whether Python or the browser saved it."""
    blocks = dict(re.findall(r'<script[^>]*\bid="(graph|written)"[^>]*>(.*?)</script>', page, flags=re.S))
    return json.loads(blocks["graph"]), json.loads(blocks["written"])


def paragraphs(graph):
    """The graph in reading order, for writing from it: each paragraph with its
    nodes (row by row, left to right, when the page has placed them) and the
    arrows that touch it, endpoints given as text."""
    names = {n["id"]: n["text"] for n in graph["nodes"]}
    names.update((p["id"], "¶" + p["point"]) for p in graph["paragraphs"])
    result = []
    for p in graph["paragraphs"]:
        inner = [n for n in graph["nodes"] if n.get("paragraph") == p["id"]]
        if all("x" in n and "y" in n for n in inner):
            inner.sort(key=lambda n: (round(n["y"] / 40), n["x"]))
        ids = {n["id"] for n in inner} | {p["id"]}
        result.append({"id": p["id"], "role": p["role"], "point": p["point"],
                       "nodes": [{"text": n["text"], "evidence": n.get("evidence", "")} for n in inner],
                       "edges": [(names.get(e["from"], ""), e["label"], names.get(e["to"], ""))
                                 for e in graph["edges"] if e["from"] in ids or e["to"] in ids]})
    return result


def signature(graph, paragraph):
    """What the text of a paragraph depends on: its role and point, its nodes,
    and the arrows that touch it. Positions are left out."""
    names = {n["id"]: n["text"] for n in graph["nodes"]}
    names.update((p["id"], "¶" + p["point"]) for p in graph["paragraphs"])
    ids = {n["id"] for n in graph["nodes"] if n.get("paragraph") == paragraph["id"]}
    return (paragraph["role"], paragraph["point"],
            sorted((n["text"], n.get("evidence", "")) for n in graph["nodes"] if n["id"] in ids),
            sorted((names.get(e["from"], ""), e["label"], names.get(e["to"], "")) for e in graph["edges"]
                   if e["from"] in ids or e["to"] in ids or paragraph["id"] in (e["from"], e["to"])))


def changed_paragraphs(graph, written):
    """What the author's edits ask of the text: paragraphs to rewrite (new, or
    different from what the text was written from), paragraphs to drop, whether
    the order of the surviving paragraphs changed, and nodes placed in no
    paragraph."""
    before = {p["id"]: signature(written, p) for p in written["paragraphs"]}
    now = [p["id"] for p in graph["paragraphs"]]
    return {
        "rewrite": [p["id"] for p in graph["paragraphs"] if before.get(p["id"]) != signature(graph, p)],
        "drop": [key for key in before if key not in now],
        "reordered": [key for key in now if key in before] != [key for key in before if key in now],
        "unplaced": [n["text"] for n in graph["nodes"] if n.get("paragraph") not in now],
    }
