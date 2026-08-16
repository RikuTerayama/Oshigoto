#!/usr/bin/env python3
"""Static and rendered contracts for the five-item mobile accordion navigation."""

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
        soup = BeautifulSoup(client.get("/tools/pdf").get_data(as_text=True), "html.parser")
        menu = soup.select_one("[data-mobile-menu-panel]")
        require(menu is not None, "mobile menu panel missing")
        labels = [node.get_text(" ", strip=True) for node in menu.select(":scope > a, :scope > .site-nav__dropdown-wrap > button")]
        require(labels == ["ホーム", "ツール ▾", "ガイド ▾", "リソース ▾", "企業向け"], f"top-level menu changed: {labels}")
        triggers = menu.select("[data-mobile-accordion-trigger]")
        require(len(triggers) == 3, "Tools, Guide and Resources must be accordions")
        for trigger in triggers:
            require(trigger.get("aria-expanded") == "false", "accordion must initialize closed")
            require(soup.select_one(f"#{trigger.get('aria-controls')}") is not None, "accordion panel missing")

    nav = (ROOT / "templates/includes/header_v2.html").read_text(encoding="utf-8")
    css = (ROOT / "static/css/common.css").read_text(encoding="utf-8")
    css += (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
    require("resetMobileAccordions" in nav and "keydown" in nav and "Escape" in nav, "accordion close/reset contract missing")
    require("max-height: calc(100dvh" in css, "small-height menu max-height missing")
    require("overflow-y: auto !important" in css, "mobile menu must be scrollable")
    require("overscroll-behavior: contain" in css, "menu overscroll guard missing")
    require("flex-wrap: nowrap !important" in css, "mobile menu must remain one vertical column")
    require('[data-mobile-accordion-panel][hidden]' in css, "hidden accordion panel override missing")
    print("PASS: five top-level items, three accordions and scrollable mobile panel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
