# grilling

[← all skills](../../README.md)

A Claude Code skill that interviews you about a plan, a decision or an idea, one round of
questions at a time, until every decision in it is settled. It finds the gaps a plan in
your head always has (an unhandled failure, a choice made by default) before code is written.

## How it works

1. **Round 0:** you state the problem, what done looks like, and your approach (or "don't know yet").
2. **Design tree rounds:** each round asks every decision whose prerequisites are settled (the frontier), up to 4 clickable questions with one recommendation; your answers unblock the next round.
3. Facts are Claude's job: it sends a subagent to look them up instead of asking you. Decisions are yours.
4. **Draw first:** at a structure decision you sketch it on the [whiteboard](../whiteboard/README.md), Claude grills each box, then draws its alternative beside yours.
5. **Learning mode, no approach yet:** Claude names the kind of problem, teaches only the missing concept on a small example, and hands the decision back to you.
6. **Learning mode, at the close:** you write one or two lines on what you learned; Claude updates `~/.claude/learning/` from evidence only (a click on its recommendation counts as Introduced, never Demonstrated).
7. It ends when the frontier is empty, and Claude does not act on the plan until you confirm.

## Example

```
You:    grill me: our nightly export job sometimes sends the same report twice.
Claude: [Round 0] Approach? -> you: "Don't know yet"
Claude: This is a retry-without-idempotency problem. [Concept ...] How would you apply it here?
You:    store a sent-marker per report and day, check it before sending.
Claude: [Round 1] Key: Report id + date (Recommended) / Report id only
                  Store: Existing database (Recommended) / A file
                  Order: Mark before / Mark after sending (Recommended)
You:    picks, plus a note: "can the mail provider dedupe for us?"
Claude: (subagent checks the mail client) -> [Round 2] structure: what would you draw?
```

## Install

```sh
npx skills@latest add bobocs50/bobo-cooking-stack --skill grilling
```

By hand, user-level on macOS / Linux:

```sh
mkdir -p ~/.claude/skills/grilling && curl -fsSL https://raw.githubusercontent.com/bobocs50/bobo-cooking-stack/main/skills/grilling/SKILL.md -o ~/.claude/skills/grilling/SKILL.md
```

Plugin install: see the [root README](../../README.md). Run with `/grilling` or
"grill me on this plan". For learning mode, set up
[learning-by-building](../../learning-by-building/README.md#install).

## Files

| File | What it does |
|---|---|
| [`SKILL.md`](SKILL.md) | The whole skill: the instructions Claude follows |
| [`agents/openai.yaml`](agents/openai.yaml) | Display name and short description for other agent tools |

The full rules are in [`SKILL.md`](SKILL.md). Related: [whiteboard](../whiteboard/README.md),
[learning-by-building](../../learning-by-building/README.md).
