"""Drill for .claude/hooks/mutation_check.py, the revert-and-rerun check of the commit
review: a drill that fails once the code change is undone is "pinned", one that
stays green is "unpinned", a no drill: subject is "no_drill", a broken apply is
"skipped", and the temp worktree is gone afterwards. The staged changes come from a
throwaway git repo in a temp folder, never from this one; nothing is spent.

    python tests/drill_mutation_check.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

import mutation_check
from _drill import expect as _expect

RESULTS = []


def expect(label, condition):
    RESULTS.append(_expect(label, condition))


DRILL_PINS = """import sys
sys.path.insert(0, "src")
import calc
sys.exit(0 if calc.double(2) == 4 else 1)
"""
DRILL_RED = """import sys
sys.exit(1)
"""
DRILL_LAX = """import sys
sys.path.insert(0, "src")
import calc
sys.exit(0 if callable(calc.double) else 1)
"""


def git(folder, *args):
    return subprocess.run(
        ["git", *args], cwd=folder, check=True, capture_output=True, text=True, encoding="utf-8"
    )


def write(folder, name, text):
    path = Path(folder) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def temp_repo(tmp, name):
    """A committed repo whose double() is still wrong; the staged change fixes it."""
    repo = Path(tmp) / name
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "drill@example.invalid")
    git(repo, "config", "user.name", "drill")
    write(repo, "src/calc.py", "def double(x):\n    return x + 1\n")
    write(repo, "tests/drill_calc.py", DRILL_LAX)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "base")
    return repo


def stage_fix(repo, drill_text):
    write(repo, "src/calc.py", "def double(x):\n    return x * 2\n")
    write(repo, "tests/drill_calc.py", drill_text)
    git(repo, "add", ".")
    return git(repo, "diff", "--cached").stdout


def worktrees(repo):
    return git(repo, "worktree", "list", "--porcelain").stdout.count("worktree ")


with tempfile.TemporaryDirectory() as tmp:
    repo = temp_repo(tmp, "pins")
    diff = stage_fix(repo, DRILL_PINS)
    got = mutation_check.check(str(repo), diff, "fix double", 120)
    expect("a drill that fails with the fix undone is pinned", got["status"] == "pinned")
    expect(
        "the report names the drill and that it passed reverted = False",
        got["drills"]
        == [
            {
                "name": "drill_calc.py",
                "reverted_ok": False,
                "with_change_ok": True,
                "seconds": got["drills"][0]["seconds"],
            }
        ],
    )
    expect("the worktree is removed afterwards", worktrees(repo) == 1)
    expect(
        "the repo's own index and files are untouched",
        git(repo, "status", "--porcelain").stdout.count("\n") == 2,
    )

    repo = temp_repo(tmp, "lax")
    diff = stage_fix(repo, DRILL_LAX + "\n# edited\n")
    got = mutation_check.check(str(repo), diff, "fix double", 120)
    expect("a drill that still passes with the fix undone is unpinned", got["status"] == "unpinned")
    expect(
        "the unpinned drill is listed as green reverted", got["drills"][0]["reverted_ok"] is True
    )
    expect("the worktree is removed after unpinned too", worktrees(repo) == 1)

    expect(
        "drills run with PYTHONDONTWRITEBYTECODE=1, so no stale .pyc carries the changed"
        " code into the reverted run",
        mutation_check.drill_env(str(repo))["PYTHONDONTWRITEBYTECODE"] == "1",
    )

    repo = temp_repo(tmp, "brief")
    write(repo, "src/brief.md", "changed\n")
    git(repo, "add", ".")
    got = mutation_check.check(str(repo), git(repo, "diff", "--cached").stdout, "brief", 120)
    expect(
        "a trunk change to a non-Python file with no drill naming it is skipped, not unpinned",
        got["status"] == "skipped",
    )

    repo = temp_repo(tmp, "brief_drill")
    write(repo, "src/brief.md", "changed\n")
    brief_drill = (
        "import sys\nfrom pathlib import Path\n"
        "sys.exit(0 if 'changed' in (Path(__file__).parent.parent / 'src' / 'brief.md')"
        ".read_text() else 1)\n"
    )
    write(repo, "tests/drill_brief.py", brief_drill)
    git(repo, "add", ".")
    got = mutation_check.check(str(repo), git(repo, "diff", "--cached").stdout, "brief", 120)
    expect(
        "a diff with a trunk file but no .py code file is skipped, even with a drill reading it",
        got["status"] == "skipped" and "No .py code file" in got["detail"],
    )

    repo = temp_repo(tmp, "docs_only")
    write(repo, "ref/x.md", "x\n")
    write(repo, "tests/drill_calc.py", DRILL_LAX + "\n# edited\n")
    git(repo, "add", ".")
    got = mutation_check.check(str(repo), git(repo, "diff", "--cached").stdout, "docs", 120)
    expect("a diff with no code file is skipped: nothing to revert", got["status"] == "skipped")

    repo = temp_repo(tmp, "note")
    write(repo, "ref/ids.md", "D-9\n")
    note_drill = (
        "import sys\nfrom pathlib import Path\n"
        "sys.exit(0 if 'D-9' in (Path(__file__).parent.parent / 'ref' / 'ids.md')"
        ".read_text() else 1)\n"
    )
    diff = stage_fix(repo, note_drill)
    got = mutation_check.check(str(repo), diff, "fix double", 120)
    expect(
        "a note staged with the code stays on the revert, so a drill reading only the note"
        " does not count as pinning the code",
        got["status"] == "unpinned",
    )

    got = mutation_check.check(str(repo), diff, "fix double\n\nbody", 120)
    expect("a plain subject runs the check, not the no_drill path", got["status"] != "no_drill")
    got = mutation_check.check(str(repo), diff, "No drill: pure refactor\n", 120)
    expect(
        "a no drill: subject is no_drill and runs nothing",
        got["status"] == "no_drill" and got["drills"] == [],
    )

    repo = temp_repo(tmp, "code-only")
    write(repo, "src/calc.py", "def double(x):\n    return x * 2\n")
    git(repo, "add", ".")
    code_diff = git(repo, "diff", "--cached").stdout
    got = mutation_check.check(str(repo), code_diff, "fix double", 120)
    expect(
        "no drill in the diff: a drill naming the module is found by its stem",
        [d["name"] for d in got["drills"]] == ["drill_calc.py"],
    )

    write(repo, "src/other.py", "x = 1\n")
    git(repo, "add", ".")
    other = "diff --git a/src/zzz.py b/src/zzz.py\nnew file mode 100644\n--- /dev/null\n+++ b/src/zzz.py\n@@ -0,0 +1 @@\n+x = 1\n"
    got = mutation_check.check(str(repo), other, "add zzz", 120)
    expect(
        "no drill names the change: unpinned with that detail",
        got["status"] == "unpinned"
        and got["files"]
        == [
            {"path": "src/zzz.py", "status": "no_drill_named", "drills": [], "red_with_change": []}
        ]
        and "src/zzz.py" in got["detail"],
    )

    broken = "diff --git a/src/calc.py b/src/calc.py\n--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,1 +1,1 @@\n-nothing like this\n+x\n"
    got = mutation_check.check(str(repo), broken, "x", 120)
    expect(
        "a code diff that does not apply is an error at the apply, not skipped and not raised",
        got["status"] == "error"
        and got["detail"].startswith("git apply of the staged diff failed"),
    )
    expect("the worktree is removed after the apply error", worktrees(repo) == 1)

    got = mutation_check.check(str(Path(tmp) / "not-a-repo"), diff, "x", 120)
    expect("a folder that is not a repo is an error, not raised", got["status"] == "error")

    got = mutation_check.check(str(repo), diff, "x", 0)
    expect(
        "a spent time budget is an error, says it timed out and marks the file timeout",
        got["status"] == "error"
        and "Timed out" in got["detail"]
        and [f["status"] for f in got["files"]] == ["timeout"],
    )

    repo = temp_repo(tmp, "red-both")
    diff = stage_fix(repo, DRILL_RED)
    got = mutation_check.check(str(repo), diff, "fix double", 120)
    expect(
        "a drill red with the change is red_with_change and does not pin the file",
        got["status"] == "red_with_change"
        and got["files"][0]["status"] == "red_with_change"
        and got["files"][0]["red_with_change"] == ["drill_calc.py"],
    )
    expect(
        "the red drill is listed with with_change_ok False",
        got["drills"][0]["name"] == "drill_calc.py" and got["drills"][0]["with_change_ok"] is False,
    )
    expect("the worktree is removed after the baseline skip", worktrees(repo) == 1)

    repo = temp_repo(tmp, "mixed-red")
    diff = stage_fix(repo, DRILL_PINS)
    write(repo, "tests/drill_broken.py", DRILL_RED)
    git(repo, "add", ".")
    diff = git(repo, "diff", "--cached").stdout
    got = mutation_check.check(str(repo), diff, "fix double", 120)
    by_name = {}
    for entry in got["drills"]:
        by_name[entry["name"]] = entry
    expect(
        "a drill red with the change is left out of the verdict, the other still decides: pinned",
        got["status"] == "pinned"
        and by_name["drill_broken.py"]["with_change_ok"] is False
        and by_name["drill_calc.py"]["reverted_ok"] is False,
    )

    repo = temp_repo(tmp, "mixed-diff")
    write(repo, "src/calc.py", "def double(x):\n    return x * 2\n")
    write(repo, "tests/drill_unrelated.py", "import sys\nsys.exit(0)\n")
    git(repo, "add", ".")
    mixed = git(repo, "diff", "--cached").stdout
    got = mutation_check.check(str(repo), mixed, "fix double", 120)
    expect(
        "a diff with a drill and a module: the drill in the diff and the drill naming the module both run",
        sorted(d["name"] for d in got["drills"]) == ["drill_calc.py", "drill_unrelated.py"],
    )

    expect(
        "a subject that carries no drill: and a reason is no_drill",
        mutation_check.no_drill_subject("tidy a docstring - no drill: pure refactor")
        and mutation_check.no_drill_subject("no drill: pure refactor"),
    )
    expect(
        "a subject that only mentions the phrase (backticks, quotes, no reason) is not no_drill",
        not mutation_check.no_drill_subject("explain the `no drill: reason` convention")
        and not mutation_check.no_drill_subject('say "no drill: x" in the subject')
        and not mutation_check.no_drill_subject("the phrase no drill:")
        and not mutation_check.no_drill_subject("add a drill"),
    )
    got = mutation_check.check(str(repo), mixed, "document the `no drill: reason` rule", 120)
    expect("a mention-only subject still runs the check", got["status"] != "no_drill")

    repo = temp_repo(tmp, "two-files")
    write(repo, "src/triple.py", "def triple(x):\n    return x + 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "triple")
    diff = stage_fix(repo, DRILL_PINS)
    write(repo, "src/triple.py", "def triple(x):\n    return x * 3\n")
    git(repo, "add", ".")
    diff = git(repo, "diff", "--cached").stdout
    got = mutation_check.check(str(repo), diff, "fix both", 120)
    by_path = {}
    for entry in got["files"]:
        by_path[entry["path"]] = entry["status"]
    expect(
        "two changed files, only one tested: the untested one is unpinned and named,"
        " the tested one pinned",
        got["status"] == "unpinned"
        and by_path == {"src/calc.py": "pinned", "src/triple.py": "unpinned"}
        and "src/triple.py" in got["detail"]
        and "src/calc.py" not in got["detail"],
    )

    write(
        repo,
        "tests/drill_triple.py",
        "import sys\nsys.path.insert(0, 'src')\nimport triple\n"
        "sys.exit(0 if triple.triple(2) == 6 else 1)\n",
    )
    git(repo, "add", ".")
    diff = git(repo, "diff", "--cached").stdout
    got = mutation_check.check(str(repo), diff, "fix both", 120)
    by_path = {}
    for entry in got["files"]:
        by_path[entry["path"]] = entry["status"]
    expect(
        "two changed files, both tested: pinned, each file by its own drill",
        got["status"] == "pinned"
        and by_path == {"src/calc.py": "pinned", "src/triple.py": "pinned"},
    )
    expect("the worktree is removed after the per-file runs", worktrees(repo) == 1)

    side = temp_repo(tmp, "side-by-side")
    write(side, "src/triple.py", "def triple(x):\n    return x + 1\n")
    git(side, "add", ".")
    git(side, "commit", "-q", "-m", "triple")
    log = Path(tmp) / "cwd.log"
    logging_drill = (
        "import os, sys\nsys.path.insert(0, 'src')\n"
        f"with open({str(log)!r}, 'a') as out:\n    out.write(os.getcwd() + chr(10))\n"
    )
    stage_fix(side, logging_drill + "import calc\nsys.exit(0 if calc.double(2) == 4 else 1)\n")
    write(side, "src/triple.py", "def triple(x):\n    return x * 3\n")
    write(
        side,
        "tests/drill_triple.py",
        logging_drill + "import triple\nsys.exit(0 if triple.triple(2) == 6 else 1)\n",
    )
    git(side, "add", ".")
    os.environ["PROJECT_MUTATION_WORKERS"] = "2"
    got = mutation_check.check(str(side), git(side, "diff", "--cached").stdout, "fix both", 120)
    del os.environ["PROJECT_MUTATION_WORKERS"]
    trees = set(log.read_text(encoding="utf-8").split())
    print("  worktrees the drills ran in: " + str(len(trees)))
    expect(
        "with 2 workers the two reverted files run in two worktrees, both still pinned, and"
        " every worktree is removed afterwards",
        got["status"] == "pinned" and len(trees) == 2 and worktrees(side) == 1,
    )

    alone = temp_repo(tmp, "alone")
    write(alone, "src/triple.py", "def triple(x):\n    return x + 1\n")
    git(alone, "add", ".")
    git(alone, "commit", "-q", "-m", "triple")
    spans = Path(tmp) / "spans.log"

    def timed_drill(name, check):
        return (
            "import sys, time\nsys.path.insert(0, 'src')\nbegan = time.time()\ntime.sleep(2)\n"
            + check
            + f"\nwith open({str(spans)!r}, 'a') as out:\n"
            + f"    out.write({name!r} + ' ' + str(began) + ' ' + str(time.time()) + chr(10))\n"
            + "sys.exit(0 if ok else 1)\n"
        )

    stage_fix(alone, DRILL_LAX)
    write(alone, "src/triple.py", "def triple(x):\n    return x * 3\n")
    write(
        alone, "tests/drill_alone.py", timed_drill("alone", "import calc\nok = calc.double(2) == 4")
    )
    write(
        alone,
        "tests/drill_z_triple.py",
        timed_drill("other", "import triple\nok = triple.triple(2) == 6"),
    )
    git(alone, "add", ".")
    os.environ["PROJECT_MUTATION_WORKERS"] = "2"
    mutation_check.ALONE = ("drill_alone.py",)
    try:
        got = mutation_check.check(
            str(alone), git(alone, "diff", "--cached").stdout, "fix both", 120
        )
    finally:
        mutation_check.ALONE = ()
        del os.environ["PROJECT_MUTATION_WORKERS"]
    runs = []
    for line in spans.read_text(encoding="utf-8").split("\n"):
        if line:
            name, began, ended = line.split()
            runs.append((name, float(began), float(ended)))
    overlaps = 0
    for index in range(len(runs)):
        name, began, ended = runs[index]
        if name != "alone":
            continue
        for other in range(len(runs)):
            other_name, other_began, other_ended = runs[other]
            if other != index and began < other_ended and other_began < ended:
                overlaps += 1
    print("  drill runs: " + str(len(runs)) + ", ALONE runs overlapping another: " + str(overlaps))
    expect(
        "a drill of ALONE never runs beside another drill, with the change or reverted, and"
        " both files stay pinned",
        got["status"] == "pinned" and overlaps == 0 and len(runs) >= 4,
    )

    own = os.environ.pop("PROJECT_MUTATION_WORKERS", None)
    default = mutation_check.worker_count()
    os.environ["PROJECT_MUTATION_WORKERS"] = "7"
    overridden = mutation_check.worker_count()
    del os.environ["PROJECT_MUTATION_WORKERS"]
    if own is not None:
        os.environ["PROJECT_MUTATION_WORKERS"] = own
    expect(
        "PROJECT_MUTATION_WORKERS sets the count; without it min(4, CPU count) run at once",
        overridden == 7 and default == min(4, os.cpu_count() or 1),
    )

    write(repo, "tests/drill_calc_slow.py", "import time\n" + DRILL_PINS)
    git(repo, "add", ".")
    diff = git(repo, "diff", "--cached").stdout
    got = mutation_check.check(str(repo), diff, "fix both", 120)
    reverted = {}
    for drill in got["drills"]:
        reverted[drill["name"]] = drill["reverted_ok"]
    expect(
        "a file's reverted run stops at its first red drill: calc.py is pinned by drill_calc.py,"
        " so drill_calc_slow.py, which would also go red for it, runs reverted only for"
        " triple.py and stays green",
        got["status"] == "pinned"
        and reverted["drill_calc.py"] is False
        and reverted["drill_calc_slow.py"] is True,
    )

    repo = temp_repo(tmp, "tail-append")
    old_text = "first\r kept\nlast line — and ·\n"
    write(repo, "notes.md", old_text)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "notes")
    write(repo, "notes.md", old_text + "new — line\n" * 3)
    git(repo, "add", ".")
    raw = subprocess.run(["git", "diff", "--cached"], cwd=repo, check=True, capture_output=True)
    tail_diff = raw.stdout.decode("utf-8")
    git(repo, "reset", "-q", "--hard", "HEAD")
    expect(
        "a patch with a lone CR in its context and non-ASCII lines appended at the end of a file"
        " applies on a fresh checkout: the patch goes to git apply as bytes, not through"
        " Windows text mode",
        mutation_check.apply_patch(str(repo), tail_diff, "test") is None,
    )

    drill_sees_commit = (
        "import subprocess, sys\nsys.path.insert(0, 'src')\nimport calc\n"
        "tracked = subprocess.run(['git', 'ls-files'], capture_output=True, text=True)"
        ".stdout.split()\n"
        "subject = subprocess.run(['git', 'log', '-1', '--format=%s'], capture_output=True,"
        " text=True).stdout.strip()\n"
        "ok = 'tests/drill_added.py' in tracked and subject == 'add drill'"
        " and calc.double(2) == 4\nsys.exit(0 if ok else 1)\n"
    )
    fixed_calc = "def double(x):\n    return x * 2\n"
    repo = temp_repo(tmp, "commit-seen")
    write(repo, "src/calc.py", fixed_calc)
    write(repo, "tests/drill_added.py", drill_sees_commit)
    git(repo, "add", ".")
    got = mutation_check.check(str(repo), git(repo, "diff", "--cached").stdout, "add drill", 120)
    expect(
        "the mutation worktree holds the commit under test: a drill added by the diff is tracked"
        " and the subject is the commit's, so a drill that asks git is pinned",
        got["status"] == "pinned",
    )
    repo = temp_repo(tmp, "worktree-message")
    write(repo, "src/calc.py", fixed_calc)
    write(repo, "tests/drill_added.py", drill_sees_commit)
    git(repo, "add", ".")
    both = git(repo, "diff", "--cached").stdout
    got = mutation_check.check(str(repo), both, "", 120, worktree_message="add drill\n\nbody")
    expect(
        "the worktree commit takes worktree_message while commit_message stays empty: the"
        " subject the drill reads is the real one",
        got["status"] == "pinned",
    )
    got = mutation_check.check(
        str(repo), both, "no drill: notes only", 120, worktree_message="add drill"
    )
    expect(
        "a no drill: commit_message still returns no_drill whatever worktree_message says",
        got["status"] == "no_drill",
    )

    tree = Path(tmp) / "select"
    write(tree, "src/store.py", "def put():\n    return 1\n")
    write(tree, "src/api.py", "def app():\n    from store import put\n    return put()\n")
    write(tree, "tests/drill_imports_api.py", "import api\n")
    write(tree, "tests/drill_imports_store.py", "import store\n")
    write(tree, "tests/drill_path.py", "open('src/store.py')\n")
    write(tree, "tests/drill_prose.py", "print('the store is empty')\n")
    write(tree, "tests/drill_note.py", "print('see notes_stem')\n")
    write(tree, "tests/drill_quoted.py", "fixture = 'import api' + chr(10)\n")
    got = mutation_check.drills_naming(["store"], str(tree / "tests"))
    expect(
        "a drill importing a module that imports the stem is selected, a lazy import inside a"
        " function included",
        "drill_imports_api.py" in got,
    )
    expect(
        "a drill importing the stem or naming its file is selected",
        "drill_imports_store.py" in got and "drill_path.py" in got,
    )
    expect(
        "a drill whose prose only says the word of the stem is not selected",
        "drill_prose.py" not in got and "drill_quoted.py" not in got,
    )
    pkg = Path(tmp) / "packages"
    write(pkg, "src/pipeline/grounding.py", "def check():\n    return 1\n")
    write(pkg, "src/pipeline/flags.py", "from pipeline.grounding import check\n")
    write(pkg, "tests/drill_named.py", "from pipeline import grounding\n")
    write(pkg, "tests/drill_dotted.py", "from pipeline.grounding import check\n")
    write(pkg, "tests/drill_aliased.py", "import pipeline.grounding as g\n")
    write(pkg, "tests/drill_listed.py", "from pipeline import (\n    grounding,\n)\n")
    write(pkg, "tests/drill_importer.py", "from pipeline import flags\n")
    write(pkg, "tests/drill_word.py", "print('grounding is checked')\n")
    got = mutation_check.drills_naming(["grounding"], str(pkg / "tests"))
    print("  drills selected for pipeline/grounding: " + str(got))
    expect(
        "a package import of the stem selects the drill: from pkg import x, from pkg.x import,"
        " import pkg.x, a parenthesised list, and an importer's package import",
        got
        == [
            "drill_aliased.py",
            "drill_dotted.py",
            "drill_importer.py",
            "drill_listed.py",
            "drill_named.py",
        ],
    )
    expect(
        "a stem that is no module of the spine dir still matches as a word",
        mutation_check.drills_naming(["notes_stem"], str(tree / "tests")) == ["drill_note.py"],
    )

    repo = temp_repo(tmp, "brief-md")
    write(repo, ".claude/orchestration/brief.md", "brief\n")
    git(repo, "add", ".")
    got = mutation_check.check(str(repo), git(repo, "diff", "--cached").stdout, "brief", 120)
    expect(
        "a brief-only diff is skipped with the reason, not an error",
        got["status"] == "skipped" and "No .py code file" in got["detail"],
    )

sys.exit(0 if all(RESULTS) else 1)
