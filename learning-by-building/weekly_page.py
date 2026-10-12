"""Render the weekly learning review, ~/.claude/learning/weekly.html, as a short newsletter:
headline numbers, the Monday judgement, small charts, where you stand, what is next, one
table. Free, offline, no Claude call, no external request. The Monday job (run_weekly.ps1)
runs it last; weekly_stats.py --html calls render() too.

    python weekly_page.py                 # real files
    python weekly_page.py --data <path>   # another weekly.json, for testing

Inputs, all in this folder: weekly.json (the counts per week, oldest first), weekly.md (the
judgement under the newest "Interpretation (" line), profile.md (Strong / Developing /
Revisit / Now), progress.md (Needs reinforcement). It invents nothing: an empty section
says so.
"""

import html
import json
import re
import sys
from pathlib import Path

LEARNING = Path.home() / ".claude" / "learning"
PROFILE = LEARNING / "profile.md"
PROGRESS = LEARNING / "progress.md"
WEEKLY = LEARNING / "weekly.md"
DATA = LEARNING / "weekly.json"
PAGE = LEARNING / "weekly.html"

# key, label, direction of "good": +1 up is good, -1 down is good, 0 neutral
TILES = [
    ("code_q_answered", "Code questions answered", 1),
    ("corrections", "Corrections", -1),
    ("rejected", "Rejected actions", -1),
    ("interrupts", "Interrupts", -1),
    ("dont_understand", "“Don’t understand” prompts", -1),
    ("agent_runs", "Agent runs", 0),
    ("prompts", "Prompts", 0),
    ("paid_runs", "Paid-run commands", 0),
]

CHARTS = [
    ("corrections", "Corrections"),
    ("rejected", "Rejected actions"),
    ("interrupts", "Interrupts"),
    ("dont_understand", "“Don’t understand” prompts"),
    ("code_q_answered", "Code questions answered (asked behind)"),
    ("agent_runs", "Agent runs"),
    ("prompts", "Prompts"),
    ("paid_runs", "Paid-run commands"),
]

LABELS = [
    "How you got better",
    "What went wrong",
    "What you learned",
    "Learn next",
    "How you worked with Claude",
    "Context",
]


# ---------------------------------------------------------------- reading


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
    """Top-level '- ' items; a continuation line (indented two spaces) stays a separate line
    inside its item, joined with '\\n'. Empty list when none or 'none yet'."""
    items = []
    for line in body.splitlines():
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif line.startswith("  ") and items:
            items[-1] += "\n" + line.strip()
    return [i for i in items if i and not i.lower().startswith("none")]


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


def week_rows(weekly):
    """One dict per '## Week ending' entry in weekly.md, newest first."""
    rows = []
    for part in re.split(r"(?m)^## Week ending ", weekly)[1:]:
        lines = part.splitlines()
        week = lines[0].strip()
        text = "\n".join(lines)
        rows.append({"week": week, "interp": interpretation(text)})
    rows.reverse()
    return rows


def judgement_blocks(items):
    """[(label, [sentence, ...])] from the interpretation bullets '- **Label:** text'."""
    blocks = []
    for item in items:
        m = re.match(r"\*\*([^*]+?):?\*\*:?\s*(.*)", item, re.S)
        if m:
            label = m.group(1).strip()
            text = m.group(2)
        else:
            label = ""
            text = item
        lines = []
        for sentence in text.split("\n"):
            if sentence.strip():
                lines.append(sentence.strip())
        blocks.append((label, lines))
    return blocks


def load_weeks(data_path):
    try:
        data = json.loads(Path(data_path).read_text(encoding="utf-8"))
    except Exception:
        return []
    weeks = data.get("weeks", []) if isinstance(data, dict) else []
    weeks = [w for w in weeks if isinstance(w, dict) and w.get("week_ending")]
    weeks.sort(key=lambda w: w["week_ending"])
    return weeks


def num(week, key):
    v = week.get(key) if week else None
    return v if isinstance(v, (int, float)) else 0


# ---------------------------------------------------------------- html bits


def inline(t):
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", lambda m: "<code>" + m.group(1) + "</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", lambda m: "<strong>" + m.group(1) + "</strong>", t)
    t = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", lambda m: "<em>" + m.group(1) + "</em>", t)
    return t


def ul(items, empty):
    if not items:
        return '<p class="empty">' + inline(empty) + "</p>"
    out = ["<ul>"]
    for i in items:
        out.append("<li>" + "<br>".join(inline(line) for line in i.split("\n")) + "</li>")
    out.append("</ul>")
    return "".join(out)


def short(items):
    """Bullets as one short line each: wrapped lines joined, every (parenthetical) removed,
    the first sentence kept."""
    out = []
    for i in items:
        text = " ".join(i.split("\n"))
        while re.search(r"\([^()]*\)", text):
            text = re.sub(r"\s*\([^()]*\)", "", text)
        first = re.split(
            r"(?<!incl\.)(?<!e\.g\.)(?<!i\.e\.)(?<=[.!?])\s+(?=[A-Z“\"])", text.strip(), maxsplit=1
        )[0]
        out.append(first.strip().rstrip(".:"))
    return out


def fmt(n):
    if isinstance(n, float) and not n.is_integer():
        return "{:.1f}".format(n)
    return "{:,}".format(int(n))


def tiles(this, last):
    out = ['<div class="tiles">']
    for key, label, good in TILES:
        cur = num(this, key)
        out.append('<div class="tile"><div class="v">' + fmt(cur) + "</div>")
        out.append('<div class="l">' + inline(label) + "</div>")
        if last is None:
            out.append('<div class="d neutral">no earlier week</div>')
        else:
            d = cur - num(last, key)
            if d == 0:
                cls, arrow = "neutral", "→"
            else:
                arrow = "↑" if d > 0 else "↓"
                if good == 0:
                    cls = "neutral"
                elif (d > 0) == (good > 0):
                    cls = "good"
                else:
                    cls = "bad"
            sign = "+" if d > 0 else ("−" if d < 0 else "±")
            out.append(
                '<div class="d ' + cls + '">' + arrow + " " + sign + fmt(abs(d)) + " vs last week</div>"
            )
        out.append("</div>")
    out.append("</div>")
    return "\n".join(out)


def bar_path(x, base, w, h):
    """A bar standing on y=base with its top two corners rounded (4px, less for a tiny bar);
    a zero bar is a 1px hairline so the week still shows up on hover."""
    h = max(h, 1)
    r = min(4, h / 2, w / 2)
    y = base - h
    return "M%.1f,%.1f V%.1f Q%.1f,%.1f %.1f,%.1f H%.1f Q%.1f,%.1f %.1f,%.1f V%.1f Z" % (
        x, base, y + r, x, y, x + r, y, x + w - r, x + w, y, x + w, y + r, base
    )


def bar_chart(weeks, key, title, behind=None):
    """One small bar chart as inline SVG: x = week_ending, last bar in the accent, earlier
    bars in the lighter step, an optional second series (behind) as a wider lighter bar."""
    n = len(weeks)
    w, h = 300, 120
    top, bottom, left, right = 22, 26, 6, 6
    plot_h = h - top - bottom
    vals = [num(wk, key) for wk in weeks]
    back = [num(wk, behind) for wk in weeks] if behind else [0] * n
    peak = max(vals + back + [1])
    # at most 48px per week so a short history does not become four fat blocks
    slot = min((w - left - right) / max(n, 1), 48)
    gap = 2
    bar_w = max(slot - gap, 4)
    out = [
        '<svg class="chart" viewBox="0 0 ' + str(w) + " " + str(h) + '" role="img" aria-label="'
        + html.escape(title) + '">',
        '<text class="t" x="0" y="13">' + inline(title) + "</text>",
    ]
    for i, wk in enumerate(weeks):
        x = left + i * slot + gap / 2
        label = wk["week_ending"]
        if behind:
            bh = back[i] / peak * plot_h
            out.append(
                '<path class="back" d="%s"><title>%s: %s asked</title></path>'
                % (bar_path(x, top + plot_h, bar_w, bh), html.escape(label), fmt(back[i]))
            )
        bh = vals[i] / peak * plot_h
        bw = bar_w * 0.6 if behind else bar_w
        bx = x + (bar_w - bw) / 2
        cls = "cur" if i == n - 1 else "prev"
        out.append(
            '<path class="%s" d="%s"><title>%s: %s</title></path>'
            % (cls, bar_path(bx, top + plot_h, bw, bh), html.escape(label), fmt(vals[i]))
        )
        if i == n - 1:
            out.append(
                '<text class="val" x="%.1f" y="%.1f" text-anchor="middle">%s</text>'
                % (x + bar_w / 2, max(top + plot_h - bh - 4, 12), fmt(vals[i]))
            )
    out.append(
        '<line class="axis" x1="%d" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (left, top + plot_h, left + n * slot, top + plot_h)
    )
    # x labels: first and last week, month-day only, so they never collide
    if n:
        out.append(
            '<text class="ax" x="%.1f" y="%d">%s</text>' % (left + gap / 2, h - 8, weeks[0]["week_ending"][5:])
        )
    if n > 1:
        out.append(
            '<text class="ax" x="%.1f" y="%d" text-anchor="end">%s</text>'
            % (left + n * slot - gap / 2, h - 8, weeks[-1]["week_ending"][5:])
        )
    out.append("</svg>")
    return "\n".join(out)


def charts(weeks):
    out = ['<div class="charts">']
    for key, title in CHARTS:
        behind = "code_q_asked" if key == "code_q_answered" else None
        out.append(bar_chart(weeks, key, title, behind))
    out.append("</div>")
    return "\n".join(out)


def columns(profile):
    cols = [
        ("Strong", bullets(get(profile, "Strong", ""))),
        ("Developing", bullets(get(profile, "Developing", ""))),
        ("Revisit", bullets(get(profile, "Revisit", ""))),
    ]
    out = ['<div class="cols">']
    for title, items in cols:
        out.append('<div class="col"><h3>' + title + ' <span class="n">' + str(len(items)) + "</span></h3>")
        out.append(ul(short(items), "nothing yet"))
        out.append("</div>")
    out.append("</div>")
    return "\n".join(out)


def table(weeks):
    head = [
        "Week",
        "Prompts",
        "Code q. asked",
        "answered",
        "sure",
        "Corrections",
        "Rejected",
        "Interrupts",
        "Don’t understand",
        "Agent runs",
        "Paid-run commands",
    ]
    keys = [
        "prompts",
        "code_q_asked",
        "code_q_answered",
        "code_q_sure",
        "corrections",
        "rejected",
        "interrupts",
        "dont_understand",
        "agent_runs",
        "paid_runs",
    ]
    out = ['<div class="tbox"><table><thead><tr>']
    for h_ in head:
        out.append("<th>" + inline(h_) + "</th>")
    out.append("</tr></thead><tbody>")
    for wk in reversed(weeks):
        overrides = wk.get("overrides") or []
        out.append("<tr><td>" + inline(wk["week_ending"]) + "</td>")
        for k in keys:
            mark = "*" if k in overrides else ""
            out.append("<td>" + fmt(num(wk, k)) + mark + "</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


# ---------------------------------------------------------------- page


def render(data_path=None):
    data_path = Path(data_path) if data_path else DATA
    profile = sections(read(PROFILE))
    progress = sections(read(PROGRESS))
    weeks = load_weeks(data_path)
    this = weeks[-1] if weeks else None
    last = weeks[-2] if len(weeks) > 1 else None

    md_weeks = week_rows(read(WEEKLY))
    judged = None
    for row in md_weeks:
        if row["interp"]:
            judged = row
            break
    if this:
        week_line = this.get("window_start", "") + " to " + this["week_ending"]
    elif md_weeks:
        week_line = "week ending " + md_weeks[0]["week"]
    else:
        week_line = "no week on record"

    p = []
    p.append("<header><h1>Weekly learning review</h1>")
    p.append('<p class="week">' + inline(week_line) + "</p>")
    p.append('<p class="sub">built from your session logs and learning files</p></header>')

    if this:
        p.append("<section>" + tiles(this, last) + "</section>")
    else:
        p.append('<section><p class="empty">No counts yet: weekly.json is missing or empty.</p></section>')

    p.append("<section><h2>This week in short</h2>")
    if judged:
        if this and judged["week"] != this["week_ending"]:
            p.append('<p class="hint">judgement from the week ending ' + inline(judged["week"]) + "</p>")
        for label, lines in judgement_blocks(judged["interp"]):
            if label:
                p.append("<h3>" + inline(label) + "</h3>")
            p.append('<p class="lines">' + "<br>".join(inline(s) for s in lines) + "</p>")
    else:
        p.append('<p class="empty">The Monday judgement is not written yet.</p>')
    p.append("</section>")

    if weeks:
        p.append("<section><h2>Over the weeks</h2>" + charts(weeks) + "</section>")

    p.append("<section><h2>How you stand</h2>" + columns(profile) + "</section>")

    now = bullets(get(profile, "Now", ""))
    needs = bullets(get(progress, "Needs reinforcement", ""))
    p.append('<section><h2>What is next</h2><div class="cols two">')
    p.append("<div class=col><h3>Now</h3>" + ul(short(now), "nothing planned") + "</div>")
    p.append("<div class=col><h3>Not good yet</h3>" + ul(short(needs), "nothing marked") + "</div>")
    p.append("</div></section>")

    p.append("<section><h2>Week by week</h2>")
    if weeks:
        p.append(table(weeks))
        p.append('<p class="hint">* hand-counted (override), not counted by the script.</p>')
    else:
        p.append('<p class="empty">no weeks in weekly.json</p>')
    p.append("</section>")

    p.append(
        "<footer>built from " + " · ".join(
            inline(str(x)) for x in (data_path, WEEKLY, PROFILE, PROGRESS)
        ) + "</footer>"
    )

    page = (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>Weekly learning review</title><style>" + CSS + "</style></head><body>"
        "<main>" + "\n".join(p) + "</main></body></html>"
    )
    PAGE.write_text(page, encoding="utf-8")
    print("page written: " + str(PAGE))


CSS = """
:root{color-scheme:light;--bg:#fcfcfb;--plane:#f9f9f7;--fg:#0b0b0b;--fg2:#52514e;--muted:#898781;
--grid:#e1e0d9;--axis:#c3c2b7;--ring:rgba(11,11,11,.10);--acc:#2a78d6;--acc-lite:#9ec5f4;--acc-back:#cde2fb;
--good:#006300;--bad:#d03b3b;--code:#f0efec}
@media(prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#1a1a19;--plane:#0d0d0d;--fg:#f0efec;--fg2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--acc:#3987e5;--acc-lite:#256abf;--acc-back:#184f95;
--good:#0ca30c;--bad:#d03b3b;--code:#2c2c2a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:820px;margin:0 auto;padding:28px 16px 48px}
header h1{font-size:1.5rem;margin:0;letter-spacing:-.01em}
.week{margin:2px 0 0;font-weight:600;color:var(--fg2)}
.sub{margin:0;color:var(--muted);font-size:.9rem}
section{margin-top:28px;padding-top:18px;border-top:1px solid var(--grid)}
h2{font-size:1.05rem;margin:0 0 12px;letter-spacing:-.01em}
h3{font-size:.85rem;margin:14px 0 4px;color:var(--fg2);text-transform:uppercase;letter-spacing:.04em}
h3:first-child{margin-top:0}
.lines{margin:0 0 6px}
p{margin:6px 0}
ul{margin:4px 0;padding-left:18px}li{margin:3px 0}
.empty{color:var(--muted);font-style:italic}.hint{color:var(--muted);font-size:.85rem}
code{background:var(--code);padding:1px 4px;border-radius:3px;font-size:.9em}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
@media(max-width:600px){.tiles{grid-template-columns:repeat(2,1fr)}}
.tile{border:1px solid var(--ring);border-radius:8px;padding:10px 12px;background:var(--bg)}
.tile .v{font-size:1.9rem;font-weight:600;line-height:1.1}
.tile .l{font-size:.8rem;color:var(--fg2);margin-top:2px}
.tile .d{font-size:.78rem;margin-top:4px;font-variant-numeric:tabular-nums}
.d.good{color:var(--good)}.d.bad{color:var(--bad)}.d.neutral{color:var(--muted)}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:14px 20px}
@media(max-width:600px){.charts{grid-template-columns:1fr}}
.chart{width:100%;height:auto;display:block;font-family:inherit}
.chart text{fill:var(--fg2);font-size:11px}
.chart .t{fill:var(--fg);font-size:12px;font-weight:600}
.chart .val{fill:var(--fg);font-size:11px;font-weight:600;font-variant-numeric:tabular-nums}
.chart .ax{fill:var(--muted);font-size:10px;font-variant-numeric:tabular-nums}
.chart .axis{stroke:var(--axis);stroke-width:1}
.chart .cur{fill:var(--acc)}.chart .prev{fill:var(--acc-lite)}.chart .back{fill:var(--acc-back)}
.chart path:hover{opacity:.8}
.cols{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.cols.two{grid-template-columns:1fr 1fr}
@media(max-width:600px){.cols,.cols.two{grid-template-columns:1fr}}
.col h3 .n{color:var(--acc);margin-left:4px}
.col li{font-size:.92rem}
.tbox{overflow-x:auto;border:1px solid var(--ring);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:.85rem;white-space:nowrap}
th,td{text-align:right;padding:6px 10px;border-bottom:1px solid var(--grid);font-variant-numeric:tabular-nums}
th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-weight:500;background:var(--plane)}
tbody tr:last-child td{border-bottom:0}
footer{margin-top:36px;color:var(--muted);font-size:.75rem;word-break:break-all}
"""


if __name__ == "__main__":
    args = sys.argv[1:]
    path = None
    if "--data" in args:
        i = args.index("--data")
        if i + 1 < len(args):
            path = args[i + 1]
    render(path)
