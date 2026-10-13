"""Weekly learning check, run by a SessionStart hook in ~/.claude/settings.json.

Once every 7 days it counts how the user worked with Claude Code in the last
7 days (all projects), appends the counts to ~/.claude/learning/weekly.md with
"Interpretation: pending", and tells Claude to run the weekly-review skill,
which interprets the counts and updates profile.md. While an entry is still
pending, every session start reminds Claude again. Otherwise it prints nothing.

Counts and the user's own short prompts only; tool output (which can hold
document text) is never copied.

    python weekly_stats.py --hook     as the hook: maybe write, maybe remind
    python weekly_stats.py --force    write an entry now, whatever the date, then rebuild weekly.json
    python weekly_stats.py --json     rebuild weekly.json only: one row per week, oldest first,
                                      from the first transcript to the latest Monday (for charts)
    python weekly_stats.py --apply F  put the interpretation a headless run printed into weekly.md
    python weekly_stats.py --html     render the progress page (weekly_page.py)

weekly.json rows are fixed calendar weeks: `week_ending` is a Monday (the day the review
runs) and the window is the six days before it plus that Monday, local midnight to local
midnight, so the newest row grows until the next Monday starts (see window_of).
weekly_overrides.json, next to this script, maps a week_ending to keys whose computed value
it replaces (hand counts for weeks before a marker existed); the row lists them under
"overrides" and carries the override's "note".
"""

import json
import re
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home() / ".claude"
LEARNING = HOME / "learning"
WEEKLY = LEARNING / "weekly.md"
WEEKLY_JSON = LEARNING / "weekly.json"
OVERRIDES = LEARNING / "weekly_overrides.json"
LAST = LEARNING / ".last_review"
DAYS = 7
PAID_MARKER = "EDAT_PAID_OK=1"  # only ever added to a shell command after the user's go for a paid run

# Background context only, never a target (2026-10-08): "explain" is good learning
# behaviour, and "don't"/"stop" are ordinary instructions, so neither is counted
# as a correction.
CORRECTION = re.compile(r"^\s*(no[,!. ]|nein|nope|wrong|falsch|why did|that'?s not|not what|i told you)", re.I)
DONE_WHEN = re.compile(r"done when|definition of done|definiton of done|fertig wenn", re.I)
# Background count only (restored 2026-10-12 for the charts, after the 2026-10-08 version dropped
# it): asking for an explanation is good learning behaviour, so this is context, not a target.
DONT_UNDERSTAND = re.compile(
    r"don'?t understand|dont understand|what does this mean|verstehe nicht|versteh ich nicht"
    r"|erkl[äa]r|\bexplain\b|dont get it|don'?t get it|dont undrs|dont undsr",
    re.I,
)
# The practice that runs inside the work (D-089), four kinds since 2026-10-13: the code
# question, name the mechanism, the failure question, the trade-off question. Both ends are
# Claude's own markers, so a clarifying question by the user is not booked as an answer: a
# question is an assistant text block that starts with "<Kind> question"; it counts as
# answered when a later assistant block in the same session carries a line
# "Rating (sure|unsure|not said): ...", and "sure/unsure said" is read off that rating
# (profile.md "Monthly check"). The earlier paper:/guess: counters matched 0 prompts ever and
# were replaced on 2026-10-12; a first version that took the next user prompt as the answer
# booked "what does this mean?" as one.
QUESTION = re.compile(r"^\s*(\*\*)?(code|mechanism|failure|trade-?off) question\s*(\(|:|\*\*)", re.I)
RATING = re.compile(r"^\s*(\*\*)?rating\s*\((sure|unsure|not said)\)", re.I | re.M)
# The Monday task runs Claude without Edit; it prints these blocks and --apply writes them.
INTERP = re.compile(r"<<<INTERPRETATION\s*\n(.*?)\nINTERPRETATION>>>", re.S)
PROFILE = re.compile(r"<<<PROFILE\s*\n(.*?)\nPROFILE>>>", re.S)
FAR_FUTURE = datetime(9999, 1, 1, tzinfo=timezone.utc)
# Project folders under ~/.claude/projects are named after the path with separators as "-".
HOME_PREFIX = re.sub(r"[:\\/]", "-", str(Path.home())) + "-"


def load_terms():
    """The CS terms the user is meant to pick up: the first column of the table under
    "## Terms" in progress.md, aliases split on " / " (2026-10-13). Only the user's own
    prompts are searched for them, never Claude's text, so a term counts once it is the
    user's word."""
    try:
        text = (LEARNING / "progress.md").read_text(encoding="utf-8")
    except Exception:
        return []
    m = re.search(r"^## Terms[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    terms = []
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not cells[0] or cells[0].startswith("-") or cells[0].lower() == "term":
            continue
        for alias in cells[0].split(" / "):
            alias = alias.strip().strip("`*")
            if alias:
                terms.append(alias)
    return terms


def term_pattern(term):
    # whole words, hyphen or space between the words, any ending on the last word
    # ("rate limit" also finds "rate-limiting"); the look-around keeps "contract" from
    # matching inside "contracted rates"
    words = [re.escape(w) for w in re.split(r"[\s-]+", term) if w]
    return re.compile(r"(?<![\w-])" + r"[\s-]+".join(words) + r"(?![\w-])", re.I)


TERMS = load_terms()
TERM_PATTERNS = [(t, term_pattern(t)) for t in TERMS]
# The line Claude writes the first time a term comes up: `term = plain meaning; edat example`.
TERM_LINE = re.compile(
    r"^\s*(\*\*)?(" + "|".join(re.escape(t) for t in TERMS) + r")(\*\*)?\s*=\s", re.I | re.M
) if TERMS else None


def last_review():
    try:
        return date.fromisoformat(LAST.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def pending():
    return WEEKLY.exists() and "Interpretation: pending" in WEEKLY.read_text(encoding="utf-8")


def new_tally():
    return {
        "sessions": set(), "projects": Counter(), "prompts": [], "agents": Counter(),
        "skills": Counter(), "slash": Counter(), "rejected": 0, "denied": 0,
        "interrupts": 0, "paid_blocks": 0, "paid_runs": 0,
        "asked": 0, "answered": 0, "sure": 0, "asked_kind": Counter(), "terms_shown": 0,
    }


def parse_when(ts):
    try:
        when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when


def scan(windows, mtime_cutoff=None):
    """Read every transcript once; a record lands in the first window (since, until, tally)
    with since <= timestamp < until. One pass for all weeks, since the transcripts are large."""
    for path in (HOME / "projects").glob("*/*.jsonl"):
        try:
            if mtime_cutoff is not None and path.stat().st_mtime < mtime_cutoff:
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        session = path.stem
        project = path.parent.name.replace(HOME_PREFIX, "")
        # Per session, not per window: a rating next Monday still closes this week's question.
        open_question = False
        for line in lines:
            try:
                o = json.loads(line)
            except Exception:
                continue
            when = parse_when(o.get("timestamp") or "")
            if when is None or o.get("isSidechain"):
                continue
            t = None
            for since, until, tally in windows:
                if since <= when < until:
                    t = tally
                    break
            if t is None:
                continue
            msg = o.get("message") or {}
            content = msg.get("content")
            if o.get("type") == "assistant":
                for c in content or []:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "text":
                        text = c.get("text") or ""
                        q = QUESTION.search(text)
                        if q and not open_question:
                            t["asked"] += 1
                            t["asked_kind"][q.group(2).lower().replace("tradeoff", "trade-off")] += 1
                            open_question = True
                        if TERM_LINE is not None:
                            # a "term = " line inside a fenced code block is code, not a term line
                            prose = re.sub(r"```.*?```", "", text, flags=re.S)
                            t["terms_shown"] += len(TERM_LINE.findall(prose))
                        rating = RATING.search(text)
                        if rating and open_question:
                            t["answered"] += 1
                            if rating.group(2).lower() in ("sure", "unsure"):
                                t["sure"] += 1
                            open_question = False
                    if c.get("type") == "tool_use":
                        inp = c.get("input") or {}
                        name = c.get("name")
                        if name in ("Agent", "Task"):
                            t["agents"][str(inp.get("subagent_type") or "general-purpose")] += 1
                        if name == "Skill":
                            t["skills"][str(inp.get("skill"))] += 1
                        if name in ("Bash", "PowerShell") and PAID_MARKER in str(inp.get("command") or ""):
                            t["paid_runs"] += 1
                        if name == "AskUserQuestion":
                            for q in inp.get("questions") or []:
                                if not isinstance(q, dict):
                                    continue
                                qm = QUESTION.search(q.get("question") or "")
                                if qm:
                                    if not open_question:
                                        t["asked"] += 1
                                        t["asked_kind"][qm.group(2).lower().replace("tradeoff", "trade-off")] += 1
                                    open_question = True
                continue
            if o.get("type") != "user":
                continue
            if isinstance(content, list):
                for c in content:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "tool_result":
                        head = json.dumps(c.get("content"))[:400]
                        if "denied by the Claude Code auto mode" in head:
                            t["denied"] += 1
                        elif "doesn't want to proceed" in head or "tool use was rejected" in head:
                            t["rejected"] += 1
                        if "costs money" in head and "EDAT_PAID_OK" in head:
                            t["paid_blocks"] += 1
                    elif c.get("type") == "text" and "[Request interrupted by user" in c.get("text", ""):
                        t["interrupts"] += 1
                continue
            if not isinstance(content, str) or o.get("isMeta"):
                continue
            if "[Request interrupted by user" in content:
                t["interrupts"] += 1
                continue
            m = re.search(r"<command-name>/?([^<]+)</command-name>", content)
            if m:
                t["slash"][m.group(1).strip()] += 1
                continue
            # Mask pasted blocks first: a prompt that opens with a paste still holds the
            # user's own words after it (found by a fixture test on 2026-10-13).
            text = re.sub(r"<pasted_content.*?</pasted_content[^>]*>", "[pasted]", content, flags=re.S).strip()
            if text.startswith("<") or text.startswith("Caveat:") or not text:
                continue
            t["prompts"].append(text)
            t["sessions"].add(session)
            t["projects"][project] += 1


def finish(t):
    t["sessions"] = len(t["sessions"])
    return t


def collect(since, until=None):
    """Counts for since <= timestamp < until. With until=None (the hook and --force path)
    the window is open-ended and transcripts untouched since a day before `since` are skipped."""
    t = new_tally()
    if until is None:
        scan([(since, FAR_FUTURE, t)], mtime_cutoff=since.timestamp() - 86400)
    else:
        scan([(since, until, t)])
    return finish(t)


def prompt_stats(prompts):
    lengths = sorted(len(p) for p in prompts)
    median = lengths[len(lengths) // 2] if lengths else 0
    corrections = [p for p in prompts if CORRECTION.search(p)]
    done_when = sum(1 for p in prompts if DONE_WHEN.search(p))
    dont_understand = sum(1 for p in prompts if DONT_UNDERSTAND.search(p))
    terms = Counter()
    for p in prompts:
        # A prompt that long is a pasted report or skill text, not the user's own words
        # (2026-10-13: three of seven hits were 15-22k-char pastes without a pasted tag).
        if len(p) > 1500:
            continue
        for term, pattern in TERM_PATTERNS:
            if pattern.search(p):
                terms[term] += 1
    return median, corrections, done_when, dont_understand, terms


def entry(since, today, d):
    prompts = d["prompts"]
    median, corrections, done_when, _, terms = prompt_stats(prompts)
    kinds = ", ".join(f"{k} {v}" for k, v in d["asked_kind"].most_common()) or "none"
    words = ", ".join(f"{k} {v}" for k, v in terms.most_common()) or "none"
    lines = [
        f"## Week ending {today.isoformat()}",
        "",
        f"Window: {since.date().isoformat()} to {today.isoformat()} (all projects).",
        "",
        f"- Sessions: {d['sessions']}; prompts: {len(prompts)}; median prompt length: {median} chars",
        f"- Projects: {', '.join(f'{k} {v}' for k, v in d['projects'].most_common()) or 'none'}",
        f"- Questions (D-089, four kinds since 2026-10-13): asked {d['asked']} ({kinds}); answered {d['answered']}; 'sure'/'unsure' said: {d['sure']}",
        f"- CS terms in your own prompts (progress.md 'Terms'): {sum(terms.values())} ({words}); term lines Claude set out: {d['terms_shown']}",
        "",
        "Background only, no targets:",
        f"- Prompts with a 'done when': {done_when}",
        f"- Correction prompts ('no,', 'wrong', 'I told you'…): {len(corrections)}",
        f"- Actions you rejected: {d['rejected']}; interrupts: {d['interrupts']}; auto-mode blocks: {d['denied']}; paid-run guard blocks: {d['paid_blocks']}",
        f"- Subagents: {sum(d['agents'].values())} ({', '.join(f'{k} {v}' for k, v in d['agents'].most_common()) or 'none'})",
        f"- Skills: {', '.join(f'{k} {v}' for k, v in d['skills'].most_common()) or 'none'}",
        f"- Slash commands: {', '.join(f'{k} {v}' for k, v in d['slash'].most_common()) or 'none'}",
        "",
        "Sample corrections (first 80 chars):",
    ]
    for p in corrections[:8]:
        lines.append("- " + p[:80].replace("\n", " "))
    lines += ["", "Interpretation: pending", ""]
    return "\n".join(lines)


def write_entry():
    today = date.today()
    since = datetime.now(timezone.utc) - timedelta(days=DAYS)
    text = entry(since, today, collect(since))
    if not WEEKLY.exists():
        WEEKLY.write_text("# Weekly learning log\n\nWritten by weekly_stats.py every 7 days; "
                          "the weekly-review skill fills in each Interpretation.\n\n", encoding="utf-8")
    with WEEKLY.open("a", encoding="utf-8") as f:
        f.write(text + "\n")
    LAST.write_text(today.isoformat(), encoding="utf-8")


def window_of(week_ending):
    """The local-midnight bounds of a row: six days before the Monday through the Monday itself,
    so "week ending 2026-10-12" covers 10-06 00:00 to 10-13 00:00, like the weekly.md entries."""
    start = datetime.combine(week_ending - timedelta(days=DAYS - 1), datetime.min.time()).astimezone()
    end = datetime.combine(week_ending + timedelta(days=1), datetime.min.time()).astimezone()
    return start, end


def first_transcript_date():
    """Local date of the oldest timestamp; a session file is chronological, so its first
    timestamped line is its oldest and the whole file need not be read."""
    oldest = None
    for path in (HOME / "projects").glob("*/*.jsonl"):
        try:
            with path.open(encoding="utf-8") as f:
                for line in f:
                    m = re.search(r'"timestamp"\s*:\s*"([^"]+)"', line)
                    if not m:
                        continue
                    when = parse_when(m.group(1))
                    if when is not None and (oldest is None or when < oldest):
                        oldest = when
                    break
        except Exception:
            continue
    return oldest.astimezone().date() if oldest else date.today()


def load_overrides():
    try:
        data = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def week_rows():
    """One row per Monday from the first transcript's week to the latest Monday on or before today."""
    today = date.today()
    first = first_transcript_date()
    monday = first + timedelta(days=(7 - first.weekday()) % 7)  # the Monday whose window holds `first`
    last = today - timedelta(days=today.weekday())
    windows = []
    mondays = []
    while monday <= last:
        start, end = window_of(monday)
        windows.append((start, end, new_tally()))
        mondays.append(monday)
        monday += timedelta(days=DAYS)
    scan(windows)
    overrides = load_overrides()
    rows = []
    for (start, _end, t), week_ending in zip(windows, mondays):
        finish(t)
        median, corrections, done_when, dont_understand, terms = prompt_stats(t["prompts"])
        row = {
            "week_ending": week_ending.isoformat(),
            "window_start": start.date().isoformat(),
            "sessions": t["sessions"],
            "prompts": len(t["prompts"]),
            "median_prompt_chars": median,
            "projects": dict(t["projects"].most_common()),
            "code_q_asked": t["asked"],
            "code_q_answered": t["answered"],
            "code_q_sure": t["sure"],
            "question_kinds": dict(t["asked_kind"].most_common()),
            "terms_used": sum(terms.values()),
            "terms_by_word": dict(terms.most_common()),
            "terms_shown": t["terms_shown"],
            "done_when": done_when,
            "corrections": len(corrections),
            "dont_understand": dont_understand,
            "rejected": t["rejected"],
            "interrupts": t["interrupts"],
            "auto_mode_blocks": t["denied"],
            "paid_guard_blocks": t["paid_blocks"],
            "paid_runs": t["paid_runs"],
            "agent_runs": sum(t["agents"].values()),
            "agents_by_type": dict(t["agents"].most_common()),
            "skills": dict(t["skills"].most_common()),
            "slash": dict(t["slash"].most_common()),
        }
        override = overrides.get(row["week_ending"])
        if isinstance(override, dict):
            replaced = []
            for key, value in override.items():
                if key == "note":
                    row["note"] = value
                elif key in row:
                    row[key] = value
                    replaced.append(key)
            if replaced:
                row["overrides"] = replaced
        rows.append(row)
    return rows


def write_json():
    rows = week_rows()
    out = {"generated": datetime.now().astimezone().isoformat(timespec="seconds"), "weeks": rows}
    WEEKLY_JSON.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return rows


def print_rows(rows):
    cols = ["week_ending", "prompts", "corrections", "dont_understand", "rejected", "interrupts",
            "auto_mode_blocks", "paid_guard_blocks", "agent_runs", "paid_runs",
            "code_q_asked", "code_q_answered", "code_q_sure", "terms_used", "terms_shown"]
    print("\t".join(cols))
    for r in rows:
        print("\t".join(str(r[c]) for c in cols) + ("\toverrides=" + ",".join(r["overrides"]) if r.get("overrides") else ""))


def apply(out_path):
    """Write what the headless review printed into weekly.md (run_weekly.ps1 calls this).
    Claude may not edit ~/.claude files in a non-interactive run (seen 2026-10-12), so the
    skill prints the interpretation between markers and this puts it in place. Profile
    changes are only noted; the next interactive session applies them."""
    out = Path(out_path).read_text(encoding="utf-8-sig", errors="replace")
    weekly = WEEKLY.read_text(encoding="utf-8")
    m = INTERP.search(out)
    if not m:
        print("no <<<INTERPRETATION block in " + out_path + "; weekly.md left pending")
        return
    block = "Interpretation (" + date.today().isoformat() + ", written by the Monday task):\n" + m.group(1).strip()
    p = PROFILE.search(out)
    if p:
        block += "\n\nProfile changes: pending (apply in the next interactive session)\n" + p.group(1).strip()
    if "Interpretation: pending" not in weekly:
        print("weekly.md has no pending entry; nothing applied")
        return
    weekly = weekly.replace("Interpretation: pending", block, 1)
    WEEKLY.write_text(weekly, encoding="utf-8")
    print("interpretation applied")


def profile_pending():
    return WEEKLY.exists() and "Profile changes: pending" in WEEKLY.read_text(encoding="utf-8")


def hook():
    last = last_review()
    wrote = False
    if last is None or (date.today() - last).days >= DAYS:
        write_entry()
        wrote = True
    if not pending() and not profile_pending():
        return
    if pending():
        context = ("Weekly learning review is due: ~/.claude/learning/weekly.md has an entry with "
                   "'Interpretation: pending'. Before the user's first task, run the weekly-review skill "
                   "without asking (the user chose automatic weekly updates on 2026-10-07), keep it short, "
                   "then carry on with their request.")
    else:
        context = ("The Monday learning review ran headless and left 'Profile changes: pending' in the "
                   "newest entry of ~/.claude/learning/weekly.md. Before the user's first task, apply "
                   "those changes to profile.md / agentic-coding.md exactly as listed, replace that line "
                   "with 'Profile changes: applied <today>', tell the user in one line, then carry on.")
    out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
    if wrote:
        out["systemMessage"] = "Weekly learning stats written to ~/.claude/learning/weekly.md; Claude will update your profile."
    print(json.dumps(out))


if __name__ == "__main__":
    started = time.time()
    if "--force" in sys.argv:
        write_entry()
        print(f"entry written in {time.time() - started:.1f}s")
        rows = write_json()
        print(f"weekly.json rebuilt with {len(rows)} weeks in {time.time() - started:.1f}s")
    elif "--json" in sys.argv:
        rows = write_json()
        print_rows(rows)
        print(f"weekly.json rebuilt with {len(rows)} weeks in {time.time() - started:.1f}s")
    elif "--apply" in sys.argv:
        apply(sys.argv[sys.argv.index("--apply") + 1])
    elif "--html" in sys.argv:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import weekly_page  # the progress page, built from all three learning files

        weekly_page.render()
    else:
        try:
            hook()
        except Exception:
            pass
