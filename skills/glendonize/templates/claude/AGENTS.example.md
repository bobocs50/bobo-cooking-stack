# This is NOT a normal Python repo

There is no build system and no Python package manifest; the linter and formatter is Ruff (`ruff.toml`, run by `tests/drill_ruff.py`, D-105), and the frontend has its own `npm run lint` and `npm run build`. Do not invent a `make` target. The test suite is the drill family: every `tests/drill_*.py` is a plain, free, offline script run by `python tests/run_drills.py`; every `main/` module with deterministic logic has a drill that imports it (D-047). Not pytest — a drill prints what it checked and why.

Running the wrong script spends real money (see "Gates"). `main/parsed_output.csv` exists so downstream code can be iterated for free — never re-parse to test classification or extraction. Read `notes/` (authoritative) before proposing an approach.

# Evidence-based collaboration

- Do not guess when a missing decision would materially change an extracted value, a prompt sentence, or a grounding rule. State what is known, identify the missing decision, and stop that branch until it is resolved.
- Do not agree or oppose reflexively. Base recommendations on the user's current instruction, the constraints in `notes/`, the current implementation, and observable evidence — a drill run, a `grep -c` against the parsed corpus, a scored report.
- When a new instruction conflicts with an earlier constraint, name the conflict and treat the user's latest explicit instruction as the override.
- Never substitute invented filenames, placeholder page numbers, improvised quotes, or fabricated field values. A null with a reason is correct; a plausible value is a defect — a silent wrong value in an certification record.
- Before a consequential judgment call the brief does not settle, present the exact decision needed; continue only with work that does not depend on it.

# Citation

Code cites the register and the notes; nothing cites code. Write `(R3)`, `(D-014)`, `(Q-002)`, `(notes/PRODUCT.md)` at the end of the clause they govern — in comments, docstrings and drill labels. The register is `notes/REQUIREMENTS.md` and `notes/DECISIONS.md`; `tests/drill_boundaries.py` fails on a cited id that does not resolve.

Cite a document by path and section number — `(notes/GROUNDING.md 3.1)` — never by line range. The German prose — GOALS, PRODUCT — is cited by filename alone (D-025). Decision first when the decision is the subject `(D-014, R7)`, requirement first when it is `(R3, D-007)`.

`main/*.py` is exempt: nobody but the user adds a citation there (D-022); proposals are handed over as a list, never applied.

A comment says why, never what. A comment is a pointer, not evidence: read the code it sits on. A claim about behaviour belongs in a drill, not a comment (D-050).

# Reviewing a diff

Defects first, style last: a plausible value where a null with a reason belonged; a fallback that fills a field without saying so; a grounding result read as correctness (notes/OVERVIEW.md 6); a check reported as run that was skipped; a note that contradicts its owner in `notes/README.md`; a cited id that does not resolve; a comment that restates the code or asserts untested behaviour (D-050). Name file and line, defect or question. If nothing survives, say what remains untested rather than "looks good".

# Parking

When a missing decision or an unverifiable fact would change the result: stop that branch, add a `Q-` entry to `notes/OPEN_QUESTIONS.md` with what is known and the exact act that would settle it, cite it where the branch stopped, and continue everything else. External facts go in `notes/PLATFORM_CONSTRAINTS.md` as ASSERTED until a source is read and linked. Before blaming a prompt for a missing value, `grep -c` the corpus in `main/parsed_output.csv` — it costs nothing.

# Gates

Before any commit, in order: `python tests/run_drills.py` (every drill, `.env.example` credentials blanked, exits non-zero if any failed), then `npm run lint`, `npm run build` and `npm run test:ui` in `frontend/` (Playwright on an invented fixture — plumbing, never whether a value is right). All of it is free and needs no credentials.

A red test written before its fix lives in `tests/tdd/`, outside the gate; the commit that greens it renames it into `tests/drill_*.py`, or moves it to `eval/` if it needs gitignored data (D-049, D-100, `tests/tdd/README.md`).

Never in the gate, never on your own initiative — only on the user's instruction, after the estimate and the user's go (D-074):

- Paid: `main/step1_parsing.py` (<OCR service> per page), `main/pipeline.py`, `main/api.py` (one LLM call per criterion), `eval/loop_run.py`, `eval/pn_run.py` (<OCR service> and LLM).
- Free but not runnable in CI (gitignored inputs): `eval/score.py`, `eval/gold.py`, `eval/gold_init.py`, `main/step3_classification.py`.

Every paid run is booked in `notes/BUDGET.md`, where the balances live:
- Before: run the script's own estimate (`eval/pn_run.py estimate`, same options as `run`), tell the user the estimate, the spend so far and what is left after it, add the line, then wait for the user's own go — never estimate and run in one turn. A range you eyeballed is not the estimate; estimates ran about 2x low with many pages (#2).
- After: book the actual from the script's `spent in total` and the new balance in the same commit as the run's findings.

Every `eval/` file states `Cost: free - ...` or `Cost: PAID - ...` in its docstring; `tests/drill_boundaries.py` fails without it.

Minimum check while working (the full gate still runs before the commit):

| Change | Minimum check |
|---|---|
| A note, comment, docstring, drill label | `python tests/drill_boundaries.py` |
| Failure handling in `main/`, or a drill | that drill, then `python tests/run_drills.py` |
| Any Python file | `python -m ruff format <path>`, then `python tests/drill_ruff.py` (D-105) |
| `frontend/` | `npm run lint`, `npm run build`, `npm run test:ui` |
| `.github/workflows/verify.yml` | `python tests/run_drills.py`, then push and watch the run |
| A prompt, the grounding check, the flagging logic | the user reads the diff before it runs (D-085); free drills; a scored run only on the user's say-so |

An implementer's "verified" means the row for its change was run, and the report names it.

# Working loop

- `main/*.py` is never delegated to a subagent and is written only on the user's go for that piece (D-011, D-085); a brief that has an agent edit `main/` is a defect in the brief.
- Fan out across git worktrees only for work with no open decision in it; two chunks touching one file run in sequence.
- Read `.claude/orchestration/COORDINATION.md` (gitignored, D-048) before spawning anything, and write what is in flight there before the workers start.
- A subagent's report, and its numbers, are claims: read the diff, run the drills, recompute one number before a decision rests on it.
- Every report states, in order: outcome, files changed, exact checks run, what was skipped, what was not touched.

Commit after every logical change and push right after it; the user never runs git by hand (D-026, D-058). The change and its checks in one commit, the gate green first, only that change's files staged (never `git add -A`), subject one sentence in this repo's style. No "WIP", no `--no-verify`, no unrelated batching; work is not finished while uncommitted.

Every commit touching `main/*.py` carries the drill line that fails if it is reverted, or says `no drill:` and why in the subject; a drill never loses an `expect(` call unless the subject says `drop drill:` and why (`PROJECT_DRILL_DROP_OK=1` for the local run first). `tests/drill_boundaries.py` and CI enforce both (D-094).
