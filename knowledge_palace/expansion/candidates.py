"""Global Candidate identity, Discovery Occurrences, Scope-bound decisions.

Identity precedence: doi > openalex > arxiv > normalized-title hash. A
Candidate is identity-verified (and budget-eligible) only when it carries at
least one external id. Occurrences record every discovery path; decisions
live under their Scope key only — no global blacklist can exist by
construction.
"""

import hashlib
import re

DECISIONS = ("selected", "deferred", "rejected")
_ID_PRECEDENCE = ("doi", "openalex", "arxiv")


def candidate_key(record):
    """Stable global key for a normalized record; None when unidentifiable."""
    ids = record.get("ids") or {}
    for kind in _ID_PRECEDENCE:
        value = ids.get(kind)
        if value:
            return "%s:%s" % (kind, str(value).lower())
    title = re.sub(r"\W+", " ", str(record.get("title") or "")).lower().strip()
    if not title:
        return None
    return "title:" + hashlib.sha256(title.encode("utf-8")).hexdigest()[:16]


def build_hit_index(vault_identity):
    """(kind, value) → work slug, from graph identity output."""
    index = {}
    for slug, work in vault_identity["works"].items():
        for kind, value in (work.get("external_ids") or {}).items():
            index[(kind, str(value).lower())] = slug
    return index


def vault_hit(record, hit_index):
    """Existing Vault work slug for this record, or None."""
    ids = record.get("ids") or {}
    for kind in _ID_PRECEDENCE:
        value = ids.get(kind)
        if value and (kind, str(value).lower()) in hit_index:
            return hit_index[(kind, str(value).lower())]
    return None


class CandidatePool:
    """Globally deduplicated candidates, persistable as canonical JSON."""

    def __init__(self, entries=None):
        self._entries = entries or {}

    def upsert(self, record, run_id, via, direction, depth):
        """Merge a discovery into the pool → (key, is_new). Idempotent for
        identical occurrences, so checkpoint resume never duplicates."""
        key = candidate_key(record)
        if key is None:
            return None, False
        ids = {k: v for k, v in (record.get("ids") or {}).items() if v}
        entry = self._entries.get(key)
        is_new = entry is None
        if is_new:
            entry = {
                "key": key,
                "ids": ids,
                "title": record.get("title"),
                "year": record.get("year"),
                "verified": bool(ids),
                "occurrences": [],
                "decisions": {},
            }
            self._entries[key] = entry
        else:
            for kind, value in ids.items():
                entry["ids"].setdefault(kind, value)
            entry["verified"] = entry["verified"] or bool(ids)
            if not entry.get("title") and record.get("title"):
                entry["title"] = record["title"]
        occurrence = {"run": run_id, "via": via, "direction": direction, "depth": depth}
        if occurrence not in entry["occurrences"]:
            entry["occurrences"].append(occurrence)
        return key, is_new

    def decide(self, key, scope, decision, reason, exploratory=False, decided_via="auto"):
        if decision not in DECISIONS:
            raise ValueError("decision %r not in %s" % (decision, list(DECISIONS)))
        if key not in self._entries:
            raise ValueError("unknown candidate %r" % key)
        self._entries[key]["decisions"][scope] = {
            "decision": decision,
            "reason": reason,
            "exploratory": bool(exploratory),
            "decided_via": decided_via,
        }

    def decision_for(self, key, scope):
        entry = self._entries.get(key)
        return (entry or {}).get("decisions", {}).get(scope)

    def get(self, key):
        return self._entries.get(key)

    def keys(self):
        return sorted(self._entries)

    def to_payload(self):
        return {key: self._entries[key] for key in sorted(self._entries)}

    @classmethod
    def from_payload(cls, payload):
        return cls(dict(payload or {}))
