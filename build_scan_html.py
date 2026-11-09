#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a comfortable, self-contained HTML reading page from a scan memo."""

from __future__ import annotations

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
  display: block;
  color: var(--muted);
  text-decoration: none;
  font-size: 13px;
  line-height: 1.45;
  padding: 6px 0 6px 10px;
  border-left: 2px solid transparent;
}
nav.toc a:hover { color: var(--ink); }
nav.toc a.active {
  color: var(--accent);
  border-left-color: var(--accent);
  font-weight: 600;
}
nav.toc .l3 { padding-left: 22px; font-size: 12px; }

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
        items.append(
            f'<li><a class="{cls}" href="#{item["id"]}">{item["text"]}</a></li>'
        )
    return "<ol>\n" + "\n".join(items) + "\n</ol>"


def build() -> Path:
    raw = SRC.read_text(encoding="utf-8")
    meta, body_md = parse_front(raw)
    conv = markdown.Markdown(extensions=["tables", "sane_lists", "nl2br"])
    body = conv.convert(body_md)
    body, toc = add_heading_ids(body)
    body = classify_subs(body)
    body = wrap_tables(body)
    body = wrap_major_subsections(body)

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
