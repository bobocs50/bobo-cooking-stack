# Plans

<!--
Status: current - changes in the same commit as a plan is set, a step moves, or a plan ends
Checked against: <sha7> (<date>)
-->

Work that runs over more than one session, written where every session and
every subagent can read it. The live state of a swarm stays in the gitignored
coordination log (D-nnn); a plan here is the goal, the steps and what was
chosen on the way.

## 1. Rules

1. A plan is written here when the user sets it, before its first step starts.
2. Each plan names its goal, a "Done when" line that a number can check, its
   steps with their state (open, running, done, dropped), and a dated log of the
   choices made on the way, each pointing at its D-, Q- or issue id.
3. A step's state changes in the same commit as the work that moved it.
4. A finished plan is never deleted. It moves to section 3, its steps folded
   into one line, with the numbers that met its "Done when". A dropped plan
   moves there too, with the reason.
5. A plan holds no rule and no decision of its own: a rule goes to AGENTS.md or
   CLAUDE.md, a decision to DECISIONS.md, a parked branch to OPEN_QUESTIONS.md.

## 2. Active

### 2.1 <Plan name> (<start date>)

Goal: <one sentence>.

Done when: <a sentence a number can say no to>.

Steps:
1. <step> - open
2. <step> - open

Log:
- <date> - plan set by the user.

## 3. Completed

None yet.
