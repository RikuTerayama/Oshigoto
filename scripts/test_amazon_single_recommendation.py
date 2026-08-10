#!/usr/bin/env python3
"""Regression checks for route-managed Amazon recommendation limits."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["AMAZON_AFFILIATE_ENABLED"] = "true"
os.environ["AMAZON_ASSOCIATE_TAG"] = "jobcanauto-22"
os.environ.setdefault("AFFILIATE_ENABLED", "true")
os.environ.setdefault("AFFILIATE_TEXTLINKS_ENABLED", "true")
os.environ.setdefault("AFFILIATE_BANNERS_ENABLED", "true")

import app as app_module  # noqa: E402
import lib.amazon_creators as creators  # noqa: E402
from lib.amazon_affiliate_map import (  # noqa: E402
    AMAZON_ELIGIBLE_EXACT_PATHS,
    AMAZON_HARD_EXCLUDED_PATHS,
    AMAZON_HIGH_CONTENT_EXACT_PATHS,
    AMAZON_ICON_ALLOWLIST,
    AMAZON_THEME_ICON_MAP,
    AMAZON_THEME_POOL,
    VISIBLE_AMAZON_MAX_PER_PAGE,
    get_amazon_page_policy,
    get_amazon_visible_limit,
)


ARTICLE_PATH = "/blog/excel-format-mistakes-and-design"
AMAZON_URL_RE = re.compile(r'https://www\.amazon\.co\.jp/[^"\'<> ]+')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build(path: str, page_type: str = "tool") -> dict | None:
    return creators.build_single_amazon_recommendation(path, page_type, slot_id="amazon-single")


def main() -> int:
    require(VISIBLE_AMAZON_MAX_PER_PAGE == 1, "visible Amazon maximum must be one")
    require(get_amazon_visible_limit("/") == 2, "landing Amazon maximum must be two")
    require(get_amazon_visible_limit("/tools") == 2, "tools Amazon maximum must be two")
    require(get_amazon_visible_limit("/guide/pdf") == 2, "long-form Amazon maximum must be two")
    require(get_amazon_visible_limit("/faq") == 1, "medium-page Amazon maximum must remain one")
    require(any(theme.get("enabled") for theme in AMAZON_THEME_POOL), "enabled theme pool required")
    require(set(AMAZON_THEME_ICON_MAP.values()) <= AMAZON_ICON_ALLOWLIST, "theme icons must be allowlisted")
    require(get_amazon_page_policy("/tools/pdf") is not None, "eligible policy missing")
    require(get_amazon_page_policy("/business") is None, "business must be excluded")
    require(get_amazon_page_policy("not-a-path") is None, "invalid path must be excluded")

    original_bucket = creators._rotation_bucket_key
    try:
        creators._rotation_bucket_key = lambda: "daily:2026-08-08"
        first = build("/tools/pdf")
        second = build("/tools/pdf")
        require(first == second and first is not None, "same day/path selection must be deterministic")
        require(first["icon_key"] in AMAZON_ICON_ALLOWLIST, "single icon must be allowlisted")
        require(first.get("image_url", "") == "", "product images are forbidden")
        require(not any(key in first for key in ("price", "rating", "review_count", "stock")), "product commerce metadata is forbidden")
        parsed = urlparse(first["url"])
        require(parse_qs(parsed.query).get("tag") == ["jobcanauto-22"], "associate tag must appear exactly once")

        landing_primary = build("/", "landing")
        landing_secondary = creators.build_landing_secondary_amazon_recommendation(
            "/",
            "landing",
            exclude_theme_ids=[landing_primary["theme_id"]],
            exclude_urls=[landing_primary["url"]],
        )
        require(landing_secondary is not None, "landing secondary recommendation missing")
        require(landing_secondary["theme_id"] != landing_primary["theme_id"], "landing themes must differ")
        require(landing_secondary["url"] != landing_primary["url"], "landing URLs must differ")
        require(landing_secondary["placement"] == "landing-lower-amazon", "secondary placement mismatch")

        tools_primary = build("/tools", "tool_index")
        tools_secondary = creators.build_secondary_amazon_recommendation(
            "/tools",
            "tool_index",
            exclude_theme_ids=[tools_primary["theme_id"]],
            exclude_urls=[tools_primary["url"]],
        )
        require(tools_secondary is not None, "tools secondary recommendation missing")
        require(tools_secondary["theme_id"] != tools_primary["theme_id"], "tools themes must differ")
        require(tools_secondary["url"] != tools_primary["url"], "tools URLs must differ")
        require(tools_secondary["placement"].endswith("-secondary"), "tools secondary placement mismatch")

        original_icon = AMAZON_THEME_ICON_MAP.get(first["theme_id"])
        AMAZON_THEME_ICON_MAP[first["theme_id"]] = "unknown-icon"
        try:
            fallback_icon_card = build("/tools/pdf")
            require(
                fallback_icon_card is not None and fallback_icon_card["icon_key"] == "document",
                "unknown theme icons must fall back to the neutral document icon",
            )
        finally:
            if original_icon is None:
                AMAZON_THEME_ICON_MAP.pop(first["theme_id"], None)
            else:
                AMAZON_THEME_ICON_MAP[first["theme_id"]] = original_icon

        checked_paths = ("/", "/tools", "/tools/pdf", "/tools/image-compress", "/tools/qr-code")
        current_day_candidates = [build(path, "tool") for path in checked_paths]
        rotated = False
        for day in range(9, 32):
            creators._rotation_bucket_key = lambda day=day: f"daily:2026-08-{day:02d}"
            candidates = [build(path, "tool") for path in checked_paths]
            if any(a and b and a["theme_id"] != b["theme_id"] for a, b in zip(current_day_candidates, candidates)):
                rotated = True
                break
        require(
            rotated,
            "daily rotation must change at least one eligible route across the checked buckets",
        )
    finally:
        creators._rotation_bucket_key = original_bucket

    original_tag = os.environ.pop("AMAZON_ASSOCIATE_TAG")
    try:
        require(build("/tools/pdf") is None, "missing tag must fail closed")
    finally:
        os.environ["AMAZON_ASSOCIATE_TAG"] = original_tag

    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    eligible_paths = sorted(AMAZON_ELIGIBLE_EXACT_PATHS) + [ARTICLE_PATH]
    for path in eligible_paths:
        response = client.get(path)
        require(response.status_code == 200, f"{path}: expected 200")
        set_cookie_headers = response.headers.getlist("Set-Cookie")
        require(
            not any("amazon_recent_history" in value for value in set_cookie_headers),
            f"{path}: Amazon recommendation must not create a history cookie",
        )
        html = response.get_data(as_text=True)
        urls = AMAZON_URL_RE.findall(html)
        maximum = get_amazon_visible_limit(path)
        require(1 <= len(urls) <= maximum, f"{path}: expected 1..{maximum} Amazon URLs, got {len(urls)}")
        require(len(set(urls)) == len(urls), f"{path}: duplicate Amazon URL")
        require(len(re.findall(r'<section\s+class="amazon-single-card(?:\s|\")', html)) == len(urls), f"{path}: card count mismatch")
        require(html.count('class="amazon-single-card__cta"') == len(urls), f"{path}: CTA count mismatch")
        require(html.count('class="amazon-single-card__icon"') == len(urls), f"{path}: icon count mismatch")
        require('class="amazon-recommendation-grid"' not in html, f"{path}: legacy grid rendered")
        require('class="affiliate-side-box"' not in html, f"{path}: legacy side box rendered")
        require("amazon-recommendation-card__media" not in html, f"{path}: product media rendered")
        require("PR / Amazon affiliate" in html, f"{path}: PR label missing")
        amazon_index = html.find('class="amazon-single-card"')
        a8_index = html.find('data-a8-creative-id="')
        if a8_index >= 0:
            require(abs(a8_index - amazon_index) > 500, f"{path}: Amazon and A8 are too close in DOM")

    for path in sorted(AMAZON_HARD_EXCLUDED_PATHS):
        html = client.get(path).get_data(as_text=True)
        require(not AMAZON_URL_RE.findall(html), f"{path}: Amazon URL must be absent")
        require('class="amazon-single-card"' not in html, f"{path}: Amazon wrapper must be absent")

    source = (ROOT / "app.py").read_text(encoding="utf-8")
    context_start = source.index("def inject_env_vars")
    context_source = source[context_start:source.index("# P0-1 SEO", context_start)]
    require("get_amazon_recommendations(" not in context_source, "page rendering must not call Creators API")
    require("_prepare_recent_affiliate_history_cookie(" not in context_source, "single recommendation must not write history")

    print(f"PASS: {len(eligible_paths)} eligible routes respect route-managed Amazon limits")
    print(f"PASS: {len(AMAZON_HIGH_CONTENT_EXACT_PATHS)} long-form routes allow at most two recommendations")
    print(f"PASS: {len(AMAZON_HARD_EXCLUDED_PATHS)} excluded routes render none")
    print("PASS: deterministic rotation, tag handling, icon allowlist, A8 spacing, no page-render API call")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
