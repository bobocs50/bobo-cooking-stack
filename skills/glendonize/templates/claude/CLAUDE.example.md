# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` holds the rules of engagement that apply to every agent, not just
Claude Code; this file holds the manual and the rules only Claude Code can obey,
and a rule lives in one of the two only (D-127). Read it too.

@AGENTS.md

This file is the rules. The descriptions live in `notes/`, indexed and numbered
by `notes/README.md` — read it to find the right document.

`notes/` is authoritative — read the relevant file before proposing an approach.
`notes/GOALS.md` first for any architecture question (German): the product
goal, why this isn't RAG, why no agents. `notes/PRODUCT.md`: <domain standard> category →
criterion → section mapping and the field set. `notes/<COMPANY>_AI_GUARDRAIL.md`: the
transcribed <company AI-governance doc> obligations — read it before anything
touching compliance, tenancy or where data flows.

## Working agreement

### Agent swarms

Swarm by default: whenever a task holds more than one independent sub-task that
subagents can take, spawn real Agent subagents (one per sub-task) in the background
without being asked — I never have to say 'swarm' (D-119). Do not substitute
script-level parallel workers, and do not do the work yourself instead. Kept with
Claude: `main/*.py` edits and anything holding an open decision. If you think a swarm
is a bad fit, say why in one line and then spawn it anyway unless I change my mind (D-074).

Size a swarm to the task, not to a habit: first check the other sessions (ListAgents)
so no two agents do the same work, then spawn one agent per independent sub-task, as
many as the task has (the machine has 32 GB). Every agent follows AGENTS.md, runs the
free checks for its change when done, and reports outcome, files, checks, skipped and
untouched. Paid runs start with `--parallel 16` (`eval/pn_run.py`'s default) unless a rate
limit shows; I should not have to ask for parallelism (D-090).

Every swarm starts right away; no guess is asked first. When the findings come back, show
them with your verdict (D-108).

My code reading has two triggers, both yours to raise, about one question a day at most
(D-085, D-089, D-092):
1. A commit touches the always-list: the schema, grounding, in-dossier / set-aside, merge
   rules, flags, null handling, an error path that swallows a failure, a cache key, a
   catalog row, or a drill that is deleted or weakened. Right after the commit, first run a
   reviewer subagent that sees only the diff and reports gaps, then show me the hunk (at
   most ~40 lines, with one sentence on what it decides) and ask one question.
2. Before a paid run: the hunk the run will test (a prompt rule, a page-selection rule or
   constant), if not already asked under 1. My answer is the prediction the run's numbers
   then check.
Never for imports, renames, comments, formatting, the frontend, eval scripts. The question
is one of four kinds, rotated (D-109): the code question (what comes out for a given input;
find the defect or say none, one in three; which caller still assumes the old shape, with
the call sites shown; why this and not null; which drill line would still pass if the fix
were wrong); "name the mechanism" (I give the textbook term for what the function
implements); the failure question (what reaches the reviewer when a call fails or a file is
half-written); the trade-off question (why this design and not the other; what breaks the
other way). Each starts with its marker line ("Code question:", "Mechanism question:",
"Failure question:", "Trade-off question:") and ends with "Rating (sure|unsure|not said): …".
Never yes/no, never answerable from the commit message, never style. I say sure or unsure
and answer in 2–3 sentences; you correct in one line that names the line and the
consequence. Prompt diffs are still shown before the run (D-085).

### Agent review of code commits

Every commit that touches `main/ eval/ tests/ frontend/ .github/ .claude/hooks/` is reviewed by
agents before it lands, blocking only on a confirmed defect (D-123). Tiered by risk (D-125):
`main/` and `.claude/hooks/` get three finders and one verifier per defect on opus; `eval/ tests/
frontend/ .github/` alone get one finder and a verifier on sonnet; notes get none.
Stage in one call, commit in the next: never `git add ... && git commit`, never `-a`, never `--amend`
on code, because the hook reviews the staged diff. Fix a confirmed finding, or answer it with a
`review: <finding id> - not a defect because ...` line; never bypass, `PROJECT_REVIEW_SKIP=1` only on my
word. The `Agent-Review` trailer it adds is checked by `tests/drill_review_stamp.py`.
It does not replace my code question or my prompt-diff read (D-085, D-109). Re-check 2026-11-02.

### Approval before acting

- 'yes but…', questions, or discussion are NOT a go. Only act on explicit approval
  ('go', 'do it', 'yes').
- For decision docs and GitHub issue changes (new/close/delete): propose first,
  then wait. Issue comments are posted without asking, like code and note
  changes, which are committed and pushed without asking (D-058, D-074, D-099).
- Ask clarifying questions with AskUserQuestion (CLI choices), not as prose.

### Failures get a permanent fix

When a failure shows up (a red gate, a wrong claim, a rejected action, a broken run, a
value that slipped past a check), name the failure mode and its cause in one line the
moment it happens, and build or propose the fix that stops it coming back: a drill, a
hook, a gate step or a rule, never only the one instance (D-124).

### Definition of done for issues

An issue is NOT done just because it is closed on GitHub. Before saying an issue is
fixed, check its target metric (e.g. hit rate vs D-101's 85–95% target) against the latest
eval run and quote the numbers. If no fresh run exists, say so (D-074).

### Paid runs & budget

- The estimate, the go and the booking are in AGENTS.md "Gates"; state the estimate per corpus
  and per criterion (Flammability extraction is the most expensive), every time, even when I
  asked for the run (D-074).
- A hook enforces it: `.claude/hooks/guard_paid_run.py` blocks any shell command
  that starts a paid script unless it carries `PROJECT_PAID_OK=1`. Add the marker only
  after my go for that run, never to get past a block (D-074).
- Use generous timeouts for long runs. Never stop a run early because it looks slow;
  report progress instead.
- Commit after each meaningful step, not at the end (D-026).

### Explanations

Explain in plain language first (2–5 short bullets, no jargon), then give details
only if I ask. When explaining metrics, define each one in one sentence with the
actual numbers (D-074).

System design is learned while building, never as a lesson: use the standard
system-design terms whenever you explore, propose or explain, so I pick them up in
use; when I describe something with a wrong or vague term, correct it in passing
with the right word and one example; when we build architecture or I grill you,
give tips and better proposals with the System Design Primer
(https://github.com/donnemartin/system-design-primer) as the reference. The terms
are standard CS words only, each listed with its <project> place in my private learning
file (not in the repo); the mechanism question of D-109 draws on that list. No
vocabulary sessions, no term quizzes (D-098).

## Project status

Steps 1–5 of the roadmap in README.md "Status" are built, first verified on the 4 sample
PDFs and since measured on the three corpora <corpus-a>, <corpus-b> and <corpus-c> (D-110, D-111):
ingestion and <OCR service> parsing, the criteria catalog,
deterministic keyword classification, extraction and grounding. `main/pipeline.py`
wires them into one callable, `main/api.py` exposes it over HTTP, and `frontend/`
is the React/TS/Tailwind review UI.

All 15 criteria are live and all four category tabs are `built: true`.

The pipeline takes a **dossier**: 3–4 PDFs uploaded together, one record per
criterion, every field citing the document it came from as well as the page. No
single PDF answers a criterion on its own — see `notes/OVERVIEW.md 2`.

The part number is an input: the calling program sends it with the request and
every criterion uses it; the PDFs are not searched for it (D-081). In the UI the
reviewer types it and confirms; the old proposal call from pages 1–2 is removed
(D-104). Each criterion's result carries a `record` in
the gold-set shape — eight bare-value keys — instead of the old templated
`fields` block (D-031).

The comparison against <company extraction service> was removed
(D-107). The field set is in `notes/PRODUCT.md`; the live schema is `build_schema()` in `main/step4_extraction.py`.

`.github/workflows/verify.yml` runs the free gate on push — `python tests/run_drills.py`,
every `tests/drill_*.py`, the Ruff lint and format check `tests/drill_ruff.py` among them (it globs the directory, so a new drill is picked up without
editing the workflow), the step "Every main/ change carries a drill" (D-094), plus the
frontend's own `npm run lint`, `npm run build` and the Playwright `npm run test:ui`.
It adds no runner and no manifest, and holds no secrets, so nothing in it can spend
money (D-021).

## Data handling

`documents/`, `main/parsed_output.csv` and `main/parsed_output.txt` are
gitignored. The PDFs are proprietary <domain> test reports carrying an
explicit "do not reproduce or transfer in any medium" legend; the two output
files are their OCR'd text. **Never commit them and never paste page text into
chat or commit messages** — inspect with short context windows (±50 chars around
a match) and keep debug prints to counts and page numbers (R4).

**All processing of document content must stay in EU regions (R3).** The OCR service runs in
<eu-region>. The extraction LLM is <llm-deployment> in <eu-region> (D-114), after a gap on
another provider (D-071). Claude Code itself
processes in the US, so on its own initiative it keeps proprietary page content
out of the conversation: code, structure, page numbers and short match contexts
only — never whole pages, never rendered page images. The exception is the
user's explicit act: a screenshot the user hands over is read, and a PDF the user
says to check is read (D-059).

The extraction LLM is `<llm-deployment>` at reasoning effort medium (D-117), and the
layer 2 classifier `<llm-deployment>` at medium as well (D-121), both on <llm-resource>
(`<LLM_ENDPOINT>`, `<LLM_KEY>`), <eu-region>, which meets R3 (D-114); the deployment is
EU data-zone. Running the pipeline and
the paid eval scripts against it is the intended workflow and needs no further
confirmation. Why a region response header is not evidence of residency is in
`notes/PLATFORM_CONSTRAINTS.md`.

## Cost

**`main/step1_parsing.py` bills the OCR service per page and takes minutes — never re-run it
to test downstream code.** `main/parsed_output.csv` is the hand-off that exists
precisely so classification and extraction can be iterated for free (D-003).
`notes/LOCAL_SETUP.md 6` has the full paid/free table.

## Rejected — don't re-propose

LangGraph or an agent framework (D-001: the flow is one loop and one `if`, no
LLM-decided routing, no pause-and-resume); a local PDF parser first with OCR fallback
(D-002); ranking a "primary" page per criterion — extraction decides, add only if
it demonstrably cites bad pages; keyword tiers, AND-groups or regex section
patterns; a deterministic Python merge or document role tags for cross-document
conflicts (D-006 — the model resolves them); capping the pages sent per call
(send all, measure first).

Also settled: **machines add and flag; only a human removes** (R8). No layer has
a veto over another's hits.

## Outstanding

The blocking ones are tracked in `notes/OPEN_QUESTIONS.md`.

**Classification layer 2**, a cheap LLM pass over the OCR text of every page,
unioned with the keyword hits, is built and measured at the classification level
(D-056, D-067); the pipeline keeps no learned-keyword list (D-066) —
`notes/ARCHITECTURE.md 2.3a`. D-056's value target (more than 80% on the 13 in-scope
criteria) and D-101's (85–95% hit rate, at most 3–5% wrong or invented) are met on
<corpus-a> and <corpus-b> by the d106 run of 2026-10-12 and not yet on the held-out
<corpus-c> (d110, 2026-10-13); the numbers are in `notes/GOLD_SET.md 7` and issue #2.

## Domain context

<domain standard> is a public industry standard, not company-specific. The product
maps its criteria (e.g. "<criterion name>") to supporting test-report PDFs and
extracts a fixed set of fields per criterion, each with a page/quote citation, for
<domain> certification records. Every extracted value must be traceable and a human review step before
persisting is mandatory (R1, R2).

## How code gets written here

`main/*.py` is the spine — a bug is a silent wrong value in a certification
record, not a crash, so the user must be able to explain every line to a
colleague. Division of labour (D-011, D-085):
- Claude drafts all of it, mechanical code and judgment code (LLM prompts, the
  grounding check, the flagging logic) — only after an explicit go-ahead for that
  specific piece, never speculatively — and commits and pushes it (D-058).
- The user reads every prompt diff before it runs and decides; the user does not
  write spine code or commit. Line-by-line review of the rest of `main/` starts
  once the architecture is settled (D-085).
- Planning docs, one-off inspection scripts and comment clean-ups are
  periphery — draft freely.

Style in `main/*.py`: plain `for` loops with a named accumulator, no
comprehensions; comments only where the *why* isn't obvious (D-050).

Run scripts from `main/` — `step3_classification.py` imports `criteria_catalog` as a
bare module. On Windows prefix with `PYTHONIOENCODING=utf-8` (D-016). Node is at
`C:\Program Files\nodejs` and **not on PATH**.

### Commit every logical change and push it

The rule, the gate order and the `main/*.py` exception are in AGENTS.md
"Working loop" and "Gates" (D-026, D-058) — this file does not restate them.

### Delegating execution to the `implementer` agent

Delegate only once the approach is settled — an agent briefed from a
half-understood task writes confident, wrong code, and here that means a silent
wrong value in a certification record.

Write the brief to a file and name goal, exact paths, numbered steps, what is
out of scope, the verification command, and the constraints that bear on the
task. The agent starts with an empty context and has not read this file. Read
the diff before reporting — the agent's report is a claim, not evidence.

## Keeping this current

An architecture, setup or failure-handling change is written into the document
that describes it — `notes/ARCHITECTURE.md`, `notes/LOCAL_SETUP.md`,
`notes/FAILURES.md` — as part of the change, once verified, not as a follow-up
chore. This file holds the rules; if a rule changes, it changes here, and the
decision goes in `notes/DECISIONS.md` with its date.
