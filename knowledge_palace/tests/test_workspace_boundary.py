"""The material boundary of the workspace package."""

import unittest

from knowledge_palace.workspace.material import new_material, validate_material

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



if __name__ == "__main__":
    unittest.main()
