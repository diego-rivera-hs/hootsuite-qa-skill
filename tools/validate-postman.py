#!/usr/bin/env python3
"""
validate-postman.py — validate a Postman collection v2.1 before handing it to the dev.

Usage:
    python3 tools/validate-postman.py <path-to-collection.json>

Exit 0 on success, 1 on any validation failure.
"""

import json
import re
import sys


def validate(path: str) -> None:
    with open(path) as f:
        d = json.load(f)

    # Top-level keys
    assert set(d.keys()) <= {"info", "item", "auth", "event", "variable"}, \
        f"unexpected top-level keys: {set(d.keys()) - {'info', 'item', 'auth', 'event', 'variable'}}"

    assert "info" in d and "item" in d, "missing required top-level keys: info, item"

    # Schema inside info (not at root)
    info = d["info"]
    assert "schema" in info, "schema MUST be inside info{}"
    assert info["schema"].endswith("v2.1.0/collection.json"), \
        f"wrong schema: {info['schema']}"
    assert "schema" not in d, "schema must NOT be at the top level"

    # Variables
    vars_ = d.get("variable", [])
    assert vars_, "missing top-level `variable` array — add localhost + placeholders"
    keys = {v["key"] for v in vars_}

    # Auth detection
    auth_header = "Jwt-Identity"
    needs_auth = auth_header in keys
    auto_mint_mode = "basicAuth" in keys

    # Per-item checks
    referenced: set[str] = set()
    items_missing_auth: list[int] = []
    items_cursor_with_filters: list[tuple] = []
    host_vars_per_item: list[tuple] = []
    HOST_VAR_RE = re.compile(r"\{\{(localhost|staginghost|devhost)\}\}")

    for i, it in enumerate(d["item"]):
        assert "name" in it and "request" in it, f"item[{i}] missing name or request"
        u = it["request"].get("url")
        assert isinstance(u, dict) and "raw" in u and "host" in u and "path" in u, \
            f"item[{i}].request.url must be object with raw/host/path"

        referenced.update(re.findall(r"\{\{(\S+?)\}\}", json.dumps(it)))

        item_name = it.get("name", "")
        is_missing_auth_test = (
            f"missing {auth_header}" in item_name
            or "missing jwt-identity" in item_name.lower()
        )

        if needs_auth and not is_missing_auth_test:
            headers = {h["key"] for h in it["request"].get("header", [])}
            if auth_header not in headers:
                items_missing_auth.append(i)

        host_str = " ".join(u.get("host", []))
        m = HOST_VAR_RE.search(host_str)
        if m:
            host_vars_per_item.append((i, item_name, m.group(1)))

        query_keys = {q.get("key") for q in u.get("query", []) if isinstance(q, dict)}
        if "cursor" in query_keys and (query_keys & {"orderBy", "teamName"}):
            items_cursor_with_filters.append((i, item_name, sorted(query_keys)))

    # All referenced vars declared
    missing_vars = referenced - keys
    assert not missing_vars, f"items reference undeclared vars: {missing_vars}"

    # All items use the same host var
    host_choices = {h for _, _, h in host_vars_per_item}
    assert len(host_choices) <= 1, \
        f"items use mixed host vars (breaks runner): {sorted(host_choices)}\n" \
        f"  offenders: {host_vars_per_item}"

    # cursor + orderBy/teamName are mutually exclusive
    assert not items_cursor_with_filters, \
        f"cursor is mutually exclusive with orderBy/teamName: {items_cursor_with_filters}"

    if needs_auth:
        assert not items_missing_auth, \
            f"items missing `{auth_header}` header (add it or mark as missing-auth test): {items_missing_auth}"

        if auto_mint_mode:
            events = d.get("event", [])
            assert any(e.get("listen") == "prerequest" for e in events), \
                "`basicAuth` present (auto-mint) but no collection-level prerequest event"
            script_text = json.dumps(events)
            assert "toLowerCase()" in script_text, \
                "auto-mint script must use case-insensitive `h.key.toLowerCase()` match"
            assert "pm.collectionVariables" in script_text, \
                "auto-mint script must use pm.collectionVariables, not pm.environment"
            assert "timeout" in script_text, \
                "auto-mint script must set explicit timeout on pm.sendRequest"

    # No pm.environment usage anywhere
    full_dump = json.dumps(d)
    assert "pm.environment.set" not in full_dump and "pm.environment.get" not in full_dump, \
        "use pm.collectionVariables.set/get — pm.environment.* is a no-op when no env is selected"

    mode_label = "auto-mint" if auto_mint_mode else "manual JWT" if needs_auth else "no auth"
    host_label = list(host_choices)[0] if host_choices else "none"
    print(
        f"OK — {len(d['item'])} items, {len(vars_)} vars, "
        f"all {{{{var}}}} refs resolved, auth: {mode_label}, host: {{{{{host_label}}}}}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <collection.json>", file=sys.stderr)
        sys.exit(1)

    try:
        validate(sys.argv[1])
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
