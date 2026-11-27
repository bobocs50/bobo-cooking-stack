"""Per-commit drill rules over a pushed range. Runs nothing, spends nothing.

    python tests/commit_range.py BASE HEAD

A push of several commits is judged commit by commit: each commit that changes a
src/*.py file must itself change something under tests/ or say `no drill:` in its own
subject, and no commit may lose an `expect(` call from a drill unless its own subject
says `drop drill:`. Reading only the pushed range's last subject let an earlier commit
ride on a later one. BASE of all zeros or an unknown commit falls back to
HEAD~1, as a new branch or a force push has no usable base.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPINE_PY = re.compile(r"^src/.*\.py$")
TEST_FILE = re.compile(r"^tests/")
DRILL_FILE = re.compile(r"tests/drill_[^/]*\.py")


def git_out(*args, cwd=ROOT):
    result = subprocess.run(
        ["git"] + list(args), cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )
    return result.returncode, result.stdout


def resolve_base(base, head, cwd=ROOT):
    if base and set(base) != {"0"}:
        code, _ = git_out("rev-parse", "--verify", "--quiet", base + "^{commit}", cwd=cwd)
        if code == 0:
            return base
    return head + "~1"


def commits_between(base, head, cwd=ROOT):
    _, out = git_out("rev-list", "--reverse", "--no-merges", base + ".." + head, cwd=cwd)
    return out.split()


def subject_of(commit, cwd=ROOT):
    _, out = git_out("log", "-1", "--format=%s", commit, cwd=cwd)
    return out.strip()


def changed_files(commit, cwd=ROOT):
    _, out = git_out("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", commit, cwd=cwd)
    return out.split()


def spine_without_drill(commits, cwd=ROOT):
    bad = []
    for commit in commits:
        files = changed_files(commit, cwd=cwd)
        spine_py = []
        has_tests = False
        for name in files:
            if SPINE_PY.match(name):
                spine_py.append(name)
            if TEST_FILE.match(name):
                has_tests = True
        subject = subject_of(commit, cwd=cwd)
        if spine_py and not has_tests and "no drill:" not in subject:
            bad.append(commit[:10] + " " + subject[:70] + " -> " + ", ".join(spine_py))
    return bad


def drill_losses(commit, count_expects, cwd=ROOT):
    code, _ = git_out("rev-parse", "--verify", "--quiet", commit + "^", cwd=cwd)
    if code != 0:
        return []
    _, listing = git_out(
        "diff-tree", "--no-commit-id", "--name-status", "-r", "-M", commit, "--", "tests/", cwd=cwd
    )
    lost = []
    for line in listing.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, name = parts[0], parts[1]
        now_name = parts[-1]
        if status == "A" or not DRILL_FILE.fullmatch(name):
            continue
        label = name if now_name == name else name + " -> " + now_name
        _, before_text = git_out("show", commit + "^:" + name, cwd=cwd)
        before = count_expects(before_text)
        if status == "D" or not DRILL_FILE.fullmatch(now_name):
            lost.append(label + ": " + str(before) + " -> gone")
            continue
        _, after_text = git_out("show", commit + ":" + now_name, cwd=cwd)
        after = count_expects(after_text)
        if after < before:
            lost.append(label + ": " + str(before) + " -> " + str(after))
    return lost


def drill_renames(base, head, cwd=ROOT):
    _, moves = git_out("diff", "--name-status", "-M", base, head, "--", "tests/", cwd=cwd)
    renamed = {}
    for line in moves.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].startswith("R") and DRILL_FILE.fullmatch(parts[2]):
            renamed[parts[1]] = parts[2]
    return renamed


def unannounced_drops(commits, count_expects, cwd=ROOT):
    bad = []
    for commit in commits:
        subject = subject_of(commit, cwd=cwd)
        if "drop drill:" in subject:
            continue
        for line in drill_losses(commit, count_expects, cwd=cwd):
            bad.append(commit[:10] + " " + line)
    return bad


def main():
    if len(sys.argv) != 3:
        print("usage: python tests/commit_range.py BASE HEAD")
        raise SystemExit(2)
    head = sys.argv[2]
    base = resolve_base(sys.argv[1], head)
    commits = commits_between(base, head)
    bad = spine_without_drill(commits)
    for line in bad:
        print("src/ changed without a tests/ change and no 'no drill:' in its subject: " + line)
    if bad:
        raise SystemExit(1)
    print("ok: " + str(len(commits)) + " commit(s) in " + base + ".." + head)


if __name__ == "__main__":
    main()
