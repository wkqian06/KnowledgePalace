"""Thin hub pages, marker-scoped regeneration, brief stale flags."""

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from knowledge_palace.graph.builder import write_index
from knowledge_palace.viewer.export import build_bundle
from knowledge_palace.viewer.obsidian import (
    build_pages,
    export,
    mark_brief_staleness,
    resolve_wiki_dir,
    run,
    scan_generated,
    write_pages,
)

MINI = Path(__file__).resolve().parent / "fixtures" / "vault-mini"

BRIEF = """---
snapshot_id: {snapshot}
generated_at: 2026-07-21
command: brief map concept-echo
stale: false
---

# Map: concept-echo

Body line one.
Body line two.
"""


class WikiCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.state = self.root / "state"
        write_index(MINI, self.state)
        self.payload = build_bundle(MINI, self.state)

    def pages(self):
        return build_pages(self.payload, vault_name="vault", wiki_name="wiki")


class TestPageSet(WikiCase):
    def test_expected_page_set_for_vault_mini(self):
        pages = self.pages()
        expected = {
            "overview.md",
            "domains/alpha-domain.md",
            "domains/beta-domain.md",
            "concepts/alpha-domain.md",
            "concepts/beta-domain.md",
            "concepts/concept-echo.md",
            "concepts/concept-foxtrot.md",
            "concepts/concept-gamma.md",
            "concepts/concept-shared-pattern.md",
            "concepts/method-delta.md",
            "gaps/gap-echo-noise.md",
            "gaps/gap-gamma-drift.md",
            "transfers/transfer-echo-to-gamma.md",
        }
        self.assertEqual(set(pages), expected)  # no papers/, no claim pages

    def test_deterministic(self):
        self.assertEqual(self.pages(), self.pages())

    def test_links_are_posix_path_qualified(self):
        blob = "".join(self.pages().values())
        for target in re.findall(r"\[\[([^|\]]+)", blob):
            self.assertTrue(
                target.startswith("vault/") or target.startswith("wiki/"), target
            )
            self.assertNotIn("\\", target)
            self.assertFalse(target.endswith(".md"), target)
            self.assertNotIn("#C", target)  # claim anchors are not headings
        self.assertNotIn(str(MINI.resolve()), blob)

    def test_edge_kinds_land_in_sections(self):
        pages = self.pages()
        transfer = pages["transfers/transfer-echo-to-gamma.md"]
        for heading in ("## From", "## To", "## Bridges", "## Addresses", "## Evidence papers"):
            self.assertIn(heading, transfer)
        self.assertIn("[[vault/papers/alpha-2020-echo|", transfer)
        gap = pages["gaps/gap-echo-noise.md"]
        self.assertIn("[[wiki/gaps/gap-gamma-drift|", gap)  # Related gaps
        self.assertIn("[[vault/gaps/gap-echo-noise|", gap)  # Card link
        echo = pages["concepts/concept-echo.md"]
        self.assertIn("## Gaps concerning this", echo)
        self.assertIn("[[vault/concepts#task|", echo)


class TestRegeneration(WikiCase):
    def test_unmarked_collision_refused_untouched(self):
        wiki = self.root / "wiki"
        wiki.mkdir()
        (wiki / "overview.md").write_text("# my own page\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            write_pages(wiki, self.pages())
        self.assertEqual(
            (wiki / "overview.md").read_text(encoding="utf-8"), "# my own page\n"
        )
        self.assertFalse((wiki / "gaps").exists())  # nothing else written either

    def test_orphans_deleted_unmarked_kept(self):
        wiki = self.root / "wiki"
        (wiki / "gaps").mkdir(parents=True)
        (wiki / "briefs").mkdir()
        (wiki / ".obsidian").mkdir()
        marked = "---\npalace_generated: true\npalace_kind: gap\n---\n\nold\n"
        (wiki / "gaps" / "old.md").write_text(marked, encoding="utf-8")
        (wiki / "notes.md").write_text("# my notes\n", encoding="utf-8")
        (wiki / "briefs" / "x.md").write_text(marked, encoding="utf-8")
        (wiki / ".obsidian" / "graph.md").write_text(marked, encoding="utf-8")

        written, deleted = write_pages(wiki, self.pages())
        self.assertEqual(written, 13)
        self.assertEqual(deleted, 1)
        self.assertFalse((wiki / "gaps" / "old.md").exists())
        self.assertTrue((wiki / "notes.md").exists())
        self.assertTrue((wiki / "briefs" / "x.md").exists())  # briefs exempt
        self.assertTrue((wiki / ".obsidian" / "graph.md").exists())
        self.assertFalse(list(wiki.rglob("*.part")))

    def test_idempotent_bytes_on_disk(self):
        wiki = self.root / "wiki"
        write_pages(wiki, self.pages())
        first = {p: p.read_bytes() for p in wiki.rglob("*.md")}
        write_pages(wiki, self.pages())
        second = {p: p.read_bytes() for p in wiki.rglob("*.md")}
        self.assertEqual(first, second)

    def test_scan_ignores_briefs_and_dotdirs(self):
        wiki = self.root / "wiki"
        write_pages(wiki, self.pages())
        managed = scan_generated(wiki)
        self.assertEqual(len(managed), 13)


class TestBriefStaleness(WikiCase):
    def brief_at(self, snapshot):
        wiki = self.root / "wiki"
        (wiki / "briefs").mkdir(parents=True)
        path = wiki / "briefs" / "map-concept-echo.md"
        path.write_text(BRIEF.format(snapshot=snapshot), encoding="utf-8")
        return wiki, path

    def test_stale_flip_preserves_body_bytes(self):
        wiki, path = self.brief_at("snap-000000000000")
        before = path.read_text(encoding="utf-8")
        body_before = before.split("---\n", 2)[2]
        flipped = mark_brief_staleness(wiki, "snap-current")
        self.assertEqual(flipped, ["briefs/map-concept-echo.md"])
        after = path.read_text(encoding="utf-8")
        self.assertIn("stale: true", after)
        self.assertEqual(after.split("---\n", 2)[2], body_before)

    def test_matching_snapshot_untouched(self):
        wiki, path = self.brief_at("snap-current")
        original = path.read_bytes()
        self.assertEqual(mark_brief_staleness(wiki, "snap-current"), [])
        self.assertEqual(path.read_bytes(), original)  # flag already correct

    def test_frontmatterless_brief_untouched(self):
        wiki = self.root / "wiki"
        (wiki / "briefs").mkdir(parents=True)
        path = wiki / "briefs" / "free-form.md"
        path.write_text("just prose\n", encoding="utf-8")
        self.assertEqual(mark_brief_staleness(wiki, "snap-x"), [])
        self.assertEqual(path.read_text(encoding="utf-8"), "just prose\n")


class TestDirResolutionAndCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        private = self.root / "private"
        self.roots = {
            "vault_dir": private / "vault",
            "state_dir": private / "state",
            "source_dir": self.root / "sources",
            "workspace_dir": private / "workspace",
        }
        for path in self.roots.values():
            path.mkdir(parents=True)

    def write_config(self):
        config = self.root / ".palace.toml"
        config.write_text(
            "".join(
                '%s = "%s"\n' % (key, self.roots[key].as_posix())
                for key in ("vault_dir", "state_dir", "source_dir", "workspace_dir")
            ),
            encoding="utf-8",
        )
        return config

    def test_default_is_vault_sibling_wiki(self):
        target = resolve_wiki_dir(None, self.roots)
        self.assertEqual(target, self.roots["vault_dir"].parent / "wiki")

    def test_rejects_dir_inside_any_root(self):
        for key in self.roots:
            with self.assertRaises(ValueError):
                resolve_wiki_dir(self.roots[key] / "wiki", self.roots)

    def test_rejects_dir_containing_a_root(self):
        with self.assertRaises(ValueError):
            resolve_wiki_dir(self.roots["vault_dir"].parent, self.roots)
        with self.assertRaises(ValueError):
            resolve_wiki_dir(self.root, self.roots)

    def test_stale_index_is_maintained_before_export(self):
        shutil.copytree(MINI, self.roots["vault_dir"], dirs_exist_ok=True)
        write_index(self.roots["vault_dir"], self.roots["state_dir"])
        card = self.roots["vault_dir"] / "gaps" / "gap-echo-noise.md"
        card.write_text(
            card.read_text(encoding="utf-8") + "\n<!-- x -->\n", encoding="utf-8"
        )
        config = self.write_config()
        self.assertEqual(run(["--config", str(config)]), 0)
        self.assertTrue((self.roots["vault_dir"].parent / "wiki").exists())

    def test_cli_end_to_end(self):
        shutil.copytree(MINI, self.roots["vault_dir"], dirs_exist_ok=True)
        write_index(self.roots["vault_dir"], self.roots["state_dir"])
        config = self.write_config()
        self.assertEqual(run(["--config", str(config)]), 0)
        wiki = self.roots["vault_dir"].parent / "wiki"
        self.assertTrue((wiki / "overview.md").is_file())
        overview = (wiki / "overview.md").read_text(encoding="utf-8")
        self.assertIn("```mermaid", overview)
        self.assertIn("[[vault/", overview)


if __name__ == "__main__":
    unittest.main()
