"""The material boundary and the no-Git/no-network
guarantee of the workspace package, by construction."""

import unittest
from pathlib import Path

from knowledge_palace.workspace.material import new_material, validate_material

WORKSPACE_PKG = Path(__file__).resolve().parents[1] / "workspace"
FORBIDDEN_MARKERS = (
    "subprocess", "os.system", "os.popen",          # no Git, no shell
    "urllib", "http.client", "socket", "requests",  # no network
)


class TestMaterialBoundary(unittest.TestCase):
    def test_valid_material(self):
        material = new_material("user-results-csv", "materials/results.csv", "data")
        self.assertEqual(validate_material(material), [])
        self.assertIs(material["vault_claim_eligible"], False)

    def test_tampered_eligibility_is_a_validation_error(self):
        material = new_material("m", "materials/x.md", "draft")
        material["vault_claim_eligible"] = True
        errors = validate_material(material)
        self.assertTrue(any("never become Vault Claim" in e for e in errors))

    def test_absolute_and_escaping_paths_rejected(self):
        for path in ("/etc/passwd", "../outside.md", "a/../../b"):
            material = new_material("m", path, "other")
            self.assertTrue(validate_material(material), path)

    def test_unknown_kind_and_bare_id_rejected(self):
        self.assertTrue(validate_material(new_material("m", "x.md", "poem")))
        self.assertTrue(validate_material(new_material("", "x.md", "draft")))


class TestNoGitNoNetworkByConstruction(unittest.TestCase):
    def test_workspace_sources_carry_no_shell_or_network_markers(self):
        for path in sorted(WORKSPACE_PKG.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            source = path.read_text(encoding="utf-8")
            for marker in FORBIDDEN_MARKERS:
                self.assertNotIn(
                    marker,
                    source,
                    "%s must stay shell- and network-free (found %r)"
                    % (path.name, marker),
                )


if __name__ == "__main__":
    unittest.main()
