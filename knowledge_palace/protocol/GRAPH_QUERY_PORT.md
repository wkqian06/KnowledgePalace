# GraphQueryPort — UI-neutral internal query contract (schema v1.0)

The one internal, read-only query contract over the rebuildable Graph Index.
Data flow is fixed: `Vault → rebuildable Graph Index → GraphQueryPort → future
Adapter → Viewer`. The contract consists of this document, the canonical
schema `graph_query_port.schema.json`, the validator
`tools/gqp_validator.py`, and contract tests; the Graph Index and a
production port are implementation decisions (storage format included
— SQLite is a candidate, not a commitment). Any implementation must pass the
validator and contract tests unchanged. No HTTP surface, no server, no
Viewer code belongs to this contract.

## Types

| Type | Fields | Notes |
|---|---|---|
| `IndexSnapshot` | `snapshot_id`, `vault_fingerprint`, `built_at` | identifies the index build a response was served from |
| `CanonicalRef` | `root` (`vault\|state\|source\|workspace\|framework`), `path`, `anchor?` | logical reference; `path` is a relative, forward-slash path — never absolute, no `..`, no backslash, no drive letter |
| `NodeView` | `id`, `kind`, `label`, `canonical_ref?`, `attrs{}` | `kind` is an OPEN set (registry-driven); consumers must tolerate unknown kinds |
| `EdgeView` | `id`, `kind`, `from`, `to`, `attrs{}` | directed; weights and qualitative bands ride in `attrs` |
| `HierarchySpec` | `id`, `label`, `levels[]` (`level`, `label`, `node_kinds[]`) | registry-defined; multiple hierarchies coexist |
| `GraphPage` | `total`, `returned`, `truncated`, `next_cursor`, `items[]` | bounded pagination, see rules below |
| Error | `error.code`, `error.message`, `error.evidence?` | typed rejection; carries `schema_version` (snapshot optional) |

## Operations (the complete surface)

| Operation | Request | Success response |
|---|---|---|
| `list_hierarchies` | — | `hierarchies: [HierarchySpec]` |
| `list_levels` | `hierarchy_id` | `hierarchy_id`, `levels: [HierarchyLevel]` |
| `query_level` | `hierarchy_id`, `level`, `filters?`, `cursor?`, `limit?` | `page: GraphPage<NodeView>` |
| `query_context` | `node_id`, `entry_parent?`, `cursor?`, `limit?` | `node`, `parents`, `entry_parent`, `siblings` or `sibling_groups`, `children`, `edges` |
| `get_content` | `node_id` | `node_id`, `canonical_ref`, `media_type`, `content`, `truncated` |

These five operations are the entire surface. The port exposes **zero
authoritative writes**: no create, update, delete, annotate, or rebuild
operation exists in the contract, and implementations must not add one.

## Envelope rules

- Every response — success or error — carries `schema_version` (`"1.0"`).
- Every success response carries `snapshot` (an `IndexSnapshot`).
- Errors use the closed code set: `stale_index`, `unknown_hierarchy`,
  `unknown_node`, `unknown_operation`, `bad_cursor`, `invalid_request`.

## Stale-index rejection

The Graph Index is a deletable one-way projection of the Vault. Before serving
any operation, an implementation MUST compare its index's
`vault_fingerprint` against the current Vault fingerprint. On mismatch it MUST
refuse the query with `error.code = "stale_index"` and a rebuild hint in
`error.message` — it must never silently serve stale data. A spec-conforming
stale rejection is a valid response; a success response served from a stale
index is a contract violation (`tools/gqp_validator.py` checks this when
given the current fingerprint).

## Pagination rules

- Every list-shaped result is a `GraphPage` with explicit `total`, `returned`,
  `truncated`, `next_cursor`. Silent omission is forbidden:
  `returned == len(items)`; `returned ≤ total`; `truncated` means more items
  remain after this page and holds exactly when `next_cursor` is non-null; a
  truncated page has `returned < total`; and following `next_cursor` to
  exhaustion yields exactly `total` items — a page must never claim completion
  (`truncated == false`) while a continuation exists.
- `limit` is bounded by the implementation (default 50, hard cap 500);
  cursors are opaque strings; an unusable cursor yields `bad_cursor`.

## Context and multi-parent rules

- `query_context` returns the node, its parents, bounded children, and bounded
  edges.
- Multi-parent nodes keep the caller's entry parent: when `entry_parent` is
  given (and is a real parent), `siblings` is one GraphPage computed under that
  parent and `entry_parent` echoes it. Without an entry parent, a multi-parent
  node returns `sibling_groups` — one `{parent_id, page}` group per parent —
  and `siblings` is null. Single-parent nodes may use `siblings` directly with
  `entry_parent` set to the sole parent.

## Brief is a view, never evidence

Nodes of kind `brief` carry `attrs.role = "view"` and
`attrs.evidence_capable = false`. No evidence-bearing edge (`evidence`,
`supports`, `disputes`, `claims`) may originate from a brief node. Briefs can
locate the sources they cite; they can never generate an evidence edge.

## Logical references only

All content addressing uses `CanonicalRef`. Absolute filesystem paths,
`..` escapes, backslash separators, drive letters, HOME expansions, and URLs
are contract violations anywhere in a response. `get_content` serves card
content by logical reference; full paper texts live only in Source Cache and
are never returned by the port.

## Versioning

`schema_version` follows `major.minor`: additive optional fields bump the
minor; anything breaking bumps the major and requires a new design-decision record. Validators
reject responses whose major version they do not know.
