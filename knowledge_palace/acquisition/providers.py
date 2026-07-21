"""Acquisition providers — read-only channels over injected transports.

Channel order: local file → Zotero → Open Access →
licensed API (not implemented in V1) → institutional (disabled experimental
stub). Every provider returns the SAME receipt schema. Transports are
injected exactly like the metadata providers; live transports exist
only behind explicit network-acquisition authorization. No provider ever writes outside
``<state_dir>/acquisition/``.
"""

import hashlib
import os
import tempfile
from pathlib import Path

from ..metadata.providers import OpenAlexProvider, ProviderError
from .receipt import add_attempt, new_receipt, resolve_identity

STAGING_DIRNAME = "acquisition"
CHANNEL_ORDER = ("local", "zotero", "openaccess", "licensed", "institutional")


class AcquisitionError(RuntimeError):
    """Typed acquisition failure: which channel, which operation, why."""

    def __init__(self, channel, operation, detail):
        super().__init__("%s.%s: %s" % (channel, operation, detail))
        self.channel = channel
        self.operation = operation
        self.detail = detail


def _staging_dir(state_dir):
    return Path(state_dir) / STAGING_DIRNAME / "staging"


def stage_bytes(state_dir, name, data):
    """Atomically stage bytes; returns (state-relative posix path, sha256).

    temp-write + rename: a failed transfer never leaves a partial staged file.
    """
    target = _staging_dir(state_dir) / name
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()
    handle, temp_name = tempfile.mkstemp(dir=str(target.parent), suffix=".part")
    try:
        with os.fdopen(handle, "wb") as fh:
            fh.write(data)
        os.replace(temp_name, str(target))
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise
    relative = target.relative_to(Path(state_dir)).as_posix()
    return relative, digest


def quarantine(state_dir, staged_relpath):
    """Rename a staged file out of the promotable namespace."""
    source = Path(state_dir) / staged_relpath
    target = source.with_name(source.name + ".quarantine")
    os.replace(str(source), str(target))
    return target.relative_to(Path(state_dir)).as_posix()


def _finish_identity(receipt, request, state_dir, staged_bytes, text_head):
    status, evidence = resolve_identity(request, staged_bytes, text_head)
    receipt["identity_status"] = status
    receipt["identity_evidence"] = evidence
    if status == "mismatch":
        text_path = receipt.get("staged_text_path")
        text_is_alias = text_path == receipt["staged_path"]
        receipt["staged_path"] = quarantine(state_dir, receipt["staged_path"])
        if text_path:
            receipt["staged_text_path"] = (
                receipt["staged_path"]
                if text_is_alias
                else quarantine(state_dir, text_path)
            )
        receipt["quarantined"] = True
        receipt["next_action"] = "identity mismatch: resolve or discard the quarantined file"
    elif status == "unverified":
        receipt["next_action"] = "verify identity at the packaged confirmation"


class LocalFileProvider:
    """User-supplied path → staged copy; a sibling .txt companion carries text."""

    channel = "local"

    def acquire(self, request, state_dir):
        receipt = new_receipt(request, self.channel, locator=request.get("local_path"))
        path_value = request.get("local_path")
        if not path_value:
            add_attempt(receipt, self.channel, "no local_path in request")
            return receipt
        source = Path(path_value)
        if not source.is_file():
            add_attempt(receipt, self.channel, "file not found: %s" % source)
            receipt["next_action"] = "provide a valid local file path"
            return receipt
        data = source.read_bytes()
        slug = request.get("work_slug") or source.stem
        staged, digest = stage_bytes(state_dir, slug + source.suffix.lower(), data)
        receipt["staged_path"] = staged
        receipt["sha256"] = digest
        receipt["acquisition_status"] = "acquired"
        add_attempt(receipt, self.channel, "staged %d bytes" % len(data))

        text_head = None
        if source.suffix.lower() == ".txt":
            receipt["staged_text_path"] = staged
            receipt["text_status"] = "ready"
            text_head = data[:8000].decode("utf-8", errors="replace")
        else:
            companion = source.with_suffix(".txt")
            if companion.is_file():
                text_data = companion.read_bytes()
                text_staged, _ = stage_bytes(state_dir, slug + ".txt", text_data)
                receipt["staged_text_path"] = text_staged
                receipt["text_status"] = "ready"
                text_head = text_data[:8000].decode("utf-8", errors="replace")
                add_attempt(receipt, self.channel, "staged .txt companion")
        _finish_identity(receipt, request, state_dir, data, text_head)
        return receipt


class OpenAccessProvider:
    """OA location via the OpenAlex metadata adapter (cache-first), then download."""

    channel = "openaccess"

    def __init__(self, fetch=None, cache=None, limiter=None, mailto=None):
        self._openalex = OpenAlexProvider(
            fetch=fetch, cache=cache, limiter=limiter, mailto=mailto
        )
        self._fetch = fetch
        self._limiter = limiter

    def acquire(self, request, state_dir):
        receipt = new_receipt(request, self.channel)
        ids = request.get("ids") or {}
        if not ids:
            add_attempt(receipt, self.channel, "no external id to resolve")
            return receipt
        try:
            record = self._openalex.resolve(ids)
        except ProviderError as err:
            receipt["acquisition_status"] = "failed"
            add_attempt(receipt, self.channel, "metadata: %s" % err.detail)
            receipt["next_action"] = "retry with --live after network-acquisition authorization"
            return receipt
        oa_url = record.get("oa_url")
        if not oa_url:
            add_attempt(receipt, self.channel, "no open-access location")
            receipt["next_action"] = "try Zotero or a local file"
            return receipt
        receipt["locator"] = oa_url
        if self._fetch is None:
            receipt["acquisition_status"] = "failed"
            add_attempt(receipt, self.channel, "download needs --live (gated)")
            receipt["next_action"] = "retry with --live after network-acquisition authorization"
            return receipt
        if self._limiter is not None:
            self._limiter.wait(self.channel)
        try:
            data = self._fetch(oa_url, {"User-Agent": "knowledge-palace/0.4"})
        except Exception as err:  # transport boundary: typed, never half-staged
            receipt["acquisition_status"] = "failed"
            add_attempt(receipt, self.channel, "download failed: %s" % err)
            return receipt
        slug = request.get("work_slug") or "download"
        suffix = ".pdf" if data[:5] == b"%PDF-" else ".bin"
        staged, digest = stage_bytes(state_dir, slug + suffix, data)
        receipt["staged_path"] = staged
        receipt["sha256"] = digest
        receipt["acquisition_status"] = "acquired"
        add_attempt(receipt, self.channel, "downloaded %d bytes" % len(data))
        # ponytail: no PDF text extraction in V1 (reader-capability boundary);
        # bare downloads stay text_status=not_attempted until a .txt exists.
        _finish_identity(receipt, request, state_dir, data, None)
        return receipt


class ZoteroReadOnlyProvider:
    """Zotero as a read-only PDF/metadata entry. Local API first, Web API
    fallback; stable keys only; never notes, annotations, or the live SQLite."""

    channel = "zotero"
    LOCAL_BASE = "http://localhost:23119/api/users/0"
    WEB_BASE = "https://api.zotero.org/users"

    def __init__(self, fetch=None, api_key=None, user_id=None):
        self._fetch = fetch
        self._api_key = api_key
        self._user_id = user_id

    def _bases(self):
        bases = [self.LOCAL_BASE]
        if self._user_id:
            bases.append("%s/%s" % (self.WEB_BASE, self._user_id))
        return bases

    def _headers(self):
        headers = {"User-Agent": "knowledge-palace/0.4"}
        if self._api_key:
            headers["Zotero-API-Key"] = self._api_key
        return headers

    def acquire(self, request, state_dir):
        import json as _json

        receipt = new_receipt(request, self.channel)
        doi = (request.get("ids") or {}).get("doi")
        if not doi:
            add_attempt(receipt, self.channel, "zotero lookup needs a DOI")
            return receipt
        if self._fetch is None:
            receipt["acquisition_status"] = "failed"
            add_attempt(receipt, self.channel, "zotero access needs --live (gated)")
            receipt["next_action"] = "retry with --live after network-acquisition authorization"
            return receipt
        for base in self._bases():
            search_url = "%s/items?q=%s&itemType=-attachment" % (base, doi)
            try:
                items = _json.loads(self._fetch(search_url, self._headers()))
            except Exception as err:
                add_attempt(receipt, self.channel, "%s: %s" % (base.split("/")[2], err))
                continue
            if not items:
                add_attempt(receipt, self.channel, "no item for DOI at %s" % base.split("/")[2])
                continue
            item_key = items[0]["key"]
            receipt["locator"] = "zotero:%s" % item_key
            children_url = "%s/items/%s/children" % (base, item_key)
            try:
                children = _json.loads(self._fetch(children_url, self._headers()))
            except Exception as err:
                add_attempt(receipt, self.channel, "children: %s" % err)
                continue
            attachment = next(
                (
                    child
                    for child in children
                    if (child.get("data") or {}).get("contentType") == "application/pdf"
                ),
                None,
            )
            if attachment is None:
                add_attempt(receipt, self.channel, "item %s has no PDF attachment" % item_key)
                receipt["next_action"] = "try open access or a local file"
                return receipt
            file_url = "%s/items/%s/file" % (base, attachment["key"])
            try:
                data = self._fetch(file_url, self._headers())
            except Exception as err:
                receipt["acquisition_status"] = "failed"
                add_attempt(receipt, self.channel, "attachment download failed: %s" % err)
                return receipt
            slug = request.get("work_slug") or item_key
            staged, digest = stage_bytes(state_dir, slug + ".pdf", data)
            receipt["staged_path"] = staged
            receipt["sha256"] = digest
            receipt["acquisition_status"] = "acquired"
            add_attempt(
                receipt, self.channel, "attachment %s: %d bytes" % (attachment["key"], len(data))
            )
            _finish_identity(receipt, request, state_dir, data, None)
            return receipt
        receipt["next_action"] = "no Zotero copy found; try open access or a local file"
        return receipt


class InstitutionalAccessProvider:
    """Disabled experimental stub — V1 never attempts institutional access."""

    channel = "institutional"
    maturity = "experimental (disabled)"

    def acquire(self, request, state_dir):
        raise AcquisitionError(
            self.channel,
            "acquire",
            "experimental provider is disabled in V1 (headless HPC promises no "
            "browser/SSO/2FA); use local, Zotero, or open access",
        )


def acquire_via(providers, request, state_dir):
    """Try providers in order; first acquired receipt wins, attempts carry
    over. A provider that refuses outright (e.g. the disabled institutional
    stub) becomes a recorded attempt, never a crash."""
    carried = []
    last = None
    for provider in providers:
        try:
            receipt = provider.acquire(request, state_dir)
        except AcquisitionError as err:
            carried.append({"channel": err.channel, "outcome": err.detail[:200]})
            continue
        receipt["attempts"] = carried + receipt["attempts"]
        if receipt["acquisition_status"] == "acquired":
            return receipt
        carried = receipt["attempts"]
        last = receipt
    if last is None:
        last = new_receipt(request, "none")
        last["acquisition_status"] = "failed"
        last["attempts"] = carried
        last["next_action"] = "every channel refused; supply a local file"
    return last
