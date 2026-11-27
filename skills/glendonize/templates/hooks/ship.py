# Adapt per repo: set these before the first run; the rest of the file is generic.
#   REMOTE        the push URL of the repo (https://github.com/OWNER/REPO.git).
#   TRUNK         the path prefix whose changes reach the user instead of the fixer ("src/");
#                 leaf_answer() matches it anywhere in a path, so a UI folder holding its own
#                 src/ makes every answer naming it ask: pick a prefix no other folder uses.
#   FRONTEND      the repo's UI folder: a range touching it runs the npm gate and the optional
#                 ui-compare step; set it to a folder that never exists when the repo has no UI.
#   the branch    "main" is written out in fetch(), the ls-remote of step_push (refs/heads/main)
#                 and its git push target (head + ":refs/heads/main"); origin/main in messages.
#   MEMORY_FILES  the agent memory files that select drill_boundaries (AGENTS.md, CLAUDE.md).
#   RUFF          the linter the lint step runs and tests/drill_ruff.py checks; drop the lint
#                 step's ruff calls if the repo has another linter.
#   the CI workflow  "verify.yml" in the gh run list of the ci step.
#   the drill glob   tests/drill_*.py (select_drills, run_one, drops_expects, CI_FAIL, and
#                 mutation_check.drills_naming); the extra drills drill_ruff.py, drill_pyright.py,
#                 drill_boundaries.py in select_drills run only when the file exists.
#   PROJECT_*     the env names (PROJECT_SHIP_STUB, PROJECT_SHIP_TRIES, PROJECT_SHIP_MODEL,
#                 PROJECT_SHIP_CHILD, PROJECT_REVIEW_CHILD, ...); rename to the repo's prefix and
#                 in tests/drill_ship.py.
#   ui-compare    optional: for a range touching FRONTEND the ui_compare() step runs
#                 ~/.claude/skills/ui-compare/ui_compare.py and prints its one-line result; it is
#                 skipped when that skill or the repo's .ui-compare.json is missing, and never
#                 blocks a push.
#   ship_briefs/  review.md, verify.md, fix.md and document.md name the repo's paths and rules;
#                 rewrite them from the target's own AGENTS.md.
#   state folder  .claude/orchestration/ship_runs and ship_log.jsonl in the main checkout (gitignore it).
# Keep the no-mistakes notice below and THIRD_PARTY_NOTICES.md (MIT, Kun Chen).
"""The push pipeline: an agent runs this in the background instead of `git push`.

    python .claude/hooks/ship.py [--intent TEXT | --intent-file F]
    python .claude/hooks/ship.py --resume <run id> --answer "<finding id>: fix|drop|not a defect because ..."
    python .claude/hooks/ship.py --status

Portions ported from no-mistakes, Copyright (c) 2026 Kun Chen, MIT License (the step order of
AllSteps, the fix-and-rerun loop of executeStep, the protected-path refusal, the review-approved
push head, the no-force ls-remote check and the CI polling; THIRD_PARTY_NOTICES.md).

Run from a checkout whose HEAD is ahead of origin/main. The caller's checkout is never edited:
the run adds a detached worktree of its HEAD under the system temp folder and works there, with
the git hooks active. The steps run in this fixed order:

1. intent    --intent text, else the commit subjects, any cited #N (gh issue view, best effort)
             and the heading line of every cited D-xxx. Never blocks.
2. rebase    fetch and rebase onto origin/main. A conflict in src/ asks; a leaf conflict goes
             to the fixer, at most PROJECT_SHIP_TRIES (default 3) times. A D- or Q- heading the
             range adds that origin/main already has with other text asks (renumber).
3. review    one read-only opus child judges the range diff against the intent, bloated drills
             included; findings are defects or questions (questions only go into the record).
             A retry (a fresh ship of a branch whose earlier commits a run already reviewed)
             reads only the commits added since that reviewed commit, here and in verify, when
             the earlier run's record proves it: the reviewed commit is an ancestor of HEAD, its
             patch-id is unchanged by the rebase and that run's verify step closed every finding.
             Anything unproven reads the whole range.
4. verify    one fresh opus child per defect. A leaf defect is fixed only when confirmed, then
             rechecked, at most 3 tries; a refuted one is dropped and logged. A src/ defect is
             asked with the verdict and evidence attached as advice, never hidden.
5. test      the targeted drills (changed drills, the drills mutation_check.drills_naming
             selects for a changed file, 
             drill_ruff, drill_pyright when a .py changed, drill_boundaries when a .md, AGENTS.md
             or CLAUDE.md changed), then the rest of the gate before anything is pushed: the
             per-commit rule "every src/ change carries a drill" (python tests/commit_range.py,
             and, for a range touching frontend/, npm ci, npm run lint, build and test:ui
             with C:/Program Files/nodejs on PATH. The full python tests/run_drills.py run is
             not made here: GitHub Actions runs it for the pushed commit. Then the
             revert-and-rerun of mutation_check.py
             for a src/ .py change, except a file whose change leaves every statement as it was
             (comments, docstrings and layout: the syntax trees without docstrings are equal),
             which is skipped and recorded as comment_only. A red drill or frontend command goes to the fixer when the
             range is leaf only; with a src/ change in the range it asks, as does an unpinned
             src/ file and any commit_range finding (only a new commit can repair a commit's
             shape). The fixer and the ask get the drill's name, every line of its whole output
             that holds FAIL, then the tail, so a long log no longer cuts the failing expect off.
6. document  one read-only child names the owner note of each stale fact; a leaf gap goes to the
             fixer once, anything else is logged. A gap under .claude/, which the fixer cannot
             edit, and a gap the fixer left unchanged print "not applied: <file>" and are
             recorded as not_applied.
7. lint      ruff format and ruff check --fix on the changed .py files outside src/, then
             drill_ruff; a src/ lint failure asks, a leaf one goes to the fixer.
8. push      only a HEAD that descends from the reviewed commit, never forced; when origin/main
             moved, rebase once more and test again first, for at most MAIN_MOVES (3) moves;
             a fourth fails the run with the count. When the rebase changed the reviewed diff
             (patch-id), review and verify run again on the rebased range before that test.
             A push refused as non-fast-forward or "fetch first" (origin/main moved after the
             look) takes that rebase path PUSH_RACES (1) more time; a second refusal fails.
9. ci        poll verify.yml for the pushed commit, which runs every drill (the step's result
             says gate "ci"); a red leaf run goes to the fixer and steps 5-8 again; a red drill
             that step 5 did not select is logged as selection_miss. A run GitHub never started
             (no run for the commit, a run without jobs or whose jobs have no steps; never read
             from the log text) has the reason "CI not started (GitHub Actions minutes or
             billing)" and the full python tests/run_drills.py run is made here on the pushed
             commit instead, through the memory gate: green is the ci step's pass (gate "local",
             with the reason), red is handled like a red CI run. A started run still going when
             PROJECT_SHIP_CI_TIMEOUT ends takes the same way (reason "CI did not finish in time"). A commit can reach main before
             the full suite is green; a red result is fixed after landing.

Review through test, every retest after a rebase and the fixes of a --resume pass a memory
gate: a run enters while fewer than PROJECT_SHIP_SLOTS (3) runs are inside and more than
PROJECT_SHIP_MIN_FREE_GB (6) of physical memory is free, holding a slot file in ship_slots/ of the
main checkout's .claude/orchestration. A run that waits prints and records "waiting: <n> runs
inside, <x> GB free" (--status shows it) and checks again every 30 s; a slot whose holder
process is gone is taken over.

After every fixer call any src/ path the fixer changed is restored and the user is asked. The
fixer may also answer "not a defect because ...": on a leaf problem the change is dropped, with no
ask and no ship_log line, except in the document step, where the run goes on to lint; an
answer with needs_main set or naming src/ still asks. Fix commits are normal commits, subject
`ship: <step> fix - <summary>`.

Every git fetch is tried 3 times, with a growing pause (PROJECT_SHIP_RETRY_PAUSE, 5 s), when it
fails on DNS or a connection, not on authentication; the push is tried 3 times when the server
fails it ("remote: fatal error", "remote rejected" without "non-fast-forward"). A run that failed
at the push keeps its tree, and --resume <run id> with no answer restarts it at the push step.

Exit 0: landed and CI green (or nothing to push). Exit 2: asks the user in
.claude/orchestration/ship_runs/<run id>.ask.md, worktree kept, continue with --resume. Exit 3:
nothing landed after 3 tries, or the user's answer hands the change back to the session, or CI
stayed red, all logged; or the fixer answered "not a defect" on a leaf problem before the push,
not logged (in the CI step the change has landed, so the run ends as landed with CI red, logged);
the worktree is removed; a hand-back first prints the SHAs of the run's own fix commits
(cherry-pick them, oldest first), which are otherwise lost with the tree, and keeps them in the
record as kept_commits. Exit 1: the pipeline itself failed, worktree kept.

The run record .claude/orchestration/ship_runs/<run id>.json of the main checkout is written after
every step, and every finished or stopped run adds one line to
.claude/orchestration/ship_log.jsonl, except a leaf "not a defect" drop before the push.
A run cut off with its session is not resumed; --status prints one line per such run, and first
removes the ship tree of every run that is no longer running (one that ended with its tree left,
one whose process is gone); an asking or failed run keeps its tree.

PROJECT_SHIP_STUB=<json file> {"review": [...], "verify": [...], "fix": [...], "document": [...]}
replaces every claude child with the next answer of its role (a fix answer may carry
"write": {path: text}, written into the worktree); PROJECT_SHIP_GH_STUB=<json file>
{"run list": [...], "run view": [...], "issue view": [...]} replaces gh, the last answer of a
key repeating. PROJECT_SHIP_REMOTE, PROJECT_SHIP_STATE, PROJECT_SHIP_CI_POLL, PROJECT_SHIP_CI_TIMEOUT,
PROJECT_SHIP_TRIES, PROJECT_SHIP_LOCK_POLL, PROJECT_SHIP_FREE_GB_FILE and PROJECT_SHIP_MODEL move the remote,
the record and slot folder and the limits for the drill (tests/drill_ship.py); PROJECT_SHIP_FRONTEND, a JSON list of
argument lists, replaces the npm commands of the frontend gate; PROJECT_SHIP_UI_COMPARE and
PROJECT_SHIP_UI_COMPARE_TIMEOUT replace the ui-compare skill script and its time limit.

"""

import argparse
import ast
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOK_DIR))

import mutation_check

BRIEFS = HOOK_DIR / "ship_briefs"
RUFF = [sys.executable, "-m", "ruff"]
REMOTE = "https://github.com/OWNER/REPO.git"
STEPS = ("intent", "rebase", "review", "verify", "test", "document", "lint", "push", "ci")
TRUNK = "src/"
MEMORY_FILES = ("AGENTS.md", "CLAUDE.md")
READ_TOOLS = "Read,Grep,Glob"
READ_DENIED = "Bash,PowerShell,Edit,Write,NotebookEdit,WebFetch,WebSearch"
FIX_TOOLS = "Read,Grep,Glob,Edit,Write"
FIX_DENIED = "Bash,PowerShell,NotebookEdit,WebFetch,WebSearch"
OUTPUT_TAIL = 6000
LONG_LINE = 2000
LONG_LINE_KEPT = 200
FINISHED = ("landed", "empty", "dropped", "handed_back", "landed_ci_red")
EXIT_CODES = {
    "landed": 0,
    "empty": 0,
    "failed": 1,
    "asking": 2,
    "dropped": 3,
    "handed_back": 3,
    "landed_ci_red": 3,
}
SHA = re.compile(r"[0-9a-f]{40}")
ANSWER = re.compile(r"^\s*([A-Z]+\d+)\s*:\s*(.+?)\s*$", re.DOTALL)
CI_FAIL = re.compile(r"FAIL\s+(drill_\w+\.py)")
DRILL_FAIL = re.compile(r"^FAIL\s+(drill_\w+\.py)", re.MULTILINE)
GH_STAMP = re.compile(r"\d{4}-\d\d-\d\dT[\d:.]+Z$")
DRILLS_FAILED = re.compile(r"^FAILED: (.+)$", re.MULTILINE)
NET_TRIES = 3
AUTH_FAILED = re.compile(
    r"authentication failed|could not read (?:username|password)|permission denied"
    r"|invalid username|repository not found|returned error: 40[13]",
    re.IGNORECASE,
)
NETWORK_FAILED = re.compile(
    r"could not resolve host|temporary failure in name resolution|name or service not known"
    r"|connection (?:timed out|reset|refused)|timed out|failed to connect|unable to access"
    r"|early eof|rpc failed|remote end hung up|network is unreachable",
    re.IGNORECASE,
)
NOT_STARTED_REASON = "CI not started (GitHub Actions minutes or billing)"
TIMED_OUT_REASON = "CI did not finish in time (PROJECT_SHIP_CI_TIMEOUT)"
NODE_DIR = r"C:\Program Files\nodejs"
FRONTEND = "frontend/"
GATE_SECONDS = 1800
UI_COMPARE_SECONDS = 600
HEAVY = ("review", "verify", "test")
SLOTS_DIR = "ship_slots"
SLOTS = 3
MIN_FREE_GB = 6.0
LOCK: dict[str, str | None] = {"path": None, "run": None}
MAIN_MOVES = 3
PUSH_RACES = 1
STUBS: dict[str, dict | None] = {"claude": None, "gh": None}


class ShipError(Exception):
    full = ""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def limit(name, default):
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return default


def tries():
    return limit("PROJECT_SHIP_TRIES", 3)


def remote():
    return os.environ.get("PROJECT_SHIP_REMOTE") or REMOTE


def repo_path(work, path):
    path = str(path).strip().replace("\\", "/")
    top = str(work).replace("\\", "/").rstrip("/") + "/"
    if path.lower().startswith(top.lower()):
        path = path[len(top) :]
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


def is_trunk(path):
    return str(path).replace("\\", "/").startswith(TRUNK)


def fixer_can_edit(path):
    return not str(path).replace("\\", "/").startswith(".claude/")


def leaf_ask(ask):
    return (
        ask["step"] == "verify"
        and ask["kind"] not in ("main_defect", "hook_defect")
        and not is_trunk(ask["file"])
        and fixer_can_edit(ask["file"])
    )


def git(folder, *args, check=True, env=None, timeout=600):
    done = subprocess.run(
        ["git", *args],
        cwd=folder,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=timeout,
    )
    if check and done.returncode != 0:
        detail = (done.stderr or done.stdout).strip()
        error = ShipError("git " + " ".join(args[:3]) + " failed: " + detail[:400])
        error.full = detail
        raise error
    return done


def transient_network(text):
    return NETWORK_FAILED.search(text) is not None and AUTH_FAILED.search(text) is None


def server_rejected(text):
    lowered = text.lower()
    if main_moved(text):
        return False
    return "remote: fatal error" in lowered or "remote rejected" in lowered


def main_moved(text):
    lowered = text.lower()
    return "non-fast-forward" in lowered or "fetch first" in lowered


def git_retrying(folder, *args, again, timeout=600):
    pause = float(os.environ.get("PROJECT_SHIP_RETRY_PAUSE") or 5)
    for attempt in range(1, NET_TRIES + 1):
        try:
            return git(folder, *args, timeout=timeout)
        except ShipError as error:
            if attempt == NET_TRIES or not again(error.full or str(error)):
                raise
            print(
                "ship: " + str(error)[:200] + "; try " + str(attempt + 1) + " of " + str(NET_TRIES)
            )
            time.sleep(pause * attempt)
    raise ShipError("git " + " ".join(args[:3]) + " was not tried")


def out(folder, *args):
    return git(folder, *args).stdout.strip()


def lines(text):
    found = []
    for line in text.splitlines():
        if line.strip():
            found.append(line.strip())
    return found


def is_ancestor(folder, older, newer):
    return git(folder, "merge-base", "--is-ancestor", older, newer, check=False).returncode == 0


def fetch(work):
    git_retrying(work, "fetch", remote(), "main", again=transient_network)
    return out(work, "rev-parse", "FETCH_HEAD")


def range_diff(run, work, binary=False, start=None):
    args = ["diff", "--no-color", "--no-ext-diff"]
    if binary:
        args.append("--binary")
    done = subprocess.run(
        ["git", *args, start or run["base"], "HEAD"], cwd=work, capture_output=True, timeout=600
    )
    if done.returncode != 0:
        raise ShipError("git diff failed: " + done.stderr.decode("utf-8", errors="replace")[:400])
    return done.stdout.decode("utf-8", errors="replace")


def changed_paths(run, work):
    return lines(out(work, "diff", "--name-only", run["base"], "HEAD"))


def subjects(run, work):
    return lines(out(work, "log", "--reverse", "--format=%s", run["base"] + "..HEAD"))


def gh(args, folder):
    stub = STUBS["gh"]
    if stub is not None:
        key = args[0] + " " + args[1]
        answers = stub.get(key)
        if not answers:
            raise ShipError("no gh stub answer for " + key)
        answer = answers.pop(0) if len(answers) > 1 else answers[0]
        if isinstance(answer, dict) and "gh_error" in answer:
            raise ShipError("gh " + key + " failed: " + answer["gh_error"])
        return answer if isinstance(answer, str) else json.dumps(answer)
    exe = shutil.which("gh")
    if exe is None:
        raise ShipError("the gh CLI is not on PATH")
    command = [exe, *args]
    slug = re.search(r"github\.com[/:]([^/]+/[^/]+?)(?:\.git)?$", remote())
    if slug:
        command += ["-R", slug.group(1)]
    done = subprocess.run(
        command,
        cwd=folder,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if done.returncode != 0:
        raise ShipError("gh " + " ".join(args[:2]) + " failed: " + done.stderr.strip()[:300])
    return done.stdout


def parse_answer(text):
    text = text.strip()
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1).strip())
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except ValueError:
            continue
    raise ShipError("a child's answer is not JSON: " + json.dumps(text[:300]))


def call_child(role, prompt, work):
    stub = STUBS["claude"]
    if stub is not None:
        answers = stub.get(role)
        if not answers:
            raise ShipError("no stub answer left for " + role)
        answer = dict(answers.pop(0))
        for relative, text in (answer.pop("write", None) or {}).items():
            path = Path(work) / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return answer
    exe = shutil.which("claude")
    if exe is None:
        raise ShipError("the claude CLI is not on PATH")
    fixer = role == "fix"
    command = [
        exe,
        "-p",
        "--model",
        os.environ.get("PROJECT_SHIP_MODEL") or "opus",
        "--output-format",
        "json",
        "--allowedTools",
        FIX_TOOLS if fixer else READ_TOOLS,
        "--disallowedTools",
        FIX_DENIED if fixer else READ_DENIED,
        "--permission-mode",
        "dontAsk",
        "--no-session-persistence",
    ]
    env = dict(os.environ)
    env.pop("BUN_INSPECT", None)
    env["PROJECT_REVIEW_CHILD"] = "1"
    env["PROJECT_SHIP_CHILD"] = "1"
    timeout = limit("PROJECT_SHIP_CHILD_TIMEOUT", 900)
    for attempt in (1, 2):
        try:
            return child_answer(role, command, prompt, timeout, env, work)
        except ShipError as error:
            if attempt == 2 or fixer or "not JSON" not in str(error):
                raise
            print("ship: " + role + " child answered without JSON, asking again: " + str(error))
    raise ShipError(role + " child gave no answer")


def child_answer(role, command, prompt, timeout, env, work):
    try:
        done = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            cwd=work,
        )
    except subprocess.TimeoutExpired:
        raise ShipError(role + " child timed out after " + str(timeout) + " s")
    if done.returncode != 0:
        shown = (done.stderr or done.stdout or "").strip()[-800:]
        raise ShipError(role + " child exited " + str(done.returncode) + ": " + shown)
    try:
        outer = json.loads(done.stdout)
    except ValueError:
        raise ShipError(role + " child printed no JSON")
    if (
        not isinstance(outer, dict)
        or outer.get("is_error")
        or not isinstance(outer.get("result"), str)
    ):
        raise ShipError(role + " child returned an error result")
    answer = parse_answer(outer["result"])
    if not isinstance(answer, dict):
        raise ShipError(role + " child's answer is not a JSON object")
    return answer


def brief(name):
    return (BRIEFS / name).read_text(encoding="utf-8")


def context(run, work, diff=True, start=None):
    text = "\n\nIntent:\n" + (run.get("intent") or "(none given)") + "\n"
    text += "\nBase commit: " + (start or run["base"]) + "\nTarget commit: the worktree's HEAD\n"
    if start:
        text += "\nThe commits up to the base commit were reviewed by run "
        text += str((run.get("prior") or {}).get("run")) + "; this range is only what came after.\n"
    text += "\nChanged files:\n"
    whole = range_diff(run, work, start=start)
    for path, _section in mutation_check.split_sections(whole):
        text += "- " + path + "\n"
    if diff:
        text += "\nRange diff:\n```diff\n" + shortened(whole) + "\n```\n"
    return text


def shortened(diff):
    kept = []
    for line in diff.split("\n"):
        if len(line) > LONG_LINE:
            cut = str(len(line) - LONG_LINE_KEPT)
            line = line[:LONG_LINE_KEPT] + " [" + cut + " characters shortened for the review]"
        kept.append(line)
    return "\n".join(kept)


def tail(text):
    return text[-OUTPUT_TAIL:]


def fail_lines(text):
    found = []
    for line in text.splitlines():
        body = line.rsplit("\t", 1)[-1].strip()
        words = body.split(None, 1)
        if words and GH_STAMP.match(words[0]):
            body = words[1] if len(words) > 1 else ""
        if body == "ok" or body.startswith("ok "):
            continue
        if "FAIL" in line:
            found.append(line.strip()[:400])
    return found


def with_fails(fails, shown, name):
    if not fails:
        return shown
    text = "FAIL lines of " + name + ":\n" + "\n".join(fails)
    return text + "\n\nEnd of its output:\n" + shown


def state_dir(caller):
    if os.environ.get("PROJECT_SHIP_STATE"):
        return Path(os.environ["PROJECT_SHIP_STATE"])
    common = out(caller, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common).parent / ".claude" / "orchestration"


def runs_dir(run):
    return Path(run["state"]) / "ship_runs"


def save(run):
    folder = runs_dir(run)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (run["id"] + ".json")).write_text(json.dumps(run, indent=1), encoding="utf-8")


def pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return kernel.GetLastError() == 5
        code = ctypes.c_ulong()
        try:
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def lock_holder(path):
    try:
        holder = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {}
    return holder if isinstance(holder, dict) else {}


def create_lock(path, run):
    text = json.dumps({"pid": os.getpid(), "run": run["id"], "at": now()})
    spare = Path(str(path) + "." + uuid.uuid4().hex[:8] + ".new")
    spare.write_text(text, encoding="utf-8")
    try:
        os.link(spare, path)
        return True
    except FileExistsError:
        return False
    finally:
        spare.unlink(missing_ok=True)


def take_over(path, holder):
    aside = Path(str(path) + "." + uuid.uuid4().hex[:8] + ".stale")
    try:
        os.rename(path, aside)
    except OSError:
        return
    if lock_holder(aside) != holder:
        try:
            os.link(aside, path)
        except OSError:
            pass
    aside.unlink(missing_ok=True)


def free_gb():
    stub = os.environ.get("PROJECT_SHIP_FREE_GB_FILE")
    if stub:
        try:
            return float(Path(stub).read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None
    if sys.platform == "win32":
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return status.ullAvailPhys / 2**30
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 2**20
    except (OSError, ValueError, IndexError):
        return None
    return None


def claim(path, run):
    if create_lock(path, run):
        return True
    holder = lock_holder(path)
    if holder is None:
        return create_lock(path, run)
    if not holder:
        try:
            old = time.time() - path.stat().st_mtime > 60
        except OSError:
            old = False
        if not old:
            return False
    elif pid_alive(holder.get("pid")):
        return False
    else:
        print("ship: took over the slot of run " + str(holder.get("run")) + " (process gone)")
    take_over(path, holder)
    return create_lock(path, run)


def inside(folder):
    count = 0
    for path in folder.glob("slot-*.lock"):
        holder = lock_holder(path)
        if holder and pid_alive(holder.get("pid")):
            count += 1
    return count


def take_lock(run):
    if LOCK["run"] == run["id"]:
        return
    folder = Path(run["state"]) / SLOTS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    slots = max(1, limit("PROJECT_SHIP_SLOTS", SLOTS))
    try:
        floor = float(os.environ.get("PROJECT_SHIP_MIN_FREE_GB") or MIN_FREE_GB)
    except ValueError:
        floor = MIN_FREE_GB
    pause = float(os.environ.get("PROJECT_SHIP_LOCK_POLL") or 30)
    while True:
        free = free_gb()
        if free is None or free > floor or inside(folder) == 0:
            for number in range(slots):
                path = folder / ("slot-" + str(number) + ".lock")
                if claim(path, run):
                    LOCK["path"] = str(path)
                    LOCK["run"] = run["id"]
                    if run.get("waiting"):
                        run.setdefault("waited", []).append(run.pop("waiting"))
                        save(run)
                    return
        shown = "unknown" if free is None else format(free, ".1f")
        text = "waiting: " + str(inside(folder)) + " runs inside, " + shown + " GB free"
        if run.get("waiting") != text:
            run["waiting"] = text
            run["pid"] = os.getpid()
            save(run)
            print("ship: " + text, flush=True)
        time.sleep(pause)


def drop_lock():
    if not LOCK["path"]:
        return
    path = Path(LOCK["path"])
    holder = lock_holder(path)
    if holder and holder.get("run") == LOCK["run"] and holder.get("pid") == os.getpid():
        path.unlink(missing_ok=True)
    LOCK["path"] = None
    LOCK["run"] = None


def locked(run, function, work):
    take_lock(run)
    try:
        return function(run, work)
    finally:
        drop_lock()


def log_line(run, entry):
    path = Path(run["state"]) / "ship_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def outcome(step, status, started, findings=None, attempts=0, **extra):
    result = {
        "step": step,
        "status": status,
        "findings": findings or [],
        "attempts": attempts,
        "seconds": round(time.monotonic() - started, 2),
    }
    result.update(extra)
    return result


def new_ask(run, prefix, step, kind, path, line, claim, verdict=None, evidence=""):
    run["ask_seq"] = run.get("ask_seq", 0) + 1
    return {
        "id": prefix + str(run["ask_seq"]),
        "step": step,
        "kind": kind,
        "file": path,
        "line": line,
        "claim": claim,
        "verdict": verdict,
        "evidence": evidence,
    }


def verdict_words(verdict):
    if verdict.get("confirmed"):
        return "confirmed"
    if verdict.get("said") is True:
        return "confirmed without evidence (counts as not confirmed)"
    return "refuted"


def finding_ask(finding, kind, note=""):
    verdict = finding.get("verdict") or {}
    return {
        "id": finding["id"],
        "step": "verify",
        "kind": kind,
        "file": finding["file"],
        "line": finding["line"],
        "claim": finding["claim"] + (" [" + note + "]" if note else ""),
        "verdict": verdict_words(verdict),
        "evidence": verdict.get("evidence", ""),
    }


KIND_WORDS = {
    "main_defect": "a reviewer finding on src/ (the verdict is advice only)",
    "fixer_main": "the fixer changed src/; those paths were restored",
    "fixer_not_a_defect": "the fixer answered that this is not a defect",
    "hook_defect": "a confirmed finding under .claude/, which the fixer cannot edit",
    "rebase_conflict": "the rebase onto origin/main conflicts in src/",
    "id_collision": "the change adds a D- or Q- id that origin/main already has with other text",
    "test_red": "a drill naming a changed src/ file is red",
    "unpinned": "the revert-and-rerun found a src/ change no drill pins",
    "lint_main": "ruff fails on a changed src/ file",
    "ci_red": "CI is red and the cause may be in src/",
    "commit_range": "a commit breaks the per-commit drill rule",
}


def option_lines(ask):
    if ask["step"] == "rebase":
        return (
            "  - any answer: the run hands the change back; nothing can be pushed from this HEAD\n"
        )
    if ask["step"] == "ci":
        lines = "  - fix: the run ends handed back; the commit is already on origin/main with CI "
        lines += "red, the session fixes it and ships a new commit\n"
        lines += "  - not a defect because ... / drop: the run ends; the commit is already on "
        lines += "origin/main and stays as it is\n"
        return lines
    if leaf_ask(ask):
        fix = "the pipeline's fixer repairs it (up to 3 tries); if all 3 fail or the fixer "
        fix += "answers not a defect, the change is dropped and nothing is pushed; if the fixer "
        fix += "touches or names src/, the run asks again"
    else:
        fix = "the run stops and hands the change back, whatever the other answers say; the "
        fix += "session fixes it and ships again"
    lines = "  - fix: " + fix + "\n"
    lines += "  - not a defect because ...: the finding is dismissed with your reason\n"
    lines += "  - drop: the finding is dismissed without a reason "
    lines += "(drop does NOT throw the change away)\n"
    lines += "  - then: once every finding is answered and none stops the run, it goes on from "
    lines += "the next step towards the push; that step can still ask, fail or drop\n"
    return lines


def write_ask(run):
    text = "# ship run " + run["id"] + " asks the user\n\n"
    text += "Commit " + out(run["worktree"], "rev-parse", "HEAD") + ", worktree " + run["worktree"]
    text += ", stopped after " + run["last_step"] + ".\n\n"
    for ask in run["asks"]:
        text += "## " + ask["id"] + ": " + KIND_WORDS.get(ask["kind"], ask["kind"]) + "\n\n"
        text += "- where: " + str(ask["file"]) + ":" + str(ask["line"]) + "\n"
        text += "- finding: " + str(ask["claim"]) + "\n"
        if ask.get("verdict"):
            text += "- verifier verdict: " + ask["verdict"] + "\n"
        if ask.get("evidence"):
            text += "- evidence: " + str(ask["evidence"]) + "\n"
        text += "- options:\n" + option_lines(ask) + "\n"
    text += "Answer with:\n\n    python .claude/hooks/ship.py --resume " + run["id"]
    text += ' --answer "<id>: fix|drop|not a defect because ..."\n'
    path = runs_dir(run) / (run["id"] + ".ask.md")
    path.write_text(text, encoding="utf-8")
    return path


def remove_worktree(run):
    work = run.get("worktree")
    if not work:
        return
    caller = run.get("caller")
    if caller and Path(caller).is_dir():
        try:
            git(caller, "worktree", "remove", "--force", work, check=False)
        except OSError:
            pass
    shutil.rmtree(Path(work).parent, ignore_errors=True)


def fixer_commits(run):
    since = run.get("landed") or run.get("base")
    if not since or not run.get("worktree"):
        return []
    try:
        text = out(
            run["worktree"],
            "log",
            "--reverse",
            "--format=%H %s",
            "--grep",
            "^Ship-Run: " + str(run.get("id")),
            since + "..HEAD",
        )
    except (ShipError, OSError, TypeError):
        return []
    return lines(text)


def sweep(folder):
    swept = []
    for path in sorted((Path(folder) / "ship_runs").glob("*.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        work = run.get("worktree")
        if not work or not run.get("caller") or not Path(work).exists():
            continue
        if not Path(work).parent.name.startswith("project-ship-"):
            continue
        state = run.get("status")
        pid = run.get("pid")
        cut_off = state == "running" and isinstance(pid, int) and not pid_alive(pid)
        if cut_off:
            kept = fixer_commits(run)
            if kept:
                run["kept_commits"] = kept
                path.write_text(json.dumps(run, indent=1), encoding="utf-8")
                print(
                    "ship: run "
                    + str(run.get("id"))
                    + " was cut off with fix commits not on any branch; its tree stays at "
                    + str(work)
                    + "; cherry-pick, oldest first:"
                )
                for line in kept:
                    sha, _space, subject = line.partition(" ")
                    print("  git cherry-pick " + sha + "  # " + subject)
                continue
        if state in FINISHED or cut_off:
            remove_worktree(run)
            swept.append(str(run.get("id")) + " (" + str(state) + ")")
    return swept


def finish(run, status, logged=True):
    drop_lock()
    run["status"] = status
    run["finished"] = now()
    if status == "handed_back":
        run["kept_commits"] = fixer_commits(run)
        if run["kept_commits"]:
            print("ship: the fixer's commits are not on your branch; cherry-pick, oldest first:")
            for kept in run["kept_commits"]:
                sha, _space, subject = kept.partition(" ")
                print("  git cherry-pick " + sha + "  # " + subject)
    save(run)
    if status == "asking":
        print("ship asks: " + str(write_ask(run)))
    if status in FINISHED:
        remove_worktree(run)
    entry = {
        "kind": "run",
        "run": run["id"],
        "status": status,
        "at": run["finished"],
        "head": run["head"],
        "landed": run.get("landed"),
        "steps": [],
        "error": run.get("error"),
    }
    for step in run["steps"]:
        entry["steps"].append([step["step"], step["status"], step["attempts"]])
    if logged:
        log_line(run, entry)
    print("ship run " + run["id"] + ": " + status)
    return EXIT_CODES[status]


def porcelain(work):
    text = git(
        work, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames"
    ).stdout
    paths = []
    for record in text.split("\0"):
        if len(record) > 3:
            paths.append(record[3:])
    return paths


def read_bytes(work, path):
    try:
        return Path(work, path).read_bytes()
    except OSError:
        return None


def trunk_snapshot(work):
    snapshot = {}
    for path in porcelain(work):
        if is_trunk(path):
            snapshot[path] = read_bytes(work, path)
    return snapshot


def restore_trunk(work, snapshot):
    restored = []
    for path in porcelain(work):
        if not is_trunk(path):
            continue
        if path in snapshot:
            before = snapshot[path]
            if read_bytes(work, path) == before:
                continue
            if before is None:
                Path(work, path).unlink(missing_ok=True)
            else:
                Path(work, path).write_bytes(before)
        elif git(work, "cat-file", "-e", "HEAD:" + path, check=False).returncode == 0:
            git(work, "checkout", "HEAD", "--", path)
        else:
            git(work, "rm", "--cached", "-q", "--", path, check=False)
            Path(work, path).unlink(missing_ok=True)
        restored.append(path)
    return restored


def fixer(run, work, step, problem):
    prompt = brief("fix.md") + "\n\nStep: " + step + "\n\nProblem:\n" + problem
    prompt += context(run, work, diff=False)
    snapshot = trunk_snapshot(work)
    answer = call_child("fix", prompt, work)
    summary = " ".join(str(answer.get("summary") or "agent fix").split())[:80]
    reason = str(answer.get("not_a_defect") or "").strip()
    if answer.get("needs_main") is True:
        reason = "the fix needs src/: " + (reason or "(no reason given)")
    restored = restore_trunk(work, snapshot)
    if (restored or reason) and step != "rebase":
        git(work, "reset", "-q", "--hard", "HEAD")
        git(work, "clean", "-fdq")
    return summary, reason, restored


def leaf_answer(reason):
    if not reason:
        return False
    return re.search(r"(?<![\w-])src/", reason.replace("\\", "/")) is None


def dropped(step, started, reason, attempts=0):
    return outcome(step, "drop", started, attempts=attempts, not_a_defect=reason)


def drops_expects(diff):
    for path, text in mutation_check.split_sections(diff):
        if not path.startswith("tests/drill_"):
            continue
        net = 0
        for line in text.splitlines():
            if line.startswith(("+++", "---")) or "expect(" not in line:
                continue
            if line.startswith("-"):
                net -= 1
            elif line.startswith("+"):
                net += 1
        if net < 0:
            return True
    return False


def commit_fix(run, work, step, summary, dropped_because=""):
    git(work, "add", "-A")
    paths = lines(out(work, "diff", "--cached", "--name-only"))
    if not paths:
        return None
    staged = subprocess.run(
        ["git", "diff", "--cached", "--binary", "--no-color", "--no-ext-diff"],
        cwd=work,
        capture_output=True,
        check=True,
    ).stdout
    if drops_expects(staged.decode("utf-8", "replace")):
        if not dropped_because:
            git(work, "reset", "-q", "--hard", "HEAD")
            git(work, "clean", "-fdq")
            return None
        summary = "drop drill: " + dropped_because
    message = "ship: " + step + " fix - " + summary + "\n\nShip-Run: " + run["id"]
    handle, name = tempfile.mkstemp(prefix="project-ship-msg-", suffix=".txt")
    os.close(handle)
    try:
        Path(name).write_text(message + "\n", encoding="utf-8")
        git(work, "commit", "-q", "-F", name)
    finally:
        Path(name).unlink(missing_ok=True)
    return True


def step_intent(run, work):
    started = time.monotonic()
    if run.get("intent_arg"):
        run["intent"] = run["intent_arg"]
        return outcome("intent", "pass", started, source="argument")
    parts = []
    issues = []
    decisions = []
    for subject in subjects(run, work):
        parts.append("- " + subject)
        for number in re.findall(r"(?<![\w&])#(\d+)\b", subject):
            if number not in issues:
                issues.append(number)
        for found in re.findall(r"\bD-\d{3}\b", subject):
            if found not in decisions:
                decisions.append(found)
    text = "Commit subjects:\n" + "\n".join(parts)
    for number in issues:
        try:
            shown = json.loads(gh(["issue", "view", number, "--json", "title,body"], work))
            text += "\n\nIssue #" + number + ": " + str(shown.get("title"))
            text += "\n" + str(shown.get("body") or "")[:2000]
        except (ShipError, ValueError, AttributeError, OSError, subprocess.SubprocessError):
            continue
    register = Path(work) / "notes" / "DECISIONS.md"
    if decisions and register.is_file():
        for line in register.read_text(encoding="utf-8").splitlines():
            for found in decisions:
                if line.startswith("## " + found + " "):
                    text += "\n\n" + line[:800]
    run["intent"] = text
    return outcome("intent", "pass", started, source="commits")


def conflict_markers(work, paths):
    for path in paths:
        try:
            text = Path(work, path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "<<<<<<<" in text or ">>>>>>>" in text:
            return True
    return False


ID_FILES = ("docs/DECISIONS.md", "docs/OPEN_QUESTIONS.md")


def heading_ids(text):
    found = {}
    for line in text.splitlines():
        match = re.match(r"##\s+([DQ]-\d+)\b", line)
        if match:
            found[match.group(1)] = line.strip()
    return found


def id_collisions(work, base):
    found = []
    for path in ID_FILES:
        before = git(work, "show", base + ":" + path, check=False)
        if before.returncode != 0:
            continue
        old = heading_ids(before.stdout)
        added = out(work, "diff", "-U0", base + "..HEAD", "--", path)
        for line in added.splitlines():
            if not line.startswith("+##"):
                continue
            for ident, heading in heading_ids(line[1:]).items():
                if ident in old and old[ident] != heading:
                    found.append((path, ident, old[ident], heading))
    return found


def earlier_review(run, work):
    best = None
    for path in sorted(runs_dir(run).glob("*.json")):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(entry, dict) or entry.get("id") == run["id"]:
            continue
        closed = False
        for step in entry.get("steps") or []:
            if isinstance(step, dict) and step.get("step") == "verify":
                closed = step.get("status") in ("pass", "fixed", "skip")
        if not closed:
            continue
        reviewed = entry.get("reviewed")
        base = entry.get("base")
        if not (isinstance(reviewed, str) and isinstance(base, str)):
            continue
        if not (SHA.fullmatch(reviewed) and SHA.fullmatch(base)):
            continue
        if not is_ancestor(work, reviewed, run["head"]) or is_ancestor(work, reviewed, run["base"]):
            continue
        if best is None or is_ancestor(work, best["reviewed"], reviewed):
            best = {"run": entry.get("id"), "reviewed": reviewed, "base": base}
    if best is not None:
        best["after"] = int(out(work, "rev-list", "--count", best["reviewed"] + "..HEAD"))
        if best["after"] == 0:
            return None
    return best


def prove_earlier_review(run, work):
    prior = run.get("prior")
    if not prior:
        return
    try:
        twin = out(work, "rev-parse", "HEAD~" + str(prior["after"]))
        before = patch_id(work, prior["base"], prior["reviewed"])
        after = patch_id(work, run["base"], twin)
    except ShipError:
        return
    if before and before == after:
        run["since"] = twin


def step_rebase(run, work):
    started = time.monotonic()
    first = run.get("reviewed") is None and "prior" not in run
    base = fetch(work)
    if first:
        run["prior"] = earlier_review(run, work)
    env = dict(os.environ)
    env["GIT_EDITOR"] = "true"
    attempts = 0
    done = git(work, "rebase", base, check=False, env=env)
    while done.returncode != 0:
        conflicted = lines(out(work, "diff", "--name-only", "--diff-filter=U"))
        if not conflicted:
            git(work, "rebase", "--abort", check=False)
            raise ShipError("git rebase failed: " + (done.stderr or done.stdout).strip()[:300])
        trunk = []
        for path in conflicted:
            if is_trunk(path):
                trunk.append(path)
        if trunk:
            git(work, "rebase", "--abort", check=False)
            ask = new_ask(
                run,
                "B",
                "rebase",
                "rebase_conflict",
                trunk[0],
                0,
                "conflicted: " + ", ".join(trunk),
            )
            return outcome("rebase", "ask", started, attempts=attempts, asks=[ask])
        if attempts >= tries():
            git(work, "rebase", "--abort", check=False)
            return outcome("rebase", "fail", started, attempts=attempts)
        attempts += 1
        problem = "A rebase onto origin/main stopped on conflicts in: " + ", ".join(conflicted)
        _summary, reason, restored = fixer(run, work, "rebase", problem)
        if not restored and leaf_answer(reason):
            git(work, "rebase", "--abort", check=False)
            return dropped("rebase", started, reason, attempts)
        if restored or reason:
            git(work, "rebase", "--abort", check=False)
            kind = "fixer_main" if restored else "fixer_not_a_defect"
            where = restored[0] if restored else conflicted[0]
            said = (
                "restored: " + ", ".join(restored)
                if restored
                else "conflicted: " + ", ".join(conflicted)
            )
            ask = new_ask(run, "B", "rebase", kind, where, 0, said, evidence=reason)
            return outcome("rebase", "ask", started, attempts=attempts, asks=[ask])
        if conflict_markers(work, conflicted):
            continue
        git(work, "add", "--", *conflicted)
        done = git(work, "rebase", "--continue", check=False, env=env)
    run["base"] = base
    if first:
        prove_earlier_review(run, work)
    if out(work, "rev-list", "--count", base + "..HEAD") == "0":
        return outcome("rebase", "skip", started, attempts=attempts, empty=True)
    collisions = id_collisions(work, base)
    if collisions:
        path, ident, old, new = collisions[0]
        said = ident + " is already on origin/main as [" + old + "] and this change adds [" + new
        said += "]; renumber to the next free id"
        ask = new_ask(run, "B", "rebase", "id_collision", path, 0, said)
        return outcome("rebase", "ask", started, attempts=attempts, asks=[ask])
    return outcome("rebase", "fixed" if attempts else "pass", started, attempts=attempts)


def step_review(run, work):
    started = time.monotonic()
    since = run.get("since")
    if since and since == out(work, "rev-parse", "HEAD"):
        run["findings"] = []
        return outcome("review", "skip", started, since=since, nothing_new=True)
    answer = call_child("review", brief("review.md") + context(run, work, start=since), work)
    raw = answer.get("findings")
    if not isinstance(raw, list):
        raise ShipError("the reviewer's answer has no findings list")
    findings = []
    for item in raw:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("file"), str)
            or not isinstance(item.get("claim"), str)
            or item.get("kind") not in ("defect", "question")
        ):
            raise ShipError("a reviewer finding lacks file, claim or kind")
        line = item.get("line")
        findings.append(
            {
                "id": "R" + str(len(findings) + 1),
                "file": repo_path(work, item["file"]),
                "line": line if isinstance(line, int) else 0,
                "claim": item["claim"],
                "kind": item["kind"],
                "bloat": item.get("bloat") is True,
            }
        )
    run["findings"] = findings
    return outcome("review", "pass", started, findings=findings, since=since)


def verify_finding(run, work, finding, recheck):
    prompt = brief("verify.md")
    if recheck:
        prompt += "\n\nRecheck after a fix: judge the current files."
    prompt += "\n\nFinding " + finding["id"] + " (" + finding["file"] + ":" + str(finding["line"])
    prompt += "): " + finding["claim"] + context(run, work, start=run.get("since"))
    answer = call_child("verify", prompt, work)
    evidence = str(answer.get("evidence") or "").strip()
    return {
        "confirmed": answer.get("confirmed") is True and bool(evidence),
        "gone": answer.get("confirmed") is False and bool(evidence),
        "said": answer.get("confirmed"),
        "evidence": evidence,
    }


def fix_loop(run, work, finding):
    for _attempt in range(tries()):
        finding["attempts"] = finding.get("attempts", 0) + 1
        problem = "Review finding " + finding["id"] + " at " + finding["file"] + ":"
        problem += str(finding["line"]) + ", confirmed by the verifier: " + finding["claim"]
        problem += "\nVerifier evidence: " + str((finding.get("verdict") or {}).get("evidence"))
        summary, reason, restored = fixer(run, work, "review", problem)
        if restored:
            return finding_ask(finding, "fixer_main", "restored: " + ", ".join(restored))
        if leaf_answer(reason):
            finding["outcome"] = "not_a_defect"
            finding["not_a_defect"] = reason
            return "drop"
        if reason:
            return finding_ask(finding, "fixer_not_a_defect", "fixer: " + reason)
        because = ""
        if finding.get("bloat"):
            because = finding["id"] + " bloated drill, confirmed: " + finding["claim"][:160]
        if not commit_fix(run, work, "review", summary, " ".join(because.split())):
            continue
        again = verify_finding(run, work, finding, recheck=True)
        finding["recheck"] = again
        if again["gone"]:
            finding["outcome"] = "fixed"
            return "fixed"
    finding["outcome"] = "failed"
    return "fail"


def attempts(run):
    total = 0
    for finding in run.get("findings", []):
        total += finding.get("attempts", 0)
    return total


def step_verify(run, work):
    started = time.monotonic()
    asks = []
    fixed = 0
    for finding in run.get("findings", []):
        if finding["kind"] != "defect":
            continue
        finding["verdict"] = verify_finding(run, work, finding, recheck=False)
        if is_trunk(finding["file"]):
            asks.append(finding_ask(finding, "main_defect"))
            continue
        if not finding["verdict"]["confirmed"]:
            finding["outcome"] = "refuted"
            continue
        if not fixer_can_edit(finding["file"]):
            asks.append(finding_ask(finding, "hook_defect"))
            continue
        result = fix_loop(run, work, finding)
        if result == "fail":
            return outcome(
                "verify", "fail", started, findings=run["findings"], attempts=attempts(run)
            )
        if result == "drop":
            return dropped("verify", started, finding["not_a_defect"], attempts(run))
        if result == "fixed":
            fixed += 1
        else:
            asks.append(result)
    run["reviewed"] = out(work, "rev-parse", "HEAD")
    if asks:
        return outcome(
            "verify", "ask", started, findings=run["findings"], attempts=attempts(run), asks=asks
        )
    return outcome(
        "verify",
        "fixed" if fixed else "pass",
        started,
        findings=run["findings"],
        attempts=attempts(run),
    )


def select_drills(work, sections):
    tests = os.path.join(work, "tests")
    names = mutation_check.drills_in_diff(sections)
    stems = []
    python = False
    prose = False
    for path, _text in sections:
        stems.append(Path(path).stem)
        if path.endswith(".py"):
            python = True
        if path.endswith(".md") or path in MEMORY_FILES:
            prose = True
    for name in mutation_check.drills_naming(stems, tests):
        if name not in names:
            names.append(name)
    extra = ["drill_ruff.py"]
    if python:
        extra.append("drill_pyright.py")
    if prose:
        extra.append("drill_boundaries.py")
    for name in extra:
        if name not in names and os.path.isfile(os.path.join(tests, name)):
            names.append(name)
    return names


def touches_trunk(paths):
    for path in paths:
        if is_trunk(path):
            return True
    return False


def run_one(work, name, env):
    began = time.monotonic()
    try:
        done = subprocess.run(
            [sys.executable, os.path.join(work, "tests", name)],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        ok = done.returncode == 0
        text = done.stdout + done.stderr
    except subprocess.TimeoutExpired:
        ok = False
        text = name + " timed out after 600 s"
    return {
        "ok": ok,
        "output": tail(text),
        "fails": fail_lines(text),
        "seconds": round(time.monotonic() - began, 2),
    }


def run_drills(work, names):
    env = mutation_check.drill_env(work)
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {}
        for name in names:
            futures[pool.submit(run_one, work, name, env)] = name
        for future in concurrent.futures.as_completed(futures):
            results[futures[future]] = future.result()
    return results


def trunk_commits(run, work):
    found = []
    for line in lines(out(work, "log", "--format=%H %s", run["base"] + "..HEAD")):
        sha, _space, subject = line.partition(" ")
        touches = False
        for path in lines(out(work, "diff-tree", "--no-commit-id", "--name-only", "-r", sha)):
            if is_trunk(path) and path.endswith(".py"):
                touches = True
        found.append((subject, touches))
    return found


def trunk_messages(run, work):
    found = []
    for sha in lines(out(work, "log", "--reverse", "--format=%H", run["base"] + "..HEAD")):
        found.append(out(work, "log", "-1", "--format=%B", sha))
    return (chr(10) * 2).join(found)


def no_drill_message(commits):
    said = []
    for subject, touches in commits:
        if not touches:
            continue
        if not mutation_check.no_drill_subject(subject):
            return ""
        said.append(subject)
    return said[0] if said else ""


def unpinned_trunk(revert):
    if revert.get("status") == "error":
        return "the revert-and-rerun could not run: " + str(revert.get("detail"))
    found = []
    for entry in revert.get("files") or []:
        if is_trunk(entry.get("path", "")) and entry.get("status") != "pinned":
            found.append(entry["path"] + " (" + str(entry.get("status")) + ")")
    if found:
        return "not pinned by any drill: " + ", ".join(found)
    return ""


def file_at(work, revision, path):
    done = git(work, "show", revision + ":" + path, check=False)
    return done.stdout if done.returncode == 0 else None


def code_shape(text):
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            first = body[0] if body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                node.body = body[1:] or [ast.Pass()]
    return ast.dump(tree)


def comment_only(before, after):
    shape = code_shape(before)
    return shape is not None and shape == code_shape(after)


def comment_only_paths(run, work, paths):
    found = []
    for path in paths:
        before = file_at(work, run["base"], path)
        after = file_at(work, "HEAD", path)
        if before is not None and after is not None and comment_only(before, after):
            found.append(path)
    return found


def mutation_budget(diff_text):
    count = 0
    for path, _text in mutation_check.split_sections(diff_text):
        if path.endswith(".py") and not path.startswith("tests/"):
            count += 1
    return min(21600, max(300, 300 * count))


def mutation(run, work, quiet=()):
    holder = tempfile.mkdtemp(prefix="project-ship-base-")
    base_tree = os.path.join(holder, "tree")
    try:
        git(work, "worktree", "add", "--detach", base_tree, run["base"])
        message = no_drill_message(trunk_commits(run, work))
        diff = range_diff(run, work, binary=True)
        if quiet:
            kept = ""
            for path, text in mutation_check.split_sections(diff):
                if path not in quiet:
                    kept += text
            diff = kept
        return mutation_check.check(
            base_tree,
            diff,
            message,
            mutation_budget(diff),
            worktree_message=trunk_messages(run, work),
        )
    finally:
        git(work, "worktree", "remove", "--force", base_tree, check=False)
        shutil.rmtree(holder, ignore_errors=True)


def gate_env(work, base):
    env = mutation_check.drill_env(work)
    env["PROJECT_RATCHET_BASE"] = base
    return env


def run_gate_command(folder, label, command, env):
    began = time.monotonic()
    try:
        done = subprocess.run(
            command,
            cwd=folder,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GATE_SECONDS,
        )
        ok = done.returncode == 0
        text = done.stdout + done.stderr
    except subprocess.TimeoutExpired:
        ok = False
        text = label + " timed out after " + str(GATE_SECONDS) + " s"
    except OSError as error:
        ok = False
        text = label + " could not start: " + str(error)
    return {
        "ok": ok,
        "output": tail(text),
        "fails": fail_lines(text),
        "failed": failed_drills(text),
        "seconds": round(time.monotonic() - began, 2),
    }


def frontend_commands():
    stub = os.environ.get("PROJECT_SHIP_FRONTEND")
    found = []
    if stub:
        for command in json.loads(stub):
            found.append((" ".join(command), command))
        return found
    npm = shutil.which("npm", path=NODE_DIR + os.pathsep + os.environ.get("PATH", ""))
    for script in (["ci"], ["run", "lint"], ["run", "build"], ["run", "test:ui"]):
        found.append(("npm " + " ".join(script), [npm or "npm", *script]))
    return found


def ui_compare(run, work, paths):
    front = False
    for path in paths:
        if path.startswith(FRONTEND):
            front = True
    if not front:
        return ""
    script = os.environ.get("PROJECT_SHIP_UI_COMPARE") or os.path.join(
        os.path.expanduser("~"), ".claude", "skills", "ui-compare", "ui_compare.py"
    )
    if not os.path.isfile(script):
        return "ui-compare: skipped (skill missing)"
    if not os.path.isfile(os.path.join(work, ".ui-compare.json")):
        return "ui-compare: skipped (no .ui-compare.json)"
    try:
        wait = float(os.environ.get("PROJECT_SHIP_UI_COMPARE_TIMEOUT", UI_COMPARE_SECONDS))
        done = subprocess.run(
            [
                sys.executable,
                script,
                "--repo",
                work,
                "--base",
                run["base"],
                "--head",
                out(work, "rev-parse", "HEAD"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=wait,
        )
    except subprocess.TimeoutExpired:
        return "ui-compare: skipped (timed out)"
    except (OSError, ShipError) as error:
        return "ui-compare: skipped (" + str(error) + ")"
    last = ""
    for line in lines(done.stdout):
        last = line
    if done.returncode == 0 and last.startswith("UI_COMPARE ") and "FAILED" not in last:
        return "ui-compare: " + last[len("UI_COMPARE ") :].strip()
    return "ui-compare: skipped (exit " + str(done.returncode) + ")"


def failed_drills(text):
    found = []
    for line in DRILLS_FAILED.findall(text):
        for name in line.split(","):
            if name.strip():
                found.append(name.strip())
    if not found:
        found = DRILL_FAIL.findall(text)
    return found


def full_drills(run, work):
    return run_gate_command(
        work,
        "run_drills.py",
        [sys.executable, os.path.join(work, "tests", "run_drills.py")],
        gate_env(work, run["base"]),
    )


def full_gate(run, work, paths):
    env = gate_env(work, run["base"])
    found = {}
    committed = run_gate_command(
        work,
        "commit_range.py",
        [sys.executable, os.path.join(work, "tests", "commit_range.py"), run["base"], "HEAD"],
        env,
    )
    if not committed["ok"]:
        found["commit_range.py"] = committed
    front = False
    for path in paths:
        if path.startswith(FRONTEND):
            front = True
    if front:
        front_env = dict(env)
        front_env["PATH"] = NODE_DIR + os.pathsep + front_env.get("PATH", "")
        for label, command in frontend_commands():
            result = run_gate_command(os.path.join(work, "frontend"), label, command, front_env)
            if not result["ok"]:
                found[label] = result
                break
    return found


def step_test(run, work):
    started = time.monotonic()
    attempts = 0
    while True:
        sections = mutation_check.split_sections(range_diff(run, work))
        names = select_drills(work, sections)
        for name in names:
            if name not in run["selected"]:
                run["selected"].append(name)
        results = run_drills(work, names)
        gate = full_gate(run, work, [path for path, _text in sections])
        for name in gate:
            names.append(name)
            results[name] = gate[name]
        red = []
        for name in names:
            if not results[name]["ok"] and name not in ("drill_ruff.py", "commit_range.py"):
                red.append(name)
        if not red:
            break
        output = ""
        for name in red:
            shown = with_fails(results[name]["fails"], results[name]["output"], name)
            output += "\n--- " + name + "\n" + shown
        if touches_trunk([path for path, _text in sections]):
            ask = new_ask(
                run,
                "T",
                "test",
                "test_red",
                "tests/" + red[0],
                0,
                "red: " + ", ".join(red),
                evidence=output,
            )
            return outcome("test", "ask", started, attempts=attempts, asks=[ask], drills=names)
        if attempts >= tries():
            return outcome("test", "fail", started, attempts=attempts, drills=names)
        attempts += 1
        summary, reason, restored = fixer(run, work, "test", "These drills are red:" + output)
        if not restored and leaf_answer(reason):
            return dropped("test", started, reason, attempts)
        if restored or reason:
            kind = "fixer_main" if restored else "fixer_not_a_defect"
            ask = new_ask(
                run,
                "T",
                "test",
                kind,
                "tests/" + red[0],
                0,
                "red: " + ", ".join(red),
                evidence=reason or "restored: " + ", ".join(restored),
            )
            return outcome("test", "ask", started, attempts=attempts, asks=[ask], drills=names)
        commit_fix(run, work, "test", summary)
    trunk_py = []
    for path, _text in sections:
        if is_trunk(path) and path.endswith(".py"):
            trunk_py.append(path)
    quiet = comment_only_paths(run, work, trunk_py)
    for path in quiet:
        print("ship: the revert-and-rerun skips " + path + " (comments and docstrings only)")
    revert = None
    asks = []
    if len(quiet) < len(trunk_py):
        revert = mutation(run, work, quiet)
        problem = unpinned_trunk(revert)
        if problem:
            asks.append(new_ask(run, "M", "test", "unpinned", "src/", 0, problem))
    if "commit_range.py" in results and not results["commit_range.py"]["ok"]:
        asks.append(
            new_ask(
                run,
                "T",
                "test",
                "commit_range",
                "tests/commit_range.py",
                0,
                "red: commit_range.py",
                evidence=results["commit_range.py"]["output"],
            )
        )
    if asks:
        return outcome(
            "test", "ask", started, attempts=attempts, asks=asks, drills=names, mutation=revert
        )
    status = "fixed" if attempts else "pass"
    compared = ui_compare(run, work, [path for path, _text in sections])
    if compared:
        print("ship: " + compared)
    return outcome(
        "test",
        status,
        started,
        attempts=attempts,
        drills=names,
        mutation=revert,
        comment_only=quiet,
        ui_compare=compared,
    )


def step_document(run, work):
    started = time.monotonic()
    try:
        answer = call_child("document", brief("document.md") + context(run, work), work)
    except ShipError as error:
        return outcome("document", "skip", started, error=str(error))
    gaps = answer.get("gaps") if isinstance(answer.get("gaps"), list) else []
    leaf = []
    logged = []
    denied = []
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        path = repo_path(work, gap.get("file") or "")
        if path and not is_trunk(path) and path not in MEMORY_FILES:
            if fixer_can_edit(path):
                leaf.append(gap)
            else:
                denied.append(path)
                print(
                    "ship: not applied: "
                    + path
                    + " (the fixer cannot edit .claude/): "
                    + str(gap.get("claim") or "")
                )
        else:
            logged.append(gap)
    if not leaf:
        return outcome("document", "pass", started, findings=gaps, not_applied=denied)
    summary, reason, restored = fixer(
        run, work, "document", "Documentation gaps: " + json.dumps(leaf)
    )
    if restored:
        ask = new_ask(
            run, "D", "document", "fixer_main", restored[0], 0, "restored: " + ", ".join(restored)
        )
        return outcome(
            "document", "ask", started, findings=gaps, attempts=1, asks=[ask], not_applied=denied
        )
    if leaf_answer(reason):
        return outcome(
            "document",
            "pass",
            started,
            findings=gaps,
            attempts=1,
            not_a_defect=reason,
            not_applied=denied,
        )
    if reason:
        ask = new_ask(
            run,
            "D",
            "document",
            "fixer_not_a_defect",
            leaf[0].get("file"),
            0,
            str(leaf[0].get("claim")),
            evidence=reason,
        )
        return outcome(
            "document", "ask", started, findings=gaps, attempts=1, asks=[ask], not_applied=denied
        )
    if not commit_fix(run, work, "document", summary):
        changed = []
    else:
        changed = lines(out(work, "show", "--name-only", "--format=", "HEAD"))
    for gap in leaf:
        path = repo_path(work, gap.get("file") or "")
        if path not in changed:
            denied.append(path)
            print("ship: not applied: " + path + " (the fixer left it unchanged)")
    if not changed:
        return outcome(
            "document",
            "pass",
            started,
            findings=gaps,
            attempts=1,
            unchanged=True,
            not_applied=denied,
        )
    return outcome("document", "fixed", started, findings=gaps, attempts=1, not_applied=denied)


def ruff(work, *args):
    return subprocess.run(
        RUFF + list(args),
        cwd=work,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )


def autofix(run, work):
    leaf = []
    for path in changed_paths(run, work):
        if path.endswith(".py") and not is_trunk(path) and Path(work, path).is_file():
            leaf.append(path)
    if leaf:
        ruff(work, "format", *leaf)
        ruff(work, "check", "--fix", "--quiet", *leaf)
        commit_fix(run, work, "lint", "ruff format and ruff check --fix")


def step_lint(run, work):
    started = time.monotonic()
    attempts = 0
    autofix(run, work)
    while os.path.isfile(os.path.join(work, "tests", "drill_ruff.py")):
        result = run_drills(work, ["drill_ruff.py"])["drill_ruff.py"]
        if result["ok"]:
            break
        trunk = []
        for path in changed_paths(run, work):
            if is_trunk(path) and path.endswith(".py") and Path(work, path).is_file():
                trunk.append(path)
        if trunk:
            checked = ruff(work, "check", *trunk)
            formatted = ruff(work, "format", "--check", *trunk)
            if checked.returncode != 0 or formatted.returncode != 0:
                ask = new_ask(
                    run,
                    "L",
                    "lint",
                    "lint_main",
                    trunk[0],
                    0,
                    "ruff fails on src/",
                    evidence=tail(checked.stdout + formatted.stdout),
                )
                return outcome("lint", "ask", started, attempts=attempts, asks=[ask])
        if attempts >= tries():
            return outcome("lint", "fail", started, attempts=attempts)
        attempts += 1
        summary, reason, restored = fixer(
            run, work, "lint", "tests/drill_ruff.py is red:\n" + result["output"]
        )
        if not restored and leaf_answer(reason):
            return dropped("lint", started, reason, attempts)
        if restored or reason:
            kind = "fixer_main" if restored else "fixer_not_a_defect"
            ask = new_ask(
                run,
                "L",
                "lint",
                kind,
                "tests/drill_ruff.py",
                0,
                "drill_ruff red",
                evidence=reason or ", ".join(restored),
            )
            return outcome("lint", "ask", started, attempts=attempts, asks=[ask])
        commit_fix(run, work, "lint", summary)
        autofix(run, work)
    return outcome("lint", "fixed" if attempts else "pass", started, attempts=attempts)


def assert_reviewed(work, reviewed):
    head = out(work, "rev-parse", "HEAD")
    if not reviewed:
        raise ShipError("refusing to push: no reviewed commit recorded")
    if head != reviewed and not is_ancestor(work, reviewed, head):
        raise ShipError(
            "refusing to push: HEAD "
            + head[:12]
            + " does not descend from the reviewed commit "
            + reviewed[:12]
        )
    return head


def patch_id(work, older, newer):
    diff = git(work, "diff", "--no-color", "--no-ext-diff", older, newer).stdout
    done = subprocess.run(
        ["git", "patch-id", "--stable"],
        cwd=work,
        input=diff,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return (done.stdout.split() or [""])[0]


def nested(step, inner, started):
    return outcome(
        step,
        inner["status"],
        started,
        asks=inner.get("asks", []),
        resume_at=inner.get("resume_at") or "push",
        not_a_defect=inner.get("not_a_defect"),
    )


def step_push(run, work):
    started = time.monotonic()
    races = 0
    while True:
        head = assert_reviewed(work, run["reviewed"])
        listed = out(work, "ls-remote", remote(), "refs/heads/main").split()
        tip = listed[0] if listed else ""
        if not tip or tip == run["base"] or is_ancestor(work, tip, head):
            try:
                git_retrying(
                    work,
                    "push",
                    remote(),
                    head + ":refs/heads/main",
                    again=server_rejected,
                    timeout=3600,
                )
            except ShipError as error:
                if races >= PUSH_RACES or not main_moved(error.full or str(error)):
                    raise
                races += 1
                print("ship: origin/main moved during the push; rebasing and pushing again")
                continue
            run["landed"] = head
            return outcome("push", "pass", started, landed=run["landed"])
        moves = run.get("main_moves", 0) + 1
        if moves > MAIN_MOVES:
            raise ShipError(
                "origin/main moved "
                + str(moves)
                + " times during the run (at most "
                + str(MAIN_MOVES)
                + " are rebased); run ship again"
            )
        run["main_moves"] = moves
        old_base = run["base"]
        old_reviewed = run["reviewed"]
        after = out(work, "rev-list", "--count", old_reviewed + "..HEAD")
        rebased = step_rebase(run, work)
        run["steps"].append(rebased)
        save(run)
        if rebased.get("empty"):
            return outcome("push", "skip", started, empty=True)
        if rebased["status"] in ("ask", "fail", "drop"):
            return nested("push", rebased, started)
        twin = out(work, "rev-parse", "HEAD~" + after)
        run["retest_open"] = True
        save(run)
        take_lock(run)
        try:
            if patch_id(work, old_base, old_reviewed) == patch_id(work, run["base"], twin):
                run["reviewed"] = twin
            else:
                print(
                    "ship: the rebase onto the moved origin/main changed the diff; reviewing again"
                )
                run["since"] = None
                for function in (step_review, step_verify):
                    again = function(run, work)
                    run["steps"].append(again)
                    save(run)
                    if again["status"] in ("ask", "fail", "drop"):
                        return outcome(
                            "push",
                            again["status"],
                            started,
                            asks=again.get("asks", []),
                            resume_at="test",
                            not_a_defect=again.get("not_a_defect"),
                        )
            tested = step_test(run, work)
        finally:
            drop_lock()
        run["steps"].append(tested)
        save(run)
        if tested["status"] in ("ask", "fail", "drop"):
            return nested("push", tested, started)
        run["retest_open"] = False


def ci_runs(work, sha):
    deadline = time.monotonic() + limit("PROJECT_SHIP_CI_TIMEOUT", 1200)
    pause = limit("PROJECT_SHIP_CI_POLL", 30)
    while True:
        text = gh(
            [
                "run",
                "list",
                "--commit",
                sha,
                "--workflow",
                "verify.yml",
                "--json",
                "status,conclusion,databaseId",
            ],
            work,
        )
        try:
            runs = json.loads(text)
        except ValueError:
            raise ShipError("gh run list printed no JSON")
        done = bool(runs)
        for entry in runs:
            if entry.get("status") != "completed":
                done = False
        if done:
            return runs
        if time.monotonic() > deadline:
            return None if runs else []
        time.sleep(pause)


def run_jobs(work, number):
    text = gh(["run", "view", number, "--json", "jobs"], work)
    try:
        jobs = json.loads(text).get("jobs")
    except (ValueError, AttributeError):
        return True
    for job in jobs or []:
        if job.get("steps"):
            return True
    return False


def step_ci(run, work):
    started = time.monotonic()
    attempts = 0
    while True:
        sha = run["landed"]
        runs = ci_runs(work, sha)
        local = None
        why = NOT_STARTED_REASON
        if runs is None:
            why = TIMED_OUT_REASON
            local = locked(run, full_drills, work)
        elif not runs:
            local = locked(run, full_drills, work)
        else:
            run["ci_watched"] = True
            failed = []
            for entry in runs:
                if entry.get("conclusion") != "success":
                    failed.append(entry)
            if not failed:
                return outcome(
                    "ci", "fixed" if attempts else "pass", started, attempts=attempts, gate="ci"
                )
            number = str(failed[0].get("databaseId"))
            broken = failed[0].get("conclusion") == "startup_failure"
            if not broken and not run_jobs(work, number):
                local = locked(run, full_drills, work)
        if local is not None:
            if local["ok"]:
                return outcome(
                    "ci",
                    "fixed" if attempts else "pass",
                    started,
                    attempts=attempts,
                    gate="local",
                    reason=why,
                    drills=local["output"],
                )
            where = "the full suite run locally (" + why + ")"
            log = local["output"]
            fails = local["fails"]
            red = sorted(set(local["failed"]))
        else:
            where = "CI"
            fails = None
            try:
                log = gh(["run", "view", number, "--log-failed"], work)
            except ShipError as error:
                if not broken:
                    raise
                log = str(error)
            red = sorted(set(CI_FAIL.findall(log)))
        if fails is None:
            fails = fail_lines(log)
        shown = with_fails(fails, tail(log), "the failing log")
        for name in red:
            if name not in run["selected"]:
                log_line(
                    run,
                    {
                        "kind": "selection_miss",
                        "run": run["id"],
                        "drill": name,
                        "commit": sha,
                        "at": now(),
                    },
                )
        if touches_trunk(changed_paths(run, work)):
            ask = new_ask(
                run,
                "C",
                "ci",
                "ci_red",
                "src/",
                0,
                where + " red on " + sha[:12] + ": " + ", ".join(red),
                evidence=shown,
            )
            return outcome("ci", "ask", started, attempts=attempts, asks=[ask])
        if attempts >= tries():
            return outcome("ci", "fail", started, attempts=attempts)
        attempts += 1
        summary, reason, restored = fixer(
            run, work, "ci", where + " is red on the pushed commit. Failing log:\n" + shown
        )
        if not restored and leaf_answer(reason):
            return dropped("ci", started, reason, attempts)
        if restored or reason:
            kind = "fixer_main" if restored else "fixer_not_a_defect"
            ask = new_ask(
                run,
                "C",
                "ci",
                kind,
                "src/" if restored else "-",
                0,
                where + " red: " + ", ".join(red),
                evidence=reason or ", ".join(restored),
            )
            return outcome("ci", "ask", started, attempts=attempts, asks=[ask])
        commit_fix(run, work, "ci", summary)
        for function in (step_test, step_document, step_lint, step_push):
            if function is step_test:
                again = locked(run, step_test, work)
            else:
                again = function(run, work)
            run["steps"].append(again)
            save(run)
            if again["status"] in ("ask", "fail", "drop"):
                return nested("ci", again, started)


FUNCTIONS = {
    "intent": step_intent,
    "rebase": step_rebase,
    "review": step_review,
    "verify": step_verify,
    "test": step_test,
    "document": step_document,
    "lint": step_lint,
    "push": step_push,
    "ci": step_ci,
}


def drive(run, first):
    work = run["worktree"]
    if first == "done":
        return finish(run, "landed_ci_red")
    position = STEPS.index(first)
    while position < len(STEPS):
        name = STEPS[position]
        run["current"] = name
        save(run)
        if name in HEAVY:
            take_lock(run)
        else:
            drop_lock()
        result = FUNCTIONS[name](run, work)
        run["steps"].append(result)
        run["last_step"] = name
        save(run)
        if result["status"] == "ask":
            run["asks"] = result["asks"]
            following = STEPS[position + 1] if position + 1 < len(STEPS) else "done"
            run["next_step"] = result.get("resume_at") or following
            return finish(run, "asking")
        if result["status"] == "fail":
            return finish(run, "landed_ci_red" if run.get("landed") else "dropped")
        if result["status"] == "drop":
            if run.get("landed"):
                return finish(run, "landed_ci_red")
            print("ship: the fixer answered not a defect: " + str(result.get("not_a_defect")))
            return finish(run, "dropped", logged=False)
        if result.get("empty"):
            return finish(run, "empty")
        position += 1
    return finish(run, "landed")


def start(intent):
    caller = out(os.getcwd(), "rev-parse", "--show-toplevel")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run = {
        "id": stamp + "-" + uuid.uuid4().hex[:6],
        "status": "running",
        "started": now(),
        "caller": caller,
        "pid": os.getpid(),
        "state": str(state_dir(caller)),
        "head": out(caller, "rev-parse", "HEAD"),
        "worktree": None,
        "base": None,
        "reviewed": None,
        "landed": None,
        "intent_arg": intent,
        "intent": "",
        "findings": [],
        "selected": [],
        "steps": [],
        "asks": [],
        "answers": [],
        "last_step": "start",
        "current": "start",
        "ci_watched": False,
    }
    save(run)
    return run


def prepare(run):
    holder = tempfile.mkdtemp(prefix="project-ship-")
    work = os.path.join(holder, "tree")
    git(run["caller"], "worktree", "add", "--detach", work, run["head"])
    run["worktree"] = work
    save(run)
    run["base"] = fetch(work)
    if out(work, "rev-list", "--count", run["base"] + "..HEAD") == "0":
        print("nothing to push: HEAD holds no commit that origin/main lacks")
        return False
    return True


def parse_answers(texts):
    parsed = {}
    for text in texts:
        match = ANSWER.match(text)
        if not match:
            raise ShipError("an answer reads '<id>: fix|drop|not a defect because ...': " + text)
        said = match.group(2)
        lowered = said.lower()
        if lowered == "fix":
            action = "fix"
        elif lowered == "drop":
            action = "drop"
        elif lowered.startswith("not a defect because") and len(said) > len("not a defect because"):
            action = "answered"
        else:
            raise ShipError("unknown answer for " + match.group(1) + ": " + said)
        parsed[match.group(1)] = {"action": action, "text": said}
    return parsed


def resume(run, texts):
    work = run["worktree"]
    parsed = parse_answers(texts)
    remaining = []
    hand_back = False
    fixed = False
    for ask in run["asks"]:
        answer = parsed.get(ask["id"])
        if answer is None:
            remaining.append(ask)
            continue
        run["answers"].append({"ask": ask, "answer": answer, "at": now()})
        if ask["step"] == "rebase":
            hand_back = True
        elif answer["action"] != "fix":
            continue
        elif leaf_ask(ask):
            finding = None
            for candidate in run["findings"]:
                if candidate["id"] == ask["id"]:
                    finding = candidate
            if finding is None:
                raise ShipError("no finding " + ask["id"] + " in the run record")
            run["status"] = "running"
            save(run)
            take_lock(run)
            result = fix_loop(run, work, finding)
            if result == "fail":
                return finish(run, "dropped")
            if result == "drop":
                return finish(run, "dropped", logged=False)
            elif result == "fixed":
                fixed = True
            else:
                remaining.append(result)
        else:
            hand_back = True
    if hand_back:
        return finish(run, "handed_back")
    if remaining:
        run["asks"] = remaining
        return finish(run, "asking")
    run["asks"] = []
    run["main_moves"] = 0
    run["retest_open"] = False
    if fixed:
        run["reviewed"] = out(work, "rev-parse", "HEAD")
    run["status"] = "running"
    save(run)
    return drive(run, run["next_step"])


def resume_push(run):
    work = run.get("worktree")
    refusal = None
    if not work or not Path(work).is_dir() or not run.get("reviewed"):
        refusal = "cannot restart at the push: its tree is gone"
    elif run.get("retest_open"):
        refusal = "failed in the retest after a rebase, so its range is not tested"
    if refusal:
        print("ship: run " + run["id"] + " " + refusal, file=sys.stderr)
        return 1
    run["pid"] = os.getpid()
    run["status"] = "running"
    run["error"] = None
    run["main_moves"] = 0
    save(run)
    return drive(run, "push")


def status_lines(folder):
    found = []
    for path in sorted((Path(folder) / "ship_runs").glob("*.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        state = run.get("status")
        commit = str(run.get("landed") or run.get("head") or "")[:12]
        watched = "CI watched" if run.get("ci_watched") else "CI not watched"
        if state == "running" and run.get("waiting") and pid_alive(run.get("pid")):
            found.append(
                "ship run "
                + run["id"]
                + " "
                + str(run["waiting"])
                + ", before "
                + str(run.get("current"))
                + ", commit "
                + commit
            )
        elif state == "running":
            found.append(
                "ship run "
                + run["id"]
                + " stopped after "
                + str(run.get("last_step"))
                + ", "
                + watched
                + ", commit "
                + commit
            )
        elif state == "asking":
            found.append(
                "ship run "
                + run["id"]
                + " asks the user after "
                + str(run.get("last_step"))
                + ", see "
                + str(path.with_suffix(".ask.md"))
                + ", commit "
                + commit
            )
        elif state == "failed":
            found.append(
                "ship run "
                + run["id"]
                + " failed in "
                + str(run.get("current"))
                + ": "
                + str(run.get("error"))[:160]
                + ", worktree "
                + str(run.get("worktree"))
            )
    return found


def load_stubs():
    for key, name in (("claude", "PROJECT_SHIP_STUB"), ("gh", "PROJECT_SHIP_GH_STUB")):
        path = os.environ.get(name)
        STUBS[key] = json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def main(argv=None):
    parser = argparse.ArgumentParser(description="the push pipeline")
    parser.add_argument("--intent")
    parser.add_argument("--intent-file")
    parser.add_argument("--resume")
    parser.add_argument("--answer", action="append", default=[])
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    if args.status:
        folder = state_dir(out(os.getcwd(), "rev-parse", "--show-toplevel"))
        for swept in sweep(folder):
            print("ship: removed the tree of run " + swept)
        for line in status_lines(folder):
            print(line)
        return 0
    load_stubs()
    run = None
    try:
        if args.resume:
            try:
                parse_answers(args.answer)
            except ShipError as error:
                print("ship: " + str(error) + "; the run still asks", file=sys.stderr)
                return 2
            folder = state_dir(out(os.getcwd(), "rev-parse", "--show-toplevel")) / "ship_runs"
            record = json.loads((folder / (args.resume + ".json")).read_text(encoding="utf-8"))
            failed_push = record.get("status") == "failed" and record.get("current") == "push"
            if failed_push and args.answer:
                print(
                    "ship: run " + args.resume + " failed at the push; resume it without an answer",
                    file=sys.stderr,
                )
                return 1
            if record.get("status") != "asking" and not failed_push:
                state = str(record.get("status"))
                print("ship: run " + args.resume + " is " + state + ", not asking", file=sys.stderr)
                return 1
            run = record
            if failed_push:
                return resume_push(run)
            run["pid"] = os.getpid()
            return resume(run, args.answer)
        intent = args.intent
        if args.intent_file:
            intent = Path(args.intent_file).read_text(encoding="utf-8")
        run = start(intent)
        if not prepare(run):
            return finish(run, "empty")
        return drive(run, "intent")
    except Exception as error:
        message = (
            type(error).__name__ + ": " + str(error)
            if not isinstance(error, ShipError)
            else str(error)
        )
        print("ship failed: " + message, file=sys.stderr)
        if run is None or not run.get("state"):
            return 1
        run["error"] = message
        return finish(run, "failed")
    finally:
        drop_lock()


if __name__ == "__main__":
    sys.exit(main())
