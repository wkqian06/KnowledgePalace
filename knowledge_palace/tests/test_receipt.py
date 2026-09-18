"""The three-axis receipt contract — validation,
mechanical identity, and the claim-eligibility truth table."""

import unittest

from knowledge_palace.acquisition.receipt import (
    claim_eligible,
    new_receipt,
    new_request,
    resolve_identity,
    validate_receipt,
)

DOI = "10.99999/fixture.alpha2020"


def receipt_with(**overrides):
    receipt = new_receipt(new_request(work_slug="w", ids={"doi": DOI}), "local")
    receipt.update(overrides)
    return receipt


class TestValidation(unittest.TestCase):
    def test_fresh_receipt_is_valid_and_pessimistic(self):
        receipt = receipt_with()
        self.assertEqual(validate_receipt(receipt), [])
        self.assertEqual(receipt["acquisition_status"], "not_found")
        self.assertEqual(receipt["identity_status"], "unverified")
        self.assertEqual(receipt["text_status"], "not_attempted")

    def test_axis_enums_are_closed(self):
        for axis in ("acquisition_status", "identity_status", "text_status"):
            errors = validate_receipt(receipt_with(**{axis: "excellent"}))
            self.assertTrue(any(axis in error for error in errors), axis)

    def test_acquired_requires_sha(self):
        errors = validate_receipt(receipt_with(acquisition_status="acquired"))
        self.assertTrue(any("sha256" in error for error in errors))

    def test_mismatch_requires_quarantine(self):
        errors = validate_receipt(receipt_with(identity_status="mismatch"))
        self.assertTrue(any("quarantine" in error for error in errors))
        clean = receipt_with(identity_status="mismatch", quarantined=True)
        self.assertEqual(validate_receipt(clean), [])

    def test_staged_paths_must_be_state_relative(self):
        errors = validate_receipt(receipt_with(staged_path="/abs/evil.pdf"))
        self.assertTrue(any("state-relative" in error for error in errors))
        errors = validate_receipt(receipt_with(staged_text_path="a/../../b.txt"))
        self.assertTrue(any("state-relative" in error for error in errors))


class TestClaimEligibility(unittest.TestCase):
    def test_truth_table_requires_all_three_axes(self):
        base = dict(
            acquisition_status="acquired",
            identity_status="verified",
            text_status="ready",
            sha256="a" * 64,
        )
        self.assertTrue(claim_eligible(receipt_with(**base)))
        for downgrade in (
            {"acquisition_status": "failed"},
            {"identity_status": "unverified"},
            {"identity_status": "mismatch", "quarantined": True},
            {"text_status": "not_attempted"},
            {"text_status": "needs_ocr"},
            {"text_status": "extraction_failed"},
            {"quarantined": True},
        ):
            overrides = dict(base)
            overrides.update(downgrade)
            self.assertFalse(claim_eligible(receipt_with(**overrides)), downgrade)


class TestMechanicalIdentity(unittest.TestCase):
    def test_expected_sha_match_and_mismatch(self):
        data = b"payload"
        import hashlib

        good = new_request(expected_sha256=hashlib.sha256(data).hexdigest())
        self.assertEqual(resolve_identity(good, staged_bytes=data)[0], "verified")
        bad = new_request(expected_sha256="0" * 64)
        status, evidence = resolve_identity(bad, staged_bytes=data)
        self.assertEqual(status, "mismatch")
        self.assertIn("!=", evidence)

    def test_doi_in_text_head_verifies(self):
        request = new_request(ids={"doi": DOI})
        status, evidence = resolve_identity(
            request, text_head="Title page ... doi:%s ..." % DOI.upper()
        )
        self.assertEqual(status, "verified")
        self.assertIn("DOI", evidence)

    def test_user_confirmation_is_recorded_with_provenance(self):
        request = new_request(
            user_confirmed_identity=True, confirmation_provenance="ingest batch 7"
        )
        status, evidence = resolve_identity(request)
        self.assertEqual(status, "verified")
        self.assertIn("ingest batch 7", evidence)

    def test_default_is_unverified(self):
        self.assertEqual(resolve_identity(new_request())[0], "unverified")


if __name__ == "__main__":
    unittest.main()
