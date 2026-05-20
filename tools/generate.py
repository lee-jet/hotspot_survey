#!/usr/bin/env python3
"""Generate a report scaffold from a GitHub URL.

Usage:
    python3 tools/generate.py https://github.com/owner/repo
    python3 tools/generate.py https://github.com/owner/repo --slug custom-slug
    python3 tools/generate.py https://github.com/owner/repo --order 9
    python3 tools/generate.py https://github.com/owner/repo --overwrite
    python3 tools/generate.py https://github.com/owner/repo --draft   # status=draft

This is the **scaffold** stage: it fetches GitHub metadata + README, fills
hub:* meta, and emits an HTML file with TODO placeholders in the 5 sections
(结论 / 能力对比 / 应用场景 / 风险与缓解 / 来源).

After scaffolding:
1. Fill in section content (manually or via LLM)
2. Run `python3 tools/merge.py` to register the new card in index.html
3. Run `bash tools/ship.sh` to push
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import REPORTS_DIR, attr  # noqa: E402

GH_URL_RE = re.compile(r"https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


def parse_url(url: str) -> tuple[str, str]:
    m = GH_URL_RE.match(url.strip())
    if not m:
        raise SystemExit(f"ERROR: not a recognizable GitHub URL: {url}")
    return m.group(1), m.group(2)


def http_get(url: str, accept: str = "application/json") -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": "research-hub-generate/1.0", "Accept": accept}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ERROR: HTTP {e.code} fetching {url}")
    except urllib.error.URLError as e:
        raise SystemExit(f"ERROR: network error fetching {url}: {e.reason}")


def fetch_repo_meta(owner: str, repo: str) -> dict:
    raw = http_get(f"https://api.github.com/repos/{owner}/{repo}")
    return json.loads(raw)


def fetch_readme(owner: str, repo: str, branch: str) -> str | None:
    for name in ("README.md", "README.zh.md", "Readme.md", "readme.md"):
        try:
            return http_get(
                f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{name}",
                accept="text/plain",
            )
        except SystemExit:
            continue
    return None


def derive_topic(description: str | None, topics: list[str]) -> str:
    """Pick a short topic label heuristically."""
    if not description and not topics:
        return "工具"
    hints = " ".join((description or "").lower().split() + [t.lower() for t in topics])
    table = [
        ("cli|terminal|shell", "终端工具"),
        ("agent|autonom|loop", "AI Agent"),
        ("mcp|model-context|model context", "MCP"),
        ("browser|playwright|puppeteer|selenium", "浏览器自动化"),
        ("wifi|csi|rssi|esp32|sensing", "感知硬件"),
        ("plan|memory|file|context", "长任务记忆"),
        ("crawl|scrape|fetch|reach|internet", "互联网工具"),
        ("skill|workflow|practice|tdd|engineer", "工程实践"),
        ("feishu|lark|slack|messag", "办公自动化"),
        ("rust|wasm|c\\+\\+|python|go|java", "开发框架"),
    ]
    for pat, label in table:
        if re.search(pat, hints):
            return label
    return "工具"


THEME_PALETTE = [
    "theme-feishu",
    "theme-warp",
    "theme-planning",
    "theme-reach",
    "theme-playwright",
    "theme-ruview",
    "theme-mattpocock",
    "theme-ralph",
]


def derive_theme(slug: str) -> str:
    # Stable hash → palette index
    h = sum(ord(c) for c in slug) % len(THEME_PALETTE)
    return THEME_PALETTE[h]


def derive_glyph(topic: str) -> str:
    table = {
        "办公自动化": "chat",
        "感知硬件": "wifi",
        "终端工具": "terminal",
        "AI Agent": "loop",
        "MCP": "browser",
        "浏览器自动化": "browser",
        "长任务记忆": "file",
        "互联网工具": "globe",
        "工程实践": "skill",
    }
    return table.get(topic, "tool")


def derive_cover(owner: str, repo: str) -> str:
    # GitHub OpenGraph image; works for any public repo.
    return f"https://opengraph.githubassets.com/research-hub/{owner}/{repo}"


def build_html(
    slug: str,
    owner: str,
    repo: str,
    meta: dict,
    args: argparse.Namespace,
    readme_excerpt: str,
) -> str:
    title = args.title or meta.get("description") or repo
    description = meta.get("description") or ""
    topics = meta.get("topics") or []
    topic = args.topic or derive_topic(description, topics)
    theme = args.theme or derive_theme(slug)
    glyph = args.glyph or derive_glyph(topic)
    cover = args.cover or derive_cover(owner, repo)
    summary = description or "(请补充：核心能力一句话总结)"
    homepage = meta.get("homepage") or ""
    release_tag = (meta.get("default_branch") or "main")
    repo_url = meta.get("html_url") or f"https://github.com/{owner}/{repo}"

    hub_meta = {
        "slug": slug,
        "title": title,
        "topic": topic,
        "summary": summary,
        "cover": cover,
        "theme": theme,
        "pills": args.pills or f"{topic}|blue;TODO|amber",
        "glyph": glyph,
        "order": str(args.order),
        "matrix-subject": args.matrix_subject or topic,
        "matrix-question": args.matrix_question or f"{repo} 的核心能力、应用场景与风险边界。",
        "matrix-risk": args.matrix_risk or "TODO（供应链 / 凭据 / 注入 / 抓取合规）",
        "matrix-label": args.matrix_label or repo,
        "status": "draft" if args.draft else "published",
    }
    meta_block = "\n".join(
        f'  <meta name="hub:{k}" content="{attr(v)}">' for k, v in hub_meta.items()
    )

    # Extract a small README hint for the body (first ~600 chars, cleaned)
    excerpt = (readme_excerpt or "").strip()
    if len(excerpt) > 600:
        excerpt = excerpt[:600].rstrip() + " …"
    excerpt_html = attr(excerpt) if excerpt else "（README 抓取失败或为空，请手工补充。）"

    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{attr(title)} · 调研报告</title>
{meta_block}
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
          <h1>{attr(title)} 调研报告</h1>
          <p class="lead">{attr(summary)}</p>
          <div class="pill-row">
            <span class="pill blue">{attr(topic)}</span>
            <span class="pill amber">TODO · 风险待补</span>
          </div>
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
            <p>TODO：用 1-2 句话说明在什么场景下推荐使用此工具。</p>
          </div>
          <div class="callout warn">
            <h3>补充场景 / 替代方案</h3>
            <p>TODO：列出适合补充使用的相关工具或限制场景。</p>
          </div>
        </div>
        <div class="kpi-row">
          <div class="kpi"><strong>{meta.get("stargazers_count", 0):,}</strong><span>GitHub stars</span></div>
          <div class="kpi"><strong>{meta.get("forks_count", 0):,}</strong><span>forks</span></div>
          <div class="kpi"><strong>{(meta.get("language") or "—")}</strong><span>主语言</span></div>
          <div class="kpi"><strong>{(meta.get("license") or {{}}).get("spdx_id") or "—"}</strong><span>license</span></div>
        </div>
      </div>
    </section>

    <section id="capabilities" class="section">
      <div class="shell">
        <h2>2. 核心能力</h2>
        <p class="muted">README 节选（待手工补全成正式结构）：</p>
        <pre><code>{excerpt_html}</code></pre>
      </div>
    </section>

    <section id="applications" class="section">
      <div class="shell">
        <h2>3. 应用场景</h2>
        <div class="grid three">
          <article class="card"><h3>场景一</h3><p>TODO</p></article>
          <article class="card"><h3>场景二</h3><p>TODO</p></article>
          <article class="card"><h3>场景三</h3><p>TODO</p></article>
        </div>
      </div>
    </section>

    <section id="risks" class="section">
      <div class="shell">
        <h2>4. 风险与缓解</h2>
        <div class="grid two">
          <div class="callout risk"><h3>风险 1</h3><p>TODO</p></div>
          <div class="callout warn"><h3>风险 2</h3><p>TODO</p></div>
        </div>
      </div>
    </section>

    <section id="sources" class="section">
      <div class="shell">
        <h2>5. 参考来源</h2>
        <div class="sources">
          <a class="source-link" href="{attr(repo_url)}">GitHub 仓库<span>{owner}/{repo}</span></a>
          <a class="source-link" href="{attr(repo_url)}/blob/{attr(release_tag)}/README.md">README<span>{attr(release_tag)} 分支</span></a>
          <a class="source-link" href="{attr(repo_url)}/releases">Releases<span>历史版本</span></a>
          {'<a class="source-link" href="' + attr(homepage) + '">官网<span>homepage</span></a>' if homepage else ''}
        </div>
      </div>
    </section>
  </main>

  <footer class="footer">
    <div class="shell">脚手架由 tools/generate.py 生成，待手工或 LLM 补完五段式内容。</div>
  </footer>
</body>
</html>
'''


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="GitHub repo URL, e.g. https://github.com/owner/repo")
    ap.add_argument("--slug", help="Override report slug (default: repo name kebab)")
    ap.add_argument("--order", type=int, default=99, help="Sort order in index (lower = earlier)")
    ap.add_argument("--title", help="Override card title")
    ap.add_argument("--topic", help="Override topic badge")
    ap.add_argument("--theme", help="Override theme class (theme-*)")
    ap.add_argument("--glyph", help="Override glyph name (chat/wifi/terminal/file/loop/globe/browser/skill/tool)")
    ap.add_argument("--cover", help="Override cover image URL")
    ap.add_argument("--pills", help="Pills 'Label|color;Label|color'")
    ap.add_argument("--matrix-subject")
    ap.add_argument("--matrix-question")
    ap.add_argument("--matrix-risk")
    ap.add_argument("--matrix-label")
    ap.add_argument("--draft", action="store_true", help="Mark hub:status=draft (excluded from merge)")
    ap.add_argument("--overwrite", action="store_true", help="Replace existing report file")
    args = ap.parse_args(argv)

    owner, repo = parse_url(args.url)
    slug = args.slug or re.sub(r"[^a-z0-9-]", "-", repo.lower()).strip("-")
    out = REPORTS_DIR / f"{slug}.html"
    if out.exists() and not args.overwrite:
        raise SystemExit(f"ERROR: {out} already exists. Use --overwrite to replace.")

    print(f"→ Fetching repo metadata: {owner}/{repo}")
    meta = fetch_repo_meta(owner, repo)
    branch = meta.get("default_branch", "main")
    print(f"→ Fetching README from {branch} branch")
    readme = fetch_readme(owner, repo, branch) or ""

    html = build_html(slug, owner, repo, meta, args, readme)
    out.write_text(html, encoding="utf-8")
    print(f"✓ Wrote {out}")
    print()
    print("Next steps:")
    print(f"  1. Edit {out.relative_to(Path.cwd())} — fill in 5-段式 TODO placeholders")
    print(f"  2. python3 tools/merge.py     # register the card in index.html")
    print(f"  3. bash tools/ship.sh          # commit + push to GitHub")
    if args.draft:
        print()
        print("(Status: draft — merge.py will SKIP this report until you change hub:status to 'published'.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
