"""Card and registry parsing → deterministic Work/Manifestation/Claim identity.

The primary key is the card's filename stem (== its slug by contract; a
mismatching ``slug:`` field is reported). External ids (DOI/arXiv) parsed from
``source:`` are secondary evidence: the same external id under two different
slugs, or near-duplicate titles, produce entries in ``confirmations`` for the
user — never a silent merge. Parse failures land per-file in ``parse_errors``;
nothing is skipped silently. All functions are read-only.
"""

import difflib
import re
from collections import Counter
from pathlib import Path

AXES = ("domain", "task", "pattern", "function", "method", "metric", "failure-mode")
GAP_RELATIONS = ("identifies", "supports", "partially_addresses", "disputes", "reframes")

_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"']+)")
_ARXIV = re.compile(r"(?:arxiv[.:/]+(?:abs/)?)(\d{4}\.\d{4,5})", re.IGNORECASE)
_CLAIM = re.compile(r"^- C(\d+)(?: \[([^\]]*)\])?: (.*)$")
_PROFILE_LINE = re.compile(r"^- ([a-z][a-z-]*): (C\d+(?:, ?C\d+)*)$")
_KEYLINE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")
_ROW = re.compile(r"^\| ([a-z0-9][a-z0-9-]*) \|")
TITLE_SIMILARITY = 0.92  # confirmation threshold — surfaces a pair, never merges


def split_frontmatter(text, origin):
    """Return (frontmatter_lines, body, problems)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], text, ["%s: missing frontmatter delimiter" % origin]
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], "\n".join(lines[index + 1 :]), []
    return [], text, ["%s: unterminated frontmatter" % origin]


def _parse_value(raw):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        items = []
        for item in raw[1:-1].split(","):
            item = item.strip().strip('"').strip("'").strip()
            if item:
                items.append(item)
        return items
    return raw.strip('"')


def _as_list(value, field, origin, problems):
    """List-shaped fields must be lists; a scalar is one problem, not chars."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    problems.append("%s: %s expected a [list], got %r" % (origin, field, value))
    return []


def parse_frontmatter(fm_lines, origin):
    """Single-line ``key: value`` subset; unknown shapes become problems."""
    values, problems = {}, []
    for lineno, raw in enumerate(fm_lines, start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        match = _KEYLINE.match(raw)
        if not match:
            problems.append("%s:%d: unparseable frontmatter line %r" % (origin, lineno, raw))
            continue
        key, rest = match.group(1), match.group(2)
        if key in values:
            problems.append("%s:%d: duplicate frontmatter key %r" % (origin, lineno, key))
            continue
        values[key] = _parse_value(rest)
    return values, problems


def extract_external_ids(source_value):
    ids = {}
    if isinstance(source_value, str):
        doi = _DOI.search(source_value)
        if doi:
            ids["doi"] = doi.group(1).rstrip(".").lower()
        arxiv = _ARXIV.search(source_value)
        if arxiv:
            ids["arxiv"] = arxiv.group(1)
    return ids


def parse_claims(body, origin):
    """Claims are ``- C<n>: <text>`` items; long quotes wrap onto two-space
    indented continuation lines and the anchor follows the last em-dash.
    An OPTIONAL bracket group carries per-claim concept bindings
    (``- C<n> [slug, slug]: …``); its absence — every historical claim — is
    an empty binding, never an error here (the new-ingest rule lives in
    ``semantic/binding.py``)."""
    claims, problems = [], []
    seen = set()
    lines = body.splitlines()
    index = 0
    while index < len(lines):
        match = _CLAIM.match(lines[index])
        index += 1
        if not match:
            continue
        number = int(match.group(1))
        bound_concepts = [
            slug.strip()
            for slug in (match.group(2) or "").split(",")
            if slug.strip()
        ]
        parts = [match.group(3)]
        while (
            index < len(lines)
            and lines[index].startswith("  ")
            and lines[index].strip()
            and not lines[index].lstrip().startswith("- ")
        ):
            parts.append(lines[index].strip())
            index += 1
        rest = " ".join(parts)
        if number in seen:
            problems.append("%s: duplicate claim number C%d" % (origin, number))
        seen.add(number)
        if " — " in rest:
            quote, anchor = rest.rsplit(" — ", 1)
            anchor = anchor.strip()
        else:
            quote, anchor = rest, None
            problems.append("%s: claim C%d has no evidence anchor" % (origin, number))
        claims.append(
            {
                "n": number,
                "quote": quote.strip(),
                "anchor": anchor,
                "concepts": bound_concepts,
            }
        )
    return claims, problems


def parse_profile_section(body, origin):
    """The optional ``## Study profile`` section: ``- <role>: C1, C3`` lines."""
    roles, problems = {}, []
    in_section = False
    for raw in body.splitlines():
        if raw.startswith("## "):
            in_section = raw.strip() == "## Study profile"
            continue
        if not in_section:
            continue
        stripped = raw.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        match = _PROFILE_LINE.match(stripped)
        if not match:
            problems.append("%s: bad Study profile line %r" % (origin, stripped))
            continue
        role = match.group(1)
        if role in roles:
            problems.append("%s: duplicate Study profile role %r" % (origin, role))
            continue
        roles[role] = [ref.strip() for ref in match.group(2).split(",")]
    return roles, problems


def _gap_entries(values, origin, problems):
    entries = []
    for raw in values or []:
        gap, sep, relation = raw.rpartition(":")
        if not sep or relation not in GAP_RELATIONS:
            problems.append("%s: bad gap entry %r" % (origin, raw))
            continue
        entries.append((gap, relation))
    return entries


def _card_files(directory):
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.md") if p.name != "INDEX.md")


def load_registry(concepts_path, problems):
    """`## <axis>` sections of `| Slug | Parents | Status | ... |` rows."""
    registry = {}
    axis = None
    for raw in concepts_path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("## "):
            axis = raw[3:].strip()
            continue
        match = _ROW.match(raw)
        if not (axis and match):
            continue
        cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
        slug = cells[0]
        if slug in registry:
            problems.append("concepts.md: duplicate slug %r" % slug)
            continue
        parents_cell = cells[1] if len(cells) > 1 else ""
        parents = [
            p.strip()
            for p in parents_cell.split(",")
            if p.strip() and p.strip() != "-"
        ]
        registry[slug] = {
            "axis": axis,
            "parents": parents,
            "status": cells[2] if len(cells) > 2 else "",
        }
    return registry


def load_domains(domains_path, problems):
    domains = {}
    for raw in domains_path.read_text(encoding="utf-8").splitlines():
        match = _ROW.match(raw)
        if match:
            cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
            domains[cells[0]] = cells[1] if len(cells) > 1 else cells[0]
    if not domains:
        problems.append("domains.md: no registry rows found")
    return domains


def load_vault_identity(vault):
    """Read the whole Vault (read-only) into an identity report."""
    vault = Path(vault)
    problems = []
    identity = {
        "works": {},
        "claims": {},
        "gaps": {},
        "transfers": {},
        "briefs": {},
        "registry": load_registry(vault / "concepts.md", problems),
        "domains": load_domains(vault / "domains.md", problems),
        "confirmations": [],
        "parse_errors": problems,
    }

    for path in _card_files(vault / "papers"):
        origin = "papers/" + path.name
        slug = path.stem
        fm_lines, body, errs = split_frontmatter(path.read_text(encoding="utf-8"), origin)
        problems.extend(errs)
        fm, fm_problems = parse_frontmatter(fm_lines, origin)
        problems.extend(fm_problems)
        if fm.get("slug") and fm["slug"] != slug:
            problems.append("%s: slug field %r != filename stem" % (origin, fm["slug"]))
        claims, claim_problems = parse_claims(body, origin)
        problems.extend(claim_problems)
        profile_roles, profile_problems = parse_profile_section(body, origin)
        problems.extend(profile_problems)
        work = {
            "profile_roles": profile_roles,
            "slug": slug,
            "title": fm.get("title", slug),
            "year": fm.get("year"),
            "source": fm.get("source", ""),
            "local": fm.get("local", ""),
            "external_ids": extract_external_ids(fm.get("source", "")),
            "axes": {
                axis: list(_as_list(fm.get(axis), axis, origin, problems))
                for axis in AXES
            },
            "gaps": _gap_entries(
                _as_list(fm.get("gaps"), "gaps", origin, problems), origin, problems
            ),
            "path": "papers/" + path.name,
        }
        identity["works"][slug] = work
        for claim in claims:
            identity["claims"]["%s#C%d" % (slug, claim["n"])] = {
                "work": slug,
                "n": claim["n"],
                "quote": claim["quote"],
                "anchor": claim["anchor"],
                "concepts": claim["concepts"],
            }

    for path in _card_files(vault / "gaps"):
        origin = "gaps/" + path.name
        fm_lines, _, errs = split_frontmatter(path.read_text(encoding="utf-8"), origin)
        problems.extend(errs)
        fm, fm_problems = parse_frontmatter(fm_lines, origin)
        problems.extend(fm_problems)
        identity["gaps"][path.stem] = {
            "status": fm.get("status", ""),
            "type": fm.get("type", ""),
            "concepts": _as_list(fm.get("concepts"), "concepts", origin, problems),
            "related": _as_list(fm.get("related"), "related", origin, problems),
            "path": "gaps/" + path.name,
        }

    for path in _card_files(vault / "transfers"):
        origin = "transfers/" + path.name
        fm_lines, _, errs = split_frontmatter(path.read_text(encoding="utf-8"), origin)
        problems.extend(errs)
        fm, fm_problems = parse_frontmatter(fm_lines, origin)
        problems.extend(fm_problems)
        identity["transfers"][path.stem] = {
            "a": fm.get("a", ""),
            "c": fm.get("c", ""),
            "bridges": _as_list(fm.get("bridges"), "bridges", origin, problems),
            "gaps": _as_list(fm.get("gaps"), "gaps", origin, problems),
            "papers": _as_list(fm.get("papers"), "papers", origin, problems),
            "status": fm.get("status", ""),
            "path": "transfers/" + path.name,
        }

    for path in _card_files(vault / "briefs"):
        identity["briefs"][path.stem] = {"path": "briefs/" + path.name}

    _collect_confirmations(identity)
    return identity


def _collect_confirmations(identity):
    """Exact external-id collisions and fuzzy title pairs → user confirmations."""
    by_external = {}
    for slug, work in identity["works"].items():
        for kind, value in work["external_ids"].items():
            by_external.setdefault((kind, value), []).append(slug)
    for (kind, value), slugs in sorted(by_external.items()):
        if len(slugs) > 1:
            identity["confirmations"].append(
                {
                    "kind": "duplicate-external-id",
                    "detail": "%s %s shared by %s" % (kind, value, sorted(slugs)),
                    "slugs": sorted(slugs),
                }
            )
    titles = sorted(
        (slug, re.sub(r"\W+", " ", str(work["title"])).lower().strip())
        for slug, work in identity["works"].items()
    )
    # Precomputed difflib upper bounds prune the O(N²) pass BEFORE any
    # SequenceMatcher is built — at the 5k-work ceiling the unpruned pass
    # is 12.5M full ratio() calls (~15 min per Vault load).
    # The formulas are the documented definitions of real_quick_ratio
    # (2·min(len)/total) and quick_ratio (2·multiset-matches/total), both
    # proven upper bounds on ratio(), so the accept set is unchanged.
    prepped = [
        (slug, title, len(title), Counter(title)) for slug, title in titles
    ]
    for i, (slug_a, title_a, len_a, count_a) in enumerate(prepped):
        for slug_b, title_b, len_b, count_b in prepped[i + 1 :]:
            if not title_a or not title_b:
                continue
            total = len_a + len_b
            if 2.0 * min(len_a, len_b) / total < TITLE_SIMILARITY:
                continue
            if 2.0 * sum((count_a & count_b).values()) / total < TITLE_SIMILARITY:
                continue
            ratio = difflib.SequenceMatcher(None, title_a, title_b).ratio()
            if ratio >= TITLE_SIMILARITY:
                identity["confirmations"].append(
                    {
                        "kind": "fuzzy-title",
                        "detail": "titles %.2f similar: %s vs %s" % (ratio, slug_a, slug_b),
                        "slugs": [slug_a, slug_b],
                    }
                )
