#!/usr/bin/env python3
"""Regression checks for the unified public theme and vertical tool steps."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["AMAZON_AFFILIATE_ENABLED"] = "true"
os.environ["AMAZON_ASSOCIATE_TAG"] = "theme-check-22"
os.environ.setdefault("AFFILIATE_ENABLED", "true")
os.environ.setdefault("AFFILIATE_BANNERS_ENABLED", "true")

from app import app  # noqa: E402


HEADER_ROUTES = (
    "/",
    "/tools",
    "/tools/pdf",
    "/tools/csv",
    "/tools/image-compress",
    "/tools/qr-code",
    "/guide",
    "/guide/pdf",
    "/faq",
    "/business",
    "/privacy",
)
STEP_ROUTES = (
    "/tools/pdf",
    "/tools/csv",
    "/tools/image-batch",
    "/tools/image-cleanup",
    "/tools/seo",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app.config["TESTING"] = True
    client = app.test_client()

    for path in HEADER_ROUTES:
        response = client.get(path, follow_redirects=False)
        require(response.status_code == 200, f"{path}: expected 200")
        soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
        require(len(soup.select(".site-header")) == 1, f"{path}: shared header missing or duplicated")

    not_found = client.get("/missing-public-theme-check", follow_redirects=False)
    require(not_found.status_code == 404, "404 route contract changed")
    require(len(BeautifulSoup(not_found.get_data(as_text=True), "html.parser").select(".site-header")) == 1, "404 header missing")

    for path in STEP_ROUTES:
        soup = BeautifulSoup(client.get(path).get_data(as_text=True), "html.parser")
        steps = soup.select(".tool-step-list > li")
        require(len(steps) >= 3, f"{path}: tool instructions missing")

    css = (ROOT / "static" / "css" / "common.css").read_text(encoding="utf-8")
    require(".landing-page .site-header" not in css, "body-class-dependent header rule returned")
    require(".landing-page .site-nav" not in css, "body-class-dependent nav rule returned")
    require("background: rgba(255, 252, 246, 0.96);" in css, "paper header background missing")
    require("background: #0e7c7b;" in css, "Amazon CTA background missing")
    require(".amazon-single-card .amazon-single-card__cta:visited" in css, "visited CTA state missing")
    require("background: #095c5b;" in css, "Amazon hover/focus background missing")
    require("background: #eef1ec;" in css, "sage parent surface missing")
    require("background: #fffdf8;" in css, "paper clickable card surface missing")

    step_blocks = re.findall(r"[^{}]*tool-step-list[^{}]*\{([^{}]*)\}", css)
    require(step_blocks, "tool step CSS missing")
    require(
        not any(re.search(r"grid-template-columns\s*:\s*repeat\(", block) for block in step_blocks),
        "horizontal tool step columns returned",
    )

    print(f"PASS: {len(HEADER_ROUTES)} public routes and 404 use the shared header")
    print(f"PASS: {len(STEP_ROUTES)} tool pages retain vertical instructions")
    print("PASS: Amazon CTA and resource card palette contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
