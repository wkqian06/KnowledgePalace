"""Deterministic, stdlib-only tools of the KnowledgePalace shared core."""

SCHEMA_VERSION = "1.0"

ROLES = (
    "extractor",
    "linker",
    "scout",
    "auditor",
    "analyst",
    "stylist",
    "expansion-reviewer",
    "writer",
    "reviewer",
)

TEMPLATE_FILES = (
    "expansion-run.md",
    "gap-card.md",
    "gaps-INDEX.md",
    "paper-card.md",
    "papers-INDEX.md",
    "style-bank-entry.md",
    "style-profile.md",
    "transfer-card.md",
)

PROTOCOL_FILES = (
    "PROTOCOL.md",
    "COMMANDS.md",
    "GRAPH_QUERY_PORT.md",
    "graph_query_port.schema.json",
)
