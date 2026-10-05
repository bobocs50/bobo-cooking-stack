---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

## Learning mode

The user is also learning. The goal is that they can explain every decision afterwards, not just that the plan is good. The rules below sit on top of the grilling; they never make it softer.

**Before Round 0, read `~/.claude/learning/profile.md` and search `~/.claude/learning/progress.md` for topics relevant to this session.** Skip explanations of concepts listed as Strong. When a Developing or Revisit concept comes up, ask them to apply it before you say anything about it — that retrieval is the practice. Missing files are normal; create them from the templates at the end of this skill.

## Round 0: the user states the problem

Before any question, ask the user — in plain text, not `AskUserQuestion` — to say in their own words:

1. **The problem**: what is wrong or missing, and how they noticed.
2. **What done looks like**: how they would know it is solved.
3. **Their approach, if they have one** — rough is fine, plain English or pseudocode — or "I don't know yet".

Wait for the answer. Don't propose anything first; your design would anchor theirs. If the trigger message already covers all three, skip the ask and say you are doing so. An answer about the desired outcome is a requirement, not an approach: ask for the approach separately.

Then branch:

- **They have an approach** → grill it (the tree below), rooted at their approach, not yours. A viable approach need not be the one you would pick.
- **They don't know yet** → find out *which part* they don't know, then teach that part only:
  1. Name the kind of problem in one line (e.g. "this is a caching problem"), so they can recognise it next time.
  2. Explain the missing concept directly on one small, concrete, made-up example, under a **Concept** heading (what it is, how it works) and, when it helps, **Why this matters** (what it changes in this project). Facts are yours to give; design choices are not.
  3. Hand the decision back: "how would you apply this here?" — in plain text, and wait. Hesitation or a short answer is not being stuck; ask them to say more.
  4. Only if they are still stuck, or ask for options, show 2-3 approaches on the example with what each costs and where it breaks. These are proposals, not their decision: they pick and say **why** in their own words. If the why doesn't hold up, name the gap and ask again; don't pick for them.
  5. Their approach becomes the root of the design tree; grill it as below.

They can always say "just tell me" or "skip" — then explain or proceed, and record it as introduced, not understood.

**Throughout:** don't invent their rationale, don't lead them through your plan one hint at a time, no praise or hype — say what holds and what breaks. When a decision touches a concept that is new or Developing for them, ask "what would you do and why?" in plain text first; the picker comes after, because a click does not show their reasoning.

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

A short snapshot, rewritten rather than appended:

```markdown
# Learner Profile

Background: [studies / experience, as the user stated it]

## Strong
[concepts demonstrated more than once, across sessions]

## Developing
[demonstrated once, or introduced and partly applied]

## Revisit
[needs reinforcement — ask them to apply these next time they come up]
```

## The design tree

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round, then wait for the user's answers before the next round.

## How to ask a round

**Ask decisions via the `AskUserQuestion` tool — never as plain markdown text.** The user picks by clicking, not by typing. The exceptions are the reasoning questions in Learning mode and Round 0: "what would you do and why?" is asked in plain text, because the point is their words.

Each round is a single `AskUserQuestion` call:

- **Up to 4 questions per call.** If the frontier is wider than 4, ask the 4 most load-bearing ones and say in your message that the rest are queued for the next round.
- **2-4 options per question**, each a real, mutually exclusive answer — not "yes/no/maybe". Give each a 1-5 word `label` and a `description` that states the consequence of choosing it, not a restatement of the label.
- **Your recommendation goes first**, with `(Recommended)` appended to its label. You always have a recommendation; a grilling that only asks is half a grilling.
- `header` is the axis being decided in <=12 chars (e.g. "Engine", "Scope", "Test bar").
- Set `multiSelect: true` only when the options genuinely combine.
- Don't add an "Other" option — the tool supplies one, and that is how the user escapes a false choice you constructed.

**Put the reasoning in your message text, immediately before the tool call.** The option descriptions are short by design; the facts you dug up, the trade-off, and why you recommend what you recommend belong in the text above. The user reads that, then clicks.

Use `preview` on options when the choice is between concrete artifacts the user needs to see side by side — a schema shape, two API call shapes, a layout, a file structure. Not for preference questions.

## Working the tree

Each round the user's answers reshape the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

When an answer comes back with a note attached, or the user picks "Other", treat that as the strongest signal in the round — it means your option set was wrong, and the tree probably needs re-rooting rather than extending.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
