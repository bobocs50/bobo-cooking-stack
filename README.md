# bobo-cooking-stack

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

My Claude Code skills for building real software with AI agents, and still understanding
what got built. Small, plain Markdown, meant to be edited.

## Install

<details>
<summary><strong>Claude Code plugin</strong></summary>

```
/plugin marketplace add bobocs50/bobo-cooking-stack
/plugin install bobo-cooking-stack@bobo-cooking-stack
```

Commands are namespaced, e.g. `/bobo-cooking-stack:glendonize`.

</details>

<details>
<summary><strong>Any agent, as editable files</strong></summary>

```bash
npx skills@latest add bobocs50/bobo-cooking-stack                   # all
npx skills@latest add bobocs50/bobo-cooking-stack --skill grilling  # one
```

`npx skills@latest update` pulls changes.

</details>

Pick one way per agent, or you get every skill twice. Want to keep learning while agents
code? Also set up [learning-by-building](learning-by-building/README.md#install).

## Why these skills exist

### #1: The agent made up a rule

> "Don't ever take down a fence until you know the reason it was put up." — Chesterton's fence

**Problem:** agents invent reasons for rules nobody explained, run scripts that cost money,
and fill missing decisions with plausible guesses.

**Fix:** [`/glendonize`](skills/glendonize/README.md) gives the repo written rules agents
read, a register of decisions the code cites, checks that fail when a cited rule disappears,
and a gate made only of free commands.

### #2: The agent built the wrong thing

> "No one knows exactly what they want." — Thomas & Hunt, *The Pragmatic Programmer*

**Problem:** the plan felt clear, the result shows you meant different things.

**Fix:** [`grilling`](skills/grilling/README.md) interviews you a round at a time until every
decision is settled. At structure decisions you sketch first on
[`whiteboard`](skills/whiteboard/README.md), and the agent reads your drawing.

### #3: I shipped code I don't understand

> "What I cannot create, I do not understand." — Richard Feynman

**Problem:** when the agent writes the code, you skip the part where you would have learned.

**Fix:** [`learning-by-building`](learning-by-building/README.md) asks you one question about
a risky hunk when it lands, and a weekly cron job runs
[`weekly-review`](learning-by-building/weekly-review/README.md), which updates your learning
profile only from evidence.

## Reference

| Skill | Starts with | Does |
|---|---|---|
| [glendonize](skills/glendonize/README.md) | `/glendonize` | Makes a repo agent-ready in gated phases; the first pass writes nothing |
| [grilling](skills/grilling/README.md) | "grill me" | Design-tree interview with a learning mode |
| [whiteboard](skills/whiteboard/README.md) | `/whiteboard`, "draw it" | Hand-drawn board from a Mermaid file; the agent reads what you draw |
| [weekly-review](learning-by-building/weekly-review/README.md) | the weekly job | Weekly learning review from evidence |

## Credits

[glendonC](https://github.com/glendonC)'s [1321](https://github.com/glendonC/1321) for
glendonize · Matt Pocock's [skills](https://github.com/mattpocock/skills) (MIT) for grilling
and this README's shape · [nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise) for the
learning mode.

## License

MIT. See [LICENSE](LICENSE).
