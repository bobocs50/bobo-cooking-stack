"""Drill for .claude/hooks/housekeeping.py, the SessionEnd cleanup: it removes an
agent worktree only when nothing in it can be lost. Run in a throwaway git repo with
its own worktrees - never in this repo.

    python tests/drill_housekeeping.py

Cost: free - offline, invented files only.

Adapt per repo: nothing for the scenario, which sets its own REBUILT, PAID_CACHE and
DEFAULT_BRANCH on the hook (the invented repo below matches them); drill_settings checks
the hook's real values. Needs tests/_drill.py and Python 3.12+.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

import housekeeping
from _drill import expect

# The scenario builds its own repo, so it sets the knobs an adapted hook may have changed;
# drill_settings checks the values the repo really runs with.
REAL = (list(housekeeping.REBUILT), housekeeping.PAID_CACHE)
housekeeping.REBUILT = [".claude/settings.local.json", ".ruff_cache/", "node_modules/"]
housekeeping.PAID_CACHE = "data/paid_cache/"
housekeeping.DEFAULT_BRANCH = "main"

IDENTITY = ["-c", "user.name=drill", "-c", "user.email=drill@example.invalid"]
OLD = str(int(time.time()) - 72 * 3600) + " +0000"


def git(cwd, *arguments, old=False):
    env = dict(os.environ)
    if old:
        env["GIT_COMMITTER_DATE"] = OLD
        env["GIT_AUTHOR_DATE"] = OLD
    return subprocess.run(
        ["git"] + IDENTITY + list(arguments), cwd=cwd, capture_output=True, text=True, env=env
    )


def worktree(repo, name, commit_file=None):
    path = repo / ".claude" / "worktrees" / name
    git(repo, "worktree", "add", "-q", "-b", "worktree-" + name, str(path), "main")
    if commit_file:
        (path / commit_file).write_text(name + "\n", encoding="utf-8")
        git(path, "add", commit_file)
        git(path, "commit", "-q", "-m", name)
    return path


def link_folder(link, target):
    """A junction on Windows, as agents make them, a symlink elsewhere."""
    Path(link).parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, check=True
        )
    else:
        os.symlink(target, link, target_is_directory=True)


def new_repo(folder):
    repo = Path(folder) / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    # git sees a Windows junction as a folder, which "data/paid_cache/" matches, but a
    # symlink as a file, which it does not; without the slash the symlink stands in for
    # the junction on a Linux runner.
    cache_ignore = "data/paid_cache/" if os.name == "nt" else "data/paid_cache"
    (repo / ".gitignore").write_text(
        "out/\n__pycache__/\n.claude/settings.local.json\n.ruff_cache/\n"
        "node_modules/\n" + cache_ignore + "\n",
        encoding="utf-8",
    )
    (repo / "data" / "paid_cache").mkdir(parents=True)
    (repo / "data" / "paid_cache" / "known.json").write_text("{}", encoding="utf-8")
    git(repo, "add", "a.txt", ".gitignore")
    git(repo, "commit", "-q", "-m", "base", old=True)
    return repo


def drill_rules():
    print("1. what is removed and what is kept")
    passed = True
    with tempfile.TemporaryDirectory() as folder:
        repo = new_repo(folder)
        # Made from the three-day-old main before the merge, so only its git activity
        # is fresh.
        cache_only = worktree(repo, "agent-cache")
        (cache_only / "__pycache__").mkdir()
        (cache_only / "__pycache__" / "a.cpython-313.pyc").write_bytes(b"x")
        merged = worktree(repo, "agent-merged", "m.txt")
        git(repo, "merge", "-q", "--ff-only", "worktree-agent-merged")
        dirty = worktree(repo, "agent-dirty")
        (dirty / "a.txt").write_text("changed\n", encoding="utf-8")
        untracked = worktree(repo, "agent-untracked")
        (untracked / "new.txt").write_text("new\n", encoding="utf-8")
        ignored = worktree(repo, "agent-ignored")
        (ignored / "out").mkdir()
        (ignored / "out" / "run.json").write_text("{}", encoding="utf-8")
        unmerged = worktree(repo, "agent-unmerged", "u.txt")
        # Landed the way the push pipeline lands: the same change in main under another hash.
        rebased = worktree(repo, "agent-rebased", "r.txt")
        git(repo, "cherry-pick", "-x", "worktree-agent-rebased")
        # What a real agent worktree holds: every one has the settings.local.json copy.
        real = worktree(repo, "agent-real")
        (real / ".claude").mkdir()
        (real / ".claude" / "settings.local.json").write_text("{}", encoding="utf-8")
        (real / ".ruff_cache").mkdir()
        (real / ".ruff_cache" / "x").write_text("x", encoding="utf-8")
        (real / "node_modules" / "pkg").mkdir(parents=True)
        (real / "node_modules" / "pkg" / "index.js").write_text("", encoding="utf-8")
        (real / "data").mkdir()
        link_folder(real / "data" / "paid_cache", repo / "data" / "paid_cache")
        # Left by an earlier run: git dropped the worktree, the junction stayed.
        shell = repo / ".claude" / "worktrees" / "agent-shell" / "data"
        shell.mkdir(parents=True)
        link_folder(shell / "paid_cache", repo / "data" / "paid_cache")
        # Branches an earlier pass left without their worktree.
        git(repo, "branch", "worktree-agent-landed", "main")
        lone = worktree(repo, "agent-lone", "l.txt")
        git(repo, "worktree", "remove", "--force", str(lone))
        stray = repo / ".claude" / "worktrees" / "agent-stray"
        stray.mkdir()
        (stray / "notes.txt").write_text("x", encoding="utf-8")
        paid = worktree(repo, "agent-paid-cache")
        (paid / "data" / "paid_cache").mkdir(parents=True)
        (paid / "data" / "paid_cache" / "new.json").write_text("{}", encoding="utf-8")

        fresh = housekeeping.clean(repo, dry_run=True, now=int(time.time()), min_age_hours=24)
        passed &= expect(
            "worktrees made just now from a three-day-old main are kept: their last git "
            "activity is fresh although their commit is old (an agent may work in them)",
            fresh["removed"] == [] and fresh["kept"].get("used in the last 24 h", 0) >= 1,
        )
        later = int(time.time()) + 48 * 3600
        result = housekeeping.clean(repo, now=later)
        passed &= expect(
            "only the clean merged worktree, one whose change main holds under another "
            "hash (the push pipeline rebases), the one holding nothing but __pycache__ and "
            "one shaped like a real agent worktree (settings.local.json copy, .ruff_cache, "
            "node_modules, a paid cache main already has) go",
            sorted(result["removed"])
            == ["agent-cache", "agent-merged", "agent-real", "agent-rebased"]
            and not rebased.exists()
            and not merged.exists()
            and not cache_only.exists()
            and not real.exists(),
        )
        passed &= expect(
            "the agent's junction to the main paid cache is unlinked, never followed: the "
            "worktree folder and a shell an earlier run left are gone, the cache file stays, "
            "and an unlisted folder holding a real file is not touched",
            not (repo / ".claude" / "worktrees" / "agent-shell").exists()
            and result["shells"] == 1
            and (repo / "data" / "paid_cache" / "known.json").exists()
            and (stray / "notes.txt").exists(),
        )
        passed &= expect(
            "a paid-cache file the main checkout lacks keeps its worktree: it cost money to make",
            paid.exists() and (paid / "data" / "paid_cache" / "new.json").exists(),
        )
        passed &= expect(
            "a worktree with a gitignored output (out/run.json) is kept with it: git "
            "worktree remove would delete it, and git status does not show it",
            ignored.exists()
            and (ignored / "out" / "run.json").exists()
            and result["kept"].get("has ignored files") == 2,
        )
        passed &= expect(
            "a change, an untracked file and a commit not in main keep a worktree too",
            dirty.exists()
            and untracked.exists()
            and unmerged.exists()
            and result["kept"].get("has changes") == 2
            and result["kept"].get("commit not in main") == 1,
        )
        branches = git(repo, "branch", "--list", "worktree-*").stdout
        passed &= expect(
            "the removed worktrees' branches are deleted, also the one main holds under "
            "another hash; the unmerged branch stays",
            "worktree-agent-merged" not in branches
            and "worktree-agent-rebased" not in branches
            and "worktree-agent-unmerged" in branches,
        )
        passed &= expect(
            "a branch an earlier pass left without its worktree goes when main holds it; "
            "one holding a commit main lacks stays",
            "worktree-agent-landed" not in branches and "worktree-agent-lone" in branches,
        )

        gone = worktree(repo, "agent-gone")
        shutil.rmtree(gone)
        missing = housekeeping.clean(repo, dry_run=True, now=later)
        passed &= expect(
            "a listed worktree whose folder is gone is skipped and counted, not a crash "
            "that stops the pass",
            missing["kept"].get("folder missing") == 1,
        )
        entry = repo / ".git" / "worktrees" / "agent-gone"
        os.chmod(entry, stat.S_IREAD | stat.S_IEXEC)
        live_entry = repo / ".git" / "worktrees" / "agent-unmerged"
        pruned = housekeeping.clean(repo, now=later)
        passed &= expect(
            "a stale entry left read-only is pruned, so git no longer prints 'failed to "
            "delete ... Permission denied'; a live worktree's entry stays",
            pruned["stale_pruned"] == 1 and not entry.exists() and live_entry.exists(),
        )
    return passed


def drill_real_clock():
    print("1b. at the real time, the hook's own git status is not activity")
    passed = True
    with tempfile.TemporaryDirectory() as folder:
        repo = new_repo(folder)
        idle = worktree(repo, "agent-idle")
        old = time.time() - 72 * 3600
        admin = repo / ".git" / "worktrees" / "agent-idle"
        for item in [idle / ".git", admin] + list(admin.rglob("*")):
            os.utime(item, (old, old))
        result = housekeeping.clean(repo)
        passed &= expect(
            "a clean worktree untouched for three days goes when the hook runs now: "
            "the git status it runs first rewrites the index, and that no longer counts "
            "as use (with it, every worktree looked used 0 s ago and none ever went)",
            result["removed"] == ["agent-idle"] and not idle.exists(),
        )
    return passed


def drill_log_place():
    print("1c. a session that ends inside an agent worktree logs in the main checkout")
    with tempfile.TemporaryDirectory() as folder:
        repo = new_repo(folder)
        inside = worktree(repo, "agent-session")
        saved = (housekeeping.REPO_ROOT, housekeeping.LOG)
        housekeeping.REPO_ROOT, housekeeping.LOG = inside, None
        try:
            housekeeping.main([])
        finally:
            housekeeping.REPO_ROOT, housekeeping.LOG = saved
        log = Path(".claude") / "orchestration" / "housekeeping.log"
        return expect(
            "the line lands in the main checkout's log, none in the worktree: a log there "
            "is a gitignored file that would keep the worktree forever",
            (repo / log).exists() and not (inside / log).exists(),
        )


def drill_never_fails():
    print("2. the hook never fails the session and always logs")
    passed = True
    with tempfile.TemporaryDirectory() as folder:
        saved = (housekeeping.clean, housekeeping.LOG)
        housekeeping.LOG = Path(folder) / "housekeeping.log"

        def broken(repo, dry_run=False):
            raise RuntimeError("drill")

        housekeeping.clean = broken
        try:
            code = housekeeping.main([])
        finally:
            housekeeping.clean, housekeeping.LOG = saved
        lines = (Path(folder) / "housekeeping.log").read_text(encoding="utf-8").splitlines()
        passed &= expect(
            "an error inside the cleanup exits 0 and writes one log line naming it",
            code == 0 and len(lines) == 1 and "RuntimeError" in json.loads(lines[0])["error"],
        )
    return passed


def drill_wired():
    print("3. the hook is registered")
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = []
    for group in settings.get("hooks", {}).get("SessionEnd", []):
        for hook in group.get("hooks", []):
            commands.append(hook.get("command", ""))
    found = False
    for command in commands:
        if "housekeeping.py" in command:
            found = True
    return expect(
        "settings.json runs housekeeping.py on SessionEnd: unregistered, it never runs "
        "(in production the entry was once lost in a checkout reset)",
        found,
    )


def drill_settings():
    print("4. the hook's real settings keep what every agent worktree holds")
    rebuilt, paid = REAL
    passed = expect(
        "REBUILT lists .claude/settings.local.json: Claude Code copies it into every "
        "worktree, so without it no worktree was ever removed",
        ".claude/settings.local.json" in rebuilt,
    )
    passed &= expect(
        "PAID_CACHE is None or a folder ending in '/'",
        paid is None or paid.endswith("/"),
    )
    return passed


def main():
    passed = drill_rules()
    passed &= drill_real_clock()
    passed &= drill_log_place()
    passed &= drill_never_fails()
    passed &= drill_wired()
    passed &= drill_settings()
    print("")
    print("ALL PASSED" if passed else "SOME FAILED")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
