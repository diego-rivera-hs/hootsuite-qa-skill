# hootsuite-qa-skill

Cursor skill + agent for generating QA artifacts from a branch diff. Six modes, derived from `master...HEAD`, zero padding.

## What it does

| Mode | Output | Use when |
|---|---|---|
| `QA-scenarios` | Numbered list in chat | Quick scenario review without a file |
| `QA-notes` | `.md` expanded | QA docs that live in the repo |
| `QA-guide` | `.md` vital checklist (5–7 items) | Hand-off to another dev |
| `QA-postman` | `.postman_collection.json` | You have Postman |
| `QA-requests` | curl / URL+body / `.http` / HTTPie | Other tooling |
| `QA-description` | PR body markdown | PR description only |

---

## Install

### Option A — Cursor user skill (recommended, available across all projects)

```bash
mkdir -p ~/.cursor/skills/qa-testing
cp SKILL.md ~/.cursor/skills/qa-testing/SKILL.md
```

Cursor picks it up automatically. Trigger with `qa-testing` or any mode alias in chat.

### Option B — Project-level agent (available in one workspace via `@qa-testing`)

```bash
mkdir -p /your/project/.cursor/agents
cp .cursor/agents/qa-testing.mdc /your/project/.cursor/agents/qa-testing.mdc
```

Use `@qa-testing QA-guide` in the Cursor chat for that project.

---

## Usage

Just type the mode in chat:

```
QA-scenarios
QA-guide
QA-postman
QA-notes
QA-requests
QA-description
qa-testing          ← shows mode menu
```

The skill detects the ticket key from the branch name, runs the diff, reads the relevant source files, and generates the artifact.

---

## Tools

### `tools/validate-postman.py`

Validates a generated Postman collection before handing it to the dev. The agent calls this automatically after `QA-postman`.

```bash
python3 tools/validate-postman.py path/to/TICKET.postman_collection.json
```

Checks: schema placement, variable declarations, auth headers on all items, consistent host var, cursor/filter mutual exclusion, no `pm.environment.*`.

---

## Service support

| Repo | Type | Auth |
|---|---|---|
| `service-organization` | TOPS (Scala/Play) | Per `application.conf` |
| `organization-management` | BFF (Go/chi) | Aperture `Jwt-Identity` via `basicAuth` (base64 email:password) |

For BFF collections the agent will ask your preferred auth strategy (manual JWT paste vs auto-mint) and explain how to generate `basicAuth`.

---

## File structure

```
hootsuite-qa-skill/
├── SKILL.md                        ← Cursor user skill (full spec)
├── .cursor/
│   └── agents/
│       └── qa-testing.mdc         ← Project-level agent (compact, references SKILL.md)
├── tools/
│   └── validate-postman.py        ← Postman collection validator
└── README.md
```

---

## Updating

Pull latest and re-copy `SKILL.md` to `~/.cursor/skills/qa-testing/SKILL.md`.

```bash
git pull
cp SKILL.md ~/.cursor/skills/qa-testing/SKILL.md
```
