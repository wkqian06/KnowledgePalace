"""Project briefs stay well-formed; writing context and passage replacement
refuse ambiguous inputs."""

import unittest

from knowledge_palace.workspace.brief import new_brief, validate_brief
from knowledge_palace.workspace.writing import replace_passage, writing_context


def sample_brief(**overrides):
    base = dict(
        project="echo-paper",
        problem="echo cancellation drifts",
        contribution="a drift-aware canceller",
        sections=[
            {"name": "introduction", "kind": "introduction", "depends_on": []},
            {"name": "methods", "kind": "methods", "depends_on": ["introduction"]},
            {"name": "results", "kind": "results", "depends_on": ["methods"]},
        ],
        evidence=[
            {"ref": "claim:alpha-2020-echo#C1",
             "quote": "echo cancellation reduces drift",
             "anchor": "— §3 [¶2] / p.4"},
            {"ref": "project-source:doi:10.55555/elsewhere",
             "quote": "drift persists at scale",
             "anchor": "— §5 / p.11"},
        ],
        materials=["material:user-results-csv"],
    )
    base.update(overrides)
    return new_brief(**base)


class TestBrief(unittest.TestCase):
    def test_valid_brief(self):
        self.assertEqual(validate_brief(sample_brief()), [])

    def test_evidence_needs_id_shape_quote_and_anchor(self):
        bad = sample_brief(evidence=[{"ref": "the alpha paper", "quote": "q"}])
        errors = validate_brief(bad)
        self.assertTrue(any("not id-shaped" in e for e in errors))
        self.assertTrue(any("anchor required" in e for e in errors))

    def test_material_refs_are_barred_from_evidence(self):
        bad = sample_brief(
            evidence=[{"ref": "material:user-results-csv", "quote": "q", "anchor": "a"}]
        )
        errors = validate_brief(bad)
        self.assertTrue(any("never Claim evidence" in e for e in errors))

    def test_unknown_dependency_and_duplicate_names_rejected(self):
        bad = sample_brief(sections=[
            {"name": "methods", "kind": "methods", "depends_on": ["missing"]},
            {"name": "methods", "kind": "methods", "depends_on": []},
        ])
        errors = validate_brief(bad)
        self.assertTrue(any("unknown" in e for e in errors))
        self.assertTrue(any("unique" in e for e in errors))

    def test_assembled_is_reserved(self):
        bad = sample_brief(sections=[
            {"name": "assembled", "kind": "other", "depends_on": []},
        ])
        errors = validate_brief(bad)
        self.assertTrue(any("reserved" in e for e in errors))


class TestWritingContext(unittest.TestCase):
    def test_project_mode_takes_evidence_and_materials_from_the_brief(self):
        context = writing_context("draft", "analysis", brief=sample_brief(), section="methods")
        self.assertEqual(context["project"], "echo-paper")
        self.assertEqual([row["ref"] for row in context["evidence"]],
                         ["claim:alpha-2020-echo#C1", "project-source:doi:10.55555/elsewhere"])
        self.assertEqual(context["materials"], ["material:user-results-csv"])

    def test_unknown_section_and_invalid_brief_refused(self):
        with self.assertRaises(ValueError):
            writing_context("draft", "analysis", brief=sample_brief(), section="acknowledgements")
        with self.assertRaises(ValueError):
            writing_context("draft", "analysis", brief=sample_brief(sections=[]))

    def test_direct_mode_passes_supplied_inputs_through(self):
        context = writing_context("draft", "analysis", evidence=["claim:x#C1"])
        self.assertIsNone(context["project"])
        self.assertEqual(context["evidence"], ["claim:x#C1"])
        self.assertEqual((context["text"], context["analysis"]), ("draft", "analysis"))


class TestReplacePassage(unittest.TestCase):
    def test_replaces_one_unique_passage_only(self):
        document = "Intro.\n\nThe old sentence.\n\nOutro.\n"
        revised = replace_passage(document, "The old sentence.", "The new sentence.")
        self.assertEqual(revised, "Intro.\n\nThe new sentence.\n\nOutro.\n")

    def test_missing_or_ambiguous_passage_refused(self):
        document = "same\n\nsame\n"
        for original in ("", "absent", "same"):
            with self.assertRaises(ValueError):
                replace_passage(document, original, "x")


if __name__ == "__main__":
    unittest.main()
