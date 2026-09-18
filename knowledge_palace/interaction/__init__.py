"""Interaction layer: bounded, id-only retrieval for discussion and ideas.

prefilter and research_helpers select a bounded candidate set from the Graph
Index; novelty runs the profile-relative 10/15/30 pipeline for idea refinement;
project_source resolves author-supplied references against Vault identity and
records the external-novelty opt-in. Scientific judgment stays with the agent.
"""
