"""Weekly learning check, run by a SessionStart hook in ~/.claude/settings.json.

Once every 7 days it counts how the user worked with Claude Code in the last
7 days (all projects), appends the counts to ~/.claude/learning/weekly.md with
"Interpretation: pending", and tells Claude to run the weekly-review skill,
which interprets the counts and updates profile.md. While an entry is still
pending, every session start reminds Claude again. Otherwise it prints nothing.

Counts and the user's own short prompts only; tool output (which can hold
document text) is never copied.

    python weekly_stats.py --hook     as the hook: maybe write, maybe remind
    python weekly_stats.py --force    write an entry now, whatever the date
    python weekly_stats.py --apply F  write the interpretation printed in file F into weekly.md
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
LAST = LEARNING / ".last_review"
DAYS = 7
# Text a paid-run guard hook prints when it blocks a command, if you have one.
PAID_GUARD_TEXT = "costs money"
# Claude Code names a project folder after its path; this prefix is your home folder.
HOME_PREFIX = re.sub(r"[:\\/]", "-", str(Path.home())) + "-"

# Background context only, never a target: "explain" is good learning
# behaviour, and "don't"/"stop" are ordinary instructions, so neither is counted.
CORRECTION = re.compile(r"^\s*(no[,!. ]|nein|nope|wrong|falsch|why did|that'?s not|not what|i told you)", re.I)
DONE_WHEN = re.compile(r"done when|definition of done|definiton of done|fertig wenn", re.I)
# The one practice that runs inside the work. Both ends are Claude's own markers, so a
# clarifying question by the user is not booked as an answer: a question is an assistant text
# block that starts with "Code question"; it counts as answered when a later assistant block in
# the same session carries a line "Rating (sure|unsure|not said): ...", and "sure/unsure said"
# is read off that rating. CLAUDE.snippet.md tells Claude to write both markers.
CODE_Q = re.compile(r"^\s*(\*\*)?code question\s*(\(|:|\*\*)", re.I)
RATING = re.compile(r"^\s*(\*\*)?rating\s*\((sure|unsure|not said)\)", re.I | re.M)
# The weekly job runs Claude without Edit; it prints these blocks and --apply writes them.
INTERP = re.compile(r"<<<INTERPRETATION\s*\n(.*?)\nINTERPRETATION>>>", re.S)
PROFILE = re.compile(r"<<<PROFILE\s*\n(.*?)\nPROFILE>>>", re.S)


def last_review():
    try:
        return date.fromisoformat(LAST.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def pending():
    return WEEKLY.exists() and "Interpretation: pending" in WEEKLY.read_text(encoding="utf-8")


def collect(since):
    sessions = set()
    projects = Counter()
    prompts = []
    agents = Counter()
    skills = Counter()
    slash = Counter()
    rejected = 0
    denied = 0
    interrupts = 0
    paid_blocks = 0
    asked = 0
    answered = 0
    sure = 0
    cutoff = since.timestamp() - 86400
    for path in (HOME / "projects").glob("*/*.jsonl"):
        try:
            if path.stat().st_mtime < cutoff:
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        open_question = False
        for line in lines:
            try:
                o = json.loads(line)
            except Exception:
                continue
            ts = o.get("timestamp") or ""
            try:
                when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if when < since or o.get("isSidechain"):
                continue
            msg = o.get("message") or {}
            content = msg.get("content")
            if o.get("type") == "assistant":
                for c in content or []:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "text":
                        text = c.get("text") or ""
                        if CODE_Q.search(text) and not open_question:
                            asked += 1
                            open_question = True
                        rating = RATING.search(text)
                        if rating and open_question:
                            answered += 1
                            if rating.group(2).lower() in ("sure", "unsure"):
                                sure += 1
                            open_question = False
                    if c.get("type") == "tool_use":
                        inp = c.get("input") or {}
                        if c.get("name") in ("Agent", "Task"):
                            agents[inp.get("subagent_type") or "general-purpose"] += 1
                        if c.get("name") == "Skill":
                            skills[inp.get("skill")] += 1
                        if c.get("name") == "AskUserQuestion":
                            for q in inp.get("questions") or []:
                                if isinstance(q, dict) and CODE_Q.search(q.get("question") or ""):
                                    if not open_question:
                                        asked += 1
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
                            denied += 1
                        elif "doesn't want to proceed" in head or "tool use was rejected" in head:
                            rejected += 1
                        if PAID_GUARD_TEXT in head:
                            paid_blocks += 1
                    elif c.get("type") == "text" and "[Request interrupted by user" in c.get("text", ""):
                        interrupts += 1
                continue
            if not isinstance(content, str) or o.get("isMeta"):
                continue
            if "[Request interrupted by user" in content:
                interrupts += 1
                continue
            m = re.search(r"<command-name>/?([^<]+)</command-name>", content)
            if m:
                slash[m.group(1).strip()] += 1
                continue
            if content.startswith("<") or content.startswith("Caveat:"):
                continue
            text = re.sub(r"<pasted_content.*?</pasted_content[^>]*>", "[pasted]", content, flags=re.S)
            prompts.append(text)
            sessions.add(path.stem)
            projects[path.parent.name.replace(HOME_PREFIX, "")] += 1
    return {
        "sessions": len(sessions), "projects": projects, "prompts": prompts, "agents": agents,
        "skills": skills, "slash": slash, "rejected": rejected, "denied": denied,
        "interrupts": interrupts, "paid_blocks": paid_blocks,
        "asked": asked, "answered": answered, "sure": sure,
    }


def entry(since, today, d):
    prompts = d["prompts"]
    lengths = sorted(len(p) for p in prompts)
    median = lengths[len(lengths) // 2] if lengths else 0
    corrections = [p for p in prompts if CORRECTION.search(p)]
    done_when = sum(1 for p in prompts if DONE_WHEN.search(p))
    lines = [
        f"## Week ending {today.isoformat()}",
        "",
        f"Window: {since.date().isoformat()} to {today.isoformat()} (all projects).",
        "",
        f"- Sessions: {d['sessions']}; prompts: {len(prompts)}; median prompt length: {median} chars",
        f"- Projects: {', '.join(f'{k} {v}' for k, v in d['projects'].most_common()) or 'none'}",
        f"- Code questions: asked {d['asked']}; answered {d['answered']}; 'sure'/'unsure' said: {d['sure']}",
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


HTML_PAGE = LEARNING / "weekly.html"


def html_escape(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(t):
    t = html_escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    return t


def render_html():
    """weekly.md as one page, newest week first, for reading on Monday (user, 2026-10-12:
    "do now html page for me to read"). No dependency: headings, bullets, bold, code."""
    text = WEEKLY.read_text(encoding="utf-8") if WEEKLY.exists() else ""
    parts = re.split(r"(?m)^## ", text)
    entries = [p for p in parts[1:] if p.strip()]
    entries.reverse()
    body = []
    for entry in entries:
        lines = entry.splitlines()
        body.append("<section><h2>" + inline(lines[0]) + "</h2>")
        in_list = False
        for line in lines[1:]:
            if line.startswith("- "):
                if not in_list:
                    body.append("<ul>")
                    in_list = True
                body.append("<li>" + inline(line[2:]) + "</li>")
                continue
            if in_list:
                body.append("</ul>")
                in_list = False
            if not line.strip():
                continue
            cls = ' class="judge"' if line.startswith("Interpretation") else ""
            body.append("<p" + cls + ">" + inline(line) + "</p>")
        if in_list:
            body.append("</ul>")
        body.append("</section>")
    page = (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>Weekly learning review</title><style>"
        ":root{--bg:#fbfaf7;--fg:#1f2328;--muted:#6b7280;--line:#e5e1d8;--mark:#b45309;--code:#efece5}"
        "@media(prefers-color-scheme:dark){:root{--bg:#17191c;--fg:#e6e3dc;--muted:#9aa0a6;--line:#2c3036;--mark:#f0a24b;--code:#24282e}}"
        "body{margin:0;padding:24px 16px 64px;background:var(--bg);color:var(--fg);"
        "font:16px/1.55 Georgia,'Times New Roman',serif;max-width:760px;margin-inline:auto}"
        "h1{font-size:1.5rem;margin:0 0 4px}h1+p{color:var(--muted);margin-top:0}"
        "section{border-top:1px solid var(--line);padding-top:16px;margin-top:24px}"
        "h2{font-size:1.2rem;margin:0 0 8px}ul{padding-left:20px;margin:6px 0}li{margin:4px 0}"
        "p.judge{color:var(--mark);font-weight:600;margin:16px 0 4px}"
        "code{background:var(--code);padding:1px 4px;border-radius:3px;font-size:.9em}"
        "</style></head><body><h1>Weekly learning review</h1>"
        "<p>Newest week first. The counts come from your session logs; the judgement is written "
        "by the weekly-review skill each Monday. Source: <code>~/.claude/learning/weekly.md</code>.</p>"
        + "\n".join(body)
        + "</body></html>"
    )
    HTML_PAGE.write_text(page, encoding="utf-8")
    print("html written: " + str(HTML_PAGE))


def apply(out_path):
    """Write what the headless review printed into weekly.md (run_weekly calls this).
    A non-interactive Claude may not edit ~/.claude files, so the skill prints the
    interpretation between markers and this puts it in place. Profile changes are only
    noted; the next interactive session applies them."""
    out = Path(out_path).read_text(encoding="utf-8-sig", errors="replace")
    weekly = WEEKLY.read_text(encoding="utf-8")
    m = INTERP.search(out)
    if not m:
        print("no <<<INTERPRETATION block in " + out_path + "; weekly.md left pending")
        return
    block = "Interpretation (" + date.today().isoformat() + ", written by the weekly job):\n" + m.group(1).strip()
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
                   "without asking (the user chose automatic weekly updates), keep it short, "
                   "then carry on with their request.")
    else:
        context = ("The weekly learning review ran headless and left 'Profile changes: pending' in the "
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
    elif "--apply" in sys.argv:
        apply(sys.argv[sys.argv.index("--apply") + 1])
    elif "--html" in sys.argv:
        render_html()
    else:
        try:
            hook()
        except Exception:
            pass
