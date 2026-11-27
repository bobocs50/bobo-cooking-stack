"""Gives a fresh git worktree the gitignored files a run needs.

A worktree holds only tracked files. Runs from agent worktrees stopped, or cost money, for the
same reason, one missing file each: no cache of paid results (a probe paid for the same pages
twice), no .env (a start stopped before any call), no model cache (a run stopped asking for a paid
call). The files to give a worktree are listed here, once:

  LINKED   folders linked (a junction on Windows, a symlink elsewhere) to the main checkout's
           folder, so what a worktree run pays for lands in the shared cache and is never paid
           twice; a folder already there is left as it is
  COPIED   files copied when missing, so a run reaches its credentials

Nothing that counts a budget is provided: a budget file in the worktree would start from zero. A
paid run starts from the main checkout.

    python .claude/hooks/worktree_setup.py <worktree>            # link and copy
    python .claude/hooks/worktree_setup.py <worktree> --dry-run  # list it, change nothing

The main checkout is found from git (the parent of the common git dir), so no path is written
here. Free and offline: it links folders, copies files and calls nothing.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

LINKED = ["runtime/cache"]
COPIED = [".env"]
REMINDER = "paid runs start from the main checkout: its folders hold the budget's spend"


def main_checkout(worktree):
    done = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "--git-common-dir"],
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        return None
    common = Path(done.stdout.strip())
    if not common.is_absolute():
        common = (worktree / common).resolve()
    return common.parent


def plan(main, worktree):
    found = []
    for name in LINKED:
        source = main / name
        target = worktree / name
        if source.is_dir() and not target.exists():
            found.append(("link", source, target))
    for name in COPIED:
        source = main / name
        target = worktree / name
        if source.is_file() and not target.exists():
            found.append(("copy", source, target))
    return found


def link(source, target):
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(target), str(source)],
            check=True,
            capture_output=True,
        )
    else:
        os.symlink(source, target, target_is_directory=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("worktree", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--main", type=Path, default=None)
    args = parser.parse_args()
    worktree = args.worktree.resolve()
    if not (worktree / ".git").exists():
        print("not a git worktree (no .git entry): " + str(worktree))
        return 2
    main_dir = args.main or main_checkout(worktree)
    if main_dir is None:
        print("cannot find the main checkout from " + str(worktree))
        return 2
    main_dir = main_dir.resolve()
    if worktree == main_dir:
        print("the worktree is the main checkout itself: nothing to do")
        return 0
    steps = plan(main_dir, worktree)
    if not steps:
        print("nothing missing")
    for action, source, target in steps:
        print(("would " if args.dry_run else "") + action + ": " + str(target))
        if args.dry_run:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if action == "copy":
            shutil.copy2(source, target)
        else:
            link(source, target)
    if REMINDER:
        print(REMINDER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
