"""Unified material acquisition: three-axis receipts, read-only providers,
staging in Derived State, and the immutable Source Snapshot transaction.

Hard rules: nothing becomes Claim-eligible unless
identity_status == verified AND text_status == ready; an identity mismatch
quarantines the staged file; a provider failure never yields a half-written
receipt or a partial staged file; full-text bytes never land under the
Vault; promotion into the real Source Cache happens only behind
the source-write gate with packaged user confirmation.
"""
