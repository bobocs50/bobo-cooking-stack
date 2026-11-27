---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Outcome first, Claude researches and proposes, then every decision is grilled with a recommendation, and the session ends with what good looks like. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it. The session runs in five phases: **the outcome, their rough idea, your research and proposal, the grilling, what good looks like.** Facts are your job; decisions are theirs.

## Learning mode

The user is also learning. The goal is that they can explain every decision afterwards, not just that the plan is good. The rules below sit on top of the grilling; they never make it softer.

**Before Phase 1, read `~/.claude/learning/profile.md` and search `~/.claude/learning/progress.md` for topics relevant to this session.** Skip explanations of concepts listed as Strong. When a Developing or Revisit concept comes up, ask them to apply it before you say anything about it — that retrieval is the practice.

## Phase 1: the outcome

Before anything else, one `AskUserQuestion` call (the user clicks; typing goes under Other) asks for:

1. **The problem**: what is wrong or missing, and how they noticed.
2. **What done looks like**: how they would know it is solved.
3. **An example of good, if they have one**: a link, a repo, a file, a screenshot. Offer "None" and "Find some"; theirs arrives under Other.

The options for 1 and 2 are readings of what the user already wrote, never your design. Skip a question the trigger message already answers; "nothing to grill" is never the answer. Write one `Done when:` line from the answers, observable and testable, and show it.

## Phase 2: their rough idea

Ask in plain text: "Your rough idea, in a line or two, or 'none'?" and wait. This comes before your proposal, so their idea is said before yours can anchor it. Start the research (Phase 3) in the background while they answer.

If they say "none" and the missing piece is a concept rather than a fact, teach that part only before you propose:

1. Name the kind of problem in one line (e.g. "this is a caching problem"), so they can recognise it next time.
2. Explain the missing concept in text, never a drawing, on one small, concrete example, made-up or from the project, with 1–2 sources, under a **Concept** heading (what it is, how it works) and, when it helps, **Why this matters** (what it changes in this project).
3. Hand it back: "how would you apply this here?" — in plain text, and wait. Hesitation or a short answer is not being stuck; ask them to say more.

They can always say "just tell me" or "skip" — then proceed, and list it under "Shown so far" in progress.md, not as a record.

## Phase 3: research and propose

Send sub-agents for the facts: the existing code, the docs, outside sources, their example of good. Each gets a narrow brief; run them in parallel. Then show, in at most one screen:

- **The approach** in 3–6 lines, and where it differs from their rough idea and why. A viable idea of theirs need not lose to yours; say so when it holds.
- **Facts found**: a short table, fact | source. Only facts with a source go here. You decide no design question on their behalf; every decision goes to Phase 4.
- **Open decisions**: the list Phase 4 will grill.

Ask "anything here you'd contest?" as one click; a contested fact is checked again, not argued.

## Phase 4: the grilling

Grill every open decision with the design tree below, each question with your recommended answer. Taste questions (naming, look, tone) are decisions too and get a recommendation like any other.

**Throughout:** don't invent their rationale, no praise or hype — say what holds and what breaks. **Their answer first, where it is practice (2026-10-08):** at a structure decision (next section) and wherever a new, Developing or Revisit concept decides the answer, ask "what would you do and why?" in plain text, wait, then say where their answer agrees or differs from yours; the picker comes after, because a click does not show their reasoning. Every other decision goes straight to the picker; their reasoning fits under Other or a note. When they ask about existing code, answer *why*; *what it does* is theirs to say first.

### Structure decisions: the user sketches first

Only when a decision about structure comes up — a new layer, step, data shape, boundary or component — is it settled on drawings, not on a list of options:

1. **The user draws the first sketch** as a Mermaid flowchart, opened with `/whiteboard` (hand-drawn, dark, full screen), one concept per diagram, every box named with a system-design term (the "Terms" table in `~/.claude/learning/progress.md` if there is one, otherwise the standard terms: pipeline, boundary, cache, fallback, …); arrows bare, labelled only where the label says something the boxes don't ("retry and reconcile"). A box without a term is the first question. An uncertain edge is drawn with a question mark, not asserted. You never draw before their sketch exists; your Phase 3 approach stays in words until then.
2. **Grill the drawing** in plain text, one box or edge at a time: why does this box exist; what is its one responsibility; what happens when it fails, times out or half-succeeds, and where is that surfaced; who owns each piece of state that crosses a boundary; what still works if this box dies; what did this choice reject, and what would make you reconsider.
3. **Then draw your alternative beside it**, same look and vocabulary, and say where it differs and why.
4. **They pick** (`AskUserQuestion`, `preview` on both sketches) and say why. A term they used and defended goes into progress.md "Words you used"; a click alone is exposure and goes under "Shown so far" at most.

On their ask, open the sketch on `/whiteboard`; the Mermaid in the conversation stays the record.

## Phase 5: what good looks like

When the frontier is empty, write a note of 3–6 lines: the examples of good, theirs first, then the ones research found, each with its link and the 2–3 qualities that make it good for this plan; check it against the `Done when:` line. The `Done when:` line, the facts, the settled decisions and this note are the shared understanding. Confirm it with one click ("Shared understanding: yes / something's off"). Do not act on the plan before that.

## Closing the session

After they confirmed the shared understanding:

1. **Teach-back.** Ask them to explain the two most load-bearing decisions in their own words, in plain text. Their explanation is a record; a decision they accepted without a why is not.
2. Ask them for one or two lines in their own words: what they learned, and what is still unclear. Don't write it for them.
3. Update the learning files (below) from evidence only. Show them the update in a few lines.
4. If the session taught them something about *working with Claude or agents* (how they prompted, briefed, delegated, verified, or a mistake in that), add a dated line to `~/.claude/learning/agentic-coding.md` under "Lessons learned" or "Setup changes", and rewrite "How I work now" if their workflow changed. Their words where possible.

### What counts as evidence

- **A record**: they did something themselves — answered a code question, predicted a run, explained a decision, caught a wrong claim — rated in one line (right or off, which line, the consequence). Clicking a recommendation is never a record.
- **Shown so far**: you explained it, or they picked your recommendation without their own why. Exposure, not learning.
- **Needs reinforcement**: they got it wrong, or said it is still unclear.

Never record quotations of whole exchanges, and never anything from a proprietary document — concepts and decisions only.

### `~/.claude/learning/progress.md`

Append to the existing sections, never a new topic heading: a dated paragraph under "Records" (project, what they did, the rating, what is not yet there), a line under "Needs reinforcement", a term under "Words you used" only if they used and defended it, and anything you explained under "Shown so far". A record is never deleted; a wrong one gets "superseded <date>".

### `~/.claude/learning/profile.md`

The user's own document. Touch only the Strong / Developing / Revisit lists at its end (Strong: a rated record more than once across sessions; Developing: once, or shown and partly applied; Revisit: needs reinforcement); never rewrite the rest.

## The design tree

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round, then wait for the user's answers before the next round.

## How to ask a round

**Ask decisions via the `AskUserQuestion` tool — never as plain markdown text.** The user picks by clicking, not by typing. The only plain-text questions are their rough idea (Phase 2), the teach-back, and the ones Learning mode names, a structure sketch and a new concept, because there the point is their words.

Each round is a single `AskUserQuestion` call:

- **Up to 4 questions per call.** If the frontier is wider than 4, ask the 4 most load-bearing ones and say in your message that the rest are queued for the next round.
- **2-4 options per question**, each a real, mutually exclusive answer — not "yes/no/maybe". Give each a 1-5 word `label` and a `description` that states the consequence of choosing it, not a restatement of the label.
- **Your recommendation goes first**, with `(Recommended)` appended to its label. You always have a recommendation on a design decision; a grilling that only asks is half a grilling. A question that tests the user (a prediction, a which-line, a what-would-happen) carries no `(Recommended)` and equal-length options.
- `header` is the axis being decided in <=12 chars (e.g. "Engine", "Scope", "Test bar").
- Set `multiSelect: true` only when the options genuinely combine.
- Don't add an "Other" option — the tool supplies one, and that is how the user escapes a false choice you constructed.

**Put the reasoning in your message text, immediately before the tool call.** The option descriptions are short by design; the facts you dug up, the trade-off, and why you recommend what you recommend belong in the text above. The user reads that, then clicks.

Use `preview` on options when the choice is between concrete artifacts the user needs to see side by side — a schema shape, two API call shapes, two structure sketches, a file structure. Not for preference questions.

## Working the tree

Each round the user's answers reshape the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

When an answer comes back with a note attached, or the user picks "Other", treat that as the strongest signal in the round — it means your option set was wrong, and the tree probably needs re-rooting rather than extending.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The grilling is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Then go to Phase 5.
