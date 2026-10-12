# bobo-cooking-stack

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Claude Code skills by bobocs50 for building software with AI coding agents without losing
track of what gets built. There are two goals:

- **Keep the repo safe for agents.** Agents follow written rules, cite recorded decisions,
  and never run a step that costs money.
- **Keep the human learning.** You still understand and can explain the code and the design,
  even though agents write most of it.

It is for developers who use Claude Code every day, often with several agents at once, and
who want both of those things.

## The parts

| Part | What it does | Read more |
|---|---|---|
| `glendonize` | Makes a repo agent-ready in gated phases. It adds an `AGENTS.md` working agreement, a numbered register of requirements, decisions and open questions that code cites, boundary checks that read source as text, and a gate that runs only free commands. It writes nothing on the first pass and nothing it cannot trace to a line in your repo. | [skills/glendonize/README.md](skills/glendonize/README.md) |
| `grilling` | Interviews you about a plan, one round of questions at a time, mapped as a design tree, until every decision is settled. Its learning mode has you state the problem and your own approach first, and it teaches a missing concept on a small example instead of handing you its design. | [skills/grilling/README.md](skills/grilling/README.md) |
| `whiteboard` | Opens a Mermaid flowchart as a full-screen, hand-drawn Excalidraw board in your browser. You draw on it and press "Send to Claude"; the agent reads the PNG and the scene and updates the Mermaid to match. | [skills/whiteboard/README.md](skills/whiteboard/README.md) |
| `weekly-review` | Once a week, turns the counts in `~/.claude/learning/weekly.md` into 3 to 5 plain bullets on how your learning went. It updates your learning profile only from evidence a check produced, never from the counts alone. | [skills/weekly-review/README.md](skills/weekly-review/README.md) |
| `learning-loop` | Not a skill. It is the setup that the learning parts run on: a weekly stats script, a guess-first hook, a `CLAUDE.md` snippet that makes Claude ask you one question about a risky hunk, and templates for your profile and progress files under `~/.claude/learning/`. | [learning-loop/README.md](learning-loop/README.md) |

## How the parts fit together

```
your repo ──> glendonize ──> AGENTS.md, register, boundary checks, free gate
                                   (agents can now work in it safely)

a plan ─────> grilling ───> design tree, decisions settled
                 │
                 └─ at a structure decision ──> whiteboard
                      (you sketch first, the skill grills the drawing,
                       then draws its alternative beside yours)

while agents build ──> learning-loop ──> weekly.md (counts)
                                              │
                                              └──> weekly-review ──> profile.md updated
```

- **glendonize** structures the repo once, so agents have written rules to follow and cannot
  spend money by accident.
- **grilling** stress-tests a plan before it is built. When the plan reaches a structure
  decision (a new layer, step, data shape or boundary), you draw the first sketch with
  **whiteboard**, and the grilling works on your drawing.
- **The learning loop and weekly-review** keep track of what you learn while agents build.
  Grilling sessions write what you showed you understand to
  `~/.claude/learning/progress.md`. The `CLAUDE.md` snippet makes Claude ask you about code
  you are about to trust. Once a week, `weekly-review` reads all of it and updates your
  profile.

Each part also works alone. You can install `whiteboard` without `grilling`, or `glendonize`
without any of the learning parts. Grilling's learning mode reads
`~/.claude/learning/profile.md` and `progress.md`, and the learning loop's templates create
those files.

## Install

### Everything at once

With the `skills` CLI:

```sh
npx skills@latest add bobocs50/bobo-cooking-stack
```

You pick which coding agents to install it on. It writes each skill as an ordinary file that
you own and can edit. Run `npx skills update` to pull later changes.

Or as a Claude Code plugin, from inside a session:

```
/plugin marketplace add bobocs50/bobo-cooking-stack
/plugin install bobo-cooking-stack@bobo-cooking-stack
```

When installed as a plugin, the commands are namespaced, for example
`/bobo-cooking-stack:glendonize`.

Both ways install the four skills only. The learning loop's scripts, hooks and templates are
copied by hand from a clone of this repo. The steps are in the
[learning loop's install section](learning-loop/README.md#install).

### One skill at a time

```sh
npx skills@latest add bobocs50/bobo-cooking-stack --skill glendonize
npx skills@latest add bobocs50/bobo-cooking-stack --skill grilling
npx skills@latest add bobocs50/bobo-cooking-stack --skill whiteboard
npx skills@latest add bobocs50/bobo-cooking-stack --skill weekly-review
```

Each skill's README lists what else it needs. For example, `whiteboard` needs Python and a
browser that can reach a CDN, and `weekly-review` needs the learning loop's files.

## Run

| Part | Trigger |
|---|---|
| `glendonize` | `/glendonize` or `/glendonize path/to/repo`, "make this repo agent-ready", or a request for a decision register, constraints doc, boundary checks or a gate |
| `grilling` | `/grilling` or "grill me" |
| `whiteboard` | `/whiteboard`, "draw it", "sketch this", or a grilling that reaches a structure decision |
| `weekly-review` | Runs itself when the `SessionStart` hook says a review is due, or from a scheduled task; by hand with `/weekly-review` or "weekly review" |

## Repo layout

```
bobo-cooking-stack/
├── .claude-plugin/
│   ├── plugin.json          # plugin manifest: lists the four skills
│   └── marketplace.json     # makes the repo a one-plugin marketplace
├── skills/
│   ├── glendonize/
│   │   ├── SKILL.md
│   │   └── README.md
│   ├── grilling/
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   └── agents/openai.yaml
│   ├── whiteboard/
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   ├── serve.py         # local server, Python standard library only
│   │   ├── board.html       # the Excalidraw board
│   │   └── example.mmd      # a sample Mermaid flowchart
│   └── weekly-review/
│       ├── SKILL.md
│       └── README.md
├── learning-loop/
│   ├── README.md
│   ├── weekly_stats.py      # counts the week, appends to weekly.md
│   ├── guess_first.py       # UserPromptSubmit hook: guess before a swarm
│   ├── run_weekly.ps1       # Windows scheduled-task runner
│   ├── settings.example.json  # the hooks to merge into ~/.claude/settings.json
│   ├── CLAUDE.snippet.md    # paste into a project's CLAUDE.md
│   └── templates/           # profile.md, progress.md, agentic-coding.md
├── LICENSE
└── README.md
```

## Credits

- `glendonize` is named after the repo structure of glendonC
  ([github.com/glendonC](https://github.com/glendonC)), in particular his public repo
  [1321](https://github.com/glendonC/1321), and is inspired by it.
- `grilling` builds on the grilling skill in Matt Pocock's
  [skills](https://github.com/mattpocock/skills) (MIT).
- The learning mode in `grilling` and the teach-first, explain-it-back part of the learning
  loop are modelled on [nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise).

## License

MIT. See [LICENSE](LICENSE).
