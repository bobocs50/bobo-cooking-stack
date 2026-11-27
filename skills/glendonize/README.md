<div align="center">

<img src="../../assets/glendonize.svg" width="80" alt="">

# glendonize

Builds a harness for your repo, so AI agents can work in it without making things up.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE) [![Claude Code skill](https://img.shields.io/badge/Claude%20Code-skill-orange.svg)](SKILL.md)

</div>

<br>

The harness is two proven setups put together:

<table>
<tr>
<td width="50%" valign="top">
<h3>The structure</h3>
From glendonC's many-minions and <a href="https://github.com/glendonC/1321">1321</a>.<br><br>
Written rules for agents, a numbered log of decisions that the code cites, notes with one owner each, and free checks that run before every commit.
</td>
<td width="50%" valign="top">
<h3>The push pipeline</h3>
From Kun Chen's <a href="https://github.com/kunchenguid/no-mistakes">no-mistakes</a>.<br><br>
Commits are instant. At the push, a background job reviews the change against what you asked for, verifies each finding, runs the tests, fixes small issues and only then pushes.
</td>
</tr>
</table>

Both inspired by poteto's [pstack](https://github.com/cursor/plugins/tree/main/pstack): skills that make an agent work like a careful engineer, so you can run several at once.

## Full or Yolo

glendonize asks first which one you want.

| | Full | Yolo |
|---|---|---|
| Rules, decision log, notes | yes | yes |
| Free checks before each commit | yes | yes |
| Push pipeline | yes | plain `git push` |
| Guards against paid scripts and private folders | yes | no |
| Good for | long projects, real data | hackathons, prototypes |

A Yolo repo can be upgraded to Full later by running it again.

## What it stops

| Problem | What glendonize does |
|---|---|
| The agent makes up a reason | A decision with no recorded reason says so |
| A surprise bill | Paid scripts are listed and kept out of the checks |
| A guessed value | A missing decision becomes an open question; that branch stops |
| Untested code | New code cannot land without a test, and tests cannot quietly lose checks |
| An unreviewed push | In Full, every push is reviewed and tested first |

## Install

```sh
npx skills@latest add bobocs50/bobo-cooking-stack --skill glendonize
```

Then run `/glendonize` in a git repo. It works in gated phases and writes nothing on the first pass. Run it again later and it picks up where it stopped.

The full rules are in [SKILL.md](SKILL.md). [All skills](../../README.md)
