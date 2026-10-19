<div align="center">

# glendonize

*Make a repo safe for several AI coding agents at once, one gated phase at a time.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Claude Code skill](https://img.shields.io/badge/Claude%20Code-skill-orange.svg)](SKILL.md)

</div>

A Claude Code skill that installs a working agreement, a numbered register of requirements,
decisions and open questions that code cites, checks that read source as text, and a gate made
only of free commands. It writes nothing it cannot trace to a line in your repo, and it lists
the whole result as a Harness table in your README. Modelled on glendonC's many-minions and
[1321](https://github.com/glendonC/1321). [All skills](../../README.md).

---

## Files

| Topic | Description |
|---|---|
| [SKILL.md](SKILL.md) | The full rules, phases and the shape of every file it writes |
| [README.md](README.md) | This page |

## Phases

| Topic | Description |
|---|---|
| [0 Survey](SKILL.md#phase-0--survey-writes-only-agent_readymd) | Writes only `AGENT_READY.md`: stack, free vs paid steps, candidates, conflicts |
| [1 Unblock](SKILL.md#phase-1--unblock) | Ignores agent worktrees and reduces `CLAUDE.md` to an import of `AGENTS.md` |
| [2 Register](SKILL.md#phase-2--register) | Requirements and decisions from confirmed candidates only |
| [3 Working agreement](SKILL.md#phase-3--working-agreement) | `AGENTS.md` under 8 KiB: your text first, then the shared sections |
| [4 Parking and constraints](SKILL.md#phase-4--parking-and-constraints) | Open questions, and vendor facts marked checked or not checked |
| [5 Boundary checks](SKILL.md#phase-5--boundary-checks) | One check per boundary, plus citations, file size and the test ratchets |
| [6 Gate](SKILL.md#phase-6--gate) | The free commands as a CI workflow or a local script, plus the hooks |
| [7 Docs](SKILL.md#phase-7--docs) | The docs index, the numbered docs, and the Harness table in your README |
| [8 Close](SKILL.md#phase-8--close) | Rebuilds the Harness table, writes a summary, deletes `AGENT_READY.md` |

## What it stops

| Topic | Description |
|---|---|
| Invented reasons | A decision with no recorded reason says so instead of getting one made up |
| Surprise bills | Scripts that cost money are listed and kept out of the gate and CI |
| Broken citations | A check fails when code cites a rule that does not exist |
| Guessed values | A missing decision becomes an open question; that branch stops, the rest goes on |
| Untested code | A new module cannot land without a test, and tests cannot quietly lose checks |
| Unread commits | For Claude Code repos, agents read every code commit before it lands |

---

## Install

```sh
npx skills@latest add bobocs50/bobo-cooking-stack --skill glendonize
```

By hand, user-level on macOS / Linux:

```sh
mkdir -p ~/.claude/skills/glendonize && curl -fsSL https://raw.githubusercontent.com/bobocs50/bobo-cooking-stack/main/skills/glendonize/SKILL.md -o ~/.claude/skills/glendonize/SKILL.md
```

Then run `/glendonize` (or `/glendonize path/to/repo`) in a git repo. Run it again later and it
resumes at the first unfinished phase and rebuilds the Harness table; your rulings are never
asked twice. Related: [grilling](../grilling/README.md), [whiteboard](../whiteboard/README.md).
