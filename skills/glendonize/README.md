# glendonize

[← all skills](../../README.md)

A Claude Code skill that gives a repo the structure several AI coding agents need to work in it
safely: a working agreement, a numbered register of requirements, decisions and open questions
that code cites, boundary checks that read source as text, and a gate made only of free commands.
It installs them one gated phase at a time and writes nothing it cannot trace to a line in your repo.
It is modelled on glendonC's many-minions and his public repo [1321](https://github.com/glendonC/1321).

| Failure | Mechanism |
|---|---|
| An agent invents a reason for a rule nobody explained | Decision register; no recorded reason means `Rationale: not recorded` |
| An agent runs a script that bills per call | Free-only gate: a confirmed deny-list, and CI that holds no secrets |
| Code cites a rule that was renamed or never written | Citation resolvability check |
| A missing decision is filled with a guess | Parking: stop that branch, open a `Q-` entry, continue the rest |
| A new module lands without a test | Pairing ratchet over a tracked `untested.txt` that only shrinks |

## How it works

1. **Never invent.** Every proposed entry names its `file:lines`, and you confirm it before it is written.
2. **Phase 0 only surveys.** It writes just `AGENT_READY.md`, kept out of git through `.git/info/exclude`.
3. **Conflicts go to you.** Both sides are quoted, you rule, and the ruling becomes a dated `D-` entry.
4. **Every phase ends at a gate** (a Verify step, then your approval) and lands as its own commit.
5. **It pushes only when you ask.** It never uses `git add -A` or `--no-verify`.
6. **It resumes.** Run it again and it names the first unfinished phase; rulings are never re-asked.

| # | Phase | Adds |
|---|---|---|
| 0 | Survey | `AGENT_READY.md`: stack, free vs paid steps, candidates, conflicts, a phase menu |
| 1 | Unblock | `.claude/worktrees/` in `.gitignore`; `CLAUDE.md` reduced to `@AGENTS.md` |
| 2 | Register | `docs/REQUIREMENTS.md`, `docs/DECISIONS.md` from confirmed candidates only |
| 3 | Working agreement | `AGENTS.md` (at most 8 KiB): your text verbatim, then Citation, Review, Parking, Gates, Working loop |
| 4 | Parking and constraints | `docs/OPEN_QUESTIONS.md`, `docs/PLATFORM_CONSTRAINTS.md` (each fact VERIFIED or ASSERTED) |
| 5 | Boundary checks | One text-reading check per confirmed boundary, plus citations, `AGENTS.md` size, ratchet |
| 6 | Gate | The free commands, as `.github/workflows/verify.yml` or a local script |
| 7 | Docs | `docs/README.md` (the owner index), then the numbered docs it lists |
| 8 | Close | A summary; deletes `AGENT_READY.md` |

Phase 0 tells you which phases add something to your repo; the rest can be skipped.

## Example

```
> /glendonize
Phase 0 wrote only AGENT_READY.md:
- Stack: Python with pytest. 9 of 14 source files have a test; 5 become the ratchet baseline.
- Deny-list: scripts/summarize.py (README.md:41 "costs a few cents per invoice").
- Rule: "amounts are stored in cents" (README.md:58), no reason given.
- Parked: TODO(user) "which rate source is authoritative?" becomes a Q- candidate.
- Conflict: CLAUDE.md holds rules of its own; the plan moves them into AGENTS.md. Your ruling?
```

Phase 2 then writes `D-002 — Amounts are stored in cents` with `Rationale: not recorded`.

## Install

```sh
npx skills@latest add bobocs50/bobo-cooking-stack --skill glendonize
```

By hand, user-level on macOS / Linux:

```sh
mkdir -p ~/.claude/skills/glendonize && curl -fsSL https://raw.githubusercontent.com/bobocs50/bobo-cooking-stack/main/skills/glendonize/SKILL.md -o ~/.claude/skills/glendonize/SKILL.md
```

Then run `/glendonize` (or `/glendonize path/to/repo`) in a git repo. The plugin install is in
the [root README](../../README.md).

Full rules, phases and templates: [`SKILL.md`](SKILL.md). Related: [grilling](../grilling/SKILL.md),
[whiteboard](../whiteboard/SKILL.md).
