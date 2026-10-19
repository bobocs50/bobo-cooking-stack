"""Drill for the commit-review hook in .claude/hooks/review_diff.py: which commits it
lets through, refuses or denies on a confirmed defect, and the trailer it adds
(D-123). Every agent call is replaced by PROJECT_REVIEW_STUB, so nothing is spent and
nothing leaves the machine; the staged diffs come from a throwaway git repo in a
temp folder, never from this one.

    python tests/drill_review_hook.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "review_diff.py"
sys.path.insert(0, str(HOOK.parent))

import review_diff
from _drill import expect

COMMIT = 'git commit -m "change"'
DEFECT = {"id": "x", "file": "main/x.py", "line": 7, "claim": "wrong key", "kind": "defect"}
CONFIRMED = {"confirmed": True, "evidence": "main/x.py:7"}


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def temp_repo(tmp):
    repo = Path(tmp) / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    # The quoted-path line needs git to quote; a user config with quotepath=false must not
    # turn it red.
    git(repo, "config", "core.quotepath", "true")
    return repo


def staged(folder, name, text):
    """Stage one file in the throwaway repo and return its staged diff."""
    path = Path(folder) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    git(folder, "add", name)
    return review_diff.staged_diff_of(folder, False)


CALLS = [0]


def run_review(command, diff, stub, log, cache=None):
    """review() with the stub file, log and cache redirected to the temp folder; a fresh
    cache per call unless one is passed, so each case sees its own stub."""
    stub_path = Path(log).parent / "stub.json"
    stub_path.write_text(json.dumps(stub), encoding="utf-8")
    if cache is None:
        CALLS[0] += 1
        cache = Path(log).parent / f"cache{CALLS[0]}.json"
    os.environ["PROJECT_REVIEW_STUB"] = str(stub_path)
    os.environ["PROJECT_REVIEW_LOG"] = str(log)
    os.environ["PROJECT_REVIEW_CACHE"] = str(cache)
    decision, reason, new = review_diff.review(command, diff)
    return decision, reason or "", new or ""


def stub_with(a=(), verify=None):
    return {"A": list(a), "B": [], "C": [], "verify": verify or {}}


def drill_passes():
    print("1. a command that is not a commit, and a notes-only commit, pass untouched")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        repo = temp_repo(tmp)
        notes = staged(repo, "README.md", "x\n")
        log = Path(tmp) / "log.jsonl"
        out = run_review("git status", notes, stub_with(), log)
        ok &= expect("git status: pass, no rewrite", out == ("pass", "", ""))
        stub = stub_with(a=[DEFECT], verify={"A1": CONFIRMED})
        out = run_review(COMMIT, notes, stub, log)
        ok &= expect(
            "notes-only commit: pass with no trailer, agents never asked",
            out == ("pass", "", ""),
        )
        ok &= expect("notes-only commit writes no log line", not log.exists())
    return ok


def drill_verdicts():
    print("2. a code diff: confirmed defect denies, refuted passes, no evidence counts as refuted")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        repo = temp_repo(tmp)
        code = staged(repo, "main/x.py", "x = 1\n")
        log = Path(tmp) / "log.jsonl"
        hash12 = review_diff.diff_hash(code)
        stub = stub_with(a=[DEFECT], verify={"A1": CONFIRMED})
        decision, reason, _ = run_review(COMMIT, code, stub, log)
        ok &= expect("confirmed defect: deny", decision == "deny")
        ok &= expect(
            "the reason names file:line and the finding id",
            "main/x.py:7" in reason and "[A1]" in reason,
        )
        ok &= expect("the reason says how to answer", "not a defect because" in reason)
        refuted = {"confirmed": False, "evidence": "main/x.py:3 guards it"}
        decision, _, new = run_review(
            COMMIT, code, stub_with(a=[DEFECT], verify={"A1": refuted}), log
        )
        ok &= expect(
            "refuted by the verifier: allow with the pass trailer",
            decision == "allow" and f'--trailer "Agent-Review: pass {hash12} opus-full"' in new,
        )
        ok &= expect(
            "the trailer sits right after git commit", new.startswith("git commit --trailer ")
        )
        bare = {"confirmed": True, "evidence": "  "}
        decision, _, _ = run_review(COMMIT, code, stub_with(a=[DEFECT], verify={"A1": bare}), log)
        ok &= expect("confirmed without evidence counts as not confirmed", decision == "allow")
        decision, _, new = run_review(COMMIT, code, stub_with(), log)
        ok &= expect(
            "no findings: pass trailer", decision == "allow" and "Agent-Review: pass " in new
        )
        light = staged(repo, "eval/y.py", "y = 2\n")
        rules_only = {"A": [], "B": [DEFECT], "C": [], "verify": {"B1": CONFIRMED}}
        decision, reason, new = run_review(COMMIT, light, rules_only, log)
        ok &= expect(
            "main/ staged too: the full review runs, so B's confirmed defect denies (D-125)",
            decision == "deny" and "[B1]" in reason and "did not run" not in reason,
        )
        git(repo, "rm", "-q", "--cached", "main/x.py")
        light = review_diff.staged_diff_of(repo, False)
        decision, _, new = run_review(COMMIT, light, rules_only, log)
        ok &= expect(
            "eval/ only: finder A alone on sonnet, B and C never asked, pass (D-125)",
            decision == "allow"
            and "Agent-Review: pass " in new
            and new.endswith(' sonnet-light" -m "change"'),
        )
        git(repo, "add", "main/x.py")
        quoted = staged(repo, "notes/ä.md", "q\n")
        git(repo, "rm", "-q", "--cached", "main/x.py", "eval/y.py")
        quoted = review_diff.staged_diff_of(repo, False)
        ok &= expect(
            "a path git quotes (notes/ä.md) is read as code and gets the full review (D-125)",
            review_diff.has_quoted_path(quoted)
            and review_diff.touches_scope(quoted)
            and review_diff.tier(quoted)[0] == "full",
        )
        git(repo, "rm", "-q", "--cached", "notes/ä.md")
        git(repo, "add", "main/x.py", "eval/y.py")
        ok &= expect(
            "a plain path is not taken for a quoted one",
            not review_diff.has_quoted_path(review_diff.staged_diff_of(repo, False)),
        )
        git(repo, "rm", "-q", "--cached", "eval/y.py")
        question = dict(DEFECT, kind="question")
        decision, _, _ = run_review(COMMIT, code, stub_with(a=[question]), log)
        ok &= expect("a question is not verified and does not block", decision == "allow")
        lines = log.read_text(encoding="utf-8").splitlines()
        ok &= expect(
            "every review appends one log line",
            len(lines) == 7 and json.loads(lines[0])["diff_hash"] == hash12,
        )
    return ok


def drill_answered():
    print("3. a confirmed defect answered in the commit message passes as answered")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        repo = temp_repo(tmp)
        code = staged(repo, "main/x.py", "x = 1\n")
        log = Path(tmp) / "log.jsonl"
        stub = stub_with(a=[DEFECT], verify={"A1": CONFIRMED})
        answer = 'git commit -m "change\n\nreview: A1 — not a defect because the key is checked upstream"'
        decision, _, new = run_review(answer, code, stub, log)
        ok &= expect(
            "answered: allow with the answered trailer",
            decision == "allow" and "Agent-Review: answered " in new,
        )
        ok &= expect(
            "the log records which findings were answered",
            json.loads(log.read_text(encoding="utf-8").splitlines()[0])["answered"] == ["A1"],
        )
        other = 'git commit -m "review: A2 - not a defect because x"'
        ok &= expect(
            "an answer for another id does not count",
            run_review(other, code, stub, log)[0] == "deny",
        )
        vague = 'git commit -m "review: A1 - fine"'
        ok &= expect(
            "an answer without 'not a defect because' does not count",
            run_review(vague, code, stub, log)[0] == "deny",
        )
        cache = Path(tmp) / "kept.json"
        first = run_review(COMMIT, code, stub, log, cache)
        other_finding = dict(DEFECT, claim="a different bug")
        retry_stub = stub_with(a=[other_finding], verify={"A1": CONFIRMED})
        retry = run_review(answer, code, retry_stub, log, cache)
        ok &= expect(
            "the retry with an answer reuses the first review, so A1 is the finding it answers",
            first[0] == "deny"
            and retry[0] == "allow"
            and json.loads(log.read_text(encoding="utf-8").splitlines()[-1])["findings"][0]["claim"]
            == "wrong key",
        )
        ok &= expect(
            "the reused review is marked cached in the log",
            json.loads(log.read_text(encoding="utf-8").splitlines()[-1])["cached"] is True,
        )
    return ok


def drill_refusals():
    print("4. commands whose staged diff would not be what lands are refused")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        repo = temp_repo(tmp)
        code = staged(repo, "main/x.py", "x = 1\n")
        log = Path(tmp) / "log.jsonl"
        stub = stub_with()
        for command in (
            'git add x && git commit -m "m"',
            'git add main/x.py && git commit -m "m"',
            'git add . ; git commit -m "m"',
            'git commit -a -m "m"',
            'git commit -am "m"',
            'git commit --all -m "m"',
            'git commit -m "m" main/x.py',
            'git commit --amend -m "m"',
        ):
            ok &= expect(f"denied: {command}", run_review(command, code, stub, log)[0] == "deny")
        staging_notes = 'git add README.md && git commit -m "m"'
        ok &= expect(
            "git add of a notes file then commit is not refused for the staging",
            run_review(staging_notes, "", stub, log)[0] == "pass",
        )
        ok &= expect(
            "but with code already staged it is refused: the added file would break the stamp hash",
            run_review(staging_notes, code, stub, log)[0] == "deny",
        )
        ok &= expect(
            "the -a inside the message text is not the -a flag",
            run_review('git commit -m "use -a here"', code, stub, log)[0] == "allow",
        )
        ok &= expect(
            "--amend on a notes-only diff passes",
            run_review("git commit --amend -m m", "", stub, log)[0] == "pass",
        )
    return ok


def drill_failure_and_escape():
    print("5. a review that did not run denies; the skip and the child guard")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        repo = temp_repo(tmp)
        code = staged(repo, "main/x.py", "x = 1\n")
        log = Path(tmp) / "log.jsonl"
        garbage = {"A": "not a list", "B": [], "C": [], "verify": {}}
        decision, reason, _ = run_review(COMMIT, code, garbage, log)
        ok &= expect(
            "unparseable finder output: deny, and the reason says the review did not run",
            decision == "deny" and "did not run" in reason,
        )
        raised = []
        for helper in (
            review_diff.commit_args,
            review_diff.stages_code,
            review_diff.stages_any,
            lambda command: review_diff.with_trailer(command, "pass", "0" * 12, "opus"),
        ):
            try:
                helper("git status")
            except review_diff.ReviewError:
                raised.append(True)
        ok &= expect(
            "a helper called on a command with no git commit raises ReviewError, not AttributeError",
            len(raised) == 4,
        )
        for command in (
            'git commit -m "m"',
            'cd repo && git commit -m "m"',
            'PROJECT_REVIEW_SKIP=1 git commit -m "m"',
            'git -C repo commit -m "m"',
            '(git commit -m "m")',
            "time git commit -m m",
            "{ git commit -m m; }",
            "env A=1 git commit -m m",
            "if x; then git commit -m m; fi",
            'bash -c "git commit -m m"',
            "! git commit -m m",
        ):
            ok &= expect(
                f"a wrapped commit is still found, so it cannot skip the review: {command}",
                review_diff.commit_match(command) is not None,
            )
        decision, _, _ = run_review(COMMIT, code, stub_with(a=[DEFECT]), log)
        ok &= expect("a defect with no verifier verdict: deny", decision == "deny")
        decision, _, _ = run_review(COMMIT, code, {"A": [], "B": []}, log)
        ok &= expect("a missing role in the stub: deny", decision == "deny")
        stub = stub_with(a=[DEFECT], verify={"A1": CONFIRMED})
        decision, _, new = run_review("PROJECT_REVIEW_SKIP=1 " + COMMIT, code, stub, log)
        ok &= expect(
            "PROJECT_REVIEW_SKIP=1: allow with the skipped trailer and - for the model",
            decision == "allow" and " skipped " in new and ' -"' in new,
        )

        payload = json.dumps(
            {
                "tool_name": "Bash",
                "cwd": str(repo),
                "tool_input": {"command": COMMIT, "description": "d"},
            }
        )
        env = dict(os.environ)
        env["PROJECT_REVIEW_CHILD"] = "1"
        done = subprocess.run(
            [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True, env=env
        )
        ok &= expect(
            "PROJECT_REVIEW_CHILD=1: exit 0, no output, nothing reviewed",
            done.returncode == 0 and done.stdout == "",
        )
        env.pop("PROJECT_REVIEW_CHILD")
        stub_path = Path(tmp) / "stub.json"
        stub_path.write_text(json.dumps(stub_with()), encoding="utf-8")
        env["PROJECT_REVIEW_STUB"] = str(stub_path)
        env["PROJECT_REVIEW_LOG"] = str(log)
        done = subprocess.run(
            [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True, env=env
        )
        out = json.loads(done.stdout)["hookSpecificOutput"]
        ok &= expect(
            "as Claude Code calls it: allow with updatedInput",
            out["permissionDecision"] == "allow"
            and "Agent-Review: pass " in out["updatedInput"]["command"],
        )
        ok &= expect(
            "updatedInput keeps the other tool_input fields",
            out["updatedInput"]["description"] == "d",
        )
        status = json.dumps({"tool_input": {"command": "git status"}})
        done = subprocess.run(
            [sys.executable, str(HOOK)], input=status, capture_output=True, text=True, env=env
        )
        ok &= expect(
            "not a commit: exit 0 and no output", done.returncode == 0 and done.stdout == ""
        )
    return ok


if __name__ == "__main__":
    results = [
        drill_passes(),
        drill_verdicts(),
        drill_answered(),
        drill_refusals(),
        drill_failure_and_escape(),
    ]
    sys.exit(0 if all(results) else 1)
