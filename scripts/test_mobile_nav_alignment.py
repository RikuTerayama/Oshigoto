#!/usr/bin/env python3
"""Rendered and CSS contracts for centered mobile top-level navigation."""

from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app.config["TESTING"] = True
    with app.test_client() as client:
        soup = BeautifulSoup(client.get("/").get_data(as_text=True), "html.parser")
        menu = soup.select_one("[data-mobile-menu-panel]")
        require(menu is not None, "mobile menu missing")
        top_level = menu.select(":scope > a, :scope > .site-nav__dropdown-wrap > button")
        labels = [item.get_text(" ", strip=True).replace(" ▾", "") for item in top_level]
        require(labels == ["ホーム", "ツール", "ガイド", "リソース", "企業向け"], f"top-level labels changed: {labels}")
        require(len(menu.select("[data-mobile-accordion-trigger]")) == 3, "accordion triggers changed")

    css = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
    start = css.rfind("/* Final cascade")
    contract = css[start:]
    require("justify-content: center !important" in contract, "top-level center alignment missing")
    require("min-height: 48px !important" in contract, "top-level touch target missing")
    require("text-align: center !important" in contract, "top-level text alignment missing")
    require("text-align: left !important" in contract, "submenu left alignment missing")
    require("justify-content: flex-start !important" in contract, "submenu row alignment missing")
    print("PASS: five mobile top-level rows centered; submenus remain left aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
