---
name: glendonize
description: Give a repo a structure modelled on glendonC's many-minions and 1321 so parallel agents can work in it safely — an AGENTS.md working agreement, a numbered R/D/Q register that code cites, PLATFORM_CONSTRAINTS with VERIFIED/ASSERTED facts, boundary checks that read source as text, a free-only gate, a test beside every source file enforced as a ratchet, a numbered docs/ set written from an owner index with a plans doc, and for Claude Code repos, in the Full setup (a Yolo setup, chosen at the start, skips them), a paid-run guard and a push pipeline (commits are instant; a background job reviews the range against its intent, verifies, runs the targeted tests and re-runs them against the reverted spine code, lints and pushes), an issue proof template and a parked Launch phase, every rule placed by the trust pyramid (codebase, static analysis, verification, prose, human review), all listed in a Harness table in the README. Asks Full or Yolo first; a Yolo repo can later upgrade to Full. Gated phases; writes nothing on the first pass; mines what the repo already says; parks what it cannot verify. Use when the user invokes /glendonize, says "glendonize this", "make this repo agent-ready", "structure it like many-minions", or asks for a decision register, constraints doc, boundary checks or a gate.
---

# Glendonize

Install, in the repo at `$ARGUMENTS` (a path) or the current directory, a structure
modelled on glendonC's many-minions, with the docs governance of his public repo
glendonC/1321 (owner index, status block, review rule, per-change check table); the push
pipeline (L.8) ports Kun Chen's no-mistakes (https://github.com/kunchenguid/no-mistakes, MIT). Neither
repo needs to be open to use this skill: everything it installs is in this file. The
structure is fixed; the stack is detected; the forms are in **Shapes** at the end.

## The rule this skill obeys before it installs it

Never invent a requirement, a decision, a "must not", an external fact, a dependency, or
a doc row. Every proposed entry names where it was found — `file:lines` in
`AGENT_READY.md`; the register itself cites sections. Every entry is confirmed by the user
before it is written. What cannot be settled becomes a `Q-` entry, that branch stops,
everything else continues. A survey that finds nothing to park is guessing. Subagent
summaries are leads, not facts: re-read the file before citing it.

If a proposed artifact contradicts a sentence in the repo's own `AGENTS.md`, `CLAUDE.md`
or README, stop that branch and put it in the conflict brief (Phase 0). Argue the case;
do not proceed on your own reading. The user's ruling is written back into the repo as a
dated `D-` entry so the next agent finds it instead of re-arguing it.

## Context — gather it, do not ask for it

```
git rev-parse --show-toplevel; git branch --show-current; git remote -v; git rev-parse HEAD
git status --porcelain; git worktree list
ls AGENT_READY.md AGENTS.md CLAUDE.md README.md .env.example .cursorrules GEMINI.md 2>&1
ls .github/workflows .github/copilot-instructions.md docs notes scripts test-support tests 2>&1
ls .claude/worktrees 2>&1; grep -n "worktrees" .gitignore .git/info/exclude 2>&1
gh auth status; which python; which node
```

Read `AGENTS.md`, `CLAUDE.md` and any other instruction file **in full**. They are the raw
material and this skill does not overrule them. If the current directory is inside a
nested worktree, move to the main one (`git worktree list`, first line) before anything.

## Resume

If `AGENT_READY.md` exists: do not restart. Compare its recorded `HEAD` and dirty set to
now; if either moved, re-run Phase 0 in diff mode and report what changed. Then name the
first unchecked phase and ask: resume there, or discard? Rulings stored in the file are
never re-asked.

## Escape hatch

If Phase 0 finds the structure already present and unchanged, say so, list what is
missing (usually the register) and offer only the phases that add something. The README's
Harness matrix (Shapes N) is still rebuilt from the files on disk on every run, so it never
lists a file that was moved or deleted since the last one.

## Setup: Full or Yolo

Phase 0 opens by asking which setup, with AskUserQuestion, one question with a briefing of at
most one screen (what each installs, the Yolo warning below, what an upgrade adds). The answer
is a ruling: `Setup: Full | Yolo` is written to `AGENT_READY.md` and as a dated `D-` in Phase 2.

- **Full**: everything in this file, unchanged.
- **Yolo**: the many-minions / 1321 shape without the push pipeline and the two guards. Items
  only Full installs carry the tag **(Full only)** where they are introduced.

| Piece | Full | Yolo |
|---|---|---|
| Phases 0-5, 7, 8 (register, working agreement, parking, constraints, boundary checks, docs, close) | yes | yes |
| Phase 6 gate: free drills + lint before each commit, `verify.yml` on a GitHub remote | yes | yes |
| Phase 6 push pipeline, revert-and-rerun, paid-run hook (L.5, L.8, L.13) | yes | no |
| Phase 9 Launch (parked) | yes | yes |
| L.1-L.4, L.6, L.7, L.9, L.10, L.14, L.16, L.19-L.25 | yes | yes |
| L.17 housekeeping, L.18 after_compact | yes | yes, if they do not block |
| L.27 worktree setup, L.28 `commit_range.py` (CI and the boundary checks use it, not only the pipeline) | yes | yes |
| L.5 paid-run guard, L.26 protected-folder guard, L.8 push pipeline, L.13 revert-and-rerun | yes | no |
| Templates installed | all in `templates/` | `claude/*`, `github/*`, `notes/PLANS.md`, `hooks/{after_compact,housekeeping,worktree_setup}.py`, `tests/{_drill,run_drills,commit_range,drill_boundaries,drill_run_drills,drill_commit_range,drill_after_compact,drill_housekeeping,drill_worktree_setup}.py` |
| Templates not installed | none | `hooks/{ship,mutation_check,guard_paid_run,guard_private_paths}.py`, `hooks/ship_briefs/*`, `tests/{drill_ship,drill_mutation_check,drill_guard_paid_run,drill_guard_private_paths}.py`, `THIRD_PARTY_NOTICES.md` |

What Yolo changes in what it writes:

- **`AGENTS.md` / `CLAUDE.md`**: no "push only through `ship.py`" rule, no paid-run marker rule, no
  agent-review section; the push rule is a plain `git push`, after the gate is green. The working
  agreement says: "This repo runs the Yolo setup: no push pipeline, no paid-run guard. Run the
  free gate before each commit; push with `git push`; ask before any paid run." Paid runs stay a
  rule in prose (L.20: it moved down a layer, and the Q- entry says so).
- **`.claude/settings.json`**: from `templates/hooks/settings.json` keep the `SessionEnd`
  housekeeping and the `SessionStart` `compact` after_compact entries; drop the `PreToolUse`
  `Bash|PowerShell` guard entry, any `Read|Grep|Glob` guard_private_paths entry and the
  `SessionStart` `startup|resume` `ship.py --status` entry. No file is written for it.
- **`drill_boundaries.py`**: cut the checks that read `guard_paid_run.py`, the three-list deny-list
  agreement and `ship_briefs` (they fail on a missing file); keep citations, cost labels, the
  AGENTS.md cap, the drill-count ratchet.
- **Harness matrix (Shapes N)**: lists only files on disk, so the Hooks group has no guard or
  pipeline row.
- **Phase 0 survey**: the deny-list is still mined and written (a `Cost:` label per script and
  the budget ledger still hold), but nothing enforces it.

**Yolo briefing warning, printed verbatim:** "Without the paid-run guard nothing stops an agent
from starting a paid script; watch your API costs."

**Upgrade to Full.** If Phase 0 finds `Setup: Yolo` in the register (or no `ship.py` and no
`guard_paid_run.py` under `.claude/hooks/` beside a glendonize structure), it offers "upgrade to
Full" next to the Escape hatch list. The upgrade adds only the missing pieces: the Full-only
templates above, their settings entries, the AGENTS.md / CLAUDE.md rules for them, the matrix
rows, and a dated `D-` superseding the Yolo one. Everything already installed stays untouched.

## Commits — automatic, one per change

Each phase whose gate passes is committed before the next starts: that phase's files only
(never `git add -A`), subject one sentence in the repo's style (`git log --format=%s -20`),
never `--no-verify`. Before Phase 6 exists, "the gate" is Phase 5's check plus whatever the
repo already runs. Phase 0 commits nothing. Push only when asked; a push is done when
`gh run watch` reports success (with no CI, when the local gate passes). A red run is fixed
before anything else — a gate nobody looks at is not a gate (in one production repo CI
stayed red for a week, across dozens of pushes, and nobody noticed).

---

## The structure

| Path | Role |
|---|---|
| `AGENTS.md` | the working agreement, ≤ 8 KiB — Shapes A |
| `CLAUDE.md` | imports `@AGENTS.md` — Shapes B |
| `README.md` | outward-facing; links the docs index, never copies it; ends in the Harness matrix — Shapes N |
| `.gitignore` | includes `.claude/worktrees/` |
| `.env.example` | one line per secret, no values, a comment saying which steps need none |
| `docs/README.md` + fixed docs | the owner index and its rows — Shapes C |
| `docs/REQUIREMENTS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md` | `R1`…, `D-001`…, `Q-001`… — Shapes D |
| `docs/PLATFORM_CONSTRAINTS.md` | external facts, VERIFIED or ASSERTED — Shapes E |
| `docs/WORKFLOW.md` | opens with the trust pyramid (L.20), then the loop — Shapes K |
| `docs/<DOMAIN>.md` × n | one per contract several parts of the code honour; pattern only, names come from the repo |
| `docs/local/` | optional; gitignored scratch and handoffs; no tracked doc links it |
| `.claude/orchestration/COORDINATION.md` | optional; gitignored coordinator log, read first by every session — Shapes J |
| the gate | free commands in order — Phase 6, Shapes F |
| `scripts/boundary_check.py` or `<code>/boundary.test.ts` | boundary checks — Shapes G |
| `test-support/` | only when the stack has a runner |

Docs home is `docs/`. If the repo keeps prose in `notes/` or elsewhere, that is a
conflict for the brief: propose the move, do not decide it. If an empty file with a target
name already exists, fill it — never create a sibling. If an ADR directory exists,
decisions cite `ADR-0001`, not `D-001`; detect before choosing the prefix.

---

## Phase 0 — Survey. Writes only `AGENT_READY.md`.

Produce all seven items, then ask with AskUserQuestion (≤4 per round, as many rounds as
the candidates need). Exclude the state file via `.git/info/exclude`, not `.gitignore` —
Phase 0 touches nothing else.

**1. Stack.** From files; install nothing to find out. A runner is detected from config
files and `scripts`, never from `devDependencies`.

| Found | Stack | Checker | Gate steps |
|---|---|---|---|
| `package.json` + vitest/jest config or `"test"` script | TS with runner | `boundary.test.ts` beside the code | existing `test`, `typecheck`, `lint`, `build` |
| `package.json`, no runner | TS, no runner | none of its own; the repo's one checker scans it as text | existing `lint`, `build` |
| `pyproject.toml`/`pytest.ini`/`conftest.py`/`tests/` | Python with pytest | `test_boundary.py` beside the code | pytest, plus ruff/pyright only if configured |
| `.py` files, none of the above | Python, no runner | `scripts/boundary_check.py`, run like the repo's other scripts | the free scripts the repo already names |
| both | mixed | **one checker**, in the runtime the gate already has, with a `ROOTS` list | one job per side |
| `go.mod`, `Cargo.toml`, JVM, other | unsupported | none | rules, register, parking, docs only — say so |

Never replace an existing linter. Where installed tooling already holds a boundary
(`no-restricted-imports`, an import-linter contract, a tsconfig without `dom` over a core
dir), extend it; a text scan is for what no installed tool checks.

With a runner, also measure **pairing**: the test-file convention the repo already uses
(`x.test.ts` beside `x.ts`; `tests/test_x.py` for `pkg/x.py`), how many source files have
a test by that convention, and the list of those that do not — that list is the ratchet's
baseline (Phase 5). A heavily tested repo can still leave a large share of its source
files without a sibling test when nothing enforces the pairing; report the real ratio,
not "1:1". Without a runner there is no pairing to measure; say so. If tests are named by
behaviour rather than by source stem, there is no pairing either: say so, and Phase 5
installs no ratchet.

**2. Free vs paid.** Mine candidates: prose saying costs / bills / per page / per call /
real money / do not run; modules reading env vars matching `KEY|TOKEN|SECRET|ENDPOINT`;
modules importing a paid SDK. The user confirms the deny-list. A repo with none gets an
empty deny-list and a line saying so. A step is free when the survey can show it reads no
billing credential and makes no billable call; installing packages is free. A free step
that reaches an external host (not localhost, not a CI service container) is flagged as a
flakiness risk for a ruling. In doubt, paid. Each deny-listed script refuses to run without
its key, and without it writes `skipped: <reason>` to its result — never a pass.

**3. Bans.** "Do not add X", "there is no X and don't create one". Banned things are
never proposed. Name the ban and what replaces it.

**4. Candidates, each with provenance and its pyramid layer** (L.20: the highest layer that can
hold it; a rule proposed as prose says why no type, lint or test can):
- **Requirements / decisions** — rule-shaped sentences: never, must, always, only, by
  decision, rejected, accepted deviation. Bucket: *settled with rationale*, *settled
  without*, *unsettled*.
- **Boundaries** — "X must not import / call / write / reach Y" from prose, and from
  shape: a dir nothing else may depend on; the exact set of files that reach the network;
  paths named private that must never be tracked.
- **External facts** — vendor, API, limit, region claims. ASSERTED until a source is linked.
- **Parked** — read and not settled; with the act that would settle it.
- **Doc rows** — the fixed rows plus domain rows drawn from top-level dirs and existing
  prose. A row with nothing behind it is not proposed.
- **Non-claims** — sentences of the form "X is not Y" / "this does not mean" (a grounded
  value is not a correct one; agreement is not accuracy). They seed OVERVIEW's last section.
- **Existing citations** — how code already points at docs (`path:line`, `Source:`,
  ids). The citation phase upgrades that style; it never adds a second one.

**5. Conflict brief** — Shapes H. One block per conflict, both sides quoted verbatim, a
proposed resolution, "Your ruling?". Always check: docs home ≠ `docs/`; a ban that a
planned artifact could fall under; **two working agreements** (`CLAUDE.md` with rules of
its own beside `AGENTS.md`; `.cursorrules`, `copilot-instructions.md`, `GEMINI.md`);
`AGENTS.md` untracked; a "no linter / no build" sentence that a subdir already contradicts;
the push rule (when asked vs when the batch is done).

**6. Blockers.** Dirty tree (the phases read the working tree; CI reads the commit — they
will disagree); `.claude/worktrees/` or any dir holding a `.git` *file* not ignored (a full
second copy; every scan double-counts it); promised-but-empty files; no remote (Phase 6
degrades to a local gate script); `gh auth status` failing (parking stays local; no
`gh run watch`).

**7. Phase menu.** The Setup (Full or Yolo) is asked first. Phases 1–8 (and the parked Phase 9, Launch), one line each on what they add here; which to skip. Add the
L.11 carry-over table with a yes / no / not-applicable per row.

Write `AGENT_READY.md` (Shapes I): Progress list, survey, candidates, **rulings verbatim**,
recorded `HEAD`. **Gate:** the user rules on every conflict and approves every list.
`git status --porcelain` must show nothing new. Do not proceed on "looks fine".

## Phase 1 — Unblock

`.gitignore` gains `.claude/worktrees/`. `CLAUDE.md` resolves per Shapes B. User commits or
explicitly accepts the dirty baseline. No design content.
**Verify:** `git check-ignore .claude/worktrees`; `CLAUDE.md` contains `@AGENTS.md` and restates none of its rules. **Gate.**

## Phase 2 — Register

`docs/REQUIREMENTS.md` (`R1`…) and `docs/DECISIONS.md` (`D-001`…) from confirmed
candidates only, Shapes D. Settled-with-rationale → `D-` quoting it. Settled-without →
`D-` with `Rationale: not recorded` — **never a plausible reason**; a fabricated rationale
is invisible six months later and is what this structure exists to prevent. Unsettled →
`Q-`. Every Phase 0 ruling → a dated `D-` in the user's words. Ids assigned once, never
renumbered. A thin repo yields a five-entry register and says so; do not pad.
Tell the user this is the expensive gate and estimate it from the count.
**Verify:** every entry has id, sentence, `Source:`; no id collides. **Gate.**

## Phase 3 — Working agreement

`AGENTS.md` per Shapes A: existing sentences verbatim, then the sections. If none exists,
open with the five bullets, nouns adapted to the domain. Where a section touches an
existing ban, name the conflict and the ruling in the file's own text. Cap 8 KiB — it
loads into every agent's context every time; if verbatim extension exceeds it, propose
(do not perform) moving content in Phase 7, with a ruling.
**Verify:** old text appears as unchanged diff lines; `wc -c AGENTS.md` ≤ 8192 (Phase 5 enforces it). **Gate:** user reads it all.

## Phase 4 — Parking and constraints

`docs/OPEN_QUESTIONS.md` seeded from the unsettled bucket and every `TODO(user)` in code.
`docs/PLATFORM_CONSTRAINTS.md` with the preamble **verbatim** (Shapes E); entries only from
confirmed candidates; ASSERTED unless the repo already links a source. If `gh auth status`
succeeds, offer once to mirror open `Q-` as issues — thin pointers, title `Q-nnn — <question>`,
body one line plus a link to the section; the file stays the truth and the issue closes in
the commit that settles it.
**Verify:** every VERIFIED has a URL in its paragraph; every `Q-` names a settling act. **Gate.**

## Phase 5 — Boundary checks

Shapes G, one check per confirmed boundary. Self-guard first and it **hard-exits**. The
walk skips the skeleton's `SKIP` set and any dir with a `.git` file. Strip comments before
vocabulary scans (`tokenize` for Python; regex for TS); use `ast` for Python imports.
`offending` as `"<file>: <specifier>"`; non-zero exit. Include **citation resolvability**
(every id, doc path and `docs/X.md N.N` in source *and docs* resolves) — without it the
register rots — and AGENTS.md ≤ 8 KiB, tracked when `CLAUDE.md` imports it. If CI will
exist, include the secrets-free check; it strips comment lines first, because the deny-list
header names every paid script. Join an existing family of free check scripts by name
(e.g. `checks/check_*.py`) and inherit its sanction; the gate then runs the glob only.
Counted exemptions without CI are advisory; say so.

With a runner and stem-named tests, add the **pairing ratchet** (Shapes G, check 8): a tracked
`tests/untested.txt` (or `test-support/untested.txt`) lists the source files Phase 0 found
without a test. The check fails on a source file that is in neither the list nor paired
with a test, and on a listed file that has since gained one — the list shrinks, never
grows, and a new module cannot land untested. Generated, vendored and type-only files are
excluded by an explicit glob the user confirms, never by judgement. A hard 1:1 fails on day
one and gets muted, which is why it is a ratchet.

A test file that exists but was gutted passes the pairing ratchet, so add the **assertion-count
ratchet** next to it (Shapes L.1): per test file, the count of assertion calls at the push base
may not drop; a deliberate drop says `drop test:` and why in the commit subject, and an env var
lets the local run pass before that commit exists. In one production repo 57 checks left in one
commit with nothing noticing before this existed (2026-10). Where scripts can pay, every script in
the paid dir declares `Cost: free - <why>` or `Cost: PAID - <why>` on its own docstring line; the
check fails an unlabelled script, and the deny-list is derived from the `PAID` lines with a fixed
floor of the known ones, so a new paid script cannot land unlisted. The runner that executes the
checks blanks every credential named in `.env.example` in the child environment, one guard
instead of one per script.
**Verify:** run it; it passes on day one — a red check gets muted. Then plant one violation per check in a temp copy and see it go red — a check that has never failed proves nothing; never commit the plant. **Gate:** each check is a rule the user holds.

## Phase 6 — Gate

The gate is the list of free commands, run in order before every commit; CI only re-runs
it. GitHub remote and the user wants CI → `.github/workflows/verify.yml` (Shapes F).
Otherwise the repo's own runner holds the list (`npm run check`, or `scripts/gate.sh` +
`.ps1`); no `.github/` is a valid end state (1321 has none). One job per side; only steps
Phase 0 showed free; deny-list comment first; no `secrets:`; `permissions: contents: read`;
`timeout-minutes`; `concurrency` that cancels only pull-request runs. A test step fails when
it runs zero tests, or when a test is skipped, pending or `.only` without a line in one
tracked list of accepted skips, each with its reason (vitest `passWithNoTests: false`,
`forbidOnly`): a green run that ran nothing is what the gate exists to catch.

(Full only) For a Claude Code repo also propose the push pipeline (Shapes L.8, copied from `templates/`)
with its revert-and-rerun (L.13), the issue proof template (L.14), the plans doc (L.9) and the
vacuous-pass guards (L.10), each with its reason; for a repo with private content the
protected-folder guard (L.26), for agents in worktrees the worktree setup (L.27), for a repo with a
UI the optional `ui-compare` screenshots (L.8). With the pipeline the gate before a commit is
the change's own minimum check; CI runs the whole list. Review depth follows L.16.

Four more steps a production repo earned (Shapes L), each optional, each proposed with its
reason: a CI step that fails a commit touching the spine dirs without a change under the test
dir unless the subject says `no test:` and why (`fetch-depth: 0` and `github.event.before` give
it a base; `tests/commit_range.py`, L.28, judges each commit of the range); a **red-test home** (`tests/tdd/`) outside the gate glob, so a test-first failure can be
committed and the greening commit renames it into the gate; a local-check dir for a green test
that needs gitignored data, since CI has nothing to run it on; and, for Claude Code repos, a
`PreToolUse` hook that blocks a shell command naming a deny-listed script unless it carries a
marker the agent adds only after the user's go. A paid deny-list also earns a budget ledger doc
row: estimate before, actual after, in the same commit as the run's findings. For Python with no
linter, the twin of the promise rules below is Ruff with bug rules only (`E4 E7 E9 F B`), version
pinned in CI, run by a check script; a typecheck with a per-file error baseline that only shrinks
is the counted-exemption variant for types.

**Dependencies are derived, then proven:** walk the gate scripts' imports with `ast`,
subtract stdlib, then `git clone --no-hardlinks . <tmp>` (not `git archive`: an export has
no `.git`, so every check that calls `git ls-files` or `git log` fails there for no reason —
seen 2026-10-19), create a fresh venv with only the derived packages (`python -m venv`, no
`--system-site-packages`), and run the whole gate there. Global site-packages hide lazy imports
(in one production repo a PDF library imported Pillow inside a method; the walk missed it,
the local run passed because Pillow was installed globally, CI was red for a week). On Windows keep `<tmp>`
short — 260-char path limit. When a manifest is banned, install inline with a comment
naming the setup section it duplicates; record the drift as a `Q-`. Set
`PYTHONIOENCODING=utf-8` when the repo's setup says to.
**Verify:** names no deny-listed script; Phase 5's check agrees; the fresh-venv run is green. **Gate:** never-runs list confirmed; first push is the user's, done when `gh run watch` reports success.

## Phase 7 — Docs

`docs/README.md` **first** (Shapes C): the owner index — fixed rows plus confirmed domain
rows, each with Owns / Does not own / Update when. **Gate on the rows.** Then generation —
one agent per row (Agent tool, or `/wt`) for repos with many rows; a single pass when there
are few. Each agent gets only: its row, the code, the register, and: *number every
subsection; cite nothing by quotation; link siblings by filename only; quote no count or
measurement without the commit or result file it came from; put the Status block under the
heading.* Root `README.md` links the index, never copies it. The user's own
prose stays where the Phase 0 ruling put it, is never rewritten, translated or renumbered,
and is cited by filename alone. Existing code citations are upgraded to `docs/X.md N.N`;
ids go into existing test/drill labels (`expect("raises empty_input (D-014)")`); no new
comments in files whose style rule forbids them.

`docs/WORKFLOW.md` opens with the **trust pyramid** (Shapes K): the figure, then the table with the
last column filled from files that exist in the target repo, found with `git ls-files`. A layer
with nothing behind it says `nothing yet` and is never padded; it becomes a candidate for the user
to rule on, the highest empty layer first.

Last, the root `README.md` gets its **Harness matrix** (Shapes N): one `| Topic | Description |`
table per group (Rules, Register, Checks, Gate, Hooks, Docs), one row per harness file that
exists in the repo, found with `git ls-files`, never from this skill's own list. A group with
no file is left out; a file the repo has that the skill did not install (an older check, an
existing workflow) is listed too if it does a harness job. The section sits between
`<!-- harness:start -->` and `<!-- harness:end -->`; a re-run replaces only what is between
the markers and leaves the rest of the README alone. Before the markers exist, show the
section and ask where it goes; the user's README text is never rewritten.
**Verify:** every index link resolves; every cited doc has numbered headings; every agent-written doc has a Status block; every Harness matrix link resolves to a tracked file; every path in the pyramid table is tracked. **Gate.**

## Phase 8 — Close

Rebuild the README's Harness matrix (Shapes N) from `git ls-files` as the last write, so it
shows what this run left on disk, and commit it with the close. Summary in the Working-loop
report order: files written, `D-` count, open `Q-` list, skips and why. Delete `AGENT_READY.md` and its `.git/info/exclude` line. Say in one sentence which
mechanisms carry regardless of domain (register, constraints, parking, boundary checks,
gate) and which depend on the domain tolerating unreviewed output (worktree fan-out).

## Phase 9 — Launch (parked until the product has real users)

Not built on a first run. Phase 0 asks one question: does the product have real users today?
If no, this phase is written as a `Q-` entry in `docs/OPEN_QUESTIONS.md` and a plan in
`docs/PLANS.md` (L.9), both saying "applied once the product is in real use", and the skill
installs no code for it. If yes, propose Shapes O row by row, each with its reason. Gate: the
user confirms each row; a row with nothing behind it (no flag system, no telemetry) is parked.

---

# Shapes

## A. `AGENTS.md`

A new file opens with five bullets like these, nouns adapted to the domain:

```markdown
# Evidence-based collaboration

- Stop rather than guess when an unmade product, content or visual decision would change the outcome in a material way. Say what is established, name the decision or asset that is missing, and halt that line of work until someone supplies it.
- Neither accept nor resist a suggestion by reflex. Ground each recommendation in the user's present instruction, the recorded product constraints, the code as it stands, and evidence you can observe from running a check.
- If a fresh instruction clashes with an earlier constraint, point out the clash and let the user's most recent explicit instruction win. Never quietly bend one to fit the other.
- A missing approved asset is never filled with a stock icon, a placeholder, made-up copy, dummy data or ad-hoc artwork, unless the user has asked for exactly that stand-in.
- When the brief leaves open a choice with real consequences, lay out the precise decision, or the asset brief, needed to settle it. Meanwhile carry on only with work that does not hinge on it.
```

Then the sections, appended after whatever already exists:

```markdown
# Citation

Code cites the register and the docs; nothing cites code. Write `(R3)`, `(D-014)`,
`(Q-002)`, `(docs/OPERATIONS.md 2.4)` at the end of the clause they govern — in comments,
docstrings and test or drill labels. Section numbers, never pasted sentences: prose moves,
numbers do not. Decision first when the decision is the subject `(D-078, R21)`, requirement
first when it is `(R12, D-080)`. The register is docs/REQUIREMENTS.md and docs/DECISIONS.md;
a cited id that does not resolve fails the boundary check.
A comment is a pointer, not evidence: read the code it sits on before relying on it. Keep
comments that say why, citations and cost headers; do not write comments that restate what
the code does, or that assert behaviour elsewhere ("caller guarantees non-null") — those go
stale silently, and the second kind belongs in a test.

# Reviewing a diff

Defects first, style last. The defects that matter here: <the repo's own classes — e.g. a
plausible value where a null with a reason belonged; a fallback that fills a field without
saying so; a check reported as run that was skipped; a doc contradicting its owner in
docs/README.md; a cited id that does not resolve; a comment relied on as proof of behaviour that no test pins>. Name file and line; say whether each
finding is a defect or a question. If nothing survives verification, say what remains
untested, never "looks good".

# Parking

When a missing decision or an unverifiable fact would change the result: stop that branch,
add a `Q-` entry to docs/OPEN_QUESTIONS.md with what is known and the exact act that would
settle it, cite it where the branch stopped, and continue everything that does not depend
on it. External facts go in docs/PLATFORM_CONSTRAINTS.md as ASSERTED until a source is read
and linked. A plausible value is a defect; a null with a reason is correct.

# Gates

Run before any commit, in this order: <free steps>. Never run here: <deny-list, with why>.
Boundary checks read source as text and cost nothing; they are not a test suite.
<!-- conflict slot: "<existing rule, verbatim>" — ruled <date>: <ruling> (D-nnn). -->

While working, the minimum check per kind of change — the full gate still runs before the commit:

| Change | Minimum check |
|---|---|
| A doc, comment or label | the boundary check — every citation still resolves |
| <code area> | <the free check that covers it, then all of them> |
| <frontend dir> | `npm run lint`, `npm run build` |
| the gate file itself | the boundary check (no paid script named), then push and watch the run |

An implementer's "verified" means the row for its change was run, and the report names it.

# Working loop

Fan out across git worktrees (`/wt`, one module per agent) only for work with no open
decision in it; anything that holds a decision runs in a single stream with a person in the
loop. Two chunks touching one file run in sequence. A subagent's report is a claim; read the
diff and run the checks. The review rule above is unchanged by the gates.

Commit after every logical change without being asked: the change and its checks in one
commit, the free gate green first, only that change's files staged, subject one sentence in
this repo's style. No "WIP", no `--no-verify`.

The test lands in the commit that lands the behaviour, beside the source file it covers
(`x.test.ts` beside `x.ts` | `tests/test_x.py`). Where the code is deterministic — a value
in, a value out — write the test first, run it, and read the failure before writing the
code: a test that has never failed proves nothing. Where the output comes from a model or a
vendor, the test covers the shaping around it with a recorded fixture, and the live call is
checked by <the paid, user-authorised run>. <Only where Phase 5 installed the ratchet:> The
untested list (`tests/untested.txt`) only shrinks; a new source file without a test fails the check.
<Only where Phase 6 installed them:> A red test written before its fix lives in `tests/tdd/`, outside
the gate, and names the issue it waits for; the commit that makes it green moves it into the gate.
Every commit touching <spine dirs> carries its test, or says `no test:` and why in the subject; a
test file never loses an assertion, or the subject says `drop test:` and why (`no drill:` /
`drop drill:` where the repo calls its tests drills).

A browser test only for what only a browser decides — a click really lands on page N, the
last row is reachable at phone width — fed a recorded fixture of **invented** values with
every backend call intercepted (`page.route('**/api/**')`), and an unknown call fails it.
It checks plumbing, never whether a value is right; that stays with the human walkthrough
and the scored run. A flaky check is deleted with its reason in the subject line, never
muted: deleting flaky end-to-end tests outright, even the day before a demo, beats muting them. Push <when asked | when the batch is done —
ruled in Phase 0>; a push is done when `gh run watch` reports success. Uncommitted work in a
worktree is lost when the worktree is removed. Every report states, in order: outcome, files
changed, exact checks run, what was skipped, what was not touched.
```

## B. `CLAUDE.md`

Target: `CLAUDE.md` holds `@AGENTS.md`, plus at most a repo manual that restates none of its
rules. Branches: (i) `CLAUDE.md` has rules, no `AGENTS.md` — move the rules, leave the import;
(ii) both have content — diff them, the user rules which sentences are rules (→ `AGENTS.md`)
and which are manual; (iii) `AGENTS.md` untracked — flag it before anything cites it. A ruling to keep it untracked
is valid: its rules are then enforced as checks, and no tracked file cites it. A fourth ruling
is valid too and worth naming in Phase 0: agent-neutral rules stay in `AGENTS.md`, and rules that
only Claude Code can obey (swarm sizing, approval words, what a hook enforces) go in `CLAUDE.md`
under its own heading; the conflict is then a split by audience, not a duplicate.

## C. `docs/README.md` and numbering

The index is an owner registry, written first: every current fact has one owner; others
point at it, never restate it; when two disagree the owner is right. Rows grouped in tables
(contracts and the map · register · setup and findings · the user's prose); `|---|`, no
colons, sentence case, no trailing stop.

```markdown
| Document | Owns | Does not own | Update when |
|---|---|---|---|
| [PLATFORM_CONSTRAINTS.md](PLATFORM_CONSTRAINTS.md) | Vendor facts, each VERIFIED or ASSERTED | What this repo decided (DECISIONS) | A vendor fact is learned, checked, or found wrong |
```

Fixed rows: OVERVIEW — the whole idea in one page, ending in *Standing non-claims* (each
limit the product does not claim, one line, pointing at the doc that explains it); PRODUCT
— what it is, for whom, what it is not; ARCHITECTURE — the map, linking the contracts;
PLATFORM_CONSTRAINTS (E); OPERATIONS — health, checks, recovery, deploying; LOCAL_SETUP —
real systems locally, first run (a small repo may fold OPERATIONS into it; record that as a
`D-`); REQUIREMENTS, DECISIONS, OPEN_QUESTIONS (D); PLANS — work that runs over more than one
session (Shapes L.9); `<DOMAIN>.md` — one per contract several parts of the code honour.

Under each agent-written doc's heading — a commit, not a date: a typed date is a freshness
claim nothing checks; `git rev-parse HEAD` at the moment of checking is one anybody can.
The user's prose carries none:

```markdown
<!--
Status: current | register | snapshot | transcript - <when it changes, e.g. "in the same commit as src/errors.py">
Checked against: <sha>
-->
```

Every doc code will cite is RFC-numbered (`## 1. Scope` / `## 2. Conventions` / `### 2.1 …`).
Code cites `docs/X.md 2.7` — path and number, no link, no `§`; a second reference in the
same sentence drops the path: *(docs/X.md 5.9.1) and the download (5.9.2)*.

## D. Register and parking entries

```markdown
## R3 — <one sentence, what the product must do>
Source: <docs/X.md N.N, or the filename alone for unnumbered prose> · Since: 2026-09-22

## D-014 — <one sentence, what was decided>
Rationale: <quoted from the source> | not recorded
Rejected: <alternative — why, quoted> | not recorded
Source: AGENTS.md "Gates" · Decided: 2026-09-16 · Supersedes: — · Cited by: src/errors.py

## Q-002 — <the question>
Known: <what the repo says, with sources>
Settles it: <the exact human act — "one person with access to the vendor account reads its documentation page">
Who: <role> · Opened: 2026-09-22 · Blocks: D-014 | nothing
```

## E. `docs/PLATFORM_CONSTRAINTS.md`

Preamble verbatim:

```markdown
# Platform constraints

Verified vendor facts. Check here before assuming a vendor can do something.

Every entry is tagged VERIFIED (a source was read and is linked) or ASSERTED
(not yet checked). Do not promote an ASSERTED line to VERIFIED without adding
the source. If a fact is missing, say it is missing rather than filling it.

Re-read the linked source before treating a VERIFIED line as current.
```

Then `## <Vendor>` / `### <Topic>`, one bold claim per paragraph, ending in its tag:

```markdown
**<Claim.>** <evidence, quoted>. VERIFIED: <url>
- <Claim.> ASSERTED.
**Missing fact: <what>.** <what the repo does instead>.
```

A contradiction between sources is recorded as one, with a nested missing fact. A superseded
paragraph stays; the newer one says it supersedes it.

## F. The gate in CI

Order: checks that build state → test → typecheck → lint → build. Alphabetised `env:`.
Drop what the survey did not find; always keep the header comment.

```yaml
# Everything here is free. This workflow holds no secrets, so a paid call
# cannot succeed even by accident. Never run here: <script> (<why: bills per page>).
# See AGENTS.md "Gates". The pip line mirrors <setup section>; no manifest by D-nnn
# (drift: Q-nnn); derived from imports, proven in a fresh venv from a `git clone`.
name: Verify
on: { pull_request: {}, push: { branches: [main] } }
permissions: { contents: read }
concurrency:  # a cancelled main run leaves no record of whether that commit was green
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
  group: "verify-${{ github.ref }}"
jobs:
  checks:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    env: { PYTHONIOENCODING: utf-8 }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install <derived>
      - run: for f in <free-check-glob>; do echo "== $f"; python "$f" || exit 1; done
```

A Node side is a second job: `setup-node` with `cache: npm`, `npm ci`, then only the
`lint` / `typecheck` / `test` / `build` scripts that exist. A shell step asserts one
condition per line (`test "$code" = 200`): in an `&&` chain `set -e` ignores every
command but the last. When no linter exists at all,
propose only five promise-bug rules: `no-floating-promises`, `no-misused-promises`,
`await-thenable`, `only-throw-error`, `require-await` — a missing `await` is an error
typecheck cannot see. The Python twin is Ruff with `select = ["E4", "E7", "E9", "F", "B"]`, no
stylistic lint rules (`ruff format --check` beside it is a separate choice), pinned (`ruff==<x.y.z>`) in the pip line because a newer release changes what it
flags. Any check that compares against the push base (Shapes L.1, L.2) needs `fetch-depth: 0` on
the checkout step and `${{ github.event.before }}` passed in as the base; on a first push
(all-zero `before`) both fall back to `HEAD~1`, on a forced push the CI step falls back and the
ratchet skips, printing that it had nothing to compare.

## G. Boundary checks

Read source as text, never import it. Variants: FORBIDDEN prefix list, ALLOWED regex list
(preferred), exact-allow-set, labelled-regex vocabulary scan, counted exemptions (a leak may
shrink, never grow; an exemption used zero times is stale and fails too), the **assertion-count
ratchet** and the **cost label** (both Shapes L), and the **drift
check**: a shape that one side owns in code and another side restates by hand because it
cannot import it (a Python schema copied into TypeScript types; a TS list copied into SQL
and Swift) — import or call the owner, read the
copy as text, pull the names with a regex, compare, and print both lists on failure. Find
candidates in Phase 0: grep the field names of the main record across languages; two hits
in two languages is a drift check. What an agent would not write unaided: the hard-exit
self-guard, the nested-worktree skip, the **relative-path** skip test (matching `SKIP`
against the absolute path made the check scan zero files from any checkout under
`.claude/`, and in one production repo several agents in a single day reported green
checks that had scanned nothing), comment stripping
before vocabulary scans, comment-line stripping before the gate scan. The rest is ordinary.

**Python, no runner** (`scripts/boundary_check.py`, stdlib only):

```python
"""Boundary checks over source text. Files are read, never imported: nothing here can pay.
A comment may say why a rule exists; only the code is held to it."""
import io, re, subprocess, tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", ".claude", "node_modules", "__pycache__", "dist", ".venv", "venv"}
DENY_LISTED = ["<paid_script.py>"]


def files(*roots, suffixes):
    out = []
    for root in roots:
        for p in sorted((ROOT / root).rglob("*")):
            if SKIP & set(p.relative_to(ROOT).parts):  # relative: an agent worktree under
                continue                                # .claude/worktrees/ would scan nothing
            if any((q / ".git").is_file() for q in p.parents if q != ROOT):
                continue  # a nested worktree is a full second copy of the repo
            if p.is_file() and p.suffix in suffixes:
                out.append(p)
    return out


def code_only(p):
    """Source minus comments and docstrings. Tokens come back space-joined
    (`requests . get`), so vocabulary regexes need \\s* around `.` and `(`."""
    if p.suffix != ".py":
        t = re.sub(r"/\*[\s\S]*?\*/", "", p.read_text(encoding="utf-8"))
        return re.sub(r"(?m)(^|\s)//.*$", r"\1", t)
    kept, prev = [], tokenize.INDENT
    for tok in tokenize.generate_tokens(io.StringIO(p.read_text(encoding="utf-8")).readline):
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.STRING and prev in (tokenize.INDENT, tokenize.DEDENT,
                                                    tokenize.NEWLINE, tokenize.NL):
            continue  # docstring
        kept.append(tok.string)
        if tok.type not in (tokenize.NL, tokenize.NEWLINE):
            prev = tok.type
    return " ".join(kept)


def rel(p):
    return p.relative_to(ROOT).as_posix()


def git_files(*args):
    out = subprocess.run(["git", "ls-files", "-z", *args], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    return set(out.split("\0")) - {""}


# A link is a claim about a clone, not this disk: ignored private notes must not resolve it
KNOWN = git_files("--cached", "--others", "--exclude-standard")


def expect(label, ok, detail=()):
    print(("  ok   " if ok else "  FAIL ") + label + "".join("\n         " + d for d in detail))
    return ok


def main():
    ok = True
    spine = files("<code-root>", suffixes={".py"})
    # 0. self-guard: an emptied or moved tree passes every check vacuously
    if len(spine) < <N> or not {"<a.py>", "<b.py>"} <= {p.name for p in spine}:
        raise SystemExit(f"SELF-GUARD TRIPPED ({len(spine)} files) - nothing below is meaningful")
    # 1. forbidden prefix: ast imports of <code-root> vs module stems under <other>  (D-nnn)
    # 2. exact-allow-set: files whose code_only() matches
    #    r"\brequests\s*\.\s*(get|post|put|patch|delete|request)\b|\burlopen\s*\(" == ["<path>"]  (R-n)
    # 3. each private path is in .gitignore AND has nothing under it in `git ls-files`  (R-n)
    # 4. the gate cannot pay; strip comment lines, the deny-list header names every paid script
    for wf in files(".github/workflows", suffixes={".yml", ".yaml"}):
        body = re.sub(r"(?m)^\s*#.*$", "", wf.read_text(encoding="utf-8"))
        bad = [w for w in ("secrets.", *DENY_LISTED) if w in body]
        ok &= expect(f"{rel(wf)} holds no secrets and names no paid script", not bad, bad)
    # 5. every cited id, doc path and section resolves - docs cite each other, so scan .md too
    heads = []
    for name in ("REQUIREMENTS", "DECISIONS", "OPEN_QUESTIONS"):
        if f"docs/{name}.md" in KNOWN:
            heads += re.findall(r"(?m)^## (R\d+|D-\d{3}|Q-\d{3}) ", (ROOT / "docs" / f"{name}.md").read_text(encoding="utf-8"))
    ids, dups = set(heads), sorted({i for i in heads if heads.count(i) > 1})
    ok &= expect("no register id is defined twice (two branches took one id)", not dups, dups)
    dangling = []
    for p in files("<all roots>", "docs", suffixes={".py", ".ts", ".tsx", ".md"}):
        if rel(p) not in KNOWN:
            continue
        text = p.read_text(encoding="utf-8")
        for cited in set(re.findall(r"(?<![\w-])(R\d{1,3}|D-\d{3}|Q-\d{3})(?![\w-])", text)) - ids:
            dangling.append(f"{rel(p)}: {cited}")
        for doc, sec in set(re.findall(r"(?<![\w/])docs/([A-Z_]+\.md)(?: (\d+(?:\.\d+)*))?", text)):
            t = f"docs/{doc}"
            if t not in KNOWN or sec and not re.search(rf"(?m)^#+ {re.escape(sec)}\.?\s", (ROOT / t).read_text(encoding="utf-8")):
                dangling.append(f"{rel(p)}: docs/{doc} {sec}")
    ok &= expect("every cited id, doc and section resolves", not dangling, sorted(dangling))
    # 6. AGENTS.md loads into every context: <= 8 KiB, and tracked when a tracked CLAUDE.md imports it
    agents, tracked = ROOT / "AGENTS.md", git_files("--cached")
    ok &= expect("AGENTS.md <= 8192 bytes", not agents.exists() or agents.stat().st_size <= 8192)
    imports = "CLAUDE.md" in tracked and "@AGENTS.md" in (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    ok &= expect("AGENTS.md tracked when CLAUDE.md imports it", not imports or "AGENTS.md" in tracked)
    # 7. (if docs/local/ is used) no tracked doc links docs/local/
    # 8. pairing ratchet (only with a runner and stem-named tests): every source file has a test or is on the
    #    untested list; a listed file that gained a test is stale. The list shrinks, never grows.
    listed = set((ROOT / "tests" / "untested.txt").read_text(encoding="utf-8").split())
    def has_test(p):
        return (ROOT / "tests" / f"test_{p.stem}.py").exists()  # or p.with_name(p.stem + ".test.ts")
    unpaired = sorted(rel(p) for p in spine if not has_test(p) and rel(p) not in listed
                      and not p.match("<generated glob>"))
    stale = sorted(rel(p) for p in spine if has_test(p) and rel(p) in listed)
    ok &= expect("every source file has a test or is on tests/untested.txt", not unpaired, unpaired)
    ok &= expect("no listed file has gained a test (remove it from the list)", not stale, stale)
    print("\nALL PASSED" if ok else "\nSOME FAILED")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
```

**TS with vitest** (`<dir>/boundary.test.ts`, colocated):

```ts
/** <Claim in product language> (R8, D-067). <The defect nothing else would catch.> */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const root = fileURLToPath(new URL("./", import.meta.url));
const ALLOWED = [/^node:/, /^\.\.?\//, /^@\/shared\//];

const sourceFiles = (d: string): string[] => readdirSync(d, { withFileTypes: true }).flatMap((e) =>
  e.isDirectory() ? sourceFiles(join(d, e.name)) : /(?<!\.test)\.tsx?$/.test(e.name) ? [join(d, e.name)] : []);
/** A comment may say why a rule exists; only the code is held to it. */
const withoutComments = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|\s)\/\/.*$/gm, "$1");
/** The modules a file imports, in static, dynamic and side-effect form. */
const specifiersOf = (p: string) => {
  const s = withoutComments(readFileSync(p, "utf8"));
  return [...s.matchAll(/from\s+["']([^"']+)["']/g), ...s.matchAll(/import\(\s*["']([^"']+)["']\s*\)/g),
    ...s.matchAll(/^import\s+["']([^"']+)["']/gm)].map(([, m]) => m);
};
const named = (p: string) => relative(root, p).split(sep).join("/");

describe("<the thing being bounded>", () => {
  const files = sourceFiles(root);
  it("scans the files it expects to scan", () => { // fails loudly, not vacuously
    expect(files.length).toBeGreaterThan(3);
    expect(files.map(named)).toEqual(expect.arrayContaining(["<a>.ts", "<b>.ts"]));
  });
  it("depends only on what it is allowed to", () => {
    expect(files.flatMap((p) => specifiersOf(p).filter((s) => !ALLOWED.some((a) => a.test(s)))
      .map((s) => `${named(p)}: ${s}`))).toEqual([]);
  });
  // exact-allow-set: expect([...new Set(reached)]).toEqual(["@/adapters/port"]);
  // counted exemptions: { occurrences: 10, term: "legacyName" } via toEqual — a leak shrinks, never grows.
  // pairing ratchet: files without `${stem}.test.ts(x)` minus test-support/untested.txt → toEqual([]);
  //   listed files that now have one → toEqual([]) too, so the list only shrinks.
});
```

## H. Conflict brief block

```markdown
**C1 — <what is being added>, against <which existing rule>**
`AGENTS.md:3-5` says, verbatim: "<the sentence>"
This plan adds: <artifact>.
Why it may be inside the rule: <argument>. Where it is genuinely outside: <honest part>.
**Your ruling?** If accepted, it is written into AGENTS.md verbatim, dated, as D-nnn.
If declined: <what is dropped and what still stands>.
```

## I. `AGENT_READY.md`

```markdown
# glendonize — state
HEAD: <sha> · Started: <date> · Repo: <path>

## Progress
- [ ] 0 Survey  - [ ] 1 Unblock  - [ ] 2 Register  - [ ] 3 Agreement
- [ ] 4 Parking  - [ ] 5 Boundaries  - [ ] 6 Gate  - [ ] 7 Docs  - [ ] 8 Close
- [ ] 9 Launch (parked: Q-/plans entry only until real users)

## Survey
<stack table row · docs home · free steps · deny-list · bans · remote · gh · blockers>

## Candidates
### Requirements / Decisions   ### Boundaries   ### External facts   ### Parked   ### Doc rows   ### Non-claims
<each with Source: file:lines>

## Rulings (verbatim, never re-asked)
C1 — <the user's sentence> · <date>
```

## J. Running the phases with parallel agents (optional)

When several agents build the structure, or later work inside it, four habits keep them
apart and keep the history readable:

- **A coordinator log that outlives a context reset.** Install it, do not just mention it:
  1. `.claude/orchestration/COORDINATION.md`, gitignored (it holds session state, not
     project truth; the register stays the truth).
  2. Seed it on the day it is created with the real state: what is in flight, and every
     item already waiting on the user. An empty template is ignored; a seeded one is read.
  3. `AGENTS.md` "Working loop" gains one sentence: every session reads the log first and
     updates it before it stops.
  4. A dated `D-` entry records why, so the next agent does not delete it as clutter.

  ```markdown
  # Coordination
  ## Now
  <one line: what the repo is doing today>
  ## Workers
  | Branch / worktree | Role | State | Last report |
  |---|---|---|---|
  ## Waiting on the user
  - <decision>: <the exact question> (Q-nnn if parked)
  ## Findings this batch
  - F1 <file:line> <defect> - <open | fixed in <sha>>
  ```
- **Workers by role, not by file.** One builds toward the goal, one verifies, one stages the
  next batch. Two workers never own the same file at once.
- **A landing rule.** A single worker's output is rebased and re-split into one-behaviour
  commits; a parallel batch lands as a `--no-ff` merge whose message is one hand-written
  sentence. Topic branches live minutes to hours, not days.
- **Review by concern after a batch, never per feature.** The reference (git evidence,
  2026-10-01): 2 of its 20 largest merges had any review within an hour; review was named
  read-only agents, one concern each (audit, verify, edges, security), run over a whole
  workstream once it had landed, in two waves — a boundary audit the night after the first
  big landing, security reviews of one new mechanism once it existed — plus a design review
  *before* the risky code was written. Each pass returns a numbered list; each finding is
  fixed in its own commit citing it in the subject, `(F3)`, **and kept as a test** (85 of
  its test names cite a finding). The human makes the calls the list cannot. A normal
  feature gets no review: report, gate, and QA when something reached the screen.
- **QA only when it reached the screen or a value could move.** The reference had no
  checklist and no test plan: it ran the real thing and wrote the number down, dated, in the
  owner doc ("15 of 15", "12 readings each, three rounds, the same answer"); live checks
  stayed behind env flags and out of CI; UI was rendered and looked at. Install the habit as
  one line: *after a scored or live check, the number and the date go into the note that owns
  the fact.* A number that lives only in chat is lost by the next session.
- **The loop itself is a doc, or nobody runs it.** Install `docs/WORKFLOW.md` from Shape K:
  the human's steps, the slice-list shape, what happens between "go" and the report, review
  by concern, QA when needed, the never-list. Owner row in `docs/README.md`.

Removing a worktree inside a synced folder (OneDrive, Dropbox) can print `Permission
denied`: the sync client still holds the directory. Git has already unregistered the
worktree (`git worktree list` no longer shows it); delete the folder later. Report it as
that, not as a failed removal.

If the repo will be published, plan one cleanup pass before it goes public: handoffs, task
files, dated attributions and any private ids removed in one sweep.


## K. `docs/WORKFLOW.md` — the loop at a glance

Fill the angle brackets from Phase 0 (the deny-list, the spine dirs, the paid check, the
human's name). Keep it to tables; the evidence lives in `docs/` history and in this skill.

```markdown
# Workflow

Thin by default: talk, slice, build, land, one report. A small change needs little of this.

## The trust pyramid: where a rule goes
~~~text
   cost    _______________________________________________
    |      \                   Codebase                  /
    |       \   good API design, architecture,          /
    |        \  refactoring                            /
    |         \---------------------------------------/
    |          \          Static analysis            /
    |           \  lints, types, compilers,         /
    |            \ tests, CI                       /
    |             \-------------------------------/
    |              \        Verification         /
    |               \      formal, runtime      /
    |                \-------------------------/
    |                 \         Prose         /
    |                  \ rules, skills, docs /
    |                   \-------------------/
    |                    \      Human      /
    |                     \     review    /
    v                      \_____________/
~~~

| Layer, cheapest first | What it is | Here |
|---|---|---|
| 1. Codebase | good API design, architecture, refactoring | <module layout, import directions, the API contract> |
| 2. Static analysis | lints, types, compilers, tests, CI | <linter, type checker, tests, boundary checks, the gate> |
| 3. Verification | formal and runtime | <strict schemas, spend caps, output checks; models of shared state> |
| 4. Prose | rules, skills, AGENTS.md | <AGENTS.md, CLAUDE.md, docs/, briefs> |
| 5. Human review | <Human> | <what no layer above can decide: a value, a prompt sentence, money> |

A new rule goes in the highest layer that can hold it. A prose rule broken once moves up into a
check. A check's failure message says what to do instead.

## <Human>'s steps
| Step | <Human> | Coordinator | Done when |
|---|---|---|---|
| Grill | problem on paper · argue till it holds | grounds it (owner doc, module, data check) · writes D-, doc, Q- | one sentence + what proves it wrong |
| Slice | read the list · mark mine · "go" | slice list, vertical, each line with its check | every line has a check |
| (build · land · ship) | own lines, or nothing | agents in worktrees · tests · commits · gate · push · CI | — |
| Report | read · answer 0–2 questions | one report after the batch, `PASS/ISSUES/BLOCKED` + quoted output | nothing waiting on <Human> |
| QA | walk it · score it y/n · write the number | — | the number is the verdict |

## Writing the ask
1. Outcome first: what finished looks like.
2. The way is the AI's: it researches and works out the steps.
3. Personal preference and taste come out of a grill / interview.
4. Show what good looks like: references.

## Grill, on paper
Problem (as the user sees it) · Evidence · Done (a sentence a check can say *no* to) · Not.
Observable answer → prototype, don't argue. New layer or shape → two sketches. Third fix at
the same gate → back here, attack the premise. Nothing in D-/doc/Q- changed → skip to Slice.

## Slice
One behaviour sentence · its check · owner (`goal` / `<Human>` / `later`). Vertical: one
thin behaviour through every layer it needs. Dependency order, riskiest unknown first;
lines with no arrow between them run in parallel. >10 lines = two features; >40 min = split.

## Between "go" and the report
Build: one agent per slice, own worktree, 10–40 min; may fan out inside, returns one diff
and one report. Land: periphery lands on the report and the gate; <spine dirs> get their
diff read. Ship: <the push pipeline, or: gate commands → fast-forward main → push → `gh run watch`>.

## Review
| Case | What happens |
|---|---|
| Normal feature | nothing — report, gate, QA |
| <Judgment code> | thought through in Grill before; one review of the diff after |
| After a batch / before a milestone | read-only agents by concern → F1…Fn → one fix commit + one test each → <Human> answers the few that need a call |

## QA — only when it reached the screen or a value could move
Walk it (<the 10-minute real-data walk>) · Score it (<the paid check>, y/n) · Write the
number down, dated, in the owner doc.

## Bugs · Issues · Never
Bug: failing test → fix → pass → one commit. Issue: only big + blocked outside the code,
Context / Options / Done when, closed by "On main now:" or a one-line ruling. Never:
<spine without the human> · <paid runs to test code> · <data that may not leave> · past a
missing decision · a muted red check.
```

## L. Mechanisms learned in production (added 2026-10-12)

Each of these came from one production repo that ran the structure above for a month with
several agents; each exists because one specific thing went wrong. Propose them in Phase 5 or
6 with the reason, never silently.

### L.1 Assertion-count ratchet

The pairing ratchet (Shapes G, check 8) only knows a test file exists. This one reads each
test file at the push base and now, counts the assertion calls (`expect(` or the runner's
equivalent) and fails when a file has fewer, or is gone. The base comes from an env var CI sets
to `github.event.before`; locally, a dirty test dir is compared with `HEAD` and a clean one with
`HEAD~1`, since the commit is then already made. On a first push (all-zero `before`) both fall
back to `HEAD~1`; on a forced push, when the sha is not in the clone, the ratchet prints that it
had nothing to compare and skips. A deliberate
removal is allowed by `drop test:` in the commit subject, which CI reads with `git log -1
--format=%s`, or by `<REPO>_DROP_OK=1` for the local run before that commit exists. Print the
delta per file on every run so the reader sees which check went. Why: 57 checks were deleted in
one commit with nothing noticing.

### L.2 The spine change carries its test

One shell step in CI, before the checks:

```yaml
      - name: Every <spine dir> change carries a test
        env:
          BEFORE: ${{ github.event.before }}
          HEAD_SHA: ${{ github.sha }}
        run: |
          base="$BEFORE"
          if [ -z "$base" ] || [ -z "${base//0/}" ] || ! git cat-file -e "$base^{commit}" 2>/dev/null; then
            base="HEAD~1"
          fi
          changed=$(git diff --name-only "$base" "$HEAD_SHA" || true)
          spine=$(echo "$changed" | grep -E '^<spine dir>/.*\.(py|ts)$' || true)
          tests=$(echo "$changed" | grep -E '^<test dir>/' || true)
          subject=$(git log -1 --format=%s "$HEAD_SHA")
          if [ -n "$spine" ] && [ -z "$tests" ] && [[ "$subject" != *"no test:"* ]]; then
            echo "<spine dir> changed without a <test dir> change and no 'no test:' in the subject:"
            echo "$spine"; exit 1
          fi
```

`no test:` is for a rename, a comment, formatting; the subject says which. The Working loop
sentence "the test lands in the commit that lands the behaviour" was a rule nothing enforced
until this step.

### L.3 Red-test home

`tests/tdd/README.md`: tests written before their fix live here, each a plain script that fails
today on purpose and names the issue it waits for. The gate glob (`tests/test_*.py`,
`tests/drill_*.py`) does not match this folder, so a red test can be committed without muting
anything. The commit that makes one green renames it into the gate glob. A test that turns green
but needs gitignored data moves to a local-check dir instead, since CI has no data for it. This
resolves the contradiction between "write the test first and read the failure" and "the gate is
green before every commit".

### L.4 Cost label and derived deny-list

Every script in the dir that may pay carries, on its own line of the module docstring, one
of:

```
Cost: free - reads <cache>, makes no network call.
Cost: PAID - one LLM call per <unit>; --dry-run only prints the plan.
```

The boundary check fails a script without the line, and builds the deny-list from the `PAID`
lines plus a fixed floor of known names, in case a docstring loses its label. Only the gate scan
reads that derived list; the CI header comment and the hook's own list below are still written
by hand, so the boundary check also reads both as text (the hook's `PAID_SCRIPTS` tuple, the
workflow's leading `#` block) and fails, per side, on a derived name missing from either. A
script added to one list and not the others is otherwise let through by the hook or unwarned in CI.

### L.5 Paid-run hook (Claude Code) (Full only)

`.claude/hooks/guard_paid_run.py`, registered as `PreToolUse` on `Bash|PowerShell` in the repo's
`.claude/settings.json`: reads the tool call JSON from stdin, denies a command whose text names a
deny-listed script unless it carries `<REPO>_PAID_OK=1` (an estimate-only invocation, the script
without its `--go`, passes), with the push pipeline (L.8) a plain `git push` too, lets everything else through, and lets unreadable input through too, so a broken hook cannot stop every command. The agent adds the
marker only after the user's go for that run, never to get past a block; the rule says so in
`CLAUDE.md`. Limit, stated in the docstring: it reads the command text, so a scratch script that
imports the paid module is not caught. The hook gets its own test in the gate.

Hardened since 2026-10-23: the hook fails closed on a shell it cannot read (`bash -c`, `sh -c`,
`Start-Process`, `uv run`, `python -` on stdin, a pipe into an interpreter or `xargs`), lets a
deny-listed file name through only in read-only git shapes (`git log`, `diff`, `show`, `grep`,
`add`, `commit`), keeps `FREE_PROGRAMS` and `PIPE_READERS` lists of commands that only read, and
denies `git help` or `--help` (it opens a browser on Windows), a bare `git stash` (the stash stack
is shared by every worktree), and a line continuation that hides `--go`. A script that only prints
an estimate without `--go` is listed apart (`ESTIMATE_ONLY_WITHOUT_GO`). The template keeps
`PAID_SCRIPTS`, `FORMER_PAID_SCRIPTS` and `MODULE_ROOTS` as placeholders and the marker as
`PROJECT_PAID_OK`; rename all of them from the Phase 0 survey. When `guard_private_paths.py` (L.26)
is carried, the hook also denies a recursive `grep`, `rg`, `findstr` or
`Get-ChildItem -Recurse | Select-String` that can reach a protected folder of the repo, and imports
its `reaches_protected`.

### L.6 Budget ledger

A fixed docs row when a deny-list exists: before each paid run, the script's own estimate and
the balance after it; after, the actual from the script's output, in the same commit as the
run's findings. Estimates ran about 2x low when many pages were sent, so the row says that.

### L.7 Typecheck baseline

`tests/pyright_baseline.txt` (or the tsc equivalent): errors per file on the day the checker was
added. The check fails a file with more errors than listed, and a file with fewer until its line
is lowered: counted exemptions applied to types, so a code base with old errors still gets a
checker today.

## M. Templates and the mechanisms added 2026-10-19

`templates/` beside this file holds working copies of every row of L.11, taken from the
production repo on 2026-10-19 (commits 6ce92bf to 1069187; the push pipeline from 55f27e7, 2026-10-21; the housekeeping and after-compaction hooks from origin/main d5bf177, 2026-10-23; refreshed from origin/main on 2026-11-26: the paid-run guard, revert-and-rerun, drill runner, boundary checks, CI workflow, `commit_range.py`, and the new `guard_private_paths.py` and `worktree_setup.py`; `ship.py`, `drill_ship.py` and `settings.json` the same day, after the ui-compare step landed). They carry that repo's names: the `PROJECT_` env
prefix, its `SCOPE` and `HIGH_RISK` dirs, its D-ids and its paid scripts. Copy, then rename
every one of those from the Phase 0 survey; never install them unchanged. `ship_briefs/review.md`
names that repo's rules and is rewritten from the target's own `AGENTS.md`.

### L.11 Carry-over inventory: everything the production repo runs

Phase 0 lists this table with a yes / no / not-applicable per row; nothing is installed unasked. Rows tagged (Full only) are `no` under Yolo (Setup section above); the settings.json row drops their entries.
User-level rows already act in every repo on this machine; copy them into the repo only when
other people or cloud sessions must get them too.

| Piece | Template | Level | Carried when |
|---|---|---|---|
| Paid-run guard (L.5) (Full only) | `hooks/guard_paid_run.py`, `tests/drill_guard_paid_run.py` | repo | a deny-list exists |
| Protected folders denied to the file tools, repo-bounded (L.26) (Full only) | `hooks/guard_private_paths.py`, `tests/drill_guard_private_paths.py` | repo | private content must stay out of the session (reports, customer data, caches) |
| Worktree setup: link gitignored caches, copy `.env` (L.27) | `hooks/worktree_setup.py`, `tests/drill_worktree_setup.py` | repo | agents run in worktrees and a run needs gitignored caches or `.env` |
| Per-commit test rule over a pushed range (L.28) | `tests/commit_range.py`, `tests/drill_commit_range.py` | repo | CI and the boundary checks share it; the spine-needs-a-test rule |
| Before/after screenshots of a UI change (L.8) | `ui-compare/{SKILL.md,ui_compare.py,test_ui_compare.py}` copied to `~/.claude/skills/ui-compare` when missing; a `.ui-compare.json` and a screenshot spec on invented data in the repo | user + repo | the repo has a UI |
| Push pipeline: reviewer, verifier, fixer, document pass, trunk report (L.8) (Full only) | `hooks/ship.py`, `hooks/ship_briefs/{review,verify,fix,document}.md`, `tests/drill_ship.py`, `THIRD_PARTY_NOTICES.md` | repo | code pushed by agents |
| Revert-and-rerun check (L.13) (Full only) | `hooks/mutation_check.py`, `tests/drill_mutation_check.py` | repo | the pipeline is carried and its tests run in a second worktree |
| Issue proof template (L.14) | `github/ISSUE_TEMPLATE/task.yml`, `config.yml` | repo | GitHub remote and the repo tracks issues |
| Launch phase (Shapes O) | none; a `Q-` entry and a plan | repo | parked until real users |
| Worktree housekeeping at session end (L.17) | `hooks/housekeeping.py`, `tests/drill_housekeeping.py` | repo | agents run in git worktrees |
| Post-compaction re-read (L.18) | `hooks/after_compact.py`, `tests/drill_after_compact.py` | repo | Claude Code sessions run long; with a coordination file (Shapes J) |
| Hooks wired: the guard before every shell command, `guard_private_paths.py` on `Read|Grep|Glob`, `ship.py --status` on `SessionStart` startup/resume, `after_compact.py` on `SessionStart` compact, `housekeeping.py` on `SessionEnd` | `hooks/settings.json` -> `.claude/settings.json` (drop the entries of hooks not carried) | repo | any hook carried |
| Drill runner that fails on an empty glob (L.10); an `ALONE` list of drills that must not share the machine | `tests/run_drills.py`, `tests/drill_run_drills.py` | repo | Python, no runner |
| Boundary checks: citations, cost labels, three-list deny-list agreement, AGENTS.md 8 KiB (line endings normalised), drill-count ratchet that follows renames and judges each commit of a range, citations also scanned in the hooks and briefs, the paid-script lists compared both ways | `tests/drill_boundaries.py` (Shapes G) | repo | always; cut to the confirmed checks |
| CI gate | `github/verify.yml` (Shapes F) | repo | GitHub remote |
| Plans doc (L.9) | `notes/PLANS.md` | repo | always |
| Issue loader skill (`/issue-context N`) | `claude/skills/issue-context/SKILL.md` | repo | `gh` works and the repo tracks issues |
| Repo facts for auto mode (approved providers, paid scripts, sensitive files) | `claude/settings.local.example.json` -> `.claude/settings.local.json` | repo, untracked | auto mode is used |
| Implementer subagent (briefed, worktree, stops on ambiguity) | `claude/agents/implementer.md` | user | already global; copy to `.claude/agents/` only for other people |
| Trust pyramid (L.20) | Shapes K, first section of `docs/WORKFLOW.md` | repo | always |
| Prompt rules of thumb (L.25) | Shapes K, "Writing the ask" in `docs/WORKFLOW.md` | repo | always |
| Working agreement for Claude only: swarm by default, the agent review rule, approval before acting, failures get a permanent fix, definition of done for issues, paid-run estimate, code-question rotation, compact instructions (L.18) | `claude/CLAUDE.example.md` (sections "Working agreement", "Paid runs & budget", "Compact Instructions") | repo | always; each rule only once its mechanism is installed |
| Rules for every agent | `claude/AGENTS.example.md` (Shapes A shows the shape) | repo | always |
| Coordination log | Shapes J | repo, gitignored | parallel sessions |
| Harness matrix in the root README | Shapes N | repo | always; rebuilt on every run |
| Humanizer and pyright plugins | `~/.claude/settings.json` | user | already global; never copied, it is personal |

The two `*.example.md` files are reference, not templates: take a section's shape, never its
D-ids, paths or domain words.

### L.8 Push pipeline (Claude Code) (Full only)

A commit is instant; the review runs at the push. An agent pushes only with
`python .claude/hooks/ship.py --intent "<the ask and the Scope: line>"`, started as a Claude Code
background job so the session wakes when the run ends or asks; the guard (L.5) also denies a
plain `git push`. Templates: `hooks/ship.py`, `hooks/ship_briefs/{review,verify,fix,document}.md`,
`tests/drill_ship.py`; logic and prompts are ported from Kun Chen's no-mistakes (MIT), so
`THIRD_PARTY_NOTICES.md` goes in with them. In a detached worktree of HEAD under the system temp
folder, never the caller's checkout, it runs fixed steps:

| Step | What it does |
|---|---|
| intent | the ask and the session's Scope: line, else the commit subjects and cited issues; handed to every later step, never blocks |
| rebase | onto the remote default branch; a spine conflict asks the human, a leaf one goes to the fixer |
| review | one read-only headless `claude -p` reviewer on the strong model judges the range against the intent, bloated tests included |
| verify | one fresh verifier per defect |
| test | the targeted tests (changed tests and tests naming a changed file), lint and typecheck, and for spine code the revert-and-rerun (L.13) |
| document | one pass naming the owner doc of each stale fact; a gap is advice |
| lint | `ruff format` and `ruff check --fix` (or the stack's twin) outside the spine, then the check; last, so it cleans every fix |
| push | only the reviewed head or one descending from it, never forced |
| ci | watches the workflow, which runs the whole gate; a red test the test step did not pick is logged as a selection miss |

Who acts on a finding: on leaf code the verifier gates the fixer, an agent fixes only a
confirmed defect, and a failed step is fixed and rerun at most 3 times, else the change is dropped
and logged for the weekly count; a leaf fixer's "not a defect" drops the change quietly, except in
the document step, where it passes on to lint. A leaf change never comes back to the human. The
reviewer flags bloated tests and the fixer removes rather than adds. On spine code the
verifier is advice only: the finding stops the run and reaches the human with the verdict and the
evidence, one per message, and `--resume <run id> --answer "<id>: fix|drop|not a defect because ..."`
continues on the ruling; no agent edits the spine.

Hand-back (added 2026-10-23). Three path classes, one test for both `resume()` and the ask file
(`leaf_ask()`), so the two cannot drift apart:

| Path | Confirmed finding | A "fix" answer |
|---|---|---|
| leaf (outside the spine and the hooks dir) | goes to the fixer, no ask | (no ask) |
| hooks dir (`.claude/`: the hooks, the pipeline, its briefs) | verified like leaf, but asked, never fixed | hands the change back to the session; the run ends `handed_back` (exit 3) |
| spine | asked, the verdict as advice | hands the change back to the session, whatever the other answers say |

A leaf fixer's "not a defect" drops the change, also beside a spine finding and also after the
human's own "fix"; only a fixer that touches or names the spine makes the run ask again. "drop"
and "not a defect because ..." only dismiss the finding; the run then goes on from the next step.
A rebase ask hands back on any answer (the rebase was aborted, nothing can be pushed from that
HEAD); a CI ask's commit is already on the remote, so "fix" hands back for a new commit and the
other two leave it as it is. The ask file spells out, per finding, what each answer does to it,
and the push once for all answers on one closing line. Why: Claude Code refused every fixer edit
under `.claude/` in its don't-ask mode whatever `--allowedTools` said (two runs, 2026-10-23), and
the human chose the hand-back over widening what an agent may change in the hooks; and "drop" was
read as "throw the change away" when it only dismissed the finding.

Children run read-only (`--allowedTools Read,Grep,Glob`, `--permission-mode dontAsk`,
`--no-session-persistence`) and bill against the user's Claude plan. The run record is
written after every step to a gitignored `ship_runs/<run id>.json`, finished runs add a line to
`ship_log.jsonl`, except a leaf change its fixer called "not a defect", which is dropped with no
line. Exit 0 landed and CI green; 2 asks (`<run id>.ask.md`, worktree kept); 3 nothing landed,
CI red, or the change handed back; 1 the pipeline failed. A run cut off with its session is not resumed: `SessionStart`
runs `ship.py --status`, which prints one line for it, and it is restarted by hand. No pre-push
hook; a commit-msg hook, if any, keeps only cheap subject checks. Stub env vars replace the
children and `gh` for the drill.

Why: the commit-time review it replaced (three finders and a verifier on every code commit) made
every commit wait, median 49 s and up to 502 s, at 4.81 review rounds per landed commit, and the
committing session could do nothing else meanwhile. The 3 tries are the limit no-mistakes and the
Claude Code team both use: a problem three tries do not fix is not mechanical. No-mistakes has no
verifier because a person rules every finding; here agents fix leaf findings alone, so the verifier
gates them, and on the spine it never filters, since a wrong refutation would hide a real defect.

The pipeline does not replace the human's reading of the spine diff; it is a second reader.

For a repo with a UI, glendonize installs `ui-compare` from `templates/ui-compare/` into
`~/.claude/skills/ui-compare` (only when it is missing; run `python test_ui_compare.py` there once)
and writes the repo's `.ui-compare.json` plus a screenshot spec that runs on invented data only. It
shows the person before and after screenshots of a UI change in the browser, so they judge the
change by what they see instead of by reading the code. The push pipeline calls it on a UI
change; it is a look for the human, not a gate, and a repo without a UI skips it.

**Trunk report: removed 2026-10-21.** The annotated-diff report after the push, and a verifier on
every fixer edit of a test in the test and CI steps, were both chosen and then dropped the same
day as additions that answered no failure that had happened. A spine finding reaches the human as
the run's ask, which replaces the report. Carry neither unless the target repo has the failure.

### L.12 Review report

Folded into L.8, then removed with the trunk report (2026-10-21).

### L.13 Revert-and-rerun (mutation check) (Full only)

Inside the pipeline's test step, for a range that changes spine code, `hooks/mutation_check.py`
(drill `tests/drill_mutation_check.py`) proves the tests pin the change. It adds a detached
worktree of the range's base outside the repo, applies only the test-dir part of the range diff
there, and runs the tests that cover the change: test files added or changed in the range, else
test files whose text names a changed module's stem. Credentials are blanked as the gate runner
does. Status per spine file:

| Status | Meaning | Effect |
|---|---|---|
| `pinned` | at least one test fails against the reverted code | reported |
| `unpinned` | all green without the change, or no test names the change | the run stops and asks the human (a refactor with no behaviour change is answered `not a defect because ...`) |
| `no_drill` | every spine commit in the range says `no test:` (or `no drill:`) | allowed, reported |
| `skipped` | worktree, apply or timeout failure | reported with the reason; never raises |

The worktree is removed with `--force` and pruned in a `finally`. Why: a test that stays green
when the code it covers is undone tests nothing, and the assertion-count ratchet (L.1) cannot see it.

Since 2026-11-26 the check is faster and stricter. Spine files are reverted in parallel
worktrees (`min(4, CPU count)` at once, `PROJECT_MUTATION_WORKERS` overrides); drills named in the
`ALONE` tuple never run beside another drill; a file's reverted run stops at its first red drill;
the worktree is committed with the range's own message (`worktree_message`) so a drill that asks
git for the subject or the tracked files sees the real thing; the patch goes to `git apply` as
bytes, because Windows text mode converts a lone CR and breaks a patch that appends non-ASCII
lines at the end of a file; and drill selection is import-aware: a drill is picked when it imports
the changed module, imports a module that imports it (a lazy import inside a function counts), or
names its file, never because its prose says the word.

A call-site change needs an entry-point test (2026-10-23). A one-line change in the spine's
entry point that only passed an argument through to a function (the pipeline handing the sent
pages to the review-flag builder) came back `unpinned`, although that function had its own test:
a test of the callee stays green when the caller stops passing the argument. Only a test that runs
the whole entry point in its free fake mode (stubbed model, invented input) and checks the
argument's effect in the output pinned it. So when a spine change is a call site, the pinning test
drives the caller, not the callee; a repo whose entry point has no fake mode gets one before such
a change can be pinned.

### L.14 Issue proof template

New issues carry a required **Proof** section and a **Done when** section naming the target metric
(`templates/github/ISSUE_TEMPLATE/task.yml`; a bug form follows the same two sections). Proof is:
run tag with the numbers quoted, files, the test that pins the change, a screenshot where one
fits. The closing comment has the same shape ("On main now: ..."), kept as a short block at the end
of the template's description, since GitHub has no comment template. A boundary check reads every
template and fails one missing either section.

### L.15 Pre-push spec review

Removed: no git pre-push hook. The pipeline's intent step (L.8) hands the ask, the Scope: line or
the cited issues to the reviewer, which judges the range against them.

### L.16 Review is a gradient

Anchor every review on safety, not on a fixed ritual: how large is the blast radius, and can the
change be gated or rolled back. The smaller both are, the lighter the review; a leaf finding is
settled by the verifier and the fixer with no human, a trunk range adds the human's ruling, the
report and the revert-and-rerun. A change behind a feature flag with a one-step revert can ship
lighter than a migration. Trunk-or-leaf by directory (L.8) is the cheap proxy for this; where the
survey finds a change class that is both large-radius and irreversible (a data migration, a cache
key, a schema), name it as trunk even outside the spine dirs.

### L.9 Plans doc

`notes/PLANS.md` (template in `templates/notes/PLANS.md`): work that runs over more than one
session, written where every session and every subagent reads it, because a plan kept in one
session's memory or the gitignored coordinator log is invisible to the others. Each plan names
its goal, a "Done when" line a number can check, its steps with their state, and a dated log of
the choices made on the way, each pointing at its `D-`/`Q-`/issue. A step's state changes in the
same commit as the work that moved it. A finished plan is never deleted: it moves to Completed,
its steps folded into one line, with the numbers that met "Done when"; a dropped plan moves there
with its reason. A plan holds no rule and no decision of its own. Modelled on OpenAI's
`exec-plans/active` + `completed`, kept as one file while the docs dir stays flat.

### L.10 Vacuous-pass guards

Each of these let a run print green while checking nothing, in the production repo:

- The gate runner fails when its glob found no check at all (`templates/tests/run_drills.py`,
  pinned by `drill_run_drills.py` on an empty temp dir).
- The typecheck baseline fails on a line whose count is 0: such a line hides that the file is
  clean, and lets it regress unnoticed back to one error.
- `AGENTS.md` over 8 KiB fails the boundary check; when it grows past the cap, trim by moving
  Claude-only rules (what a hook enforces, approval words, swarm sizing) to `CLAUDE.md` and
  deleting duplicates, never by dropping a rule.
- CI: `permissions: contents: read`, cancel only pull-request runs, Playwright `forbidOnly` in CI.
- The citation check scans every tracked source root including the spine and the root rule
  files, and resolves doc paths against tracked files, not the disk.

### L.17 Worktree housekeeping at session end (Claude Code)

`hooks/housekeeping.py` (drill `tests/drill_housekeeping.py`), registered as `SessionEnd` in the
repo's `.claude/settings.json`. Agent runs leave a git worktree and a `worktree-agent-*` branch
under `.claude/worktrees/` each; nothing removed them, and Windows left stale
`.git/worktrees/<name>` entries read-only, so every commit printed "failed to delete ...:
Permission denied". Each pass:

- clears the read-only flag on stale admin entries only (never a live one) and runs `git worktree prune`;
- removes an agent worktree, with its branch, only when nothing in it can be lost: no change, no
  untracked file, its commit in the default branch (also under another hash, by `git cherry`, since
  the push pipeline rebases), last commit and last git activity both older than 24 h, and no
  gitignored file except what is rebuilt for free (caches, `node_modules`, build output, the
  `settings.local.json` copy Claude Code puts in every worktree) or a paid cache whose every file
  the main checkout already holds at the same size. A folder git reports as one ignored line is
  judged file by file;
- keeps, and counts by reason, a dirty, unmerged, young or folder-missing worktree, a gitignored
  output (`git worktree remove` would delete it silently), and a paid-cache file main lacks;
- deletes a `worktree-agent-*` branch no worktree holds when the default branch has every commit
  of it, and a folder git no longer lists when it holds only links and empty folders; a link (an
  agent's junction to the main cache) is unlinked, never followed, and a folder with a real file
  stays;
- appends one JSON line to the main checkout's `.claude/orchestration/housekeeping.log`, never the
  worktree's (a log there is a gitignored file that keeps that worktree forever), and exits 0 on
  any error. `--dry-run` prints what would go.

What went wrong, in order (2026-10-21 to 23): the `SessionEnd` entry was lost in a checkout reset,
so the hook never ran; once back, it kept every worktree, because each held the `settings.local.json`
copy, and because its own `git status` rewrote the index, so activity read from the admin folder
said every worktree was used seconds ago. Activity is now read from the admin files without the
index and the folder itself, and the drill runs one case at the real clock, plus a check that the
hook is registered. It touches no worktree outside `.claude/worktrees/` (the pipeline's and the
mutation check's temp worktrees clean themselves).

### L.18 Compaction setup (Claude Code)

Three levers, all in the harness rather than in the human remembering `/compact`:

- a smaller auto-compact window in the user's own `~/.claude/settings.json` (300k in production),
  so a summary is made from a short transcript; a status line that warns as the window fills;
- a `### Compact Instructions` section in `CLAUDE.md` naming, in order, what a summary keeps: the
  task with its done-when line and proving command, every decision waiting on the human with its
  briefing, every agent in flight, the session's commits by hash and whether pushed, the gate
  state, the estimate, go and spend of any paid run, uncommitted files; and what it drops (tool
  output, sensitive text);
- `hooks/after_compact.py` (drill `tests/drill_after_compact.py`), a `SessionStart` hook with
  matcher `compact`, whose `additionalContext` re-reads from disk the tail of the coordination
  file (Shapes J), the last commits and `git status --short` of the folder the session runs in.
  Those win over the summary: the coordination file is the working state, and a hold another
  session wrote there is newer than any summary. The coordination file is gitignored, so a session
  in a worktree reads it from the main checkout (the parent of the common git dir). It prints
  nothing on any other start, a failure becomes a one-line note in the context, every path exits
  0, and its three git calls fit inside the hook timeout (the drill checks that against settings.json).

What went wrong: no `/compact` was ever run by hand in a long session, and auto-compaction fired
near the model's full window, so each summary was squeezed from a huge transcript and dropped
holds, gos and gate state. Rejected: a hook that starts a compaction (Claude Code has none), one
that writes into the summary (`PreCompact` cannot), keeping the summary rules in memory (memory
does not survive a compaction; `CLAUDE.md` is re-read from disk).

### L.19 Commit with a pathspec in a shared checkout

Several sessions share one checkout and so one git index. "Stage only that change's files" is not
enough when another session stages too: on 2026-10-23 a plain `git add <mine> && git commit` swept
another session's two staged hook files into an unrelated commit, which was undone with
`git reset --soft HEAD~1` and recommitted. The rule: in a shared checkout, commit with
`git commit -m "..." -- <paths>`, which commits only those paths whatever else is staged, and read
`git show --stat HEAD` after every commit. In production this is so far a session-memory rule, not
a line in the repo's rule files; carry it into `AGENTS.md` "Working loop" when the target runs
parallel sessions in one checkout.

### L.20 The trust pyramid decides where a rule goes (added 2026-11-16)

Lauren Tan's (@poteto) "how do I trust my agents more?" pyramid, adopted in production as the order
for the whole development. Upside down, cost growing downward: **codebase** (API design,
architecture, refactoring) → **static analysis** (lints, types, compilers, tests, CI) →
**verification** (formal, runtime) → **prose** (rules, skills, AGENTS.md) → **human review**. The
skill applies it to every candidate it proposes: a rule goes in the highest layer that can hold
it; a rule that can be a type, a lint or a test is never written as prose; a prose rule broken once
moves up into a check (the failure-gets-a-permanent-fix rule); human review is spent only on what
no layer above can decide (a value, a prompt sentence, money).

Where the skill uses it: Phase 0 puts a layer on every candidate, Phase 7 writes the figure and the
table into `docs/WORKFLOW.md` (Shapes K) with each layer mapped to the target repo's own files, and
the highest empty layer is the first thing proposed. An automated agent review counts as prose: it
reads rules and can miss, so it never replaces a check. A check's failure message says what to do
instead (L.21). Deeper layers: L.22 is the codebase layer, L.23 the verification layer.

### L.21 No comments, and checks that teach (added 2026-11-16)

A comment is prose inside code: nothing enforces it, it can be wrong while every check stays green,
and it excuses code that does not do the right thing. Production removed about 2,500 comment lines
in one day. The rule for the target: no comments in source, except where a person reads the
program as text (in production: the marker line above each step file's one entry function, the
comment on each call inside it, and the step comments of the top-level run function); one file
docstring per file, holding a `Register:` line with the ids the removed comments cited; function
docstrings only on those entry functions. Why a line exists goes in the commit message or the
decision entry; a behaviour claim goes in a test.

How to remove them without losing knowledge, learned the hard way:
- Before a removal lands, every comment that holds a fact found nowhere else is sorted: a vendor
  or platform limit → `PLATFORM_CONSTRAINTS.md`; a design reason → the owner doc; a behaviour a test
  can pin → a test, red with the code line reverted. In production three of four areas landed
  before this step and the facts had to be dug back out of `git show`.
- Proof per file: AST-equal to the old file once docstrings are stripped from both sides, the full
  gate green, and for the value-producing code a replay of saved results with zero differences.
- One agent per area (spine, rest of the source, tests, eval/hooks), files owned by other running
  agents left out and done last.

The check that blocks new comments, like every check the skill installs, prints a message that
tells the agent what to do instead ("move the why into the commit message; a behaviour claim
into tests/<x>"), never only "comment found". Agents follow a check that teaches; they patch around
one that only refuses.

### L.22 One entry function per step file (added 2026-11-16)

The codebase layer of L.20. Each pipeline step file ends with exactly one entry function under a
marker line (`# ---- main: the only function another file imports ----`); it is a short list of
helper calls, one comment each, no loop; helpers sit above it in the order it calls them. Another
file imports only that entry function (constants excepted). Helpers used by several steps live in
a `helpers/` folder of a few topic files named after what they hold (not `shared_*`, not one file
per helper). The top-level run function reads as the steps in order, one commented call each. A
test pins it: entry function last, marker above, imports only entry functions, no loop in an entry
function. Proven move-only by the same replay and byte checks as L.21.

### L.23 Formal verification for shared state (added 2026-11-16; first model built in production the same day)

The verification layer of L.20 for the parts where several processes change the same state at once:
a cost ledger with reservations, job claims with leases, idempotency keys, per-file OCR marks.
TLA+ with TLC: one module for the job lifecycle and the ledger, one for the file-processing worker;
money as integers, the clock and model content abstracted, 2–3 users/jobs/workers so TLC finishes
in about a minute. A design swarm of four read-only agents (state inventory, first spec, tooling,
code conformance) found that every bug of the month in the job and ledger code was an invariant
violation a model checker would have shown. Tooling: TLC needs Java 11+ (check the local machine
first; a Windows box often has Java 8), the jar pinned with a checksum, specs in `formal/`, a test
that runs TLC and turns a counterexample into a step-by-step message. Code conformance starts
small: a plain test that every function writing shared state maps to a spec action and back,
which catches a new write path the day it is added; trace validation only once drift is seen.

Built in production so far: one module for the job lifecycle, the spend ledger and the idempotency
key, run by one drill through a vendored, hash-pinned TLC. Two gate configs, about 11 s and 10 s,
because no single config at full depth ends in under a minute: one wide (2 users, 2 jobs, 2
workers), one deep (1 job, two days, a fault, a resent key). Every invariant carries a `why:` line
with its decision id, and a config that loses an invariant turns the drill red. Invariants TLC finds
false on the code as it is go to `formal/tdd/`, outside the gate, until the fix lands; ten were
there at the last look (2026-11-24). Not built: the file-processing worker's module. No code
conformance test was found in the production drills.

### L.24 Swarm hygiene (added 2026-11-16)

Three failures from one day of parallel agents, each now a line in every brief:
- **Unique scratch names.** Agents share the session scratchpad; two agents both wrote
  `strip.py`, one overwrote the other's mid-run and broke its files. A brief gives each agent its
  script-name prefix.
- **The push runs in the background, never under `timeout`.** A push pipeline run takes longer than
  a shell timeout; one agent's run was killed at 10 minutes before it pushed.
- **The drill line in a commit subject must be true.** A refactor commit that changes no test says
  `no drill:` and why; a brief that told agents to name a drill on every commit got eight commits
  rejected by the per-commit drill rule. Fold a multi-agent refactor branch into one commit per
  behaviour before shipping.

### L.25 Rules of thumb for a prompt (added 2026-11-24)

The user's four rules, written into `docs/WORKFLOW.md` (Shapes K, "Writing the ask"):
- **Write the outcome.** What finished looks like.
- **Let the AI figure out the way** and do the research.
- **Grill / interview** to get personal preference and taste.
- **Show what good looks like:** references.

### L.26 Protected folders denied to the file tools (added 2026-11-26) (Full only)

`hooks/guard_private_paths.py` (drill `tests/drill_guard_private_paths.py`), a `PreToolUse` hook on
`Read|Grep|Glob`, for a repo whose agent session must never see some content (customer reports,
personal data, caches of either). `PROTECTED_FOLDERS` is a tuple of path-part tuples, relative to
the repo root, with `fnmatch` wildcards; `PROTECTED_SUFFIXES` denies an untracked file of a type
(a PDF the repo does not hold), `ALLOWED_ENV` names an optional switch that turns the hook off.
Rules: only a path INSIDE the repo's protected folders is denied, a path outside the repo is never
blocked, whatever its folders are called; the deny reason starts with `Private:` and tells the
agent to hand that step to the person's own approved tool; unreadable input passes and a crash
in the decision denies. The shell guard of L.5 imports `reaches_protected`, which also flags a
folder above a protected one, so `grep -r .` from the repo root is caught.

What went wrong (2026-11-26): the first version of the shell-side search guard matched the
protected folder names anywhere in a path, so `ls -R` and `grep` over `~/.claude/skills` were
denied because a folder there was called like a protected one. The repo-bounded rule fixes that,
and both drills pin the outside-the-repo case, the file-tool one and the shell one.

### L.27 Worktree setup (added 2026-11-26)

`hooks/worktree_setup.py` (drill `tests/drill_worktree_setup.py`): an agent worktree starts without
the gitignored files a run needs, so every agent re-created a cache or lacked `.env`. The script
finds the main checkout from `git rev-parse --git-common-dir`, links the folders in `LINKED`
(a junction on Windows, a symlink elsewhere, so a cache is shared and never copied), copies the
files in `COPIED` that the worktree lacks, and leaves anything that already exists as it is. It
refuses a folder that is no worktree (exit 2), does nothing in the main checkout, and
`--dry-run` lists what it would do. The agent brief names it as the first step in a worktree.

### L.28 Per-commit test rule over a range (added 2026-11-26)

`tests/commit_range.py` (drill `tests/drill_commit_range.py`) is the one place that judges a pushed
range commit by commit: each commit that changes a spine file must itself change something under
`tests/` or say `no drill:` in its own subject, and no commit may lose an assertion call unless
its own subject says `drop drill:`. CI runs `python tests/commit_range.py "$BEFORE" "$HEAD_SHA"`
instead of an inline shell step, and boundary check 9 imports its helpers. Why: judging the
range by its last subject let an earlier spine commit ride on a later commit that touched the tests
or carried the marker. A base of all zeros or an unknown commit falls back to `HEAD~1`; a drill
moved to another drill name is followed, one moved out of the gate counts as gone.

## N. The Harness matrix in the root `README.md`

The README shows the whole harness at a glance, in the format of
github.com/nexu-io/harness-engineering-guide: a table per group, the file as a relative link
in the left column, one short plain sentence in the right. Rules for it:

- Rows come from `git ls-files`, never from this list: a file that is not tracked is not a row,
  and a path is never guessed. Ignored files (the coordination log, `settings.local.json`) are
  left out.
- One table per group, in this order, a group with no file dropped: **Rules** (`AGENTS.md`,
  `CLAUDE.md`), **Register** (REQUIREMENTS, DECISIONS, OPEN_QUESTIONS, PLATFORM_CONSTRAINTS,
  the budget ledger), **Checks** (boundary checks, the test ratchet and its list, the drill or
  test runner), **Gate** (the CI workflow or the local gate script), **Hooks** (the paid-run
  guard, the protected-folder guard, the push pipeline and its briefs, the worktree-setup,
  housekeeping and after-compaction hooks, the settings file that wires them), **Docs** (the docs index,
  WORKFLOW, PLANS).
- One row per file, one line per row. The description says what the file stops going wrong, in
  plain words: no register ids, no emoji, no trailing stop.
- Header row `| Topic | Description |` with `|---|---|`. A horizontal rule `---` above the
  section, none inside it.
- If the repo's README already opens in the nexu style (centred title, italic tagline, badges),
  keep it; if it has no README, propose that opening too, with badges only for what is real
  (license file, CI workflow).

```markdown
---

<!-- harness:start -->
## Harness

How agents are kept safe in this repo. Regenerated by `/glendonize`; edit outside the markers.

### Rules

| Topic | Description |
|---|---|
| [AGENTS.md](AGENTS.md) | The working agreement every agent reads first |
| [CLAUDE.md](CLAUDE.md) | Rules only Claude Code can follow, on top of AGENTS.md |

### Register

| Topic | Description |
|---|---|
| [DECISIONS.md](docs/DECISIONS.md) | Every settled decision with its reason, or a note that none was recorded |
| [OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) | What is still undecided and the exact step that would settle it |

### Gate

| Topic | Description |
|---|---|
| [verify.yml](.github/workflows/verify.yml) | Runs the free checks on every push and holds no secrets |
<!-- harness:end -->
```

## O. Launch phase (parked; Phase 9)

Applied once the product has real users. Until then it is a `Q-` entry and a plan, not code.
Each row is proposed with its reason, and only where the repo has something to attach it to.

| Row | What it is | Reason |
|---|---|---|
| Feature flag and kill switch | every user-visible feature ships behind a flag that can be turned off without a deploy | the fastest rollback is not a revert and a rebuild |
| Canary release | the change reaches a small, named cohort first (a percentage or an internal group), not everyone | a defect then reaches few users, the blast radius of L.16 made real |
| Observability | crashes and errors per release, plus the product signals that say whether the change did its job (the "Done when" metric of the issue) | a canary nobody watches is a full release |
| Expand or roll back | a written decision after a fixed observation window: widen the cohort if the signals hold, flip the switch if not; the outcome is a dated `D-` | rollback is quick only if the decision was made in advance |

Park conditions: no flag system, no telemetry, or no users. Name what is missing in the `Q-`, and
the act that settles it ("the owner confirms the first external users and the telemetry vendor").
