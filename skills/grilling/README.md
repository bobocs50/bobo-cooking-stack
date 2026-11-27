<div align="center">

<img src="../../assets/grilling.svg" width="80" alt="">

# grilling

**Nothing gets built by guess.**

Claude interviews you about a plan, one round at a time, until every decision is settled and you can explain each one yourself.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE) [![Claude Code skill](https://img.shields.io/badge/Claude%20Code-skill-orange.svg)](SKILL.md)

</div>

<br>

<p align="center"><img src="../../assets/grilling-tree.svg" width="760" alt=""></p>

<p align="center"><sub>Every decision branches into the ones that hang off it. A round asks all the decisions that are ready; it ends when nothing is open and you confirm.</sub></p>

## How it works

| Topic | Description |
|---|---|
| Round 0 | You state the problem, what done looks like, and your approach or "don't know yet" |
| Design tree rounds | Each round asks every decision that is ready, up to 4 clickable questions, one recommended |
| Facts vs decisions | Claude looks facts up with a subagent; decisions stay yours |
| Draw first | At a structure decision you sketch on the [whiteboard](../whiteboard/README.md), then Claude draws its alternative beside yours |
| Learning mode | With no approach yet, Claude names the kind of problem, teaches only the missing concept, and hands the decision back |
| Close | You write what you learned; Claude does not act on the plan until you confirm |

## Example

```
You:    grill me: our nightly export job sometimes sends the same report twice.
Claude: [Round 0] Approach? -> you: "Don't know yet"
Claude: This is a retry-without-idempotency problem. [Concept ...] How would you apply it here?
You:    store a sent-marker per report and day, check it before sending.
Claude: [Round 1] Key: Report id + date (Recommended) / Report id only
                  Order: Mark before / Mark after sending (Recommended)
```

## Files

| Topic | Description |
|---|---|
| [SKILL.md](SKILL.md) | The whole skill: the instructions Claude follows |
| [agents/openai.yaml](agents/openai.yaml) | Display name and short description for other agent tools |

## Install

```sh
npx skills@latest add bobocs50/bobo-cooking-stack --skill grilling
```

By hand, user-level on macOS / Linux:

```sh
mkdir -p ~/.claude/skills/grilling && curl -fsSL https://raw.githubusercontent.com/bobocs50/bobo-cooking-stack/main/skills/grilling/SKILL.md -o ~/.claude/skills/grilling/SKILL.md
```

Plugin install: see the [root README](../../README.md#install). For learning mode, copy
[templates/](templates/) to `~/.claude/learning/` (`cp -n templates/*.md ~/.claude/learning/`) and fill in `profile.md`.

## Built from

- The grilling itself from Matt Pocock's [skills](https://github.com/mattpocock/skills)
- Learning mode from [nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise)

The full rules are in [SKILL.md](SKILL.md). [All skills](../../README.md)
