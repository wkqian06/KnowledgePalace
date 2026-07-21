"""Govern stays offline — the live transport is the
single network code path, confined to metadata/providers.py."""

import unittest
from pathlib import Path

CORE = Path(__file__).resolve().parents[1]
NETWORK_MARKERS = ("urllib", "http.client", "socket", "requests")
THE_ONE_NETWORK_FILE = CORE / "metadata" / "providers.py"


class TestOfflineGuarantee(unittest.TestCase):
    def test_network_code_exists_only_in_providers(self):
        for path in sorted(CORE.rglob("*.py")):
            if (
                path == THE_ONE_NETWORK_FILE
                or "__pycache__" in path.parts
                or "tests" in path.parts  # test sources may name the markers
            ):
                continue
            source = path.read_text(encoding="utf-8")
            for marker in NETWORK_MARKERS:
                self.assertNotIn(
                    marker,
                    source,
                    "%s must stay offline (found %r)" % (path.relative_to(CORE), marker),
                )

    def test_live_transport_is_lazily_imported(self):
        source = THE_ONE_NETWORK_FILE.read_text(encoding="utf-8")
        head = source[: source.index("def live_transport")]
        for line in head.splitlines():
            stripped = line.strip()
            self.assertFalse(
                stripped.startswith("import urllib") or stripped.startswith("from urllib"),
                "urllib must be imported inside live_transport(), not at module top",
            )
        self.assertIn("import urllib.request", source)


if __name__ == "__main__":
    unittest.main()
