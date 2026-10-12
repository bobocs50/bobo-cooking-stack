# grilling

[← all skills](../../README.md)

A Claude Code skill that interviews you about a plan, a decision or an idea, one round of
questions at a time, until every decision in it is settled and you and Claude agree on what
the plan is. It maps the plan as a **design tree**: each decision branches into the
decisions that depend on it, and Claude only asks what can be answered now.

It exists because a plan in your head always has gaps you have not noticed: a failure
case nobody handled, a choice made by default, a step that depends on a decision that was
never taken. Grilling finds them before code is written. On top of that it has a
**learning mode**: you state the problem and your own approach first, Claude teaches a
missing concept instead of handing you its design, and at the end it records what you
showed you understood. The goal is that you can explain every decision afterwards, not
only that the plan is good.

The skill is one file: [`SKILL.md`](SKILL.md).

## How it works

In the order it runs:

| Step | What happens |
|---|---|
| 1. Read your learning record | Claude reads `~/.claude/learning/profile.md` and searches `~/.claude/learning/progress.md` for topics relevant to this session |
| 2. Round 0: you state the problem | One question prompt asks for the problem, what done looks like, and your approach |
| 3. Branch | You have an approach: Claude grills it. You don't: Claude teaches the missing part, then you build the approach |
| 4. Rounds | Each round asks every decision that can be answered now (the frontier), up to 4 at a time |
| 5. Structure decisions | You draw first on a whiteboard, Claude grills the drawing, then draws its alternative beside yours |
| 6. End | The frontier is empty and you confirm the shared understanding |
| 7. Close | You write one or two lines on what you learned; Claude updates the learning files from evidence only |

### Round 0: you state the problem

Before any design question, Claude asks one question prompt (you click; free text goes
under "Other") with three questions:

1. **The problem**: what is wrong or missing, and how you noticed.
2. **What done looks like**: how you would know it is solved.
3. **Your approach, if you have one**: rough is fine, plain English or pseudocode, or "I
   don't know yet".

The options for 1 and 2 are readings of what you already wrote, never Claude's design,
because that would anchor yours. For 3 the only options are "Don't know yet" and "Just
propose", so an approach arrives in your own words under "Other". An answer about the
outcome you want is a requirement, not an approach, and Claude asks for the approach
separately. If your first message already covers all three, Round 0 is skipped and the
first real round starts. "Nothing to grill" is never the answer.

### If you have an approach

Claude grills your approach, with the design tree rooted at it, not at the approach Claude
would pick. A viable approach does not have to be Claude's favourite.

### If you don't know yet

Claude finds out which part you don't know and teaches only that part:

1. It names the kind of problem in one line ("this is a caching problem"), so you
   recognise it next time.
2. It explains the missing concept in text, on one small concrete example (made up or from
   your project), with one or two sources, under a **Concept** heading, and when it helps a
   **Why this matters** heading. Facts are Claude's to give; design choices are not.
3. It hands the decision back: "how would you apply this here?", in plain text, and waits.
   A short or hesitant answer is not being stuck; it asks you to say more.
4. Only if you are still stuck, or you ask for options, it shows 2 to 3 approaches on the
   example, with what each costs and where it breaks. You pick and say **why** in your own
   words. If the why does not hold up, it names the gap and asks again. It does not pick
   for you.
5. Your approach becomes the root of the design tree.

You can always say "just tell me" or "skip". Claude then explains or moves on, and records
the concept as Introduced, not Demonstrated.

### The design tree and its rounds

The **frontier** is every decision whose prerequisites are already settled: the questions
Claude can ask now without guessing at answers it has not heard yet. Each round asks the
whole frontier, then waits. Your answers settle decisions, which unblocks the ones that
depended on them, and Claude recomputes the frontier for the next round. A question whose
answer depends on another question still open in the same round waits for a later round.

When you attach a note to an answer or pick "Other", Claude treats it as the strongest
signal in the round: its option set was wrong, and the tree probably needs a new root
rather than another branch.

Finding facts is Claude's job, never yours. When a question needs a fact from your
filesystem or tools, Claude sends a subagent to look it up instead of asking you. It does
not wait for it: only the questions that depend on that fact wait; the rest of the round is
asked now. Decisions are yours, and Claude puts each one to you and waits.

### How questions are asked

Decisions go through Claude Code's `AskUserQuestion` prompt, so you answer by clicking.
Each round is one call:

| Rule | Detail |
|---|---|
| Questions per round | Up to 4. If the frontier is wider, the 4 that carry the most weight go first and Claude says the rest are queued |
| Options per question | 2 to 4, each a real answer that excludes the others, never "yes / no / maybe". A label of 1 to 5 words, and a description that says what choosing it leads to |
| Recommendation | Always one, listed first with `(Recommended)` on its label. A grilling that only asks is half a grilling |
| Header | The axis being decided, at most 12 characters ("Engine", "Scope", "Test bar") |
| Multi-select | Only when the options really combine |
| "Other" | Never added by Claude; the prompt supplies it, and it is how you escape a false choice |
| Reasoning | In the message text just above the prompt: the facts found, the trade-off, and why the recommendation |
| Preview | Only when you need to compare concrete things side by side: two schema shapes, two API call shapes, two sketches, a file structure. Not for questions of taste |

Plain-text questions are the exception, used only where your own words are the point: a
structure sketch and a new concept (see below).

### Your answer first

At a structure decision, and wherever a new concept, or one your profile lists as
Developing or Revisit, decides the answer, Claude first asks in plain text "what would you
do and why?" and waits. Then it says where your answer agrees with its own and where it
differs, and only then shows the clickable options, because a click does not show your
reasoning. Every other decision goes straight to the clickable prompt; your reasoning fits
under "Other" or a note. Asking for your answer at every click would be ritual, not
practice.

Two more rules hold throughout: Claude does not invent your rationale, and it does not lead
you through its own plan one hint at a time. No praise: it says what holds and what breaks.
When you ask about existing code, it answers *why*; *what the code does* is for you to say
first.

### Structure decisions: you draw first

A decision about structure (a new layer, a step, a data shape, a boundary, a component) is
settled on drawings, not on a list of options:

1. **You draw the first sketch** as a Mermaid flowchart, opened with
   [`/whiteboard`](../whiteboard/README.md): hand-drawn, dark, full screen. One concept per
   diagram. Every box is named with a system-design term (pipeline, boundary, cache,
   fallback, ...) from the "System design vocabulary" in your `progress.md`. Arrows are
   bare, with a label only where it says something the boxes don't ("retry and
   reconcile"). A box without a term is the first question. An edge you are unsure of is
   drawn with a question mark. Claude never draws before your sketch exists.
2. **Claude grills the drawing** in plain text, one box or edge at a time: why does this
   box exist; what is its one responsibility; what happens when it fails, times out or
   half-succeeds, and where is that shown; who owns each piece of state that crosses a
   boundary; what still works if this box dies; what did this choice reject, and what
   would make you reconsider.
3. **Claude draws its alternative beside yours**, same look and vocabulary, and says where
   it differs and why.
4. **You pick** in a clickable prompt with both sketches as previews, and say why. A term
   you used and defended counts as Demonstrated; a click alone counts as Introduced.

If you ask, Claude opens the sketch in lavish
([kunchenguid/lavish-axi](https://github.com/kunchenguid/lavish-axi)) as an editable
whiteboard. Either way the Mermaid in the conversation stays the record.

### When it ends

The session is done when the frontier is empty: every branch of the tree visited, nothing
left silently assumed. Claude does not act on the plan until you confirm that you have
reached a shared understanding.

## Learning mode: what it reads and records

Learning mode sits on top of the grilling and never makes it softer. It uses the files of
the [learning-by-building](../../learning-by-building/README.md) in `~/.claude/learning/`.

**Before Round 0** it reads:

| File | Used for |
|---|---|
| `profile.md` | Concepts listed as Strong are not explained again. When a Developing or Revisit concept comes up, you are asked to apply it before Claude says anything about it: recalling it is the practice |
| `progress.md` | Searched for topics relevant to this session; its "System design vocabulary" names the boxes on a sketch |

**Teach, don't design.** Claude gives facts and explains concepts. Design choices stay
yours: it shows options only when you are stuck or ask, and you pick with a reason.

**At the close**, when the frontier is empty and you have confirmed:

1. You write one or two lines in your own words: what you learned, and what is still
   unclear. Claude does not write them for you.
2. Claude updates the learning files from evidence only and shows you the update in a few
   lines.
3. If the session taught you something about working with Claude or agents (how you
   prompted, briefed, delegated or checked, or a mistake there), Claude adds a dated line
   to `~/.claude/learning/agentic-coding.md` under "Lessons learned" or "Setup changes",
   and rewrites "How I work now" if your workflow changed. Your words where possible.

What counts as evidence:

| Level | Meaning |
|---|---|
| Demonstrated | You reasoned it yourself: proposed it, or explained why, and it held up |
| Introduced | Claude explained it, or you picked its recommendation without your own why. Clicking a recommendation is never Demonstrated |
| Needs reinforcement | You got it wrong, or said it is still unclear |

What it writes:

| File | What changes |
|---|---|
| `progress.md` | One `## <Topic>` per concept (`## Caching`, `## Idempotent retries`), readable on its own, with three bullet lists: Introduced, Demonstrated, Needs reinforcement. Each bullet is dated and names the project. An existing topic is updated, never duplicated |
| `profile.md` | Your own document. Only the Strong / Developing / Revisit lists at its end are touched (Strong: demonstrated more than once across sessions; Developing: once, or introduced and partly applied; Revisit: needs reinforcement). The rest is never rewritten |
| `agentic-coding.md` | Only for a lesson about working with agents, as above |

It never records quotations of whole exchanges, and never anything from a proprietary
document: concepts and decisions only.

If you have no `~/.claude/learning/` folder, the grilling itself still works; set the folder
up from the [learning-by-building install section](../../learning-by-building/README.md#install) to get
the learning mode.

## A short session

Made up, but true to the skill.

**You:** grill me: our nightly export job sometimes sends the same report twice.

**Round 0.** Your message gives the problem but not what done looks like or an approach,
so Claude asks one prompt with three questions. Problem: "Duplicate report emails, seen by
customers" (a reading of what you wrote). Done: "Every report is sent exactly once, even
after a crash", or "Duplicates are rare enough". Approach: "Don't know yet" or "Just
propose". You pick "Don't know yet".

**Teaching.** Claude asks which part is unclear, you say "why it happens twice at all".
Claude names it: "this is a retry-without-idempotency problem." Under **Concept** it
explains, on a made-up job that sends then crashes before marking the report done, why a
retry sends it again, and what an idempotency key is, with one source. Then: "How would
you apply this here?" You answer in plain text: store a sent-marker per report and day,
check it before sending.

**Round 1.** Your sent-marker is now the root. The frontier has three decisions, asked in
one prompt:

| Header | Options (recommendation first) |
|---|---|
| Key | Report id + date (Recommended) / Report id only / Hash of the content |
| Store | The job's existing database (Recommended) / A file next to the job |
| Order | Mark before sending / Mark after sending (Recommended) |

Above the prompt, Claude explains the trade-off: marking before sending loses a report if
the send fails; marking after sending can still duplicate on a crash between the two
steps. You pick the recommendations, but on "Order" you add a note: "can the mail provider
dedupe for us?" That note is the strongest signal of the round. Claude sends a subagent to
check whether the mail client in your repo accepts an idempotency key, instead of asking
you.

**Round 2: a structure decision.** The subagent finds that it does. That adds a boundary
to the design, so Claude asks in plain text what you would draw and why, then opens
`/whiteboard`. You draw `Scheduler --> Export job --> Sent-marker store`, with an edge to
`Mail provider` marked `?`. Claude grills one box at a time ("what happens if the store is
down: do you send or skip?"), then draws its alternative beside yours, with the key passed
to the provider. You pick yours plus the key, and say why.

**Close.** The frontier is empty and you confirm. You write: "learned: a retry needs a key,
or it repeats the side effect. Unclear: where the key should live when two services both
retry." Claude shows the update: `progress.md`, `## Idempotent retries`, Demonstrated
(dated, your project), because you proposed the marker and defended the box; "where the key
lives across services" under Needs reinforcement.

## Install

```sh
npx skills@latest add bobocs50/bobo-cooking-stack --skill grilling
```

Pick which coding agents to install it on. It writes the skill as files you own and can
edit; pull later changes with `npx skills update`.

Or as a Claude Code plugin (it brings this repo's skills together), from inside a session:

```
/plugin marketplace add bobocs50/bobo-cooking-stack
/plugin install bobo-cooking-stack@bobo-cooking-stack
```

Or by hand, user-level on macOS / Linux:

```sh
mkdir -p ~/.claude/skills/grilling && curl -fsSL https://raw.githubusercontent.com/bobocs50/bobo-cooking-stack/main/skills/grilling/SKILL.md -o ~/.claude/skills/grilling/SKILL.md
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills\grilling" | Out-Null; Invoke-WebRequest https://raw.githubusercontent.com/bobocs50/bobo-cooking-stack/main/skills/grilling/SKILL.md -OutFile "$HOME\.claude\skills\grilling\SKILL.md"
```

For the drawing step, install [whiteboard](../whiteboard/README.md) too. For learning mode,
set up the [learning-by-building](../../learning-by-building/README.md#install).

## Run

In Claude Code: `/grilling`, or any "grill" phrase such as "grill me on this plan".
Installed as a plugin, the command is namespaced: `/bobo-cooking-stack:grilling`.

## Files

| File | What it does |
|---|---|
| [`SKILL.md`](SKILL.md) | The whole skill: the instructions Claude follows, with the trigger description in its front matter |
| [`agents/openai.yaml`](agents/openai.yaml) | Display metadata for other agent tools that look for `agents/openai.yaml`: a display name "Grilling" and the short description "Stress-test thinking a round of questions at a time". It holds no instructions; the skill's behaviour is all in `SKILL.md` |

## What it will not do

- **Pick for you.** It always has a recommendation, but every decision is yours, and when
  you are taught a concept you choose the approach and give the reason.
- **Ask you for facts it can look up.** Those go to a subagent.
- **Draw before you do.** At a structure decision your sketch comes first.
- **Act on the plan** before you confirm the shared understanding.
- **Record more than it saw.** A click on its recommendation is Introduced, never
  Demonstrated; no quotations of whole exchanges and nothing from proprietary documents go
  into the learning files.
- **Rewrite your profile.** Only the Strong / Developing / Revisit lists at the end of
  `profile.md` change.

## Requirements and limits

- Written for Claude Code: it asks through the `AskUserQuestion` prompt and dispatches
  subagents to look up facts.
- The drawing step needs the [whiteboard](../whiteboard/README.md) skill (Python, and a
  browser that can reach the CDN Excalidraw loads from).
- Learning mode needs the files in `~/.claude/learning/` from the
  [learning-by-building](../../learning-by-building/README.md).

## FAQ

**Is this a quiz?** No. It is a design review of your plan in which you do the reasoning.
The questions are decisions in your plan, not tests of vocabulary.

**Can I just get an answer?** Yes. Say "just tell me" or "skip". Claude explains or moves
on, and records the concept as Introduced.

**Why up to 4 questions a round, not one at a time?** Every decision that can be answered
now is asked together; one at a time would make you wait on questions that do not depend on
each other. More than 4 are queued for the next round.

**Why does it ask "what would you do and why?" in plain text sometimes?** Only where your
reasoning is the point: at a structure decision, and when a new or shaky concept decides
the answer. A click does not show reasoning. Everywhere else you click.

**What if none of the options fit?** Pick "Other" and write your answer. Claude treats that
as a sign its options were wrong and rethinks the tree.

## Related

- [whiteboard](../whiteboard/README.md): the hand-drawn board used at structure decisions.
- [learning-by-building](../../learning-by-building/README.md): the `~/.claude/learning/` files this skill
  reads and updates, and the weekly report.
- [weekly-review](../../learning-by-building/weekly-review/README.md): turns the week's counts into a review and
  updates the same profile.

## Credits

Builds on the grilling skill in Matt Pocock's
[skills](https://github.com/mattpocock/skills) (MIT). The learning mode is modelled on
[nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise).
