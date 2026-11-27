# Adapt per repo: set these before the first run; the rest of the file is production code as is.
#   REBUILT         gitignored paths that cost nothing to lose (caches, dependency folders, build
#                   output); keep .claude/settings.local.json, which Claude Code copies into every
#                   worktree - without it no worktree is ever removed.
#   PAID_CACHE      a gitignored folder of paid output (OCR, model answers) that agents fill, with
#                   a trailing slash, or None. A worktree whose copy holds a file the main
#                   checkout lacks is kept.
#   DEFAULT_BRANCH  the branch a worktree's commits must already be in ("main").
#   MIN_AGE_HOURS   how long a worktree must be idle before it may go (24).
#   the layout      .claude/worktrees/<name> and the worktree-agent-* branches are Claude Code's
#                   own agent-worktree names; change them only if the repo makes its own.
#   the log         .claude/orchestration/housekeeping.log in the main checkout (gitignore it).
# Needs Python 3.12+ (Path.is_junction). Wire it as a SessionEnd hook in .claude/settings.json.
"""SessionEnd hook: clears what agent runs leave behind, and nothing else.

1. `git worktree prune`: drops the .git/worktrees entries whose folder is gone (the
   source of the "failed to delete .git/worktrees/agent-...: Permission denied"
   lines on every commit). Windows leaves some of them read-only, which is why git
   could not delete them, so the read-only flag is cleared first - on stale entries
   only, never on a live worktree's.
2. Removes an agent worktree under .claude/worktrees/ only when nothing can be lost:
   no uncommitted change, no untracked file, no gitignored file (run outputs, a .env
   - `git worktree remove` deletes those too) other than what is rebuilt for free
   (REBUILT: caches, node_modules, the settings.local.json copy Claude Code puts in
   every worktree) or a paid cache (PAID_CACHE) whose every file the main checkout's
   copy already holds (it cost money to make), its commit already in main, and neither its
   last commit nor its last git activity younger than MIN_AGE_HOURS (an agent may
   still work in it). A commit main holds under another hash (a rebase) counts as
   in main. A listed worktree whose folder is gone is skipped and counted.
   Its branch worktree-agent-* goes too, and what git leaves of the folder (an agent's
   junction to the main checkout's paid cache): the link is unlinked, never followed.

A dirty, unmerged or young worktree is kept and counted. Every run appends one line
to the main checkout's .claude/orchestration/housekeeping.log. It never fails the session: any error is
logged and the hook exits 0. Free and offline.

    python .claude/hooks/housekeeping.py            # what the hook runs
    python .claude/hooks/housekeeping.py --dry-run  # say what would go
"""

import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# None: the main checkout's .claude/orchestration/housekeeping.log. A log written
# inside an agent worktree is a gitignored file that keeps that worktree forever.
LOG = None
MIN_AGE_HOURS = 24
# Gitignored paths that cost nothing to lose. Every agent worktree holds the
# settings.local.json copy, so without it no worktree was ever removed.
REBUILT = [
    ".claude/settings.local.json",
    ".ruff_cache/",
    ".pytest_cache/",
    "node_modules/",
    "dist/",
]
# None when the repo has no paid cache.
PAID_CACHE = "data/paid_cache/"
DEFAULT_BRANCH = "main"


def git(repo, arguments):
    return subprocess.run(
        ["git"] + arguments, cwd=repo, capture_output=True, text=True, encoding="utf-8"
    )


def stale_entries(repo):
    """The .git/worktrees/<name> folders whose worktree folder no longer exists."""
    stale = []
    admin = Path(repo) / ".git" / "worktrees"
    if not admin.is_dir():
        return stale
    for entry in admin.iterdir():
        gitdir = entry / "gitdir"
        target = gitdir.read_text(encoding="utf-8").strip() if gitdir.exists() else ""
        if not target or not Path(target).exists():
            stale.append(entry)
    return stale


def make_writable(folder):
    for root, folders, files in os.walk(folder):
        for name in folders + files:
            path = os.path.join(root, name)
            os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)
    os.chmod(folder, os.stat(folder).st_mode | stat.S_IWRITE)


def agent_worktrees(repo):
    """(path, branch) of every worktree under .claude/worktrees/, from git's own list."""
    found = []
    path = None
    for line in git(repo, ["worktree", "list", "--porcelain"]).stdout.splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree ") :])
        elif line.startswith("branch ") and path is not None:
            if ".claude/worktrees/" in path.as_posix():
                found.append((path, line[len("branch refs/heads/") :]))
    return found


def removable(repo, path, now, min_age_hours):
    """Why this worktree stays, or None when nothing in it can be lost."""
    if not Path(path).is_dir():
        return "folder missing"
    status = git(path, ["status", "--porcelain", "--ignored"])
    if status.returncode != 0:
        return "unreadable"
    for line in status.stdout.splitlines():
        if line.startswith("!! ") and lossless(repo, path, line[3:]):
            continue
        if line.startswith("!! "):
            return "has ignored files"
        return "has changes"
    head = git(path, ["rev-parse", "HEAD"]).stdout.strip()
    if git(repo, ["merge-base", "--is-ancestor", head, DEFAULT_BRANCH]).returncode != 0:
        # The push pipeline rebases before it lands, so a landed commit is in main under
        # another hash; git cherry marks every commit main lacks by content with "+".
        cherry = git(repo, ["cherry", DEFAULT_BRANCH, head])
        if cherry.returncode != 0 or "+ " in cherry.stdout:
            return "commit not in main"
    stamp = git(path, ["log", "-1", "--format=%ct"]).stdout.strip()
    if not stamp or now - int(stamp) < min_age_hours * 3600:
        return "younger than " + str(min_age_hours) + " h"
    # A worktree just made from an old main has an old commit but is in use: the
    # admin folder git writes on every operation in it says when it was last used.
    if now - last_activity(path) < min_age_hours * 3600:
        return "used in the last " + str(min_age_hours) + " h"
    return None


def is_rebuilt(relative):
    if "__pycache__" in relative.split("/") or relative.endswith(".pyc"):
        return True
    for rebuilt in REBUILT:
        if relative == rebuilt or relative.startswith(rebuilt):
            return True
    return False


def lossless(repo, path, relative):
    """True when deleting this gitignored path loses nothing."""
    relative = relative.replace("\\", "/")
    if is_rebuilt(relative):
        return True
    if PAID_CACHE and relative.startswith(PAID_CACHE):
        return in_main_cache(repo, Path(path) / relative, Path(path) / PAID_CACHE)
    full = Path(path) / relative
    if not full.is_dir():
        return False
    # git reports a folder holding only ignored files as one line ("!! data/"), so
    # each file in it is judged on its own; rebuilt folders are not walked.
    for root, folders, files in os.walk(full):
        inside = Path(root).relative_to(path).as_posix() + "/"
        walked = []
        for name in folders:
            if not is_rebuilt(inside + name + "/"):
                walked.append(name)
        folders[:] = walked
        for name in files:
            if not lossless(repo, path, inside + name):
                return False
    return True


def in_main_cache(repo, target, cache_root):
    """Every file under target exists in the main checkout's paid cache, same size."""
    main_cache = Path(repo) / PAID_CACHE
    files = [target]
    if target.is_dir():
        files = []
        for item in target.rglob("*"):
            if item.is_file():
                files.append(item)
    for item in files:
        twin = main_cache / item.relative_to(cache_root)
        if not twin.is_file() or twin.stat().st_size != item.stat().st_size:
            return False
    return True


def last_activity(path):
    """The newest change time of the files in the worktree's admin folder under
    .git/worktrees/, without the index and the folder itself: any `git status`, this
    hook's own included, rewrites the index (through index.lock, which touches the
    folder), so with them every worktree looked used seconds ago and none ever went."""
    pointer = Path(path) / ".git"
    newest = pointer.stat().st_mtime
    if pointer.is_file():
        text = pointer.read_text(encoding="utf-8").strip()
        if text.startswith("gitdir:"):
            admin = Path(text[len("gitdir:") :].strip())
            for item in list(admin.glob("*")) + [admin / "logs" / "HEAD"]:
                if item.name.startswith("index") or not item.is_file():
                    continue
                newest = max(newest, item.stat().st_mtime)
    return int(newest)


def clean(repo, dry_run=False, now=None, min_age_hours=MIN_AGE_HOURS):
    """{'removed': [...], 'kept': {reason: count}} after one pass."""
    now = now or int(time.time())
    stale = stale_entries(repo)
    if not dry_run:
        for entry in stale:
            make_writable(entry)
        git(repo, ["worktree", "prune"])
    removed = []
    kept = {}
    for path, branch in agent_worktrees(repo):
        reason = removable(repo, path, now, min_age_hours)
        if reason is not None:
            kept[reason] = kept.get(reason, 0) + 1
            continue
        if not dry_run:
            done = git(repo, ["worktree", "remove", str(path)])
            if done.returncode != 0:
                kept["remove failed"] = kept.get("remove failed", 0) + 1
                continue
            # removable() proved every commit is in main, also under another hash,
            # which -d does not see, so -D loses nothing.
            git(repo, ["branch", "-D", branch])
            clear_shell(path)
        removed.append(path.name)
    shells = 0
    folder = Path(repo) / ".claude" / "worktrees"
    if folder.is_dir():
        listed = []
        for path, _branch in agent_worktrees(repo):
            listed.append(Path(path).name)
        for item in folder.iterdir():
            if item.is_dir() and item.name not in listed and not dry_run and clear_shell(item):
                shells += 1
    return {
        "removed": removed,
        "kept": kept,
        "stale_pruned": len(stale),
        "shells": shells,
        "branches": drop_landed_branches(repo, dry_run),
    }


def drop_landed_branches(repo, dry_run):
    """Deletes a worktree-agent-* branch no worktree holds whose every commit main has,
    by hash or by content (git cherry); an earlier pass removed its worktree."""
    held = []
    for _path, branch in agent_worktrees(repo):
        held.append(branch)
    dropped = 0
    refs = git(repo, ["for-each-ref", "--format=%(refname:short)", "refs/heads/worktree-agent-*"])
    for ref in refs.stdout.splitlines():
        if ref in held:
            continue
        cherry = git(repo, ["cherry", DEFAULT_BRANCH, ref])
        if cherry.returncode != 0 or "+ " in cherry.stdout:
            continue
        if not dry_run:
            git(repo, ["branch", "-D", ref])
        dropped += 1
    return dropped


def is_link(path):
    return path.is_symlink() or path.is_junction()


def clear_shell(folder):
    """Removes a folder git left behind holding only links and empty folders (an agent's
    junction to the main checkout's paid cache): a link is unlinked, never followed, so the cache it
    points to stays. False, and nothing touched, when a real file is in it."""
    folder = Path(folder)
    if not folder.is_dir() or is_link(folder) or not only_links(folder):
        return False
    remove_links(folder)
    return True


def only_links(folder):
    # os.walk descends into a Windows junction, so the walk is by hand.
    for item in folder.iterdir():
        if is_link(item):
            continue
        if not item.is_dir() or not only_links(item):
            return False
    return True


def remove_links(folder):
    for item in folder.iterdir():
        if item.is_junction():
            os.rmdir(item)
        elif item.is_symlink():
            item.unlink()
        else:
            remove_links(item)
    os.rmdir(folder)


def main_checkout(start):
    """The main checkout, also when the session that ends worked in a worktree."""
    common = git(start, ["rev-parse", "--path-format=absolute", "--git-common-dir"])
    if common.returncode != 0:
        return start
    return Path(common.stdout.strip()).parent


def main(argv):
    dry_run = "--dry-run" in argv
    repo = REPO_ROOT
    try:
        repo = main_checkout(REPO_ROOT)
        result = clean(repo, dry_run=dry_run)
    except Exception as error:
        result = {"error": type(error).__name__ + ": " + str(error)}
    entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "dry_run": dry_run}
    entry.update(result)
    if dry_run:
        print(json.dumps(entry, indent=2))
        return 0
    try:
        log = LOG or Path(repo) / ".claude" / "orchestration" / "housekeeping.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
