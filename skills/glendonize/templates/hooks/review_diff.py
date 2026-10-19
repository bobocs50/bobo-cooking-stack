"""PreToolUse hook: a commit that touches code is reviewed by agents before it
lands, and a confirmed defect blocks it until it is fixed or answered (D-123).

Claude Code passes the tool call (Bash or PowerShell) as JSON on stdin; the
command is in tool_input.command. Flow for a command that runs `git commit`:

1. Refuse what cannot be reviewed: a command that stages and commits in one go
   (`git add ... && git commit`, `-a`, a pathspec) because the staged diff at
   hook time would not be what lands, and `--amend` on a code commit.
2. Staged diff = `git diff --cached --binary --no-color --no-ext-diff`. A diff
   that touches none of main/ eval/ tests/ frontend/ .github/ .claude/hooks/
   passes untouched, with no trailer.
3. Three finders (A bugs, B rules, C silent values) run as separate headless
   `claude -p` processes in parallel, then one verifier per `defect` finding,
   also in parallel. That full review is for a diff touching main/ or
   .claude/hooks/; any other reviewed diff gets finder A alone on
   PROJECT_REVIEW_LIGHT_MODEL (default sonnet), with the same verifier (D-125). A confirmed defect needs evidence; confirmed without
   evidence counts as not confirmed. Questions are logged, not verified.
4. A confirmed defect that the commit message does not answer with a line
   `review: <finding id> - not a defect because ...` denies the commit. Anything
   else is allowed, and the command is rewritten with
   `--trailer "Agent-Review: <pass|answered|skipped> <12 hex> <model-tier or ->"`,
   e.g. `opus-full` or `sonnet-light` (D-125).
5. A review that did not run (claude missing, timeout, unparseable output)
   denies: a check reported as run that was skipped is a defect (AGENTS.md
   "Reviewing a diff"). The user alone sets PROJECT_REVIEW_SKIP=1 in the command
   for the trailer `skipped`. PROJECT_REVIEW_CHILD=1 (set for the child processes)
   makes the hook do nothing, so a child's own hooks cannot recurse.

Every review appends one JSON line to .claude/orchestration/review_log.jsonl.
The findings and verdicts are kept in .claude/orchestration/review_cache.json
(PROJECT_REVIEW_CACHE) by staged diff, model and briefs, so the retry after a
`review:` answer sees the same ids instead of a fresh run.
PROJECT_REVIEW_MODEL picks the model (default opus). PROJECT_REVIEW_STUB=<json file>
replaces every claude call with canned answers
{"A": [...], "B": [...], "C": [...], "verify": {"<finding id>": {...}}} for the
drill; finding ids are assigned by this hook as the role letter and the
position from 1 (A1, A2, B1 ...).

Verified against the Claude Code docs on 2026-10-19 (code.claude.com/docs/en/hooks,
/cli-reference, /headless):
- hook output: {"hookSpecificOutput": {"hookEventName": "PreToolUse",
  "permissionDecision": "allow"|"deny"|"ask"|"defer", "permissionDecisionReason":
  "...", "updatedInput": {...}}}. updatedInput "replaces the entire input
  object, so include unchanged fields alongside modified ones", and is paired
  with "allow". Exit 0 with no output leaves the normal permission flow.
- child call: `claude -p --model M --output-format json --allowedTools
  Read,Grep,Glob --disallowedTools Bash,Edit,Write,... --permission-mode dontAsk
  --no-session-persistence`, prompt on stdin; the answer text is the `result`
  field of the JSON. --bare is not used: it skips the subscription login.
"""

import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
REPO_ROOT = HOOK_DIR.parent.parent
BRIEFS = HOOK_DIR / "review_briefs"
LOG = REPO_ROOT / ".claude" / "orchestration" / "review_log.jsonl"
CACHE = REPO_ROOT / ".claude" / "orchestration" / "review_cache.json"

SCOPE = ("main/", "eval/", "tests/", "frontend/", ".github/", ".claude/hooks/")
# A wrong line here is a silent wrong value in a record or a hole in the review itself,
# so it gets all three finders; the rest of SCOPE gets the bug finder alone (D-125).
HIGH_RISK = ("main/", ".claude/hooks/")
ROLES = ("A", "B", "C")
LIGHT_ROLES = ("A",)
BRIEF_FILES = {
    "A": "A_bugs.md",
    "B": "B_rules.md",
    "C": "C_silent_values.md",
    "verify": "verifier.md",
}
CHILD_TIMEOUT = 300
ALLOWED_TOOLS = "Read,Grep,Glob"
DISALLOWED_TOOLS = "Bash,PowerShell,Edit,Write,NotebookEdit,WebFetch,WebSearch"

NOTES_ONLY = ("notes/", "README", "CLAUDE.md", "AGENTS.md")
# Anywhere in the command, on purpose: a commit wrapped in `time`, `{ }`, `if`, `env` or
# `bash -c` must not slip past the review. The cost is a false block when the words sit in
# an echo or a grep; write that text with the edit tool instead (D-123).
COMMIT = re.compile(r"\bgit\s+(?:-[A-Za-z]\s+\S+\s+)*commit\b")
STAGERS = re.compile(r"^\s*git\s+(?:-[A-Za-z]\s+\S+\s+)*(add|rm|mv)\b(.*)$")
SKIP = re.compile(r"PROJECT_REVIEW_SKIP\s*=\s*[\"']?1")
ANSWER = re.compile(
    r"review:\s*([A-Za-z]\d+)\s*(?:-+|—|–)\s*not a defect because\s+\S", re.IGNORECASE
)
DIFF_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$", re.MULTILINE)
QUOTED_HEADER = re.compile(r'^diff --git .*"', re.MULTILINE)
VALUE_FLAGS = {
    "-m",
    "-F",
    "-C",
    "-c",
    "-t",
    "--message",
    "--file",
    "--author",
    "--date",
    "--trailer",
    "--template",
    "--cleanup",
    "--reuse-message",
    "--reedit-message",
}
VALUE_LETTERS = "mFCct"


class ReviewError(Exception):
    """The review could not run or its answer could not be read."""


def commit_match(command):
    return COMMIT.search(command)


def commit_found(command):
    """The git commit match, for the helpers that run only after one was found."""
    match = COMMIT.search(command)
    if match is None:
        raise ReviewError("no git commit in the command")
    return match


def commit_args(command):
    """Option tokens of the git commit, quoted values and the heredoc removed."""
    match = commit_found(command)
    rest = command[match.end() :]
    for cut in ("$(", "<<"):
        position = rest.find(cut)
        if position != -1:
            rest = rest[:position]
    rest = re.sub(r'"[^"]*"', " QUOTED ", rest)
    rest = re.sub(r"'[^']*'", " QUOTED ", rest)
    rest = rest.replace('"', " ").replace("'", " ")
    rest = re.split(r"&&|\|\||[;|\n]", rest)[0]
    return rest.split()


def has_all_flag(tokens):
    for token in tokens:
        if token == "--all":
            return True
        if token.startswith("-") and not token.startswith("--"):
            for letter in token[1:]:
                if letter == "a":
                    return True
                if letter in VALUE_LETTERS:
                    break
    return False


def has_pathspec(tokens):
    skip_next = False
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if token == "--":
            return True
        if ">" in token or "<" in token:
            continue
        if token.startswith("-"):
            if token in VALUE_FLAGS:
                skip_next = True
            elif not token.startswith("--") and token[-1] in VALUE_LETTERS and len(token) > 2:
                skip_next = True
            continue
        return True
    return False


def stages_code(command):
    """True when a git add/rm/mv before the commit stages anything but notes and the root documents."""
    before = command[: commit_found(command).start()]
    for segment in re.split(r"&&|\|\||[;\n|]", before):
        match = STAGERS.match(segment)
        if match is None:
            continue
        if match.group(1) != "add":
            return True
        for token in match.group(2).split():
            token = token.strip("\"'").replace("\\", "/")
            if token.startswith("./"):
                token = token[2:]
            if token.startswith("-") or not token.startswith(NOTES_ONLY):
                return True
    return False


def stages_any(command):
    """True when the command runs a git add/rm/mv before the commit."""
    before = command[: commit_found(command).start()]
    for segment in re.split(r"&&|\|\||[;\n|]", before):
        if STAGERS.match(segment) is not None:
            return True
    return False


def diff_paths(staged_diff):
    paths = []
    for old, new in DIFF_HEADER.findall(staged_diff):
        paths.append(old)
        paths.append(new)
    return paths


def has_quoted_path(staged_diff):
    """Git quotes a path with special characters ("a/main/\\303\\244.py"), which DIFF_HEADER
    cannot read; such a diff is treated as code and as high risk, never as notes (D-125)."""
    return QUOTED_HEADER.search(staged_diff) is not None


def touches_scope(staged_diff):
    if has_quoted_path(staged_diff):
        return True
    for path in diff_paths(staged_diff):
        if path.startswith(SCOPE):
            return True
    return False


def diff_hash(staged_diff):
    return hashlib.sha256(staged_diff.encode("utf-8", "surrogateescape")).hexdigest()[:12]


def with_trailer(command, verdict, hash12, model):
    model = re.sub(r"[^\w.\[\]-]", "", model) or "-"
    trailer = f'--trailer "Agent-Review: {verdict} {hash12} {model}"'
    match = commit_found(command)
    return command[: match.end()] + " " + trailer + command[match.end() :]


def confirmed_defects(findings, verdicts):
    """Defect findings whose verifier confirmed them with evidence."""
    confirmed = []
    for finding in findings:
        if finding.get("kind") != "defect":
            continue
        verdict = verdicts.get(finding["id"])
        if not isinstance(verdict, dict):
            continue
        evidence = verdict.get("evidence")
        if verdict.get("confirmed") is True and isinstance(evidence, str) and evidence.strip():
            confirmed.append(finding)
    return confirmed


def precheck(command, staged_diff, model):
    """The decision that needs no agent (not a commit, a refusal, out of scope, the skip),
    or None when the agents must run."""
    if commit_match(command) is None:
        return ("pass", None, None)
    tokens = commit_args(command)
    hash12 = diff_hash(staged_diff)
    skip = SKIP.search(command) is not None
    reason = None
    if has_all_flag(tokens):
        reason = "`git commit -a` stages inside the commit"
    elif has_pathspec(tokens):
        reason = "`git commit <pathspec>` commits files the staged diff does not show"
    elif stages_code(command):
        reason = "the command stages code and commits in one call"
    if reason is not None:
        if skip:
            return (
                "allow",
                "review skipped on the user's word (D-123)",
                with_trailer(command, "skipped", hash12, "-"),
            )
        return (
            "deny",
            f"blocked: {reason}, so the staged diff the reviewers see would not be what lands. "
            "Stage in a separate call first, then commit with a plain `git commit -m ...` (D-123).",
            None,
        )
    if not touches_scope(staged_diff):
        return ("pass", None, None)
    if stages_any(command) and not skip:
        # The hash is taken before the add runs, so what lands would not match the stamp.
        return (
            "deny",
            "blocked: code is already staged and the command stages more before committing, so "
            "the added files would land unreviewed and the Agent-Review hash would not match. "
            "Stage in a separate call first, then commit with a plain `git commit -m ...` (D-123).",
            None,
        )
    if "--amend" in tokens:
        return (
            "deny",
            "blocked: --amend on a code commit rewrites a commit the reviewers did not see. "
            "Make a new commit instead (D-123).",
            None,
        )
    if skip:
        return (
            "allow",
            "review skipped on the user's word (D-123)",
            with_trailer(command, "skipped", hash12, "-"),
        )
    return None


def decide(command, staged_diff, findings, verdicts, model="opus"):
    """(decision, reason, new_command): ('pass', None, None) lets the command through
    untouched, ('allow', reason, new_command) rewrites it with the trailer, ('deny',
    reason, None) blocks it (D-123)."""
    early = precheck(command, staged_diff, model)
    if early is not None:
        return early
    hash12 = diff_hash(staged_diff)
    answered = {}
    for found in ANSWER.finditer(command):
        answered[found.group(1).upper()] = True
    confirmed = confirmed_defects(findings, verdicts)
    open_defects = []
    for finding in confirmed:
        if finding["id"].upper() not in answered:
            open_defects.append(finding)
    if open_defects:
        lines = []
        for finding in open_defects:
            lines.append(
                f"- [{finding['id']}] {finding.get('file')}:{finding.get('line')} "
                f"{finding.get('claim')} (evidence: {verdicts[finding['id']]['evidence']})"
            )
        return (
            "deny",
            "blocked: the agent review confirmed "
            + str(len(open_defects))
            + " defect(s) in the staged diff "
            + hash12
            + ":\n"
            + "\n".join(lines)
            + "\nFix it and stage again, or answer it in the commit message with a line "
            "`review: <finding id> - not a defect because ...`; the findings are kept for "
            "this staged diff, so the ids stay the same on the retry (D-123).",
            None,
        )
    verdict = "answered" if confirmed else "pass"
    return (
        "allow",
        f"agent review {verdict} on staged diff {hash12} (D-123)",
        with_trailer(command, verdict, hash12, model),
    )


def parse_answer(text):
    """JSON from a model answer, tolerating a code fence or a sentence around it."""
    text = text.strip()
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1).strip())
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except ValueError:
            continue
    raise ReviewError("the reviewer's answer is not JSON")


def call_claude(role, prompt, model):
    """One headless claude -p process with a fresh context and read-only tools."""
    exe = shutil.which("claude")
    if exe is None:
        raise ReviewError("the claude CLI is not on PATH")
    command = [
        exe,
        "-p",
        "--model",
        model,
        "--output-format",
        "json",
        "--allowedTools",
        ALLOWED_TOOLS,
        "--disallowedTools",
        DISALLOWED_TOOLS,
        "--permission-mode",
        "dontAsk",
        "--no-session-persistence",
    ]
    env = dict(os.environ)
    env["PROJECT_REVIEW_CHILD"] = "1"
    try:
        done = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=CHILD_TIMEOUT,
            env=env,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        raise ReviewError(f"reviewer {role} timed out after {CHILD_TIMEOUT} s")
    if done.returncode != 0:
        raise ReviewError(f"reviewer {role} exited {done.returncode}")
    try:
        outer = json.loads(done.stdout)
    except ValueError:
        raise ReviewError(f"reviewer {role} printed no JSON")
    if (
        not isinstance(outer, dict)
        or outer.get("is_error")
        or not isinstance(outer.get("result"), str)
    ):
        raise ReviewError(f"reviewer {role} returned an error result")
    return parse_answer(outer["result"])


def ask(role, key, prompt, model, stub):
    """The answer for one role: from the stub when there is one, else from claude."""
    if stub is not None:
        if role == "verify":
            answers = stub.get("verify")
            if not isinstance(answers, dict) or key not in answers:
                raise ReviewError(f"no stub verdict for {key}")
            return answers[key]
        if role not in stub:
            raise ReviewError(f"no stub answer for {role}")
        return stub[role]
    return call_claude(key, prompt, model)


def brief(role):
    return (BRIEFS / BRIEF_FILES[role]).read_text(encoding="utf-8")


def run_parallel(jobs):
    """Run [(name, function)] in threads; the results by name, ReviewError if any failed."""
    results = {}
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
        futures = {}
        for name, function in jobs:
            futures[pool.submit(function)] = name
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as error:
                failures.append(f"{name}: {error}")
    if failures:
        raise ReviewError("; ".join(sorted(failures)))
    return results


def tier(staged_diff):
    """('full', roles, model) when the diff touches HIGH_RISK, else ('light', roles, model)."""
    if has_quoted_path(staged_diff):
        return ("full", ROLES, os.environ.get("PROJECT_REVIEW_MODEL") or "opus")
    for path in diff_paths(staged_diff):
        if path.startswith(HIGH_RISK):
            return ("full", ROLES, os.environ.get("PROJECT_REVIEW_MODEL") or "opus")
    return ("light", LIGHT_ROLES, os.environ.get("PROJECT_REVIEW_LIGHT_MODEL") or "sonnet")


def find_and_verify(staged_diff, model, stub, roles=ROLES):
    """(findings, verdicts) from the finders, then one verifier per defect."""
    jobs = []
    for role in roles:
        prompt = brief(role) + "\n\n## Staged diff\n\n" + staged_diff
        jobs.append((role, lambda role=role, prompt=prompt: ask(role, role, prompt, model, stub)))
    found = run_parallel(jobs)
    findings = []
    for role in roles:
        items = found[role]
        if not isinstance(items, list):
            raise ReviewError(f"finder {role} did not return a JSON list")
        position = 0
        for item in items:
            if not isinstance(item, dict) or item.get("kind") not in ("defect", "question"):
                raise ReviewError(f"finder {role} returned a finding without kind defect|question")
            position += 1
            finding = dict(item)
            finding["id"] = f"{role}{position}"
            findings.append(finding)
    jobs = []
    for finding in findings:
        if finding["kind"] != "defect":
            continue
        prompt = (
            brief("verify")
            + "\n\n## Finding\n\n"
            + json.dumps(finding)
            + "\n\n## Staged diff\n\n"
            + staged_diff
        )
        jobs.append(
            (
                finding["id"],
                lambda finding=finding, prompt=prompt: ask(
                    "verify", finding["id"], prompt, model, stub
                ),
            )
        )
    verdicts = run_parallel(jobs) if jobs else {}
    for name, verdict in verdicts.items():
        if not isinstance(verdict, dict) or not isinstance(verdict.get("confirmed"), bool):
            raise ReviewError(f"verifier for {name} did not return {{confirmed: bool}}")
    return findings, verdicts


def staged_diff_of(cwd, amend):
    done = subprocess.run(
        ["git", "diff", "--cached", "--binary", "--no-color", "--no-ext-diff"],
        cwd=cwd,
        capture_output=True,
    )
    if done.returncode != 0:
        raise ReviewError("git diff --cached failed")
    text = done.stdout.decode("utf-8", "surrogateescape")
    if amend:
        # An amend lands HEAD's files too, so they decide the scope.
        shown = subprocess.run(
            ["git", "show", "--format=", "--name-only", "HEAD"], cwd=cwd, capture_output=True
        )
        for name in shown.stdout.decode("utf-8", "replace").split():
            text += f"\ndiff --git a/{name} b/{name}\n"
    return text


def cache_key(staged_diff, model):
    """Same staged diff, model and briefs: same review. Finding ids are positional, so a
    retry with a `review:` answer must see the findings it answers, not a fresh run."""
    briefs = hashlib.sha256()
    for name in sorted(BRIEF_FILES.values()):
        briefs.update((BRIEFS / name).read_bytes())
    return f"{diff_hash(staged_diff)}:{model}:{briefs.hexdigest()[:12]}"


def cache_path():
    return Path(os.environ.get("PROJECT_REVIEW_CACHE") or CACHE)


def read_cache():
    try:
        entries = json.loads(cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(entries, dict):
        return {}
    return entries


def cached_review(key):
    """(findings, verdicts) of an earlier review with the same key, or None."""
    entry = read_cache().get(key)
    if not isinstance(entry, dict):
        return None
    findings = entry.get("findings")
    verdicts = entry.get("verdicts")
    if not isinstance(findings, list) or not isinstance(verdicts, dict):
        return None
    return findings, verdicts


def store_review(key, findings, verdicts):
    entries = read_cache()
    entries[key] = {"findings": findings, "verdicts": verdicts}
    try:
        path = cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries), encoding="utf-8")
    except OSError:
        pass


def write_log(entry):
    path = Path(os.environ.get("PROJECT_REVIEW_LOG") or LOG)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def review(command, staged_diff):
    """The full decision for one command: pre-checks, agents, verdict, log line."""
    level, roles, model = tier(staged_diff)
    if commit_match(command) is None:
        return ("pass", None, None)
    early = precheck(command, staged_diff, model)
    if early is not None:
        return early
    stub = None
    if os.environ.get("PROJECT_REVIEW_STUB"):
        stub = json.loads(Path(os.environ["PROJECT_REVIEW_STUB"]).read_text(encoding="utf-8"))
    key = cache_key(staged_diff, model) + ":" + level
    cached = cached_review(key)
    try:
        if cached is not None:
            findings, verdicts = cached
        else:
            findings, verdicts = find_and_verify(staged_diff, model, stub, roles)
            store_review(key, findings, verdicts)
    except ReviewError as error:
        write_log(
            {
                "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "diff_hash": diff_hash(staged_diff),
                "error": str(error),
            }
        )
        return (
            "deny",
            f"blocked: the agent review did not run ({error}). A review that did not run must not pass "
            "silently; retry, or the user sets PROJECT_REVIEW_SKIP=1 (D-123).",
            None,
        )
    # The stamp names the tier too, so `git log` shows which review a commit got (D-125).
    result = decide(command, staged_diff, findings, verdicts, model + "-" + level)
    answered = []
    for found in ANSWER.finditer(command):
        answered.append(found.group(1).upper())
    write_log(
        {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "diff_hash": diff_hash(staged_diff),
            "model": model,
            "level": level,
            "decision": result[0],
            "cached": cached is not None,
            "findings": findings,
            "verdicts": verdicts,
            "answered": answered,
        }
    )
    return result


def main():
    if os.environ.get("PROJECT_REVIEW_CHILD") == "1":
        return 0
    try:
        call = json.load(sys.stdin)
        tool_input = call["tool_input"]
        command = tool_input["command"]
    except Exception:
        return 0
    if commit_match(command) is None:
        return 0
    cwd = call.get("cwd") or os.getcwd()
    try:
        staged = staged_diff_of(cwd, "--amend" in commit_args(command))
        decision, reason, new_command = review(command, staged)
    except Exception as error:
        decision, reason, new_command = (
            "deny",
            f"blocked: the agent review hook failed ({error}); a review that did not run must not pass (D-123).",
            None,
        )
    if decision == "pass":
        return 0
    output = {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }
    if decision == "allow":
        updated = dict(tool_input)
        updated["command"] = new_command
        output["updatedInput"] = updated
    print(json.dumps({"hookSpecificOutput": output}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
