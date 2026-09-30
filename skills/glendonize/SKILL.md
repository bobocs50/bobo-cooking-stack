---
name: glendonize
description: Give a repo a structure modelled on glendonC's many-minions and 1321 so parallel agents can work in it safely — an AGENTS.md working agreement, a numbered R/D/Q register that code cites, PLATFORM_CONSTRAINTS with VERIFIED/ASSERTED facts, boundary checks that read source as text, a free-only gate, a test beside every source file enforced as a ratchet, and a numbered docs/ set written from an owner index. Gated phases; writes nothing on the first pass; mines what the repo already says; parks what it cannot verify. Use when the user invokes /glendonize, says "glendonize this", "make this repo agent-ready", "structure it like many-minions", or asks for a decision register, constraints doc, boundary checks or a gate.
---

# Glendonize

Install, in the repo at `$ARGUMENTS` (a path) or the current directory, a structure
modelled on glendonC's many-minions, with the docs governance of his public repo
glendonC/1321 (owner index, status block, review rule, per-change check table). Neither
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
missing (usually the register) and offer only the phases that add something.

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
| `README.md` | outward-facing; links the docs index, never copies it |
| `.gitignore` | includes `.claude/worktrees/` |
| `.env.example` | one line per secret, no values, a comment saying which steps need none |
| `docs/README.md` + fixed docs | the owner index and its rows — Shapes C |
| `docs/REQUIREMENTS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md` | `R1`…, `D-001`…, `Q-001`… — Shapes D |
| `docs/PLATFORM_CONSTRAINTS.md` | external facts, VERIFIED or ASSERTED — Shapes E |
| `docs/<DOMAIN>.md` × n | one per contract several parts of the code honour; pattern only, names come from the repo |
| `docs/local/` | optional; gitignored scratch and handoffs; no tracked doc links it |
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

Never replace an existing linter.

With a runner, also measure **pairing**: the test-file convention the repo already uses
(`x.test.ts` beside `x.ts`; `tests/test_x.py` for `pkg/x.py`), how many source files have
a test by that convention, and the list of those that do not — that list is the ratchet's
baseline (Phase 5). A heavily tested repo can still leave a large share of its source
files without a sibling test when nothing enforces the pairing; report the real ratio,
not "1:1". Without a runner there is no pairing to measure; say so.

**2. Free vs paid.** Mine candidates: prose saying costs / bills / per page / per call /
real money / do not run; modules reading env vars matching `KEY|TOKEN|SECRET|ENDPOINT`;
modules importing a paid SDK. The user confirms the deny-list. A repo with none gets an
empty deny-list and a line saying so. A gate step is free only when the survey can show
it: no network, no credential read, no paid import. In doubt, paid.

**3. Bans.** "Do not add X", "there is no X and don't create one". Banned things are
never proposed. Name the ban and what replaces it.

**4. Candidates, each with provenance:**
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

**7. Phase menu.** Phases 1–8, one line each on what they add here; which to skip.

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

With a runner, add the **pairing ratchet** (Shapes G, check 8): a tracked
`tests/untested.txt` (or `test-support/untested.txt`) lists the source files Phase 0 found
without a test. The check fails on a source file that is in neither the list nor paired
with a test, and on a listed file that has since gained one — the list shrinks, never
grows, and a new module cannot land untested. Generated, vendored and type-only files are
excluded by an explicit glob the user confirms, never by judgement. A hard 1:1 fails on day
one and gets muted, which is why it is a ratchet.
**Verify:** run it; it passes on day one — a red check gets muted. **Gate:** each check is a rule the user holds.

## Phase 6 — Gate

The gate is the list of free commands, run in order before every commit; CI only re-runs
it. GitHub remote and the user wants CI → `.github/workflows/verify.yml` (Shapes F).
Otherwise the repo's own runner holds the list (`npm run check`, or `scripts/gate.sh` +
`.ps1`); no `.github/` is a valid end state (1321 has none). One job per side; only steps
Phase 0 showed free; deny-list comment first; no `secrets:`; `timeout-minutes` +
`concurrency`.

**Dependencies are derived, then proven:** walk the gate scripts' imports with `ast`,
subtract stdlib, then `git archive HEAD | tar -x -C <tmp>`, create a fresh venv with only
the derived packages, and run the whole gate there. Global site-packages hide lazy imports
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
subsection; cite nothing by quotation; link siblings by filename only; put the Status block
under the heading.* Root `README.md` links the index, never copies it. The user's own
prose stays where the Phase 0 ruling put it, is never rewritten, translated or renumbered,
and is cited by filename alone. Existing code citations are upgraded to `docs/X.md N.N`;
ids go into existing test/drill labels (`expect("raises empty_input (D-014)")`); no new
comments in files whose style rule forbids them.
**Verify:** every index link resolves; every cited doc has numbered headings; every agent-written doc has a Status block. **Gate.**

## Phase 8 — Close

Summary in the Working-loop report order: files written, `D-` count, open `Q-` list, skips
and why. Delete `AGENT_READY.md` and its `.git/info/exclude` line. Say in one sentence which
mechanisms carry regardless of domain (register, constraints, parking, boundary checks,
gate) and which depend on the domain tolerating unreviewed output (worktree fan-out).

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

# Reviewing a diff

Defects first, style last. The defects that matter here: <the repo's own classes — e.g. a
plausible value where a null with a reason belonged; a fallback that fills a field without
saying so; a check reported as run that was skipped; a doc contradicting its owner in
docs/README.md; a cited id that does not resolve>. Name file and line; say whether each
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
checked by <the paid, user-authorised run>. The untested list (`tests/untested.txt`) only
shrinks; a new source file without a test fails the check.

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
and which are manual; (iii) `AGENTS.md` untracked — flag it before anything cites it.

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
real systems locally, first run; REQUIREMENTS, DECISIONS, OPEN_QUESTIONS (D); `<DOMAIN>.md`
— one per contract several parts of the code honour.

Under each agent-written doc's heading — "checked", not "updated": a date is when someone
looked, not proof nothing drifted; the user's prose carries none:

```markdown
<!--
Status: current | register | snapshot | transcript - <when it changes, e.g. "in the same commit as src/errors.py">
Last checked against the code: <date>
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
# Everything here is free and offline. This workflow holds no secrets, so a paid call
# cannot succeed even by accident. Never run here: <script> (<why: bills per page>).
# See AGENTS.md "Gates". The pip line mirrors <setup section>; no manifest by D-nnn
# (drift: Q-nnn); derived from imports, proven in a fresh venv from `git archive`.
name: Verify
on: [pull_request, push]
concurrency: { cancel-in-progress: true, group: "verify-${{ github.ref }}" }
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
`lint` / `typecheck` / `test` / `build` scripts that exist. When no linter exists at all,
propose only five promise-bug rules: `no-floating-promises`, `no-misused-promises`,
`await-thenable`, `only-throw-error`, `require-await` — a missing `await` is an error
typecheck cannot see.

## G. Boundary checks

Read source as text, never import it. Variants: FORBIDDEN prefix list, ALLOWED regex list
(preferred), exact-allow-set, labelled-regex vocabulary scan, counted exemptions (a leak may
shrink, never grow; an exemption used zero times is stale and fails too), and the **drift
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
import io, re, tokenize
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
    ids = set()
    for name in ("REQUIREMENTS", "DECISIONS", "OPEN_QUESTIONS"):
        p = ROOT / "docs" / f"{name}.md"
        if p.exists():
            ids |= set(re.findall(r"(?m)^## (R\d+|D-\d{3}|Q-\d{3}) ", p.read_text(encoding="utf-8")))
    dangling = []
    for p in files("<all roots>", "docs", suffixes={".py", ".ts", ".tsx", ".md"}):
        text = p.read_text(encoding="utf-8")
        for cited in set(re.findall(r"(?<![\w-])(R\d{1,3}|D-\d{3}|Q-\d{3})(?![\w-])", text)) - ids:
            dangling.append(f"{rel(p)}: {cited}")
        for doc, sec in set(re.findall(r"(?<![\w/])docs/([A-Z_]+\.md)(?: (\d+(?:\.\d+)*))?", text)):
            t = ROOT / "docs" / doc
            if not t.exists() or sec and not re.search(rf"(?m)^#+ {re.escape(sec)}\.?\s", t.read_text(encoding="utf-8")):
                dangling.append(f"{rel(p)}: docs/{doc} {sec}")
    ok &= expect("every cited id, doc and section resolves", not dangling, sorted(dangling))
    # 6. AGENTS.md loads into every context: <= 8 KiB, and tracked when CLAUDE.md imports it
    size = (ROOT / "AGENTS.md").stat().st_size
    ok &= expect(f"AGENTS.md is {size} bytes <= 8192", size <= 8192)
    # 7. (if docs/local/ is used) no tracked doc links docs/local/
    # 8. pairing ratchet (only with a runner): every source file has a test or is on the
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

- **A coordinator log that outlives a context reset.** A gitignored
  `.claude/orchestration/` file holding *Now*, a worker table (branch, role, state) and
  *decisions waiting*. The coordinator rereads it after every reset instead of rebuilding
  the picture from chat.
- **Workers by role, not by file.** One builds toward the goal, one verifies, one stages the
  next batch. Two workers never own the same file at once.
- **A landing rule.** A single worker's output is rebased and re-split into one-behaviour
  commits; a parallel batch lands as a `--no-ff` merge whose message is one hand-written
  sentence. Topic branches live minutes to hours, not days.
- **One review round per batch.** Findings are numbered (`F1`, `F2`…) in the log; each is
  fixed in its own commit that cites it in the subject, `(F3)`.

If the repo will be published, plan one cleanup pass before it goes public: handoffs, task
files, dated attributions and any private ids removed in one sweep.
