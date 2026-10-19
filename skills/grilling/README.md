<div align="center">

# grilling

*Interviews you about a plan, one round at a time, until every decision is settled.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)

[All skills](../../README.md)

</div>

A plan in your head always has gaps: an unhandled failure, a choice made by default. This
Claude Code skill finds them before code is written. Run it with `/grilling` or "grill me on
this plan".

---

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

---

## Install

```sh
npx skills@latest add bobocs50/bobo-cooking-stack --skill grilling
```

By hand, user-level on macOS / Linux:

```sh
mkdir -p ~/.claude/skills/grilling && curl -fsSL https://raw.githubusercontent.com/bobocs50/bobo-cooking-stack/main/skills/grilling/SKILL.md -o ~/.claude/skills/grilling/SKILL.md
```

Plugin install: see the [root README](../../README.md#install). For learning mode, set up
[learning-by-building](../../learning-by-building/README.md#install).

## License

MIT. See [LICENSE](../../LICENSE).
