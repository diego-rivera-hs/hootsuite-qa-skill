# hootsuite-qa-skill

Skip the manual QA doc grind. Auto-generate Postman collections, test scenarios, and PR descriptions directly from your git diff — built for Hootsuite services.

---

## How it works

Finished your ticket? Just type in the Cursor chat:

```
qa-testing
```

You'll get a menu with all available modes. Pick the one you need and the skill does the rest — reads the diff, finds the real endpoints, matches field names from source, and generates the artifact.

```
Which one do you want?

  QA-scenarios   → numbered test list in chat
  QA-notes       → .md with explanations + evidence slots
  QA-guide       → vital-only checklist (5–7 items) for handoff
  QA-postman     → importable Postman collection with pm.test assertions
  QA-requests    → curl commands, URL+body for Postman, or .http file
  QA-description → paste-ready PR body
```

Or skip the menu and call the mode directly:

```
QA-guide
QA-postman
QA-description
```

---

## Modes

| Mode | Output | Best for |
|---|---|---|
| `QA-scenarios` | Numbered list in chat | Quick review before writing a file |
| `QA-notes` | `.md` with explanations + screenshot slots | QA docs that live in the repo |
| `QA-guide` | `.md` vital checklist (5–7 items) | Handing off to another dev |
| `QA-postman` | `.postman_collection.json` | You already use Postman |
| `QA-requests` | curl / URL+body / `.http` / HTTPie | Other tooling or a quick paste |
| `QA-description` | PR body markdown | Writing the PR description |

---

## Install

### Option A — Cursor user skill (recommended)

Available across all your projects automatically.

```bash
mkdir -p ~/.cursor/skills/qa-testing
cp SKILL.md ~/.cursor/skills/qa-testing/SKILL.md
```

### Option B — Project agent

Drop it into a specific project and use `@qa-testing` in that workspace.

```bash
mkdir -p /your/project/.cursor/agents
cp .cursor/agents/qa-testing.mdc /your/project/.cursor/agents/qa-testing.mdc
```

---

## Token efficiency

This skill is designed to be lean. It borrows principles from [caveman mode](https://github.com/hootsuite/hootsuite-cursor-plugins) — instructions to the AI are written without filler or redundant prose, so the model gets straight to the point and spends fewer tokens on boilerplate reasoning. You get the same quality output at a lower cost per run.

In practice: shorter prompts in, sharper artifacts out.

---

## Service support

| Repo | Type | Auth |
|---|---|---|
| `service-organization` | TOPS (Scala/Play) | Detected from the service config |
| `organization-management` | BFF (Go/chi) | Aperture `Jwt-Identity` — the skill asks for your `basicAuth` (base64 of `email:password`) and walks you through setup |

---

## Updating

```bash
git pull
cp SKILL.md ~/.cursor/skills/qa-testing/SKILL.md
```
