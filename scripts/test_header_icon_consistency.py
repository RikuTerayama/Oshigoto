#!/usr/bin/env python3
"""Ensure every primary navigation section receives one shared SVG icon."""

import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402
from lib.nav import get_nav_sections, get_nav_sections_fallback  # noqa: E402


EXPECTED = ("home", "tools", "guide", "resource", "business")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_rendered_header(sections: list[dict], label: str) -> None:
    with app.test_request_context("/glossary"):
        html = app.jinja_env.get_template("includes/header_v2.html").render(
            nav_sections=sections,
            affiliate_top_slot_mode=None,
            affiliate_top_slot_id=None,
        )
    soup = BeautifulSoup(html, "html.parser")

    for section_id in EXPECTED:
        item = soup.select_one(f"#nav-{section_id}")
        require(item is not None, f"{label}: nav-{section_id} is missing")
        icons = item.select("svg.site-nav__icon[aria-hidden='true']")
        require(len(icons) == 1, f"{label}: nav-{section_id} must have one decorative SVG icon")
        require(icons[0].get("width") == "18", f"{label}: nav-{section_id} icon must be 18px")

    resource = soup.select_one("button#nav-resource")
    require(resource is not None, f"{label}: resource must remain a dropdown trigger")
    require(resource.get("aria-haspopup") == "true", f"{label}: resource aria-haspopup regression")
    require(resource.get("aria-expanded") == "false", f"{label}: resource aria-expanded regression")

    business = soup.select_one("a#nav-business")
    require(business is not None, f"{label}: business must remain a direct link")
    require(business.get("href") == "/business", f"{label}: business href regression")


def main() -> int:
    check_rendered_header(get_nav_sections(), "primary")
    check_rendered_header(get_nav_sections_fallback(), "fallback")
    print("OK: header icon consistency passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
