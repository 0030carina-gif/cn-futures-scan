#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a comfortable, self-contained HTML reading page from a scan memo."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/tmp/mdenv/lib/python3.13/site-packages")
import markdown

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "scans" / "2026-11-09.md"
OUT = ROOT / "index.html"
OUT_DATED = ROOT / "scans" / "2026-11-09.html"

CSS = r"""
:root {
  --bg: #efe8db;
  --paper: #fbf7f0;
  --ink: #1c1915;
  --muted: #6e675c;
  --faint: #948c80;
  --line: #e5ddcf;
  --accent: #8d3a2b;
  --accent-soft: #f4e6e0;
  --up: #c0392b;
  --down: #1e7a52;
  --card: #fffdf8;
  --soft: #f3eee4;
  --shadow: 0 1px 2px rgba(40,30,16,.04), 0 10px 28px rgba(40,30,16,.06);
  --sans: "Source Han Sans SC", "Noto Sans SC", "PingFang SC", "Hiragino Sans GB",
          "Microsoft YaHei", "Heiti SC", system-ui, sans-serif;
  --serif: "Source Han Serif SC", "Noto Serif SC", "Songti SC", "STSong",
           "SimSun", Georgia, serif;
  --mono: "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace;
  color-scheme: light;
}
html[data-theme="dark"] {
  --bg: #141210;
  --paper: #1c1916;
  --ink: #f0e9de;
  --muted: #b0a79b;
  --faint: #8a8277;
  --line: #3a342c;
  --accent: #e08a7a;
  --accent-soft: #3a2723;
  --up: #e06b62;
  --down: #5dcaa0;
  --card: #221e1a;
  --soft: #2a251f;
  --shadow: 0 1px 2px rgba(0,0,0,.25), 0 10px 28px rgba(0,0,0,.28);
  color-scheme: dark;
}
@media (prefers-color-scheme: dark) {
  html:not([data-theme="light"]) {
    --bg: #141210;
    --paper: #1c1916;
    --ink: #f0e9de;
    --muted: #b0a79b;
    --faint: #8a8277;
    --line: #3a342c;
    --accent: #e08a7a;
    --accent-soft: #3a2723;
    --up: #e06b62;
    --down: #5dcaa0;
    --card: #221e1a;
    --soft: #2a251f;
    --shadow: 0 1px 2px rgba(0,0,0,.25), 0 10px 28px rgba(0,0,0,.28);
    color-scheme: dark;
  }
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
html, body { margin: 0; padding: 0; }
body {
  background:
    radial-gradient(1200px 500px at 10% -10%, rgba(141,58,43,.06), transparent 50%),
    var(--bg);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 17px;
  line-height: 1.85;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 22px;
  background: color-mix(in srgb, var(--bg) 86%, transparent);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--line);
}
.brand {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}
.brand .mark {
  color: var(--accent);
  font-size: 12px;
  letter-spacing: .16em;
  font-weight: 600;
  white-space: nowrap;
}
.brand .when {
  color: var(--muted);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tools { display: flex; gap: 8px; flex-shrink: 0; }
.tools button, .toc-toggle {
  appearance: none;
  border: 1px solid var(--line);
  background: var(--card);
  color: var(--ink);
  font: inherit;
  font-size: 13px;
  padding: 6px 10px;
  border-radius: 999px;
  cursor: pointer;
}
.tools button:hover, .toc-toggle:hover { border-color: var(--accent); color: var(--accent); }
.toc-toggle { display: none; }

.wrap {
  display: grid;
  grid-template-columns: 220px minmax(0, 760px);
  gap: 48px;
  max-width: 1120px;
  margin: 0 auto;
  padding: 36px 28px 96px;
}

nav.toc {
  position: sticky;
  top: 68px;
  align-self: start;
  max-height: calc(100vh - 88px);
  overflow: auto;
  padding-right: 8px;
}
nav.toc h2 {
  margin: 0 0 12px;
  font-size: 11px;
  letter-spacing: .18em;
  color: var(--faint);
  font-weight: 600;
  font-family: var(--sans);
}
nav.toc ol { list-style: none; margin: 0; padding: 0; }
nav.toc li { margin: 0; }

nav.toc a {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  color: var(--muted);
  text-decoration: none;
  font-size: 13px;
  line-height: 1.45;
  padding: 6px 0 6px 10px;
  border-left: 2px solid transparent;
}
nav.toc a .t { flex: 1; min-width: 0; }
nav.toc a:hover { color: var(--ink); }
nav.toc a.active {
  color: var(--accent);
  border-left-color: var(--accent);
  font-weight: 600;
}
nav.toc .l3 { padding-left: 22px; font-size: 12px; }
nav.toc .legend {
  margin: 0 0 14px;
  color: var(--faint);
  font-size: 12px;
  line-height: 1.55;
  font-weight: 400;
  letter-spacing: 0;
}
.bias {
  flex-shrink: 0;
  display: inline-block;
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 700;
  line-height: 1.5;
  padding: 0 6px;
  border-radius: 4px;
  letter-spacing: .12em;
  vertical-align: middle;
  margin-left: 6px;
}
.bias.long { color: #c0392b; background: rgba(192, 57, 43, .12); }
.bias.short { color: #1e7a52; background: rgba(30, 122, 82, .14); }
.bias.neutral { color: #6f675d; background: rgba(111, 103, 93, .12); }
html[data-theme="dark"] .bias.long,
html:not([data-theme="light"]) .bias.long { color: #e06b62; background: rgba(224, 107, 98, .18); }
html[data-theme="dark"] .bias.short,
html:not([data-theme="light"]) .bias.short { color: #5dcaa0; background: rgba(93, 202, 160, .16); }
html[data-theme="dark"] .bias.neutral,
html:not([data-theme="light"]) .bias.neutral { color: #b0a79b; background: rgba(176, 167, 155, .16); }
@media (prefers-color-scheme: light) {
  html:not([data-theme="dark"]) .bias.long { color: #c0392b; background: rgba(192, 57, 43, .12); }
  html:not([data-theme="dark"]) .bias.short { color: #1e7a52; background: rgba(30, 122, 82, .14); }
  html:not([data-theme="dark"]) .bias.neutral { color: #6f675d; background: rgba(111, 103, 93, .12); }
}

article header.hero {
  padding: 8px 0 28px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 8px;
}
.kicker {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 12px;
  letter-spacing: .2em;
  font-weight: 600;
}
h1.title {
  font-family: var(--serif);
  font-weight: 650;
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.22;
  letter-spacing: .02em;
  margin: 0 0 10px;
}
.lede {
  margin: 0 0 18px;
  color: var(--muted);
  font-size: 15px;
}
.pills { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 18px; }
.pill {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 13px;
  color: var(--ink);
}
.pill em { font-style: normal; color: var(--muted); margin-right: 6px; }
.pill.down { color: var(--down); }
.pill.up { color: var(--up); }

.meta-grid {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 6px 14px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px 18px;
  font-size: 13.5px;
  line-height: 1.65;
  box-shadow: var(--shadow);
}
.meta-grid dt { color: var(--faint); margin: 0; }
.meta-grid dd { margin: 0; color: var(--ink); }

article h2 {
  font-family: var(--serif);
  font-size: 24px;
  font-weight: 650;
  letter-spacing: .03em;
  margin: 52px 0 16px;
  padding-top: 8px;
  scroll-margin-top: 76px;
}
article h2 .num {
  color: var(--accent);
  font-size: .78em;
  margin-right: .35em;
}
article h3 {
  font-size: 18px;
  font-weight: 650;
  margin: 32px 0 10px;
  scroll-margin-top: 76px;
}
article h4 {
  font-size: 16px;
  font-weight: 650;
  margin: 22px 0 8px;
  color: var(--ink);
  scroll-margin-top: 76px;
}

article p { margin: 0 0 12px; }
article li { margin: 0 0 6px; }
article ul, article ol { padding-left: 1.25em; margin: 0 0 14px; }
article strong { font-weight: 650; }

article hr {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 28px 0;
}

.section-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 22px 26px 8px;
  margin: 20px 0 28px;
  box-shadow: var(--shadow);
}
.section-card > h3:first-child,
.section-card > h4:first-child { margin-top: 0; }

h3.sub, h4.sub {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  letter-spacing: .06em;
  margin: 26px 0 10px;
}
h3.sub::before, h4.sub::before {
  content: "";
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}
h3.sub.fund::before, h4.sub.fund::before { background: var(--accent); }
h3.sub.logic::before, h4.sub.logic::before { background: #b8860b; }
h3.sub.tech::before, h4.sub.tech::before { background: #2c6e6a; }
html[data-theme="dark"] h3.sub.logic::before,
html[data-theme="dark"] h4.sub.logic::before { background: #e0c170; }
html[data-theme="dark"] h3.sub.tech::before,
html[data-theme="dark"] h4.sub.tech::before { background: #7ec9c3; }

.table-wrap { overflow-x: auto; margin: 0 0 16px; }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  line-height: 1.55;
  min-width: 560px;
}
th, td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}
th {
  color: var(--muted);
  font-weight: 600;
  font-size: 12px;
  letter-spacing: .06em;
  background: var(--soft);
}
tr:last-child td { border-bottom: 0; }

.note, .disclaimer {
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.7;
}
footer.disclaimer {
  margin-top: 56px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
}

.hero, article, .meta-grid, .pills, .section-card { min-width: 0; max-width: 100%; }
.meta-grid dd { overflow-wrap: anywhere; word-break: break-word; }
.pills { max-width: 100%; }
.pill { max-width: 100%; white-space: normal; overflow-wrap: anywhere; }

@media (max-width: 960px) {
  .wrap { grid-template-columns: 1fr; gap: 0; padding: 20px 18px 72px; }
  .meta-grid {
    grid-template-columns: 1fr;
    gap: 2px 0;
  }
  .meta-grid dt { margin-top: 8px; }
  .meta-grid dt:first-child { margin-top: 0; }
  nav.toc {
    display: none;
    position: fixed;
    top: 52px;
    left: 12px;
    right: 12px;
    z-index: 30;
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 16px 16px 20px;
    max-height: calc(100vh - 80px);
    box-shadow: var(--shadow);
  }
  nav.toc.open { display: block; }
  .toc-toggle { display: inline-flex; }
  .section-card { padding: 16px 16px 4px; }
  article h2 { font-size: 22px; margin-top: 36px; }
}

@media print {
  .topbar, nav.toc, .tools, .toc-toggle { display: none !important; }
  body { background: #fff; }
  .wrap { display: block; padding: 0; }
  .section-card { box-shadow: none; break-inside: avoid; }
}

.season-chart {
  margin: 16px 0 22px;
  padding: 10px 10px 6px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: var(--shadow);
  overflow: hidden;
  max-width: 100%;
}
.season-chart svg.season-svg,
.season-chart svg {
  display: block;
  width: 100%;
  height: auto;
  max-width: 100%;
}
.season-chart figcaption {
  margin: 4px 6px 8px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.55;
}
.season-chart-group {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin: 14px 0 22px;
}
.season-svg {
  --chart-bg: #fbf7f0;
  --chart-ink: #1c1915;
  --chart-muted: #6e675c;
  --chart-grid: #e5ddcf;
}
html[data-theme="dark"] .season-svg {
  --chart-bg: #221e1a;
  --chart-ink: #f0e9de;
  --chart-muted: #b0a79b;
  --chart-grid: #3a342c;
}
@media (prefers-color-scheme: dark) {
  html:not([data-theme="light"]) .season-svg {
    --chart-bg: #221e1a;
    --chart-ink: #f0e9de;
    --chart-muted: #b0a79b;
    --chart-grid: #3a342c;
  }
}
"""

JS = r"""
(function () {
  const root = document.documentElement;
  const saved = localStorage.getItem("scan-theme");
  if (saved) root.setAttribute("data-theme", saved);

  const themeBtn = document.getElementById("theme-toggle");
  const tocBtn = document.getElementById("toc-toggle");
  const toc = document.getElementById("toc");

  function labelTheme() {
    const dark = isDark();
    themeBtn.textContent = dark ? "浅色" : "深色";
  }
  function isDark() {
    if (root.getAttribute("data-theme") === "dark") return true;
    if (root.getAttribute("data-theme") === "light") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  themeBtn.addEventListener("click", function () {
    const next = isDark() ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("scan-theme", next);
    labelTheme();
  });
  labelTheme();

  tocBtn.addEventListener("click", function () {
    toc.classList.toggle("open");
  });
  toc.querySelectorAll("a").forEach(function (a) {
    a.addEventListener("click", function () { toc.classList.remove("open"); });
  });

  const links = Array.from(toc.querySelectorAll("a[href^='#']"));
  const map = links.map(function (a) {
    const id = decodeURIComponent(a.getAttribute("href").slice(1));
    return { a: a, el: document.getElementById(id) };
  }).filter(function (x) { return x.el; });

  function sync() {
    let current = map[0];
    const y = window.scrollY + 90;
    map.forEach(function (item) {
      if (item.el.offsetTop <= y) current = item;
    });
    links.forEach(function (a) { a.classList.remove("active"); });
    if (current) current.a.classList.add("active");
  }
  document.addEventListener("scroll", sync, { passive: true });
  sync();
})();
"""



SKIP_BIAS = (
    "市场总览",
    "夜盘",
    "后续关注",
    "数据缺口",
    "主要来源",
    "基本面",
    "分析逻辑",
    "技术面",
)


def load_bias_items(date: str) -> list[dict]:
    path = ROOT / "scans" / f"{date}-bias.json"
    if not path.exists():
        path = ROOT / "scans" / "bias.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("items", data if isinstance(data, list) else [])


def should_label(text: str) -> bool:
    return not any(s in text for s in SKIP_BIAS)


def find_bias(text: str, items: list[dict]) -> dict | None:
    hits = [it for it in items if (it.get("match") or "") and it["match"] in text]
    if not hits:
        return None
    return max(hits, key=lambda it: len(it["match"]))


def badge_html(bias: str, reason: str = "") -> str:
    cls = {"多": "long", "空": "short", "中性": "neutral"}.get(bias)
    if not cls:
        return ""
    title = f' title="{reason}"' if reason else ""
    return f'<span class="bias {cls}"{title}>{bias}</span>'


def apply_bias(html: str, toc: list[dict], items: list[dict]) -> tuple[str, list[dict]]:
    for item in toc:
        hit = find_bias(item["text"], items) if should_label(item["text"]) else None
        item["bias"] = hit.get("bias") if hit else None
        item["reason"] = hit.get("reason") if hit else ""
        if not item["bias"]:
            continue
        badge = badge_html(item["bias"], item["reason"])
        hid = re.escape(item["id"])
        html = re.sub(
            rf'(<h{item["level"]}\b[^>]*\sid="{hid}"[^>]*>)(.*?)(</h{item["level"]}>)',
            rf"\1\2 {badge}\3",
            html,
            count=1,
            flags=re.S,
        )
    return html, toc


def slugify(text: str, used: dict) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("｜", "-").replace("|", "-")
    base = text or "section"
    n = used.get(base, 0)
    used[base] = n + 1
    return base if n == 0 else f"{base}-{n+1}"


def add_heading_ids(html: str) -> tuple[str, list[dict]]:
    used: dict[str, int] = {}
    toc: list[dict] = []

    def repl(m):
        level = int(m.group(1))
        attrs = m.group(2) or ""
        inner = m.group(3)
        if re.search(r'\sid="', attrs):
            hid = re.search(r'\sid="([^"]+)"', attrs).group(1)
        else:
            hid = slugify(inner, used)
            attrs = f'{attrs} id="{hid}"'
        toc.append({"level": level, "id": hid, "text": re.sub(r"<[^>]+>", "", inner)})
        return f"<h{level}{attrs}>{inner}</h{level}>"

    html = re.sub(r"<h([2-4])([^>]*)>(.*?)</h\1>", repl, html, flags=re.S)
    return html, toc


def classify_subs(html: str) -> str:
    def repl(m):
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        classes = []
        if "基本面" in inner:
            classes.append("sub fund")
        elif "分析逻辑" in inner or inner.strip().startswith("逻辑") or "逻辑" == re.sub(r"<[^>]+>", "", inner)[-2:]:
            classes.append("sub logic")
        elif "技术面" in inner:
            classes.append("sub tech")
        if classes:
            if re.search(r'class="', attrs):
                attrs = re.sub(r'class="([^"]*)"', lambda x: f'class="{x.group(1)} {classes[0]}"', attrs)
            else:
                attrs += f' class="{classes[0]}"'
        return f"<h{tag}{attrs}>{inner}</h{tag}>"

    return re.sub(r"<h([34])([^>]*)>(.*?)</h\1>", repl, html, flags=re.S)


def wrap_tables(html: str) -> str:
    return re.sub(r"(<table>.*?</table>)", r'<div class="table-wrap">\1</div>', html, flags=re.S)


def wrap_major_subsections(html: str) -> str:
    """Wrap h3 blocks that look like contract subsections (e.g. 3.1 原油) in cards.
    Do not wrap the top-level 基本面/逻辑/技术面 under a variety, those stay inline.
    """
    parts = re.split(r"(<h3\b[^>]*>.*?</h3>)", html, flags=re.S)
    out = [parts[0]]
    i = 1
    while i < len(parts):
        heading = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        text = re.sub(r"<[^>]+>", "", heading)
        is_contract = bool(re.match(r"\s*\d+\.\d+", text)) or ("简要" in text and "铝" in text)
        is_subhead = any(k in text for k in ("基本面", "分析逻辑", "技术面"))
        if is_contract and not is_subhead:
            # body until next h3 already split; split off following h2
            pre, mid, post = body, "", ""
            m = re.search(r"<h2\b", body)
            if m:
                mid, post = body[: m.start()], body[m.start() :]
                pre = mid
            out.append(f'<div class="section-card">\n{heading}\n{pre}</div>\n{post}')
        else:
            out.append(heading + body)
        i += 2
    return "".join(out)


def parse_front(md: str) -> tuple[dict, str]:
    lines = md.splitlines()
    meta = {"title": "期货全市场扫描", "subtitle": "", "fields": []}
    i = 0
    if lines and lines[0].startswith("# "):
        meta["title"] = lines[0][2:].strip()
        i = 1
    if i < len(lines) and lines[i].startswith("## "):
        meta["subtitle"] = lines[i][3:].strip()
        i += 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == "---":
            i += 1
            break
        m = re.match(r"\*\*(.+?)\*\*：\s*(.*)", line)
        if m:
            val = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", m.group(2))
            meta["fields"].append((m.group(1), val))
            i += 1
            continue
        break
    # drop trailing file-path footnote
    rest = "\n".join(lines[i:])
    rest = re.sub(r"\n---\s*\n\s*\*本文件路径：.*$", "\n", rest)
    return meta, rest


def toc_html(toc: list[dict]) -> str:
    items = []
    for item in toc:
        if item["level"] > 3:
            continue
        cls = "l3" if item["level"] == 3 else "l2"
        badge = badge_html(item.get("bias") or "", item.get("reason") or "")
        items.append(
            f'<li><a class="{cls}" href="#{item["id"]}"><span class="t">{item["text"]}</span>{badge}</a></li>'
        )
    legend = (
        '<p class="legend">'
        "依据基本面，不单看当日涨跌："
        '<span class="bias long">多</span> 红 · '
        '<span class="bias short">空</span> 绿，交织标 '
        '<span class="bias neutral">中性</span></p>'
    )
    return legend + "\n<ol>\n" + "\n".join(items) + "\n</ol>"


CHART_DIR = ROOT / "scans" / "charts"

# Where to inject each symbol's seasonal chart in the HTML body.
# Keys are substrings of the heading text (h2/h3); value is list of symbol codes.
# (heading_substring, codes, prefer_anchor_regexes)
# Anchor regexes are searched inside the section; chart is inserted after the first match.
CHART_PLACEMENTS = [
    ("二、碳酸锂", ["LC"], [r"交易所仓单[\s\S]{0,400}?</p>", r"<p><strong>库存[\s\S]*?</p>"]),
    ("3.1 原油", ["SC"], [r"仓单约[\s\S]{0,80}?</p>", r"仓单[\s\S]{0,120}?</p>"]),
    ("3.2 燃料油", ["FU"], [r"该口径作废[\s\S]{0,40}?</p>", r"燃油仓单[\s\S]{0,200}?</p>"]),
    ("3.3 LPG", ["PG"], [r"仓单约[\s\S]{0,80}?</p>", r"仓单[\s\S]{0,80}?</p>"]),
    ("3.4 苯乙烯", ["EB"], [r"工厂库存[\s\S]{0,80}?</p>", r"库存：[\s\S]{0,200}?</p>"]),
    ("3.5 沥青", ["BU"], [r"厂库仓单[\s\S]{0,120}?</p>", r"仓单（金十[\s\S]{0,300}?</p>"]),
    ("3.6 甲醇", ["MA", "TA", "EG", "V"], [r"</table></div>", r"</table>"]),
    ("4.1 铜", ["CU"], [r"金十日讯 2844[\s\S]{0,120}?</p>", r"<p><strong>仓单[\s\S]*?</p>"]),
    ("4.2 铝", ["AL"], [r"仓单金十[\s\S]{0,200}?</p>", r"社库约[\s\S]{0,200}?</p>"]),
    ("5.1 焦煤", ["JM"], [r"交易所仓单[\s\S]{0,80}?</p>", r"<p><strong>库存[\s\S]*?</p>"]),
    ("5.2 螺纹", ["RB"], [r"仓单同花顺[\s\S]{0,120}?</p>", r"仓单[\s\S]{0,80}?</p>"]),
    ("5.3 热卷", ["HC"], [r"仓单约[\s\S]{0,80}?</p>", r"社库[\s\S]{0,120}?</p>"]),
    ("5.4 铁矿", ["I"], [r"港口累库[\s\S]{0,80}?</p>", r"库存：47[\s\S]{0,200}?</p>"]),
    ("5.5 焦炭", ["J"], [r"焦炭库存[\s\S]{0,120}?</p>", r"全样本焦炭库存[\s\S]{0,120}?</p>"]),
    ("六、生猪", ["LH"], [r"冻品库容[\s\S]{0,200}?</p>", r"<p><strong>需求[\s\S]*?</p>"]),
    ("7.1 棕榈油", ["P"], [r"作废。?</p>", r"棕榈油仓单[\s\S]{0,160}?</p>"]),
    ("7.2 豆油", ["Y"], [r"跌幅受限。[\s\S]{0,80}?</p>", r"收储[\s\S]{0,200}?</p>"]),
]


def load_chart_fragment(code: str) -> str:
    path = CHART_DIR / f"{code}_season.html"
    if not path.exists():
        note_path = CHART_DIR / f"{code}_skip.html"
        if note_path.exists():
            return note_path.read_text(encoding="utf-8")
        return ""
    return path.read_text(encoding="utf-8")


def _chart_block(codes: list[str]) -> str:
    frags = [load_chart_fragment(c) for c in codes]
    frags = [f for f in frags if f]
    if not frags:
        return ""
    if len(frags) == 1:
        return "\n" + frags[0]
    return '\n<div class="season-chart-group">\n' + "\n".join(frags) + "\n</div>\n"


def inject_season_charts(html: str) -> str:
    """Insert seasonal charts after inventory/receipt discussion inside each variety section."""
    used: set[str] = set()
    # Work on full HTML with look-ahead: find heading, then search forward until next same-or-higher heading
    for key, codes, anchors in CHART_PLACEMENTS:
        codes = [c for c in codes if c not in used]
        if not codes:
            continue
        hm = re.search(
            rf"<h([23])\b[^>]*>[^<]*{re.escape(key)}.*?</h\1>",
            html,
            flags=re.S,
        )
        if not hm:
            continue
        level = int(hm.group(1))
        sec_start = hm.end()
        # end at next h2, or next h3 if current is h3
        if level == 2:
            end_m = re.search(r"<h2\b", html[sec_start:])
        else:
            end_m = re.search(r"<h[23]\b", html[sec_start:])
        sec_end = sec_start + end_m.start() if end_m else len(html)
        section = html[sec_start:sec_end]
        block = _chart_block(codes)
        if not block:
            for c in codes:
                used.add(c)
            continue
        insert_at = None
        for pat in anchors:
            m = re.search(pat, section)
            if m:
                insert_at = m.end()
                break
        if insert_at is None:
            insert_at = 0
        section = section[:insert_at] + block + section[insert_at:]
        html = html[:sec_start] + section + html[sec_end:]
        for c in codes:
            used.add(c)
    return html



def build() -> Path:
    raw = SRC.read_text(encoding="utf-8")
    meta, body_md = parse_front(raw)
    conv = markdown.Markdown(extensions=["tables", "sane_lists", "nl2br"])
    body = conv.convert(body_md)
    body, toc = add_heading_ids(body)
    body = classify_subs(body)
    date = SRC.stem.replace("-bias", "")
    if date.startswith("scan-"):
        date = date[len("scan-"):]
    # SRC is like scans/2026-11-09.md
    date = SRC.stem
    bias_items = load_bias_items(date)
    body, toc = apply_bias(body, toc, bias_items)
    body = wrap_tables(body)
    body = wrap_major_subsections(body)
    body = inject_season_charts(body)

    fields = "".join(
        f"<dt>{k}</dt><dd>{v}</dd>" for k, v in meta["fields"] if k != "声明"
    )
    disclaimer = next((v for k, v in meta["fields"] if k == "声明"), "公开信息整理，非投资建议。")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>期货全市场扫描 · 2026-11-09</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="topbar">
    <div class="brand">
      <span class="mark">期货全市场扫描</span>
      <span class="when">2026-11-09 周一 · 日盘 + 夜盘补记</span>
    </div>
    <div class="tools">
      <button class="toc-toggle" id="toc-toggle" type="button">目录</button>
      <button id="theme-toggle" type="button">深色</button>
    </div>
  </div>
  <div class="wrap">
    <nav class="toc" id="toc">
      <h2>目录</h2>
      {toc_html(toc)}
    </nav>
    <article>
      <header class="hero">
        <p class="kicker">中国商品期货每日扫描</p>
        <h1 class="title">2026年11月9日</h1>
        <p class="lede">中国商品期货重点品种深度扫描（投研备忘）· 北京时间</p>
        <div class="pills">
          <span class="pill down"><em>涨跌宽度</em>16 涨 / 43 跌</span>
          <span class="pill down"><em>商品指数</em>1556.66（-0.25%）</span>
          <span class="pill down"><em>碳酸锂</em>-4.85%</span>
          <span class="pill down"><em>夜盘燃油</em>跌超 6%</span>
          <span class="pill up"><em>生猪</em>+1.91%</span>
        </div>
        <dl class="meta-grid">{fields}</dl>
      </header>
      {body}
      <footer class="disclaimer">
        <p>{disclaimer} 仓单以上期所金十日讯、同花顺快讯为准；奇货可查与之冲突的燃油、棕榈油仓单口径已作废。技术面均线若标注来自第三方午盘估算，则以收盘后终端为准。</p>
      </footer>
    </article>
  </div>
  <script>{JS}</script>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT_DATED.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    OUT_DATED.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    print(f"wrote {OUT_DATED}")
    return OUT


if __name__ == "__main__":
    build()
