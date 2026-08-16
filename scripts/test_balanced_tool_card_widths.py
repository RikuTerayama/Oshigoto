#!/usr/bin/env python3
"""Guard equal-width seven-card layouts on Landing and Tools index."""

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
        landing = BeautifulSoup(client.get("/").get_data(as_text=True), "html.parser")
        tools = BeautifulSoup(client.get("/tools").get_data(as_text=True), "html.parser")
        require(len(landing.select(".landing-tool-grid.balanced-seven-grid > .tool-card-v2")) == 7, "Landing must expose seven cards")
        require(len(tools.select(".tools-catalog-grid.balanced-seven-grid > .tool-catalog-card")) == 7, "Tools index must expose seven cards")

    css = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
    require("display: flex" in css and "flex-wrap: wrap" in css and "justify-content: center" in css, "balanced flex contract missing")
    require("calc((100% - (3 * var(--public-gap-md))) / 4)" in css, "desktop equal-width contract missing")
    require("calc((100% - var(--public-gap-md)) / 2)" in css, "tablet equal-width contract missing")
    require("flex-basis: 100%" in css and "width: 100%" in css, "mobile equal-width contract missing")
    require(".landing-page .balanced-seven-grid > *:nth-child" not in css, "Landing card-specific stretch rule returned")
    require(".tools-index-page .balanced-seven-grid > *:nth-child" not in css, "Tools card-specific stretch rule returned")
    print("PASS: Landing and Tools keep seven equal-width cards across desktop, tablet and mobile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
