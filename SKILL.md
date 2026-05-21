---
name: qa-testing
description: >-
  Generate QA artifacts for a ticket about to enter QA handoff. Six modes
  derived from `master...HEAD`: QA-scenarios (in-chat full coverage list),
  QA-notes (.md with expanded explanations), QA-guide (.md vital-only
  checklist for another dev), QA-postman (.postman_collection.json with
  pm.test scripts), QA-requests (sample-driven request set in curl /
  .http / HTTPie / markdown / any format the dev pastes), QA-description
  (PR body: ticket, goal, changes, behavior, optional risks, Postman path
  if generated — not step-by-step QA; that is `QA-guide` / other modes). Use when the user says "QA-scenarios",
  "QA-notes", "QA-guide", "QA-postman", "QA-requests", "QA-curl",
  "QA-http", "QA-description", "QA notes", "QA scenarios", "QA guide",
  "QA postman", "PR description", or asks for QA documentation, postman
  tests, curl scripts, http files, or a PR body for a ticket they just
  finished. Also use — without picking a mode — when the user says just
  "qa-testing", "QA-testing", "QA testing", "qa", or anything ambiguous
  like "QA for this ticket" / "give me QA stuff": render the mode menu
  and ask which one to use (see "Disambiguation" section).
---

# QA Testing

Six modes, same discovery base (branch diff vs master), different output.

## Modes

| Mode | Output | Depth | Destination |
|---|---|---|---|
| `QA-scenarios` | Chat | Full coverage | — |
| `QA-notes` | `.md` | Medium, expanded | `docs/` → `.idea/tickets/` → ask |
| `QA-guide` | `.md` | Vital-only checklist | `docs/` → `.idea/tickets/` → ask |
| `QA-postman` | `.postman_collection.json` | Full + `pm.test` | Ask dev → project root |
| `QA-requests` | curl / URL-for-Postman / `.http` / other | Full coverage | Ask dev → project root |
| `QA-description` | Chat | Minimal PR body | — |

## Disambiguation

When invoked without a mode (e.g. `qa-testing`, `qa`, "QA for this ticket"), show this table and ask. Do NOT run discovery yet.

| Mode | Output | When to use |
|---|---|---|
| `QA-scenarios` | Numbered list in chat | See scenarios without writing a file |
| `QA-notes` | `.md` with explanations + screenshot slots | QA docs that live in the repo |
| `QA-guide` | `.md` vital-only checklist (5–7 items) | Hand-off so another dev runs QA quickly |
| `QA-postman` | `.postman_collection.json` with `pm.test` | You have Postman and want an importable collection |
| `QA-requests` | curl / URL-for-Postman / `.http` / HTTPie / fetch | You prefer other tooling or a quick paste |
| `QA-description` | Paste-ready PR markdown | Short PR text only — not scenario checklists |

Ask "Which one do you want?" Wait for answer before doing anything else.

## Shared workflow

### Step 1 — Ticket key

`git rev-parse --abbrev-ref HEAD`. Extract ticket key (e.g. `TOPS-1234`). If none, ask.

### Step 2 — Diff

```bash
BASE=$(git merge-base origin/master HEAD 2>/dev/null || git merge-base origin/main HEAD)
git diff "$BASE"...HEAD --stat
git diff "$BASE"...HEAD
# Uncommitted work: git diff "$BASE" --stat && git diff "$BASE"
```

Extract: routes/endpoints, validations, DB changes, dark launch flags, DAO/service additions.

### Step 3 — Read source files

Before writing any URL, body, or field name — read the model and route files from the diff. Match field names verbatim.

#### Step 3a — Discover real HTTP URL

Don't trust OpenAPI path alone. Find:

1. **Router prefix** — `router.Route`, `router.Mount`, `pathPrefix`, `server.servlet.context-path`.
2. **Port** — read `config/**/config.yml` or `application.conf`. Don't assume `8080`.
3. **Auth prefix** — `/v2/`, `/api/`, `/public/` sub-routes.
4. **Error shape** — read the error handler (`ErrorHandler`, `ExceptionMapper`). Know the actual JSON: `{code, message}`, `{errors:[...]}`, etc.
5. **Status code mapping** — find the error→HTTP mapper (`simplerr.Code`, `@ResponseStatus`, custom `ApiError`).
6. **Auth headers** — read auth middleware:
   - **Hootsuite aperture (BFF `organization-management`, most BFFs)**: requires `Jwt-Identity`. Minted via `POST https://aperture-authz.staging.hootops.com/authz/basic` with `Authorization: Basic <base64(email:password)>` + `{"ttl":60}`. JWT comes back in `Jwt-Identity` response header.
   - **OAuth**: `Authorization: Bearer <token>`.
   - **Custom session**: `Cookie: session=...`.

Every URL must use the **full path** as the dev will hit it. If OpenAPI says `/foo` and router mounts under `/public`, URL is `{{localhost}}/public/foo`.

Decide prefix handling: if stable across envs → hardcode in paths, `{{localhost}}` = host+port only. If per-env → fold into `{{baseUrl}}`.

#### Step 3b — Detect service type

Check repo root / folder name:

- **`service-organization`** → TOPS (direct Scala/Play service).
- **`organization-management`** → BFF (Go/chi, aperture `Jwt-Identity` + `X-As-Member-Id`, variables-heavy collection).

This drives QA-postman collection shape (see mode section).

### Step 4 — Pre-requisites

Include what applies:

- **DL flag**: name, file path, exact config line, value per phase.
- **DB migration**: SQL file path.
- **Service**: start command + port.
- **Variables**: `{{localhost}}`, `{{memberId}}`, `{{organizationId}}`, etc.

### Step 5 — Build scenarios

Cover at minimum:

- Happy path per new endpoint/category/param.
- Gating regression (DL OFF: old behavior intact).
- Gating enabled (DL ON: new behavior visible).
- Negative validation: invalid/missing/wrong-type input.
- DB persistence: `SELECT` verifying the row.
- Delete/cleanup path if supported.

**Derive scenarios directly from the diff.** Don't invent scenarios for code not touched. If you spot a plausible edge case not explicitly in the diff, add it as `(optional)`.

DL present → split into **Phase 1 — DL OFF** / **Phase 2 — DL ON** with flip instruction between. No DL → flat list.

#### Pagination (cursor + filters are mutually exclusive)

- **Page 1**: send `limit` + `orderBy` + filters. Capture `metadata.collectionInfo.next.cursor`.
- **Page 2+**: send `limit` + `cursor` ONLY. No `orderBy` or filters — cursor encodes them.

Verify in the downstream controller before pinning this pattern.

#### BFF enum casting

`openapi-generator` chi templates cast enum params without validation (`orderByParam := TeamOrderBy(query.Get("orderBy"))`). "Invalid enum → 4xx" tests probe the **downstream** parser. Read it before picking the invalid value — some strings parse fine due to `split("_")` logic. Assertions: `4xx` + generic `{code, message}`.

---

## `QA-scenarios` (chat)

Derive scenarios strictly from the diff. Each scenario: **5–6 word label**, URL, body (if any), one-line expected. Mark spotted edge cases as `(optional)`.

```markdown
**Pre-requisites**
- DL: `<file>` → `<exact-line>` (Phase 1: `value: false`, Phase 2: flip)
- DB: apply `<sql-file>` on `<schema>`
- Service: `<command>` (port `<port>`)
- Vars: `{{localhost}}`, `{{memberId}}`, …

**Phase 1 — DL OFF**

1. **<5–6 word label>**
   - `<METHOD> {{localhost}}/<path>`
   - body: `<json>` (omit if none)
   - expected: `<status>` + `<key signal>`

**Phase 2 — DL ON** (restart after flip)

3. ...
```

No DL → drop phases, flat numbered list.

---

## `QA-notes` (.md)

Destination: `docs/` → `.idea/tickets/` → ask. File: `<TICKET>-QA-notes.md`.

Like `QA-scenarios` but adds a one-sentence "why" per scenario and DB/side-effect verification. No padding — keep it scannable.

````markdown
# <TICKET> — QA notes

## Pre-requisites

- **DL**: `<file>` → `<exact-line>` (Phase 1: `false`, Phase 2: `true`).
- **DB**: apply `<sql-file>` on `<schema>`.
- **Service**: `<command>` (port `<port>`).
- **Vars**: `{{localhost}}`, `{{memberId}}`, …

---

## Phase 1 — DL OFF

### 1. <Short label>

<One sentence: what this exercises.>

`<METHOD> {{localhost}}/<path>`

```json
<body — omit if none>
```

**Expected**: `<status>` · <response signal> · <DB check if relevant>

**Evidence**: _paste snippet_

---

## Phase 2 — DL ON (restart after flip)

...
````

No DL → single section.

---

## `QA-guide` (.md, checklist)

Destination: same picker. File: `<TICKET>-QA-guide.md`.

**Vital-only, 5–7 bullets max.** Pick scenarios that prove the contract change works. Skip routine validations (400 on non-numeric id, 401 on missing auth, generic 404) — unit tests cover those.

Each bullet: **label** — `METHOD path?params` — `status` + key signal — `_Postman item N._`

No body (unless body is the point). No URL host in bullet text. No sign-off section.

Template (no DL):

```markdown
# <TICKET> — QA guide

**Setup**: `make run` (port `<port>`). No DL. Postman: `<path>/<TICKET>.postman_collection.json`.

<1–2 sentences of context.>

---

- [ ] **1. <label>** — `GET {{localhost}}/<path>?<param>={{val}}` — `<status>` + <key signal>. _Postman item 1._
- [ ] **2. <label>** — `POST {{localhost}}/<path>` — `<status>` + <key signal>. _Postman item 2._
```

Template (with DL):

```markdown
# <TICKET> — QA guide

**Setup**: in `<dl-file>` set `<exact-line value: false>` for Phase 1; flip to `true` + restart for Phase 2. Postman: `<path>/<TICKET>.postman_collection.json`.

## Phase 1 — DL OFF

- [ ] **1. <label>** — `<METHOD> {{localhost}}/<path>` — `<status>` + <signal>. _Postman item N._

## Phase 2 — DL ON

- [ ] **2. <label>** — `<METHOD> {{localhost}}/<path>` — `<status>` + <signal>. _Postman item N._
```

Chain across two items → `_Postman items 4 → 5._`

If a vital scenario is missing from the collection — add the Postman item first, don't paper over it with a "manual" note.

---

## `QA-postman` (collection)

### Detect service type first

- **`service-organization`** (TOPS): Scala/Play direct service. Check `application.conf` for port and auth config. No BFF variable layer.
- **`organization-management`** (BFF): Go/chi. Uses aperture `Jwt-Identity` + `X-As-Member-Id`. Variables-heavy. Prompt for `basicAuth`.

### For BFF (`organization-management`) — auth setup

Tell the dev upfront:

> Para autenticar los requests, la colección usa `basicAuth` — tu email y contraseña de Hootsuite **codificados en base64**.
> Generalo con: `printf '%s' 'tu@hootsuite.com:tupassword' | base64`
> Pegá el resultado en el **Current Value** de la variable de colección `basicAuth`.

Then ask which auth strategy:

```
A) Manual JWT  — pegás el JWT en la variable `Jwt-Identity` (refrescás cada ~30 min).
B) Auto-mint   — el pre-request script lo mintea automáticamente usando tu `basicAuth`.
```

Use `AskQuestion`. Default: **A (manual)** — zero moving parts, works on every Postman install.

Also ask default host:

```
A) {{localhost}}   — make run local (default)
B) {{staginghost}} — staging desplegado
C) {{devhost}}     — dev desplegado
```

Default: **A**. Bake chosen host into every item. Don't mix hosts.

### Collection structure

- `info.name`: `"<resource> Tests (<TICKET>)"`.
- `info.description`: every env var, REQUIRED vs AUTO, auth notes.
- `info.schema`: `"https://schema.getpostman.com/json/collection/v2.1.0/collection.json"` — **inside `info`**, not top-level.
- `item`: flat list. Names: `"1. Happy - <case>"` / `"8. Error - <case> -> <status> <ErrorName> (<code>)"`.

Top-level skeleton:

```json
{
  "info": {
    "_postman_id": "<ticket-slug>",
    "name": "<resource> Tests (<TICKET>)",
    "description": "<vars + prereqs + auth notes>",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "event": [{ "listen": "prerequest", "script": { "type": "text/javascript", "exec": ["// token minting if auto-mint"] } }],
  "variable": [
    { "key": "localhost", "value": "http://localhost:<port>", "type": "string", "description": "Service base URL." },
    { "key": "<required>", "value": "", "type": "string", "description": "REQUIRED. <what to put>." },
    { "key": "<auto>", "value": "", "type": "string", "description": "AUTO. Populated by item N, consumed by item M." }
  ],
  "item": []
}
```

### Pre-request token minting

#### Strategy A — Manual JWT

No pre-request script. Dev pastes JWT in `Jwt-Identity` collection variable (Current Value).

```json
{
  "key": "Jwt-Identity",
  "value": "",
  "type": "string",
  "description": "REQUIRED. Paste JWT here (Current Value). Mint: curl -s -X POST https://aperture-authz.staging.hootops.com/authz/basic -H 'Authorization: Basic <base64>' -H 'Content-Type: application/json' -d '{\"ttl\": 1800}' -D - -o /dev/null | awk 'tolower($1)==\"jwt-identity:\"{print $2}' | tr -d '\\r\\n' | pbcopy && echo copied. Refresh every 30 min."
}
```

#### Strategy B — Auto-mint (only when dev opts in)

```json
"event": [
  {
    "listen": "prerequest",
    "script": {
      "type": "text/javascript",
      "exec": [
        "const basicAuth = pm.collectionVariables.get('basicAuth');",
        "if (!basicAuth || basicAuth.indexOf('<') === 0) { throw new Error('Set `basicAuth` (base64 email:password) in collection Variables.'); }",
        "const url = pm.request.url.toString();",
        "const isDev = url.includes('dev.hootdev.com') || url.includes('{{devhost}}');",
        "const env = isDev ? 'dev' : 'staging';",
        "const apertureUrl = isDev ? 'https://aperture-authz.dev.hootdev.com/authz/basic' : 'https://aperture-authz.staging.hootops.com/authz/basic';",
        "const cacheKey = 'Jwt-Identity-' + env;",
        "const cacheExpKey = 'Jwt-Identity-Exp-' + env;",
        "const cached = pm.collectionVariables.get(cacheKey);",
        "const cachedExp = parseInt(pm.collectionVariables.get(cacheExpKey) || '0', 10);",
        "const nowSec = Math.floor(Date.now() / 1000);",
        "if (cached && cached.length > 50 && cachedExp > nowSec + 60) { pm.collectionVariables.set('Jwt-Identity', cached); return; }",
        "pm.sendRequest({ url: apertureUrl, method: 'POST', header: { 'Authorization': 'Basic ' + basicAuth, 'Content-Type': 'application/json' }, body: { mode: 'raw', raw: JSON.stringify({ ttl: 1800 }) }, timeout: 10000 }, function (err, res) {",
        "    if (err) { throw new Error('aperture-authz ' + env + ' failed: ' + err.message); }",
        "    if (res.code !== 200) { throw new Error('aperture-authz ' + env + ' returned ' + res.code); }",
        "    const jwtHeader = res.headers.find(h => h.key.toLowerCase() === 'jwt-identity');",
        "    if (!jwtHeader) { throw new Error('No jwt-identity header in aperture response.'); }",
        "    const jwt = jwtHeader.value;",
        "    let exp = nowSec + 1800;",
        "    try { const p = JSON.parse(atob(jwt.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'))); if (p.exp) exp = p.exp; } catch(e) {}",
        "    pm.collectionVariables.set(cacheKey, jwt); pm.collectionVariables.set(cacheExpKey, String(exp)); pm.collectionVariables.set('Jwt-Identity', jwt);",
        "});"
      ]
    }
  }
]
```

Required vars for auto-mint:

| Var | Role |
|---|---|
| `basicAuth` | REQUIRED. `base64(email:password)`. Current Value only. |
| `Jwt-Identity` | AUTO. Active JWT. |
| `Jwt-Identity-staging` / `Jwt-Identity-dev` | AUTO. Cached per env. |
| `Jwt-Identity-Exp-staging` / `Jwt-Identity-Exp-dev` | AUTO. Unix exp epoch. |

**Critical (already in snippet):**
- Case-insensitive header match: `h.key.toLowerCase()`.
- `pm.collectionVariables` everywhere — `pm.environment.set` is no-op with no env selected.
- TTL caching with `exp` from JWT payload.
- `timeout: 10000` on `pm.sendRequest`.
- Throw on every error path.
- Local service uses **staging** JWT key (check `config/local/config.yml`).

### Item structure

```json
{
  "name": "<N>. <Happy|Error> - <case>",
  "event": [{
    "listen": "test",
    "script": {
      "type": "text/javascript",
      "exec": [
        "pm.test('Status 200', () => pm.response.to.have.status(200));",
        "const json = pm.response.json();",
        "pm.test('Has data array', () => pm.expect(json.data).to.be.an('array'));"
      ]
    }
  }],
  "request": {
    "method": "GET",
    "header": [
      {"key": "Jwt-Identity", "value": "{{Jwt-Identity}}"},
      {"key": "X-As-Member-Id", "value": "{{adminMemberId}}"}
    ],
    "url": {
      "raw": "{{localhost}}/<path>?<k>={{<v>}}",
      "host": ["{{localhost}}"],
      "path": ["<seg>", "<seg>"],
      "query": [{"key": "<k>", "value": "{{<v>}}"}]
    }
  },
  "response": []
}
```

POST/PATCH/PUT/DELETE: add `body` block + `Content-Type: application/json` header.

For "missing Jwt-Identity → 401" item: add item-level prerequest that sets `pm.collectionVariables.set('Jwt-Identity', '')` to override collection pre-request. Assert status only — aperture returns `Content-Length: 0`, no JSON body.

**Tests that don't belong:**
- "Missing `X-As-Member-Id` → 401" — act-as header, not auth. Missing it with valid JWT → 200.
- "Wrong basic auth → 401" — tests aperture-authz, not the service.

### Validate before reporting ready

```bash
python3 - <<'PY'
import json, re
d = json.load(open("<path>"))
assert set(d.keys()) <= {"info", "item", "auth", "event", "variable"}, f"unexpected top-level keys: {set(d.keys())}"
assert "info" in d and "item" in d
assert "schema" in d["info"]
assert d["info"]["schema"].endswith("v2.1.0/collection.json")
assert "schema" not in d
vars_ = d.get("variable", [])
assert vars_, "missing variable array"
keys = {v["key"] for v in vars_}
auto_mint_mode = "basicAuth" in keys
auth_header = "Jwt-Identity"
needs_auth = auth_header in keys
referenced = set()
items_missing_auth = []
items_cursor_with_filters = []
host_vars_per_item = []
HOST_VAR_RE = re.compile(r"\{\{(localhost|staginghost|devhost)\}\}")
for i, it in enumerate(d["item"]):
    assert "name" in it and "request" in it, f"item[{i}] missing name/request"
    u = it["request"].get("url")
    assert isinstance(u, dict) and "raw" in u and "host" in u and "path" in u, f"item[{i}].url must have raw/host/path"
    referenced.update(re.findall(r"{{(\S+?)}}", json.dumps(it)))
    item_name = it.get("name", "")
    is_missing_auth = "missing " + auth_header in item_name or "missing jwt-identity" in item_name.lower()
    if needs_auth and not is_missing_auth:
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
missing = referenced - keys
assert not missing, f"undeclared vars: {missing}"
host_choices = {h for _, _, h in host_vars_per_item}
assert len(host_choices) <= 1, f"mixed host vars: {sorted(host_choices)}"
assert not items_cursor_with_filters, f"cursor + filters mutually exclusive: {items_cursor_with_filters}"
if needs_auth:
    assert not items_missing_auth, f"items missing {auth_header}: {items_missing_auth}"
    if auto_mint_mode:
        events = d.get("event", [])
        assert any(e.get("listen") == "prerequest" for e in events)
        script_text = json.dumps(events)
        assert "toLowerCase()" in script_text
        assert "pm.collectionVariables" in script_text
        assert "timeout" in script_text
full_dump = json.dumps(d)
assert "pm.environment.set" not in full_dump and "pm.environment.get" not in full_dump
mode_label = "auto-mint" if auto_mint_mode else "manual JWT" if needs_auth else "no auth"
print(f"OK — {len(d['item'])} items, {len(vars_)} vars, all refs resolved, auth: {mode_label}")
PY
```

After writing + validating, tell dev: file path, vars to fill (Current Value for secrets), auth setup steps, DL flag state.

---

## `QA-requests`

For devs who don't use Postman collections.

### Step 1 — Ask format preference

```
How do you want the requests?

  A) curl          — runnable bash one-liners
  B) URL + body    — paste directly into Postman (no collection file)
  C) .http file    — JetBrains / VS Code REST Client
  D) HTTPie        — terminal http tool
  E) Other         — paste a sample and I'll mirror it
```

Use `AskQuestion`. Aliases: `QA-curl` → A; `QA-http` → C; `QA-httpie` → D.

### Step 2 — Output destination

Ask for target folder; fall back to project root.

File names: curl → `<TICKET>-qa-curls.sh`; `.http` → `<TICKET>-qa.http`; HTTPie → `<TICKET>-qa-httpie.sh`; URL+body → output in chat (no file); other → mirror extension.

### Step 3 — Render

One block per scenario. Each block:
- Heading/comment: number + 5–6 word label.
- Full request (method, URL, headers, body) in chosen format.
- Expected comment: status + key signal.

`curl` template:
```bash
# 1. Happy - admin baseline
curl -sS -X GET "$LOCALHOST/v2/teams?organizationId=$ORG_ID" \
  -H "Accept: application/json" \
  -H "Jwt-Identity: $JWT"
# expected: 200 + data array.
```

`.http` template:
```http
### 1. Happy - admin baseline
GET {{localhost}}/v2/teams?organizationId={{organizationId}}
Accept: application/json
Jwt-Identity: {{Jwt-Identity}}

> {% client.test("Status 200", () => client.assert(response.status === 200)); %}
```

**URL + body (option B)** — output in chat, one block per scenario:
```
1. Happy - admin baseline
GET {{localhost}}/v2/teams?organizationId={{organizationId}}
Headers: Jwt-Identity: {{Jwt-Identity}}, X-As-Member-Id: {{memberId}}
Expected: 200 + data array.
```

### Step 4 — Tell dev

File path (or "output above" if chat), env vars to define, DL flag state.

---

## `QA-description` (chat)

PR body in chat only. **English always** — GitHub is read org-wide.

**Scope**: ticket + what changed (skip: changelog entries, version bumps, codegen churn, `go.sum`, `package-lock.json`) + behavior before/after if user-visible + risks if concrete.

**Target: ~10–20 lines.** If longer, trim.

**Never include**: pre-requisites, test scenarios, curl/Postman steps, "no breaking changes", "backward compatible", "no DB migration", "depends on upstream already merged" — obvious or noise.

**Changes bullets**: concrete code delta only. Tests: one terse bullet max, only if structurally notable (new test class, new file, new mock surface). For routine test updates: `**Tests**: updated` or omit entirely.

**Behavior section**: omit if same as Changes. Before/After only for user-visible or API contract changes. DL → Before / After (DL OFF) / After (DL ON).

**Risks**: max 2 bullets, only when concrete + non-obvious from the diff alone.

Template:

```markdown
## **Ticket**

[<TICKET>](https://hootsuite.atlassian.net/browse/<TICKET>)

## **Goal**

<1–2 sentences. Start with verb. No "This PR…">

## **Changes**

- **<Component>**: <what changed>
- **<Component>**: <what changed>

## **Behavior** *(omit if redundant with Changes)*

- **Before**: …
- **After**: …

## **Risks** *(omit if nothing concrete)*

- **<Label>**: …

## **Postman collection** *(omit if none)*

**Path**: `<path>/<TICKET>.postman_collection.json`
```

---

## Format rules (all modes)

- Variable style: Postman (`{{localhost}}`) for scenarios/notes/guide/postman. Mirror dev's style for `QA-requests`.
- Match request bodies verbatim to source model — read the file first.
- Data-writing scenarios include a `SELECT` verifying the row.
- Quote DL lines, error codes, field names verbatim from source.
- `QA-description`: English, no scenario lists, no setup steps.
