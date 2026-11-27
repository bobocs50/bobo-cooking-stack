---
name: ui-compare
description: Show the user before/after screenshots of a UI change in the browser. Use after a UI change that matters (a new screen, layout or flow), not for small tweaks, and when the user types /ui-compare or asks "show me what changed" on screen. Needs a .ui-compare.json in the repo.
---

# ui-compare

The user does not read code. After a UI change they look at the before and after
side by side and say whether it is good. This skill produces that page.

## Run it

1. Pick the commits. Base = the commit before the change (e.g. `origin/main` or
   `HEAD~1`). Head = the commit with the change, or `WORKTREE` for uncommitted work.
2. Run, in the background if it may take minutes (it builds the frontend twice):

       python "%USERPROFILE%\.claude\skills\ui-compare\ui_compare.py" --repo <repo> --base <commit> --head <commit|WORKTREE> --open

   In Git Bash use `"$USERPROFILE/.claude/skills/ui-compare/ui_compare.py"`.
3. The last stdout line is `UI_COMPARE <path>` (the compare.html) or
   `UI_COMPARE FAILED <reason>`. Exit 0 ok, 1 failure, 2 usage error.
4. Tell the user the full path of compare.html. `--open` has already opened it in the
   default browser; if the run was started without it, run `start "" "<path>"`.
5. Report what the page shows only if you looked at the PNGs (see data rule).
   Never claim a visual check you did not take; "the page is open for you" is
   the honest default.

On `FAILED`, quote the reason verbatim and stop; do not retry blindly.

## What it does

- Checks out base and head as temporary detached git worktrees (WORKTREE = a copy of the
  tracked and untracked-not-ignored files), runs the repo's `setup` and `shots`
  commands in each, removes the worktrees afterwards, also on failure.
- Output: `C:\Users\<user>\ui-compare\<repo>\<YYYY-MM-DD-HHMM>-<shortsha>\` with
  `before\`, `after\`, `compare.html` (inline CSS, relative images, no CDN) and the
  marker `.ui-compare-run`. A name on one side only shows as "new" or "gone".
- Retention at every run: the newest 10 run folders per repo stay. A folder without the
  marker, or holding a file named `keep`, is never deleted. The first prune on a machine
  runs dry and writes `.pruned-once`. `--prune-dry-run` only prints what would go.

## Data rule

Screenshots show test or invented data only (R4, D-226). Read the PNGs yourself only when
the config's `"data"` says the data is invented. Real or unknown data: do not open the
images, give the user the path and let them look.

## Add it to a new repo

No `.ui-compare.json` makes the script stop with a message. To add one:

1. Ask the user (clickable question) which test data the screenshots may show: an
   invented fixture, a seeded demo account, a mock server. Never real or customer data. If
   no such data exists, say so and stop; do not point the app at real data.
2. Find how the repo starts its UI and runs browser tests (usually Playwright).
3. Write a spec that opens each screen and saves PNGs to the folder in env
   `UI_COMPARE_OUT`, serving on env `UI_PORT` (a free port the script picks).
4. Commit `.ui-compare.json` at the repo root:

       {"cwd": "frontend",
        "setup": [["npm","ci"],["npm","run","build"]],
        "shots": ["npx","playwright","test","e2e/ui_compare.spec.ts","--workers=1"],
        "copy_into_base": ["e2e/ui_compare.spec.ts","e2e/fixture.ts"],
        "path_extra": ["C:\\Program Files\\nodejs"],
        "data": "invented fixture e2e/fixture.ts"}

   - `cwd`: folder (relative to the repo root) where the commands run.
   - `setup`: commands run in order in both checkouts, each a list of arguments.
   - `shots`: the command that writes PNGs into `UI_COMPARE_OUT`.
   - `copy_into_base`: files (relative to `cwd`) copied from head into the base checkout,
     so an old base commit that predates the spec still gets shots.
   - `path_extra`: folders put in front of PATH (Node is not on PATH on this machine).
   - `data`: one line naming the test data; start it with "invented" only if it is.
5. Test with `--base HEAD --head WORKTREE` and open the page.

## Self-test

`python "%USERPROFILE%\.claude\skills\ui-compare\test_ui_compare.py"`: free, offline,
temp folders only (it sets `UI_COMPARE_ROOT`, so it never touches the real output folder).
