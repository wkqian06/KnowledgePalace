"""Source Snapshot promotion — the one write path into the Source Cache.

Runs only inside the orchestrator's packaged confirmation (and, for the
REAL Source Cache, only after the source-write gate). Promotion is
immutable by construction: an existing snapshot with a different hash is a
typed refusal, an identical one is an idempotent no-op, and rejection means
doing nothing at all — the Source Cache and Vault stay byte-identical.
"""

import hashlib
import os
import re
import tempfile
import unicodedata
from pathlib import Path

from .providers import AcquisitionError
from .receipt import validate_receipt
from ..graph.identity import (load_vault_identity, split_frontmatter,
                              parse_frontmatter, parse_claims, extract_external_ids)
from ..semantic.binding import validate_claims
from ..semantic.evidence_helpers import read_tables

FULLTEXT_DIRNAME = "fulltext"


def quote_is_in_source(quote, local, source_dir):
    """Is this exact wording present in the work's own cached text?

    A transcription repair rewrites a quote in place, so the boundary has to
    see for itself that the new wording is the paper's. Case, punctuation and
    every separator are erased on both sides first: these caches wrap lines
    mid-word, drop ligatures and lose hyphens, none of which is evidence.
    Without a cached text there is nothing to check against, so the repair is
    refused rather than assumed. An OCR-derived cache is refused too: its
    characters are a guess at the page, so "matching the source" there would
    license repairing a quote into the scanner's own mistakes.
    """
    if not source_dir or not local:
        return False
    text_file = (Path(source_dir) / local.strip()).with_suffix(".txt")
    if not text_file.exists():
        return False
    header = text_file.read_text(encoding="utf-8", errors="replace")[:400]
    if re.search(r"^TOOL:.*OCR", header, re.MULTILINE | re.IGNORECASE):
        return False
    def fold(text):
        return re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", text).lower())

    return fold(quote.strip().strip('"')) in fold(
        text_file.read_text(encoding="utf-8", errors="replace"))


def copy_immutable(staged_file, destination):
    """temp+rename copy that never overwrites a differing existing snapshot."""
    data = staged_file.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if destination.exists():
        existing = hashlib.sha256(destination.read_bytes()).hexdigest()
        if existing == digest:
            return digest, "already-present"
        raise AcquisitionError(
            "transaction",
            "promote",
            "refusing to overwrite %s: existing sha %s… != staged %s… "
            "(snapshots are immutable; corrections append, never replace)"
            % (destination.name, existing[:12], digest[:12]),
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(destination.parent), suffix=".part")
    try:
        with os.fdopen(handle, "wb") as fh:
            fh.write(data)
        os.replace(temp_name, str(destination))
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise
    return digest, "promoted"


def promote(receipt, state_dir, source_dir):
    """Promote a confirmed receipt's staged file(s) into the Source Cache.

    Returns {"status", "files": [{"local", "sha256", "outcome"}]} where
    ``local`` is the source_dir-relative pointer for the paper card.
    """
    violations = validate_receipt(receipt)
    if violations:
        raise AcquisitionError("transaction", "promote", "invalid receipt: %s" % violations)
    if receipt["acquisition_status"] != "acquired":
        raise AcquisitionError(
            "transaction", "promote", "nothing acquired (%s)" % receipt["acquisition_status"]
        )
    if receipt["identity_status"] != "verified":
        raise AcquisitionError(
            "transaction",
            "promote",
            "identity is %r — only verified material may become a Source Snapshot"
            % receipt["identity_status"],
        )
    if receipt.get("quarantined"):
        raise AcquisitionError("transaction", "promote", "receipt is quarantined")

    state = Path(state_dir)
    source = Path(source_dir)
    slug = receipt["request"].get("work_slug")
    if not slug:
        raise AcquisitionError("transaction", "promote", "request carries no work_slug")

    files = []
    seen = set()
    for key in ("staged_path", "staged_text_path"):
        relative = receipt.get(key)
        if not relative or relative in seen:
            continue
        seen.add(relative)
        staged_file = state / relative
        if not staged_file.is_file():
            raise AcquisitionError(
                "transaction", "promote", "staged file missing: %s" % relative
            )
        destination = source / FULLTEXT_DIRNAME / (slug + Path(relative).suffix)
        digest, outcome = copy_immutable(staged_file, destination)
        files.append(
            {
                "local": "%s/%s" % (FULLTEXT_DIRNAME, destination.name),
                "sha256": digest,
                "outcome": outcome,
            }
        )
    if not files:
        raise AcquisitionError("transaction", "promote", "receipt has no staged files")
    status = (
        "already-present"
        if all(entry["outcome"] == "already-present" for entry in files)
        else "promoted"
    )
    return {"status": status, "files": files}


def write_text(destination, text):
    """Replace a text artifact only after its complete content is written."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(destination.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_paper(vault_dir, card_text, source_dir=None):
    """Save a reviewed paper and its INDEX row, retaining identity and old Claims.

    Scientific reading is the caller's responsibility. This write boundary checks
    the identity, references and original evidence that storage must preserve.
    Rebuild the graph once after the batch and any associated Gap edits.

    With `source_dir`, an existing Claim's quote may be repaired in place when
    the new wording is verbatim in that work's cached text — a transcription
    slip is corrected toward the source, not away from it. Without it, every
    old quote must be returned unchanged.
    """
    vault = Path(vault_dir)
    lines, body, errors = split_frontmatter(card_text, "paper draft")
    fields, problems = parse_frontmatter(lines, "paper draft")
    errors.extend(problems)
    slug = fields.get("slug", "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("paper slug must be an ASCII kebab-case filename")
    if not fields.get("source") or not fields.get("title"):
        errors.append("paper identity needs a source locator and title")
    claims, problems = parse_claims(body, slug)
    errors.extend(problems)
    tables, problems = read_tables(body, slug)
    errors.extend(problems)
    identity = load_vault_identity(vault)
    ids = extract_external_ids(fields.get("source", ""))
    for other, work in identity["works"].items():
        shared = any(work["external_ids"].get(key) == value for key, value in ids.items())
        same_title = str(work["title"]).casefold().strip() == str(fields.get("title", "")).casefold().strip()
        if other != slug and (shared or same_title):
            errors.append("paper already exists as %s; reuse that card" % other)
    prior = identity["works"].get(slug)
    if prior and any(ids.get(key) != value for key, value in prior["external_ids"].items()):
        errors.append("existing paper identity changed; resolve its version before saving")
    old = {value["n"]: value for value in identity["claims"].values() if value["work"] == slug}
    current = {claim["n"]: claim for claim in claims}
    for number, claim in old.items():
        # The quote is the evidence and never changes. The anchor is only a
        # locator into the source: a provenance check that finds the quote
        # elsewhere in this work may correct it. A quote that is not in this
        # work at all is retracted in place, never deleted or overwritten.
        if number not in current:
            errors.append("C%d is missing; retract a claim in place, never delete it" % number)
        elif (current[number]["quote"] != claim["quote"]
              and not quote_is_in_source(current[number]["quote"], fields.get("local"), source_dir)):
            errors.append(
                "C%d's new quote is not verbatim in this work's cached text; a repair must "
                "match the source, a misreading appends a correction, and a quote that is "
                "not this work's is retracted" % number)
    retracted = {number for number, claim in current.items() if claim["retracted"]}
    for section, key in (
            ("Argument", "claim"), ("Conditions", "evidence"), ("Evidence relations", "claim")):
        for row in tables[section]:
            number = row[key].strip().removeprefix("C")
            if number.isdigit() and int(number) in retracted:
                errors.append("%s row cites retracted C%s; repoint it or drop the row"
                              % (section, number))
    new_claims = [claim for claim in claims if claim["n"] not in old]
    binding = validate_claims(new_claims, identity["registry"])
    if not binding["ok"]:
        errors.append("new Claim concepts do not resolve: %s" % binding)
    depth = fields.get("read_depth", "")
    coverage = fields.get("source_coverage", "not-recorded")
    if coverage not in ("full-text", "excerpt", "abstract", "metadata", "not-recorded"):
        errors.append("source_coverage must be full-text, excerpt, abstract or metadata")
    if depth not in ("full", "skim", "abstract", "metadata"):
        errors.append("read_depth must describe the material actually read")
    if (coverage == "metadata" or depth == "metadata") and claims:
        errors.append("metadata-only material cannot supply scientific Claims")
    if coverage in ("abstract", "metadata") and depth in ("full", "skim"):
        errors.append("limited source coverage cannot be labeled full/skim reading")
    for row in tables["Evidence relations"]:
        target = row["target"]
        if target.startswith("gap:"):
            found = target[4:] in identity["gaps"]
        else:
            found = target.removeprefix("claim:") in identity["claims"] or target in {
                "claim:%s#C%d" % (slug, number) for number in current}
        if not found:
            errors.append("unresolved evidence target: %s" % target)
    if errors:
        raise ValueError("paper not saved: " + "; ".join(errors))
    destination = vault / "papers" / (slug + ".md")
    unchanged = destination.is_file() and destination.read_text(encoding="utf-8") == card_text
    if not unchanged:
        write_text(destination, card_text)
    index = vault / "papers" / "INDEX.md"
    index_text = index.read_text(encoding="utf-8") if index.is_file() else (
        "# Papers INDEX\n\n| Slug | Title | Year | Venue | IF | Cites | W | Depth | Added |\n"
        "|---|---|---|---|---|---|---|---|---|\n")
    keys = ("slug", "title", "year", "venue", "journal_if", "citations", "weight", "read_depth", "added")
    cells = [str(fields.get(key, "unknown")).replace("|", "/") for key in keys]
    row = "| " + " | ".join(cells) + " |"
    index_lines = index_text.splitlines()
    positions = [i for i, line in enumerate(index_lines) if re.match(r"^\|\s*" + re.escape(slug) + r"\s*\|", line)]
    if positions:
        index_lines[positions[0]] = row
        index_lines = [line for i, line in enumerate(index_lines) if i not in positions[1:]]
    else:
        index_lines.append(row)
    updated_index = "\n".join(index_lines) + "\n"
    if updated_index != index_text:
        write_text(index, updated_index)
    return {"work": "work:" + slug, "path": str(destination),
            "status": "unchanged" if unchanged else "updated" if prior else "created",
            "read_depth": depth, "source_coverage": coverage, "new_claims": len(new_claims)}
