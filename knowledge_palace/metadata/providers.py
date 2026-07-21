"""Literature metadata providers — normalized records over injected transport.

``LiteratureProvider`` exposes resolve / search / references / cited_by and
returns normalized record dicts. The transport is a plain
``fetch(url, headers) -> bytes`` callable: tests inject stubs; the live
urllib transport below is built ONLY by ``refresh --live`` under
explicit network authorization. A provider failure raises a typed ``ProviderError`` and
never writes a partial record or poisons the cache.
"""

import json
import re
import xml.etree.ElementTree as ElementTree

PROVIDERS = ("openalex", "crossref", "semanticscholar", "arxiv")
USER_AGENT = "knowledge-palace/0.4"

_DOI_PREFIX = re.compile(r"^https?://(dx\.)?doi\.org/", re.IGNORECASE)


class ProviderError(RuntimeError):
    """Typed provider failure: which provider, which operation, why."""

    def __init__(self, provider, operation, detail):
        super().__init__("%s.%s: %s" % (provider, operation, detail))
        self.provider = provider
        self.operation = operation
        self.detail = detail


def live_transport():
    """urllib-based fetch. Constructed only for --live runs (network gate)."""
    import urllib.request

    def fetch(url, headers=None):
        request = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()

    return fetch


def _clean_doi(value):
    return _DOI_PREFIX.sub("", value).strip().lower() if value else None


class LiteratureProvider:
    name = "base"

    def __init__(self, fetch=None, cache=None, limiter=None, mailto=None, api_key=None):
        self._fetch = fetch
        self._cache = cache
        self._limiter = limiter
        self._mailto = mailto
        self._api_key = api_key

    # -- plumbing -----------------------------------------------------------

    def _headers(self):
        agent = USER_AGENT + (" (mailto:%s)" % self._mailto if self._mailto else "")
        headers = {"User-Agent": agent}
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    def _decode(self, raw):
        return json.loads(raw.decode("utf-8"))

    def _get(self, operation, url):
        """Cache-first payload fetch. Returns (payload, fetched_at)."""
        if self._cache is not None:
            hit = self._cache.get(self.name, url)
            if hit is not None:
                return hit["payload"], hit["fetched_at"]
        if self._fetch is None:
            raise ProviderError(
                self.name, operation, "cache miss on a cache-only run: %s" % url
            )
        if self._limiter is not None:
            self._limiter.wait(self.name)
        try:
            raw = self._fetch(url, self._headers())
        except Exception as err:  # transport boundary: surface, never swallow
            raise ProviderError(self.name, operation, "transport failure: %s" % err)
        try:
            payload = self._decode(raw)
        except ValueError as err:
            raise ProviderError(self.name, operation, "unparseable response: %s" % err)
        fetched_at = None
        if self._cache is not None:
            fetched_at = self._cache.put(self.name, url, payload)
        return payload, fetched_at

    def _lite(self, ids, title=None):
        entry = {"ids": {k: v for k, v in ids.items() if v}}
        if title:
            entry["title"] = title
        return entry

    # -- surface (adapters implement resolve/search/references/cited_by) ----


class OpenAlexProvider(LiteratureProvider):
    name = "openalex"
    BASE = "https://api.openalex.org"

    def _work_url(self, ref):
        if ref.get("doi"):
            return "%s/works/doi:%s" % (self.BASE, _clean_doi(ref["doi"]))
        if ref.get("openalex"):
            return "%s/works/%s" % (self.BASE, ref["openalex"].rsplit("/", 1)[-1])
        if ref.get("arxiv"):
            return "%s/works/doi:10.48550/arxiv.%s" % (self.BASE, ref["arxiv"])
        raise ProviderError(self.name, "resolve", "need doi/openalex/arxiv in %r" % ref)

    def _map(self, work, fetched_at):
        location = (work.get("primary_location") or {}).get("source") or {}
        percentile = (work.get("citation_normalized_percentile") or {}).get("value")
        if percentile is not None and percentile <= 1:
            percentile *= 100  # OpenAlex serves 0–1; snapshots store 0–100
        oa_location = work.get("best_oa_location") or {}
        return {
            "oa_url": oa_location.get("pdf_url") or oa_location.get("landing_page_url"),
            "provider": self.name,
            "ids": {
                "openalex": (work.get("id") or "").rsplit("/", 1)[-1] or None,
                "doi": _clean_doi(work.get("doi")),
            },
            "title": work.get("display_name"),
            "year": work.get("publication_year"),
            "venue": location.get("display_name"),
            "citations": work.get("cited_by_count"),
            "citation_percentile": percentile,
            "categories": [
                topic.get("display_name")
                for topic in work.get("topics") or []
                if topic.get("display_name")
            ],
            "is_preprint": location.get("type") == "repository" or None,
            "fetched_at": fetched_at,
        }

    def resolve(self, ref):
        payload, fetched_at = self._get("resolve", self._work_url(ref))
        return self._map(payload, fetched_at)

    def search(self, query, limit=10):
        url = "%s/works?search=%s&per-page=%d" % (
            self.BASE,
            query.replace(" ", "+"),
            max(1, min(int(limit), 50)),
        )
        payload, fetched_at = self._get("search", url)
        return [self._map(work, fetched_at) for work in payload.get("results") or []]

    def references(self, ref):
        payload, _ = self._get("references", self._work_url(ref))
        items = [
            self._lite({"openalex": work_id.rsplit("/", 1)[-1]})
            for work_id in payload.get("referenced_works") or []
        ]
        return {"count": len(items), "items": items}

    def cited_by(self, ref, limit=10):
        payload, _ = self._get("cited_by", self._work_url(ref))
        work_id = (payload.get("id") or "").rsplit("/", 1)[-1]
        url = "%s/works?filter=cites:%s&per-page=%d" % (
            self.BASE,
            work_id,
            max(1, min(int(limit), 50)),
        )
        listing, fetched_at = self._get("cited_by", url)
        return {
            "count": payload.get("cited_by_count"),
            "items": [self._map(w, fetched_at) for w in listing.get("results") or []],
        }


class CrossrefProvider(LiteratureProvider):
    name = "crossref"
    BASE = "https://api.crossref.org"

    def _map(self, message, fetched_at):
        issued = ((message.get("issued") or {}).get("date-parts") or [[None]])[0]
        kind = message.get("type")
        return {
            "provider": self.name,
            "ids": {"doi": _clean_doi(message.get("DOI"))},
            "title": (message.get("title") or [None])[0],
            "year": issued[0] if isinstance(issued, list) and issued else None,
            "venue": (message.get("container-title") or [None])[0],
            "citations": message.get("is-referenced-by-count"),
            "citation_percentile": None,
            "categories": message.get("subject") or [],
            "is_preprint": True if kind == "posted-content" else None,
            "peer_reviewed": True if kind == "journal-article" else None,
            "fetched_at": fetched_at,
        }

    def resolve(self, ref):
        if not ref.get("doi"):
            raise ProviderError(self.name, "resolve", "crossref resolves DOIs only")
        payload, fetched_at = self._get(
            "resolve", "%s/works/%s" % (self.BASE, _clean_doi(ref["doi"]))
        )
        return self._map(payload["message"], fetched_at)

    def search(self, query, limit=10):
        url = "%s/works?query=%s&rows=%d" % (
            self.BASE,
            query.replace(" ", "+"),
            max(1, min(int(limit), 50)),
        )
        payload, fetched_at = self._get("search", url)
        items = (payload.get("message") or {}).get("items") or []
        return [self._map(item, fetched_at) for item in items]

    def references(self, ref):
        record, _ = self._get(
            "references", "%s/works/%s" % (self.BASE, _clean_doi(ref["doi"]))
        )
        items = [
            self._lite({"doi": _clean_doi(entry.get("DOI"))}, entry.get("unstructured"))
            for entry in (record["message"].get("reference") or [])
        ]
        return {"count": len(items), "items": items}

    def cited_by(self, ref, limit=10):
        record, _ = self._get(
            "cited_by", "%s/works/%s" % (self.BASE, _clean_doi(ref["doi"]))
        )
        # Crossref exposes the count only; no public cited-by listing.
        return {"count": record["message"].get("is-referenced-by-count"), "items": []}


class SemanticScholarProvider(LiteratureProvider):
    name = "semanticscholar"
    BASE = "https://api.semanticscholar.org/graph/v1"
    FIELDS = "title,year,venue,citationCount,externalIds"

    def _paper_id(self, ref):
        if ref.get("doi"):
            return "DOI:" + _clean_doi(ref["doi"])
        if ref.get("arxiv"):
            return "ARXIV:" + ref["arxiv"]
        if ref.get("s2"):
            return ref["s2"]
        raise ProviderError(self.name, "resolve", "need doi/arxiv/s2 in %r" % ref)

    def _map(self, paper, fetched_at):
        external = paper.get("externalIds") or {}
        return {
            "provider": self.name,
            "ids": {
                "s2": paper.get("paperId"),
                "doi": _clean_doi(external.get("DOI")),
                "arxiv": external.get("ArXiv"),
            },
            "title": paper.get("title"),
            "year": paper.get("year"),
            "venue": paper.get("venue") or None,
            "citations": paper.get("citationCount"),
            "citation_percentile": None,
            "categories": [],
            "fetched_at": fetched_at,
        }

    def resolve(self, ref):
        url = "%s/paper/%s?fields=%s" % (self.BASE, self._paper_id(ref), self.FIELDS)
        payload, fetched_at = self._get("resolve", url)
        return self._map(payload, fetched_at)

    def search(self, query, limit=10):
        url = "%s/paper/search?query=%s&limit=%d&fields=%s" % (
            self.BASE,
            query.replace(" ", "+"),
            max(1, min(int(limit), 50)),
            self.FIELDS,
        )
        payload, fetched_at = self._get("search", url)
        return [self._map(item, fetched_at) for item in payload.get("data") or []]

    def references(self, ref):
        url = "%s/paper/%s/references?fields=title,externalIds&limit=100" % (
            self.BASE,
            self._paper_id(ref),
        )
        payload, _ = self._get("references", url)
        items = []
        for entry in payload.get("data") or []:
            cited = entry.get("citedPaper") or {}
            external = cited.get("externalIds") or {}
            items.append(
                self._lite(
                    {"doi": _clean_doi(external.get("DOI")), "s2": cited.get("paperId")},
                    cited.get("title"),
                )
            )
        return {"count": len(items), "items": items}

    def cited_by(self, ref, limit=10):
        url = "%s/paper/%s/citations?fields=title,externalIds&limit=%d" % (
            self.BASE,
            self._paper_id(ref),
            max(1, min(int(limit), 100)),
        )
        payload, fetched_at = self._get("cited_by", url)
        items = []
        for entry in payload.get("data") or []:
            citing = entry.get("citingPaper") or {}
            external = citing.get("externalIds") or {}
            items.append(
                self._lite(
                    {"doi": _clean_doi(external.get("DOI")), "s2": citing.get("paperId")},
                    citing.get("title"),
                )
            )
        return {"count": None, "items": items}


class ArxivProvider(LiteratureProvider):
    name = "arxiv"
    BASE = "https://export.arxiv.org/api/query"
    _ATOM = "{http://www.w3.org/2005/Atom}"

    def _decode(self, raw):
        # Atom XML, cached as {"atom": text} so the cache stays JSON.
        return {"atom": raw.decode("utf-8")}

    def _entries(self, payload, operation):
        try:
            root = ElementTree.fromstring(payload["atom"])
        except ElementTree.ParseError as err:
            raise ProviderError(self.name, operation, "bad Atom feed: %s" % err)
        return root.findall(self._ATOM + "entry")

    def _map(self, entry, fetched_at):
        arxiv_id = (entry.findtext(self._ATOM + "id") or "").rsplit("/abs/", 1)[-1]
        published = entry.findtext(self._ATOM + "published") or ""
        title = " ".join((entry.findtext(self._ATOM + "title") or "").split())
        return {
            "provider": self.name,
            "ids": {"arxiv": re.sub(r"v\d+$", "", arxiv_id) or None},
            "title": title or None,
            "year": int(published[:4]) if published[:4].isdigit() else None,
            "venue": "arXiv",
            "citations": None,
            "citation_percentile": None,
            "categories": [],
            "is_preprint": True,
            "fetched_at": fetched_at,
        }

    def resolve(self, ref):
        if not ref.get("arxiv"):
            raise ProviderError(self.name, "resolve", "need an arxiv id in %r" % ref)
        payload, fetched_at = self._get(
            "resolve", "%s?id_list=%s" % (self.BASE, ref["arxiv"])
        )
        entries = self._entries(payload, "resolve")
        if not entries:
            raise ProviderError(self.name, "resolve", "no entry for %r" % ref["arxiv"])
        return self._map(entries[0], fetched_at)

    def search(self, query, limit=10):
        url = "%s?search_query=all:%s&max_results=%d" % (
            self.BASE,
            query.replace(" ", "+"),
            max(1, min(int(limit), 50)),
        )
        payload, fetched_at = self._get("search", url)
        return [self._map(e, fetched_at) for e in self._entries(payload, "search")]

    def references(self, ref):
        # arXiv's API carries no reference lists; typed refusal, no silent [].
        raise ProviderError(self.name, "references", "arXiv exposes no reference data")

    def cited_by(self, ref, limit=10):
        raise ProviderError(self.name, "cited_by", "arXiv exposes no citation data")


ADAPTERS = {
    "openalex": OpenAlexProvider,
    "crossref": CrossrefProvider,
    "semanticscholar": SemanticScholarProvider,
    "arxiv": ArxivProvider,
}
