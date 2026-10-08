---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

## Learning mode

The user is also learning. The goal is that they can explain every decision afterwards, not just that the plan is good. The rules below sit on top of the grilling; they never make it softer.

**Before Round 0, read `~/.claude/learning/profile.md` and search `~/.claude/learning/progress.md` for topics relevant to this session.** Skip explanations of concepts listed as Strong. When a Developing or Revisit concept comes up, ask them to apply it before you say anything about it — that retrieval is the practice.

## Round 0: the user states the problem

Before any design question, one `AskUserQuestion` call (the user clicks; typing goes under Other) asks for:

1. **The problem**: what is wrong or missing, and how they noticed.
2. **What done looks like**: how they would know it is solved.
3. **Their approach, if they have one** — rough is fine, plain English or pseudocode — or "I don't know yet".

The options for 1 and 2 are readings of what the user already wrote, never your design, which would anchor theirs; for 3 offer only "Don't know yet" and "Just propose", so an approach arrives in their own words under Other. If the trigger message already covers all three, skip Round 0 and open the first frontier round; "nothing to grill" is never the answer. An answer about the desired outcome is a requirement, not an approach: ask for the approach separately.

Then branch:

- **They have an approach** → grill it (the tree below), rooted at their approach, not yours. A viable approach need not be the one you would pick.
- **They don't know yet** → find out *which part* they don't know, then teach that part only:
  1. Name the kind of problem in one line (e.g. "this is a caching problem"), so they can recognise it next time.
  2. Explain the missing concept in text, never a drawing, on one small, concrete example, made-up or from the project, with 1–2 sources, under a **Concept** heading (what it is, how it works) and, when it helps, **Why this matters** (what it changes in this project). Facts are yours to give; design choices are not.
  3. Hand the decision back: "how would you apply this here?" — in plain text, and wait. Hesitation or a short answer is not being stuck; ask them to say more.
  4. Only if they are still stuck, or ask for options, show 2-3 approaches on the example with what each costs and where it breaks. These are proposals, not their decision: they pick and say **why** in their own words. If the why doesn't hold up, name the gap and ask again; don't pick for them.
  5. Their approach becomes the root of the design tree; grill it as below.

They can always say "just tell me" or "skip" — then explain or proceed, and record it as Introduced.

**Throughout:** don't invent their rationale, don't lead them through your plan one hint at a time, no praise or hype — say what holds and what breaks. **Their answer first, where it is practice (2026-10-08):** at a structure decision (next section) and wherever a new, Developing or Revisit concept decides the answer, ask "what would you do and why?" in plain text, wait, then say where their answer agrees or differs from yours; the picker comes after, because a click does not show their reasoning. Every other decision goes straight to the picker; their reasoning fits under Other or a note. Asking at every click was a ritual, not practice. When they ask about existing code, answer *why*; *what it does* is theirs to say first.

## Structure decisions: the user sketches first

A decision about structure — a new layer, step, data shape, boundary or component — is settled on drawings, not on a list of options:

1. **The user draws the first sketch** as a Mermaid flowchart in the hand-drawn look (front matter `config: {look: handDrawn, theme: dark}`), one concept per diagram, every box named with a system-design term (`~/.claude/learning/progress.md`, "System design vocabulary": pipeline, boundary, cache, fallback, …) and every arrow labelled with what crosses it, never just "uses". A box without a term, or an unlabelled arrow, is the first question. An uncertain edge is drawn with a question mark, not asserted. You never draw before their sketch exists.
2. **Grill the drawing** in plain text, one box or edge at a time: why does this box exist; what is its one responsibility; what happens when it fails, times out or half-succeeds, and where is that surfaced; who owns each piece of state that crosses a boundary; what still works if this box dies; what did this choice reject, and what would make you reconsider.
3. **Then draw your alternative beside it**, same look and vocabulary, and say where it differs and why.
4. **They pick** (`AskUserQuestion`, `preview` on both sketches) and say why. A term they used and defended is Demonstrated for progress.md; a click alone is Introduced.

On their ask, open the sketch in lavish (kunchenguid/lavish-axi) as an editable whiteboard; the Mermaid in the conversation stays the record.

## Closing the session

When the frontier is empty and they have confirmed the shared understanding:

1. Ask them for one or two lines in their own words: what they learned, and what is still unclear. Don't write it for them.
2. Update the learning files (below) from evidence only. Show them the update in a few lines.
3. If the session taught them something about *working with Claude or agents* (how they prompted, briefed, delegated, verified, or a mistake in that), add a dated line to `~/.claude/learning/agentic-coding.md` under "Lessons learned" or "Setup changes", and rewrite "How I work now" if their workflow changed. Their words where possible.

### What counts as evidence

- **Demonstrated**: they reasoned it themselves — proposed it, or explained why, and it held up.
- **Introduced**: you explained it, or they picked your recommendation without their own why. Clicking a recommendation is never demonstrated understanding.
- **Needs reinforcement**: they got it wrong, or said it is still unclear.

Never record quotations of whole exchanges, and never anything from a proprietary document — concepts and decisions only.

### `~/.claude/learning/progress.md`

One `## <Topic>` per concept (e.g. `## Caching`, `## Idempotent retries`), each readable on its own, with three bullet lists: Introduced / Demonstrated / Needs reinforcement, each bullet dated and naming the project. Update an existing topic instead of adding a duplicate.

### `~/.claude/learning/profile.md`

The user's own document. Touch only the Strong / Developing / Revisit lists at its end (Strong: demonstrated more than once across sessions; Developing: once, or introduced and partly applied; Revisit: needs reinforcement); never rewrite the rest.

## The design tree

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round, then wait for the user's answers before the next round.

## How to ask a round

**Ask decisions via the `AskUserQuestion` tool — never as plain markdown text.** The user picks by clicking, not by typing. The only plain-text questions are the ones Learning mode names, a structure sketch and a new concept, because there the point is their words.

Each round is a single `AskUserQuestion` call:

- **Up to 4 questions per call.** If the frontier is wider than 4, ask the 4 most load-bearing ones and say in your message that the rest are queued for the next round.
- **2-4 options per question**, each a real, mutually exclusive answer — not "yes/no/maybe". Give each a 1-5 word `label` and a `description` that states the consequence of choosing it, not a restatement of the label.
- **Your recommendation goes first**, with `(Recommended)` appended to its label. You always have a recommendation; a grilling that only asks is half a grilling.
- `header` is the axis being decided in <=12 chars (e.g. "Engine", "Scope", "Test bar").
- Set `multiSelect: true` only when the options genuinely combine.
- Don't add an "Other" option — the tool supplies one, and that is how the user escapes a false choice you constructed.

**Put the reasoning in your message text, immediately before the tool call.** The option descriptions are short by design; the facts you dug up, the trade-off, and why you recommend what you recommend belong in the text above. The user reads that, then clicks.

Use `preview` on options when the choice is between concrete artifacts the user needs to see side by side — a schema shape, two API call shapes, two structure sketches, a file structure. Not for preference questions.

## Working the tree

Each round the user's answers reshape the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

When an answer comes back with a note attached, or the user picks "Other", treat that as the strongest signal in the round — it means your option set was wrong, and the tree probably needs re-rooting rather than extending.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
