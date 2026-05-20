#!/usr/bin/env python3
"""Generate a report from a GitHub URL.

Two modes:

  full (default)   — fetch README + repo meta, invoke `claude -p` to fill
                     the 5-段式 sections from the README, emit a complete
                     report ready for `merge.py`.

  --no-llm         — scaffold only: same meta + README excerpt, TODO
                     placeholders in the 5 sections. Use when offline or
                     when you want to hand-write content.

Examples:
    python3 tools/generate.py https://github.com/owner/repo
    python3 tools/generate.py https://github.com/owner/repo --order 9
    python3 tools/generate.py https://github.com/owner/repo --no-llm
    python3 tools/generate.py https://github.com/owner/repo --overwrite --draft

After generate, run:
    python3 tools/merge.py --lint     # verify quality gate
    python3 tools/merge.py            # register in index.html
    bash tools/ship.sh                # push
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import REPORTS_DIR, attr, inject_seo, seo_block_report  # noqa: E402

GH_URL_RE = re.compile(r"https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")

THEME_PALETTE = [
    "theme-feishu", "theme-warp", "theme-planning", "theme-reach",
    "theme-playwright", "theme-ruview", "theme-mattpocock", "theme-ralph",
]

GLYPH_BY_TOPIC = {
    "办公自动化": "chat",
    "感知硬件": "wifi",
    "终端工具": "terminal",
    "AI Agent": "loop",
    "MCP": "browser",
    "浏览器自动化": "browser",
    "长任务记忆": "file",
    "互联网工具": "globe",
    "工程实践": "skill",
    "代码理解": "file",
    "知识图谱": "file",
}


# ─────────────── network ───────────────

def http_get(url: str, accept: str = "application/json") -> str | None:
    req = urllib.request.Request(
        url, headers={"User-Agent": "research-hub-generate/1.0", "Accept": accept}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        print(f"  ! network error fetching {url}: {e}", file=sys.stderr)
        return None


def parse_url(url: str) -> tuple[str, str]:
    m = GH_URL_RE.match(url.strip())
    if not m:
        raise SystemExit(f"ERROR: not a recognizable GitHub URL: {url}")
    return m.group(1), m.group(2)


def fetch_repo_meta(owner: str, repo: str) -> dict:
    """Best-effort. Returns {} if api.github.com is unreachable."""
    raw = http_get(f"https://api.github.com/repos/{owner}/{repo}")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def fetch_readme(owner: str, repo: str, branch_candidates: tuple[str, ...]) -> tuple[str, str]:
    """Try common README filenames across given branches. Returns (text, branch_used)."""
    names = ("README.md", "README.zh.md", "Readme.md", "readme.md")
    for branch in branch_candidates:
        for name in names:
            txt = http_get(
                f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{name}",
                accept="text/plain",
            )
            if txt:
                return txt, branch
    return "", branch_candidates[0]


# ─────────────── derivations ───────────────

def derive_topic(text: str, topics: list[str]) -> str:
    hints = " ".join((text or "").lower().split()[:200] + [t.lower() for t in topics])
    table = [
        ("graph|index|symbol|knowledge", "代码理解"),
        ("cli|terminal|shell", "终端工具"),
        ("agent|autonom|loop", "AI Agent"),
        ("mcp|model[- ]context", "MCP"),
        ("browser|playwright|puppeteer|selenium", "浏览器自动化"),
        ("wifi|csi|rssi|esp32|sensing", "感知硬件"),
        ("plan|memory|context window", "长任务记忆"),
        ("crawl|scrape|fetch|internet", "互联网工具"),
        ("skill|workflow|tdd|engineer", "工程实践"),
        ("feishu|lark|slack|messag", "办公自动化"),
    ]
    for pat, label in table:
        if re.search(pat, hints):
            return label
    return "工具"


def derive_theme(slug: str) -> str:
    return THEME_PALETTE[sum(ord(c) for c in slug) % len(THEME_PALETTE)]


def derive_glyph(topic: str) -> str:
    return GLYPH_BY_TOPIC.get(topic, "tool")


def derive_cover(owner: str, repo: str) -> str:
    return f"https://opengraph.githubassets.com/research-hub/{owner}/{repo}"


# ─────────────── LLM ───────────────

LLM_PROMPT = """阅读以下 GitHub 项目的 README，输出**严格的 JSON 对象**（不要带任何 markdown 围栏、不要 preamble），key 见下：

{{
  "title": "中文为主、可含原名的标题，≤32 字，例: 'CodeGraph · 本地代码知识图谱'",
  "topic": "1-4 字主题胶囊，例: '代码理解' '工程实践' 'AI Agent'",
  "summary": "1-2 句卡片描述，≤100 字，突出核心价值和差异化",
  "pills": "'标签|颜色' 用分号串联；颜色限 blue|green|amber|rose|violet|teal；2-3 个；例: 'Local-first|green;LSP|blue;Beta|amber'",
  "baseline": "推荐基线：什么场景下用此工具最划算（1-2 句）",
  "alternatives": "补充场景或替代方案：何时不用 / 何时配合使用（1-2 句）",
  "capabilities": [
    {{"name": "能力短名", "desc": "1 句话描述（≤60 字）"}}
  ],
  "applications": [
    {{"name": "场景短名", "desc": "1 句话描述（≤60 字）"}}
  ],
  "risks": [
    {{"severity": "risk|warn", "title": "风险标题", "desc": "1-2 句描述 + 缓解措施"}}
  ],
  "extra_sources": [
    {{"title": "标题", "url": "https://...", "note": "短注释"}}
  ],
  "matrix_subject": "主题表第 1 列：分类标签",
  "matrix_question": "主题表第 3 列：1 句话核心问题",
  "matrix_risk": "主题表第 4 列：优先关注的风险（逗号分隔）"
}}

要求：
- capabilities/applications 各 3-5 项；risks 2-4 项；extra_sources 0-3 项（仅当 README 中有官网/文档/release 等额外链接时）
- 内容要具体、可验证，不要泛泛而谈
- pills 要反映**真实**特点（例如 Local-first、Open-source、Beta、Heavy deps 等）

GitHub 元数据（部分可能为空）：
- owner/repo: {owner}/{repo}
- description: {description}
- topics: {topics}
- language: {language}
- license: {license}
- stars: {stars}

README（节选，最多 12000 字符）：
---
{readme}
---

输出 JSON："""


def find_claude_bin(override: str | None) -> str | None:
    if override:
        return override if shutil.which(override) else None
    return shutil.which("claude")


def call_llm(claude_bin: str, prompt: str, timeout: int = 180) -> dict | None:
    print(f"  → invoking {claude_bin} -p (timeout {timeout}s)…")
    try:
        proc = subprocess.run(
            [claude_bin, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print("  ! LLM call timed out", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(f"  ! claude binary not found: {claude_bin}", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(f"  ! claude exited {proc.returncode}: {proc.stderr[:300]}", file=sys.stderr)
        return None
    out = proc.stdout.strip()
    # Strip optional ```json fences
    out = re.sub(r"^```(?:json)?\s*", "", out)
    out = re.sub(r"\s*```$", "", out)
    # Find first { ... } block
    start = out.find("{")
    end = out.rfind("}")
    if start < 0 or end <= start:
        print("  ! could not locate JSON in LLM output", file=sys.stderr)
        return None
    try:
        data = json.loads(out[start : end + 1])
    except json.JSONDecodeError as e:
        print(f"  ! JSON parse failed: {e}", file=sys.stderr)
        print(f"    raw output: {out[:400]}", file=sys.stderr)
        return None
    return data


# ─────────────── rendering ───────────────

def render_meta_block(meta: dict) -> str:
    return "\n".join(f'  <meta name="hub:{k}" content="{attr(v)}">' for k, v in meta.items())


def render_callout(severity: str, title: str, desc: str) -> str:
    cls = "risk" if severity == "risk" else "warn"
    return f'''          <div class="callout {cls}">
            <h3>{attr(title)}</h3>
            <p>{attr(desc)}</p>
          </div>'''


def render_cards_grid(items: list[dict], cols: str = "three") -> str:
    if not items:
        return '          <p class="muted">（待补）</p>'
    cards = "\n".join(
        f'''          <article class="card">
            <h3>{attr(it["name"])}</h3>
            <p>{attr(it["desc"])}</p>
          </article>''' for it in items
    )
    return f'<div class="grid {cols}">\n{cards}\n        </div>'


def render_sources(repo_url: str, branch: str, homepage: str, extras: list[dict]) -> str:
    items = [
        ("GitHub 仓库", repo_url, repo_url.split("github.com/", 1)[-1]),
        (f"README ({branch})", f"{repo_url}/blob/{branch}/README.md", "源文档"),
        ("Releases", f"{repo_url}/releases", "历史版本"),
    ]
    if homepage:
        items.append(("官网", homepage, "homepage"))
    for ex in extras or []:
        if ex.get("url"):
            items.append((ex.get("title") or "extra", ex["url"], ex.get("note") or ""))
    out = []
    for title, url, note in items:
        out.append(
            f'          <a class="source-link" href="{attr(url)}">{attr(title)}<span>{attr(note)}</span></a>'
        )
    return "\n".join(out)


def render_filled(
    slug: str, owner: str, repo: str, repo_meta: dict, llm: dict,
    cover: str, theme: str, glyph: str,
    order: int, draft: bool, readme_branch: str,
) -> tuple[str, dict]:
    title = llm["title"]
    topic = llm["topic"]
    summary = llm["summary"]
    repo_url = repo_meta.get("html_url") or f"https://github.com/{owner}/{repo}"
    homepage = repo_meta.get("homepage") or ""

    hub_meta = {
        "slug": slug,
        "title": title,
        "topic": topic,
        "summary": summary,
        "cover": cover,
        "theme": theme,
        "pills": llm.get("pills", f"{topic}|blue"),
        "glyph": glyph,
        "order": str(order),
        "matrix-subject": llm.get("matrix_subject", topic),
        "matrix-question": llm.get("matrix_question", ""),
        "matrix-risk": llm.get("matrix_risk", ""),
        "matrix-label": repo,
        "status": "draft" if draft else "published",
    }

    cap_grid = render_cards_grid(llm.get("capabilities", []), "three")
    app_grid = render_cards_grid(llm.get("applications", []), "three")
    risks_html = "\n".join(
        render_callout(r.get("severity", "warn"), r.get("title", ""), r.get("desc", ""))
        for r in llm.get("risks", [])
    ) or '          <p class="muted">（待补）</p>'
    sources_html = render_sources(
        repo_url, readme_branch, homepage, llm.get("extra_sources", [])
    )

    pills_inline = [
        f'<span class="pill {p.split("|",1)[1].strip() if "|" in p else "blue"}">{attr(p.split("|",1)[0].strip())}</span>'
        for p in (llm.get("pills") or f"{topic}|blue").split(";")
        if p.strip()
    ]

    stars = repo_meta.get("stargazers_count")
    forks = repo_meta.get("forks_count")
    lang = repo_meta.get("language") or "—"
    license_id = ((repo_meta.get("license") or {}).get("spdx_id")) or "—"
    kpi_stars = f"{stars:,}" if isinstance(stars, int) else "—"
    kpi_forks = f"{forks:,}" if isinstance(forks, int) else "—"

    html = f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{attr(title)} · 调研报告</title>
{render_meta_block(hub_meta)}
  <link rel="stylesheet" href="../assets/report.css">
</head>
<body>
  <header class="topbar">
    <div class="shell topbar-inner">
      <a class="brand" href="../index.html"><span class="mark" aria-hidden="true"></span><span>Research Hub</span></a>
      <nav class="nav" aria-label="报告导航">
        <a href="../index.html">总览</a>
        <a href="#summary">结论</a>
        <a href="#capabilities">能力</a>
        <a href="#applications">应用</a>
        <a href="#risks">风险</a>
        <a href="#sources">来源</a>
      </nav>
    </div>
  </header>

  <main>
    <section class="hero">
      <div class="shell hero-grid">
        <div>
          <p class="eyebrow">{attr(topic)} Research</p>
          <h1>{attr(title)}</h1>
          <p class="lead">{attr(summary)}</p>
          <div class="pill-row">{''.join(pills_inline)}</div>
        </div>
        <figure class="hero-media">
          <img src="{attr(cover)}" alt="{attr(title)} preview" loading="lazy" onerror="this.style.display='none'">
          <figcaption class="caption">{attr(repo_url)}</figcaption>
        </figure>
      </div>
    </section>

    <section id="summary" class="section">
      <div class="shell">
        <h2>1. 结论摘要</h2>
        <div class="grid two">
          <div class="callout good">
            <h3>推荐基线</h3>
            <p>{attr(llm.get("baseline", ""))}</p>
          </div>
          <div class="callout warn">
            <h3>补充场景 / 替代</h3>
            <p>{attr(llm.get("alternatives", ""))}</p>
          </div>
        </div>
        <div class="kpi-row">
          <div class="kpi"><strong>{kpi_stars}</strong><span>GitHub stars</span></div>
          <div class="kpi"><strong>{kpi_forks}</strong><span>forks</span></div>
          <div class="kpi"><strong>{attr(lang)}</strong><span>主语言</span></div>
          <div class="kpi"><strong>{attr(license_id)}</strong><span>license</span></div>
        </div>
      </div>
    </section>

    <section id="capabilities" class="section">
      <div class="shell">
        <h2>2. 核心能力</h2>
        {cap_grid}
      </div>
    </section>

    <section id="applications" class="section">
      <div class="shell">
        <h2>3. 应用场景</h2>
        {app_grid}
      </div>
    </section>

    <section id="risks" class="section">
      <div class="shell">
        <h2>4. 风险与缓解</h2>
        <div class="grid two">
{risks_html}
        </div>
      </div>
    </section>

    <section id="sources" class="section">
      <div class="shell">
        <h2>5. 参考来源</h2>
        <div class="sources">
{sources_html}
        </div>
      </div>
    </section>
  </main>

  <footer class="footer">
    <div class="shell">由 tools/generate.py 抓取 README 并通过 claude -p 综合而成。</div>
  </footer>
</body>
</html>
'''
    return html, hub_meta


def render_scaffold(
    slug: str, owner: str, repo: str, repo_meta: dict, readme: str,
    cover: str, theme: str, glyph: str, topic: str,
    order: int, draft: bool, readme_branch: str,
    overrides: dict,
) -> tuple[str, dict]:
    """TODO-filled scaffold (no LLM)."""
    title = overrides.get("title") or repo_meta.get("description") or repo
    repo_url = repo_meta.get("html_url") or f"https://github.com/{owner}/{repo}"
    excerpt = (readme or "").strip()[:600]
    if len(readme or "") > 600:
        excerpt += " …"

    hub_meta = {
        "slug": slug,
        "title": title,
        "topic": topic,
        "summary": overrides.get("summary") or (repo_meta.get("description") or "(待补：核心能力一句话)"),
        "cover": cover,
        "theme": theme,
        "pills": overrides.get("pills") or f"{topic}|blue;TODO|amber",
        "glyph": glyph,
        "order": str(order),
        "matrix-subject": overrides.get("matrix_subject") or topic,
        "matrix-question": overrides.get("matrix_question") or f"{repo} 的核心能力与风险。",
        "matrix-risk": overrides.get("matrix_risk") or "TODO（供应链 / 凭据 / 注入 / 抓取合规）",
        "matrix-label": overrides.get("matrix_label") or repo,
        "status": "draft" if draft else "published",
    }
    html = f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{attr(title)} · 调研报告</title>
{render_meta_block(hub_meta)}
  <link rel="stylesheet" href="../assets/report.css">
</head>
<body>
  <header class="topbar">
    <div class="shell topbar-inner">
      <a class="brand" href="../index.html"><span class="mark" aria-hidden="true"></span><span>Research Hub</span></a>
      <nav class="nav" aria-label="报告导航">
        <a href="../index.html">总览</a>
        <a href="#summary">结论</a>
        <a href="#sources">来源</a>
      </nav>
    </div>
  </header>
  <main>
    <section class="hero"><div class="shell hero-grid">
      <div>
        <p class="eyebrow">{attr(topic)} Research</p>
        <h1>{attr(title)} 调研报告</h1>
        <p class="lead">{attr(hub_meta["summary"])}</p>
      </div>
      <figure class="hero-media">
        <img src="{attr(cover)}" alt="{attr(title)}" loading="lazy" onerror="this.style.display='none'">
        <figcaption class="caption">{attr(repo_url)}</figcaption>
      </figure>
    </div></section>

    <section id="summary" class="section"><div class="shell">
      <h2>1. 结论摘要</h2>
      <p class="muted">手工补充：推荐基线 / 补充场景。</p>
    </div></section>

    <section class="section"><div class="shell">
      <h2>2. 核心能力（README 节选）</h2>
      <pre><code>{attr(excerpt) or "(README 未抓取到，请手工补充)"}</code></pre>
    </div></section>

    <section class="section"><div class="shell">
      <h2>3. 应用场景</h2><p class="muted">手工补充。</p>
    </div></section>

    <section class="section"><div class="shell">
      <h2>4. 风险与缓解</h2><p class="muted">手工补充。</p>
    </div></section>

    <section id="sources" class="section"><div class="shell">
      <h2>5. 参考来源</h2>
      <div class="sources">
        <a class="source-link" href="{attr(repo_url)}">GitHub 仓库<span>{owner}/{repo}</span></a>
        <a class="source-link" href="{attr(repo_url)}/blob/{attr(readme_branch)}/README.md">README<span>{attr(readme_branch)} 分支</span></a>
        <a class="source-link" href="{attr(repo_url)}/releases">Releases<span>历史版本</span></a>
      </div>
    </div></section>
  </main>
  <footer class="footer"><div class="shell">由 tools/generate.py --no-llm 生成的脚手架，需手工/LLM 填完五段式后才会通过 merge.py --lint。</div></footer>
</body>
</html>
'''
    return html, hub_meta


# ─────────────── main ───────────────

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("url", help="GitHub repo URL")
    ap.add_argument("--slug")
    ap.add_argument("--order", type=int, default=99)
    ap.add_argument("--title")
    ap.add_argument("--topic")
    ap.add_argument("--theme")
    ap.add_argument("--glyph")
    ap.add_argument("--cover")
    ap.add_argument("--pills")
    ap.add_argument("--matrix-subject")
    ap.add_argument("--matrix-question")
    ap.add_argument("--matrix-risk")
    ap.add_argument("--matrix-label")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--no-llm", action="store_true", help="Scaffold mode (no claude -p)")
    ap.add_argument("--llm-bin", default=None, help="Override claude binary path")
    ap.add_argument("--llm-timeout", type=int, default=240)
    args = ap.parse_args(argv)

    owner, repo = parse_url(args.url)
    slug = args.slug or re.sub(r"[^a-z0-9-]", "-", repo.lower()).strip("-")
    out = REPORTS_DIR / f"{slug}.html"
    if out.exists() and not args.overwrite:
        raise SystemExit(f"ERROR: {out} already exists. Use --overwrite to replace.")

    print(f"→ Target: {owner}/{repo} → reports/{slug}.html")
    print("→ Fetching repo metadata (api.github.com)…")
    repo_meta = fetch_repo_meta(owner, repo)
    if not repo_meta:
        print("  (offline / blocked → continuing without stars/license)")
    branches = ((repo_meta.get("default_branch") or "main"), "master")
    print(f"→ Fetching README from {branches[0]} / {branches[1]}…")
    readme, readme_branch = fetch_readme(owner, repo, branches)
    if not readme:
        print("  ! README could not be fetched", file=sys.stderr)

    cover = args.cover or derive_cover(owner, repo)
    topic = args.topic or derive_topic(
        (repo_meta.get("description") or "") + " " + readme,
        repo_meta.get("topics") or [],
    )
    theme = args.theme or derive_theme(slug)
    glyph = args.glyph or derive_glyph(topic)

    if args.no_llm:
        html, hub = render_scaffold(
            slug, owner, repo, repo_meta, readme,
            cover, theme, glyph, topic,
            args.order, args.draft, readme_branch,
            {
                "title": args.title,
                "summary": None,
                "pills": args.pills,
                "matrix_subject": args.matrix_subject,
                "matrix_question": args.matrix_question,
                "matrix_risk": args.matrix_risk,
                "matrix_label": args.matrix_label,
            },
        )
        html = inject_seo(html, seo_block_report(hub))
        out.write_text(html, encoding="utf-8")
        print(f"✓ Scaffold written: {out}")
        print("  → Fill in 5-段式 TODOs, then run merge.py")
        return 0

    # LLM mode
    claude_bin = find_claude_bin(args.llm_bin)
    if not claude_bin:
        print("  ! claude CLI not found; falling back to --no-llm scaffold", file=sys.stderr)
        return main(argv + ["--no-llm"])

    if not readme:
        print("  ! cannot run LLM without README; falling back to scaffold", file=sys.stderr)
        return main(argv + ["--no-llm"])

    prompt = LLM_PROMPT.format(
        owner=owner, repo=repo,
        description=(repo_meta.get("description") or ""),
        topics=", ".join(repo_meta.get("topics") or []) or "(none)",
        language=repo_meta.get("language") or "(unknown)",
        license=(repo_meta.get("license") or {}).get("spdx_id") or "(unknown)",
        stars=repo_meta.get("stargazers_count") or "(unknown)",
        readme=readme[:12000],
    )
    llm = call_llm(claude_bin, prompt, timeout=args.llm_timeout)
    if not llm:
        print("  ! LLM call failed; falling back to scaffold", file=sys.stderr)
        return main(argv + ["--no-llm"])

    # Apply CLI overrides on top of LLM output
    for k_cli, k_llm in (
        ("title", "title"), ("topic", "topic"), ("pills", "pills"),
        ("matrix_subject", "matrix_subject"),
        ("matrix_question", "matrix_question"),
        ("matrix_risk", "matrix_risk"),
    ):
        v = getattr(args, k_cli, None)
        if v:
            llm[k_llm] = v

    html, hub = render_filled(
        slug, owner, repo, repo_meta, llm,
        cover, theme, glyph,
        args.order, args.draft, readme_branch,
    )
    html = inject_seo(html, seo_block_report(hub))
    out.write_text(html, encoding="utf-8")
    print(f"✓ Filled report written: {out}  ({len(html):,} bytes)")
    print()
    print("Next:")
    print("  python3 tools/merge.py --lint   # quality gate")
    print("  python3 tools/merge.py          # register in index.html")
    print("  bash tools/ship.sh              # push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
