"""The argument-graph page keeps the graph through a save in either direction,
reads back in reading order, and tells which paragraphs the author's edits
touch while ignoring where things were dragged."""

import copy
import unittest

from knowledge_palace.workspace.argument_graph import changed_paragraphs, paragraphs, read_view, render_view

GRAPH = {
    "title": "Introduction — echo-paper",
    "section": "introduction",
    "paragraphs": [
        {"id": "p1", "role": "opening", "point": "cheap sensors, noisy signal"},
        {"id": "p2", "role": "closing", "point": "this work"},
    ],
    "nodes": [
        {"id": "a", "text": "cheap sensor", "evidence": "", "paragraph": "p1"},
        {"id": "b", "text": "noisy signal </script> & <b>", "evidence": "alpha-2020-echo C1", "paragraph": "p1"},
        {"id": "c", "text": "drift-aware canceller", "evidence": "", "paragraph": "p2"},
    ],
    "edges": [
        {"id": "e1", "from": "a", "to": "b", "label": "qualifies"},
        {"id": "e2", "from": "p1", "to": "p2", "label": "infers"},
    ],
}


class TestArgumentGraph(unittest.TestCase):
    def test_page_round_trips_the_graph_and_its_snapshot(self):
        edited = copy.deepcopy(GRAPH)
        edited["paragraphs"][0]["point"] = "cheap sensors need a model"
        page = render_view(edited, written=GRAPH)
        self.assertEqual(read_view(page), (edited, GRAPH))
        # a node that contains a closing script tag cannot end the JSON block early
        self.assertEqual(page.count("</script>"), 3)
        # the browser serializes attributes its own way; reading does not depend on their order
        resaved = page.replace('<script type="application/json" id="graph">', '<script id="graph" type="application/json">')
        self.assertEqual(read_view(resaved)[0], edited)

    def test_reading_order_follows_placement(self):
        placed = copy.deepcopy(GRAPH)
        placed["nodes"][0].update(x=240, y=46)   # dragged to the right of b on the same row
        placed["nodes"][1].update(x=16, y=50)
        placed["nodes"][2].update(x=16, y=46)
        first = paragraphs(placed)[0]
        self.assertEqual([n["text"] for n in first["nodes"]], ["noisy signal </script> & <b>", "cheap sensor"])
        self.assertEqual(first["edges"], [("cheap sensor", "qualifies", "noisy signal </script> & <b>"),
                                          ("¶cheap sensors, noisy signal", "infers", "¶this work")])

    def test_edits_name_the_paragraphs_to_rewrite_and_positions_do_not(self):
        graph, written = read_view(render_view(GRAPH))
        quiet = {"rewrite": [], "drop": [], "reordered": False, "unplaced": []}
        self.assertEqual(changed_paragraphs(graph, written), quiet)
        moved = copy.deepcopy(GRAPH)
        moved["nodes"][0].update(x=300, y=120)
        self.assertEqual(changed_paragraphs(moved, GRAPH), quiet)
        edited = copy.deepcopy(GRAPH)
        edited["edges"][0]["label"] = "opposes"
        edited["paragraphs"].insert(1, {"id": "p3", "role": "middle", "point": ""})
        self.assertEqual(changed_paragraphs(edited, GRAPH)["rewrite"], ["p1", "p3"])
        carried = copy.deepcopy(GRAPH)
        carried["nodes"][2]["paragraph"] = "p1"   # dragged into the first paragraph
        self.assertEqual(changed_paragraphs(carried, GRAPH)["rewrite"], ["p1", "p2"])
        swapped = copy.deepcopy(GRAPH)
        swapped["paragraphs"].reverse()
        self.assertEqual(changed_paragraphs(swapped, GRAPH)["reordered"], True)
        dropped = copy.deepcopy(GRAPH)
        del dropped["paragraphs"][1]
        self.assertEqual(changed_paragraphs(dropped, GRAPH)["drop"], ["p2"])
        self.assertEqual(changed_paragraphs(dropped, GRAPH)["unplaced"], ["drift-aware canceller"])


if __name__ == "__main__":
    unittest.main()
