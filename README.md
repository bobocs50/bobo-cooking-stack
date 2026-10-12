# bobo-cooking-stack

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

My Claude Code skills for building real software with AI agents, and still understanding
what got built.

I build a production data pipeline almost entirely through Claude Code agents, often several
at once. It is the kind of project where a silent wrong value is worse than a crash. These
skills came out of the things that went wrong along the way: agents that guessed a rule,
plans that were misunderstood, and a builder (me) who shipped code without learning from it.

They are small, plain Markdown, and meant to be edited. Take what fits, change the rest.

## Installation (30-second setup)

### 1. Get the skills

<details>
<summary><strong>Claude Code plugin</strong> (updates through <code>/plugin</code>)</summary>

Inside a Claude Code session:

```
/plugin marketplace add bobocs50/bobo-cooking-stack
/plugin install bobo-cooking-stack@bobo-cooking-stack
```

Commands are namespaced, for example `/bobo-cooking-stack:glendonize`.

</details>

<details>
<summary><strong>Any agent, as editable files</strong> (manual updates)</summary>

```bash
npx skills@latest add bobocs50/bobo-cooking-stack
```

Pick the agents to install on, and the skills you want. Each skill becomes an ordinary file
you own. `npx skills@latest update` pulls changes. One skill only:
`npx skills@latest add bobocs50/bobo-cooking-stack --skill grilling`.

</details>

<details>
<summary><strong>By hand</strong> (copy the files yourself)</summary>

Copy a skill's folder from [`skills/`](skills/) into `~/.claude/skills/`. The READMEs of
glendonize, grilling and whiteboard have the exact commands for macOS / Linux and Windows.

</details>

Pick one way per agent. Installing both the plugin and the files gives you every skill twice.

### 2. Optional: set up learning-by-building

If you want to keep learning while agents write the code, clone this repo and follow
[learning-by-building's install](learning-by-building/README.md#install): it copies a stats
script and your profile templates to `~/.claude/learning/`, installs the `weekly-review`
skill, and schedules a weekly job (cron, or Task Scheduler on Windows).

### 3. That's it

Type `/glendonize` in a repo you want agents to work in, or "grill me" about your next plan.

## Why these skills exist

### #1: The agent made up a rule

> "Don't ever take down a fence until you know the reason it was put up."
>
> Chesterton's fence, as usually paraphrased from G. K. Chesterton

**The Problem.** An agent reads "never retry uploads" in your README and helpfully adds the
reason: "to avoid duplicate charges". Nobody ever said that. Months later the invented reason
is load-bearing. Agents also run the script that bills per call, cite rules that were
renamed, and fill a missing decision with a plausible guess.

**The Fix** is a repo that holds its own rules: a working agreement every agent reads, a
numbered register of requirements and decisions that code cites (with `Rationale: not
recorded` when nobody said why), checks that fail when a cited rule disappears, and a gate
made only of free commands.

- [`/glendonize`](skills/glendonize/README.md) installs all of that, one phase at a time,
  writing nothing it cannot trace to a line already in your repo.

### #2: The agent built the wrong thing

> "No one knows exactly what they want."
>
> David Thomas & Andrew Hunt, *The Pragmatic Programmer*

**The Problem.** You think the plan is clear. The agent builds it. Then you see the result and
realise the two of you meant different things, usually at a structure decision: where a
boundary sits, which step owns a value.

**The Fix** is to be interviewed before anything is built, one round of questions at a time,
until every decision in the design tree is settled. And for structure decisions, to draw
first, because a sketch shows the gap that a sentence hides.

- [`grilling`](skills/grilling/README.md) runs that interview. In its learning mode you state
  your own approach first, and it teaches the missing concept instead of handing you its
  design.
- [`whiteboard`](skills/whiteboard/README.md) opens a Mermaid flowchart as a hand-drawn board
  in your browser. You draw, press "Send to Claude", and the agent reads your drawing.

### #3: I shipped code I don't understand

> "What I cannot create, I do not understand."
>
> Richard Feynman

**The Problem.** When the agent writes the code, you skip the part where you would have
learned. You never trace the value, never find the bug yourself, never defend the design.
You ship faster and understand less, and the gap shows the first time something breaks.

**The Fix** is to put the learning back at the few moments that matter, without slowing the
project down: one question about a risky hunk right after it is committed, concepts that
come with an example when the work needs them, and a weekly review that changes your profile
only from evidence.

- [`learning-by-building`](learning-by-building/README.md) is the setup: a `CLAUDE.md`
  snippet for the code questions, profile templates, and a weekly cron job.
- [`weekly-review`](learning-by-building/weekly-review/README.md) is the skill the job runs.

## Reference

| Skill | How it starts | What it does |
|---|---|---|
| **[glendonize](skills/glendonize/README.md)** | `/glendonize`, "make this repo agent-ready" | Gives a repo the structure parallel agents need: `AGENTS.md`, a cited R/D/Q register, boundary checks that read source as text, a free-only gate. Gated phases; the first pass writes nothing. |
| **[grilling](skills/grilling/README.md)** | "grill me", `/grilling` | Interviews you about a plan as a design tree, a round at a time, until every decision is settled. Learning mode teaches what you are missing. |
| **[whiteboard](skills/whiteboard/README.md)** | `/whiteboard`, "draw it", "sketch this", or a grilling at a structure decision | A full-screen, hand-drawn Excalidraw board from a Mermaid file, served locally; the agent reads the PNG and scene you send. |
| **[weekly-review](learning-by-building/weekly-review/README.md)** | the weekly cron job, or `/weekly-review` | Turns the week's counts into 3–5 bullets and updates your learning profile, only from evidence a check produced. |

Not a skill: **[learning-by-building](learning-by-building/README.md)**, the scripts,
templates and `CLAUDE.md` snippet the learning parts run on.

## Credits

- `glendonize` is named after and modelled on the repo structure of
  [glendonC](https://github.com/glendonC), in particular his public repo
  [1321](https://github.com/glendonC/1321).
- `grilling` builds on the grilling skill in Matt Pocock's
  [skills](https://github.com/mattpocock/skills) (MIT), whose README this one is shaped after.
- The learning mode in `grilling` and the teach-first, explain-it-back part of
  learning-by-building are modelled on [nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise).

## License

MIT. See [LICENSE](LICENSE).
