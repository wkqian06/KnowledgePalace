"""MaterialRequest / MaterialReceipt — the three-axis acquisition contract.

A receipt records what happened on three independent axes:
``acquisition_status`` (did we obtain bytes), ``identity_status`` (are the
bytes the requested Work), ``text_status`` (is machine-readable text ready).
Claim eligibility requires acquisition ``acquired`` AND identity ``verified``
AND text ``ready`` — no axis can compensate for another.

Identity becomes ``verified`` ONLY mechanically: an expected-sha256 match, a
requested DOI found in the text head, or an explicit user confirmation flag
whose provenance is recorded. Everything else stays ``unverified``; a hash
contradiction is ``mismatch`` and quarantines the staged file.
"""

import hashlib

ACQUISITION_STATUSES = ("acquired", "not_found", "auth_required", "manual_action", "failed")
IDENTITY_STATUSES = ("verified", "mismatch", "unverified")
TEXT_STATUSES = ("ready", "needs_ocr", "extraction_failed", "not_attempted")
_TEXT_HEAD_CHARS = 4000


def new_request(
    work_slug=None,
    ids=None,
    title=None,
    local_path=None,
    expected_sha256=None,
    user_confirmed_identity=False,
    confirmation_provenance=None,
):
    return {
        "work_slug": work_slug,
        "ids": dict(ids or {}),
        "title": title,
        "local_path": str(local_path) if local_path else None,
        "expected_sha256": expected_sha256,
        "user_confirmed_identity": bool(user_confirmed_identity),
        "confirmation_provenance": confirmation_provenance,
    }


def new_receipt(request, channel, locator=None):
    """A fresh receipt in its most pessimistic state; providers upgrade axes."""
    return {
        "request": dict(request),
        "channel": channel,
        "locator": locator,
        "acquisition_status": "not_found",
        "identity_status": "unverified",
        "identity_evidence": None,
        "text_status": "not_attempted",
        "sha256": None,
        "staged_path": None,
        "staged_text_path": None,
        "quarantined": False,
        "attempts": [],
        "next_action": None,
        "fetched_at": None,
    }


def add_attempt(receipt, channel, outcome):
    """Compact attempts summary — one short line per try, never raw dumps."""
    receipt["attempts"].append({"channel": channel, "outcome": str(outcome)[:200]})


def resolve_identity(request, staged_bytes=None, text_head=None):
    """Mechanical identity verdict → (status, evidence)."""
    expected = request.get("expected_sha256")
    if expected and staged_bytes is not None:
        actual = hashlib.sha256(staged_bytes).hexdigest()
        if actual == expected.lower():
            return "verified", "sha256 matches expected"
        return "mismatch", "sha256 %s… != expected %s…" % (actual[:12], expected[:12])
    doi = (request.get("ids") or {}).get("doi")
    if doi and text_head and doi.lower() in text_head[:_TEXT_HEAD_CHARS].lower():
        return "verified", "requested DOI found in text head"
    if request.get("user_confirmed_identity"):
        return "verified", "user confirmation (%s)" % (
            request.get("confirmation_provenance") or "packaged confirmation"
        )
    return "unverified", None


def claim_eligible(receipt):
    """No Claim from unverified or text-less material — ever."""
    return (
        receipt.get("acquisition_status") == "acquired"
        and receipt.get("identity_status") == "verified"
        and receipt.get("text_status") == "ready"
        and not receipt.get("quarantined")
    )


def validate_receipt(receipt):
    """Return a list of contract violations; empty means conforming."""
    errors = []
    if not isinstance(receipt, dict):
        return ["receipt must be a dict"]
    for key in (
        "request",
        "channel",
        "acquisition_status",
        "identity_status",
        "text_status",
        "attempts",
    ):
        if key not in receipt:
            errors.append("missing key %r" % key)
    if errors:
        return errors
    for axis, allowed in (
        ("acquisition_status", ACQUISITION_STATUSES),
        ("identity_status", IDENTITY_STATUSES),
        ("text_status", TEXT_STATUSES),
    ):
        if receipt[axis] not in allowed:
            errors.append("%s %r not in %s" % (axis, receipt[axis], list(allowed)))
    for key in ("staged_path", "staged_text_path"):
        value = receipt.get(key)
        if value and (value.startswith("/") or ".." in value.split("/")):
            errors.append("%s must be a state-relative path, got %r" % (key, value))
    if receipt["acquisition_status"] == "acquired" and not receipt.get("sha256"):
        errors.append("acquired material must carry its sha256")
    if receipt["identity_status"] == "mismatch" and not receipt.get("quarantined"):
        errors.append("identity mismatch must quarantine the staged file")
    return errors
