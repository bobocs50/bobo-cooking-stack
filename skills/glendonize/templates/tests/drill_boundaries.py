"""Boundary checks over the repo's own source text. Runs nothing, spends nothing.

    python tests/drill_boundaries.py

Files are read as text and never imported, so no check here can trigger a paid
call. Comments may explain why a rule exists; code may not reach past it, so the
vocabulary scans strip comments and docstrings first.

Each check is a rule someone holds, not a style preference:
  0. self-guard        - a scan over a moved or emptied tree must fail loudly
  1. spine isolation   - main/ depends on no periphery
  2. one wire          - http_retry.py is the only caller that reaches out (D-024)
  3. private paths     - proprietary data is ignored AND untracked (R4)
  4. the gate cannot pay - no secrets, no deny-listed script in CI (AGENTS.md)
  5. citations resolve - every cited R/D/Q id and notes/*.md path exists in a clone,
                         main/ and the root AGENTS.md / CLAUDE.md included (D-023)
  (4b) the three paid-script lists agree - this drill, the hook, verify.yml (D-074)
  6. the import holds  - CLAUDE.md's @AGENTS.md target is tracked (D-020),
                         and AGENTS.md stays at most 8 KiB (D-127)
  7. cost is labelled   - every eval/ file says in its docstring whether
                         it bills; a deny-listed one says PAID (AGENTS.md "Gates")
  8. every module is drilled - each main/ module is imported by a drill or listed
                         in tests/untested.txt, and a listed one is not (D-047)
  9. no drill lost a check - the count of expect( calls per tests/drill_*.py has not
                         dropped since the base commit (D-094)
"""

import ast
import io
import os
import re
import subprocess
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {
    ".git",
    ".claude",
    "node_modules",
    "__pycache__",
    "dist",
    ".venv",
    "venv",
    "ocr_cache",
    "uploads",
    "rendered_pages",
    "debug",
    "out",
    "gold",
}

# Everything under main/ that the pipeline runs on. Named so check 0 can tell a
# renamed tree from an empty one.
SPINE = {
    "api.py",
    "step3_classification.py",
    "criteria_catalog.py",
    "errors.py",
    "http_retry.py",
    "step4_extraction.py",
    "step1_parsing.py",
    "pipeline.py",
}

# The only file under main/ allowed to reach the network (D-024).
WIRE_ALLOWED = ["main/http_retry.py"]
# Tolerant of whitespace: code_only() rebuilds Python from tokens, so `requests.get`
# comes back as `requests . get`.
WIRE = re.compile(
    r"\brequests\s*\.\s*(get|post|put|patch|delete|head|request|Session|session)\b"
    r"|\bSession\s*\("
    r"|\bsession\s*\.\s*(get|post|put|patch|delete|head|request)\s*\("
    r"|\bhttpx\s*\.|\burlopen\s*\("
)

# Paths that hold proprietary reports or their OCR (R4). Each must be ignored
# and must have nothing tracked under it.
PRIVATE = [
    "documents/",
    "main/uploads/",
    "main/ocr_cache/",
    "main/debug/",
    "main/rendered_pages/",
    "eval/out/",
    "eval/gold/",
    "main/parsed_output.csv",
    "main/parsed_output.txt",
    "main/extraction_output.json",
    "main/layer2_cache/",
]

# Scripts that cost money. None of them may be named by a CI workflow. The main/
# ones are fixed; the eval/ ones are read off their `Cost: PAID` docstring by
# paid_eval_scripts(), and the two named here stay as a floor in case a docstring
# loses its label (AGENTS.md "Gates").
DENY_FIXED = [
    "step1_parsing.py",
    "pipeline.py",
    "api.py",
    "loop_run.py",
    "pn_run.py",
]

ID = re.compile(r"(?<![A-Za-z0-9_-])(R\d{1,2}|D-\d{3}|Q-\d{3})(?![A-Za-z0-9_-])")
NOTE_PATH = re.compile(r"(?<![\w/])((?:notes|docs)/[A-Za-z_]+\.md)")
# A citation may name a section: `notes/GROUNDING.md 3.1` (D-025).
NOTE_SECTION = re.compile(r"(?<![\w/])((?:notes|docs)/[A-Za-z_]+\.md) (\d+(?:\.\d+)*)")


def in_skipped(path):
    # Only the parts below ROOT count: a checkout that itself lives under a
    # skipped name (an agent worktree in .claude/worktrees/) would otherwise
    # scan nothing and trip the self-guard.
    for part in path.relative_to(ROOT).parts:
        if part in SKIP:
            return True
    # A nested worktree carries a .git *file*; it is a second copy of the repo
    # and every scan would count it twice.
    for parent in path.parents:
        if parent == ROOT:
            break
        if (parent / ".git").is_file():
            return True
    return False


def files(*roots, suffixes):
    found = []
    for root in roots:
        base = ROOT / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if in_skipped(path):
                continue
            if path.is_file() and path.suffix in suffixes:
                found.append(path)
    return found


def rel(path):
    return path.relative_to(ROOT).as_posix()


def imports(path):
    """Module names a file imports. ast never sees comments or docstrings."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def code_only(path):
    """Source with comments and docstrings removed, for vocabulary scans."""
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".py":
        text = re.sub(r"/\*[\s\S]*?\*/", "", text)
        return re.sub(r"(?m)(^|\s)//.*$", r"\1", text)
    kept = []
    previous = tokenize.INDENT
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            continue
        if token.type == tokenize.STRING and previous in (
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.NEWLINE,
            tokenize.NL,
        ):
            continue
        kept.append(token.string)
        if token.type not in (tokenize.NL, tokenize.NEWLINE):
            previous = token.type
    return " ".join(kept)


def paid_eval_scripts():
    found = []
    for path in files("eval", suffixes={".py"}):
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
        if re.search(r"(?m)^Cost: PAID - ", doc):
            found.append(path.name)
    return found


def ignore_lines():
    lines = set()
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.add(line)
    return lines


def expect(label, condition, detail=()):
    print(("  ok   " if condition else "  FAIL ") + label)
    for line in detail:
        print("         " + line)
    return condition


EXPECT_CALL = re.compile(r"(?m)^(?!\s*def )[^#\n]*\bexpect\(")


def count_expects(text):
    return len(EXPECT_CALL.findall(text))


def git_out(*args):
    result = subprocess.run(
        ["git"] + list(args), cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    return result.returncode, result.stdout


def ratchet_base():
    # CI names the push base; locally a dirty tests/ is compared with HEAD, a clean
    # one (the commit is already made) with its parent (D-094).
    named = os.environ.get("PROJECT_RATCHET_BASE", "").strip()
    if named and set(named) != {"0"}:
        return named
    code, _ = git_out("diff", "--quiet", "HEAD", "--", "tests/")
    if code == 0:
        return "HEAD~1"
    return "HEAD"


def tracked():
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout.split()


def doc_files():
    # A link is a claim about a clone: a gitignored private note on this disk must not
    # make a citation of it resolve (D-023). Untracked-but-not-ignored files count, so a
    # new note resolves before its first commit.
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return set(result.stdout.splitlines())


def register_ids():
    found = set()
    for name in ("REQUIREMENTS", "DECISIONS", "OPEN_QUESTIONS"):
        path = ROOT / "notes" / (name + ".md")
        if not path.exists():
            continue
        for match in re.findall(
            r"^## ((?:R\d+|D-\d{3}|Q-\d{3})) ", path.read_text(encoding="utf-8"), re.M
        ):
            found.add(match)
    return found


def main():
    passed = True
    print("boundary checks")

    # 0. A scan over a moved or emptied tree passes every other check vacuously.
    spine = files("main", suffixes={".py"})
    names = set()
    for path in spine:
        names.add(path.name)
    guard = expect("scanning >= 8 files under main/ (got %d)" % len(spine), len(spine) >= 8)
    missing = sorted(SPINE - names)
    guard &= expect("every load-bearing file of main/ is present", missing == [], missing)
    if not guard:
        print("")
        print("SELF-GUARD TRIPPED - nothing below is meaningful")
        raise SystemExit(1)

    # 1. main/ is the spine; eval/ and tests/ are periphery.
    periphery = set()
    for path in files("eval", "tests", suffixes={".py"}):
        periphery.add(path.stem)
    offending = []
    for path in spine:
        for module in sorted(imports(path)):
            if module.split(".")[0] in periphery:
                offending.append(rel(path) + ": " + module)
    passed &= expect("main/ imports nothing from eval/ or tests/", offending == [], offending)

    # 2. One chokepoint for every upstream call (D-024).
    reached = []
    for path in spine:
        if WIRE.search(code_only(path)):
            reached.append(rel(path))
    unexpected = sorted(set(reached) ^ set(WIRE_ALLOWED))
    passed &= expect(
        "main/http_retry.py is the only file in main/ that reaches the wire  (D-024)",
        sorted(reached) == sorted(WIRE_ALLOWED),
        unexpected,
    )

    # 3. Proprietary data is ignored and, more importantly, not already tracked (R4).
    ignored = ignore_lines()
    tracked_paths = tracked()
    for guarded in PRIVATE:
        leaked = []
        for entry in tracked_paths:
            if entry == guarded or entry.startswith(guarded):
                leaked.append(entry)
        listed = guarded in ignored or "/" + guarded in ignored
        passed &= expect(
            "%-28s ignored and untracked  (R4)" % guarded,
            listed and leaked == [],
            leaked or ([] if listed else ["no exact line in .gitignore"]),
        )

    # 4. The gate cannot pay, even by accident (AGENTS.md "Gates").
    deny_listed = sorted(set(DENY_FIXED) | set(paid_eval_scripts()))
    workflows = files(".github/workflows", suffixes={".yml", ".yaml"})
    if not workflows:
        print("  --   no CI workflow yet; check 4 has nothing to read")
    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        body = re.sub(r"(?m)^\s*#.*$", "", text)
        found = []
        if "secrets." in body:
            found.append("reads secrets.")
        for script in deny_listed:
            if script in body:
                found.append("names " + script)
        passed &= expect(
            rel(workflow) + " holds no secrets and names no paid script", found == [], found
        )

    # 4b. Three hand lists name the paid scripts: this drill's (docstring-derived), the
    # hook's and the workflow's header. A script added to one and not the others is
    # allowed by the hook or unwarned in CI without any check failing (D-074, D-047).
    hook_text = (ROOT / ".claude" / "hooks" / "guard_paid_run.py").read_text(encoding="utf-8")
    hook_block = re.search(r"PAID_SCRIPTS\s*=\s*\(([^)]*)\)", hook_text)
    hook_names = []
    if hook_block is not None:
        hook_names = re.findall(r"[\"']([\w]+)[\"']", hook_block.group(1))
    header = ""
    for line in (
        (ROOT / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8").splitlines()
    ):
        if not line.startswith("#"):
            break
        header += line + "\n"
    not_in_hook = []
    not_in_header = []
    for script in deny_listed:
        if script[: -len(".py")] not in hook_names:
            not_in_hook.append(script)
        if script not in header:
            not_in_header.append(script)
    passed &= expect(
        "every deny-listed script is in the hook's PAID_SCRIPTS  (D-074)",
        hook_names != [] and not_in_hook == [],
        ["missing from guard_paid_run.py: " + name for name in not_in_hook]
        or ([] if hook_names else ["PAID_SCRIPTS not found in guard_paid_run.py"]),
    )
    passed &= expect(
        "every deny-listed script is in verify.yml's never-run header  (D-074)",
        header != "" and not_in_header == [],
        ["missing from verify.yml header: " + name for name in not_in_header]
        or ([] if header else ["no header comment in verify.yml"]),
    )

    # 5. A register nothing can reach is a register that rots (D-023).
    known = register_ids()
    sources = files(
        "main", "eval", "tests", "notes", "frontend/src", suffixes={".py", ".ts", ".tsx", ".md"}
    )
    for root_doc in ("AGENTS.md", "CLAUDE.md"):
        sources.append(ROOT / root_doc)
    clone_files = doc_files()
    dangling = []
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for cited in sorted(set(ID.findall(text))):
            if cited not in known:
                dangling.append(rel(path) + ": " + cited)
        for cited in sorted(set(NOTE_PATH.findall(text))):
            if cited not in clone_files:
                dangling.append(rel(path) + ": " + cited)
        for doc, section in sorted(set(NOTE_SECTION.findall(text))):
            target = ROOT / doc
            if doc not in clone_files:
                continue  # already reported by the path check above
            heading = re.compile(r"(?m)^#+ " + re.escape(section) + r"(\.\s|\s)")
            if not heading.search(target.read_text(encoding="utf-8")):
                dangling.append(rel(path) + ": " + doc + " " + section)
    passed &= expect(
        "every cited id, notes/ path and section resolves  (D-025)", dangling == [], dangling
    )

    # Two parallel sessions both wrote D-086 and D-087 on 2026-10-08; a cited id
    # then resolves to two decisions and the check above cannot see it (D-090).
    duplicated = []
    for name in ("REQUIREMENTS", "DECISIONS", "OPEN_QUESTIONS"):
        path = ROOT / "notes" / (name + ".md")
        if not path.exists():
            continue
        seen = set()
        for match in re.findall(
            r"^## ((?:R\d+|D-\d{3}|Q-\d{3})) ", path.read_text(encoding="utf-8"), re.M
        ):
            if match in seen:
                duplicated.append("notes/" + name + ".md: " + match)
            seen.add(match)
    passed &= expect("every register id is defined once  (D-090)", duplicated == [], duplicated)

    # 6. CLAUDE.md imports AGENTS.md; a fresh clone must have it (D-020).
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    imported = "@AGENTS.md" in claude
    passed &= expect(
        "CLAUDE.md's @AGENTS.md target is tracked  (D-020)",
        not imported or "AGENTS.md" in tracked_paths,
    )
    # Every agent loads AGENTS.md into its context on every turn, so it is capped (D-127).
    agents_size = (ROOT / "AGENTS.md").stat().st_size
    passed &= expect(
        "AGENTS.md is at most 8192 bytes  (D-127)",
        agents_size <= 8192,
        ["AGENTS.md is " + str(agents_size) + " bytes"],
    )

    # 7. Whether a script bills is read off its own docstring, not remembered
    # (AGENTS.md "Gates").
    unlabelled = []
    for path in files("eval", suffixes={".py"}):
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
        label = re.search(r"(?m)^Cost: (free|PAID) - ", doc)
        if label is None:
            unlabelled.append(rel(path) + ": no 'Cost: free - ' or 'Cost: PAID - ' line")
        elif path.name in deny_listed and label.group(1) != "PAID":
            unlabelled.append(rel(path) + ": deny-listed but labelled free")
    passed &= expect(
        'every eval/ file carries a Cost line  (AGENTS.md "Gates")',
        unlabelled == [],
        unlabelled,
    )

    # 8. A module with logic and no drill is a silent wrong value waiting to happen;
    # the list of exceptions may only shrink (D-047).
    drill_source = ""
    for path in files("tests", suffixes={".py"}):
        if path.name.startswith("drill_"):
            drill_source += code_only(path) + "\n"
    listed = []
    for line in (ROOT / "tests" / "untested.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            listed.append(line)
    unpaired = []
    for path in spine:
        module = path.stem
        imported = (
            re.search(r"\b(?:import|from)\s+" + re.escape(module) + r"\b", drill_source) is not None
        )
        is_listed = rel(path) in listed
        if not imported and not is_listed:
            unpaired.append(rel(path) + ": no drill imports it and it is not in tests/untested.txt")
        if imported and is_listed:
            unpaired.append(
                rel(path) + ": a drill imports it now - remove it from tests/untested.txt"
            )
    for entry in listed:
        if not (ROOT / entry).exists():
            unpaired.append(entry + ": listed in tests/untested.txt but does not exist")
    passed &= expect(
        "every main/ module is imported by a drill or listed in tests/untested.txt  (D-047)",
        unpaired == [],
        unpaired,
    )

    # 9. Deleting a check from a drill makes the gate greener, not safer; 57 went in
    # one commit with nothing noticing (D-094).
    base = ratchet_base()
    code, _ = git_out("rev-parse", "--verify", "--quiet", base + "^{commit}")
    if code != 0:
        print("  --   base " + base + " not found; check 9 has nothing to compare")
    else:
        lost = []
        deltas = []
        _, listing = git_out("ls-tree", "-r", "--name-only", base, "--", "tests/")
        base_drills = []
        for name in listing.splitlines():
            if re.fullmatch(r"tests/drill_[^/]*\.py", name):
                base_drills.append(name)
        for name in base_drills:
            now_path = ROOT / name
            _, before_text = git_out("show", base + ":" + name)
            before = count_expects(before_text)
            if not now_path.exists():
                lost.append(
                    name + ": existed at " + base + " with " + str(before) + " checks, now gone"
                )
                continue
            after = count_expects(now_path.read_text(encoding="utf-8"))
            if after != before:
                deltas.append(name + ": " + str(before) + " -> " + str(after))
            if after < before:
                lost.append(name + ": " + str(before) + " -> " + str(after) + " expect( calls")
        # A deliberate removal says so in the subject, which CI can read; the env var
        # is for the local run before the commit exists (D-094).
        _, subject = git_out("log", "-1", "--format=%s")
        allowed = os.environ.get("PROJECT_DRILL_DROP_OK") == "1" or "drop drill:" in subject
        detail = []
        for line in deltas:
            detail.append("delta vs " + base + "  " + line)
        for line in lost:
            detail.append("LOST  " + line)
        passed &= expect(
            "no drill lost a check since " + base + "  (D-094)", lost == [] or allowed, detail
        )

    print("")
    print("ALL PASSED" if passed else "SOME FAILED")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
