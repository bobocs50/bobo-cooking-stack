"""Revert-and-rerun check for a trunk commit: undo the code change, keep the drills, and
see whether a drill goes red. A drill that stays green with the change undone pins
nothing, so the push pipeline stops the push and asks the human about the unpinned spine
file.

    check(repo_dir, staged_diff, commit_message, timeout=300) -> dict

The selected drills first run side by side in a detached worktree of HEAD in a temp folder
outside the repo with the whole staged diff applied (the baseline: a drill red there is
"red_with_change" and never counts as pinning). Then each changed .py file outside tests/
runs in a worktree of its own, up to worker_count() files at once (PROJECT_MUTATION_WORKERS,
default min(4, CPU count)): the worktree is reset and the staged diff minus that one file is
applied (all tests and the other code stay); the file is pinned when at least one drill
selected for it goes red, so its run stops at the first red drill. A drill of ALONE runs with
no other drill beside it, so a red from a starved start window never pins a file. The budget
left is shared by the files not yet started, times the files running at once. A second
changed file nobody tests therefore cannot ride along on the first one's drill. The working
tree and the index of repo_dir are never touched. The check
adds evidence and never raises.

The result dict: {"status", "drills", "files", "seconds", "detail"}.
  status "pinned"   every changed code file is pinned.
  status "unpinned" a code file is unpinned or has no drill naming it; detail names the paths.
  status "red_with_change" no file is unpinned, but one has only drills red with the change.
  status "no_drill" the commit subject says no drill:.
  status "skipped"  nothing to check: no .py code file in the diff. Never an infrastructure fault.
  status "error"    the check could not run: worktree add or apply failed, the time budget ran
                    out, or an exception; the files not reached are marked "timeout".
  drills  [{"name", "reverted_ok", "with_change_ok", "seconds"}]: with_change_ok False is a
          drill red with the change; reverted_ok is False when it went red for any file,
          None when no file's run reached it.
  files   [{"path", "status", "drills", "red_with_change"}], status one of pinned, unpinned,
          no_drill_named (no drill selected), red_with_change (every selected drill is red
          with the change), timeout; "drills" are the selected names, "red_with_change"
          the names among them that are red with the change.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SPINE_DIR = "src"
DIFF_HEADER = re.compile(r'^diff --git "?a/(.+?)"? "?b/(.+?)"?$')


def result(status, drills, started, detail, files=None):
    return {
        "status": status,
        "drills": drills,
        "files": files if files is not None else [],
        "seconds": round(time.monotonic() - started, 2),
        "detail": detail,
    }


def subject_of(commit_message):
    for line in commit_message.splitlines():
        if line.strip():
            return line.strip()
    return ""


def no_drill_subject(subject):
    """True when the subject carries `no drill:` followed by a reason, outside backticks and
    quotes, so a subject that only talks about the phrase does not switch the check off. A
    stricter reading than the CI step's substring test, on purpose."""
    for found in re.finditer("no drill:", subject, re.IGNORECASE):
        before = subject[: found.start()]
        inside = (
            before.count("`") % 2 == 1
            or before.count('"') % 2 == 1
            or len(re.findall(r"(?<!\w)'", before)) % 2 == 1
        )
        if not inside and subject[found.end() :].strip():
            return True
    return False


def split_sections(staged_diff):
    """The diff cut into (path, text) per file; the path is the b/ side."""
    sections = []
    path = None
    lines = []
    for line in staged_diff.splitlines(keepends=True):
        match = DIFF_HEADER.match(line.rstrip("\r\n"))
        if match:
            if path is not None:
                sections.append((path, "".join(lines)))
            path = match.group(2)
            lines = [line]
        elif path is not None:
            lines.append(line)
    if path is not None:
        sections.append((path, "".join(lines)))
    return sections


def drills_in_diff(sections):
    names = []
    for path, text in sections:
        parts = path.split("/")
        if len(parts) == 2 and parts[0] == "tests" and parts[1].startswith("drill_"):
            if parts[1].endswith(".py") and "\ndeleted file mode" not in text:
                names.append(parts[1])
    return names


def import_pattern(module):
    name = re.escape(module)
    return re.compile(
        r"^[ \t]*(?:import|from)\s+(?:" + re.escape(SPINE_DIR) + r"\.)?(?:\w+\.)*" + name + r"\b"
        r"|^[ \t]*from\s+(?:" + re.escape(SPINE_DIR) + r"\.)?[\w.]+\s+import\s+[^\n(]*\b" + name + r"\b"
        r"|^[ \t]*from\s+(?:" + re.escape(SPINE_DIR) + r"\.)?[\w.]+\s+import\s*\([^)]*\b" + name + r"\b",
        re.MULTILINE,
    )


def named_pattern(module):
    name = re.escape(module)
    return re.compile(
        r"(?<![\w.-])" + name + r"\.py\b"
        r"|\b" + re.escape(SPINE_DIR) + r"[./](?:\w+[./])*" + name + r"\b"
        r"|[\"'](?:\w+\.)*" + name + r"[\"']",
        re.MULTILINE,
    )


DATA_FOLDERS = frozenset(
    {
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        "data",
        "runtime",
    }
)


def spine_python_files(main_dir):
    found = []
    for folder, subfolders, names in os.walk(main_dir):
        kept = []
        for name in subfolders:
            if name not in DATA_FOLDERS and not name.startswith("."):
                kept.append(name)
        subfolders[:] = kept
        for name in names:
            if name.endswith(".py"):
                found.append(Path(folder) / name)
    return sorted(found)


def importers_of(module, main_dir):
    pattern = import_pattern(module)
    found = []
    for path in spine_python_files(main_dir):
        if path.stem == module:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if pattern.search(text):
            found.append(path.stem)
    return found


def drills_naming(stems, tests_dir):
    main_dir = Path(tests_dir).parent / SPINE_DIR
    main_stems = set()
    for path in spine_python_files(main_dir):
        main_stems.add(path.stem)
    patterns = []
    for stem in stems:
        if stem in main_stems:
            patterns.append(import_pattern(stem))
            patterns.append(named_pattern(stem))
            for importer in importers_of(stem, main_dir):
                patterns.append(import_pattern(importer))
        else:
            patterns.append(re.compile(re.escape(stem)))
    names = []
    for drill in sorted(Path(tests_dir).glob("drill_*.py")):
        try:
            text = drill.read_text(encoding="utf-8")
        except OSError:
            continue
        for pattern in patterns:
            if pattern.search(text):
                names.append(drill.name)
                break
    return names


def credential_names(folder):
    names = []
    try:
        lines = (Path(folder) / ".env.example").read_text(encoding="utf-8").splitlines()
    except OSError:
        return names
    for line in lines:
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        names.append(line.split("=", 1)[0].strip())
    return names


def drill_env(work):
    """The drills' environment: every credential named in .env.example blanked, no .pyc written:
    git clean keeps the ignored __pycache__, and a same-size module rewritten within the same
    second would let the reverted run load the changed code."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in credential_names(work):
        env[name] = ""
    return env


def git(folder, *args, stdin=None, timeout=60):
    return subprocess.run(
        ["git", *args],
        cwd=folder,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )


class DrillTimeout(Exception):
    """The time budget ran out before or inside a drill."""

    pass


def run_drill(work, name, env, started, timeout):
    """(green, seconds) of one drill in the worktree; DrillTimeout when the budget is spent."""
    left = timeout - (time.monotonic() - started)
    if left <= 0:
        raise DrillTimeout("Timed out after " + str(timeout) + " seconds.")
    began = time.monotonic()
    try:
        ran = subprocess.run(
            [sys.executable, os.path.join(work, "tests", name)],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=left,
        )
    except subprocess.TimeoutExpired:
        raise DrillTimeout("Timed out after " + str(timeout) + " seconds in " + name + ".")
    return ran.returncode == 0, time.monotonic() - began


def check(repo_dir, staged_diff, commit_message, timeout=300, worktree_message=None):
    started = time.monotonic()
    drills = []
    try:
        if no_drill_subject(subject_of(commit_message)):
            return result("no_drill", drills, started, "The commit subject says no drill:.")
        committed = commit_message if worktree_message is None else worktree_message
        return run_check(repo_dir, staged_diff, timeout, started, drills, committed)
    except Exception as error:
        return result(
            "error",
            drills,
            started,
            "Check could not run: " + type(error).__name__ + ": " + str(error)[:200],
        )


def apply_patch(work, text, what, commit_message=None):
    applied = subprocess.run(
        ["git", "apply", "--whitespace=nowarn"]
        + (["--index"] if commit_message is not None else [])
        + ["-"],
        cwd=work,
        input=text.encode("utf-8"),
        capture_output=True,
        timeout=60,
    )
    if applied.returncode != 0:
        message = applied.stderr.decode("utf-8", errors="replace")
        return "git apply of the " + what + " failed: " + message.strip()[:200]
    if commit_message is None:
        return None
    committed = subprocess.run(
        [
            "git",
            "-c",
            "user.name=mutation-check",
            "-c",
            "user.email=mutation-check@example.invalid",
            "commit",
            "-q",
            "--no-verify",
            "--allow-empty",
            "--allow-empty-message",
            "-F",
            "-",
        ],
        cwd=work,
        input=commit_message.encode("utf-8"),
        capture_output=True,
        timeout=60,
    )
    if committed.returncode != 0:
        message = committed.stderr.decode("utf-8", errors="replace")
        return "git commit of the " + what + " failed: " + message.strip()[:200]
    return None


def drill_entries(order, entries):
    drills = []
    for name in order:
        if name not in entries:
            continue
        entry = dict(entries[name])
        entry["seconds"] = round(entry["seconds"], 2)
        drills.append(entry)
    return drills


def file_selection(path, sections, work):
    names = drills_in_diff(sections)
    for name in drills_naming([Path(path).stem], os.path.join(work, "tests")):
        if name not in names:
            names.append(name)
    return names


def overall(files):
    unpinned = []
    red = False
    for entry in files:
        if entry["status"] in ("unpinned", "no_drill_named"):
            unpinned.append(entry["path"] + " (" + entry["status"] + ")")
        elif entry["status"] == "red_with_change":
            red = True
    if unpinned:
        return "unpinned", "Not pinned by any drill: " + ", ".join(unpinned) + "."
    if red:
        return (
            "red_with_change",
            "Only drills that are red with the change cover a file; they pin nothing.",
        )
    return "pinned", "Every changed code file has a drill that fails with only it undone."


ALONE = ()


def worker_count():
    workers = min(4, os.cpu_count() or 1)
    override = os.environ.get("PROJECT_MUTATION_WORKERS", "")
    if override.isdigit() and int(override) >= 1:
        workers = int(override)
    return workers


def run_check(repo_dir, staged_diff, timeout, started, drills, commit_message=""):
    sections = split_sections(staged_diff)
    code_paths = []
    for path, _text in sections:
        if path.endswith(".py") and not path.startswith("tests/"):
            code_paths.append(path)
    if not code_paths:
        return result("skipped", drills, started, "No .py code file changed, nothing to revert.")

    files = []
    tmp = tempfile.mkdtemp(prefix="mutation-check-")
    trees = []
    try:
        work = os.path.join(tmp, "tree")
        made = git(repo_dir, "worktree", "add", "--detach", work, "HEAD")
        if made.returncode != 0:
            return result(
                "error",
                drills,
                started,
                "git worktree add failed: " + made.stderr.strip()[:200],
                files,
            )
        trees.append(work)
        base = git(work, "rev-parse", "HEAD").stdout.strip()
        problem = apply_patch(work, staged_diff, "staged diff", commit_message)
        if problem is not None:
            return result("error", drills, started, problem, files)

        selected = {}
        order = []
        for path in code_paths:
            selected[path] = file_selection(path, sections, work)
            for name in selected[path]:
                if name not in order:
                    order.append(name)

        env = drill_env(work)
        entries = {}
        lock = threading.Lock()
        workers = worker_count()
        try:
            pooled = []
            alone = []
            for name in order:
                if name in ALONE:
                    alone.append(name)
                else:
                    pooled.append(name)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {}
                for name in pooled:
                    futures[name] = pool.submit(run_drill, work, name, env, started, timeout)
                for name in pooled:
                    green, seconds = futures[name].result()
                    entries[name] = {
                        "name": name,
                        "reverted_ok": None,
                        "with_change_ok": green,
                        "seconds": seconds,
                    }
            for name in alone:
                green, seconds = run_drill(work, name, env, started, timeout)
                entries[name] = {
                    "name": name,
                    "reverted_ok": None,
                    "with_change_ok": green,
                    "seconds": seconds,
                }
        except DrillTimeout as error:
            for path in code_paths:
                files.append(
                    {
                        "path": path,
                        "status": "timeout",
                        "drills": selected[path],
                        "red_with_change": [],
                    }
                )
            return result(
                "error",
                drill_entries(order, entries),
                started,
                timeout_detail(error, entries, order, timeout, code_paths),
                files,
            )

        by_path = {}
        reverts = []
        for path in code_paths:
            names = selected[path]
            red_names = []
            usable = []
            for name in names:
                if entries[name]["with_change_ok"]:
                    usable.append(name)
                else:
                    red_names.append(name)
            entry = {"path": path, "status": "", "drills": names, "red_with_change": red_names}
            if not names:
                entry["status"] = "no_drill_named"
            elif not usable:
                entry["status"] = "red_with_change"
            else:
                reverts.append((path, usable))
            by_path[path] = entry

        free_trees = [work]
        for number in range(1, min(workers, len(reverts))):
            extra = os.path.join(tmp, "tree" + str(number))
            made = git(repo_dir, "worktree", "add", "--detach", extra, base)
            if made.returncode != 0:
                break
            trees.append(extra)
            free_trees.append(extra)
        parallel = len(free_trees)
        state = {"waiting": len(reverts), "stopped": None, "fault": None}
        gate = threading.Condition()
        occupied = {"shared": 0, "alone": False}

        def enter_gate(alone):
            began = time.monotonic()
            with gate:
                if alone:
                    gate.wait_for(lambda: not occupied["alone"] and occupied["shared"] == 0)
                    occupied["alone"] = True
                else:
                    gate.wait_for(lambda: not occupied["alone"])
                    occupied["shared"] += 1
            return time.monotonic() - began

        def leave_gate(alone):
            with gate:
                if alone:
                    occupied["alone"] = False
                else:
                    occupied["shared"] -= 1
                gate.notify_all()

        def revert_one(path, usable):
            with lock:
                if state["stopped"] is not None or state["fault"] is not None:
                    state["waiting"] -= 1
                    return
                tree = free_trees.pop()
                left = timeout - (time.monotonic() - started)
                share = min(left, left * parallel / max(state["waiting"], 1))
                state["waiting"] -= 1
            entry = by_path[path]
            try:
                reset = git(tree, "reset", "-q", "--hard", base)
                cleaned = git(tree, "clean", "-fdq")
                if reset.returncode != 0 or cleaned.returncode != 0:
                    with lock:
                        state["fault"] = "resetting the worktree failed"
                    return
                rest = ""
                for other, text in sections:
                    if other != path:
                        rest += text
                problem = apply_patch(tree, rest, "diff without " + path, commit_message)
                if problem is not None:
                    with lock:
                        state["fault"] = problem
                    return
                tree_env = drill_env(tree)
                file_started = time.monotonic()
                entry["status"] = "unpinned"
                for name in usable:
                    waited = enter_gate(name in ALONE)
                    file_started += waited
                    try:
                        green, seconds = run_drill(tree, name, tree_env, file_started, share)
                    finally:
                        leave_gate(name in ALONE)
                    with lock:
                        entries[name]["seconds"] += seconds
                        if not green:
                            entries[name]["reverted_ok"] = False
                        elif entries[name]["reverted_ok"] is None:
                            entries[name]["reverted_ok"] = True
                    if not green:
                        entry["status"] = "pinned"
                        break
            except DrillTimeout as error:
                entry["status"] = "timeout"
                with lock:
                    if state["stopped"] is None:
                        state["stopped"] = error
            finally:
                with lock:
                    free_trees.append(tree)

        with ThreadPoolExecutor(max_workers=parallel) as pool:
            running = []
            for path, usable in reverts:
                running.append(pool.submit(revert_one, path, usable))
            for future in running:
                future.result()

        if state["fault"] is not None:
            return result("error", drill_entries(order, entries), started, state["fault"], files)
        for path in code_paths:
            entry = by_path[path]
            if entry["status"] == "":
                entry["status"] = "timeout"
            files.append(entry)
        if state["stopped"] is not None:
            return result(
                "error",
                drill_entries(order, entries),
                started,
                timeout_detail(state["stopped"], entries, order, timeout, code_paths),
                files,
            )
        status, detail = overall(files)
        return result(status, drill_entries(order, entries), started, detail, files)
    finally:
        for tree in trees:
            git(repo_dir, "worktree", "remove", "--force", tree)
        git(repo_dir, "worktree", "prune")
        shutil.rmtree(tmp, ignore_errors=True)


def timeout_detail(error, entries, order, timeout, code_paths):
    reverted = 0
    for entry in entries.values():
        if entry["reverted_ok"] is not None:
            reverted += 1
    return (
        str(error)
        + " "
        + str(len(entries))
        + " of "
        + str(len(order))
        + " selected drills ran with the change, "
        + str(reverted)
        + " ran reverted; the budget was "
        + str(timeout)
        + " s for "
        + str(len(code_paths))
        + " code files."
    )
