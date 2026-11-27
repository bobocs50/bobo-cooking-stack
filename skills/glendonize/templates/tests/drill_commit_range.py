"""A pushed range is judged commit by commit, not by its last subject.

    python tests/drill_commit_range.py

CI's "Every src/ change carries a drill" step looked at the whole push for any tests/
change and read only the last subject, so a src/ commit with no drill of its own passed
when a later commit in the push touched tests/ or said `no drill:`. tests/commit_range.py
now applies the rule per commit; this drill builds a throwaway repo and checks it. Offline,
free.
"""

import re
import subprocess
import tempfile
from pathlib import Path

from _drill import expect
from commit_range import (
    commits_between,
    drill_renames,
    spine_without_drill,
    resolve_base,
    unannounced_drops,
)

ZEROS = "0" * 40


def run(repo, *args):
    result = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
        + list(args),
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def land(repo, subject, files):
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    run(repo, "add", *files.keys())
    run(repo, "commit", "-q", "--no-verify", "-m", subject)
    return run(repo, "rev-parse", "HEAD")


def count(text):
    return len(re.findall(r"expect\(", text))


def main():
    print("per-commit drill rule over a pushed range")
    passed = True
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        run(repo, "init", "-q")
        base = land(repo, "base", {"README.txt": "x\n"})
        first = land(
            repo, "spine with its drill", {"src/a.py": "a=1\n", "tests/drill_a.py": "expect(1)\n"}
        )
        second = land(repo, "spine alone", {"src/b.py": "b=1\n"})
        third = land(repo, "only tests", {"tests/drill_c.py": "expect(1)\n"})
        head = third

        found = commits_between(base, head, cwd=repo)
        passed &= expect(
            "the range holds the three commits, oldest first", found == [first, second, third]
        )

        bad = spine_without_drill(found, cwd=repo)
        passed &= expect(
            "only the middle commit (src/b.py, no tests/, no marker) is flagged",
            len(bad) == 1 and bad[0].startswith(second[:10]),
        )

        passed &= expect(
            "a clean range gives no finding", spine_without_drill([first, third], cwd=repo) == []
        )

        marked = land(repo, "no drill: a comment-only spine change", {"src/c.py": "c=1\n"})
        passed &= expect(
            "a commit saying no drill: in its own subject is not flagged",
            spine_without_drill([marked], cwd=repo) == [],
        )
        passed &= expect(
            "the marker of a later commit does not excuse an earlier one",
            len(spine_without_drill([second, marked], cwd=repo)) == 1,
        )

        passed &= expect(
            "an all-zero base falls back to HEAD~1",
            resolve_base(ZEROS, "HEAD", cwd=repo) == "HEAD~1",
        )
        passed &= expect(
            "an empty base falls back to HEAD~1", resolve_base("", "HEAD", cwd=repo) == "HEAD~1"
        )
        passed &= expect(
            "an unknown base falls back to HEAD~1",
            resolve_base("f" * 40, "HEAD", cwd=repo) == "HEAD~1",
        )
        passed &= expect("a known base is kept", resolve_base(base, "HEAD", cwd=repo) == base)

        dropped = land(repo, "trim drill", {"tests/drill_a.py": "# nothing left\n"})
        passed &= expect(
            "a commit that removes an expect( call without drop drill: is flagged",
            len(unannounced_drops([dropped], count, cwd=repo)) == 1,
        )
        said = land(
            repo, "drop drill: a_check is obsolete", {"tests/drill_c.py": "# nothing left\n"}
        )
        passed &= expect(
            "drop drill: in the commit's own subject allows the removal",
            unannounced_drops([said], count, cwd=repo) == [],
        )
        passed &= expect(
            "the same removal is still flagged when a later subject says drop drill:",
            len(unannounced_drops([dropped, said], count, cwd=repo)) == 1,
        )

        reads = []

        def counting(text):
            reads.append(text)
            return count(text)

        untouched = land(repo, "a note only", {"README.txt": "y\n"})
        unannounced_drops([untouched], counting, cwd=repo)
        passed &= expect("a commit that leaves every drill alone reads none of them", reads == [])
        unannounced_drops([dropped], counting, cwd=repo)
        passed &= expect(
            "a commit that trims one drill reads that drill at both ends and nothing else",
            len(reads) == 2,
        )
        run(repo, "rm", "-q", "tests/drill_a.py")
        run(repo, "commit", "-q", "--no-verify", "-m", "remove a drill")
        removed = run(repo, "rev-parse", "HEAD")
        found = unannounced_drops([removed], count, cwd=repo)
        passed &= expect(
            "a commit that deletes a drill without drop drill: is flagged as gone",
            len(found) == 1 and found[0].endswith("-> gone"),
        )

        ten = "".join("expect(" + str(n) + ")\n" for n in range(10))
        land(repo, "a drill with ten checks", {"tests/drill_e.py": ten})
        run(repo, "mv", "tests/drill_e.py", "tests/drill_f.py")
        run(repo, "commit", "-q", "--no-verify", "-m", "move a drill")
        moved = run(repo, "rev-parse", "HEAD")
        passed &= expect(
            "a commit that only renames a drill loses nothing",
            unannounced_drops([moved], count, cwd=repo) == [],
        )
        run(repo, "mv", "tests/drill_f.py", "tests/drill_g.py")
        (repo / "tests/drill_g.py").write_text(ten.replace("expect(9)\n", ""), encoding="utf-8")
        run(repo, "add", "tests/drill_g.py")
        run(repo, "commit", "-q", "--no-verify", "-m", "move and trim a drill")
        trimmed = run(repo, "rev-parse", "HEAD")
        found = unannounced_drops([trimmed], count, cwd=repo)
        passed &= expect(
            "a commit that renames a drill and drops a check is flagged under both names",
            len(found) == 1 and "drill_f.py -> tests/drill_g.py: 10 -> 9" in found[0],
        )

        (repo / "tests/tdd").mkdir()
        run(repo, "mv", "tests/drill_g.py", "tests/tdd/tdd_g.py")
        run(repo, "commit", "-q", "--no-verify", "-m", "park a drill")
        parked = run(repo, "rev-parse", "HEAD")
        found = unannounced_drops([parked], count, cwd=repo)
        passed &= expect(
            "a commit that moves a drill out of the gate is flagged as gone",
            len(found) == 1 and "tests/tdd/tdd_g.py: 9 -> gone" in found[0],
        )
        passed &= expect(
            "a move between two drill names is followed over a range",
            drill_renames(moved + "^", moved, cwd=repo) == {"tests/drill_e.py": "tests/drill_f.py"},
        )
        passed &= expect(
            "a move out of the gate is not followed over a range, so check 9 finds it gone",
            drill_renames(parked + "^", parked, cwd=repo) == {},
        )

    print("")
    print("ALL PASSED" if passed else "SOME FAILED")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
