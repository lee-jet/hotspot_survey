#!/usr/bin/env python3
"""Rebuild index.html AUTO regions from reports/*.html hub:* meta.

Usage:
    python3 tools/merge.py             # rewrite index.html in place
    python3 tools/merge.py --dry-run   # show what would change, no write
    python3 tools/merge.py --check     # validate meta completeness only
    python3 tools/merge.py --lint      # quality gate: sources, TODOs, links

Touches only content between AUTO:cards / AUTO:matrix / AUTO:kpi markers.
The hero, pillars, study-boundary, footer sections are never modified.
"""
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    INDEX_PATH,
    REPORTS_DIR,
    ROOT,
    SITE_URL,
    attr,
    collect_reports,
    glyph_svg,
    inject_seo,
    replace_region,
    seo_block_index,
    seo_block_report,
)

REQUIRED = (
    "slug",
    "title",
    "topic",
    "summary",
    "cover",
    "theme",
    "matrix-subject",
    "matrix-question",
    "matrix-risk",
    "matrix-label",
)


def validate(reports: list[dict]) -> list[str]:
    errs = []
    for r in reports:
        missing = [k for k in REQUIRED if not r.get(k)]
        if missing:
            errs.append(f"{r['__filename']}: missing {missing}")
    return errs


def render_pills(spec: str) -> str:
    """Parse 'Label|color;Label|color' into pill HTML."""
    if not spec:
        return ""
    out = []
    for entry in spec.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        if "|" in entry:
            label, color = entry.split("|", 1)
        else:
            label, color = entry, "blue"
        out.append(
            f'<span class="pill {attr(color.strip())}">{attr(label.strip())}</span>'
        )
    return "".join(out)


def render_card(r: dict, delay: int) -> str:
    pills = render_pills(r.get("pills", ""))
    cover = r.get("cover", "")
    cover_img = (
        f'<img src="{attr(cover)}" alt="{attr(r["title"])} preview" '
        f'loading="lazy" onerror="this.style.display=\'none\'">'
        if cover
        else ""
    )
    return f'''          <a class="report-card themed {attr(r["theme"])} reveal" data-delay="{delay}" href="{attr(r["__path"])}" aria-label="{attr(r["title"])} 调研报告">
            <div class="thumb">
              {cover_img}
              <span class="topic">{attr(r["topic"])}</span>
              <div class="glyph" aria-hidden="true">
                {glyph_svg(r.get("glyph", "tool"))}
              </div>
            </div>
            <div class="report-card-body">
              <h3>{attr(r["title"])}</h3>
              <p>{attr(r["summary"])}</p>
              <div class="pill-row">{pills}</div>
              <div class="row"><span class="read">阅读报告</span></div>
            </div>
          </a>'''


def render_cards(reports: list[dict]) -> str:
    return "\n\n".join(render_card(r, i + 1) for i, r in enumerate(reports))


def render_matrix_row(r: dict) -> str:
    return f'''              <tr>
                <td>{attr(r["matrix-subject"])}</td>
                <td><a href="{attr(r["__path"])}">{attr(r["matrix-label"])}</a></td>
                <td>{attr(r["matrix-question"])}</td>
                <td>{attr(r["matrix-risk"])}</td>
              </tr>'''


def render_matrix(reports: list[dict]) -> str:
    return "\n".join(render_matrix_row(r) for r in reports)


def round_sources(n: int) -> str:
    """Round down to nearest 10 with + suffix; for small n keep exact."""
    if n < 10:
        return str(n)
    return f"{(n // 10) * 10}+"


def render_kpi(reports: list[dict]) -> str:
    n_reports = len(reports)
    n_sources = sum(r["__sources"] for r in reports)
    return (
        f'          <div class="kpi reveal" data-delay="1"><strong>{n_reports}</strong><span>调研对象（工具 / 框架 / 实践）</span></div>\n'
        f'          <div class="kpi reveal" data-delay="2"><strong>4</strong><span>大风险类别（Token / Cookie / Injection / 供应链）</span></div>\n'
        f'          <div class="kpi reveal" data-delay="3"><strong>{round_sources(n_sources)}</strong><span>引用来源（官网 · GitHub · Release）</span></div>\n'
        f'          <div class="kpi reveal" data-delay="4"><strong>5</strong><span>段式统一结构（结论 → 能力 → 应用 → 风险 → 来源）</span></div>'
    )


MIN_SOURCES = 3
TODO_PATTERNS = (
    re.compile(r"\bTODO\b"),
    re.compile(r"待补"),
    re.compile(r"占位"),
)


def lint_report(report: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a single report."""
    errs: list[str] = []
    warns: list[str] = []
    path = REPORTS_DIR / report["__filename"]
    text = path.read_text(encoding="utf-8")

    # 1. Sources floor
    if report["__sources"] < MIN_SOURCES:
        errs.append(
            f"only {report['__sources']} <a class=\"source-link\"> entries "
            f"(min {MIN_SOURCES})"
        )

    # 2. TODO / placeholder remnants outside <code>/<pre>
    body = re.sub(r"<pre.*?</pre>", "", text, flags=re.DOTALL)
    body = re.sub(r"<code.*?</code>", "", body, flags=re.DOTALL)
    for rx in TODO_PATTERNS:
        m = rx.search(body)
        if m:
            errs.append(f"unfilled placeholder near '{m.group(0)}'")
            break

    # 3. Internal reports/<...>.html links (a sibling exists?)
    sibling_links = set(
        re.findall(r'href="(?:\.\./)?reports/([\w-]+)\.html"', text)
    )
    for slug in sibling_links:
        if not (REPORTS_DIR / f"{slug}.html").exists():
            errs.append(f"broken sibling link: reports/{slug}.html")

    # 4. CSS link path
    if 'href="../assets/report.css"' not in text:
        warns.append("CSS link not '../assets/report.css' — may break in subpath")

    # 5. hub:status sanity
    if report.get("status") not in {"published", "draft"}:
        warns.append(f"hub:status='{report.get('status')}' (expected published|draft)")

    return errs, warns


def run_lint(reports: list[dict]) -> int:
    total_e = total_w = 0
    print(f"Linting {len(reports)} reports (min sources: {MIN_SOURCES})\n")
    for r in reports:
        errs, warns = lint_report(r)
        if not errs and not warns:
            print(f"  ✓ {r['__filename']:32}  sources={r['__sources']}")
            continue
        print(f"  ✗ {r['__filename']:32}  sources={r['__sources']}")
        for e in errs:
            print(f"      ERROR: {e}")
            total_e += 1
        for w in warns:
            print(f"      WARN:  {w}")
            total_w += 1
    print(f"\n{total_e} errors, {total_w} warnings.")
    return 1 if total_e > 0 else 0


def refresh_seo(reports: list[dict]) -> int:
    """Refresh AUTO:seo block in index.html and every report. Returns #files changed."""
    changed = 0
    # Index
    old = INDEX_PATH.read_text(encoding="utf-8")
    new = inject_seo(old, seo_block_index())
    if new != old:
        INDEX_PATH.write_text(new, encoding="utf-8")
        changed += 1
    # Reports
    for r in reports:
        path = REPORTS_DIR / r["__filename"]
        old = path.read_text(encoding="utf-8")
        new = inject_seo(old, seo_block_report(r))
        if new != old:
            path.write_text(new, encoding="utf-8")
            changed += 1
    return changed


def write_sitemap(reports: list[dict]) -> Path:
    """Write sitemap.xml listing index + all published reports."""
    from datetime import datetime, timezone
    site = SITE_URL.rstrip("/")
    sitemap_path = ROOT / "sitemap.xml"

    def stat_iso(p: Path) -> str:
        ts = p.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

    urls = [
        (f"{site}/", stat_iso(INDEX_PATH), "1.0", "weekly"),
    ]
    for r in reports:
        path = REPORTS_DIR / r["__filename"]
        urls.append((
            f"{site}/reports/{r['__filename']}",
            stat_iso(path),
            "0.8",
            "monthly",
        ))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod, priority, freq in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{freq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    sitemap_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sitemap_path


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    check_only = "--check" in argv
    lint_mode = "--lint" in argv

    reports = collect_reports()
    if not reports:
        print("ERROR: no published reports found", file=sys.stderr)
        return 1

    errs = validate(reports)
    if errs:
        print("Validation errors:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if lint_mode:
        return run_lint(reports)

    if check_only:
        print(f"✓ {len(reports)} reports, all required meta present.")
        return 0

    old = INDEX_PATH.read_text(encoding="utf-8")
    new = replace_region(old, "cards", render_cards(reports))
    new = replace_region(new, "matrix", render_matrix(reports))
    new = replace_region(new, "kpi", render_kpi(reports))

    if old == new:
        print(f"= index.html already in sync ({len(reports)} reports)")
        # Still refresh SEO + sitemap so they're up to date on every run
        seo_changed = refresh_seo(reports)
        if seo_changed:
            print(f"✓ SEO block refreshed in {seo_changed} file(s)")
        write_sitemap(reports)
        print(f"✓ sitemap.xml regenerated ({len(reports) + 1} URLs)")
        return 0

    if dry_run:
        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="index.html (current)",
            tofile="index.html (after merge)",
            n=2,
        )
        sys.stdout.writelines(diff)
        return 0

    INDEX_PATH.write_text(new, encoding="utf-8")
    print(
        f"✓ Merged {len(reports)} reports into index.html "
        f"({sum(r['__sources'] for r in reports)} sources total)"
    )
    # SEO refresh + sitemap (idempotent, only writes if changed)
    seo_changed = refresh_seo(reports)
    if seo_changed:
        print(f"✓ SEO block refreshed in {seo_changed} file(s)")
    sitemap = write_sitemap(reports)
    print(f"✓ sitemap.xml regenerated ({len(reports) + 1} URLs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
