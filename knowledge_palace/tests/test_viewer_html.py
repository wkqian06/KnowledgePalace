"""The emitted bundle is offline-only, well-formed."""

import json
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import write_index
from knowledge_palace.viewer.export import build_bundle, canonical_bytes
from knowledge_palace.viewer.html_template import render

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"


class TestHtmlSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        state = Path(tmp.name) / "state"
        write_index(MINI, state)
        cls.payload_bytes = canonical_bytes(build_bundle(MINI, state))
        cls.html = render(cls.payload_bytes).decode("utf-8")

    def test_no_external_requests_anywhere(self):
        # Network-triggering markup/code constructs must be absent. A bare
        # "https://" substring is NOT itself a violation — vault-mini's own
        # card data legitimately carries citation URLs as inert JSON text
        # (e.g. a "source" DOI/URL string); what must never appear is
        # anything that makes the BROWSER fetch it.
        for marker in (
            "<script src=", "<link ", "<img ", "fetch(", "XMLHttpRequest(",
            "new WebSocket(", "@import", "url(http",
        ):
            self.assertNotIn(marker, self.html, marker)

    def test_embedded_json_round_trips(self):
        start = self.html.index('id="palace-data">') + len('id="palace-data">')
        end = self.html.index("</script>", start)
        embedded = self.html[start:end]  # angle brackets arrive JSON-escaped; json.loads decodes them
        parsed = json.loads(embedded)
        self.assertEqual(parsed, json.loads(self.payload_bytes))

    def test_script_close_and_comment_sequences_do_not_break_out(self):
        # Two known ways untrusted text can perturb an HTML script-data
        # tokenizer: a literal "</script" terminator, and "<!--" followed
        # by an unclosed "<script" (the tokenizer's escape-state rules
        # react to a bare "<", not only to "</script"). Escaping every
        # "<" (not just "</") is required — verify against both, and
        # confirm zero bare "<" survives in the embedded segment, which
        # is what actually guarantees an HTML tokenizer can't be confused
        # regardless of which specific trigger sequence is used.
        payload = {
            "nodes": {
                "x": {"id": "x", "kind": "work", "label": "</script><script>evil()</SCRIPT>"},
                "y": {"id": "y", "kind": "work", "label": "Title <!-- and <script>foo"},
            }
        }
        raw = json.dumps(payload).encode("utf-8")
        html = render(raw).decode("utf-8")
        from knowledge_palace.viewer.html_template import _SCRIPT

        self.assertEqual(html.count(_SCRIPT), 1)  # real logic verbatim, exactly once
        start = html.index('id="palace-data">') + len('id="palace-data">')
        end = html.index("</script>", start)
        segment = html[start:end]
        self.assertNotIn("<", segment)  # no bare "<" survives to confuse a tokenizer
        self.assertEqual(json.loads(segment), payload)


if __name__ == "__main__":
    unittest.main()
