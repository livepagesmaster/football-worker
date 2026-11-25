#!/usr/bin/env python3
"""
Scans data/blogs/*.html, extracts meta tags from each file,
and writes data/blogs.json with:
  - latest : 5 newest blogs (for the main page)
  - all    : every blog, newest first
  - count  : total number of blogs
"""

import json
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BLOGS_DIR = BASE_DIR / "data" / "blogs"
OUT_FILE = BASE_DIR / "data" / "blogs.json"


def read_meta(html: str, name: str) -> str:
    """Extract <meta name="NAME" content="VALUE"> (name is case-insensitive)."""
    pattern = rf'<meta\s+name=["\']{re.escape(name)}["\']\s+content=["\'](.*?)["\']\s*/?>'
    m = re.search(pattern, html, re.I | re.S)
    return m.group(1).strip() if m else ""


def main():
    blogs = []

    if BLOGS_DIR.exists():
        for f in sorted(BLOGS_DIR.glob("*.html")):
            try:
                html = f.read_text(encoding="utf-8")
            except Exception as e:
                print(f"  skip {f.name}: {e}")
                continue

            title = read_meta(html, "blog-title")
            snippet = read_meta(html, "blog-snippet")
            date = read_meta(html, "blog-date")
            slug = read_meta(html, "blog-slug") or f.stem

            if not title:
                print(f"  skip {f.name}: no blog-title meta")
                continue

            blogs.append({
                "slug": slug,
                "title": title,
                "snippet": snippet,
                "date": date,
                "file": f.name,
            })

    # Newest first (YYYY-MM-DD sorts correctly as string)
    blogs.sort(key=lambda b: b.get("date", ""), reverse=True)

    out = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(blogs),
        "latest": blogs[:5],
        "all": blogs,
    }

    OUT_FILE.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(blogs)} blogs -> {OUT_FILE}")


if __name__ == "__main__":
    main()
