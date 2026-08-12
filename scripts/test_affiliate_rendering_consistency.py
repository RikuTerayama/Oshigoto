#!/usr/bin/env python3
"""Verify shared A8 rendering contracts before client-side hydration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AFFILIATE_ENABLED", "true")
os.environ.setdefault("AFFILIATE_BANNERS_ENABLED", "true")
os.environ.setdefault("AMAZON_AFFILIATE_ENABLED", "true")
os.environ.setdefault("AMAZON_ASSOCIATE_TAG", "affiliate-render-check-22")

from app import app  # noqa: E402
from lib.a8_affiliate_catalog import (  # noqa: E402
    A8_ELIGIBLE_EXACT_PATHS,
    A8_HARD_EXCLUDED_PATHS,
    get_a8_visible_limit,
)

WIDGET_SCRIPT = (ROOT / "static/js/affiliate-widgets.js").read_text(encoding="utf-8")
PUBLIC_CSS = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    require('a[href^="https://px.a8.net/"]' in WIDGET_SCRIPT, "hydration must verify an A8 destination")
    require('img[width="1"][height="1"]' in WIDGET_SCRIPT, "hydration must verify the A8 tracker")
    require("slot.removeAttribute('hidden')" in WIDGET_SCRIPT, "valid creatives must reveal their slot")
    require("mount.replaceChildren()" in WIDGET_SCRIPT, "invalid creatives must fail closed")
    require(".affiliate-spotlight__header" in PUBLIC_CSS, "shared affiliate heading alignment missing")
    require("text-align: center !important" in PUBLIC_CSS, "affiliate heading alignment must win legacy rules")

    matrix = []
    app.config["TESTING"] = True
    with app.test_client() as client:
        for path in sorted(A8_ELIGIBLE_EXACT_PATHS):
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
            slots = soup.select("[data-a8-responsive-slot]")
            limit = get_a8_visible_limit(path)
            require(0 < len(slots) <= limit, f"{path}: A8 slot count {len(slots)} exceeds {limit}")
            require(soup.select_one('script[src*="affiliate-widgets.js"]') is not None, f"{path}: hydration script missing")
            require("v=" in soup.select_one('script[src*="affiliate-widgets.js"]')["src"], f"{path}: hydration cache buster missing")
            creative_ids = []
            for slot in slots:
                require(slot.has_attr("hidden") and slot.has_attr("data-a8-pending"), f"{path}: slot must fail closed")
                require(slot.select_one("[data-a8-responsive-mount]") is not None, f"{path}: mount missing")
                mobile = slot.select_one("template[data-a8-mobile-template]")
                require(mobile is not None, f"{path}: mobile template missing")
                creative_ids.append(mobile.get("data-a8-creative-id"))
                require(mobile.select_one('a[href^="https://px.a8.net/"]') is not None, f"{path}: A8 anchor missing")
                require(mobile.select_one('img[width="1"][height="1"]') is not None, f"{path}: tracker missing")
            require(len(creative_ids) == len(set(creative_ids)), f"{path}: primary and secondary creative duplicated")
            matrix.append((path, len(slots), creative_ids))

        for path in sorted(A8_HARD_EXCLUDED_PATHS):
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
            require(not soup.select("[data-a8-responsive-slot], .a8-creative-slot__label"), f"{path}: excluded A8 output")

        response = client.get("/definitely-not-a-route")
        require(response.status_code == 404, "404 route missing")
        soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
        require(not soup.select("[data-a8-responsive-slot], .a8-creative-slot__label"), "404: affiliate output detected")

    print(f"PASS: shared A8 fail-closed rendering matrix verified for {len(matrix)} eligible paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
