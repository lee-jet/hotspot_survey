#!/usr/bin/env python3
"""One-shot: inject AUTO:seo block into index.html + reports/*.html.

Idempotent — safe to re-run. Removes any prior AUTO:seo block first.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    INDEX_PATH,
    REPORTS_DIR,
    SITE_URL,
    collect_reports,
    inject_seo,
    parse_meta,
    seo_block_index,
    seo_block_report,
)


def main() -> int:
    print(f"Using SITE_URL = {SITE_URL}")
    print()

    # Index
    block = seo_block_index()
    old = INDEX_PATH.read_text(encoding="utf-8")
    new = inject_seo(old, block)
    if old != new:
        INDEX_PATH.write_text(new, encoding="utf-8")
        print(f"✓ index.html  (SEO block updated, {len(block):,} chars)")
    else:
        print(f"= index.html  (already current)")

    # Reports
    touched = unchanged = 0
    for r in collect_reports():
        path = REPORTS_DIR / r["__filename"]
        block = seo_block_report(r)
        old = path.read_text(encoding="utf-8")
        new = inject_seo(old, block)
        if old != new:
            path.write_text(new, encoding="utf-8")
            print(f"✓ {path.name}")
            touched += 1
        else:
            print(f"= {path.name}")
            unchanged += 1

    print()
    print(f"{touched} updated, {unchanged} unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
