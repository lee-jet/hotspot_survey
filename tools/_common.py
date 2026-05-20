"""Shared helpers for hotspot_survey tooling."""
from __future__ import annotations

import re
import sys
from html import escape as _escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
INDEX_PATH = ROOT / "index.html"

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
