"""Drill for the push pipeline .claude/hooks/ship.py: what lands, what is dropped, what
asks the user, and that the fixer's src/ edits are undone. Free and offline: every claude child
is replaced by PROJECT_SHIP_STUB, gh by PROJECT_SHIP_GH_STUB, and origin is a bare repo in a temp
folder, so nothing reaches GitHub or a model.

    python tests/drill_ship.py

Each case builds its own clone of one seeded bare origin and runs ship.py on it as a subprocess;
the cases run in parallel to stay under 10 s.

"""

import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHIP = REPO_ROOT / ".claude" / "hooks" / "ship.py"
sys.path.insert(0, str(SHIP.parent))

import ship
from _drill import expect

GREEN = [{"status": "completed", "conclusion": "success", "databaseId": 2}]
RED = [{"status": "completed", "conclusion": "failure", "databaseId": 1}]
BROKEN = [{"status": "completed", "conclusion": "startup_failure", "databaseId": 1}]
LEAF = "tools/tool.py"
TRUNK = "src/table.json"
HOOK = ".claude/hooks/tool.py"
SEED = {
    LEAF: "VALUE = 1\n",
    TRUNK: "{}\n",
    "src/rule.py": "# a note\nLIMIT = 1\n",
    "tests/drill_tool.py": (
        "import os, sys\n"
        "if os.path.exists('tools/gate.txt') and open('tools/gate.txt').read() == 'red':\n"
        "    print('FAIL  drill_tool.py'); sys.exit(1)\n"
        "print('tool ok')\n"
    ),
    "tests/drill_other.py": 'print("ok")\n',
    "tests/drill_ruff.py": 'print("ok")\n',
    "tests/drill_pyright.py": 'print("ok")\n',
    "tools/long.txt": "a\nb\nc\nd\ne\nf\ng\n",
    "tests/run_drills.py": (
        "import os, sys\n"
        "print('full suite ran')\n"
        "if os.path.exists('tools/full.txt') and open('tools/full.txt').read() == 'red':\n"
        "    print('FAIL  drill_tool.py'); sys.exit(1)\n"
        "if os.path.exists('tools/full.txt') and open('tools/full.txt').read() == 'noisy':\n"
        "    print('FAIL  case q9-ci: got 1, wanted 2'); print('x' * 9000)\n"
        "    print('FAILED: drill_tool.py'); sys.exit(1)\n"
    ),
    "tests/commit_range.py": (
        "import os, sys\n"
        "if os.path.exists('tools/range.txt') and open('tools/range.txt').read() == 'red':\n"
        "    print('a src/ commit without a drill'); sys.exit(1)\n"
    ),
}
HOLDER = (
    "import sys, time, pathlib\n"
    "folder, wanted = pathlib.Path(sys.argv[1]), sys.argv[2]\n"
    "end = time.time() + 600\n"
    "while time.time() < end:\n"
    "    for path in folder.glob('*.json'):\n"
    "        try:\n"
    "            if wanted in path.read_text(encoding='utf-8'):\n"
    "                if len(sys.argv) > 4:\n"
    "                    pathlib.Path(sys.argv[3]).write_text(sys.argv[4])\n"
    "                sys.exit(0)\n"
    "        except OSError:\n"
    "            pass\n"
    "    time.sleep(0.1)\n"
)
MOVER = (
    "import os, pathlib, subprocess\n"
    "origin = os.environ['PROJECT_SHIP_REMOTE']\n"
    "left = pathlib.Path(origin).parent / 'moves.txt'\n"
    "count = int(left.read_text()) if left.exists() else 0\n"
    "if count > 0:\n"
    "    left.write_text(str(count - 1))\n"
    "    env = dict(os.environ, GIT_AUTHOR_NAME='u', GIT_AUTHOR_EMAIL='u@example.invalid',\n"
    "               GIT_COMMITTER_NAME='u', GIT_COMMITTER_EMAIL='u@example.invalid')\n"
    "    def g(*args):\n"
    "        return subprocess.run(['git', '--git-dir', origin, *args], env=env, check=True,\n"
    "                              capture_output=True, text=True).stdout.strip()\n"
    "    tree = g('rev-parse', 'main^{tree}')\n"
    "    edit = pathlib.Path(origin).parent / 'move_edit.txt'\n"
    "    if edit.exists():\n"
    "        env['GIT_INDEX_FILE'] = str(edit) + '.index'\n"
    "        g('read-tree', 'main')\n"
    "        blob = g('hash-object', '-w', str(edit))\n"
    "        g('update-index', '--cacheinfo', '100644,' + blob + ',tools/long.txt')\n"
    "        tree = g('write-tree')\n"
    "    new = g('commit-tree', tree, '-p', 'main', '-m', 'upstream move ' + str(count))\n"
    "    g('update-ref', 'refs/heads/main', new)\n"
)
NOISY = (
    "import sys\nprint('FAIL  case q9-marker: got 1, wanted 2')\nprint('x' * 9000)\nsys.exit(1)\n"
)
PRE_RECEIVE = chr(10).join(
    [
        "#!/bin/sh",
        "n=$(cat rejects 2>/dev/null || echo 0)",
        'if [ "$n" -gt 0 ]; then',
        "  echo $((n - 1)) > rejects",
        "  echo 'remote: fatal error in commit_refs_rules' >&2",
        "  exit 1",
        "fi",
        "",
    ]
)
REJECTS = {"push_flaky": 2, "push_down": 3}
UI_COMPARE_OK = (
    "import pathlib, sys\n"
    "pathlib.Path(__file__).with_name('args.txt').write_text(' '.join(sys.argv[1:]))\n"
    "print('noise')\n"
    "print('UI_COMPARE C:/out/compare.html')\n"
)
UI_COMPARES = {
    "ui_ok": UI_COMPARE_OK,
    "ui_leaf": UI_COMPARE_OK,
    "ui_fail": "import sys\nprint('UI_COMPARE FAILED no config')\nsys.exit(1)\n",
    "ui_slow": "import time\ntime.sleep(60)\n",
}
FAILED_AT_PUSH = {}
FRONT_CHECK = (
    "import os, sys; "
    "sys.exit(1 if os.path.exists('bad.txt') and open('bad.txt').read() == 'red' else 0)"
)


def git(folder, *args):
    return subprocess.run(
        ["git", *args], cwd=folder, capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout.strip()


def configure(folder):
    with open(Path(folder) / ".git" / "config", "a", encoding="utf-8") as handle:
        handle.write("[user]\n\tname = drill\n\temail = drill@example.invalid\n")
        handle.write("[commit]\n\tgpgsign = false\n")


def write(folder, files):
    for relative, text in files.items():
        path = Path(folder) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def seed_origin(root):
    seed = root / "seed"
    seed.mkdir()
    git(seed, "init", "-q", "-b", "main")
    configure(seed)
    write(seed, SEED)
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "seed")
    git(root, "clone", "-q", "--bare", str(seed), str(root / "origin.git"))
    return root / "origin.git"


def make_case(root, origin, name, change):
    case = root / name
    case.mkdir()
    shutil.copytree(origin, case / "origin.git")
    shutil.copytree(origin.parent / "seed", case / "repo")
    repo = case / "repo"
    if name == "conflict":
        write(repo, {TRUNK: '{"upstream": 1}\n'})
        git(repo, "commit", "-q", "-am", "upstream")
        git(repo, "push", "-q", str(case / "origin.git"), "HEAD:main")
        git(repo, "reset", "-q", "--hard", "HEAD~1")
    write(repo, change)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the change under test")
    return case


def run_ship(case, claude, gh, *args, slots=None):
    (case / "stub.json").write_text(json.dumps(claude), encoding="utf-8")
    free = case / "free.txt"
    if not free.exists():
        free.write_text("64", encoding="utf-8")
    (case / "gh.json").write_text(json.dumps(gh), encoding="utf-8")
    env = dict(os.environ)
    env.update(
        {
            "PROJECT_SHIP_STUB": str(case / "stub.json"),
            "PROJECT_SHIP_GH_STUB": str(case / "gh.json"),
            "PROJECT_SHIP_REMOTE": str(case / "origin.git"),
            "PROJECT_SHIP_STATE": str(case / "state"),
            "PROJECT_SHIP_CI_POLL": "0",
            "PROJECT_SHIP_CI_TIMEOUT": "1",
            "PROJECT_SHIP_FRONTEND": json.dumps([[sys.executable, "-c", FRONT_CHECK]]),
            "PROJECT_SHIP_UI_COMPARE": str(case / "ui_compare.py"),
            "PROJECT_SHIP_UI_COMPARE_TIMEOUT": "3",
            "PROJECT_SHIP_LOCK_POLL": "0.1",
            "PROJECT_SHIP_FREE_GB_FILE": str(free),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    env.pop("PROJECT_SHIP_TRIES", None)
    env.pop("PROJECT_SHIP_MIN_FREE_GB", None)
    env.pop("PROJECT_SHIP_SLOTS", None)
    if slots:
        env["PROJECT_SHIP_SLOTS"] = str(slots)
    done = subprocess.run(
        [sys.executable, str(SHIP), *args],
        cwd=case / "repo",
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    return done.returncode, done.stdout + done.stderr


def watch(case, wanted, *write):
    holder = subprocess.Popen(
        [sys.executable, "-c", HOLDER, str(case / "state" / "ship_runs"), wanted, *write]
    )
    threading.Thread(target=holder.wait, daemon=True).start()
    return holder


def hold_slot(case, number, run_id, wanted):
    holder = watch(case, wanted)
    folder = case / "state" / ship.SLOTS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"pid": holder.pid, "run": run_id})
    (folder / ("slot-" + str(number) + ".lock")).write_text(text, encoding="utf-8")
    return holder


def origin_log(case):
    return git(case / "origin.git", "log", "--format=%s", "main").splitlines()


def origin_file(case, relative):
    return git(case / "origin.git", "show", "main:" + relative)


def record(case):
    found = sorted((case / "state" / "ship_runs").glob("*.json"))
    return json.loads(found[-1].read_text(encoding="utf-8"))


def other_record(case, first_id):
    found = []
    for path in sorted((case / "state" / "ship_runs").glob("*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        if entry["id"] != first_id:
            found.append(entry)
    return found[-1]


def step_of(run, name):
    for step in run["steps"]:
        if step["step"] == name:
            return step
    return {}


def log_entries(case):
    path = case / "state" / "ship_log.jsonl"
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        entries.append(json.loads(line))
    return entries


def exits(code, want, output):
    ok = expect("exit " + str(want), code == want)
    if not ok:
        print(output[-3000:])
    return ok


def finding(path, claim="VALUE is wrong"):
    return {"file": path, "line": 1, "claim": claim, "kind": "defect"}


def defect(path):
    return {"findings": [finding(path)]}


CONFIRMED = {"confirmed": True, "evidence": LEAF + ":1"}
BARE = {"confirmed": True, "evidence": ""}
GONE = {"confirmed": False, "evidence": "the line now holds the fixed value"}
NO_GAPS = {"gaps": []}
UI_CLAUDE = {"review": [{"findings": []}], "document": [NO_GAPS]}
LEAF_CHANGE = {LEAF: "VALUE = 2\n"}
ASKED_CHANGE = {LEAF: "VALUE = 2\n", "tools/range.txt": "red"}
TRUNK_CHANGE = {LEAF: "VALUE = 2\n", TRUNK: '{"a": 1}\n'}

CASES = {
    "confirmed": (
        LEAF_CHANGE,
        {
            "review": [{"findings": [finding(LEAF), finding(LEAF, "a second claim")]}],
            "verify": [CONFIRMED, GONE, GONE],
            "fix": [{"write": {LEAF: "VALUE = 3\n"}, "summary": "set VALUE to 3"}],
            "document": [NO_GAPS],
        },
        {"run list": [GREEN]},
    ),
    "trunk": (
        TRUNK_CHANGE,
        {
            "review": [defect(TRUNK)],
            "verify": [{"confirmed": False, "evidence": "refuted-evidence-7q"}],
        },
        {"run list": [GREEN]},
    ),
    "fixer_trunk": (
        LEAF_CHANGE,
        {
            "review": [defect(LEAF)],
            "verify": [CONFIRMED],
            "fix": [
                {"write": {TRUNK: '{"fixer": 1}\n', LEAF: "VALUE = 9\n"}, "summary": "edit main"}
            ],
        },
        {"run list": [GREEN]},
    ),
    "exhausted": (
        LEAF_CHANGE,
        {
            "review": [defect(LEAF)],
            "verify": [CONFIRMED, BARE, BARE, BARE],
            "fix": [
                {"write": {LEAF: "VALUE = 4\n"}, "summary": "try 1"},
                {"write": {LEAF: "VALUE = 5\n"}, "summary": "try 2"},
                {"write": {LEAF: "VALUE = 6\n"}, "summary": "try 3"},
            ],
        },
        {"run list": [GREEN]},
    ),
    "not_a_defect": (
        LEAF_CHANGE,
        {
            "review": [defect(LEAF)],
            "verify": [CONFIRMED],
            "fix": [{"summary": "no change", "not_a_defect": "VALUE = 2 is what the intent asks"}],
        },
        {"run list": [GREEN]},
    ),
    "doc_not_a_defect": (
        LEAF_CHANGE,
        {
            "review": [{"findings": []}],
            "document": [{"gaps": [{"file": "tools/notes.md", "claim": "stale"}]}],
            "fix": [{"summary": "no change", "not_a_defect": "the note already says it"}],
        },
        {"run list": [GREEN]},
    ),
    "drop_with_trunk": (
        TRUNK_CHANGE,
        {
            "review": [{"findings": [finding(TRUNK), finding(LEAF), finding(LEAF, "claim two")]}],
            "verify": [CONFIRMED, CONFIRMED, CONFIRMED],
            "fix": [
                {"summary": "no change", "not_a_defect": "VALUE = 2 is what the intent asks"},
                {"summary": "no change", "not_a_defect": "claim two is not real"},
            ],
        },
        {"run list": [GREEN]},
    ),
    "hook": (
        {HOOK: "VALUE = 2\n"},
        {"review": [defect(HOOK)], "verify": [CONFIRMED]},
        {"run list": [GREEN]},
    ),
    "conflict": (TRUNK_CHANGE, {}, {"run list": [GREEN]}),
    "ci_red": (
        LEAF_CHANGE,
        {
            "review": [{"findings": []}],
            "fix": [{"write": {LEAF: "VALUE = 7\n"}, "summary": "repair CI"}],
            "document": [NO_GAPS, NO_GAPS],
        },
        {
            "run list": [RED, GREEN],
            "run view": [
                {"jobs": [{"name": "checks", "steps": [{"name": "drills"}]}]},
                "x\tFAIL  drill_tool.py\nx\tFAIL  drill_other.py\n",
            ],
        },
    ),
    "ci_startup_failure": (
        LEAF_CHANGE,
        {
            "review": [{"findings": []}],
            "fix": [
                {"write": {LEAF: "VALUE = 11\n"}, "summary": "try 1"},
                {"write": {LEAF: "VALUE = 12\n"}, "summary": "try 2"},
                {"write": {LEAF: "VALUE = 13\n"}, "summary": "try 3"},
            ],
            "document": [NO_GAPS, NO_GAPS, NO_GAPS],
        },
        {"run list": [BROKEN], "run view": [{"gh_error": "log not found: 1"}]},
    ),
    "ci_no_steps": (
        LEAF_CHANGE,
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [RED], "run view": [{"jobs": [{"name": "checks", "steps": []}]}]},
    ),
    "ci_red_billing_text": (
        LEAF_CHANGE,
        {
            "review": [{"findings": []}],
            "fix": [
                {"write": {LEAF: "VALUE = 11\n"}, "summary": "try 1"},
                {"write": {LEAF: "VALUE = 12\n"}, "summary": "try 2"},
                {"write": {LEAF: "VALUE = 13\n"}, "summary": "try 3"},
            ],
            "document": [NO_GAPS, NO_GAPS, NO_GAPS],
        },
        {
            "run list": [RED],
            "run view": [
                {"jobs": [{"name": "checks", "steps": [{"name": "drills"}]}]},
                "x\tFAIL  drill_tool.py\nx\tCI not started (minutes or billing), log not found\n",
            ],
        },
    ),
    "ci_no_run": (
        LEAF_CHANGE,
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [[]]},
    ),
    "ci_timeout": (
        LEAF_CHANGE,
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [[{"status": "in_progress", "conclusion": None, "databaseId": 3}]]},
    ),
    "ci_timeout_red": (
        {LEAF: "VALUE = 2\n", "tools/full.txt": "red"},
        {
            "review": [{"findings": []}],
            "fix": [{"write": {"tools/full.txt": "green"}, "summary": "repair the full suite"}],
            "document": [NO_GAPS, NO_GAPS],
        },
        {"run list": [[{"status": "queued", "conclusion": None, "databaseId": 3}]]},
    ),
    "ci_no_jobs": (
        LEAF_CHANGE,
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [RED], "run view": [{"jobs": []}]},
    ),
    "gate_red": (
        {LEAF: "VALUE = 2\n", "tools/gate.txt": "red"},
        {
            "review": [{"findings": []}],
            "fix": [{"write": {"tools/gate.txt": "green"}, "summary": "repair the gate"}],
            "document": [NO_GAPS],
        },
        {"run list": [GREEN]},
    ),
    "full_not_local": (
        {LEAF: "VALUE = 2\n", "tools/full.txt": "red"},
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [GREEN]},
    ),
    "ci_no_run_red": (
        {LEAF: "VALUE = 2\n", "tools/full.txt": "red"},
        {
            "review": [{"findings": []}],
            "fix": [{"write": {"tools/full.txt": "green"}, "summary": "repair the full suite"}],
            "document": [NO_GAPS, NO_GAPS],
        },
        {"run list": [[]]},
    ),
    "ci_noisy": (
        {**TRUNK_CHANGE, "tools/full.txt": "noisy"},
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [[]]},
    ),
    "doc_partial": (
        LEAF_CHANGE,
        {
            "review": [{"findings": []}],
            "document": [
                {
                    "gaps": [
                        {"file": "tools/notes.md", "claim": "stale"},
                        {"file": "tools/other.md", "claim": "stale"},
                    ]
                }
            ],
            "fix": [{"write": {"tools/notes.md": "fixed"}, "summary": "fix one note"}],
        },
        {"run list": [GREEN]},
    ),
    "front_red": (
        {"frontend/bad.txt": "red"},
        {
            "review": [{"findings": []}],
            "fix": [{"write": {"frontend/bad.txt": "green"}, "summary": "repair the frontend"}],
            "document": [NO_GAPS],
        },
        {"run list": [GREEN]},
    ),
    "ui_ok": ({"frontend/x.txt": "ok", ".ui-compare.json": "{}\n"}, UI_CLAUDE, {"run list": [GREEN]}),
    "ui_missing": ({"frontend/x.txt": "ok"}, UI_CLAUDE, {"run list": [GREEN]}),
    "ui_fail": ({"frontend/x.txt": "ok", ".ui-compare.json": "{}\n"}, UI_CLAUDE, {"run list": [GREEN]}),
    "ui_slow": ({"frontend/x.txt": "ok", ".ui-compare.json": "{}\n"}, UI_CLAUDE, {"run list": [GREEN]}),
    "ui_leaf": (LEAF_CHANGE, UI_CLAUDE, {"run list": [GREEN]}),
    "range_red": (
        {LEAF: "VALUE = 2\n", "tools/range.txt": "red"},
        {"review": [{"findings": []}]},
        {"run list": [GREEN]},
    ),
    "range_red_trunk": (
        {"src/rule.py": "LIMIT = 2\n", "tools/range.txt": "red"},
        {"review": [{"findings": []}]},
        {"run list": [GREEN]},
    ),
    "gate_together": (
        LEAF_CHANGE,
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [GREEN]},
    ),
    "gate_full": (
        LEAF_CHANGE,
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [GREEN]},
    ),
    "gate_memory": (
        LEAF_CHANGE,
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [GREEN]},
    ),
    "gate_alone": (
        LEAF_CHANGE,
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [GREEN]},
    ),
    "lock_resume": (
        TRUNK_CHANGE,
        {
            "review": [defect(TRUNK)],
            "verify": [{"confirmed": False, "evidence": "refuted-evidence-7q"}],
        },
        {"run list": [GREEN]},
    ),
    "moves_two": (
        {LEAF: "VALUE = 2\n", "tests/drill_tool.py": MOVER},
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [GREEN]},
    ),
    "moves_rereview": (
        {"tools/long.txt": "A\nb\nc\nd\ne\nf\ng\n", "tests/drill_long.py": MOVER},
        {"review": [{"findings": []}, {"findings": []}], "document": [NO_GAPS]},
        {"run list": [GREEN]},
    ),
    "moves_four": (
        {LEAF: "VALUE = 2\n", "tests/drill_tool.py": MOVER},
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [GREEN]},
    ),
    "fail_lines": (
        {TRUNK: '{"a": 1}\n', "tests/drill_noisy.py": NOISY},
        {"review": [{"findings": []}]},
        {"run list": [GREEN]},
    ),
    "doc_denied": (
        LEAF_CHANGE,
        {
            "review": [{"findings": []}],
            "document": [{"gaps": [{"file": HOOK, "claim": "stale"}]}],
        },
        {"run list": [GREEN]},
    ),
    "doc_unchanged": (
        LEAF_CHANGE,
        {
            "review": [{"findings": []}],
            "document": [{"gaps": [{"file": "tools/notes.md", "claim": "stale"}]}],
            "fix": [{"summary": "nothing to change"}],
        },
        {"run list": [GREEN]},
    ),
    "push_flaky": (
        LEAF_CHANGE,
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [GREEN]},
    ),
    "push_down": (
        LEAF_CHANGE,
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [GREEN]},
    ),
    "comment_only": (
        {"src/rule.py": "# a different note\nLIMIT = 1\n"},
        {"review": [{"findings": []}], "document": [NO_GAPS]},
        {"run list": [GREEN]},
    ),
    "keep_fix": (
        LEAF_CHANGE,
        {
            "review": [{"findings": [finding(LEAF), finding(TRUNK)]}],
            "verify": [CONFIRMED, GONE, {"confirmed": True, "evidence": TRUNK + ":1"}],
            "fix": [{"write": {LEAF: "VALUE = 3\n"}, "summary": "set VALUE to 3"}],
        },
        {"run list": [GREEN]},
    ),
}
MOVES = {"moves_two": 2, "moves_four": 4, "moves_rereview": 1}


def run_case(root, origin, name):
    change, claude, gh = CASES[name]
    case = make_case(root, origin, name, change)
    if name in MOVES:
        (case / "moves.txt").write_text(str(MOVES[name]), encoding="utf-8")
    if name in UI_COMPARES:
        (case / "ui_compare.py").write_text(UI_COMPARES[name], encoding="utf-8")
    if name in REJECTS:
        hook = case / "origin.git" / "hooks" / "pre-receive"
        with open(hook, "w", encoding="utf-8", newline="") as handle:
            handle.write(PRE_RECEIVE)
        hook.chmod(0o755)
        (case / "origin.git" / "rejects").write_text(str(REJECTS[name]), encoding="utf-8")
    if name == "moves_rereview":
        (case / "move_edit.txt").write_text("a\nb\nc\nD\ne\nf\ng\n", encoding="utf-8")
    if name == "gate_together":
        other = hold_slot(case, 0, "inside-holder", "never in a record")
        code, output = run_ship(case, claude, gh, slots=3)
        other.kill()
        return case, code, output, None
    if name == "gate_full":
        other = hold_slot(case, 0, "first-holder", "never in a record")
        hold_slot(case, 1, "second-holder", '"waiting": "waiting: 2 runs inside')
        code, output = run_ship(case, claude, gh, slots=2)
        other.kill()
        return case, code, output, None
    if name == "gate_memory":
        (case / "free.txt").write_text("1", encoding="utf-8")
        hold_slot(case, 1, "memory-holder", "1.0 GB free")
        watch(case, "1.0 GB free", str(case / "free.txt"), "64")
    if name == "gate_alone":
        (case / "free.txt").write_text("1", encoding="utf-8")
    code, output = run_ship(case, claude, gh)
    if name == "lock_resume" and code == 2:
        run_id = record(case)["id"]
        hold_slot(case, 0, "resume-holder", '"waiting": "waiting: 1 runs inside')
        resumed = {"document": [NO_GAPS]}
        again, more = run_ship(
            case, resumed, gh, "--resume", run_id, "--answer", "R1: drop", slots=1
        )
        return case, code, output, (again, more)
    if name == "trunk" and code == 2:
        run_id = record(case)["id"]
        resumed = {"document": [NO_GAPS]}
        again, more = run_ship(case, resumed, gh, "--resume", run_id, "--answer", "R1: drop")
        return case, code, output, (again, more)
    if name == "hook" and code == 2:
        run_id = record(case)["id"]
        again, more = run_ship(case, {}, gh, "--resume", run_id, "--answer", "R1: fix")
        return case, code, output, (again, more)
    if name == "push_down" and code == 1:
        failed = record(case)
        FAILED_AT_PUSH[name] = (
            failed,
            Path(failed["worktree"]).is_dir(),
            origin_file(case, LEAF),
        )
        again, more = run_ship(case, {"document": [NO_GAPS]}, gh, "--resume", failed["id"])
        return case, code, output, (again, more)
    if name == "keep_fix" and code == 2:
        run_id = record(case)["id"]
        again, more = run_ship(case, {}, gh, "--resume", run_id, "--answer", "R2: fix")
        return case, code, output, (again, more)
    return case, code, output, None


def drill_pipeline(root, origin):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(CASES)) as pool:
        futures = {}
        for name in CASES:
            futures[name] = pool.submit(run_case, root, origin, name)
        done = {}
        for name, future in futures.items():
            done[name] = future.result()
    ok = True

    print("1. a confirmed leaf defect is fixed by the fixer, rechecked and lands")
    case, code, output, _ = done["confirmed"]
    ok &= exits(code, 0, output)
    ok &= expect(
        "origin/main carries the ship review fix commit",
        "ship: review fix - set VALUE to 3" in origin_log(case),
    )
    ok &= expect("the fixed value landed", origin_file(case, LEAF) == "VALUE = 3")
    ok &= expect("the landed run's tree is removed", not Path(record(case)["worktree"]).exists())

    print("2. in the same run a refuted leaf defect is dropped, with no fixer call for it")
    second = record(case)["findings"][1]
    ok &= expect("R2 is recorded as refuted", second.get("outcome") == "refuted")

    print("3. a src/ defect asks the user with the verifier's verdict, even a refuted one")
    case, code, output, resumed = done["trunk"]
    ok &= exits(code, 2, output)
    asks = list((case / "state" / "ship_runs").glob("*.ask.md"))
    text = asks[0].read_text(encoding="utf-8") if asks else ""
    ok &= expect("ask.md names R1 and its file", "R1" in text and TRUNK in text)
    ok &= expect(
        "ask.md carries the verdict and the evidence",
        "refuted" in text and "refuted-evidence-7q" in text,
    )
    ok &= expect(
        "ask.md says what each answer does: drop pushes the change, fix on src/ hands it back",
        "drop does NOT throw the change away" in text and "hands the change back" in text,
    )
    leaf_options = ship.option_lines(
        {"step": "verify", "kind": "defect", "file": "tools/leaf_value.py", "line": 1}
    )
    ok &= expect(
        "a leaf finding's fix says the change is dropped when the fixer fails, as resume() does",
        "the change is dropped and nothing is pushed" in leaf_options
        and "answers not a defect, the change is dropped" in leaf_options,
    )
    ci_options = ship.option_lines({"step": "ci", "kind": "ci_red", "file": "src/", "line": 0})
    ok &= expect(
        "a CI ask says the commit is already on origin/main, no answer pushes or holds it back",
        "already on origin/main" in ci_options and "pushed as it is" not in ci_options,
    )
    ok &= expect(
        "no answer line promises a push: the push is decided once, after all answers",
        "pushed as it is" not in text and "goes on from the next step" in text,
    )

    print("4. --resume with 'R1: drop' continues from test and lands")
    again, more = resumed if resumed else (None, "")
    ok &= exits(again, 0, more)
    ok &= expect("the src/ change landed", '"a": 1' in origin_file(case, TRUNK))

    print("5. a fixer edit under src/ is restored and asks the user")
    case, code, output, _ = done["fixer_trunk"]
    ok &= exits(code, 2, output)
    run = record(case)
    asked = run["asks"][0]["kind"] if run["asks"] else None
    ok &= expect("the ask is fixer_main", asked == "fixer_main")
    restored = (Path(run["worktree"]) / TRUNK).read_text(encoding="utf-8")
    ok &= expect("src/ in the worktree is back to HEAD", restored == "{}\n")
    leaf = (Path(run["worktree"]) / LEAF).read_text(encoding="utf-8")
    ok &= expect("the fixer's leaf edit is dropped with it", leaf == "VALUE = 2\n")
    ok &= expect("nothing landed", origin_log(case) == ["seed"])
    shutil.rmtree(Path(run["worktree"]).parent, ignore_errors=True)

    print("6. a leaf defect still confirmed after 3 fixes does not land and is logged")
    case, code, output, _ = done["exhausted"]
    ok &= exits(code, 3, output)
    ok &= expect("nothing landed", origin_log(case) == ["seed"])
    last = log_entries(case)[-1]
    ok &= expect("ship_log.jsonl ends with a dropped run", last.get("status") == "dropped")
    ok &= expect("the worktree is removed", not Path(record(case)["worktree"]).exists())

    print("6b. the fixer's 'not a defect' on a leaf finding drops the change: no ask, no log line")
    case, code, output, _ = done["not_a_defect"]
    ok &= exits(code, 3, output)
    ok &= expect("nothing landed", origin_log(case) == ["seed"])
    ok &= expect("no ask.md", not list((case / "state" / "ship_runs").glob("*.ask.md")))
    ok &= expect("no ship_log.jsonl line", not (case / "state" / "ship_log.jsonl").exists())
    run = record(case)
    ok &= expect("the record says dropped", run["status"] == "dropped")
    ok &= expect("the worktree is removed", not Path(run["worktree"]).exists())
    ok &= expect(
        "an answer naming src/ still asks, one naming frontend/ui/domain/ does not",
        not ship.leaf_answer("the fix needs src/table.json")
        and ship.leaf_answer("fine as is")
        and ship.leaf_answer("frontend/ui/domain/x.ts is right")
        and not ship.leaf_answer("needs ./src/step2_extraction.py")
        and not ship.leaf_answer("needs C:/project/src/pipeline.py"),
    )

    print(
        "6c. a documentation gap the fixer calls not a defect passes on to lint and lands"
    )
    case, code, output, _ = done["doc_not_a_defect"]
    ok &= exits(code, 0, output)
    ok &= expect("the change landed", origin_file(case, LEAF) == "VALUE = 2")

    print("6d. a leaf drop beside a src/ finding drops the whole change, nothing asked")
    case, code, output, _ = done["drop_with_trunk"]
    ok &= exits(code, 3, output)
    ok &= expect("nothing landed", origin_log(case) == ["seed"])
    ok &= expect("no ask.md", not list((case / "state" / "ship_runs").glob("*.ask.md")))
    ok &= expect("the record keeps the src/ finding", len(record(case)["findings"]) == 3)
    print("7. a rebase onto origin/main that conflicts in src/ asks the user")
    case, code, output, _ = done["conflict"]
    ok &= exits(code, 2, output)
    run = record(case)
    asked = run["asks"][0]["kind"] if run["asks"] else None
    ok &= expect("the ask is rebase_conflict", asked == "rebase_conflict")
    shutil.rmtree(Path(run["worktree"]).parent, ignore_errors=True)

    print("8. CI red on a leaf drill: fixer, steps 5-8 again, CI green")
    case, code, output, _ = done["ci_red"]
    ok &= exits(code, 0, output)
    ok &= expect("the CI fix commit landed", "ship: ci fix - repair CI" in origin_log(case))

    print("9. a drill red in CI that the test step did not select is logged as selection_miss")
    case = done["ci_red"][0]
    misses = []
    for entry in log_entries(case):
        if entry.get("kind") == "selection_miss":
            misses.append(entry.get("drill"))
    ok &= expect("selection_miss names drill_other.py", misses == ["drill_other.py"])

    print("9f. a startup_failure run (invalid workflow file) is red, not not_started")
    case, code, output, _ = done["ci_startup_failure"]
    ok &= exits(code, 3, output)
    ok &= expect("the record says landed_ci_red", record(case)["status"] == "landed_ci_red")

    print("9g. a started red run stays red though its log text names billing")
    case, code, output, _ = done["ci_red_billing_text"]
    ok &= exits(code, 3, output)
    ok &= expect("the record says landed_ci_red", record(case)["status"] == "landed_ci_red")

    print("9e. the full gate reads red drills from run_drills.py's FAILED: line, not the tail")
    long_log = "FAIL  drill_boundaries.py\n" + "x" * 9000 + "\nFAIL  drill_ruff.py\n" + "y" * 7000
    long_log += "\n\nFAILED: drill_boundaries.py, drill_ruff.py\n"
    ok &= expect(
        "drill_boundaries.py stays red though its FAIL line left the tail",
        ship.failed_drills(long_log) == ["drill_boundaries.py", "drill_ruff.py"],
    )

    print("9c. a run GitHub never started (no run, or a run without jobs) runs the full suite here")
    for name in ("ci_no_run", "ci_no_jobs", "ci_no_steps"):
        case, code, output, _ = done[name]
        ok &= exits(code, 0, output)
        ok &= expect(name + " landed", origin_file(case, LEAF) == "VALUE = 2")
        last = record(case)["steps"][-1]
        ok &= expect(
            name + " records the ci step as the full suite run locally, with the reason",
            last["step"] == "ci"
            and last["status"] == "pass"
            and last["gate"] == "local"
            and "full suite ran" in last["drills"]
            and "not started" in last["reason"],
        )
        ok &= expect(name + " ends landed", record(case)["status"] == "landed")

    print("9c2. an Actions run still going when the wait ends runs the full suite here")
    case, code, output, _ = done["ci_timeout"]
    ok &= exits(code, 0, output)
    last = record(case)["steps"][-1]
    ok &= expect(
        "the timeout is the ci step's local full-suite pass, with its own reason",
        last["step"] == "ci"
        and last["status"] == "pass"
        and last["gate"] == "local"
        and "full suite ran" in last["drills"]
        and "did not finish" in last["reason"],
    )
    ok &= expect("the change landed", origin_file(case, LEAF) == "VALUE = 2")
    case, code, output, _ = done["ci_timeout_red"]
    ok &= exits(code, 0, output)
    ok &= expect(
        "a red suite after a timeout went to the fixer like a red CI run",
        "ship: ci fix - repair the full suite" in origin_log(case),
    )

    print("9d. the push waits for the targeted drills, the frontend and the commit rule")
    case, code, output, _ = done["gate_red"]
    ok &= exits(code, 0, output)
    ok &= expect(
        "the gate fix commit landed", "ship: test fix - repair the gate" in origin_log(case)
    )
    case, code, output, _ = done["full_not_local"]
    ok &= exits(code, 0, output)
    run = record(case)
    ok &= expect(
        "the test step did not run the full suite, though its stand-in is red",
        "run_drills.py" not in step_of(run, "test")["drills"],
    )
    ok &= expect("the change landed", origin_file(case, LEAF) == "VALUE = 2")
    ok &= expect("a started run's pass says the gate ran in CI", step_of(run, "ci")["gate"] == "ci")
    case, code, output, _ = done["ci_no_run_red"]
    ok &= exits(code, 0, output)
    ok &= expect(
        "the red full suite run here went to the fixer like a red CI run",
        "ship: ci fix - repair the full suite" in origin_log(case),
    )
    case, code, output, _ = done["front_red"]
    ok &= exits(code, 0, output)
    ok &= expect(
        "the frontend fix commit landed", "ship: test fix - repair the frontend" in origin_log(case)
    )
    print("9f. a frontend range runs the ui-compare skill after the gate and never blocks the push")
    case, code, output, _ = done["ui_ok"]
    ok &= exits(code, 0, output)
    args = (case / "args.txt").read_text(encoding="utf-8") if (case / "args.txt").exists() else ""
    ok &= expect(
        "the success line is the path of compare.html",
        "ship: ui-compare: C:/out/compare.html" in output,
    )
    ok &= expect(
        "the skill got --repo, --base and --head and no --open",
        "--repo" in args and "--base" in args and "--head" in args and "--open" not in args,
    )
    ok &= expect(
        "the step records the line", "compare.html" in step_of(record(case), "test")["ui_compare"]
    )
    case, code, output, _ = done["ui_missing"]
    ok &= exits(code, 0, output)
    ok &= expect(
        "a missing skill is one skipped line", "ui-compare: skipped (skill missing)" in output
    )
    ok &= expect("the push went on", origin_file(case, "frontend/x.txt") == "ok")
    case, code, output, _ = done["ui_fail"]
    ok &= exits(code, 0, output)
    ok &= expect("an exit 1 is skipped, not an error", "ui-compare: skipped (exit 1)" in output)
    ok &= expect("the push went on", origin_file(case, "frontend/x.txt") == "ok")
    case, code, output, _ = done["ui_slow"]
    ok &= exits(code, 0, output)
    ok &= expect("a timeout is skipped", "ui-compare: skipped (timed out)" in output)
    ok &= expect("the push went on", origin_file(case, "frontend/x.txt") == "ok")
    case, code, output, _ = done["ui_leaf"]
    ok &= exits(code, 0, output)
    ok &= expect(
        "a range without frontend/ never calls the skill",
        not (case / "args.txt").exists() and "ui-compare" not in output,
    )
    bare = tempfile.mkdtemp(prefix="project-drill-ui-")
    os.environ["PROJECT_SHIP_UI_COMPARE"] = __file__
    try:
        said = ship.ui_compare({"base": "0" * 40}, bare, ["frontend/x.txt"])
    finally:
        del os.environ["PROJECT_SHIP_UI_COMPARE"]
        shutil.rmtree(bare, ignore_errors=True)
    ok &= expect(
        "a repo without .ui-compare.json is skipped with that reason",
        said == "ui-compare: skipped (no .ui-compare.json)",
    )

    case, code, output, _ = done["range_red"]
    ok &= exits(code, 2, output)
    asked = [ask["kind"] for ask in record(case).get("asks", [])]
    ok &= expect("the ask is commit_range", asked == ["commit_range"])
    ok &= expect("nothing landed", origin_log(case) == ["seed"])
    case, code, output, _ = done["range_red_trunk"]
    ok &= exits(code, 2, output)
    asked = [ask["kind"] for ask in record(case).get("asks", [])]
    ok &= expect(
        "a src/*.py range with a red commit rule asks both, so answering one cannot skip the other",
        asked == ["unpinned", "commit_range"],
    )

    print("9b. a confirmed .claude/ defect asks the user; the fixer, refused there, is not called")
    case, code, output, resumed = done["hook"]
    ok &= exits(code, 2, output)
    asked = [ask["kind"] for ask in record(case).get("asks", [])]
    ok &= expect("the ask is hook_defect", asked == ["hook_defect"])
    hook_text = ""
    for path in (case / "state" / "ship_runs").glob("*.ask.md"):
        hook_text = path.read_text(encoding="utf-8")
    ok &= expect(
        "its fix answer hands the change back", "fix: the run stops and hands" in hook_text
    )
    again = resumed[0] if resumed else None
    ok &= expect("'R1: fix' hands the change back (exit 3), no fixer call", again == 3)

    print("17. the memory gate lets a second run in beside one inside when slots are left")
    case, code, output, _ = done["gate_together"]
    ok &= exits(code, 0, output)
    ok &= expect("it entered with no wait", "waiting:" not in output)
    case_slot = case / "state" / ship.SLOTS_DIR
    ok &= expect("the other run's slot is untouched", (case_slot / "slot-0.lock").exists())
    ok &= expect("its own slot is released", not (case_slot / "slot-1.lock").exists())

    print("17b. with every slot held a third run waits, logs and records why, then lands")
    case, code, output, _ = done["gate_full"]
    ok &= exits(code, 0, output)
    said = "waiting: 2 runs inside, 64.0 GB free"
    ok &= expect("the run logs the wait with the count and the memory", said in output)
    ok &= expect("its record keeps the wait", record(case).get("waited") == [said])
    ok &= expect(
        "it took the gone holder's slot", "took over the slot of run second-holder" in output
    )
    ok &= expect("the change landed after the wait", origin_file(case, LEAF) == "VALUE = 2")

    print("17c. a run waits while free memory is below the floor, then lands")
    case, code, output, _ = done["gate_memory"]
    ok &= exits(code, 0, output)
    ok &= expect("the wait names the memory", "waiting: 1 runs inside, 1.0 GB free" in output)
    ok &= expect("the change landed after the wait", origin_file(case, LEAF) == "VALUE = 2")
    slot = case / "state" / ship.SLOTS_DIR / "slot-0.lock"
    ok &= expect("its slot is released at the end", not slot.exists())

    print("17d. below the floor with no run inside, a run enters at once")
    case, code, output, _ = done["gate_alone"]
    ok &= exits(code, 0, output)
    ok &= expect("no wait was logged", "waiting:" not in output)
    ok &= expect("the change landed", origin_file(case, LEAF) == "VALUE = 2")

    print("19. a --resume re-enters test through the gate")
    case, code, output, resumed = done["lock_resume"]
    ok &= exits(code, 2, output)
    again, more = resumed if resumed else (None, "")
    ok &= exits(again, 0, more)
    ok &= expect("the resume waits for the full slot", "waiting: 1 runs inside" in more)
    ok &= expect("the src/ change landed", '"a": 1' in origin_file(case, TRUNK))

    print("8b. a red drill's FAIL line reaches the ask though far more output follows it")
    case, code, output, _ = done["fail_lines"]
    ok &= exits(code, 2, output)
    asks = record(case).get("asks", [])
    evidence = asks[0].get("evidence", "") if asks else ""
    ok &= expect(
        "the ask names the drill and keeps its failing line",
        "drill_noisy.py" in evidence and "FAIL  case q9-marker: got 1, wanted 2" in evidence,
    )
    data = '+<img src="data:image/svg+xml;base64,' + "A" * 900000 + '">'
    short = ship.shortened("+a short line\n" + data + "\n-old\n")
    ok &= expect(
        "the review diff shortens a line of embedded data and keeps every other line whole",
        len(short) < 1000
        and short.startswith("+a short line\n" + data[: ship.LONG_LINE_KEPT] + " [")
        and short.endswith(" characters shortened for the review]\n-old\n"),
    )
    ok &= expect(
        "fail_lines reads every FAIL line of the whole output, not the kept tail",
        ship.fail_lines("FAIL  a\n" + "x" * 9000 + "\nok\nFAILED: b\n") == ["FAIL  a", "FAILED: b"],
    )
    ok &= expect(
        "a passing check whose label holds the word FAIL is not read as a failure",
        ship.fail_lines("  ok   its FAIL line left the tail\n  FAIL the real one\n")
        == ["FAIL the real one"],
    )
    prefix = "verify\tRun drills\t2026-11-05T12:00:00.1234567Z "
    ok &= expect(
        "nor one under a gh --log-failed prefix, while a FAIL line holding the word ok is kept",
        ship.fail_lines(prefix + "  ok   its FAIL line\n" + prefix + "  FAIL result ok when b\n")
        == [prefix + "  FAIL result ok when b"],
    )
    shutil.rmtree(Path(record(case)["worktree"]).parent, ignore_errors=True)

    print("9i. a documentation edit that was not applied is said so in the run's output")
    case, code, output, _ = done["doc_denied"]
    ok &= exits(code, 0, output)
    ok &= expect("a .claude/ gap prints not applied", "not applied: " + HOOK in output)
    ok &= expect(
        "and is recorded on the document step",
        step_of(record(case), "document").get("not_applied") == [HOOK],
    )
    ok &= expect(
        "the printed line carries the gap's claim",
        "(the fixer cannot edit .claude/): stale" in output,
    )
    ok &= expect(
        "and the step keeps the gap with its claim",
        {"file": HOOK, "claim": "stale"}
        in (step_of(record(case), "document").get("findings") or []),
    )
    case, code, output, _ = done["doc_unchanged"]
    ok &= exits(code, 0, output)
    ok &= expect(
        "a gap the fixer left unchanged prints not applied", "not applied: tools/notes.md" in output
    )

    case, code, output, _ = done["doc_partial"]
    ok &= exits(code, 0, output)
    ok &= expect(
        "of two gaps the fixer edited one, the other prints not applied",
        "not applied: tools/other.md" in output and "not applied: tools/notes.md" not in output,
    )
    ok &= expect(
        "and is recorded on the document step",
        step_of(record(case), "document").get("not_applied") == ["tools/other.md"],
    )

    print("8c. the local full suite's FAIL line reaches the ci ask though far more output follows")
    case, code, output, _ = done["ci_noisy"]
    ok &= exits(code, 2, output)
    asks = record(case).get("asks", [])
    evidence = asks[0].get("evidence", "") if asks else ""
    ok &= expect(
        "the ci ask keeps the failing line of the whole output",
        "FAIL  case q9-ci: got 1, wanted 2" in evidence,
    )

    print("9h. a hand-back names the run's own fix commits instead of losing them with the tree")
    case, code, output, resumed = done["keep_fix"]
    ok &= exits(code, 2, output)
    again, more = resumed if resumed else (None, "")
    ok &= exits(again, 3, more)
    kept = record(case).get("kept_commits") or []
    ok &= expect(
        "the record keeps the fix commit and nothing else",
        len(kept) == 1 and kept[0].endswith(" ship: review fix - set VALUE to 3"),
    )
    sha = kept[0].split(" ")[0] if kept else "none"
    ok &= expect("the output tells the session to cherry-pick it", "git cherry-pick " + sha in more)
    shown = subprocess.run(
        ["git", "show", sha + ":" + LEAF], cwd=case / "repo", capture_output=True, text=True
    )
    ok &= expect(
        "the commit is still in the repository after the tree is gone",
        shown.returncode == 0 and shown.stdout.strip() == "VALUE = 3",
    )
    ok &= expect("the worktree is removed", not Path(record(case)["worktree"]).exists())
    tree = str(case / "kept_tree")
    subprocess.run(
        ["git", "worktree", "add", "-q", "--detach", tree, sha],
        cwd=case / "repo",
        capture_output=True,
    )
    base = subprocess.run(
        ["git", "rev-parse", sha + "~1"], cwd=tree, capture_output=True, text=True
    ).stdout.strip()
    landed = {"id": record(case)["id"], "worktree": tree, "base": base, "landed": sha}
    ok &= expect(
        "a fix commit the push already landed is not named for cherry-picking",
        ship.fixer_commits(landed) == [],
    )
    del landed["landed"]
    ok &= expect(
        "and one not landed still is",
        [line.split(" ")[0] for line in ship.fixer_commits(landed)] == [sha],
    )

    print("20c. a push the server fails twice is tried again and lands")
    case, code, output, _ = done["push_flaky"]
    ok &= exits(code, 0, output)
    ok &= expect("the change landed", origin_file(case, LEAF) == "VALUE = 2")
    ok &= expect("the retries are said in the output", "try 3 of 3" in output)

    print("20d. a push the server fails three times fails the run at the push; --resume lands it")
    case, code, output, resumed = done["push_down"]
    ok &= exits(code, 1, output)
    ok &= expect("the error is the server's", "commit_refs_rules" in output)
    first, had_tree, on_origin = FAILED_AT_PUSH.get("push_down", ({}, False, ""))
    ok &= expect("nothing landed before the resume", on_origin == "VALUE = 1")
    ok &= expect(
        "the failed run is marked failed at the push and keeps its tree",
        first.get("status") == "failed" and first.get("current") == "push" and had_tree,
    )
    again, more = resumed if resumed else (None, "")
    ok &= exits(again, 0, more)
    ok &= expect("the resumed run landed the change", origin_file(case, LEAF) == "VALUE = 2")
    ok &= expect("it is the same run, now landed", record(case)["status"] == "landed")
    ok &= expect("and its tree is removed", not Path(first.get("worktree", ".")).exists())
    ok &= expect(
        "a server failure is retried, a non-fast-forward is not",
        ship.server_rejected("remote: fatal error in commit_refs_rules")
        and ship.server_rejected(" ! [remote rejected] HEAD -> main (failure)")
        and not ship.server_rejected(" ! [remote rejected] HEAD -> main (non-fast-forward)")
        and not ship.server_rejected(" ! [rejected] HEAD -> main (fetch first)"),
    )

    print("9j. a src/ change that edits comments only skips the revert-and-rerun, no ask")
    case, code, output, _ = done["comment_only"]
    ok &= exits(code, 0, output)
    tested = step_of(record(case), "test")
    ok &= expect(
        "the test step records the file as comment-only and ran no revert",
        tested.get("comment_only") == ["src/rule.py"] and tested.get("mutation") is None,
    )
    ok &= expect("the change landed", "different note" in origin_file(case, "src/rule.py"))
    before = "# a note\nLIMIT = 1\n"
    ok &= expect(
        "a comment, a docstring and the layout are not statements",
        ship.comment_only(before, "# other\nLIMIT = 1  # why\n")
        and ship.comment_only("def f():\n    return 1\n", 'def f():\n    "doc"\n    return 1\n')
        and ship.comment_only('"""a"""\nX = [1,2]\n', '"""b"""\nX = [\n    1,\n    2,\n]\n'),
    )
    ok &= expect(
        "a changed statement, a changed value and broken syntax are not comment-only",
        not ship.comment_only(before, "# a note\nLIMIT = 2\n")
        and not ship.comment_only(before, "# a note\nLIMIT = 1\nLIMIT2 = 1\n")
        and not ship.comment_only(before, "# a note\nLIMIT = \n"),
    )

    print("20. origin/main moving twice before the push is rebased twice and lands")
    case, code, output, _ = done["moves_two"]
    ok &= exits(code, 0, output)
    ok &= expect("the record counts two moves", record(case).get("main_moves") == 2)
    ok &= expect(
        "the retest after the rebase passed, so the record does not hold it open",
        record(case).get("retest_open") is False,
    )
    held = {
        "id": "x",
        "worktree": str(case),
        "reviewed": "abc",
        "retest_open": True,
        "error": "remote: fatal error in commit_refs_rules",
    }
    try:
        refused = ship.resume_push(held) == 1
    except ship.ShipError as error:
        refused = False
        held["error"] = str(error)
    ok &= expect(
        "a run that failed in the retest after a rebase is not restarted at the push", refused
    )
    ok &= expect(
        "and the refusal keeps the server's error in the record",
        held["error"] == "remote: fatal error in commit_refs_rules",
    )
    answered = {
        "id": "y",
        "worktree": str(case),
        "retest_open": True,
        "asks": [{"id": "T1", "step": "test"}],
        "answers": [],
        "findings": [],
        "next_step": "push",
    }
    real_drive, real_save = ship.drive, ship.save
    ship.drive = lambda run, first: first
    ship.save = lambda run: None
    try:
        went_on = ship.resume(answered, ["T1: not a defect because the drill is flaky"])
    finally:
        ship.drive, ship.save = real_drive, real_save
    ok &= expect(
        "an answered retest ask resumes with the retest settled, so a failed push can restart",
        went_on == "push" and answered["retest_open"] is False,
    )
    ok &= expect("the change landed", origin_file(case, LEAF) == "VALUE = 2")
    log = origin_log(case)
    ok &= expect(
        "both upstream moves stay under it", "upstream move 1" in log and "upstream move 2" in log
    )

    print("20b. a move whose rebase changes the reviewed diff is reviewed again, not refused")
    case, code, output, _ = done["moves_rereview"]
    ok &= exits(code, 0, output)
    reviews = 0
    for step in record(case)["steps"]:
        if step["step"] == "review":
            reviews += 1
    ok &= expect("the rebased range had a second review", reviews == 2)
    ok &= expect(
        "both edits landed together",
        origin_file(case, "tools/long.txt").splitlines() == ["A", "b", "c", "D", "e", "f", "g"],
    )

    print("21. a fourth move fails the run with the count")
    case, code, output, _ = done["moves_four"]
    ok &= exits(code, 1, output)
    ok &= expect("the error names four moves", "moved 4 times" in output)
    ok &= expect("nothing of the change landed", origin_file(case, LEAF) == "VALUE = 1")
    shutil.rmtree(Path(record(case)["worktree"]).parent, ignore_errors=True)
    return ok


def first_ship_handed_back(root, origin, name, change, open_finding=False):
    case = make_case(root, origin, name, change)
    claude = {"review": [{"findings": []}]}
    answer = "T1: fix"
    if open_finding:
        claude = {"review": [defect(TRUNK)], "verify": [{"confirmed": False, "evidence": "e"}]}
        answer = "R1: fix"
    code, output = run_ship(case, claude, {"run list": [GREEN]})
    ok = exits(code, 2, output)
    first = record(case)
    again, more = run_ship(
        case, {}, {"run list": [GREEN]}, "--resume", first["id"], "--answer", answer
    )
    ok &= exits(again, 3, more)
    return case, first["id"], ok


def second_ship(case):
    repo = case / "repo"
    write(repo, {"tools/second.py": "SECOND = 1\n", "tools/range.txt": "green"})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the fix after the hand-back")
    claude = {"review": [{"findings": []}], "document": [NO_GAPS]}
    return run_ship(case, claude, {"run list": [GREEN]})


def drill_retry_review(root, origin):
    print("23. a fresh ship of a branch a run already reviewed reviews only the new commits")
    case, first_id, ok = first_ship_handed_back(root, origin, "retry", ASKED_CHANGE)
    reviewed = record(case)["reviewed"]
    code, output = second_ship(case)
    ok &= exits(code, 0, output)
    run = other_record(case, first_id)
    review = step_of(run, "review")
    ok &= expect(
        "the review starts at the commit the first run reviewed", review.get("since") == reviewed
    )
    ok &= expect("the record names the earlier run", run["prior"]["run"] == first_id)
    work = str(case / "repo")
    whole = ship.context(run, work)
    ok &= expect("the whole range holds the first commit's file too", "- " + LEAF in whole)
    seen = []
    real = ship.call_child
    ship.call_child = lambda role, prompt, folder: seen.append(prompt) or {"findings": []}
    try:
        ship.step_review(dict(run, since=reviewed), work)
    finally:
        ship.call_child = real
    ok &= expect(
        "step_review hands the reviewer only the range after the reviewed commit",
        len(seen) == 1 and "- tools/second.py" in seen[0] and "- " + LEAF not in seen[0],
    )
    ok &= expect(
        "a start with nothing after it is skipped, not sent to the reviewer",
        ship.step_review({"since": git(work, "rev-parse", "HEAD")}, work)["status"] == "skip",
    )
    ok &= expect("the change landed", origin_file(case, "tools/second.py") == "SECOND = 1")
    return ok


def drill_retry_open_finding(root, origin):
    print(
        "23c. a run that stopped with a review finding still open proves nothing: the whole range"
    )
    case, first_id, ok = first_ship_handed_back(root, origin, "retry_open", TRUNK_CHANGE, True)
    code, output = second_ship(case)
    ok &= exits(code, 0, output)
    run = other_record(case, first_id)
    ok &= expect("the open finding leaves no earlier review", not run.get("prior"))
    ok &= expect("so the reviewer read from the base", step_of(run, "review").get("since") is None)
    return ok


def drill_retry_unproven(root, origin):
    print("23b. an earlier review whose patch the rebase changed is unproven: the whole range")
    edit = {"tools/long.txt": "A\nb\nc\nd\ne\nf\ng\n", "tools/range.txt": "red"}
    case, first_id, ok = first_ship_handed_back(root, origin, "retry_moved", edit)
    mover = case / "mover"
    git(case, "clone", "-q", str(case / "origin.git"), str(mover))
    configure(mover)
    write(mover, {"tools/long.txt": "a\nb\nc\nD\ne\nf\ng\n"})
    git(mover, "commit", "-q", "-am", "upstream edit near the change")
    git(mover, "push", "-q", "origin", "HEAD:main")
    code, output = second_ship(case)
    ok &= exits(code, 0, output)
    run = other_record(case, first_id)
    ok &= expect("the earlier review was found", run["prior"]["run"] == first_id)
    ok &= expect("but the changed patch leaves it unproven", not run.get("since"))
    ok &= expect("so the reviewer read from the base", step_of(run, "review").get("since") is None)
    return ok


def drill_lock_status(root):
    print("22. --status shows a waiting run as waiting, and the liveness check reads a dead pid")
    folder = root / "status"
    (folder / "ship_runs").mkdir(parents=True)
    said = "waiting: 3 runs inside, 4.2 GB free"
    waiting = {
        "id": "r2",
        "status": "running",
        "waiting": said,
        "current": "review",
        "pid": os.getpid(),
    }
    (folder / "ship_runs" / "r2.json").write_text(json.dumps(waiting), encoding="utf-8")
    shown = ship.status_lines(folder)
    ok = expect("the line says why it waits", bool(shown) and said in shown[0])
    gone_waiter = subprocess.Popen([sys.executable, "-c", "pass"])
    gone_waiter.wait()
    waiting["pid"] = gone_waiter.pid
    waiting["last_step"] = "rebase"
    (folder / "ship_runs" / "r2.json").write_text(json.dumps(waiting), encoding="utf-8")
    shown = ship.status_lines(folder)
    ok &= expect(
        "a waiter whose process is gone reads as cut off, not as waiting",
        bool(shown) and said not in shown[0] and "stopped after" in shown[0],
    )
    reading = ship.free_gb()
    ok &= expect("this machine's free memory reads as a number", isinstance(reading, float))
    return ok


def drill_sweep(root, case):
    print("24. --status removes the ship tree of a run that is no longer running, no other")
    state = case / "state"
    gone_proc = subprocess.Popen([sys.executable, "-c", "pass"])
    gone_proc.wait()
    records = {
        "ended": {"status": "landed"},
        "cut_off": {"status": "running", "pid": gone_proc.pid},
        "alive": {"status": "running", "pid": os.getpid()},
        "no_pid": {"status": "running"},
        "gone_caller": {"status": "landed", "caller": str(root / "no-such-folder")},
        "asking": {"status": "asking", "pid": gone_proc.pid},
        "failed": {"status": "failed", "pid": gone_proc.pid},
    }
    trees = {}
    for name, entry in records.items():
        tree = root / ("project-ship-sweep-" + name) / "tree"
        tree.mkdir(parents=True)
        trees[name] = tree
        entry.update({"id": name, "worktree": str(tree)})
        entry.setdefault("caller", str(root))
        folder = state / "ship_runs"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (name + ".json")).write_text(json.dumps(entry), encoding="utf-8")
    fixed = root / "project-ship-sweep-cut_off_fixed" / "tree"
    fixed.mkdir(parents=True)
    git_in = ["git", "-c", "user.name=d", "-c", "user.email=d@x", "-C", str(fixed)]
    subprocess.run(git_in[:-2] + ["init", "-q", str(fixed)], check=True)
    subprocess.run(git_in + ["commit", "-q", "--allow-empty", "-m", "base"], check=True)
    base = subprocess.run(
        git_in + ["rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    message = "ship: review fix - keep me\n\nShip-Run: cut_off_fixed"
    subprocess.run(git_in + ["commit", "-q", "--allow-empty", "-m", message], check=True)
    fix_sha = subprocess.run(
        git_in + ["rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    fixed_record = {
        "id": "cut_off_fixed",
        "status": "running",
        "pid": gone_proc.pid,
        "worktree": str(fixed),
        "caller": str(root),
        "base": base,
    }
    (state / "ship_runs" / "cut_off_fixed.json").write_text(
        json.dumps(fixed_record), encoding="utf-8"
    )
    code, output = run_ship(case, {}, {}, "--status")
    ok = exits(code, 0, output)
    ok &= expect(
        "an ended run's tree and a cut-off run's tree are removed",
        not trees["ended"].exists() and not trees["cut_off"].exists(),
    )
    ok &= expect(
        "a live, a pid-less, an asking and a failed run keep theirs",
        trees["alive"].exists()
        and trees["no_pid"].exists()
        and trees["asking"].exists()
        and trees["failed"].exists(),
    )
    ok &= expect(
        "a run whose caller folder is gone is swept too, and does not end --status",
        not trees["gone_caller"].exists(),
    )
    ok &= expect("--status says which runs it swept", "run ended (landed)" in output)
    kept = json.loads((state / "ship_runs" / "cut_off_fixed.json").read_text(encoding="utf-8"))
    ok &= expect(
        "a cut-off run holding a fix commit no branch has keeps its tree and names the commit",
        fixed.exists()
        and "git cherry-pick " + fix_sha in output
        and [line.split(" ")[0] for line in kept.get("kept_commits", [])] == [fix_sha],
    )
    return ok


def flaky_git(count, text):
    seen = []

    def run(folder, *args, **kwargs):
        seen.append(args)
        if len(seen) <= count:
            error = ship.ShipError("git " + args[0] + " failed: " + text[:400])
            error.full = text
            raise error
        return subprocess.CompletedProcess(args, 0, "ok", "")

    return run, seen


def retried(count, text, again):
    fake, seen = flaky_git(count, text)
    real = ship.git
    ship.git = fake
    try:
        ship.git_retrying(".", "fetch", "origin", "main", again=again)
        raised = False
    except ship.ShipError:
        raised = True
    finally:
        ship.git = real
    return len(seen), raised


def drill_network_retry():
    print("25. a fetch is tried 3 times on a DNS or connection failure, not on an auth failure")
    saved = os.environ.get("PROJECT_SHIP_RETRY_PAUSE")
    os.environ["PROJECT_SHIP_RETRY_PAUSE"] = "0"
    try:
        dns = "fatal: unable to access 'https://github.com/x.git/': Could not resolve host: github.com"
        auth = "fatal: Authentication failed for 'https://github.com/x.git/'"
        denied = "fatal: unable to access 'https://github.com/x.git/': The requested URL returned error: 403"
        ok = expect(
            "two DNS failures, then success: three calls, no error",
            retried(2, dns, ship.transient_network) == (3, False),
        )
        ok &= expect(
            "a DNS failure that stays: three calls, then the error",
            retried(9, dns, ship.transient_network) == (3, True),
        )
        ok &= expect(
            "an authentication failure is raised at once",
            retried(9, auth, ship.transient_network) == (1, True),
        )
        ok &= expect(
            "a 403 worded 'unable to access' is an authentication failure too",
            retried(9, denied, ship.transient_network) == (1, True),
        )
        fake, seen = flaky_git(2, dns)
        real = ship.git
        ship.git = fake
        try:
            head = ship.fetch(".")
        finally:
            ship.git = real
        ok &= expect(
            "fetch() goes through the retry and then reads FETCH_HEAD",
            head == "ok" and [call[0] for call in seen] == ["fetch", "fetch", "fetch", "rev-parse"],
        )
    finally:
        if saved is None:
            os.environ.pop("PROJECT_SHIP_RETRY_PAUSE", None)
        else:
            os.environ["PROJECT_SHIP_RETRY_PAUSE"] = saved
    return ok


def drill_selection(root):
    print("10. the test step selects the drill naming a changed file and skips an unrelated one")
    tree = root / "select"
    write(tree, SEED)
    names = ship.select_drills(str(tree), [(LEAF, "")])
    ok = expect("drill_tool.py is selected (it names tool)", "drill_tool.py" in names)
    ok &= expect("drill_other.py is not selected", "drill_other.py" not in names)
    return ok


def drill_push_refusal(case):
    print("11. push refuses a HEAD that does not descend from the reviewed commit")
    repo = case / "repo"
    reviewed = git(repo, "rev-parse", "HEAD")
    sibling = git(repo, "commit-tree", "HEAD~1^{tree}", "-p", "HEAD~1", "-m", "other")
    git(repo, "checkout", "-q", "--detach", sibling)
    refused = False
    try:
        ship.assert_reviewed(str(repo), reviewed)
    except ship.ShipError:
        refused = True
    ok = expect("a sibling of the reviewed commit is refused", refused)
    git(repo, "checkout", "-q", "--detach", reviewed)
    ok &= expect(
        "the reviewed commit itself is allowed",
        ship.assert_reviewed(str(repo), reviewed) == reviewed,
    )
    return ok


def drill_restore_only_fixer_edits(case):
    print("12. only the fixer's own src/ edits are undone, not a src/ file a rebase staged")
    repo = case / "repo"
    write(repo, {TRUNK: '{"merged": 1}\n'})
    git(repo, "add", TRUNK)
    snapshot = ship.trunk_snapshot(str(repo))
    write(repo, {TRUNK: '{"fixer": 1}\n', "src/new.py": "X = 1\n"})
    restored = ship.restore_trunk(str(repo), snapshot)
    ok = expect("both fixer edits are reported", sorted(restored) == ["src/new.py", TRUNK])
    kept = (repo / TRUNK).read_text(encoding="utf-8")
    ok &= expect("the staged merge is back, not HEAD's text", kept == '{"merged": 1}\n')
    ok &= expect("the fixer's new src/ file is gone", not (repo / "main" / "new.py").exists())
    ok &= expect(
        "an untouched staged file is not reported",
        ship.restore_trunk(str(repo), ship.trunk_snapshot(str(repo))) == [],
    )
    return ok


def drill_needs_main(case):
    print("12b. a fixer answer with needs_main set is never a quiet drop (fix.md)")
    ship.STUBS["claude"] = {"fix": [{"summary": "s", "not_a_defect": "x", "needs_main": True}]}
    try:
        _summary, reason, _restored = ship.fixer({"base": "HEAD"}, str(case / "repo"), "test", "p")
    finally:
        ship.STUBS["claude"] = None
    return expect("the reason asks", reason and not ship.leaf_answer(reason))


def drill_no_drill_message():
    print("13. the revert-and-rerun is skipped only when every src/ commit says no drill:")
    mixed = ship.no_drill_message([("x no drill: typo only", True), ("y adds a rule", True)])
    ok = expect("one src/ commit without it: the check runs", mixed == "")
    alone = ship.no_drill_message([("x no drill: typo only", True), ("notes only", False)])
    ok &= expect("every src/ commit says it: skipped", alone == "x no drill: typo only")
    return ok


def drill_unpinned_trunk_only():
    print("14. the revert-and-rerun asks only for an unpinned src/ file, not a leaf one")
    leaf = {"path": "tools/x.py", "status": "no_drill_named"}
    pinned = {"status": "unpinned", "files": [leaf, {"path": "src/a.py", "status": "pinned"}]}
    ok = expect("an unnamed leaf file alone does not ask", ship.unpinned_trunk(pinned) == "")
    unpinned = {"status": "unpinned", "files": [{"path": "src/a.py", "status": "unpinned"}]}
    ok &= expect("an unpinned src/ file asks", "src/a.py" in ship.unpinned_trunk(unpinned))
    return ok


def drill_reviewer_paths():
    print("15. a reviewer's ./ or absolute worktree path to src/ still counts as src/")
    work = "C:/tmp/project-ship-x/tree"
    absolute = ship.repo_path(work, "C:\\tmp\\project-ship-x\\tree\\src\\a.py")
    ok = expect("absolute path: src/a.py", absolute == "src/a.py")
    ok &= expect("./ path: src/a.py", ship.repo_path(work, "./src/a.py") == "src/a.py")
    return ok


def drill_drop_subject():
    print("16. a fix that removes an expect( call is a drop drill: commit")
    header = ["diff --git a/tests/drill_x.py b/tests/drill_x.py", "--- a/tests/drill_x.py"]
    header.append("+++ b/tests/drill_x.py")
    dropped = "\n".join(header + ['-    ok &= expect("a", True)', " ok = True"])
    added = "\n".join(header + ['+    ok &= expect("a", True)'])
    ok = expect("a removed case is seen", ship.drops_expects(dropped))
    ok &= expect("an added case is not", not ship.drops_expects(added))
    return ok


def drill_child_not_json():
    print(
        "16c. a read-only child answering in prose is asked once more, and the error shows its answer"
    )
    calls = []
    answers = ["I looked at the diff and found nothing.", '{"findings": []}']

    class Done:
        def __init__(self, text):
            self.returncode = 0
            self.stdout = json.dumps({"is_error": False, "result": text})

    def fake_run(command, **kwargs):
        calls.append(command)
        return Done(answers[min(len(calls), len(answers)) - 1])

    saved = (ship.subprocess.run, ship.shutil.which, ship.STUBS["claude"])
    ship.subprocess.run = fake_run
    ship.shutil.which = lambda name: "claude"
    ship.STUBS["claude"] = None
    try:
        answer = ship.call_child("review", "prompt", ".")
        ok = expect("the second answer is taken after one prose answer", answer == {"findings": []})
        ok &= expect("the child was asked twice", len(calls) == 2)
        answers[1] = "Still prose."
        calls.clear()
        try:
            ship.call_child("review", "prompt", ".")
            message = ""
        except ship.ShipError as error:
            message = str(error)
        ok &= expect(
            "two prose answers fail and the error shows the answer",
            "Still prose." in message and len(calls) == 2,
        )
        answers[0] = "Edited, no JSON."
        calls.clear()
        try:
            ship.call_child("fix", "prompt", ".")
        except ship.ShipError:
            pass
        ok &= expect("the fixer is not asked again", len(calls) == 1)
    finally:
        ship.subprocess.run, ship.shutil.which, ship.STUBS["claude"] = saved
    return ok


def drill_child_env():
    print("16d. the review child does not inherit BUN_INSPECT, which makes it bind a debugger port")
    seen = []

    class Done:
        returncode = 0
        stdout = json.dumps({"is_error": False, "result": '{"findings": []}'})

    def fake_run(command, **kwargs):
        seen.append(kwargs["env"])
        return Done()

    saved = (ship.subprocess.run, ship.shutil.which, ship.STUBS["claude"])
    had = os.environ.get("BUN_INSPECT")
    ship.subprocess.run = fake_run
    ship.shutil.which = lambda name: "claude"
    ship.STUBS["claude"] = None
    os.environ["BUN_INSPECT"] = "ws://127.0.0.1:9236/"
    try:
        ship.call_child("review", "prompt", ".")
    finally:
        ship.subprocess.run, ship.shutil.which, ship.STUBS["claude"] = saved
        if had is None:
            os.environ.pop("BUN_INSPECT", None)
        else:
            os.environ["BUN_INSPECT"] = had
    return expect(
        "the child's environment has no BUN_INSPECT",
        len(seen) == 1 and "BUN_INSPECT" not in seen[0],
    )


def drill_child_exit_error():
    print("16e. a review child that exits non-zero has the tail of its stderr in the error")
    long_noise = "x" * 2000

    class Done:
        returncode = 1
        stdout = "stdout line"
        stderr = long_noise + "error: Failed to start server. Is port 9236 in use?"

    def fake_run(command, **kwargs):
        return Done()

    saved = (ship.subprocess.run, ship.shutil.which, ship.STUBS["claude"])
    ship.subprocess.run = fake_run
    ship.shutil.which = lambda name: "claude"
    ship.STUBS["claude"] = None
    try:
        try:
            ship.call_child("review", "prompt", ".")
            message = ""
        except ship.ShipError as error:
            message = str(error)
        ok = expect("the error shows the stderr line", "Is port 9236 in use?" in message)
        ok &= expect("the error keeps only the last 800 characters", len(message) < 900)
        Done.stderr = ""
        try:
            ship.call_child("review", "prompt", ".")
            message = ""
        except ship.ShipError as error:
            message = str(error)
        ok &= expect("an empty stderr falls back to stdout", "stdout line" in message)
    finally:
        ship.subprocess.run, ship.shutil.which, ship.STUBS["claude"] = saved
    return ok


def drill_resume_running(root):
    print("22b. a --resume that waits at the gate for a leaf fix is marked running first")
    seen = {}
    saved = (ship.save, ship.take_lock, ship.fix_loop, ship.finish)

    def record_status(run):
        seen["status"] = run["status"]

    ship.save = lambda run: None
    ship.take_lock = record_status
    ship.fix_loop = lambda run, work, finding: "drop"
    ship.finish = lambda run, status, logged=True: status
    try:
        ask = {"id": "R1", "step": "verify", "kind": "defect", "file": "tools/tool.py"}
        run = {
            "id": "r22b",
            "status": "asking",
            "worktree": str(root),
            "asks": [ask],
            "answers": [],
            "findings": [{"id": "R1", "file": "tools/tool.py"}],
        }
        ship.resume(run, ["R1: fix"])
    finally:
        ship.save, ship.take_lock, ship.fix_loop, ship.finish = saved
    return expect(
        "it is no longer asking while it waits, so a second --resume is refused",
        seen.get("status") == "running",
    )


def drill_id_collision(root):
    print("26. a D- or Q- id the range adds that origin/main has with other text stops")
    repo = root / "ids"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    configure(repo)
    base_text = "# Decisions\n\n## D-1 — first\n\ntext\n\n## D-2 — second\n"
    write(repo, {"docs/DECISIONS.md": base_text, "docs/OPEN_QUESTIONS.md": "## Q-1 — q\n"})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    base = git(repo, "rev-parse", "HEAD")

    def after(decisions, questions="## Q-1 — q\n"):
        git(repo, "reset", "-q", "--hard", base)
        write(repo, {"docs/DECISIONS.md": decisions, "docs/OPEN_QUESTIONS.md": questions})
        git(repo, "commit", "-q", "-am", "the change")
        return ship.id_collisions(repo, base)

    ok = expect("a new free id passes", after(base_text + "\n## D-3 — third\n") == [])
    found = after(base_text + "\n## D-2 — other text\n")
    ok &= expect(
        "an id base has with other text stops, naming the id and both headings",
        len(found) == 1
        and found[0][1] == "D-2"
        and found[0][2].endswith("second")
        and found[0][3].endswith("other text"),
    )
    moved = "# Decisions\n\n## D-2 — second\n\n## D-1 — first\n\ntext\n"
    ok &= expect("an id the range re-adds with the same heading passes", after(moved) == [])
    found = after(base_text, "## Q-1 — q\n\n## Q-1 — different\n")
    ok &= expect("a Q- id collides the same way", len(found) == 1 and found[0][1] == "Q-1")
    after(base_text + "\n## D-2 — other text\n")
    asked = []
    saved = ship.fetch, ship.new_ask
    ship.fetch = lambda work: base
    ship.new_ask = lambda run, *args, **kwargs: asked.append(args) or {"kind": args[2]}
    try:
        result = ship.step_rebase({"reviewed": base}, repo)
    finally:
        ship.fetch, ship.new_ask = saved
    ok &= expect(
        "step_rebase itself stops on the collision with an id_collision ask",
        len(asked) == 1 and asked[0][2] == "id_collision" and "D-2" in asked[0][5],
    )
    ok &= expect("and does not pass the rebase step", "pass" not in str(result))
    return ok


def push_race(rejects):
    state = {"tip": "base", "rejects": rejects, "above": set()}
    pushes, rebases = [], []

    class Done:
        def __init__(self, stdout="", returncode=0):
            self.stdout, self.returncode = stdout, returncode

    def fake_git(folder, *args, check=True, env=None, timeout=600):
        if args[0] == "rev-parse":
            return Done("head")
        if args[0] == "ls-remote":
            return Done(state["tip"] + "	refs/heads/main")
        if args[0] == "merge-base":
            return Done(returncode=0 if args[2] == args[3] or args[2] in state["above"] else 1)
        if args[0] == "rev-list":
            return Done("0")
        if args[0] == "push":
            pushes.append(args[2])
            if state["rejects"] > 0:
                state["rejects"] -= 1
                state["tip"] = "other" + str(len(pushes))
                text = " ! [rejected]        head -> main (non-fast-forward)"
                error = ship.ShipError("git push failed: " + text)
                error.full = text
                raise error
            state["tip"] = "head"
            return Done()
        raise AssertionError("unexpected git " + " ".join(args))

    def fake_rebase(run, work):
        rebases.append(state["tip"])
        state["above"].add(state["tip"])
        run["base"] = state["tip"]
        return {"step": "rebase", "status": "pass"}

    names = ("git", "step_rebase", "step_test", "patch_id", "take_lock", "drop_lock", "save")
    saved = [getattr(ship, name) for name in names]
    ship.git = fake_git
    ship.step_rebase = fake_rebase
    ship.step_test = lambda run, work: {"step": "test", "status": "pass"}
    ship.patch_id = lambda work, older, newer: "same"
    ship.take_lock = ship.drop_lock = ship.save = lambda *args: None
    try:
        result = ship.step_push({"reviewed": "head", "base": "base", "steps": []}, ".")
    except ship.ShipError as error:
        result = str(error)
    finally:
        for name, value in zip(names, saved, strict=True):
            setattr(ship, name, value)
    return result, pushes, rebases


def drill_push_race():
    print(
        "27. a push refused because origin/main moved after the look rebases and pushes once more"
    )
    result, pushes, rebases = push_race(1)
    ok = expect(
        "refused once: rebased onto the moved main, pushed again and landed",
        isinstance(result, dict)
        and result.get("status") == "pass"
        and result.get("landed") == "head"
        and len(pushes) == 2
        and rebases == ["other1"],
    )
    result, pushes, rebases = push_race(2)
    ok &= expect(
        "refused twice: the run fails with the refusal, after two pushes",
        isinstance(result, str) and "non-fast-forward" in result and len(pushes) == 2,
    )
    return ok


def main():
    root = Path(tempfile.mkdtemp(prefix="project-drill-ship-"))
    try:
        origin = seed_origin(root)
        ok = drill_pipeline(root, origin)
        ok &= drill_retry_review(root, origin)
        ok &= drill_retry_unproven(root, origin)
        ok &= drill_retry_open_finding(root, origin)
        ok &= drill_sweep(root, root / "confirmed")
        ok &= drill_network_retry()
        ok &= drill_selection(root)
        ok &= drill_push_refusal(root / "exhausted")
        ok &= drill_restore_only_fixer_edits(root / "confirmed")
        ok &= drill_needs_main(root / "not_a_defect")
        ok &= drill_no_drill_message()
        ok &= drill_unpinned_trunk_only()
        ok &= drill_reviewer_paths()
        ok &= drill_drop_subject()
        ok &= drill_child_not_json()
        ok &= drill_child_env()
        ok &= drill_child_exit_error()
        ok &= drill_lock_status(root)
        ok &= drill_resume_running(root)
        ok &= drill_id_collision(root)
        ok &= drill_push_race()
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("ALL PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
