### Learning while building

I am learning while you write the code. My learning record is in `~/.claude/learning/`
(`profile.md`, `progress.md`); read `profile.md` before explaining a concept, and skip what
it lists as Strong.

**One question, at most about one a day, at two moments, of four kinds** (the code question, name the mechanism, the failure question, the trade-off question):
1. A commit touches code that decides a value: null handling, a fallback, a merge rule, an
   error path that swallows a failure, a cache key, or a test that is deleted or weakened.
   Right after the commit, first run a reviewer subagent that sees only the diff and reports
   gaps; then show me the changed lines (at most ~40, with one sentence on what it decides) and
   ask one question.
2. Before a paid or long run: the changed lines the run will test, if not already asked under 1. My
   answer is the prediction the run's numbers then check.

Never for imports, renames, comments, formatting or test scripts. Rotate the question: what
comes out for a given input; find the defect or say none (one in three); which caller still
assumes the old shape (show the call sites); why this and not null; which test line would
still pass if the fix were wrong. Never yes/no, never answerable from the commit message,
never style. I say sure or unsure and answer in 2–3 sentences; you correct in one line that
names the line and the consequence. Record the result in `~/.claude/learning/progress.md`.
Start the question with a line `Code question: ...`, `Mechanism question: ...`,
`Failure question: ...` or `Trade-off question: ...` and, once I have answered and you have
corrected, write a line `Rating (sure|unsure|not said): right or off, the line, the consequence`; the weekly stats
count both lines. A mechanism question asks for the textbook term (what does this function
implement: a content-addressed cache, an atomic write, exponential backoff); a failure question
asks what reaches the user when a call fails or a file is half-written; a trade-off question
asks why this design and not the other, and what breaks the other way.

**Explanations.** Plain language first, 2–5 short bullets, one concrete example; details only
when I ask. Use the correct engineering term when you explain, and when I use a wrong or vague
term, correct it in passing with the right word and one example. The terms are the standard
CS words only, never your own coinages; the table under `## Terms` in `progress.md` lists them
with the place in my code where each one lives. The first time one comes up in a session,
write one line of its own: `term = plain meaning; example from my code`. When the question
touches one of those places, the term is in the question.
