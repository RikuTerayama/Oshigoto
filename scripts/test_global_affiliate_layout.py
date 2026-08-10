#!/usr/bin/env python3
"""Regression checks for the global top rail and safe inline affiliate layout."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["AMAZON_AFFILIATE_ENABLED"] = "true"
os.environ["AMAZON_ASSOCIATE_TAG"] = "layout-check-22"
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


ARTICLE_PATH = "/blog/excel-format-mistakes-and-design"
TOOL_PATHS = (
    "/tools/pdf",
    "/tools/csv",
    "/tools/image-batch",
    "/tools/image-compress",
    "/tools/image-cleanup",
    "/tools/qr-code",
    "/tools/seo",
)
REMOVED_LEADS = (
    "作業環境を見直すときに確認できます。",
    "必要なときだけ確認できます。",
    "作業内容を確認したあとに、必要な場合だけご覧ください。",
    "ページの内容を確認したあとに、必要な場合だけご覧ください。",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app.config["TESTING"] = True
    client = app.test_client()
    eligible = sorted(set(AMAZON_ELIGIBLE_EXACT_PATHS) | set(A8_ELIGIBLE_EXACT_PATHS)) + [ARTICLE_PATH]

    for path in eligible:
        response = client.get(path, follow_redirects=False)
        require(response.status_code == 200, f"{path}: expected 200")
        html = response.get_data(as_text=True)
        soup = BeautifulSoup(html, "html.parser")
        require(len(soup.select("[data-affiliate-primary-rail]")) == 1, f"{path}: primary rail missing")
        rail = soup.select_one("[data-affiliate-primary-rail]")
        amazon = rail.select_one(".global-affiliate-rail__amazon")
        publisher = rail.select_one(".global-affiliate-rail__publisher")
        a8 = rail.select_one(".global-affiliate-rail__a8")
        require(amazon is not None and publisher is not None and a8 is not None, f"{path}: incomplete primary rail")
        require(amazon.sourceline <= publisher.sourceline <= a8.sourceline, f"{path}: rail order changed")

        amazon_cards = soup.select(".amazon-single-card")
        a8_cards = soup.select(".a8-creative-slot")
        require(1 <= len(amazon_cards) <= get_amazon_visible_limit(path), f"{path}: Amazon cap")
        require(1 <= len(a8_cards) <= get_a8_visible_limit(path), f"{path}: A8 cap")
        for card in amazon_cards:
            href = card.select_one(".amazon-single-card__cta").get("href", "")
            require(parse_qs(urlparse(href).query).get("tag") == ["layout-check-22"], f"{path}: bad Amazon tag")
        for phrase in REMOVED_LEADS:
            require(phrase not in html, f"{path}: retired affiliate lead exposed")
        for header in soup.select(".affiliate-spotlight__header"):
            require(not header.select("p:not(.affiliate-spotlight__kicker)"), f"{path}: related-services lead paragraph rendered")

    for path in sorted(set(AMAZON_HARD_EXCLUDED_PATHS) | set(A8_HARD_EXCLUDED_PATHS)):
        soup = BeautifulSoup(client.get(path).get_data(as_text=True), "html.parser")
        require(not soup.select("[data-affiliate-primary-rail], .amazon-single-card, .a8-creative-slot"), f"{path}: excluded affiliate")

    landing = BeautifulSoup(client.get("/").get_data(as_text=True), "html.parser")
    tools = BeautifulSoup(client.get("/tools").get_data(as_text=True), "html.parser")
    for selector, soup in ((".landing-tools-zone", landing), (".tools-catalog-panel", tools)):
        panel = soup.select_one(selector)
        require(panel is not None, f"{selector}: panel missing")
        require(not panel.select(".amazon-single-card, .a8-creative-slot, [data-affiliate-primary-rail]"), f"{selector}: affiliate inside panel")

    for path in TOOL_PATHS:
        soup = BeautifulSoup(client.get(path).get_data(as_text=True), "html.parser")
        workspace = soup.select_one(".tool-workspace, .compress-app, .qr-app, .main-layout")
        rail = soup.select_one("[data-affiliate-primary-rail]")
        require(workspace is not None and rail is not None, f"{path}: workspace or rail missing")
        require(workspace.find_parent(class_="tool-intro-layout") is None, f"{path}: workspace entered rail boundary")
        require(not workspace.select(".amazon-single-card, .a8-creative-slot"), f"{path}: affiliate inside controls")

    css = (ROOT / "static" / "css" / "common.css").read_text(encoding="utf-8")
    require("@media (min-width: 1280px) and (min-height: 800px)" in css, "sticky guard missing")
    require("@media (max-width: 1239px)" in css, "mobile/tablet flow guard missing")
    require(".amazon-single-card .amazon-single-card__cta:visited" in css, "visited CTA rule missing")
    require("color: #fff;" in css, "white CTA text rule missing")

    print(f"PASS: {len(eligible)} eligible routes use one primary rail")
    print(f"PASS: {len(TOOL_PATHS)} tool workspaces remain outside affiliate rail boundaries")
    print("PASS: clean landing/tools panels, route caps, exclusions, lead removal, CTA rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
