"""Contextual ImpactSnapshot and classifier (pure functions, no I/O).

A snapshot stores raw observations per Work — field-normalized citation
percentile, categories, optional per-category JCR quartiles from a
user-supplied licensed export, venue text from the card — side by side.
No global high/medium/low is stored per Work: ``classify`` computes a band
for ONE explicit Evaluation Context and records that context in the result;
``classify_all`` lays the per-category verdicts side by side and never
max-picks.
"""

BANDS = ("high", "medium", "low", "unknown")
_RANK = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
JCR_BAND = {"Q1": "high", "Q2": "medium", "Q3": "low", "Q4": "low"}


def build_snapshot(record, work_slug=None, journal_if_text=None, jcr_quartiles=None):
    """Assemble one snapshot from a normalized provider record.

    ``jcr_quartiles`` maps category name → quartile string (user-supplied
    licensed data); ``journal_if_text`` is the card's persisted venue metric
    text, kept verbatim as display context.
    """
    return {
        "work": work_slug,
        "source": record.get("provider"),
        "fetched_at": record.get("fetched_at"),
        "title": record.get("title"),
        "year": record.get("year"),
        "venue": record.get("venue"),
        "citations": record.get("citations"),
        "citation_percentile": record.get("citation_percentile"),
        "categories": list(record.get("categories") or []),
        "jcr_quartiles": dict(jcr_quartiles or {}),
        "venue_metric_text": journal_if_text,
        "is_preprint": bool(record.get("is_preprint")),
        "peer_reviewed": record.get("peer_reviewed"),
    }


def _citation_band(percentile):
    if percentile is None:
        return "unknown"
    if percentile >= 90:
        return "high"
    if percentile >= 50:
        return "medium"
    return "low"


def classify(snapshot, context_category, evaluation_year):
    """Band one snapshot under ONE Evaluation Context. Pure function.

    Channels: field-normalized citation percentile (the provider normalizes
    by field and year), and the JCR quartile for the context category when
    the user supplied one (coarse fallback, flagged). The higher known
    channel wins; unknown stays unknown — there is NO fallback to absolute
    citation counts. Preprints band by citations only. A peer-reviewed paper
    under 3 years old takes a medium floor.
    """
    citation_band = _citation_band(snapshot.get("citation_percentile"))
    basis = ["citation-percentile:%s" % (snapshot.get("citation_percentile"),)]

    venue_band = "unknown"
    coarse = False
    quartile = (snapshot.get("jcr_quartiles") or {}).get(context_category)
    if snapshot.get("is_preprint"):
        basis.append("venue:excluded(preprint)")
    elif quartile in JCR_BAND:
        venue_band = JCR_BAND[quartile]
        coarse = True
        basis.append("venue:jcr-%s(coarse)" % quartile)
    else:
        basis.append("venue:unknown(no field percentile or JCR)")

    band = citation_band if _RANK[citation_band] >= _RANK[venue_band] else venue_band
    channel = "citations" if band == citation_band and band != "unknown" else (
        "venue" if band != "unknown" else "none"
    )

    year = snapshot.get("year")
    floored = False
    if (
        snapshot.get("peer_reviewed")
        and not snapshot.get("is_preprint")
        and year is not None
        and 0 <= evaluation_year - year < 3
        and _RANK[band] < _RANK["medium"]
    ):
        band = "medium"
        channel = "floor"
        floored = True
        basis.append("floor:peer-reviewed<3yr")

    return {
        "band": band,
        "channel": channel,
        "coarse_fallback": coarse and channel == "venue" and not floored,
        "context": {"category": context_category, "evaluation_year": evaluation_year},
        "basis": "; ".join(basis),
    }


def classify_all(snapshot, evaluation_year):
    """Side-by-side per-category verdicts. Never collapsed to a maximum."""
    categories = snapshot.get("categories") or []
    if not categories:
        categories = ["(uncategorized)"]
    return {
        category: classify(snapshot, category, evaluation_year)
        for category in categories
    }
