#!/usr/bin/env python3
"""Audit initial HTML, crawler access, and schema without contacting search APIs."""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app
from lib.products_catalog import get_public_products
from lib.seo import NOINDEX_PATHS, SITE_NAME
from lib.robots_policy import parse_policy

BASE = "https://oshigoto.onrender.com"
AGENTS = ("OAI-SearchBot", "PerplexityBot", "Bingbot", "Googlebot", "GPTBot")


def audit():
    client = app.test_client()
    sitemap = client.get("/sitemap.xml")
    entries = ET.fromstring(sitemap.data).findall("{*}url")
    urls = [entry.findtext("{*}loc") for entry in entries]
    robots_text = client.get("/robots.txt").get_data(as_text=True)
    parser = parse_policy(robots_text)
    paths = sorted({urlsplit(url).path for url in urls} | (NOINDEX_PATHS - {"/autofill"}))
    pages = []
    for path in paths:
        response = client.get(path, follow_redirects=False)
        soup = BeautifulSoup(response.data, "html.parser")
        canonical = soup.select_one('link[rel="canonical"]')
        meta = soup.select_one('meta[name="description"]')
        robots = soup.select_one('meta[name="robots"]')
        schemas = [json.loads(node.get_text()) for node in soup.select('script[type="application/ld+json"]')]
        main = soup.select_one("main")
        if main:
            for node in main.select("script, style"):
                node.decompose()
        pages.append({
            "path": path, "status": response.status_code,
            "canonical": canonical.get("href") if canonical else None,
            "robots": robots.get("content") if robots else None,
            "in_sitemap": BASE + path in urls,
            "title": soup.title.get_text(strip=True) if soup.title else "",
            "description": meta.get("content", "") if meta else "",
            "h1": [node.get_text(" ", strip=True) for node in soup.select("h1")],
            "main_count": len(soup.select("main")),
            "schemas": schemas,
            "internal_links": sorted({node.get("href") for node in soup.select('a[href^="/"]')}),
            "visible_text": main.get_text(" ", strip=True) if main else "",
            "crawlers": {agent: parser.can_fetch(agent, BASE + path) for agent in AGENTS},
        })
    return {"robots": robots_text, "sitemap_urls": urls,
            "lastmod": {entry.findtext("{*}loc"): entry.findtext("{*}lastmod") for entry in entries},
            "pages": pages}


def validate(report):
    urls = report["sitemap_urls"]
    assert len(urls) == len(set(urls)), "Duplicate sitemap URL"
    pages = {page["path"]: page for page in report["pages"]}
    for page in pages.values():
        path = page["path"]
        assert page["status"] == 200, path
        assert page["canonical"] == BASE + path, path
        assert page["robots"] == ("noindex,follow" if path in NOINDEX_PATHS else "index,follow"), path
        assert page["in_sitemap"] == (path not in NOINDEX_PATHS), path
        assert all(page["crawlers"].values()), path
        assert page["title"] and page["description"] and len(page["h1"]) == 1, path
        assert page["visible_text"] and page["internal_links"], path
        assert page["main_count"] == 1, path
        encoded = [json.dumps(schema, sort_keys=True) for schema in page["schemas"]]
        assert len(encoded) == len(set(encoded)), f"{path}: duplicate schema"
        for kind in ("WebSite", "Organization"):
            matches = [s for s in page["schemas"] if s.get("@type") == kind]
            assert len(matches) == 1 and matches[0]["name"] == SITE_NAME, path
        if path != "/":
            assert sum(s.get("@type") == "BreadcrumbList" for s in page["schemas"]) == 1, path
        for schema in page['schemas']:
            if schema.get('@type') == 'Article':
                assert schema['headline'] == page['h1'][0], path
                assert schema['description'] == page['description'], path
    for product in get_public_products():
        page = pages[product["path"]]
        applications = [s for s in page["schemas"] if s.get("@type") in ("WebApplication", "SoftwareApplication")]
        assert len(applications) == 1, product["id"]
        schema = applications[0]
        assert schema["name"] == product["name"] == page["h1"][0], product["id"]
        assert product["name"] in page["visible_text"], product["id"]
        assert schema["url"] == page["canonical"] and schema["description"] == page["description"], product["id"]
        assert schema["featureList"] == product["features"], product["id"]
        assert product["summary"] in page["visible_text"], product["id"]
        assert product["inputs"] and product["outputs"] and product["processing_location"], product["id"]
        assert (ROOT / product["limitations_source"]).is_file(), product["id"]
        assert product["guide_path"] in page["internal_links"], product["id"]
    parser = parse_policy(report["robots"])
    for agent in AGENTS:
        assert not parser.can_fetch(agent, BASE + "/api/pdf/lock")
    client = app.test_client()
    assert client.get("/autofill").status_code == 301
    assert client.get("/autofill").headers["Location"] == "/tools"
    assert client.get("/api/pdf/unlock").status_code == 404
    pdf = pages['/tools/pdf']['visible_text']
    assert 'PDFと設定するパスワードをサーバーへ送信' in pdf
    seo = BeautifulSoup(client.get('/tools/seo').data, 'html.parser')
    from app import MAX_SEO_CRAWL_URLS, MAX_SEO_CRAWL_DEPTH
    assert seo.select_one('#sitemap-crawl-max-urls')['max'] == str(MAX_SEO_CRAWL_URLS)
    assert seo.select_one('#sitemap-crawl-max-depth')['max'] == str(MAX_SEO_CRAWL_DEPTH)
    from unittest.mock import patch
    with patch('app._sitemap_lastmod_for_path', return_value=None):
        missing_dates = ET.fromstring(client.get('/sitemap.xml').data)
        assert not missing_dates.findall('{*}url/{*}lastmod'), 'Unknown dates must not become today'


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    report = audit()
    if args.snapshot:
        args.snapshot.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.audit_only:
        validate(report)
    print(f"{'AUDIT' if args.audit_only else 'PASS'}: {len(report['pages'])} public pages, {len(report['sitemap_urls'])} sitemap URLs, 7 tools")
