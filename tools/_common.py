"""Shared helpers for hotspot_survey tooling."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from html import escape as _escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
INDEX_PATH = ROOT / "index.html"

SITE_NAME = "Research Hub"
SITE_TAGLINE = "AI Agent 与开发者工具调研中心"
SITE_DESCRIPTION = (
    "按结论 → 核心能力 → 应用场景 → 风险与缓解 → 来源五段式系统拆解 AI Agent "
    "与开发者工具，覆盖飞书 CLI、WiFi 感知、终端 Agent、长任务记忆、自治编码"
    "循环、互联网读取、浏览器自动化、工程化技能等。"
)
SITE_KEYWORDS = (
    "AI Agent, Claude Code, Cursor, Codex, MCP, DevTools, 调研报告, "
    "Agentic 开发, 代码理解, 安全风险, Prompt Injection"
)


def detect_site_url() -> str:
    """Best-effort: derive Pages URL from git remote, else env, else fallback."""
    if env := os.environ.get("HUB_SITE_URL"):
        return env.rstrip("/")
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], text=True, cwd=ROOT
        ).strip()
        m = re.match(
            r"(?:git@github\.com:|https?://github\.com/)([\w-]+)/([\w.-]+?)(?:\.git)?/?$",
            url,
        )
        if m:
            return f"https://{m.group(1)}.github.io/{m.group(2)}"
    except Exception:
        pass
    return "https://lee-jet.github.io/hotspot_survey"


SITE_URL = detect_site_url()

META_RE = re.compile(
    r'<meta\s+name="hub:(?P<key>[\w-]+)"\s+content="(?P<val>[^"]*)"\s*/?>'
)

REGION_RE = lambda name: re.compile(
    rf'(<!--\s*AUTO:{re.escape(name)}-start\s*-->)(.*?)(<!--\s*AUTO:{re.escape(name)}-end\s*-->)',
    re.DOTALL,
)


def attr(value: str) -> str:
    """Escape a string for use inside an HTML attribute."""
    return _escape(value, quote=True)


def parse_meta(html_path: Path) -> dict[str, str]:
    """Extract all `hub:*` meta tags from a report HTML file."""
    text = html_path.read_text(encoding="utf-8")
    return {m.group("key"): m.group("val") for m in META_RE.finditer(text)}


def write_meta(html_path: Path, meta: dict[str, str]) -> None:
    """Idempotently inject hub:* meta tags right after <title>."""
    text = html_path.read_text(encoding="utf-8")
    text = re.sub(r'\n?\s*<meta\s+name="hub:[\w-]+"\s+content="[^"]*"\s*/?>', "", text)
    block = "\n".join(
        f'  <meta name="hub:{k}" content="{attr(v)}">' for k, v in meta.items()
    )
    if "</title>" in text:
        text = text.replace("</title>", f"</title>\n{block}", 1)
    else:
        raise RuntimeError(f"{html_path}: no </title> anchor for meta injection")
    html_path.write_text(text, encoding="utf-8")


def count_sources(html_path: Path) -> int:
    """Count <a class="source-link"> entries inside a report."""
    text = html_path.read_text(encoding="utf-8")
    return len(re.findall(r'class="source-link"', text))


def replace_region(html: str, name: str, new_inner: str) -> str:
    """Replace content between <!-- AUTO:name-start --> and <!-- AUTO:name-end -->.

    Preserves the indentation of the start marker so the end marker stays aligned.
    """
    rx = REGION_RE(name)
    m = rx.search(html)
    if not m:
        raise RuntimeError(f"AUTO:{name} markers not found in index.html")
    line_start = html.rfind("\n", 0, m.start(1)) + 1
    indent = html[line_start : m.start(1)]
    return (
        html[: m.start()]
        + m.group(1)
        + "\n"
        + new_inner
        + "\n"
        + indent
        + m.group(3)
        + html[m.end() :]
    )


def collect_reports(strict: bool = False) -> list[dict]:
    """Load all non-draft reports sorted by hub:order, slug.

    Adds derived keys: `__filename`, `__path`, `__sources`.
    """
    out = []
    for p in sorted(REPORTS_DIR.glob("*.html")):
        meta = parse_meta(p)
        if not meta:
            msg = f"WARN: {p.name} has no hub:* meta"
            if strict:
                raise RuntimeError(msg)
            print(msg, file=sys.stderr)
            continue
        if not meta.get("slug"):
            msg = f"WARN: {p.name} missing hub:slug"
            if strict:
                raise RuntimeError(msg)
            print(msg, file=sys.stderr)
            continue
        if meta.get("status", "published") == "draft":
            continue
        meta["__filename"] = p.name
        meta["__path"] = f"reports/{p.name}"
        meta["__sources"] = count_sources(p)
        out.append(meta)
    out.sort(key=lambda r: (int(r.get("order", "99")), r["slug"]))
    return out


# Inline glyph SVG by name (right-bottom badge in report card).
GLYPHS: dict[str, str] = {
    "chat": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "wifi": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/></svg>',
    "terminal": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>',
    "file": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="15" y2="17"/></svg>',
    "loop": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"/><path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14"/></svg>',
    "globe": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15 15 0 0 1 4 10 15 15 0 0 1-4 10 15 15 0 0 1-4-10 15 15 0 0 1 4-10z"/></svg>',
    "browser": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/><path d="M2 8h20"/></svg>',
    "skill": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
    "tool": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
}


def glyph_svg(name: str) -> str:
    return GLYPHS.get(name, GLYPHS["tool"])


# ───────────── SEO ─────────────

SEO_BLOCK_MARKER = "<!-- AUTO:seo "  # opening marker prefix


def _json_ld(obj: dict) -> str:
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return f'<script type="application/ld+json">{raw}</script>'


def seo_block_report(hub: dict, site_url: str | None = None) -> str:
    """Generate the full SEO meta + JSON-LD block for a single report."""
    site_url = (site_url or SITE_URL).rstrip("/")
    slug = hub["slug"]
    title = hub["title"]
    summary = hub.get("summary", "")
    cover = hub.get("cover", "")
    topic = hub.get("topic", "")
    pill_labels = [
        p.split("|", 1)[0].strip()
        for p in (hub.get("pills") or "").split(";")
        if p.strip()
    ]
    canonical = f"{site_url}/reports/{slug}.html"
    full_title = f"{title} · {SITE_NAME}"
    keywords = ", ".join(
        [topic] + pill_labels + ["调研报告", "AI Agent", "DevTools"]
    ).strip(", ")

    json_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": summary,
        "url": canonical,
        "inLanguage": "zh-CN",
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": site_url + "/"},
    }
    if cover:
        json_ld["image"] = cover
    if topic:
        json_ld["about"] = topic
        json_ld["articleSection"] = topic

    lines = [
        f'<!-- AUTO:seo for slug={slug} - regenerated by tools/* -->',
        f'  <link rel="canonical" href="{attr(canonical)}">',
        f'  <meta name="description" content="{attr(summary)}">',
        f'  <meta name="keywords" content="{attr(keywords)}">',
        f'  <meta name="author" content="{attr(SITE_NAME)}">',
        f'  <meta name="robots" content="index,follow,max-image-preview:large">',
        f'  <meta name="theme-color" content="#0ea5e9">',
        f'  <meta property="og:type" content="article">',
        f'  <meta property="og:title" content="{attr(full_title)}">',
        f'  <meta property="og:description" content="{attr(summary)}">',
        f'  <meta property="og:url" content="{attr(canonical)}">',
        f'  <meta property="og:site_name" content="{attr(SITE_NAME)}">',
        f'  <meta property="og:locale" content="zh_CN">',
    ]
    if cover:
        lines += [
            f'  <meta property="og:image" content="{attr(cover)}">',
            f'  <meta property="og:image:alt" content="{attr(title)} preview">',
        ]
    if topic:
        lines.append(f'  <meta property="article:section" content="{attr(topic)}">')
    for label in pill_labels[:5]:
        lines.append(f'  <meta property="article:tag" content="{attr(label)}">')
    lines += [
        '  <meta name="twitter:card" content="summary_large_image">',
        f'  <meta name="twitter:title" content="{attr(full_title)}">',
        f'  <meta name="twitter:description" content="{attr(summary)}">',
    ]
    if cover:
        lines.append(f'  <meta name="twitter:image" content="{attr(cover)}">')
    lines.append("  " + _json_ld(json_ld))
    lines.append("  <!-- AUTO:seo-end -->")
    return "\n".join(lines)


def seo_block_index(site_url: str | None = None) -> str:
    """SEO block for the index page."""
    site_url = (site_url or SITE_URL).rstrip("/")
    canonical = site_url + "/"
    full_title = f"{SITE_NAME} · {SITE_TAGLINE}"
    og_image = f"https://opengraph.githubassets.com/research-hub/lee-jet/hotspot_survey"

    json_ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": full_title,
        "url": canonical,
        "description": SITE_DESCRIPTION,
        "inLanguage": "zh-CN",
        "publisher": {"@type": "Organization", "name": SITE_NAME},
    }

    lines = [
        '<!-- AUTO:seo for index - regenerated by tools/* -->',
        f'  <link rel="canonical" href="{attr(canonical)}">',
        f'  <meta name="description" content="{attr(SITE_DESCRIPTION)}">',
        f'  <meta name="keywords" content="{attr(SITE_KEYWORDS)}">',
        f'  <meta name="author" content="{attr(SITE_NAME)}">',
        f'  <meta name="robots" content="index,follow,max-image-preview:large">',
        f'  <meta name="theme-color" content="#0ea5e9">',
        f'  <meta property="og:type" content="website">',
        f'  <meta property="og:title" content="{attr(full_title)}">',
        f'  <meta property="og:description" content="{attr(SITE_DESCRIPTION)}">',
        f'  <meta property="og:url" content="{attr(canonical)}">',
        f'  <meta property="og:site_name" content="{attr(SITE_NAME)}">',
        f'  <meta property="og:locale" content="zh_CN">',
        f'  <meta property="og:image" content="{attr(og_image)}">',
        f'  <meta property="og:image:alt" content="{attr(full_title)} preview">',
        '  <meta name="twitter:card" content="summary_large_image">',
        f'  <meta name="twitter:title" content="{attr(full_title)}">',
        f'  <meta name="twitter:description" content="{attr(SITE_DESCRIPTION)}">',
        f'  <meta name="twitter:image" content="{attr(og_image)}">',
        "  " + _json_ld(json_ld),
        "  <!-- AUTO:seo-end -->",
    ]
    return "\n".join(lines)


SEO_BLOCK_RE = re.compile(
    r"<!--\s*AUTO:seo[^>]*?-->.*?<!--\s*AUTO:seo-end\s*-->\s*",
    re.DOTALL,
)


def inject_seo(html: str, block: str) -> str:
    """Insert (or replace) an AUTO:seo block right after the last hub:* meta.

    Idempotent: removes any existing AUTO:seo block first.
    Fallback anchor: right after </title>.
    """
    # Remove existing block (if any)
    html = SEO_BLOCK_RE.sub("", html)
    # Try to insert after the last hub:* meta line
    last_hub = None
    for m in re.finditer(r'(<meta\s+name="hub:[\w-]+"\s+content="[^"]*"\s*/?>)\s*\n',
                         html):
        last_hub = m
    if last_hub:
        idx = last_hub.end()
        return html[:idx] + "  " + block + "\n" + html[idx:]
    # Fallback: after </title>
    if "</title>" in html:
        return html.replace("</title>", "</title>\n  " + block, 1)
    raise RuntimeError("Cannot find anchor (hub:* meta or </title>) to inject SEO block")
