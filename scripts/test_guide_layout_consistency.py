#!/usr/bin/env python3
"""Verify the shared guide shell across the catalog and seven detail routes."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["AMAZON_AFFILIATE_ENABLED"] = "true"
os.environ["AMAZON_ASSOCIATE_TAG"] = "guide-layout-check-22"
os.environ.setdefault("AFFILIATE_ENABLED", "true")
os.environ.setdefault("AFFILIATE_BANNERS_ENABLED", "true")

from app import app  # noqa: E402


GUIDES = ("pdf", "csv", "image-batch", "image-compress", "image-cleanup", "qr-code", "seo")
RELATED_LINK_GUIDES = set(GUIDES) - {"qr-code"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app.config["TESTING"] = True
    with app.test_client() as client:
        index = BeautifulSoup(client.get("/guide").get_data(as_text=True), "html.parser")
        require(index.select_one("body.guide-index-page") is not None, "/guide: canonical page class missing")
        require(index.select_one(".guide-shell .guide-hero") is not None, "/guide: shared hero missing")
        require(len(index.select(".guide-catalog-grid > .guide-catalog-card")) == 7, "/guide: expected seven guide cards")

        for guide_id in GUIDES:
            path = f"/guide/{guide_id}"
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
            require(soup.select_one("body.guide-detail-page") is not None, f"{path}: canonical body class missing")
            require(soup.select_one(".guide-shell") is not None, f"{path}: shared shell missing")
            require(soup.select_one(".guide-hero h1") is not None, f"{path}: shared hero missing")
            require(soup.select_one('link[href*="public-system.css"]') is not None, f"{path}: shared stylesheet missing")
            require(soup.select_one(f'a[href="/tools/{guide_id}"]') is not None, f"{path}: tool CTA missing")
            require(
                soup.select_one(".guide-section-card") is not None or soup.select_one(".guide-content") is not None,
                f"{path}: canonical information surface missing",
            )
            content = soup.select_one(".page-with-affiliate-rail__content")
            require(content is not None, f"{path}: guide content column missing")
            uncovered_headings = [
                heading.get_text(" ", strip=True)
                for heading in content.select("h2")
                if heading.find_parent(class_="guide-section-card") is None
                and heading.find_parent(class_="related-tools-section") is None
                and heading.find_parent(class_="inline-affiliate-break") is None
            ]
            require(not uncovered_headings, f"{path}: headings outside canonical cards: {uncovered_headings}")

            amazon = content.select_one(".inline-affiliate-break--amazon")
            a8 = content.select_one(".inline-affiliate-break--a8")
            related = content.select_one(".guide-related-links, .related-tools-section")
            require(amazon is not None and a8 is not None and related is not None, f"{path}: lower guide flow incomplete")
            nodes = list(content.descendants)
            require(nodes.index(amazon) < nodes.index(a8) < nodes.index(related), f"{path}: lower guide flow order changed")

            if guide_id in RELATED_LINK_GUIDES:
                related_links = content.select_one(".guide-related-links.guide-section-card")
                require(related_links is not None, f"{path}: shared related-links card missing")
                require(related_links.select_one("h2 + ul") is not None, f"{path}: related links are fragmented")

    css = (ROOT / "static" / "css" / "public-system.css").read_text(encoding="utf-8")
    require(".guide-detail-page .inline-affiliate-break" in css, "guide inline affiliate reset missing")
    require(".guide-detail-page .global-affiliate-rail__a8 { order: 2; }" in css, "guide A8 rail order missing")
    require("overflow: visible;" in css and "max-height: none;" in css, "guide rail scroll reset missing")

    print("PASS: guide index and all seven detail guides use the canonical shared format")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
