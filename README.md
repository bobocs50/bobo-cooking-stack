<div align="center">

# bobo-cooking-stack

*Claude Code skills for building real software with AI agents, and still understanding what got built.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-orange.svg)](.claude-plugin/plugin.json)

</div>

Agents invent reasons for rules, build the wrong thing, and write code you never learn from.
These skills fix one problem each. They are small, plain Markdown, and meant to be edited.

---

## Getting Started

| Topic | Description |
|---|---|
| [Install](#install) | As a Claude Code plugin or as editable files for any agent; pick one way, not both |
| [Learning setup](learning-by-building/README.md#install) | Scripts, templates and a weekly job in `~/.claude/learning/` |

## Skills

| Topic | Description |
|---|---|
| [glendonize](skills/glendonize/README.md) | Makes a repo agent-ready in gated phases; the first pass writes nothing |
| [grilling](skills/grilling/README.md) | Interviews you a round at a time until every decision in a plan is settled |
| [whiteboard](skills/whiteboard/README.md) | Opens a Mermaid chart as a hand-drawn board; Claude reads what you draw |

## Learning

| Topic | Description |
|---|---|
| [learning-by-building](learning-by-building/README.md) | One question about a risky change when it lands, at most about once a day |
| [weekly-review](learning-by-building/weekly-review/README.md) | A weekly job that updates your learning profile only from checked evidence |

## Harness

| Topic | Description |
|---|---|
| [glendonize/SKILL.md](skills/glendonize/SKILL.md) | The glendonize instructions |
| [glendonize/templates/](skills/glendonize/templates/) | Working copies of the hooks, drills, CI gate and rule files the skill installs, with project details replaced by placeholders |
| [grilling/SKILL.md](skills/grilling/SKILL.md) | The grilling instructions, with the learning mode |
| [grilling/agents/openai.yaml](skills/grilling/agents/openai.yaml) | Display name and short description for other agent tools |
| [whiteboard/SKILL.md](skills/whiteboard/SKILL.md) | The whiteboard instructions |
| [whiteboard/serve.py](skills/whiteboard/serve.py) | Local server that saves the drawing and tells Claude |
| [whiteboard/board.html](skills/whiteboard/board.html) | The Excalidraw board page |
| [whiteboard/example.mmd](skills/whiteboard/example.mmd) | A sample chart to try the board on |
| [weekly-review/SKILL.md](learning-by-building/weekly-review/SKILL.md) | The weekly review instructions |
| [weekly_stats.py](learning-by-building/weekly_stats.py) | Counts the last 7 days of sessions into `weekly.md` |
| [weekly_page.py](learning-by-building/weekly_page.py) | Renders the week as one offline HTML page |
| [run_weekly.sh](learning-by-building/run_weekly.sh) / [.ps1](learning-by-building/run_weekly.ps1) | The weekly job for cron or Windows Task Scheduler |
| [settings.example.json](learning-by-building/settings.example.json) | A `SessionStart` hook that catches a missed weekly job |
| [CLAUDE.snippet.md](learning-by-building/CLAUDE.snippet.md) | The question rules to paste into a project's `CLAUDE.md` |
| [templates/](learning-by-building/templates/) | Empty `profile.md`, `progress.md` and `agentic-coding.md` |

## Why

| Problem | Quote | Fix |
|---|---|---|
| The agent made up a rule | "Don't ever take down a fence until you know the reason it was put up." (Chesterton's fence) | [glendonize](skills/glendonize/README.md): written rules, a decision register the code cites, a gate of free commands |
| The agent built the wrong thing | "No one knows exactly what they want." (Thomas & Hunt, *The Pragmatic Programmer*) | [grilling](skills/grilling/README.md) settles every decision; [whiteboard](skills/whiteboard/README.md) for structure |
| I shipped code I don't understand | "What I cannot create, I do not understand." (Richard Feynman) | [learning-by-building](learning-by-building/README.md) asks one question per risky change |

---

## Install

<details>
<summary><strong>Claude Code plugin</strong></summary>

```
/plugin marketplace add bobocs50/bobo-cooking-stack
/plugin install bobo-cooking-stack@bobo-cooking-stack
```

</details>

<details>
<summary><strong>Any agent, as editable files</strong></summary>

```bash
npx skills@latest add bobocs50/bobo-cooking-stack                   # all
npx skills@latest add bobocs50/bobo-cooking-stack --skill grilling  # one
```

`npx skills@latest update` pulls changes.

</details>

## Contribute

Open an issue or a pull request. Keep a skill small and its README short.

## About

Credits: [glendonC/1321](https://github.com/glendonC/1321) for glendonize, Matt Pocock's
[skills](https://github.com/mattpocock/skills) (MIT) for grilling, [nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise)
for the learning mode, [nexu-io/harness-engineering-guide](https://github.com/nexu-io/harness-engineering-guide) for this README's shape.

## License

MIT. See [LICENSE](LICENSE).
