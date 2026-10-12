"""Guess-first reminder, run by a UserPromptSubmit hook in ~/.claude/settings.json.

Struggle first (learning-loop/README.md): before a swarm the user writes a one-line
guess, and when the findings come back the user judges them before Claude's
verdict. When a prompt asks for a swarm or agents and carries no "guess:" or
"skip", this adds a reminder to Claude's context. It never blocks the prompt.
"""

import json
import re
import sys

# Fires on a request for a swarm or for agents to do something, not on the word alone
# ("why read the code when an agent wrote it" is a question, not a request).
SWARM = re.compile(r"\b(sw[ae]+r?m|swearm|sawrem|parallel agents)\b|\b(use|spawn|run|start|launch|with)\s+(a\s+)?(\w+\s+)?(sub)?agents?\b", re.I)
HAS_GUESS = re.compile(r"\b(guess|predict)\s*:|\bskip\b", re.I)

CONTEXT = (
    "Guess-first habit (the user's learning loop, ~/.claude/learning/profile.md): "
    "this prompt asks for agents and has no "
    "'guess:'. Before spawning, ask the user in plain text for a one-line guess: what they "
    "think the cause or answer is and why (a rough first thought, never a number), and "
    "wait. Then spawn the swarm as asked. Exception: when the request is "
    "about the user's own learning, habits or workflow rather than code, results or a design, "
    "skip the guess and spawn directly; the thinking happens in the discussion itself. When the findings come back, show "
    "them briefly without your verdict and ask the user which hold and which don't; give "
    "your verdict only after their answer. If the user says 'skip', go ahead directly."
)


def main():
    try:
        prompt = json.load(sys.stdin).get("prompt") or ""
    except Exception:
        return
    if SWARM.search(prompt) and not HAS_GUESS.search(prompt):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit", "additionalContext": CONTEXT}}))


if __name__ == "__main__":
    main()
