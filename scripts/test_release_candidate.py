#!/usr/bin/env python3
"""Release-candidate checks for public pages, SEO, links, and monetization."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("AMAZON_AFFILIATE_ENABLED", "true")
os.environ.setdefault("AMAZON_ASSOCIATE_TAG", "release-check-22")
os.environ.setdefault("AFFILIATE_ENABLED", "true")
os.environ.setdefault("AFFILIATE_BANNERS_ENABLED", "true")

from app import app  # noqa: E402
from lib.a8_affiliate_catalog import (  # noqa: E402
    A8_ELIGIBLE_EXACT_PATHS,
    A8_HARD_EXCLUDED_PATHS,
    get_a8_visible_limit,
)
from lib.amazon_affiliate_map import (  # noqa: E402
    AMAZON_ELIGIBLE_EXACT_PATHS,
    AMAZON_HARD_EXCLUDED_PATHS,
    get_amazon_visible_limit,
)


INDEXABLE_PATHS = (
    "/",
    "/about",
    "/business",
    "/faq",
    "/glossary",
    "/best-practices",
    "/guide",
    "/guide/pdf",
    "/guide/csv",
    "/guide/image-batch",
    "/guide/image-compress",
    "/guide/qr-code",
    "/guide/image-cleanup",
    "/guide/seo",
    "/tools",
    "/tools/pdf",
    "/tools/csv",
    "/tools/image-batch",
    "/tools/image-compress",
    "/tools/qr-code",
    "/tools/image-cleanup",
    "/tools/seo",
    "/blog",
    "/blog/excel-format-mistakes-and-design",
)
NOINDEX_HTML_PATHS = ("/privacy", "/terms", "/contact", "/sitemap.html")
PUBLIC_HTML_PATHS = INDEXABLE_PATHS + NOINDEX_HTML_PATHS
NO_GO_PATHS = (
    "/tools/ocr",
    "/guide/ocr",
    "/api/ocr",
    "/_internal/ocr-spike",
    "/tools/background-removal",
    "/guide/background-removal",
    "/api/background-removal",
    "/_internal/background-removal-spike",
    "/api/pdf/unlock",
)
ERROR_CHECK_PATH = "/this-page-does-not-exist-release-check"
DUPLICATE_SCHEMA_TOOL_PATHS = (
    "/tools/pdf",
    "/tools/csv",
    "/tools/image-batch",
    "/tools/image-compress",
    "/tools/image-cleanup",
)
ADSENSE_SCRIPT = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def json_ld_documents(soup: BeautifulSoup) -> list[dict | list]:
    documents: list[dict | list] = []
    for node in soup.select('script[type="application/ld+json"]'):
        try:
            document = json.loads(node.string or node.get_text())
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AssertionError(f"invalid JSON-LD: {exc}") from exc
        require(isinstance(document, (dict, list)), "JSON-LD root must be an object or array")
        documents.append(document)
    return documents


def normalized_json(document: dict | list) -> str:
    """Return a key-order-independent representation for exact duplicate checks."""
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def schema_types(documents: list[dict | list]) -> set[str]:
    found: set[str] = set()

    def collect(value):
        if isinstance(value, dict):
            type_value = value.get("@type")
            if isinstance(type_value, str):
                found.add(type_value)
            elif isinstance(type_value, list):
                found.update(item for item in type_value if isinstance(item, str))
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    for document in documents:
        collect(document)
    return found


def require_valid_internal_target(client, path: str, source: str) -> None:
    response = client.get(path, follow_redirects=False)
    if response.status_code == 200:
        return
    if response.status_code in {301, 302, 307, 308}:
        followed = client.get(path, follow_redirects=True)
        require(followed.status_code == 200, f"{source}: redirect target failed for {path}")
        return
    raise AssertionError(f"{source}: broken internal link {path} status={response.status_code}")


def main() -> int:
    app.config["TESTING"] = True
    client = app.test_client()
    titles: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    internal_paths: set[str] = set()

    for path in PUBLIC_HTML_PATHS:
        response = client.get(path, follow_redirects=False)
        require(response.status_code == 200, f"{path}: expected 200, got {response.status_code}")
        require(response.headers.get("X-Content-Type-Options") == "nosniff", f"{path}: nosniff missing")
        require(response.headers.get("X-Frame-Options") == "SAMEORIGIN", f"{path}: frame policy missing")
        body = response.get_data(as_text=True)
        require("\ufffd" not in body, f"{path}: replacement character exposed")
        soup = BeautifulSoup(body, "html.parser")

        title = (soup.title.get_text(strip=True) if soup.title else "")
        description_node = soup.select_one('meta[name="description"]')
        description = (description_node.get("content") or "").strip() if description_node else ""
        require(title, f"{path}: title missing")
        require(description, f"{path}: meta description missing")
        titles[path] = title
        descriptions[path] = description

        require(len(soup.select("h1")) == 1, f"{path}: expected exactly one H1")
        canonical = soup.select_one('link[rel="canonical"]')
        canonical_url = (canonical.get("href") or "").strip() if canonical else ""
        require(canonical_url == f"https://oshigoto.onrender.com{path}", f"{path}: bad canonical {canonical_url!r}")

        robots = soup.select_one('meta[name="robots"]')
        robots_value = (robots.get("content") or "").lower() if robots else ""
        if path in INDEXABLE_PATHS:
            require("noindex" not in robots_value, f"{path}: indexable page is noindex")
        else:
            require("noindex" in robots_value, f"{path}: expected noindex")

        documents = json_ld_documents(soup)
        normalized_documents = [normalized_json(document) for document in documents]
        require(
            len(normalized_documents) == len(set(normalized_documents)),
            f"{path}: exact duplicate JSON-LD object detected",
        )
        types = schema_types(documents)
        require("WebSite" in types, f"{path}: WebSite schema missing")
        if path != "/":
            require("BreadcrumbList" in types, f"{path}: BreadcrumbList schema missing")
        if path.startswith("/tools/"):
            require(types & {"WebApplication", "SoftwareApplication"}, f"{path}: tool schema missing")
        if path.startswith("/guide/") or path.startswith("/blog/"):
            require("Article" in types, f"{path}: Article schema missing")
        require(not (types & {"Review", "AggregateRating"}), f"{path}: unsupported review schema exposed")
        if path in DUPLICATE_SCHEMA_TOOL_PATHS:
            root_types = [document.get("@type") for document in documents if isinstance(document, dict)]
            require(root_types.count("BreadcrumbList") == 1, f"{path}: expected one BreadcrumbList")
            require(
                sum(root_types.count(schema_type) for schema_type in ("WebApplication", "SoftwareApplication")) == 1,
                f"{path}: expected one application schema",
            )
            require(root_types.count("Offer") == 0, f"{path}: standalone Offer schema is not allowed")

        require(body.count(ADSENSE_SCRIPT) == 1, f"{path}: expected one AdSense loader")
        amazon_count = len(soup.select("section.amazon-single-card"))
        a8_count = body.count('data-a8-creative-id="')
        require(amazon_count <= get_amazon_visible_limit(path), f"{path}: too many Amazon recommendations")
        require(a8_count <= get_a8_visible_limit(path), f"{path}: too many A8 creatives")
        if path in AMAZON_HARD_EXCLUDED_PATHS:
            require(amazon_count == 0, f"{path}: Amazon rendered on excluded page")
        if path in AMAZON_ELIGIBLE_EXACT_PATHS or path.startswith("/blog/"):
            require(amazon_count == get_amazon_visible_limit(path), f"{path}: Amazon recommendation count mismatch")
        if path in A8_HARD_EXCLUDED_PATHS:
            require(a8_count == 0, f"{path}: A8 rendered on excluded page")
        if path in A8_ELIGIBLE_EXACT_PATHS or path.startswith("/blog/"):
            require(a8_count == get_a8_visible_limit(path), f"{path}: A8 creative count mismatch")

        if path == "/":
            require(len(soup.select(".hero-tool-grid > .hero-tool-card")) == 6, "/: expected six hero tool cards")
            require(len(soup.select(".landing-tool-grid > .tool-card-v2")) == 7, "/: expected seven landing tool cards")
            require(not soup.select(".hero-tool-stack, .tool-card-grid.cards-grid--balanced"), "/: legacy balanced grid class detected")
            rail = soup.select_one(".landing-affiliate-rail")
            require(rail is not None, "/: affiliate rail missing")
            require(len(rail.select(".amazon-single-card")) == 1, "/: rail must contain one Amazon recommendation")
            require(len(rail.select("[data-a8-creative-id]")) == 1, "/: rail must contain one A8 creative")
            require(rail.select_one(".landing-affiliate-rail__related") is not None, "/: publisher guide content missing from rail")
            lower_band = soup.select_one(".landing-monetization-band")
            require(lower_band is not None, "/: lower monetization band missing")
            require(len(lower_band.select(".amazon-single-card")) == 1, "/: lower Amazon recommendation missing")
            require(len(lower_band.select("[data-a8-creative-id]")) == 1, "/: lower A8 creative missing")
            require(lower_band.select_one(".related-content") is not None, "/: publisher content must separate lower affiliates")
            amazon_urls = [link.get("href") for link in soup.select(".amazon-single-card__cta")]
            require(len(amazon_urls) == 2 and len(set(amazon_urls)) == 2, "/: Amazon URLs must be distinct")
            creative_ids = [slot.get("data-a8-creative-id") for slot in soup.select("[data-a8-creative-id]")]
            require(len(creative_ids) == 2 and len(set(creative_ids)) == 2, "/: A8 creatives should differ")
            amazon_position = body.find('class="amazon-single-card"')
            related_position = body.find('class="landing-affiliate-rail__related"')
            a8_position = body.find('data-a8-creative-id="')
            require(
                -1 < amazon_position < related_position < a8_position,
                "/: expected Amazon, publisher guide, then A8 in DOM order",
            )

        if path == "/tools":
            require(len(soup.select(".tools-catalog-grid > .product-card")) == 7, "/tools: expected seven catalog cards")

        for link in soup.select("a[href]"):
            href = (link.get("href") or "").strip()
            parsed = urlparse(href)
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            if parsed.scheme or parsed.netloc or parsed.path.startswith("/static/"):
                continue
            if parsed.path.startswith("/"):
                internal_paths.add(parsed.path)

    require(len(set(titles.values())) == len(titles), "duplicate page titles detected")
    require(len(set(descriptions.values())) == len(descriptions), "duplicate meta descriptions detected")

    for path in sorted(internal_paths):
        require_valid_internal_target(client, path, "public pages")

    sitemap_response = client.get("/sitemap.xml")
    require(sitemap_response.status_code == 200, "sitemap.xml unavailable")
    sitemap_root = ET.fromstring(sitemap_response.data)
    sitemap_paths = {
        urlparse(node.find(f"{SITEMAP_NS}loc").text).path
        for node in sitemap_root.findall(f"{SITEMAP_NS}url")
    }
    require(sitemap_paths == set(INDEXABLE_PATHS), "sitemap and indexable route inventory differ")

    robots_body = client.get("/robots.txt").get_data(as_text=True)
    require("Sitemap: https://oshigoto.onrender.com/sitemap.xml" in robots_body, "robots sitemap missing")
    require("Disallow: /autofill" in robots_body, "autofill robots exclusion missing")

    autofill = client.get("/autofill", follow_redirects=False)
    require(autofill.status_code == 301 and autofill.headers.get("Location", "").endswith("/tools"), "autofill redirect changed")
    for path in NO_GO_PATHS:
        require(client.get(path, follow_redirects=False).status_code == 404, f"{path}: private feature exposed")

    error_response = client.get(ERROR_CHECK_PATH, follow_redirects=False)
    require(error_response.status_code == 404, "unknown route must remain 404")
    error_body = error_response.get_data(as_text=True)
    error_soup = BeautifulSoup(error_body, "html.parser")
    require(len(error_soup.select("h1")) == 1, "404: expected exactly one H1")
    require(error_soup.select_one("h1").get_text(strip=True) == "ページが見つかりません", "404: unexpected H1")
    require(error_soup.select_one("header.site-header") is not None, "404: shared header missing")
    require(error_soup.select_one("footer") is not None, "404: shared footer missing")
    require(error_soup.select_one('a[href="/tools"]') is not None, "404: tools recovery CTA missing")
    robots = error_soup.select_one('meta[name="robots"]')
    robots_value = (robots.get("content") or "").replace(" ", "").lower() if robots else ""
    require(robots_value == "noindex,follow", "404: expected noindex,follow")
    require(error_soup.select_one('link[rel="canonical"]') is None, "404: canonical must be absent")
    require(not json_ld_documents(error_soup), "404: structured data must be absent")
    require(not error_soup.select(".amazon-single-card, [data-a8-creative-id], .affiliate-slot, .affiliate-cards-section"), "404: affiliate output detected")
    require(error_soup.select_one("ins.adsbygoogle") is None, "404: ad slot detected")
    require(ERROR_CHECK_PATH not in error_body, "404: unknown URL echoed into response")
    require(not any(marker in error_body for marker in ("Traceback (most recent call last)", "werkzeug.debug", "File \"")), "404: stack trace exposed")
    error_id = error_soup.select_one("[data-error-id]")
    require(error_id is not None and re.fullmatch(r"[0-9a-f]{8}", error_id.get_text(strip=True)), "404: invalid error ID")
    for link in error_soup.select("a[href]"):
        href = (link.get("href") or "").strip()
        parsed = urlparse(href)
        if parsed.scheme or parsed.netloc or not parsed.path.startswith("/") or parsed.path.startswith("/static/"):
            continue
        require_valid_internal_target(client, parsed.path, "404")

    print(f"PASS: {len(PUBLIC_HTML_PATHS)} public HTML pages")
    print(f"PASS: {len(INDEXABLE_PATHS)} sitemap/indexable pages")
    print(f"PASS: {len(internal_paths)} internal link targets")
    print("PASS: SEO, schema, AdSense, Amazon, A8, and NO-GO contracts")
    print("PASS: 404 recovery and exact JSON-LD duplicate guards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
