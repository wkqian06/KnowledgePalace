"""Source Snapshot promotion — the one write path into the Source Cache.

Runs only inside the orchestrator's packaged confirmation (and, for the
REAL Source Cache, only after the source-write gate). Promotion is
immutable by construction: an existing snapshot with a different hash is a
typed refusal, an identical one is an idempotent no-op, and rejection means
doing nothing at all — the Source Cache and Vault stay byte-identical.
"""

import hashlib
import os
import tempfile
from pathlib import Path

from .providers import AcquisitionError
from .receipt import validate_receipt

FULLTEXT_DIRNAME = "fulltext"


def _copy_immutable(staged_file, destination):
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
        digest, outcome = _copy_immutable(staged_file, destination)
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
