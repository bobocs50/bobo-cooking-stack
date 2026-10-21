<div align="center">

# learning-by-building

*Learn to be a better engineer while AI agents write most of your code.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../LICENSE)

[All skills](../README.md)

</div>

When an agent writes the code, you skip the part where you would have learned. This small
Claude Code setup puts the learning back without slowing the project down. Everything stays in
`~/.claude/learning/`; only counts and your own prompts are used, never tool output.

---

## How it works

| Topic | Description |
|---|---|
| Concepts in the work | A concept comes when the work needs it, with an example and a source, and a check waiting |
| One question per risky change | After a commit that decides a value, or before a paid run, Claude shows the changed lines and asks one question, about once a day at most |
| Four kinds | Code (what comes out), mechanism (the textbook term), failure (what reaches the user), trade-off (why this design) |
| Sure or unsure | You say how sure you are first; the gap between sure and right is tracked |
| Terms | Standard CS words from the `## Terms` table in `progress.md` |

## Example

```python
def pick_report(cited, found):
    if cited:
        return cited[0]
    if found:
        return found[0]          # fallback
    return None
```

> **Claude:** Input: `cited = []`, `found = ["QTR-12"]`. What comes out, and does the record say it was a fallback?
>
> **You:** Unsure. `"QTR-12"`, and nothing marks it as a fallback.
>
> **Claude:** Right. Line 5 fills the field silently. Logged as *unsure, right*.

## Files

| Topic | Description |
|---|---|
| [CLAUDE.snippet.md](CLAUDE.snippet.md) | The question rules for a project's `CLAUDE.md` |
| [templates/](templates/) | Empty `profile.md`, `progress.md` and `agentic-coding.md` |

---

## Install

```sh
# On Windows: run this in Git Bash
git clone https://github.com/bobocs50/bobo-cooking-stack.git
cd bobo-cooking-stack/learning-by-building
mkdir -p ~/.claude/learning
cp -n templates/*.md ~/.claude/learning/
```

Then fill in `~/.claude/learning/profile.md`, and paste [CLAUDE.snippet.md](CLAUDE.snippet.md) into a project's `CLAUDE.md`.

## License

MIT. See [LICENSE](../LICENSE).
