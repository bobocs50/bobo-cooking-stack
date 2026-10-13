---
name: whiteboard
description: Open a Mermaid flowchart as a full-screen, hand-drawn, editable whiteboard in the browser (local Excalidraw page, nothing installed) so the user can draw, rename boxes and write answers on them; Done saves a PNG and the scene for Claude to read. Use when the user says /whiteboard, "whiteboard", "draw it", "sketch this", or a grilling reaches a structure decision.
argument-hint: "[what to draw]"
---

A whiteboard between the user and Claude: one dark, full-screen board, the drawing toolbar, and three buttons: "Close board", "Save draft" and "Send to Claude". Nothing else. The page is `board.html` next to this file (Excalidraw from a CDN), served by `serve.py` (Python standard library, local only).

## The user draws first

The drawing is the user's thinking. So:
- If the user gave a sketch (boxes and arrows in words, or Mermaid), draw exactly that, nothing more.
- If they gave only a topic, ask in plain text for a rough sketch — "which boxes, which arrows, in your words" — and wait. Then draw theirs.
- Draw your own alternative only beside theirs, after grilling theirs, or when they say "draw it for me".

## Mermaid rules

- `flowchart TD` (top to bottom). No front matter needed; the board is hand-drawn and dark by itself.
- One concept per board. A second concept is a second board.
- Every box named with the system-design term where one applies (the system design section of `~/.claude/learning/progress.md` if there is one, otherwise the standard terms: cache, boundary, fallback, grounding step…). A box with no term is the first question to ask.
- Arrows are bare (`-->`). A label only where it says something the boxes don't, like `-->|retry and reconcile|`; a label that just repeats the boxes ("submit", "ok") is noise. An uncertain edge gets `?` as its label.
- A question for the user is a box: `Q1[/"Q: what happens when this fails?"/] -.- C`. The user answers by writing on or next to it.
- Nothing confidential: file and step names, never document text, data values or page images. A project's own data rules apply on top.

## The loop

1. Write the Mermaid to `.lavish/<slug>.mmd` in the current working directory (add `.lavish/` to the project's `.gitignore` if it is not there).
2. Run `python <skill dir>/serve.py .lavish/<slug>.mmd`, where `<skill dir>` is this skill's base directory (shown when the skill loads; `~/.claude/skills/whiteboard` for a user-level install), as a tracked background command with a long timeout. It opens the browser on a free port and waits. The user draws; **Save draft** (or Ctrl+S) writes `<slug>.excalidraw` + `<slug>.png` next to the `.mmd` and keeps the page open; **Send to Claude** writes them and the server exits (code 0), which notifies this session; **Close board** writes them too and the server exits (code 3) without sending, for a user who is done for now.
3. Read `<slug>.png` (the Read tool shows images) and, when the picture is not enough, `<slug>.excalidraw` (JSON: element `text` fields hold the box labels and the user's notes). Then update the Mermaid in `<slug>.mmd` to match what the user drew: the Mermaid stays the record, never the `.excalidraw`.
4. To reopen the same board, run `serve.py` again on the same `.mmd`: it loads the saved `.excalidraw` first, so the user's layout survives. Delete the `.excalidraw` to start from the Mermaid again.
5. At the end, paste the final Mermaid in the conversation. It goes into the project's docs only on the user's go.

If `serve.py` exits with code 3, the user clicked **Close board**: the draft is on disk, nothing was sent, so do not read the board as an answer; ask whether to reopen or to leave it. Code 1 means it was stopped (Ctrl+C) before either button. Closing the browser tab alone does not stop it: the server keeps waiting. When the user says they closed the tab, stop the background command and ask whether to reopen. The CDN (jsdelivr, esm.sh) must be reachable; without it the page shows "load failed".
