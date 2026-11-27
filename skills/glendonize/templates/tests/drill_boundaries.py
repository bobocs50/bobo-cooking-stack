"""Boundary checks over the repo's own source text. Runs nothing, spends nothing.

    python tests/drill_boundaries.py

Cost: free - reads tracked source as text, makes no network call.

Files are read as text and never imported, so no check here can trigger a paid
call. Comments may explain why a rule exists; code may not reach past it, so the
vocabulary scans strip comments and docstrings first.

Adapt per repo: the constants below name the spine dir, the periphery, the one file allowed
to reach the network, the private paths and the fixed deny-list; keep only the checks the
Phase 0 rulings confirmed. Each check is a rule someone holds, not a style preference:
  0. self-guard        - a scan over a moved or emptied tree must fail loudly
  1. spine isolation   - the spine imports nothing from the periphery
  2. one wire          - no requests/httpx/urlopen call in the spine outside WIRE_ALLOWED,
                         and no vendor SDK import outside SDK_ALLOWED
  3. private paths     - private data is ignored AND untracked
  4. the gate cannot pay - no secrets, no deny-listed script in CI (AGENTS.md)
  (4b) the three paid-script lists agree - this drill, the hook, verify.yml, in both directions
  5. citations resolve - every cited R/D/Q id and docs/*.md path exists in a clone, the spine,
                         the root AGENTS.md / CLAUDE.md, the hooks and the review briefs included
  6. the import holds  - CLAUDE.md's @AGENTS.md target is tracked, and AGENTS.md stays at
                         most 8 KiB (line endings normalised)
  7. cost is labelled  - every file of the paid dir says in its docstring whether it bills;
                         a deny-listed one says PAID
  8. every module is drilled - each spine module is imported by a drill (read from the drills'
                         import statements, dotted path included) or listed in
                         tests/untested.txt, and a listed one is not
  9. no drill lost a check - the count of expect( calls per tests/drill_*.py has not dropped
                         since the base commit, a renamed drill followed to its new name, and
                         no commit of the pushed range drops one without `drop drill:` in its
                         own subject (tests/commit_range.py)
"""

import ast
import io
import os
import re
import subprocess
import tempfile
import tokenize
from pathlib import Path

from commit_range import commits_between, drill_renames, unannounced_drops

ROOT = Path(__file__).resolve().parent.parent
SKIP = {
    ".git",
    ".claude",
    "node_modules",
    "__pycache__",
    "dist",
    ".venv",
    "venv",
    "private_data",
}

SPINE_DIR = "src"
PERIPHERY_DIRS = ("scripts", "tests")
COST_DIR = "scripts"
DOCS_DIR = "docs"

# Everything under the spine dir that the product runs on, relative to it. Named so
# check 0 can tell a renamed tree from an empty one.
SPINE = {
    "app.py",
    "core.py",
}

# The only files of the spine allowed to reach the network.
WIRE_ALLOWED = ["src/http_client.py"]
# Tolerant of whitespace: code_only() rebuilds Python from tokens, so `requests.get`
# comes back as `requests . get`.
WIRE = re.compile(
    r"\brequests\s*\.\s*(get|post|put|patch|delete|head|request|Session|session)\b"
    r"|\bSession\s*\("
    r"|\bsession\s*\.\s*(get|post|put|patch|delete|head|request)\s*\("
    r"|\bhttpx\s*\.|\burlopen\s*\("
)
# A vendor SDK kept behind a few modules; leave SDK_MODULE empty when there is none.
SDK_MODULE = "vendor_sdk"
SDK_ALLOWED = ["src/storage.py"]

# Paths that hold data this repo must never publish. Each must be ignored and must have
# nothing tracked under it.
PRIVATE = [
    "private_data/",
]

# Scripts that cost money. None of them may be named by a CI workflow. These are fixed;
# the ones in COST_DIR are read off their `Cost: PAID` docstring by paid_scripts(), and
# the names here stay as a floor in case a docstring loses its label (AGENTS.md "Gates").
DENY_FIXED = [
    "paid_script.py",
]

ID = re.compile(r"(?<![A-Za-z0-9_-])(R\d{1,2}|D-\d{3}|Q-\d{3})(?![A-Za-z0-9_-])")
DOC_PATH = re.compile(r"(?<![\w/])(" + DOCS_DIR + r"/[A-Za-z_]+\.md)")
# A citation may name a section: `docs/X.md 3.1`.
DOC_SECTION = re.compile(r"(?<![\w/])(" + DOCS_DIR + r"/[A-Za-z_]+\.md) (\d+(?:\.\d+)*)")


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


def harness_sources(base):
    # The hooks and the review briefs cite ids too; a scan that stops at the product code
    # lets a dangling id sit in them for good.
    found = []
    patterns = (
        (".claude/hooks", "*.py"),
        (".claude/hooks/ship_briefs", "*.md"),
        (".githooks", "*.py"),
    )
    for folder, pattern in patterns:
        directory = base / folder
        if directory.is_dir():
            found.extend(sorted(directory.glob(pattern)))
    return found


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


def paid_scripts():
    found = []
    for path in files(COST_DIR, suffixes={".py"}):
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
    # one (the commit is already made) with its parent.
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
    # make a citation of it resolve. Untracked-but-not-ignored files count, so a new
    # note resolves before its first commit.
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
        path = ROOT / DOCS_DIR / (name + ".md")
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
    spine = files(SPINE_DIR, suffixes={".py"})
    names = set()
    for path in spine:
        names.add(path.relative_to(ROOT / SPINE_DIR).as_posix())
    guard = expect(
        "scanning >= %d files under %s/ (got %d)" % (len(SPINE), SPINE_DIR, len(spine)),
        len(spine) >= len(SPINE),
    )
    missing = sorted(SPINE - names)
    guard &= expect("every load-bearing file of " + SPINE_DIR + "/ is present", missing == [], missing)
    if not guard:
        print("")
        print("SELF-GUARD TRIPPED - nothing below is meaningful")
        raise SystemExit(1)

    # 1. The spine is the product; the periphery depends on it, never the reverse.
    periphery = set()
    for path in files(*PERIPHERY_DIRS, suffixes={".py"}):
        periphery.add(path.stem)
    offending = []
    for path in spine:
        for module in sorted(imports(path)):
            if module.split(".")[0] in periphery:
                offending.append(rel(path) + ": " + module)
    passed &= expect(
        SPINE_DIR + "/ imports nothing from " + " or ".join(PERIPHERY_DIRS), offending == [], offending
    )

    # 2. One chokepoint for every upstream call, and one for the vendor SDK.
    reached = []
    for path in spine:
        if WIRE.search(code_only(path)):
            reached.append(rel(path))
    unexpected = sorted(set(reached) ^ set(WIRE_ALLOWED))
    passed &= expect(
        "no requests/httpx/urlopen call in " + SPINE_DIR + "/ outside " + ", ".join(WIRE_ALLOWED),
        sorted(reached) == sorted(WIRE_ALLOWED),
        unexpected,
    )
    if SDK_MODULE:
        sdk_outside = []
        for path in spine:
            if rel(path) in SDK_ALLOWED:
                continue
            for module in sorted(imports(path)):
                if module == SDK_MODULE or module.startswith(SDK_MODULE + "."):
                    sdk_outside.append(rel(path) + ": " + module)
        passed &= expect(
            "no " + SDK_MODULE + " import in " + SPINE_DIR + "/ outside " + ", ".join(SDK_ALLOWED),
            sdk_outside == [],
            sdk_outside,
        )

    # 3. Private data is ignored and, more importantly, not already tracked.
    ignored = ignore_lines()
    tracked_paths = tracked()
    for guarded in PRIVATE:
        leaked = []
        for entry in tracked_paths:
            if entry == guarded or entry.startswith(guarded):
                leaked.append(entry)
        listed = guarded in ignored or "/" + guarded in ignored
        passed &= expect(
            "%-28s ignored and untracked" % guarded,
            listed and leaked == [],
            leaked or ([] if listed else ["no exact line in .gitignore"]),
        )

    # 4. The gate cannot pay, even by accident (AGENTS.md "Gates").
    deny_listed = sorted(set(DENY_FIXED) | set(paid_scripts()))
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
    # allowed by the hook or unwarned in CI without any check failing.
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

    def in_header(script):
        # A name that is the tail of another (`run.py` in `pn_run.py`) must not count.
        return re.search(r"(?<![\w])" + re.escape(script), header) is not None

    not_in_hook = []
    not_in_header = []
    for script in deny_listed:
        if script[: -len(".py")] not in hook_names:
            not_in_hook.append(script)
        if not in_header(script):
            not_in_header.append(script)
    passed &= expect(
        "every deny-listed script is in the hook's PAID_SCRIPTS",
        hook_names != [] and not_in_hook == [],
        ["missing from guard_paid_run.py: " + name for name in not_in_hook]
        or ([] if hook_names else ["PAID_SCRIPTS not found in guard_paid_run.py"]),
    )
    not_denied = []
    for name in hook_names:
        if name + ".py" not in deny_listed:
            not_denied.append(name + ".py")
    passed &= expect(
        "every script in the hook's PAID_SCRIPTS is deny-listed here",
        not_denied == [],
        ["missing from DENY_FIXED or a Cost: PAID docstring: " + name for name in not_denied],
    )
    passed &= expect(
        "every deny-listed script is in verify.yml's never-run header",
        header != "" and not_in_header == [],
        ["missing from verify.yml header: " + name for name in not_in_header]
        or ([] if header else ["no header comment in verify.yml"]),
    )

    # 5. A register nothing can reach is a register that rots.
    known = register_ids()
    sources = files(
        SPINE_DIR, COST_DIR, "tests", DOCS_DIR, suffixes={".py", ".ts", ".tsx", ".md"}
    )
    for root_doc in ("AGENTS.md", "CLAUDE.md"):
        sources.append(ROOT / root_doc)
    hook_sources = harness_sources(ROOT)
    sources.extend(hook_sources)
    clone_files = doc_files()
    dangling = []
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for cited in sorted(set(ID.findall(text))):
            if cited not in known:
                dangling.append(rel(path) + ": " + cited)
        for cited in sorted(set(DOC_PATH.findall(text))):
            if cited not in clone_files:
                dangling.append(rel(path) + ": " + cited)
        for doc, section in sorted(set(DOC_SECTION.findall(text))):
            target = ROOT / doc
            if doc not in clone_files:
                continue  # already reported by the path check above
            heading = re.compile(r"(?m)^#+ " + re.escape(section) + r"(\.\s|\s)")
            if not heading.search(target.read_text(encoding="utf-8")):
                dangling.append(rel(path) + ": " + doc + " " + section)
    passed &= expect(
        "every cited id, " + DOCS_DIR + "/ path and section resolves", dangling == [], dangling
    )
    passed &= expect(
        "the citation scan reads the hooks and review briefs (%d files)" % len(hook_sources),
        len(hook_sources) > 0,
    )
    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp)
        (fake / ".claude" / "hooks").mkdir(parents=True)
        (fake / ".githooks").mkdir()
        (fake / ".claude" / "hooks" / "x.py").write_text("# (D-" + "999)\n", encoding="utf-8")
        (fake / ".githooks" / "y.py").write_text("# (D-" + "998)\n", encoding="utf-8")
        planted = []
        for path in harness_sources(fake):
            for cited in ID.findall(path.read_text(encoding="utf-8")):
                if cited not in known:
                    planted.append(cited)
    passed &= expect(
        "a planted unknown id under .claude/hooks and .githooks is found",
        sorted(planted) == ["D-" + "998", "D-" + "999"],
        planted,
    )

    # Two parallel sessions can both write the next id; a cited id then resolves to two
    # decisions and the check above cannot see it.
    duplicated = []
    for name in ("REQUIREMENTS", "DECISIONS", "OPEN_QUESTIONS"):
        path = ROOT / DOCS_DIR / (name + ".md")
        if not path.exists():
            continue
        seen = set()
        for match in re.findall(
            r"^## ((?:R\d+|D-\d{3}|Q-\d{3})) ", path.read_text(encoding="utf-8"), re.M
        ):
            if match in seen:
                duplicated.append(DOCS_DIR + "/" + name + ".md: " + match)
            seen.add(match)
    passed &= expect("every register id is defined once", duplicated == [], duplicated)

    # 6. CLAUDE.md imports AGENTS.md; a fresh clone must have it.
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    imported = "@AGENTS.md" in claude
    passed &= expect(
        "CLAUDE.md's @AGENTS.md target is tracked", not imported or "AGENTS.md" in tracked_paths
    )
    # Every agent loads AGENTS.md into its context on every turn, so it is capped. Counted
    # with LF line endings: a Windows checkout adds a byte per line and must not fail.
    agents_size = len((ROOT / "AGENTS.md").read_bytes().replace(b"\r\n", b"\n"))
    passed &= expect(
        "AGENTS.md is at most 8192 bytes",
        agents_size <= 8192,
        ["AGENTS.md is " + str(agents_size) + " bytes"],
    )

    # 7. Whether a script bills is read off its own docstring, not remembered
    # (AGENTS.md "Gates").
    unlabelled = []
    for path in files(COST_DIR, suffixes={".py"}):
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
        label = re.search(r"(?m)^Cost: (free|PAID) - ", doc)
        if label is None:
            unlabelled.append(rel(path) + ": no 'Cost: free - ' or 'Cost: PAID - ' line")
        elif path.name in deny_listed and label.group(1) != "PAID":
            unlabelled.append(rel(path) + ": deny-listed but labelled free")
    passed &= expect(
        "every " + COST_DIR + "/ file carries a Cost line", unlabelled == [], unlabelled
    )

    # 8. A module with logic and no drill is a silent wrong value waiting to happen;
    # the list of exceptions may only shrink. A drill counts as importing a module when
    # an import statement of it names the module by its dotted path (`import a.b`,
    # `from a import b`, `from a.b import c`); the word in a string or a comment does not.
    drilled = set()
    for path in files("tests", suffixes={".py"}):
        if not path.name.startswith("drill_"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            dotted = []
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dotted.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                dotted.append(node.module)
                for alias in node.names:
                    dotted.append(node.module + "." + alias.name)
            for name in dotted:
                parts = name.split(".")
                for end in range(1, len(parts) + 1):
                    drilled.add(".".join(parts[:end]))
    listed = []
    for line in (ROOT / "tests" / "untested.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            listed.append(line)
    unpaired = []
    for path in spine:
        parts = list(path.relative_to(ROOT / SPINE_DIR).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        imported = ".".join(parts) in drilled
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
        "every " + SPINE_DIR + "/ module is imported by a drill or listed in tests/untested.txt",
        unpaired == [],
        unpaired,
    )

    # 9. Deleting a check from a drill makes the gate greener, not safer. A drill that
    # moved to another drill name is followed there; a drill moved out of the gate counts
    # as gone. In CI the base names a pushed range: each commit of it is judged by its own
    # subject, so a later `drop drill:` cannot excuse an earlier commit.
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
        renamed = drill_renames(base, "HEAD")
        for name in base_drills:
            now_path = ROOT / renamed.get(name, name)
            label = name if name not in renamed else name + " -> " + renamed[name]
            _, before_text = git_out("show", base + ":" + name)
            before = count_expects(before_text)
            if not now_path.exists():
                lost.append(
                    name + ": existed at " + base + " with " + str(before) + " checks, now gone"
                )
                continue
            after = count_expects(now_path.read_text(encoding="utf-8"))
            if after != before:
                deltas.append(label + ": " + str(before) + " -> " + str(after))
            if after < before:
                lost.append(label + ": " + str(before) + " -> " + str(after) + " expect( calls")
        # A deliberate removal says so in the subject, which CI can read; the env var
        # is for the local run before the commit exists.
        _, subject = git_out("log", "-1", "--format=%s")
        allowed = os.environ.get("PROJECT_DRILL_DROP_OK") == "1" or "drop drill:" in subject
        named = os.environ.get("PROJECT_RATCHET_BASE", "").strip()
        if named and set(named) != {"0"}:
            in_range = commits_between(named, "HEAD")
            if len(in_range) > 1:
                lost = unannounced_drops(in_range, count_expects)
                allowed = os.environ.get("PROJECT_DRILL_DROP_OK") == "1"
                deltas = []
        detail = []
        for line in deltas:
            detail.append("delta vs " + base + "  " + line)
        for line in lost:
            detail.append("LOST  " + line)
        passed &= expect("no drill lost a check since " + base, lost == [] or allowed, detail)

    print("")
    print("ALL PASSED" if passed else "SOME FAILED")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
