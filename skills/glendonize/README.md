# glendonize

[← all skills](../../README.md)

A Claude Code skill that gives a repository the structure several AI coding agents need to
work in it safely: a working agreement, a numbered register of requirements, decisions and
open questions that code cites, boundary checks that read source as text, and a gate made
only of free commands. It installs them one gated phase at a time and writes nothing it
cannot trace to a line in your repo.

The structure is modelled on glendonC's many-minions, with the docs rules of his public repo
[1321](https://github.com/glendonC/1321) (owner index, status block, review rule, a check
table per kind of change). You do not need either repo open: everything the skill installs
is written out in [`SKILL.md`](SKILL.md).

## Contents

- [Why](#why)
- [What you get](#what-you-get)
- [Install](#install)
- [Run](#run)
- [How it works](#how-it-works)
- [The phases](#the-phases)
- [Boundary checks and the ratchet](#boundary-checks-and-the-ratchet)
- [A first run](#a-first-run)
- [Parallel agents (optional)](#parallel-agents-optional)
- [What it will not do](#what-it-will-not-do)
- [Supported stacks](#supported-stacks)
- [Files in this folder](#files-in-this-folder)
- [FAQ](#faq)
- [Related](#related)
- [Credits](#credits)

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
| `AGENTS.md` | The working agreement every agent reads: citation, review, parking, gates, working loop. Capped at 8 KiB, because it loads into every agent's context every time |
| `CLAUDE.md` | Imports `@AGENTS.md`; restates none of its rules |
| `.gitignore` | Gains `.claude/worktrees/`, so agent worktrees are not scanned or committed |
| `docs/REQUIREMENTS.md`, `docs/DECISIONS.md` | `R1`…, `D-001`…, each with a source; rationale quoted or `not recorded` |
| `docs/OPEN_QUESTIONS.md` | `Q-001`…: what is known and the exact act that would settle it |
| `docs/PLATFORM_CONSTRAINTS.md` | External facts, each VERIFIED or ASSERTED |
| `docs/README.md` + docs | An owner index (Owns / Does not own / Update when) and the numbered docs it lists |
| Boundary checks | `scripts/boundary_check.py`, `test_boundary.py` or a colocated `boundary.test.ts`, depending on the stack |
| The gate | The free commands run before every commit, as `.github/workflows/verify.yml` or a local script (`npm run check`, or `scripts/gate.sh` + `.ps1`) |
| `tests/untested.txt` | With a test runner and tests named after source files: the ratchet list |

If the repo already uses an ADR folder, decisions are numbered `ADR-0001` instead of
`D-001`. If it keeps its prose somewhere other than `docs/` (for example `notes/`), the
skill proposes the move and asks; it does not decide it.

## Install

```sh
npx skills@latest add bobocs50/bobo-cooking-stack --skill glendonize
```

Pick which coding agents to install it on. It writes the skill as an ordinary file you own
and can edit; pull later changes with `npx skills update`.

Or as a Claude Code plugin, from inside a session. The plugin installs glendonize, grilling and
whiteboard together:

```
/plugin marketplace add bobocs50/bobo-cooking-stack
/plugin install bobo-cooking-stack@bobo-cooking-stack
```

Or by hand, user-level on macOS / Linux:

```sh
mkdir -p ~/.claude/skills/glendonize && curl -fsSL https://raw.githubusercontent.com/bobocs50/bobo-cooking-stack/main/skills/glendonize/SKILL.md -o ~/.claude/skills/glendonize/SKILL.md
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills\glendonize" | Out-Null; Invoke-WebRequest https://raw.githubusercontent.com/bobocs50/bobo-cooking-stack/main/skills/glendonize/SKILL.md -OutFile "$HOME\.claude\skills\glendonize\SKILL.md"
```

## Run

In Claude Code:

```
/glendonize               # the current repo
/glendonize path/to/repo
```

Installed as a plugin, the command is namespaced: `/bobo-cooking-stack:glendonize`. Either
way it also triggers on "glendonize this", "make this repo agent-ready", "structure it like
many-minions", or a request for a decision register, constraints doc, boundary checks or a
gate.

Requirements: a git repository. `gh` signed in is optional; without it, open questions stay
in the file and CI runs cannot be watched. Without a GitHub remote, the gate becomes a local
script instead of a workflow.

## How it works

1. **It gathers context itself.** It runs `git` (top level, branch, remotes, `HEAD`, status,
   worktrees), lists the instruction files (`AGENTS.md`, `CLAUDE.md`, `README.md`,
   `.cursorrules`, `GEMINI.md`, `.github/copilot-instructions.md`), checks for `docs/`,
   `notes/`, `tests/`, workflows, `gh auth status`, `python` and `node`. It reads every
   instruction file in full. If you start it inside a nested worktree, it moves to the main
   one first.
2. **One rule above all: never invent.** No requirement, decision, "must not", external fact,
   dependency or doc row is written unless it was found in the repo. Every proposed entry
   names its `file:lines`, and you confirm it before it is written. What cannot be settled
   becomes a `Q-` entry; that branch stops and the rest continues. Summaries from its own
   subagents count as leads: it re-reads the file before citing it.
3. **Conflicts go to you.** If something it would add contradicts a sentence in your
   `AGENTS.md`, `CLAUDE.md` or README, it stops that branch and writes a conflict block: both
   sides quoted verbatim, an argument for each, a proposed resolution and "Your ruling?". Your
   ruling is later written into the repo as a dated `D-` entry, so the next agent finds it
   instead of arguing it again.
4. **Phase 0 surveys and writes only a state file**, `AGENT_READY.md`, kept out of git through
   `.git/info/exclude` (not `.gitignore`, so the survey changes no tracked file).
5. **Phases 1 to 8 each end at a gate.** A phase has a "Verify" step (a command or a
   check the skill runs) and then waits for your approval. "Looks fine" is not approval.
6. **Each phase is committed on its own once its gate passes**: only that phase's files
   (never `git add -A`), a one-sentence subject in your repo's style (it reads
   `git log --format=%s -20`), never `--no-verify`. Phase 0 commits nothing. It pushes only
   when you ask, and a push counts as done when `gh run watch` reports success (with no CI,
   when the local gate passes). A red run is fixed before anything else.

**Resume.** If `AGENT_READY.md` already exists, it does not restart. It compares the recorded
`HEAD` and the set of changed files with now; if either moved, it re-runs the survey in diff
mode and tells you what changed. Then it names the first unchecked phase and asks: resume
there, or discard? Rulings stored in the file are never asked again.

**Escape hatch.** If the survey finds the structure already in place and unchanged, it says
so, lists what is missing (usually the register) and offers only the phases that add
something.

## The phases

| # | Phase | What it writes | Its gate |
|---|---|---|---|
| 0 | Survey | Only `AGENT_READY.md`: stack, free vs paid steps, bans, candidates with `file:lines`, conflicts, blockers, a phase menu | You rule on every conflict and approve every list; `git status --porcelain` shows nothing new |
| 1 | Unblock | `.claude/worktrees/` in `.gitignore`; `CLAUDE.md` reduced to `@AGENTS.md` (plus at most a manual that restates no rules). You commit or explicitly accept any dirty files first | `git check-ignore .claude/worktrees` passes; `CLAUDE.md` imports `AGENTS.md` and restates none of its rules |
| 2 | Register | `docs/REQUIREMENTS.md` and `docs/DECISIONS.md` from confirmed candidates only; every Phase 0 ruling becomes a dated `D-` in your words | Every entry has an id, a sentence and a `Source:`; no id collides. The skill warns this is the expensive gate and estimates it from the count |
| 3 | Working agreement | `AGENTS.md`: your existing sentences verbatim, then the sections Citation, Reviewing a diff, Parking, Gates, Working loop. A new file opens with five "evidence-based collaboration" bullets adapted to your domain | Your old text shows as unchanged lines in the diff; the file is at most 8192 bytes; you read all of it |
| 4 | Parking and constraints | `docs/OPEN_QUESTIONS.md` (from unsettled candidates and every `TODO(user)` in code) and `docs/PLATFORM_CONSTRAINTS.md` (fixed preamble, confirmed facts, ASSERTED unless the repo already links a source). If `gh` works, it offers once to mirror open questions as issues titled `Q-nnn — <question>` | Every VERIFIED line has a URL; every `Q-` names the act that settles it |
| 5 | Boundary checks | One check per confirmed boundary, plus citation resolvability, the `AGENTS.md` size and tracking check, the secrets-free CI check if CI will exist, and the ratchet where it applies | It passes on day one; then each check is made to fail once on a planted violation in a temporary copy (never committed) |
| 6 | Gate | The ordered list of free commands, as `.github/workflows/verify.yml` or a local script | It names no deny-listed script; Phase 5 agrees; the whole gate runs green in a fresh environment built from `git archive`. Your first push is done when `gh run watch` reports success |
| 7 | Docs | `docs/README.md` (the owner index) first, then the numbered docs it lists | You approve the index rows before any doc is written; every link resolves; every written doc has numbered headings and a Status block |
| 8 | Close | A summary: files written, number of `D-` entries, open `Q-` list, what was skipped and why. Deletes `AGENT_READY.md` and its exclude line | — |

Phase 0 tells you which phases add something to your repo; the rest can be skipped.

Details worth knowing, phase by phase:

- **Phase 0, free vs paid.** Candidates for the deny-list come from prose ("costs", "bills",
  "per page", "do not run"), from code reading env vars that match `KEY|TOKEN|SECRET|ENDPOINT`,
  and from paid SDK imports. You confirm the list. A step is free only if the survey can show
  it reads no billing credential and makes no billable call; in doubt, it counts as paid. A
  free step that reaches an external host is flagged as a flakiness risk for you to rule on.
- **Phase 0, bans.** Sentences like "there is no X and don't create one" are recorded, and the
  skill never proposes the banned thing.
- **Phase 0, blockers.** A dirty working tree (the phases read files on disk, CI reads the
  commit), `.claude/worktrees/` or any folder holding a `.git` file not being ignored (every
  scan would count it twice), promised-but-empty files, no remote, `gh` not signed in.
- **Phase 2, rationale.** A rule with a reason in the source gets that reason quoted. A rule
  without one gets `Rationale: not recorded`, never a plausible reason. Ids are assigned once
  and never renumbered. A thin repo gets a short register; it is not padded.
- **Phase 6, dependencies.** The skill walks the gate scripts' imports, subtracts the standard
  library, extracts `HEAD` with `git archive` into a temporary folder, creates a fresh virtual
  environment with only those packages and runs the whole gate there. Globally installed
  packages otherwise hide a missing dependency until CI fails. The workflow holds no
  `secrets:`, uses `permissions: contents: read`, a timeout, and cancels only pull-request
  runs. A test step fails when it runs zero tests, or when a test is skipped or marked
  `.only` without a line in a tracked list of accepted skips.
- **Phase 7, docs.** The fixed rows are OVERVIEW (ending in a list of things the product does
  not claim), PRODUCT, ARCHITECTURE, PLATFORM_CONSTRAINTS, OPERATIONS, LOCAL_SETUP and the
  three register files, plus one `<DOMAIN>.md` per contract that several parts of the code
  honour. With many rows it writes them with one agent per row. Each doc carries a Status
  block with the commit it was checked against, not a date. Code then cites
  `docs/X.md 2.7` (path and section number).

## Boundary checks and the ratchet

A **boundary check** is a small script (or test) that reads your source files as plain text
and fails when a rule about the code's shape is broken. It never imports your code, so it
cannot run anything paid. Examples of rules it can hold:

| Kind | Example rule |
|---|---|
| Forbidden prefix / allowed list | Nothing in `core/` imports from `web/` |
| Exact allow-set | Only `src/client.py` calls `requests.get` or `urlopen` |
| Private paths | `data/` is in `.gitignore` and nothing under it is tracked |
| Secrets-free CI | No workflow file mentions `secrets.` or a deny-listed script |
| Citation resolvability | Every `R3`, `D-014`, `Q-002` and `docs/X.md 2.4` cited in code or docs exists |
| Size and tracking | `AGENTS.md` is at most 8 KiB, and tracked when `CLAUDE.md` imports it |
| Counted exemptions | A legacy name may appear 10 times; the count may shrink, never grow |
| Drift | A schema defined in Python and copied by hand into TypeScript still has the same field names |

Every check starts with a **self-guard** that hard-exits if it found fewer files than
expected: a moved or emptied folder would otherwise pass every check while scanning nothing.
It skips paths relative to the repo root, so it still works from inside an agent worktree
under `.claude/worktrees/`, and it strips comments before scanning, so a comment that
explains a rule does not trip it.

Output from the Python variant looks like this:

```
  ok   .github/workflows/verify.yml holds no secrets and names no paid script
  ok   no register id is defined twice (two branches took one id)
  FAIL every cited id, doc and section resolves
         src/retry.py: D-017
  ok   AGENTS.md <= 8192 bytes

SOME FAILED
```

The **pairing ratchet** is one of these checks, installed only when the repo has a test
runner and names tests after source files (`tests/test_x.py` for `x.py`, or `x.test.ts`
beside `x.ts`). Phase 0 counts which source files have no test; that list becomes
`tests/untested.txt` (or `test-support/untested.txt`). From then on the check fails in two
cases:

- `src/export.py` has no test and is not on the list: a new module landed untested.
- `src/fx.py` is on the list but `tests/test_fx.py` now exists: remove it from the list.

So the list only shrinks. Generated, vendored and type-only files are left out by a glob you
confirm, not by the agent's judgement.

## A first run

Take `invoicer`, a small made-up Python repo with pytest, a `scripts/summarize.py` that
calls an LLM, and a `CLAUDE.md` holding a few rules. You type `/glendonize`. Phase 0 writes
only `AGENT_READY.md` and reports:

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

Nothing moves until every conflict has a ruling and every list is approved. After that, for
example, Phase 2 writes:

```markdown
## D-002 — Amounts are stored in cents
Rationale: not recorded
Rejected: not recorded
Source: README.md · Decided: <date> · Supersedes: — · Cited by: —
```

Phase 4 writes the rate-source question as `Q-001` with what the repo says and who can settle
it. Phase 5 writes a `test_boundary.py` (pytest is present) and lists the 5 untested files in
`tests/untested.txt`, and it passes. Phase 6 writes a workflow that runs pytest and the
boundary check and names `scripts/summarize.py` in its header comment as never run. Each
phase lands as its own commit.

## Parallel agents (optional)

When several agents build the structure, or later work inside it, the skill can also install
these habits:

- **A coordinator log**, `.claude/orchestration/COORDINATION.md`, gitignored. It holds
  session state (what is in flight, which worker holds what, what waits on you, findings of
  the current batch), not project truth; the register stays the truth. It is seeded with the
  real state on the day it is created, `AGENTS.md` gains one sentence saying every session
  reads it first and updates it before it stops, and a dated `D-` records why it exists.
- **Workers by role, not by file.** One builds, one verifies, one stages the next batch. Two
  workers never own the same file at once.
- **A landing rule.** One worker's output is rebased into one-behaviour commits; a parallel
  batch lands as a `--no-ff` merge with a one-sentence message.
- **Review by concern after a batch, not per feature.** Read-only agents, one concern each
  (audit, verify, edges, security), return numbered findings `F1…Fn`; each is fixed in its own
  commit citing it, `(F3)`, and kept as a test. A normal feature gets no review beyond the
  report and the gate.
- **QA only when something reached the screen or a value could move**, and the number and
  date go into the doc that owns the fact.
- **`docs/WORKFLOW.md`**, a one-page table of the loop: grill, slice, build, land, report, QA,
  and what never happens.

The working agreement it writes also says to fan out across git worktrees (one module per
agent, for example with a `/wt` skill if you have one) only for work with no open decision in
it.

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
  run without their key and record `skipped: <reason>`, never a pass.
- **Replace your linter.** Where a tool you already have can hold a boundary
  (`no-restricted-imports`, an import-linter contract), it extends that tool; a text scan is
  only for what no installed tool checks.
- **Push on its own.** It commits each phase automatically, with its own files only; pushing
  waits until you ask.
- **Rewrite your prose.** Your own docs stay where your ruling put them and are never
  rewritten, translated or renumbered.

## Supported stacks

| Stack | Detected from | Boundary checker | Ratchet |
|---|---|---|---|
| TypeScript with vitest/jest | `package.json` plus a runner config or a `"test"` script | Colocated `boundary.test.ts` | Yes, if tests are named after source files |
| TypeScript, no runner | `package.json` only | None of its own; the repo's one checker scans it as text | No |
| Python with pytest | `pyproject.toml`, `pytest.ini`, `conftest.py` or `tests/` | `test_boundary.py` beside the code | Yes, if tests are named after source files |
| Python, no runner | `.py` files only | `scripts/boundary_check.py` (standard library only) | No |
| Python and TypeScript together | Both | One checker covering both roots; one gate job per side | Per side, as above |
| Go, Rust, JVM, others | `go.mod`, `Cargo.toml`, … | None | No. Rules, register, parking and docs only, and the skill says so |

A runner is detected from config files and `scripts`, never from `devDependencies`, and the
skill installs nothing to find out.

## Files in this folder

| File | What it does |
|---|---|
| [`SKILL.md`](SKILL.md) | The whole skill: the rule it obeys, context gathering, resume, the nine phases, and the "Shapes" (templates for `AGENTS.md`, the register, the constraints doc, the CI workflow, the boundary checker in Python and TypeScript, the conflict block, the state file, the coordinator log and `WORKFLOW.md`) |
| `README.md` | This file |

## FAQ

**Does it change my code?** Not its behaviour. Phases 0–6 write docs, config and checks. In
Phase 7, citations your code already has are upgraded to the `docs/X.md N.N` form and ids
are added to existing test labels. It adds no comments in files whose style rule forbids them.
Your own prose is never rewritten or renumbered.

**What if I already have `AGENTS.md` or `CLAUDE.md`?** They are read in full and treated as
raw material, never overruled. Existing text is kept verbatim. If the structure is already
there, the skill says so and offers only the phases that add something.

**Can I stop halfway?** Yes. `AGENT_READY.md` records progress, `HEAD` and your rulings word
for word. Run `/glendonize` again: it checks what changed, names the first unfinished phase
and asks whether to resume or discard. It never re-asks a ruling.

**What if my repo has no tests?** You still get the register, parking, constraints, boundary
checks and the gate. There is no ratchet, and the survey says so.

**What if I have no GitHub remote or no CI?** The gate is held by your own runner
(`npm run check`, or `scripts/gate.sh` + `.ps1`). No `.github/` folder is a valid end state.
Without `gh`, open questions are not mirrored as issues.

**Does it work with Codex or other agents?** The output does: `AGENTS.md` is
agent-agnostic. The skill itself runs in Claude Code, because it uses its question prompts
and subagents.

## Related

- [grilling](../grilling/SKILL.md): stress-test a plan before you build it. The
  `docs/WORKFLOW.md` that glendonize can install starts with a "Grill" step; this is a skill
  for that step. glendonize does not call it.
- [whiteboard](../whiteboard/SKILL.md): a hand-drawn board for sketching a structure.
- [weekly-review](../../learning-by-building/weekly-review/README.md) and the [learning-by-building](../../learning-by-building/README.md):
  separate from glendonize.

## Credits

Named after and inspired by the repo structure of glendonC
([github.com/glendonC](https://github.com/glendonC)), e.g. his public repo
[1321](https://github.com/glendonC/1321).
