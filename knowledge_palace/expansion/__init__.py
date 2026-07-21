"""Bounded A→B→C literature expansion.

One Candidate per Work identity no matter how many paths discover it;
Selection Decisions are keyed by Scope so a rejection can never become a
global blacklist; the budget counts unique identity-verified non-Vault
Candidates; only ingested Works, explicit user roots, and Vault Hits expand
further; everything before the packaged confirmation lives in Derived State
(`<state_dir>/expansion/`), and the compact run record reaches the Vault
only through that confirmation (first real write behind
the vault-write gate).
"""
