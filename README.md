# glendonize

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

```sh
npx skills@latest add bobocs50/glendonize
```

A Claude Code skill that gives a repository the structure several AI coding agents need to
work in it safely: a working agreement, a numbered register of requirements, decisions and
open questions that code cites, boundary checks that read source as text, and a gate made
only of free commands. It installs them one gated phase at a time and writes nothing it
cannot trace to a line in your repo.

The whole skill is one file: [`skills/glendonize/SKILL.md`](skills/glendonize/SKILL.md).

## Why

Agents fail in predictable ways. Each mechanism exists to stop one of them.

| Failure | Mechanism | What it looks like |
|---|---|---|
| An agent invents a plausible reason for a rule nobody explained | Decision register; a rule with no recorded reason gets `Rationale: not recorded` | The README says "never retry uploads". The register gets `D-004 — Uploads are not retried. Rationale: not recorded`, not "to avoid duplicate charges", which nobody said |
| An agent runs a script that bills per call | Free-only gate: a confirmed deny-list, and CI that holds no secrets | `parse.py` bills per page. It is deny-listed, and with no `secrets:` in the workflow a paid call cannot succeed even by accident |
| Code cites a rule that was renamed or never written | Citation resolvability check | A comment says `(D-017)`, or `docs/OPERATIONS.md 2.4` became 2.5. The check fails and prints `src/retry.py: D-017` |
| Boundary rules live only in prose | Boundary checks that read source as text and never import it | "Only `client.py` may reach the network." The check fails unless the set of files calling `requests.get` / `urlopen` is exactly `["src/client.py"]` |
| A vendor fact is repeated as if it were checked | `PLATFORM_CONSTRAINTS.md`, every entry VERIFIED (source linked) or ASSERTED | "The API allows 60 requests per minute. ASSERTED." It stays that way until someone reads the vendor page and links it |
| A missing decision is filled with a guess | Parking: stop that branch, open a `Q-` entry, continue the rest | "Should expired tokens refresh silently?" becomes `Q-003` with what is known and who settles it; the refresh code waits |
| A new module lands without a test | Pairing ratchet over a tracked `untested.txt` | 40 files have no test today and are listed. `src/export.py` arrives untested and unlisted, so the check fails. The list only shrinks |

Why a ratchet and not "every file must have a test": a hard 1:1 rule fails on day one and
gets muted. Why read source as text: an import can execute code, and that code might call
something paid; a file that is only read cannot spend money.

## What you get

| File | What it is |
|---|---|
| `AGENTS.md` | The working agreement every agent reads: citation, review, parking, gates, working loop. Capped at 8 KiB |
| `CLAUDE.md` | Imports `@AGENTS.md`; restates none of its rules |
| `docs/REQUIREMENTS.md`, `docs/DECISIONS.md` | `R1`…, `D-001`…, each with a source; rationale quoted or `not recorded` |
| `docs/OPEN_QUESTIONS.md` | `Q-001`…: what is known and the exact act that would settle it |
| `docs/PLATFORM_CONSTRAINTS.md` | External facts, each VERIFIED or ASSERTED |
| `docs/README.md` + docs | An owner index (Owns / Does not own / Update when) and the numbered docs it lists |
| Boundary checks | `scripts/boundary_check.py`, `test_boundary.py` or a colocated `boundary.test.ts`, depending on the stack |
| The gate | The free commands run before every commit, as `.github/workflows/verify.yml` or a local script |
| `tests/untested.txt` | With a test runner: the ratchet list |

## Install

```sh
npx skills@latest add bobocs50/glendonize
```

Pick which coding agents to install it on. It writes the skill as an ordinary file you own
and can edit; pull later changes with `npx skills update`.

Or as a Claude Code plugin, from inside a session:

```
/plugin marketplace add bobocs50/glendonize
/plugin install glendonize@glendonize
```

Or by hand, user-level on macOS / Linux:

```sh
mkdir -p ~/.claude/skills/glendonize && curl -fsSL https://raw.githubusercontent.com/bobocs50/glendonize/main/skills/glendonize/SKILL.md -o ~/.claude/skills/glendonize/SKILL.md
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills\glendonize" | Out-Null; Invoke-WebRequest https://raw.githubusercontent.com/bobocs50/glendonize/main/skills/glendonize/SKILL.md -OutFile "$HOME\.claude\skills\glendonize\SKILL.md"
```

## Run

In Claude Code:

```
/glendonize               # the current repo
/glendonize path/to/repo
```

Installed as a plugin, the command is namespaced: `/glendonize:glendonize`. Either way it
also triggers on "make this repo agent-ready" or a request for a decision register,
constraints doc, boundary checks or a gate.

## A first run

Take `invoicer`, a small made-up Python repo with pytest, a `scripts/summarize.py` that
calls an LLM, and a `CLAUDE.md` holding a few rules. Phase 0 writes only `AGENT_READY.md`
(kept out of git through `.git/info/exclude`) and reports:

- **Stack:** Python with pytest. 9 of 14 source files have a `tests/test_x.py`; the other 5
  become the ratchet's baseline.
- **Deny-list candidates, with provenance:** `scripts/summarize.py`, because
  `README.md:41` says "costs a few cents per invoice" and line 7 reads `OPENAI_API_KEY`.
  `invoicer/fx.py` reads `FX_API_TOKEN` and nothing says whether that is paid, so it is
  treated as paid.
- **Rules:** "never round before summing line items" (`CLAUDE.md:9`, reason on line 10)
  and "amounts are stored in cents" (`README.md:58`, no reason given, so it will read
  `Rationale: not recorded`).
- **Parked:** `TODO(user): which rate source is authoritative?` becomes a `Q-` candidate.
- **One conflict brief:** `CLAUDE.md` holds rules of its own; the plan moves them into
  `AGENTS.md` and leaves `CLAUDE.md` as `@AGENTS.md`. Both sides are quoted. Your ruling?

Nothing moves until every conflict has a ruling and every list is approved. Then each phase
is committed on its own once its gate passes.

## Phases

| # | Phase | Adds |
|---|---|---|
| 0 | Survey | Stack, free vs paid steps, bans, candidates with `file:lines`, conflicts, blockers. Writes only the state file |
| 1 | Unblock | `.claude/worktrees/` ignored; `CLAUDE.md` imports `AGENTS.md` |
| 2 | Register | `REQUIREMENTS.md` and `DECISIONS.md` from confirmed candidates only |
| 3 | Working agreement | `AGENTS.md`, keeping your existing text verbatim |
| 4 | Parking and constraints | `OPEN_QUESTIONS.md`, `PLATFORM_CONSTRAINTS.md`; optionally mirrors open questions as issues |
| 5 | Boundary checks | One per confirmed boundary, plus citation resolvability and the ratchet. Must pass on day one |
| 6 | Gate | The free-only command list, in CI or a local script; dependencies proven in a fresh environment built from `git archive` |
| 7 | Docs | The owner index first, then the numbered docs it lists |
| 8 | Close | Summary and open questions; deletes the state file |

Phase 0 tells you which phases add something to your repo; the rest can be skipped.

## What it will not do

- **Write to your repo on the first pass.** Phase 0 is a survey; its only output is the
  local state file.
- **Invent requirements, decisions or facts.** Every entry names the file and lines it came
  from and is confirmed by you. What cannot be settled becomes a `Q-` entry.
- **Proceed without you.** Every phase ends at a gate you approve. Every conflict with your
  `AGENTS.md`, `CLAUDE.md` or README is put to you, and your ruling is recorded as a dated
  decision so the next agent does not argue it again.
- **Run paid scripts.** A step joins the gate only if the survey shows it reads no billing
  credential and makes no billable call. In doubt, it counts as paid. Paid scripts refuse to
  run without their key and record `skipped`, never a pass.
- **Replace your linter or push on its own.** Each phase is committed with its own files
  only (never `git add -A`); pushing waits until you ask.

## Supported stacks

| Stack | Support |
|---|---|
| Python, with or without pytest | Full; the ratchet needs a test runner |
| TypeScript, with or without vitest/jest | Full; colocated `boundary.test.ts` when a runner exists |
| Python and TypeScript together | One checker covering both, one gate job per side |
| Go, Rust, JVM, others | Rules, register, parking and docs only, and the skill says so |

## FAQ

**Does it change my code?** Not its behaviour. Phases 0–6 write docs, config and checks. In
Phase 7, citations your code already has are upgraded to the `docs/X.md N.N` form and ids
are added to existing test labels. Your own prose is never rewritten or renumbered.

**What if I already have `AGENTS.md` or `CLAUDE.md`?** They are read in full and treated as
raw material, never overruled. Existing text is kept verbatim. If the structure is already
there, the skill says so and offers only the phases that add something.

**Can I stop halfway?** Yes. `AGENT_READY.md` records progress, `HEAD` and your rulings word
for word. Run `/glendonize` again: it checks what changed, names the first unfinished phase
and asks whether to resume or discard. It never re-asks a ruling.

**Does it work with Codex or other agents?** The output does: `AGENTS.md` is
agent-agnostic. The skill itself runs in Claude Code, because it uses its question prompts
and subagents.

## Also in this repo: grilling

[`skills/grilling/SKILL.md`](skills/grilling/SKILL.md) interviews you about a plan one round
of questions at a time, mapped as a design tree, until every decision is settled. On top of
the plain grilling it has a learning mode: you state the problem and your own approach first,
it teaches a missing concept on a small made-up example instead of handing you its design,
and at the end it records what you demonstrated in `~/.claude/learning/`. Triggers on
"grill me" or `/grilling`.

```sh
npx skills@latest add bobocs50/glendonize --skill grilling
```

When a grilling reaches a structure decision (a new layer, step, data shape or boundary),
you draw the first sketch and the skill grills the drawing before it draws an alternative
beside yours.

## Also in this repo: whiteboard

[`skills/whiteboard/SKILL.md`](skills/whiteboard/SKILL.md) opens a Mermaid flowchart as a
full-screen, hand-drawn, editable whiteboard in your browser: one dark board, the drawing
toolbar, Save and Done, nothing else. `serve.py` (Python standard library, local only)
serves `board.html` (Excalidraw from a CDN) with your `.mmd` converted in the browser;
Done writes a PNG and the scene next to the `.mmd` and exits, so the agent reads what you
drew. Reopening the same `.mmd` loads your saved layout. The Mermaid stays the record.
Triggers on `/whiteboard`, "draw it" or "sketch this"; nothing to install beyond Python.

```sh
npx skills@latest add bobocs50/glendonize --skill whiteboard
```

## Credits

Named after and inspired by the repo structure of glendonC
([github.com/glendonC](https://github.com/glendonC)), e.g. his public repo
[1321](https://github.com/glendonC/1321).

`grilling` builds on the grilling skill in Matt Pocock's
[skills](https://github.com/mattpocock/skills) (MIT); its learning mode is modelled on
[nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise).

## License

MIT. See [LICENSE](LICENSE).
