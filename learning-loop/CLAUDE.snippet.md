### Learning while building

I am learning while you write the code. My learning record is in `~/.claude/learning/`
(`profile.md`, `progress.md`); read `profile.md` before explaining a concept, and skip what
it lists as Strong.

**One code question, at most about one a day, at two moments:**
1. A commit touches code that decides a value: null handling, a fallback, a merge rule, an
   error path that swallows a failure, a cache key, or a test that is deleted or weakened.
   Right after the commit, first run a reviewer subagent that sees only the diff and reports
   gaps; then show me the hunk (at most ~40 lines, with one sentence on what it decides) and
   ask one question.
2. Before a paid or long run: the hunk the run will test, if not already asked under 1. My
   answer is the prediction the run's numbers then check.

Never for imports, renames, comments, formatting or test scripts. Rotate the question: what
comes out for a given input; find the defect or say none (one in three); which caller still
assumes the old shape (show the call sites); why this and not null; which test line would
still pass if the fix were wrong. Never yes/no, never answerable from the commit message,
never style. I say sure or unsure and answer in 2–3 sentences; you correct in one line that
names the line and the consequence. Record the result in `~/.claude/learning/progress.md`.

**Struggle first.** Before a swarm that looks for a cause, ask for my one-line guess
("I think X because Y") unless I wrote `guess:` or `skip`. When the findings come back, show
them, let me say which hold, then give your verdict.

**Explanations.** Plain language first, 2–5 short bullets, one concrete example; details only
when I ask. Use the correct engineering term when you explain, and when I use a wrong or vague
term, correct it in passing with the right word and one example.
