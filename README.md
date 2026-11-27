<div align="center">

<img src="assets/logo.svg" width="96" alt="">

# bobo-cooking-stack

Three Claude Code skills for building real software with AI agents.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-orange.svg)](.claude-plugin/plugin.json)

</div>

<br>

<table>
<tr>
<td width="33%" align="center" valign="top">
<img src="assets/glendonize.svg" width="64" alt=""><br>
<h3><a href="skills/glendonize/README.md">glendonize</a></h3>
Builds a harness for your repo: <a href="https://github.com/glendonC/1321">glendonC</a> plus Kun Chen's no-mistakes push pipeline, inspired by poteto's pstack.<br><br>
<code>/glendonize</code>
</td>
<td width="33%" align="center" valign="top">
<img src="assets/grilling.svg" width="64" alt=""><br>
<h3><a href="skills/grilling/README.md">grilling</a></h3>
Asks you about a plan one round at a time, until every decision is settled and nothing gets built by guess.<br><br>
<code>/grilling</code>
</td>
<td width="33%" align="center" valign="top">
<img src="assets/whiteboard.svg" width="64" alt=""><br>
<h3><a href="skills/whiteboard/README.md">whiteboard</a></h3>
Opens a hand-drawn board in your browser. You draw the structure, Claude reads it back.<br><br>
<code>/whiteboard</code>
</td>
</tr>
</table>

## Install

As a Claude Code plugin:

```
/plugin marketplace add bobocs50/bobo-cooking-stack
/plugin install bobo-cooking-stack@bobo-cooking-stack
```

Or as editable files, for any agent:

```bash
npx skills@latest add bobocs50/bobo-cooking-stack                   # all three
npx skills@latest add bobocs50/bobo-cooking-stack --skill grilling  # just one
```

Pick one way, not both. Each skill's own page has the details.

## Credits

[glendonC/1321](https://github.com/glendonC/1321) and Kun Chen's [no-mistakes](https://github.com/kunchenguid/no-mistakes) and poteto's [pstack](https://github.com/cursor/plugins/tree/main/pstack) for glendonize, Matt Pocock's [skills](https://github.com/mattpocock/skills) for grilling, [nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise) for grilling's learning mode.

MIT licensed. Issues and pull requests welcome.
