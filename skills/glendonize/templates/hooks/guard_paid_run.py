"""PreToolUse hook: blocks a shell command that starts a paid script unless the
command carries PROJECT_PAID_OK=1, which Claude adds only after the user's go for
that run (AGENTS.md "Gates").

It reads the command's text, and text has more spellings of "start this script" than a
reader can list: every narrowing that quiets a false alarm opens a way past, and the
production repo needed seven review rounds to learn it. So the paid check is coarse and
fails closed. A paid script named as a file, a dotted module or a -m value (never as a word
of prose) is denied unless the segment it stands in is run by a program on FREE_PROGRAMS
(git, gh, grep, cat, ruff ...) or by python plainly starting a free script or a file tool.
git runs what it is handed, so it passes only in the read-only shapes of GIT_SHAPES.
A wrapped shell, Start-Process, a stdlib runner, stdin, uv, an unknown program: denied, and
the deny says where a reader is added. The check no spelling gets around is at the spend
point: the paid script itself reads PROJECT_PAID_OK from its environment and refuses without
it.

Claude Code passes the tool call as JSON on stdin. A blocked call gets a "deny"
decision with the reason; everything else exits 0 with no output, which lets the
call through. Unreadable input lets the call through too, so a broken hook
cannot stop every shell command.

An error while deciding denies, because Claude Code runs the command after a
crashed hook.

It also refuses `git help ...` and `git <command> --help`: on Git for Windows
they open the HTML manual in the user's browser, and an agent has nothing to read there.

It denies a plain `git push` too: an agent pushes through the pipeline,
`python .claude/hooks/ship.py` as a background job.

It denies a `git stash` with no `--` pathspec (`git stash`, `push`, `save`, with `-C`, `-u`,
`-m`): sessions share one checkout and a bare stash sweeps their files away.
`git stash push -- <paths>`, list, show, pop, apply and drop pass.

It denies a recursive search (`grep -r`, PowerShell's `Get-ChildItem -Recurse | Select-String`,
`findstr /s`, `rg --no-ignore`) that can reach a folder in guard_private_paths.py's
PROTECTED_FOLDERS, because a plain `grep -r` ignores .gitignore. A path outside the repo is
never denied (an earlier allow-list version blocked `ls -R` and `grep` on ~/.claude/skills,
2026-11-26), and a count in one named file passes. It catches the usual ways an agent
searches, not every one: a shell has more spellings of a search than a list can hold, so it is
a guard on a habit, not a sandbox.

A command that names a paid file and pipes into anything but a reader is denied whole:
each segment is judged alone, so `git show HEAD:<paid> | python`, `cat <paid> | python` and
`echo <paid> | xargs python` passed, the file named by a free program and run by the next
one. A pipe into a program on PIPE_READERS (head, grep, wc, Select-String, Out-String ...)
passes; python, uv, a shell, node, env, xargs and any program not listed fail closed.

Limit: it reads the command text. A script that imports a paid module and calls it (a scratch
probe importing the paid module) is not caught here; the spend point stops it.
"""

import json
import re
import shlex
import sys

PAID_SCRIPTS = (
    "paid_script",
    "paid_estimate_script",
)
FORMER_PAID_SCRIPTS = ()
ESTIMATE_ONLY_WITHOUT_GO = ("paid_estimate_script",)
MODULE_ROOTS = ("src",)

try:
    from guard_private_paths import reaches_protected
except ImportError:

    def reaches_protected(path):
        return False


MARKER = re.compile(r"PROJECT_PAID_OK\s*=\s*[\"']?1")
GO = re.compile(r"--g(o)?(?![\w-])")
CONTINUATION = re.compile(r"[\\`]\r?\n")
SEPARATOR = re.compile(r"&&|\|\||[;&|\n]")
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?([^\n]*)\n.*?\n\1[ \t]*(?=\r?\n|$)", re.DOTALL)
QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'", re.DOTALL)
HERE_STRING = re.compile(r"@(['\"])[ \t]*\r?\n(.*?)\r?\n\1@", re.DOTALL)
EXPANDS = re.compile(r"\$\(|(?<!\\)`")
BESIDE_A_HERE_STRING = ("set-content", "add-content", "out-file", "cd")
NESTED = re.compile(r"\$\(|[()`]")
REDIRECT = re.compile(r"\d?(?:>>?|<)(?:&\d+|\s*[^\s;|&<>]+)?")


PAID_NAMES = "|".join(PAID_SCRIPTS + FORMER_PAID_SCRIPTS)
MODULE_PREFIX = "|".join(MODULE_ROOTS)
MODULE = r"(?:(?:" + MODULE_PREFIX + r")\.(?:\w+\.)*)?(?:" + PAID_NAMES + r")(?!\w)"
PAID_TOKEN = re.compile(
    r"(?<![\w.-])(?:" + PAID_NAMES + r")\.py(?!\w)"
    r"|(?<![\w.-])(?:" + MODULE_PREFIX + r")\.(?:\w+\.)*(?:" + PAID_NAMES + r")(?!\w)"
    r"|-\w*m\s*" + MODULE + r"|\brunpy\b[^;|&\n]*?(?<![\w.-])" + MODULE,
    re.IGNORECASE,
)
SUBSTITUTION = re.compile(r"\$\([^()]*\)|`[^`\n]*`")
FREE_PROGRAMS = (
    "git",
    "gh",
    "cat",
    "head",
    "tail",
    "less",
    "more",
    "sed",
    "awk",
    "cut",
    "sort",
    "uniq",
    "wc",
    "diff",
    "grep",
    "egrep",
    "fgrep",
    "rg",
    "find",
    "ls",
    "dir",
    "stat",
    "file",
    "type",
    "get-content",
    "gc",
    "select-string",
    "sls",
    "findstr",
    "get-childitem",
    "gci",
    "get-item",
    "test-path",
    "measure-object",
    "compare-object",
    "cp",
    "mv",
    "rm",
    "touch",
    "mkdir",
    "copy-item",
    "move-item",
    "remove-item",
    "echo",
    "printf",
    "write-output",
    "write-host",
    "set-content",
    "add-content",
    "out-file",
    "ruff",
    "pyright",
    "mypy",
    "black",
    "code",
    "npm",
    "npx",
    "node",
)
PIPE_READERS = (
    "cat",
    "head",
    "tail",
    "less",
    "more",
    "cut",
    "sort",
    "uniq",
    "wc",
    "grep",
    "egrep",
    "fgrep",
    "select-string",
    "sls",
    "findstr",
    "measure-object",
    "out-string",
    "out-null",
    "select-object",
    "sort-object",
    "set-content",
    "add-content",
    "out-file",
)
RUNS_INSIDE = re.compile(r"[$@`{]|[<>]\(")
PIPE = re.compile(r"(?<![|\\])\|&?(?!\|)")
PYTHON_OPTION_WITH_VALUE = ("-X", "-W", "-Q")
PYTHON_PLAIN_OPTIONS = ("-u", "-B", "-E", "-I", "-O", "-OO", "-q", "-s", "-S", "-v", "-b", "-3")
FILE_TOOL_MODULES = ("ruff", "py_compile", "compileall", "pyright", "mypy", "black")
UNPLAIN = re.compile(r"[\s\"',<>$`()]")
PS_ASSIGNMENT = re.compile(r"^\s*\$[\w:]+\s*=\s*")
SHELL_KEYWORDS = ("do", "then", "else", "elif", "if", "while", "until", "!", "{")
SHELL_LEAD = re.compile(r"\s*(?:(?:do|then|else|elif|if|while|until|!|\{)\s+)*")
GIT_GLOBAL_PLAIN = ("--no-pager", "-P")
GIT_HISTORY = (
    "pusqwbzRU",
    "nSGL",
    (
        "--oneline",
        "--stat",
        "--shortstat",
        "--numstat",
        "--name-only",
        "--name-status",
        "--patch",
        "--no-patch",
        "--follow",
        "--all",
        "--graph",
        "--decorate",
        "--no-decorate",
        "--merges",
        "--no-merges",
        "--first-parent",
        "--reverse",
        "--cached",
        "--staged",
        "--color",
        "--no-color",
        "--summary",
        "--raw",
        "--no-renames",
        "--find-renames",
        "--quiet",
        "--exit-code",
        "--check",
        "--word-diff",
        "--abbrev-commit",
        "--ignore-all-space",
        "--ignore-space-change",
        "--ignore-blank-lines",
        "--no-ext-diff",
        "--no-textconv",
        "--full-history",
        "--left-right",
        "--pickaxe-regex",
        "--pickaxe-all",
    ),
    (
        "--format",
        "--pretty",
        "--since",
        "--until",
        "--after",
        "--before",
        "--author",
        "--committer",
        "--grep",
        "--max-count",
        "--skip",
        "--date",
        "--diff-filter",
        "--unified",
        "--color",
        "--word-diff",
        "--stat",
        "--abbrev",
        "--find-renames",
        "--decorate",
        "--diff-algorithm",
    ),
)
GIT_SHAPES = {
    "grep": (
        "nilLcwhHqEFPGvoIpW",
        "eABCm",
        (
            "--cached",
            "--count",
            "--line-number",
            "--ignore-case",
            "--name-only",
            "--files-with-matches",
            "--files-without-match",
            "--word-regexp",
            "--extended-regexp",
            "--fixed-strings",
            "--perl-regexp",
            "--invert-match",
            "--only-matching",
            "--heading",
            "--break",
            "--show-function",
            "--function-context",
            "--quiet",
            "--color",
            "--no-color",
            "--column",
            "--and",
            "--or",
            "--not",
            "--all-match",
        ),
        ("--max-depth", "--max-count", "--color"),
    ),
    "log": GIT_HISTORY,
    "show": GIT_HISTORY,
    "diff": GIT_HISTORY,
    "blame": (
        "wslfnpctbek",
        "LS",
        ("--porcelain", "--line-porcelain", "--show-name", "--show-number", "--show-email"),
        ("--date", "--abbrev", "--ignore-rev"),
    ),
    "status": (
        "sbzuv",
        "",
        (
            "--short",
            "--branch",
            "--porcelain",
            "--long",
            "--ignored",
            "--untracked-files",
            "--verbose",
            "-uno",
            "-uall",
            "-unormal",
        ),
        ("--porcelain", "--untracked-files", "--ignored"),
    ),
    "ls-files": (
        "cdmoszt",
        "",
        (
            "--cached",
            "--deleted",
            "--modified",
            "--others",
            "--stage",
            "--exclude-standard",
            "--error-unmatch",
            "--full-name",
        ),
        (),
    ),
    "ls-tree": (
        "rtdlz",
        "",
        ("--name-only", "--name-status", "--long", "--full-name", "--full-tree"),
        (),
    ),
    "cat-file": ("ptse", "", (), ()),
    "rev-parse": (
        "q",
        "",
        (
            "--show-toplevel",
            "--short",
            "--abbrev-ref",
            "--verify",
            "--quiet",
            "--git-dir",
            "--git-common-dir",
            "--is-inside-work-tree",
            "--show-prefix",
        ),
        ("--short",),
    ),
    "add": (
        "AufnvN",
        "",
        ("--all", "--update", "--force", "--dry-run", "--verbose", "--intent-to-add"),
        (),
    ),
    "rm": ("rfqn", "", ("--cached", "--force", "--quiet", "--dry-run", "--ignore-unmatch"), ()),
    "mv": ("fknv", "", ("--force", "--dry-run", "--verbose"), ()),
    "restore": (
        "SWq",
        "s",
        ("--staged", "--worktree", "--quiet", "--ours", "--theirs"),
        ("--source",),
    ),
    "checkout": ("qf", "bB", ("--quiet", "--force", "--detach", "--ours", "--theirs"), ()),
    "reset": ("q", "", ("--soft", "--mixed", "--hard", "--keep", "--merge", "--quiet"), ()),
    "commit": (
        "aqvsoi",
        "mF",
        (
            "--all",
            "--quiet",
            "--verbose",
            "--amend",
            "--no-edit",
            "--allow-empty",
            "--only",
            "--include",
            "--signoff",
            "--dry-run",
            "--reset-author",
        ),
        ("--message", "--file", "--author", "--date", "--cleanup"),
    ),
    "stash": (
        "uqkap",
        "m",
        (
            "--include-untracked",
            "--keep-index",
            "--staged",
            "--all",
            "--quiet",
            "--index",
            "--stat",
            "--name-only",
            "--patch",
        ),
        ("--message",),
    ),
}
GIT_WORD = re.compile(r"[\w./:=@%+~^,{}\\-]*", re.ASCII)
GIT_REWRITTEN = re.compile(r"(?<!\d),|,(?!\d)|(?<!\w)@|(?<![\w.:])\\|\\(?![\w.])", re.ASCII)
GIT_REFLOG = re.compile(r"(?<=\w@)\{\w*\}", re.ASCII)
GIT_REDIRECT = re.compile(r"\d?(?:>>?|<<?<?)(?:\$null|[\w./:~\\-]*)", re.ASCII)
GIT_NUMBER_VARIABLE = re.compile(r"\w+=\d+", re.ASCII)


def is_python(program):
    return program == "py" or program.startswith("python")


def starts_free_script(tokens):
    position = 1
    while position < len(tokens):
        token = tokens[position]
        if UNPLAIN.search(token):
            return False
        if token == "-m":
            return position + 1 < len(tokens) and tokens[position + 1] in FILE_TOOL_MODULES
        if token in ("-c", "-"):
            return False
        if token in PYTHON_OPTION_WITH_VALUE:
            position += 2
            continue
        if token in PYTHON_PLAIN_OPTIONS:
            position += 1
            continue
        if token.startswith("-"):
            return False
        return PAID_TOKEN.search(" " + token) is None
    return False


def git_words(text, shell):
    found = []
    index = 0
    text = text.rstrip()
    while index < len(text):
        if text[index] in " \t\n":
            index += 1
            continue
        end = index
        while end < len(text) and text[end] not in " \t\n\"'":
            end += 1
        bare = text[index:end]
        quote = text[end : end + 1].strip()
        if GIT_REDIRECT.fullmatch(bare):
            if quote != "":
                return None
            found.append((bare, "redirect"))
            index = end
            continue
        if GIT_WORD.fullmatch(bare) is None or GIT_REWRITTEN.search(bare):
            return None
        if "{" in GIT_REFLOG.sub("", bare) or "}" in GIT_REFLOG.sub("", bare):
            return None
        if shell == "powershell":
            if "{" in bare or (bare.startswith("-") and ("." in bare or ":" in bare)):
                return None
            if bare == "--%":
                return None
        if quote == "":
            found.append((bare, "plain"))
            index = end
            continue
        if bare != "" and not bare.endswith("="):
            return None
        close = text.find(quote, end + 1)
        if close < 0:
            return None
        content = text[end + 1 : close]
        if content == "" or content.endswith("\\"):
            return None
        if close + 1 < len(text) and text[close + 1] not in " \t\n":
            return None
        kind = "plain"
        if quote == '"' and ("$" in content or "`" in content):
            if shell == "powershell":
                return None
            if bare == "":
                kind = "open"
        if quote == "'" and shell == "powershell" and '"' in content:
            return None
        found.append((bare + content, kind))
        index = close + 1
    return found


def git_only_reads(segment, shell):
    if shell == "powershell":
        segment = PS_ASSIGNMENT.sub("", segment)
    tokens = git_words(SHELL_LEAD.sub("", segment, count=1), shell)
    if tokens is None:
        return False
    position = 0
    while position < len(tokens) and GIT_NUMBER_VARIABLE.fullmatch(tokens[position][0]):
        position += 1
    if position < len(tokens) and tokens[position] == ("env", "plain"):
        position += 1
        while position < len(tokens) and GIT_NUMBER_VARIABLE.fullmatch(tokens[position][0]):
            position += 1
    if position >= len(tokens) or tokens[position][1] != "plain":
        return False
    if program_name(tokens[position][0]) != "git":
        return False
    position += 1
    while position < len(tokens):
        word, kind = tokens[position]
        if (word, kind) == ("-C", "plain") and position + 1 < len(tokens):
            position += 2
        elif kind == "plain" and word in GIT_GLOBAL_PLAIN:
            position += 1
        else:
            break
    if position >= len(tokens) or tokens[position][1] != "plain":
        return False
    if tokens[position][0] not in GIT_SHAPES:
        return False
    flags, with_value, plain, with_equals = GIT_SHAPES[tokens[position][0]]
    position += 1
    while position < len(tokens):
        word, kind = tokens[position]
        position += 1
        if kind == "redirect":
            if word.endswith((">", "<")):
                position += 1
            continue
        if kind != "plain":
            return False
        if word == "--":
            return True
        if not word.startswith("-") or word == "-" or word in plain:
            continue
        if word.startswith("--"):
            name, equals, _ = word.partition("=")
            if equals == "" or name not in with_equals:
                return False
            continue
        for place, letter in enumerate(word[1:]):
            if letter in with_value:
                if place == len(word) - 2:
                    position += 1
                break
            if letter not in flags and letter not in "0123456789":
                return False
    return True


def value_runs_on(tokens):
    for token in tokens:
        if "=" not in token or token.startswith("-"):
            return False
        if '"' in token or "'" in token or token.endswith("\\"):
            return True
    return False


def runs_free(segment, shell):
    tokens = words(PS_ASSIGNMENT.sub("", segment))
    if value_runs_on(tokens):
        return False
    tokens = without_assignments(tokens)
    while tokens and tokens[0] in SHELL_KEYWORDS:
        if value_runs_on(tokens[1:]):
            return False
        tokens = without_assignments(tokens[1:])
    if tokens and program_name(tokens[0]) == "env":
        if value_runs_on(tokens[1:]):
            return False
        tokens = without_assignments(tokens[1:])
    if not tokens:
        return False
    program = program_name(tokens[0])
    if program == "git":
        return git_only_reads(segment, shell)
    if program in FREE_PROGRAMS:
        return True
    if is_python(program):
        return starts_free_script(tokens)
    return False


def blanks(match):
    return " " * len(match.group(0))


def segment_around(text, position):

    def separators(match):
        return ";" * len(match.group(0))

    masked = NESTED.sub(separators, QUOTED.sub(blanks, text))
    start = 0
    for match in SEPARATOR.finditer(masked):
        if match.end() > position:
            break
        start = match.end()
    after = SEPARATOR.search(masked, position)
    end = len(text) if after is None else after.start()
    return text[start:end]


def receiving_segments(text, position):
    folded = list(text)
    inside = False
    for span in SUBSTITUTION.finditer(QUOTED.sub(blanks, text)):
        if span.start() <= position < span.end():
            inside = True
        folded[span.start()] = "$"
        for index in range(span.start() + 1, span.end()):
            folded[index] = " "
    found = [segment_around("".join(folded), position)]
    if inside:
        found.append(segment_around(text, position))
    return found


def inside_expanding_quote(text, position, shell):
    quote = None
    opened = []
    inside = False
    index = 0
    while index < len(text):
        if index == position:
            inside = quote == '"' and opened != []
        char = text[index]
        if quote == "'":
            if char == "'":
                quote = None
        elif quote is None:
            if char == "#" and (index == 0 or text[index - 1] in " \t\n;"):
                end = text.find("\n", index)
                index = len(text) if end < 0 else end
                continue
            if text.startswith("@'", index) or text.startswith('@"', index):
                mark = text[index + 1]
                close = text.find("\n" + mark + "@", index)
                end = len(text) if close < 0 else close + 3
                body = text[index:end]
                if index <= position < end:
                    inside = mark == '"' and EXPANDS.search(body) is not None
                index = end
                continue
            if char in "\"'":
                quote = char
        elif opened:
            if char == '"':
                close = text.find('"', index + 1)
                if close < 0:
                    return True
                if index <= position <= close:
                    inside = True
                index = close
            elif text.startswith("$(", index):
                opened.append("$(")
                index += 1
            elif char == "(" and opened[-1] != "`":
                opened.append("(")
            elif char == ")" and opened[-1] != "`":
                opened.pop()
            elif char == "`" and opened[-1] == "`":
                opened.pop()
        elif shell == "powershell":
            if char == "`" and index + 1 < len(text):
                index += 1
            elif text.startswith("$(", index):
                opened.append("$(")
                index += 1
            elif char == '"':
                quote = None
        else:
            if char == "\\" and index + 1 < len(text) and text[index + 1] in '`"':
                index += 1
            elif text.startswith("$(", index):
                opened.append("$(")
                index += 1
            elif char == "`":
                opened.append("`")
            elif char == '"':
                quote = None
        index += 1
    if quote is not None:
        return True
    return inside


def paid_name(token):
    found = token
    for name in PAID_SCRIPTS + FORMER_PAID_SCRIPTS:
        if name in token.lower() and (found == token or len(name) > len(found)):
            found = name
    return found


def here_string_text(match):
    if match.group(1) == '"' and EXPANDS.search(match.group(2)):
        return match.group(0)
    return " "


def without_here_strings(command):
    outside = HERE_STRING.sub(here_string_text, command)
    if outside == command:
        return command
    for segment in NESTED.split(CONTINUATION.sub(" ", outside)):
        for piece in SEPARATOR.split(segment):
            tokens = words(PS_ASSIGNMENT.sub("", piece))
            if not tokens or tokens[0].startswith("#"):
                continue
            if program_name(tokens[0]) not in BESIDE_A_HERE_STRING:
                return command
    return outside


def paid_script_in(command, shell):
    command = without_here_strings(command)
    text = CONTINUATION.sub(" ", HEREDOC.sub(lambda match: " " + match.group(2) + " ", command))
    for hit in PAID_TOKEN.finditer(text):
        receiving = receiving_segments(text, hit.start())
        free = not inside_expanding_quote(text, hit.start(), shell)
        for segment in receiving:
            if not runs_free(segment, shell):
                free = False
        if free:
            continue
        name = paid_name(hit.group(0))
        if name in ESTIMATE_ONLY_WITHOUT_GO and GO.search(receiving[0]) is None:
            continue
        return name + ".py"
    return None


def pipe_receiver(segment):
    if RUNS_INSIDE.search(segment):
        return None
    tokens = words(PS_ASSIGNMENT.sub("", segment))
    while tokens and tokens[0] in SHELL_KEYWORDS:
        tokens = tokens[1:]
    if not tokens or ("=" in tokens[0] and not tokens[0].startswith("-")):
        return None
    program = program_name(tokens[0])
    if program == "sort":
        for token in tokens[1:]:
            if token.startswith("--"):
                return None
    return program


def paid_pipe_in(command):
    command = without_here_strings(command)
    text = CONTINUATION.sub(" ", HEREDOC.sub(lambda match: " " + match.group(2) + " ", command))
    hit = PAID_TOKEN.search(text)
    if hit is None:
        return None

    def separators(match):
        return ";" * len(match.group(0))

    masked = NESTED.sub(separators, QUOTED.sub(blanks, text))
    for pipe in PIPE.finditer(masked):
        after = SEPARATOR.search(masked, pipe.end())
        end = len(text) if after is None else after.start()
        program = pipe_receiver(text[pipe.end() : end])
        if after is not None and text[end] in "($`":
            program = None
        if program is None:
            return paid_name(hit.group(0)) + ".py", "a program the guard cannot read"
        if program not in PIPE_READERS:
            return paid_name(hit.group(0)) + ".py", program
    return None


GIT_OPTION_WITH_VALUE = ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env")


def git_arguments(command):
    found = []
    for segment in segments(without_message_text(command)):
        tokens = words(segment)
        tokens = without_assignments(tokens)
        if tokens and program_name(tokens[0]) == "env":
            tokens = without_assignments(tokens[1:])
        if not tokens or program_name(tokens[0]) != "git":
            continue
        found.append(tokens[1:])
    return found


def git_help_in(command):
    for arguments in git_arguments(command):
        if "--help" in arguments:
            return True
        if subcommand_of(arguments) == "help":
            return True
    return False


def git_push_in(command):
    for arguments in git_arguments(command):
        if subcommand_of(arguments) == "push":
            return True
    return False


STASH_SAVING = ("push", "save")


def git_bare_stash_in(command):
    for arguments in git_arguments(command):
        if subcommand_of(arguments) != "stash":
            continue
        position = 0
        while arguments[position] != "stash":
            if arguments[position] in GIT_OPTION_WITH_VALUE:
                position += 1
            position += 1
        rest = arguments[position + 1 :]
        if rest and not rest[0].startswith("-") and rest[0] not in STASH_SAVING:
            continue
        if "--" not in rest:
            return True
    return False


CODE_TYPES = (".py", ".ts", ".tsx", ".js", ".md", ".yml", ".toml", ".css", ".html")
INCLUDE_TYPES = (".py", ".ts", ".tsx", ".js", ".yml", ".toml", ".css")
GREP_PROGRAMS = ("grep", "egrep", "fgrep")
GREP_OPTION_WITH_VALUE = ("-m", "-A", "-B", "-C", "--exclude-dir", "--include", "--exclude")
RG_OPTION_WITH_VALUE = (
    "-g",
    "--glob",
    "-t",
    "--type",
    "-T",
    "--type-not",
    "-m",
    "--max-count",
    "-A",
    "-B",
    "-C",
)


def grep_may_search(path):
    return not reaches_protected(path)


def includes_only_code(arguments):
    globs = []
    position = 0
    while position < len(arguments):
        token = arguments[position]
        if token.startswith("--include="):
            globs.append(token.split("=", 1)[1])
        elif token == "--include" and position + 1 < len(arguments):
            globs.append(arguments[position + 1])
        position += 1
    if not globs:
        return False
    for glob in globs:
        if not glob.lower().endswith(INCLUDE_TYPES):
            return False
    return True


def search_paths(arguments, options_with_value):
    bare = []
    pattern_given = False
    position = 0
    while position < len(arguments):
        token = arguments[position]
        if token in options_with_value:
            position += 2
            continue
        if token.startswith(("--regexp", "--file")):
            pattern_given = True
            if "=" in token:
                position += 1
            else:
                position += 2
            continue
        if token.startswith("-") and not token.startswith("--") and len(token) > 1:
            letters = token[1:]
            if "e" in letters or "f" in letters:
                pattern_given = True
                if letters[-1] in ("e", "f"):
                    position += 1
            position += 1
            continue
        if not token.startswith("-"):
            bare.append(token)
        position += 1
    if pattern_given:
        return bare
    return bare[1:]


def recursive_flag(arguments):
    for token in arguments:
        if token in ("--recursive", "--dereference-recursive"):
            return True
        if token.startswith("-") and not token.startswith("--"):
            if "r" in token[1:] or "R" in token[1:]:
                return True
    return False


def powershell_search_in(token_lists, piped):
    searching = piped
    for tokens in token_lists:
        program = program_name(tokens[0])
        arguments = tokens[1:]
        paths = []
        skip_value = False
        for token in arguments:
            if skip_value:
                skip_value = False
                continue
            if token.lower() in ("-filter", "-include", "-exclude", "-pattern", "-depth"):
                skip_value = True
                continue
            if not token.startswith(("-", "/")):
                paths.append(token)
        if program in ("get-childitem", "gci", "dir", "ls") and searching:
            recursive = False
            for token in arguments:
                if len(token) > 1 and "-recurse".startswith(token.lower()):
                    recursive = True
            if recursive:
                if not paths:
                    return tokens[0] + " -Recurse"
                for path in paths:
                    if not grep_may_search(path):
                        return tokens[0] + " -Recurse " + path
        if program == "findstr":
            folders = False
            pattern_given = False
            for token in arguments:
                lowered = token.lower()
                if lowered.startswith(("/c:", "/g:")):
                    pattern_given = True
                elif lowered.startswith("/") and ":" not in lowered and "s" in lowered[1:]:
                    folders = True
            if not pattern_given:
                paths = paths[1:]
            for path in paths:
                if (folders or "*" in path) and not grep_may_search(path):
                    return "findstr " + path
        if program in ("select-string", "sls"):
            pattern_given = "-pattern" in [token.lower() for token in arguments]
            paths = []
            skip_value = False
            after_path = False
            for token in arguments:
                lowered = token.lower()
                if skip_value:
                    skip_value = False
                elif after_path:
                    paths.append(token)
                    after_path = False
                elif lowered in ("-path", "-literalpath"):
                    after_path = True
                elif lowered in ("-pattern", "-include", "-exclude", "-encoding", "-context"):
                    skip_value = True
                elif token.startswith("-"):
                    continue
                elif not pattern_given:
                    pattern_given = True
                else:
                    paths.append(token)
            for path in paths:
                if "*" in path and not grep_may_search(path):
                    return "Select-String " + path
    return None


def private_search_in(command):
    token_lists = []
    text = without_message_text(command)
    piped = re.search(r"(?<!\|)\|(?!\|)", text) is not None
    if NESTED.search(QUOTED.sub("", command)):
        piped = True
    for segment in segments(text):
        tokens = without_assignments(words(segment))
        if tokens:
            token_lists.append(tokens)
    found = powershell_search_in(token_lists, piped)
    if found:
        return found
    for tokens in token_lists:
        program = program_name(tokens[0])
        arguments = tokens[1:]
        if program in GREP_PROGRAMS and recursive_flag(arguments):
            if includes_only_code(arguments):
                continue
            paths = search_paths(arguments, GREP_OPTION_WITH_VALUE)
            if not paths:
                paths = ["."]
            for path in paths:
                if not grep_may_search(path):
                    return "grep -r " + path
        elif program in GREP_PROGRAMS:
            for path in search_paths(arguments, GREP_OPTION_WITH_VALUE):
                if "*" in path and not grep_may_search(path):
                    return "grep " + path
        if program == "rg":
            position = 0
            while position < len(arguments):
                token = arguments[position]
                glob = None
                if token in ("-g", "--glob", "--iglob") and position + 1 < len(arguments):
                    glob = arguments[position + 1]
                elif token.startswith(("--glob=", "--iglob=")):
                    glob = token.split("=", 1)[1]
                elif token.startswith("-g") and len(token) > 2:
                    glob = token[2:]
                if glob is not None:
                    glob = glob.strip("\"'")
                    if not glob.startswith("!") and not glob.lower().endswith(INCLUDE_TYPES):
                        return "rg -g " + glob
                position += 1
            for token in arguments:
                if token in ("--no-ignore", "--no-ignore-vcs", "--unrestricted"):
                    return "rg " + token
                if token.startswith("-") and not token.startswith("--") and "u" in token[1:]:
                    return "rg " + token
            for path in search_paths(arguments, RG_OPTION_WITH_VALUE):
                if not grep_may_search(path):
                    return "rg " + path
    return None


def without_message_text(command):
    stripped = CONTINUATION.sub(" ", HEREDOC.sub(lambda match: " " + match.group(2) + " ", command))

    def keep_or_placeholder(match):
        if SEPARATOR.search(match.group(0)) or NESTED.search(match.group(0)):
            return '"quoted"'
        return match.group(0)

    unquoted = QUOTED.sub(keep_or_placeholder, stripped)
    return REDIRECT.sub(" ", NESTED.sub(";", unquoted))


def words(segment):
    try:
        tokens = shlex.split(segment, posix=False)
    except ValueError:
        tokens = segment.split()
    unquoted = []
    for token in tokens:
        unquoted.append(token.strip("\"'"))
    return unquoted


def without_assignments(tokens):
    while tokens and "=" in tokens[0] and not tokens[0].startswith("-"):
        tokens = tokens[1:]
    return tokens


def program_name(token):
    name = token.strip("\"'").replace("\\", "/").rsplit("/", 1)[-1].lower()
    if name.endswith(".exe"):
        name = name[:-4]
    return name


def subcommand_of(arguments):
    position = 0
    while position < len(arguments):
        token = arguments[position]
        if not token.startswith("-"):
            return token
        if token in GIT_OPTION_WITH_VALUE:
            position += 1
        position += 1
    return None


def segments(command):
    joined = CONTINUATION.sub(" ", command)
    return SEPARATOR.split(joined)


def decision(command, shell="sh"):
    if git_help_in(command):
        return (
            "deny",
            "blocked: git help opens the HTML manual in the user's browser on Git for "
            "Windows and shows an agent nothing; read the docs with the Read "
            "tool instead.",
        )
    if git_push_in(command):
        return (
            "deny",
            "push through the pipeline: run `python .claude/hooks/ship.py` as a "
            "background job.",
        )
    if git_bare_stash_in(command):
        return (
            "deny",
            "blocked: a `git stash` without paths sweeps away the half-done files of the "
            "other sessions in the shared checkout; stash only your own with "
            "`git stash push -- <paths>`.",
        )
    search = private_search_in(command)
    if search is not None:
        return (
            "deny",
            f"blocked: `{search}` can read a folder this repo keeps private "
            "(PROTECTED_FOLDERS in .claude/hooks/guard_private_paths.py). Search with "
            "`git grep` or the Grep tool over the repo's own folders, never over those.",
        )
    script = paid_script_in(command, shell)
    if script is None:
        piped = paid_pipe_in(command)
        if piped is None or MARKER.search(command):
            return None
        return (
            "deny",
            f"blocked: the command names {piped[0]} and pipes into `{piped[1]}`, which can "
            "run what it is handed; each segment alone looks free, the pipe does not. Read "
            "the file with the Read tool or pipe into a reader (head, grep, wc, Select-String); "
            "a reader not listed yet goes in PIPE_READERS in .claude/hooks/guard_paid_run.py.",
        )
    if MARKER.search(command):
        return None
    return (
        "deny",
        f"blocked: {script} costs money. Give the user the estimate and the "
        "remaining budget from the budget ledger and wait for their go; then rerun "
        "the command prefixed with PROJECT_PAID_OK=1. A program that only reads "
        "the file and is not listed yet goes in FREE_PROGRAMS in "
        ".claude/hooks/guard_paid_run.py. A git command that names a paid file passes "
        "only in the plain read-only shapes of GIT_SHAPES there: no variable before git, "
        "no -c, listed options in full spelling, `--name=value`, no `$` outside a "
        "message.",
    )


def main():
    try:
        call = json.load(sys.stdin)
        command = call["tool_input"]["command"]
    except Exception:
        return 0
    shell = "powershell" if call.get("tool_name") == "PowerShell" else "sh"
    try:
        result = decision(command, shell)
    except Exception as error:
        result = (
            "deny",
            f"blocked: the paid-run hook failed while deciding ({error!r}); fix "
            ".claude/hooks/guard_paid_run.py before any paid command runs.",
        )
    if result is None:
        return 0
    verdict, reason = result
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": verdict,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
