"""Drill for the CI backstop of the commit review hook (D-123). Every commit after the one
that wired `review_diff.py` into .claude/settings.json and that touches main/ eval/ tests/
frontend/ .github/ or .claude/hooks/ must carry exactly one `Agent-Review:` trailer
`<pass|answered|skipped> <12 hex> <model or ->`, and the 12 hex must equal the first 12 hex
of sha256 over `git diff --binary --no-color --no-ext-diff <c>^ <c>`, the bytes the hook
hashed from the staged diff before the commit. A `skipped` stamp passes but is printed.
Needs the full history (verify.yml checks out with fetch-depth 0). Free and offline.

    python tests/drill_review_stamp.py

The self-test builds a throwaway repo, so the checker is proven before the hook is wired.
"""

import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from _drill import expect

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEWED_PREFIXES = ("main/", "eval/", "tests/", "frontend/", ".github/", ".claude/hooks/")
TRAILER_PATTERN = re.compile(r"^(pass|answered|skipped) ([0-9a-f]{12}) \S+$")
GIT_IDENTITY = [
    "-c",
    "user.name=drill",
    "-c",
    "user.email=drill@example.invalid",
    "-c",
    "commit.gpgsign=false",
]


def git(repo, arguments):
    return subprocess.run(
        ["git"] + GIT_IDENTITY + arguments, cwd=repo, capture_output=True, check=True
    ).stdout


def git_text(repo, arguments):
    return git(repo, arguments).decode("utf-8", errors="replace")


def find_base(repo):
    out = git_text(
        repo,
        ["log", "--reverse", "--format=%H", "-S", "review_diff.py", "--", ".claude/settings.json"],
    )
    for line in out.splitlines():
        if line.strip():
            return line.strip()
    return None


def commits_after(repo, base):
    out = git_text(repo, ["rev-list", "--first-parent", "--reverse", base + "..HEAD"])
    commits = []
    for line in out.splitlines():
        if line.strip():
            commits.append(line.strip())
    return commits


def touches_reviewed_folder(repo, commit):
    out = git_text(repo, ["diff", "--name-only", "-z", commit + "^", commit])
    for path in out.split("\0"):
        if path.startswith(REVIEWED_PREFIXES):
            return True
    return False


def diff_hash(repo, commit):
    body = git(repo, ["diff", "--binary", "--no-color", "--no-ext-diff", commit + "^", commit])
    return hashlib.sha256(body).hexdigest()[:12]


def trailer_values(repo, commit):
    out = git_text(repo, ["log", "-1", "--format=%(trailers:key=Agent-Review,valueonly)", commit])
    values = []
    for line in out.splitlines():
        if line.strip():
            values.append(line.strip())
    return values


def check_commit(repo, commit):
    """Returns (ok, verdict text). ok is False only for a missing or wrong stamp."""
    if not touches_reviewed_folder(repo, commit):
        return True, "no review needed (no reviewed folder touched)"
    values = trailer_values(repo, commit)
    if len(values) != 1:
        return False, "needs exactly one Agent-Review trailer, found " + str(len(values))
    match = TRAILER_PATTERN.match(values[0])
    if match is None:
        return False, "malformed Agent-Review trailer"
    actual = diff_hash(repo, commit)
    if match.group(2) != actual:
        return False, "stamp hash " + match.group(2) + " is not the diff hash " + actual
    if match.group(1) == "skipped":
        return True, "NOTE review skipped by the user's escape hatch"
    return True, "stamped " + match.group(1)


def check_repo(repo):
    """Returns a list of (short sha, ok, verdict), or None when the hook is not wired."""
    base = find_base(repo)
    if base is None:
        return None
    results = []
    for commit in commits_after(repo, base):
        ok, verdict = check_commit(repo, commit)
        results.append((commit[:8], ok, verdict))
    return results


def write(repo, relative, text):
    path = Path(repo) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    git(repo, ["add", relative])


def commit_code(repo, message, stamp_hash=None, verdict="pass"):
    """Commits what is staged, with a stamp from the staged diff unless stamp_hash is given."""
    staged = git(repo, ["diff", "--cached", "--binary", "--no-color", "--no-ext-diff"])
    stamp = stamp_hash or hashlib.sha256(staged).hexdigest()[:12]
    arguments = ["commit", "-q", "-m", message]
    if stamp_hash != "none":
        arguments += ["--trailer", "Agent-Review: " + verdict + " " + stamp + " opus"]
    git(repo, arguments)
    return git_text(repo, ["rev-parse", "HEAD"]).strip(), staged


def self_test():
    print("self-test in a throwaway repo (D-123)")
    passed = True
    with tempfile.TemporaryDirectory() as folder:
        repo = folder
        git(repo, ["init", "-q"])
        write(repo, "main/a.py", "x = 1\n")
        git(repo, ["commit", "-q", "-m", "before the hook"])
        passed &= expect("no review_diff.py in settings.json: no base", find_base(repo) is None)
        passed &= expect("so the checker reports not wired", check_repo(repo) is None)

        write(repo, ".claude/settings.json", '{"hook": "review_diff.py"}\n')
        git(repo, ["commit", "-q", "-m", "wire the hook"])
        base = git_text(repo, ["rev-parse", "HEAD"]).strip()
        passed &= expect("base is the commit that adds review_diff.py", find_base(repo) == base)

        write(repo, "main/a.py", "x = 2\n")
        good, staged = commit_code(repo, "good stamp")
        passed &= expect(
            "hash of the staged diff equals the recomputed commit diff hash",
            hashlib.sha256(staged).hexdigest()[:12] == diff_hash(repo, good),
        )
        write(repo, "main/a.py", "x = 3\n")
        wrong, _ = commit_code(repo, "wrong hash", stamp_hash="0" * 12)
        write(repo, "main/a.py", "x = 4\n")
        unstamped, _ = commit_code(repo, "no stamp", stamp_hash="none")
        write(repo, "docs/n.txt", "a note\n")
        git(repo, ["commit", "-q", "-m", "notes only"])
        notes = git_text(repo, ["rev-parse", "HEAD"]).strip()
        write(repo, "eval/b.py", "y = 1\n")
        skipped, _ = commit_code(repo, "skipped", verdict="skipped")
        write(repo, "eval/b.py", "y = 2\n")
        answered, _ = commit_code(repo, "answered", verdict="answered")

        ok, verdict = check_commit(repo, good)
        passed &= expect("correct stamp passes: " + verdict, ok)
        ok, verdict = check_commit(repo, wrong)
        passed &= expect("wrong hash fails: " + verdict, not ok)
        ok, verdict = check_commit(repo, unstamped)
        passed &= expect("unstamped code commit fails: " + verdict, not ok)
        ok, verdict = check_commit(repo, notes)
        passed &= expect("notes-only commit needs no trailer: " + verdict, ok)
        ok, verdict = check_commit(repo, skipped)
        passed &= expect("skipped stamp passes with a note: " + verdict, ok and "NOTE" in verdict)
        ok, verdict = check_commit(repo, answered)
        passed &= expect("answered stamp passes: " + verdict, ok)

        results = check_repo(repo)
        if results is None:
            return expect("checker finds the base in the throwaway repo", False)
        passed &= expect("the base itself is not checked", len(results) == 6)
        failing = 0
        for _, ok, _ in results:
            if not ok:
                failing += 1
        passed &= expect("exactly the wrong and the unstamped commit fail", failing == 2)
    return passed


def check_real_repo():
    print("commits of this repo after the review hook was wired (D-123)")
    results = check_repo(REPO_ROOT)
    if results is None:
        print("  review hook not wired yet - nothing to check")
        return True
    passed = True
    for short, ok, verdict in results:
        passed &= expect(short + " " + verdict, ok)
    print("  checked " + str(len(results)) + " commits")
    return passed


def main():
    passed = self_test()
    passed &= check_real_repo()
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
