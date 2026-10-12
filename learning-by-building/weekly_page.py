"""Render the learning progress page, ~/.claude/learning/weekly.html, from the three learning
files. Free, offline, no Claude call. The Monday job (run_weekly.ps1) runs it last;
weekly_stats.py --html calls it too.

    python weekly_page.py

Why a page: the user (2026-10-12) could not use the raw weekly.md: "it doesn't show me how
good I got, how I progressed, what I did not good, what I learned, what I should learn".
Those answers live in profile.md (Strong / Developing / Revisit, "Now"), progress.md
(Records, Needs reinforcement, Shown so far) and weekly.md (the counts per week), so the
page pulls them together. It invents nothing: an empty section says so.
"""

import html
import re
from pathlib import Path

LEARNING = Path.home() / ".claude" / "learning"
PROFILE = LEARNING / "profile.md"
PROGRESS = LEARNING / "progress.md"
WEEKLY = LEARNING / "weekly.md"
PAGE = LEARNING / "weekly.html"


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def sections(text):
    """{heading: body} for every '## ' heading; '### ' stays inside its parent."""
    out = {}
    name = None
    body = []
    for line in text.splitlines():
        if line.startswith("## "):
            if name is not None:
                out[name] = "\n".join(body).strip()
            name = line[3:].strip()
            body = []
        else:
            body.append(line)
    if name is not None:
        out[name] = "\n".join(body).strip()
    return out


def get(secs, name, default=""):
    """Section body by heading prefix: '## Shown so far (exposure, not learning)' is found
    by 'Shown so far'."""
    for heading, body in secs.items():
        if heading == name or heading.startswith(name + " ("):
            return body
    return default


def bullets(body):
    """Top-level '- ' items, continuation lines joined; empty list when none or 'none yet'."""
    items = []
    for line in body.splitlines():
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif line.startswith("  ") and items:
            items[-1] += " " + line.strip()
    return [i for i in items if i and not i.lower().startswith("none")]


def inline(t):
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", lambda m: "<code>" + m.group(1) + "</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", lambda m: "<strong>" + m.group(1) + "</strong>", t)
    return t


def ul(items, empty):
    if not items:
        return '<p class="empty">' + inline(empty) + "</p>"
    return "<ul>" + "".join("<li>" + inline(i) + "</li>" for i in items) + "</ul>"


def date_of(item):
    m = re.match(r"(\d{4}-\d{2}-\d{2})", item)
    return m.group(1) if m else ""


def week_rows(weekly):
    rows = []
    for part in re.split(r"(?m)^## Week ending ", weekly)[1:]:
        lines = part.splitlines()
        week = lines[0].strip()
        text = "\n".join(lines)
        prompts = re.search(r"prompts: (\d+)", text)
        asked = re.search(r"asked (\d+); answered (\d+); 'sure'/'unsure' said: (\d+)", text)
        agents = re.search(r"Subagents: (\d+)", text)
        judged = "Interpretation: pending" not in text
        rows.append(
            {
                "week": week,
                "prompts": prompts.group(1) if prompts else "",
                "asked": asked.group(1) if asked else "0",
                "answered": asked.group(2) if asked else "0",
                "sure": asked.group(3) if asked else "0",
                "agents": agents.group(1) if agents else "",
                "judged": judged,
                "interp": interpretation(text),
            }
        )
    rows.reverse()
    return rows


def interpretation(entry_text):
    """The bullets right under the 'Interpretation (...):' line, up to the first blank line."""
    lines = entry_text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("Interpretation (") and line.rstrip().endswith(":"):
            block = []
            for rest in lines[i + 1 :]:
                if not rest.strip():
                    break
                block.append(rest)
            return bullets("\n".join(block))
    return []


def status_block(profile):
    strong = bullets(get(profile, "Strong", ""))
    developing = bullets(get(profile, "Developing", ""))
    revisit = bullets(get(profile, "Revisit", ""))
    cards = [
        ("Strong", "shown more than once, checked each time", strong),
        ("Developing", "done once, or shown and partly applied", developing),
        ("Revisit", "got it wrong, needs another go", revisit),
    ]
    out = ['<div class="cards">']
    for title, hint, items in cards:
        out.append('<div class="card"><h3>' + title + " <span>" + str(len(items)) + "</span></h3>")
        out.append('<p class="hint">' + hint + "</p>")
        out.append(ul(items, "nothing here yet"))
        out.append("</div>")
    out.append("</div>")
    return "\n".join(out)


def render():
    profile = sections(read(PROFILE))
    progress = sections(read(PROGRESS))
    weekly = read(WEEKLY)
    weeks = week_rows(weekly)
    this_week = weeks[0] if weeks else None

    records = bullets(get(progress, "Records", ""))
    records_newest_first = sorted(records, key=date_of, reverse=True)
    week_date = this_week["week"] if this_week else ""
    recent = [r for r in records_newest_first if week_date and date_of(r) and date_of(r) > shift(week_date, -7)]
    needs = bullets(get(progress, "Needs reinforcement", ""))
    words = bullets(get(progress, "Words you used", ""))
    shown = bullets(get(progress, "Shown so far", ""))
    shown_titles = [re.sub(r"\*\*|\(.*", "", s).split(":")[0].strip() for s in shown]
    now = bullets(get(profile, "Now", ""))
    gaps = [r for r in bullets(get(progress, "Resources", "")) if r.lower().startswith("gaps")]

    parts = []
    parts.append("<h1>Learning progress</h1>")
    parts.append(
        '<p class="lead">Built from your three learning files, nothing invented. '
        "Week ending <strong>" + inline(week_date or "–") + "</strong>.</p>"
    )

    parts.append("<section><h2>This week, in plain words</h2>")
    if this_week and this_week["interp"]:
        for item in this_week["interp"]:
            m = re.match(r"\*\*([^*]+?):?\*\*:?\s*(.*)", item, re.S)
            if m:
                parts.append("<h3>" + inline(m.group(1)) + "</h3><p>" + inline(m.group(2)) + "</p>")
            else:
                parts.append("<p>" + inline(item) + "</p>")
    else:
        parts.append('<p class="empty">The Monday judgement for this week is not written yet.</p>')
    parts.append("</section>")

    parts.append("<section><h2>How you stand</h2>")
    parts.append(status_block(profile))
    parts.append("</section>")

    parts.append("<section><h2>This week: the checks behind it</h2>")
    if this_week:
        parts.append(
            '<p class="nums">Code questions: <b>' + this_week["asked"] + "</b> asked, <b>"
            + this_week["answered"] + "</b> answered, <b>" + this_week["sure"]
            + "</b> with sure/unsure said first. Project work alongside: " + this_week["prompts"]
            + " prompts, " + this_week["agents"] + " agent runs.</p>"
        )
    parts.append(ul(recent, "No record this week: nothing you did was checked. The loop stalled, not you."))
    parts.append("</section>")

    parts.append("<section><h2>Not good yet</h2>")
    parts.append(ul(needs, "nothing marked"))
    parts.append("</section>")

    parts.append("<section><h2>Learn next</h2>")
    parts.append(ul(now, "nothing planned"))
    parts.append(ul(gaps, ""))
    parts.append("</section>")

    parts.append("<section><h2>Everything you did so far, newest first</h2>")
    parts.append(ul(records_newest_first, "no record yet"))
    parts.append("<h3>Words you used and defended</h3>")
    parts.append(ul(words, "none yet; the first term you use and defend in a session lands here"))
    parts.append("</section>")

    parts.append("<section><h2>Shown to you, not practised yet</h2>")
    parts.append(ul(shown_titles, "nothing"))
    parts.append("</section>")

    parts.append("<section><h2>Week by week</h2>")
    parts.append("<table><tr><th>Week</th><th>Code questions asked</th><th>answered</th><th>sure/unsure said</th><th>Prompts</th><th>Judged</th></tr>")
    for w in weeks:
        parts.append(
            "<tr><td>" + inline(w["week"]) + "</td><td>" + w["asked"] + "</td><td>" + w["answered"]
            + "</td><td>" + w["sure"] + "</td><td>" + w["prompts"] + "</td><td>" + ("yes" if w["judged"] else "pending") + "</td></tr>"
        )
    parts.append("</table>")
    parts.append('<p class="hint">Counts before 2026-10-12 were made by hand from the session logs; from then on the script counts the "Code question" and "Rating" lines.</p>')
    parts.append("</section>")

    page = (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>Learning progress</title><style>"
        ":root{--bg:#fbfaf7;--fg:#1f2328;--muted:#6b7280;--line:#e5e1d8;--mark:#b45309;--code:#efece5;--card:#fff}"
        "@media(prefers-color-scheme:dark){:root{--bg:#17191c;--fg:#e6e3dc;--muted:#9aa0a6;--line:#2c3036;--mark:#f0a24b;--code:#24282e;--card:#1e2126}}"
        "body{margin:0;padding:24px 16px 64px;background:var(--bg);color:var(--fg);"
        "font:16px/1.55 Georgia,'Times New Roman',serif;max-width:860px;margin-inline:auto}"
        "h1{font-size:1.6rem;margin:0 0 4px}.lead{color:var(--muted);margin-top:0}"
        "section{border-top:1px solid var(--line);padding-top:16px;margin-top:28px}"
        "h2{font-size:1.25rem;margin:0 0 10px}h3{font-size:1rem;margin:16px 0 6px}"
        "ul{padding-left:20px;margin:6px 0}li{margin:6px 0}"
        ".cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}"
        ".card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px}"
        ".card h3{margin:0;display:flex;justify-content:space-between}.card h3 span{color:var(--mark)}"
        ".hint{color:var(--muted);font-size:.9em;margin:4px 0 8px}.empty{color:var(--muted);font-style:italic}"
        ".nums b{color:var(--mark)}"
        "table{border-collapse:collapse;width:100%;font-size:.95em}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}"
        "th{color:var(--muted);font-weight:normal}"
        "code{background:var(--code);padding:1px 4px;border-radius:3px;font-size:.9em}"
        "</style></head><body>" + "\n".join(parts) + "</body></html>"
    )
    PAGE.write_text(page, encoding="utf-8")
    print("page written: " + str(PAGE))


def shift(iso, days):
    from datetime import date, timedelta

    try:
        return (date.fromisoformat(iso) + timedelta(days=days)).isoformat()
    except Exception:
        return ""


if __name__ == "__main__":
    render()
