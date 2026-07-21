"""GraphQueryPort message validator (stdlib only).

Structural validation is driven by ``protocol/graph_query_port.schema.json``
through a small JSON-Schema-subset checker (type / required / properties /
additionalProperties / items / enum / $ref / oneOf / minimum / pattern —
exactly what the canonical schema uses). Contract invariants beyond structure
(pagination arithmetic, logical references, entry-parent rules, brief
non-evidence, stale service, version majors) are enforced in code and mirrored
in the schema's ``x-invariants``. The production port implementation must pass
this same validator unchanged.
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "protocol" / "graph_query_port.schema.json"
)
EVIDENCE_EDGE_KINDS = ("evidence", "supports", "disputes", "claims")
_PAGE_KEYS = {"total", "returned", "truncated", "next_cursor", "items"}
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


def load_schema(path=None):
    schema_file = Path(path) if path else SCHEMA_PATH
    return json.loads(schema_file.read_text(encoding="utf-8"))


def _is_type(value, name):
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    raise ValueError("unsupported schema type: %r" % name)


def _check(value, schema, defs, where, errors):
    if "$ref" in schema:
        _check(value, defs[schema["$ref"].rsplit("/", 1)[-1]], defs, where, errors)
        return
    if "oneOf" in schema:
        matches = 0
        for branch in schema["oneOf"]:
            branch_errors = []
            _check(value, branch, defs, where, branch_errors)
            if not branch_errors:
                matches += 1
        if matches != 1:
            errors.append(
                "%s: value matches %d oneOf branches (need exactly 1)" % (where, matches)
            )
        return
    if "enum" in schema:
        if value not in schema["enum"]:
            errors.append("%s: %r not in enum %s" % (where, value, schema["enum"]))
        return
    declared = schema.get("type")
    if declared is not None:
        types = declared if isinstance(declared, list) else [declared]
        if not any(_is_type(value, name) for name in types):
            errors.append(
                "%s: expected type %s, got %s" % (where, types, type(value).__name__)
            )
            return
    if isinstance(value, dict):
        for required_key in schema.get("required", []):
            if required_key not in value:
                errors.append("%s.%s: required key missing" % (where, required_key))
        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key in value:
                _check(value[key], subschema, defs, "%s.%s" % (where, key), errors)
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append("%s.%s: additional property not allowed" % (where, key))
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _check(item, schema["items"], defs, "%s[%d]" % (where, index), errors)
    if isinstance(value, int) and not isinstance(value, bool) and "minimum" in schema:
        if value < schema["minimum"]:
            errors.append("%s: %d below minimum %d" % (where, value, schema["minimum"]))
    if isinstance(value, str) and "pattern" in schema:
        if not re.search(schema["pattern"], value):
            errors.append("%s: %r does not match pattern %r" % (where, value, schema["pattern"]))


def validate_structure(message, def_name, schema=None):
    schema = schema or load_schema()
    errors = []
    _check(message, {"$ref": "#/$defs/" + def_name}, schema["$defs"], "$", errors)
    return errors


def _walk(obj):
    yield obj
    if isinstance(obj, dict):
        for value in obj.values():
            for sub in _walk(value):
                yield sub
    elif isinstance(obj, list):
        for value in obj:
            for sub in _walk(value):
                yield sub


def _page_violations(message):
    errors = []
    for obj in _walk(message):
        if not (isinstance(obj, dict) and _PAGE_KEYS <= set(obj)):
            continue
        total, returned = obj["total"], obj["returned"]
        truncated, cursor, items = obj["truncated"], obj["next_cursor"], obj["items"]
        if returned != len(items):
            errors.append(
                "page: silent omission — returned=%r != len(items)=%d"
                % (returned, len(items))
            )
        if returned > total:
            errors.append("page: returned=%r exceeds total=%r" % (returned, total))
        if truncated != (cursor is not None):
            errors.append(
                "page: truncated=%r but next_cursor=%r (next_cursor must be non-null "
                "iff truncated)" % (truncated, cursor)
            )
        if truncated and returned >= total:
            errors.append(
                "page: truncated=true yet returned=%r >= total=%r" % (returned, total)
            )
    return errors


def _ref_violations(message):
    errors = []
    for obj in _walk(message):
        if not (isinstance(obj, dict) and "root" in obj and "path" in obj):
            continue
        path = obj["path"]
        if not isinstance(path, str):
            continue
        if path.startswith("/") or path.startswith("\\"):
            errors.append("canonical_ref: absolute path %r" % path)
        if _WINDOWS_DRIVE.match(path):
            errors.append("canonical_ref: drive-lettered path %r" % path)
        if "\\" in path:
            errors.append("canonical_ref: backslash separator in %r" % path)
        if ".." in path.split("/"):
            errors.append("canonical_ref: parent escape in %r" % path)
        if path.startswith("~"):
            errors.append("canonical_ref: HOME expansion in %r" % path)
        if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*://", path):
            errors.append("canonical_ref: URL %r" % path)
    return errors


def _brief_violations(message):
    errors = []
    brief_ids = set()
    for obj in _walk(message):
        if not isinstance(obj, dict):
            continue
        if obj.get("kind") == "brief" and "label" in obj and "id" in obj:
            brief_ids.add(obj["id"])
            attrs = obj.get("attrs") or {}
            if attrs.get("role") != "view" or attrs.get("evidence_capable") is not False:
                errors.append(
                    "brief node %r must carry attrs.role='view' and "
                    "attrs.evidence_capable=false" % obj["id"]
                )
    for obj in _walk(message):
        if not (isinstance(obj, dict) and "from" in obj and "to" in obj and "kind" in obj):
            continue
        if obj["kind"] in EVIDENCE_EDGE_KINDS and obj["from"] in brief_ids:
            errors.append(
                "edge %r: evidence-bearing edge kind %r originates from brief node %r"
                % (obj.get("id"), obj["kind"], obj["from"])
            )
    return errors


def _context_violations(message):
    errors = []
    parents = {p["id"] for p in message.get("parents", []) if isinstance(p, dict)}
    entry = message.get("entry_parent")
    siblings = message.get("siblings")
    groups = message.get("sibling_groups")
    if entry is not None:
        if entry not in parents:
            errors.append("entry_parent %r is not one of parents %s" % (entry, sorted(parents)))
        if siblings is None:
            errors.append("entry_parent given but siblings page is null")
        if groups is not None:
            errors.append("entry_parent given but sibling_groups is not null")
    else:
        if len(parents) > 1:
            if groups is None:
                errors.append("multi-parent context without entry_parent must return sibling_groups")
            if siblings is not None:
                errors.append("multi-parent context without entry_parent must not return a flat siblings page")
            covered = [
                group.get("parent_id")
                for group in groups or []
                if isinstance(group, dict)
            ]
            if groups is not None and (
                sorted(set(covered)) != sorted(parents) or len(covered) != len(parents)
            ):
                errors.append(
                    "sibling_groups must cover each parent exactly once: groups=%s "
                    "parents=%s" % (sorted(covered), sorted(parents))
                )
        elif groups is not None:
            errors.append(
                "sibling_groups returned for a node with %d parent(s)" % len(parents)
            )
    return errors


def validate_response(op, message, schema=None, current_vault_fingerprint=None):
    """Return a list of contract violations; empty means conforming."""
    schema = schema or load_schema()
    if op not in schema["operations"]:
        return ["unknown operation: %r (surface is %s)" % (op, schema["operations"])]
    if not isinstance(message, dict):
        return ["response must be a JSON object"]

    if "error" in message:
        # A typed rejection (including stale_index) is spec-conforming.
        return validate_structure(message, "ErrorResponse", schema)

    def_name = schema["responses"][op].rsplit("/", 1)[-1]
    errors = validate_structure(message, def_name, schema)
    if errors:
        return errors

    version = message["schema_version"]
    if version.split(".", 1)[0] != schema["schema_version"].split(".", 1)[0]:
        errors.append(
            "schema_version %r has unknown major (validator knows %r)"
            % (version, schema["schema_version"])
        )
    errors.extend(_page_violations(message))
    errors.extend(_ref_violations(message))
    errors.extend(_brief_violations(message))
    if op == "query_context":
        errors.extend(_context_violations(message))
    if current_vault_fingerprint is not None:
        served = message["snapshot"]["vault_fingerprint"]
        if served != current_vault_fingerprint:
            errors.append(
                "stale index served as success: snapshot fingerprint %r != current %r "
                "(conforming behavior is an error with code 'stale_index')"
                % (served, current_vault_fingerprint)
            )
    return errors


def run(argv):
    parser = argparse.ArgumentParser(
        prog="gqp_validator", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--op", required=True, help="operation the message answers")
    parser.add_argument("--file", required=True, help="JSON response file to validate")
    parser.add_argument(
        "--fingerprint", help="current Vault fingerprint (enables stale-service check)"
    )
    args = parser.parse_args(argv)
    message = json.loads(Path(args.file).read_text(encoding="utf-8"))
    errors = validate_response(
        args.op, message, current_vault_fingerprint=args.fingerprint
    )
    for error in errors:
        print("VIOLATION: %s" % error, file=sys.stderr)
    print("%s: %d violation(s)" % (args.file, len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
