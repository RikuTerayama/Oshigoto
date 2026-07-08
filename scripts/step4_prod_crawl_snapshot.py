#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 4: 本番環境クロールスナップショット収集
対象URLを本番にGETし、status・canonical・robots・文字数・内部リンク等を収集。
出力: JSON（レポート作成用）
"""
import json
import os
import re
import sys
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:
    print("pip install requests", file=sys.stderr)
    sys.exit(1)

BASE = "https://jobcan-automation.onrender.com"
URLS = [
    "/",
    "/best-practices",
    "/privacy",
    "/blog",
    "/guide/excel-format",
    "/glossary",
    "/case-studies",
]

DOMAIN = urlparse(BASE).netloc


def analyze_html(html, page_url):
    canonical = None
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
    if not m:
        m = re.search(r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']', html, re.I)
    if m:
        canonical = m.group(1)
    meta_robots = None
    m = re.search(r'<meta[^>]+name=["\'](?:robots|googlebot)["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        meta_robots = m.group(1)
    title = None
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I | re.S)
    if m:
        title = m.group(1).strip()
    h1 = None
    m = re.search(r"<h1[^>]*>([^<]+(?:<[^>]+>[^<]*)*)</h1>", html, re.I)
    if m:
        h1 = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    ld_count = len(re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>', html, re.I))
    stripped = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    stripped = re.sub(r"<style[^>]*>.*?</style>", " ", stripped, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", stripped)
    text = re.sub(r"\s+", " ", text).strip()
    body_chars = len(text)
    internal_links = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.I):
        href = m.group(1).strip()
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        full = urljoin(page_url, href)
        p = urlparse(full)
        if p.netloc == DOMAIN or (not p.netloc and p.path):
            path = p.path.rstrip("/") or "/"
            internal_links.append(path)
    internal_links = list(set(internal_links))
    shortcut_anchors = [
        x for x in ["basic-terms", "jobcan-terms", "autofill-terms", "it-security"]
        if f'id="{x}"' in html or f"id='{x}'" in html
    ]
    return {
        "canonical": canonical,
        "meta_robots": meta_robots or "(なし)",
        "title": title,
        "h1": h1,
        "body_chars": body_chars,
        "internal_link_count": len(internal_links),
        "internal_links_sample": internal_links[:30],
        "has_ld_json": ld_count > 0,
        "ld_json_count": ld_count,
        "links_to": {
            "/guide": "/guide" in internal_links or any(p.startswith("/guide") for p in internal_links),
            "/blog": "/blog" in internal_links,
            "/glossary": "/glossary" in internal_links,
            "/tools": "/tools" in internal_links,
            "/case-studies": "/case-studies" in internal_links,
        },
        "shortcut_anchors": shortcut_anchors,
    }




def fetch_page(url, session):
    r = session.get(url, allow_redirects=True, timeout=30)
    return {
        "status": r.status_code,
        "final_url": r.url,
        "headers": {
            "cache-control": r.headers.get("Cache-Control", ""),
            "x-robots-tag": r.headers.get("X-Robots-Tag", ""),
            "content-type": r.headers.get("Content-Type", ""),
        },
    }, r.text


def main():
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (compatible; JobcanAudit/1.0)"

    pages = []
    for path in URLS:
        url = BASE.rstrip("/") + ("/" if path == "/" else path)
        print(f"Fetching {url}...", file=sys.stderr)
        try:
            meta, body = fetch_page(url, session)
            html_data = analyze_html(body, url)
            pages.append({
                "path": path,
                "url": url,
                "status": meta["status"],
                "final_url": meta["final_url"],
                "headers": meta["headers"],
                **html_data,
            })
        except Exception as e:
            pages.append({
                "path": path,
                "url": url,
                "error": str(e),
                "status": None,
            })

    # robots.txt
    try:
        r = session.get(BASE + "/robots.txt", timeout=15)
        robots = {
            "status": r.status_code,
            "body_preview": r.text[:1500] if r.text else "",
            "body_full": r.text or "",
        }
    except Exception as e:
        robots = {"error": str(e), "status": None}

    # sitemap.xml
    try:
        r = session.get(BASE + "/sitemap.xml", timeout=15)
        sitemap_body = r.text or ""
        locs = re.findall(r"<loc>([^<]+)</loc>", sitemap_body)
        lastmods = re.findall(r"<lastmod>([^<]+)</lastmod>", sitemap_body)
        sitemap = {
            "status": r.status_code,
            "loc_count": len(locs),
            "locs": locs,
            "lastmod_count": len(lastmods),
            "lastmods_unique": len(set(lastmods)) if lastmods else 0,
            "has_case_studies": any("/case-studies" in loc for loc in locs),
            "lastmods_sample": lastmods[:15],
        }
    except Exception as e:
        sitemap = {"error": str(e), "status": None}

    out = {
        "base": BASE,
        "pages": pages,
        "robots": robots,
        "sitemap": sitemap,
    }
    out_path = os.path.join(os.path.dirname(__file__), "..", "docs", "step4_prod_crawl_raw.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
