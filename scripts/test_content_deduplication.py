#!/usr/bin/env python3
"""Guard the one-purpose-one-component contract on public tool pages."""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["AMAZON_AFFILIATE_ENABLED"] = "true"
os.environ["AMAZON_ASSOCIATE_TAG"] = "dedupe-check-22"

from app import app  # noqa: E402


TOOLS = ("pdf", "csv", "image-batch", "image-compress", "image-cleanup", "qr-code", "seo")
PUBLIC_AUDIT_PATHS = (
    "/",
    "/tools",
    *(f"/tools/{slug}" for slug in TOOLS),
    "/guide",
    *(f"/guide/{slug}" for slug in TOOLS),
    "/faq",
    "/glossary",
    "/best-practices",
    "/blog",
    "/blog/excel-format-mistakes-and-design",
    "/about",
    "/business",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    template_tree = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "templates").rglob("*.html"))
    require("tool_kb_cta" not in template_tree, "tool_kb_cta reference remains")
    require("tool_content_blocks" not in template_tree, "tool_content_blocks reference remains")
    require("tool_flow_side_box" not in template_tree, "tool_flow_side_box reference remains")

    app.config["TESTING"] = True
    with app.test_client() as client:
        for path in PUBLIC_AUDIT_PATHS:
            response = client.get(path)
            require(response.status_code == 200, f"{path}: public audit expected 200")
            soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
            main = soup.select_one("main, .guide-shell")
            require(main is not None, f"{path}: public content root missing")
            headings = [heading.get_text(" ", strip=True) for heading in main.select("h1, h2")]
            duplicate_headings = [text for text, count in Counter(headings).items() if text and count > 1]
            require(not duplicate_headings, f"{path}: duplicate main headings {duplicate_headings}")
            action_pairs = [
                (link.get_text(" ", strip=True), link.get("href"))
                for link in main.select("a.btn[href], a.button[href], a.link-button[href]")
            ]
            duplicate_actions = [pair for pair, count in Counter(action_pairs).items() if pair[0] and count > 1]
            require(not duplicate_actions, f"{path}: duplicate CTA targets {duplicate_actions}")
            for section in soup.select(".related-tools-section, .related-content"):
                hrefs = [link.get("href") for link in section.select("a[href]")]
                require(len(hrefs) == len(set(hrefs)), f"{path}: duplicate href in related section")

        for tool in TOOLS:
            path = f"/tools/{tool}"
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
            require(len(soup.select(".global-affiliate-rail--tool")) == 1, f"{path}: primary rail count must be one")
            require(not soup.select(".page-sidebar, .sticky-side-box"), f"{path}: legacy sidebar returned")
            require("使い方・FAQを見る" not in soup.get_text(" ", strip=True), f"{path}: duplicate CTA returned")
            section = soup.select_one(".related-tools-section")
            require(section is not None, f"{path}: related tools missing")
            kicker = section.select_one(".section-kicker")
            heading = section.select_one("h2")
            require(kicker and heading and kicker.get_text(strip=True) != heading.get_text(strip=True), f"{path}: duplicate related heading")
            cards = section.select(".related-tools-card")
            require(1 <= len(cards) <= 3, f"{path}: related tools must contain one to three cards")
            hrefs = [link.get("href") for link in section.select("a[href]")]
            require(path not in hrefs, f"{path}: current tool appears in related tools")
            require(len(hrefs) == len(set(hrefs)), f"{path}: duplicate related href")

    print("PASS: 24 public routes are deduplicated; tool pages keep one rail, flow and related set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
