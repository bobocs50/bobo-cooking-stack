<div align="center">

# weekly-review

*Once a week, turns your raw learning counts into six short bullets and updates your profile.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)

[All skills](../../README.md)

</div>

Counts alone mislead: "9 correction prompts" could mean you got sloppier or more precise, and
a profile that moves on counts becomes a score you optimise. So the profile changes only when
something was checked: a rated code question, a prediction scored against a run, a test you took.

---

## How it works

| Topic | Description |
|---|---|
| Find the week | Reads the newest `weekly.md` entry marked `Interpretation: pending`, or makes one |
| Read the record | Reads `profile.md`, `progress.md`, earlier weeks, and your newest `/insights` report if any |
| Six bullets | How you got better, what went wrong, what you learned, learn next, how you worked with Claude, context |
| Update the profile | Changes `profile.md` only from checked evidence, dated; its own earlier verdicts do not count |
| Lessons | Logs a lesson about working with Claude in `agentic-coding.md` when the week shows one |
| No questions | It asks you nothing and proposes no new files, hooks or rules |

## Example

```markdown
- **How you got better:** You answered four questions, none last week.
  Three times you found the deciding line yourself.
  One needed a hint; one was right for the wrong reason.
- **What went wrong:** …
- **How you worked with Claude:** 18 corrections, 21 last week. …
```

## Files

| Topic | Description |
|---|---|
| [SKILL.md](SKILL.md) | The instructions Claude follows, including the headless Monday run |
| [weekly_stats.py](../weekly_stats.py) | Writes the counts this skill reads |

---

## Install

It is installed with the rest of the [learning-by-building setup](../README.md#install), which
also adds the scripts and templates it needs. A scheduled job runs it weekly; type
`/weekly-review` to run it by hand.

## License

MIT. See [LICENSE](../../LICENSE).
