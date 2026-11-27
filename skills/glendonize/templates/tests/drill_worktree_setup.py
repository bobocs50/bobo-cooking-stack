"""Drill for .claude/hooks/worktree_setup.py: which gitignored files a fresh worktree is given and
which it is left without. A throwaway repo in a temp folder, no network, no credentials.

    python tests/drill_worktree_setup.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

import worktree_setup
from _drill import expect


def git(folder, *arguments):
    subprocess.run(
        ["git", "-C", str(folder), "-c", "user.email=drill@example.com", "-c", "user.name=drill"]
        + list(arguments),
        check=True,
        capture_output=True,
    )


def make_repo(base):
    main = base / "main_checkout"
    main.mkdir()
    git(main, "init", "-q")
    (main / "a.txt").write_text("a", encoding="utf-8")
    git(main, "add", "a.txt")
    git(main, "commit", "-q", "-m", "init")
    folder = Path(*worktree_setup.LINKED[0].split("/"))
    (main / folder).mkdir(parents=True)
    (main / folder / "cached.json").write_text("{}", encoding="utf-8")
    (main / worktree_setup.COPIED[0]).write_text("KEY=1\n", encoding="utf-8")
    worktree = base / "wt"
    git(main, "worktree", "add", "-q", str(worktree), "-b", "agent-branch")
    return main, worktree


def drill_plan_and_apply():
    print("1. a worktree is given the linked folders and the copied files it lacks")
    ok = True
    base = Path(tempfile.mkdtemp(prefix="wsdrill"))
    try:
        main, worktree = make_repo(base)
        ok &= expect("the main checkout is found from git", worktree_setup.main_checkout(worktree)
                     is not None
                     and worktree_setup.main_checkout(worktree).resolve() == main.resolve())
        steps = worktree_setup.plan(main, worktree)
        ok &= expect("the plan holds one link and one copy", [s[0] for s in steps] == ["link", "copy"])
        done = subprocess.run(
            [sys.executable, str(REPO_ROOT / ".claude" / "hooks" / "worktree_setup.py"),
             str(worktree), "--dry-run"],
            capture_output=True,
            text=True,
        )
        ok &= expect(
            "--dry-run lists both and changes nothing",
            done.returncode == 0
            and "would link" in done.stdout
            and "would copy" in done.stdout
            and not (worktree / worktree_setup.COPIED[0]).exists(),
        )
        done = subprocess.run(
            [sys.executable, str(REPO_ROOT / ".claude" / "hooks" / "worktree_setup.py"),
             str(worktree)],
            capture_output=True,
            text=True,
        )
        folder = Path(*worktree_setup.LINKED[0].split("/"))
        ok &= expect("the run exits 0", done.returncode == 0)
        ok &= expect(
            "the cached file is reachable through the link",
            (worktree / folder / "cached.json").is_file(),
        )
        ok &= expect(
            "the copied file is there", (worktree / worktree_setup.COPIED[0]).read_text() == "KEY=1\n"
        )
        ok &= expect("a second pass finds nothing missing", worktree_setup.plan(main, worktree) == [])
    finally:
        link = base / "wt" / Path(*worktree_setup.LINKED[0].split("/"))
        if link.exists():
            if os.name == "nt":
                subprocess.run(["cmd", "/c", "rmdir", str(link)], capture_output=True)
            else:
                link.unlink()
        shutil.rmtree(base, ignore_errors=True)
    return ok


def drill_leaves_what_exists():
    print("2. a folder or file already in the worktree is left as it is")
    ok = True
    base = Path(tempfile.mkdtemp(prefix="wsdrill"))
    try:
        main, worktree = make_repo(base)
        (worktree / worktree_setup.COPIED[0]).write_text("KEY=mine\n", encoding="utf-8")
        folder = Path(*worktree_setup.LINKED[0].split("/"))
        (worktree / folder).mkdir(parents=True)
        ok &= expect("nothing is planned", worktree_setup.plan(main, worktree) == [])
        ok &= expect(
            "the worktree's own .env is untouched",
            (worktree / worktree_setup.COPIED[0]).read_text() == "KEY=mine\n",
        )
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return ok


def drill_refuses_a_non_worktree():
    print("3. a folder that is no git worktree is refused, the main checkout itself is a no-op")
    ok = True
    base = Path(tempfile.mkdtemp(prefix="wsdrill"))
    try:
        main, worktree = make_repo(base)
        plain = base / "plain"
        plain.mkdir()
        hook = str(REPO_ROOT / ".claude" / "hooks" / "worktree_setup.py")
        done = subprocess.run([sys.executable, hook, str(plain)], capture_output=True, text=True)
        ok &= expect("no .git entry: exit 2", done.returncode == 2)
        done = subprocess.run([sys.executable, hook, str(main)], capture_output=True, text=True)
        ok &= expect("the main checkout: exit 0 and nothing to do", done.returncode == 0
                     and "nothing to do" in done.stdout)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return ok


def main():
    passed = drill_plan_and_apply()
    passed &= drill_leaves_what_exists()
    passed &= drill_refuses_a_non_worktree()
    print("ALL PASSED" if passed else "FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
