#!/usr/bin/env python3
"""Static layout contracts for wide, rail and mobile Amazon cards."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CSS = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
COMMON_CSS = (ROOT / "static/css/common.css").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "templates/includes/amazon_single_card.html").read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    css = COMMON_CSS + PUBLIC_CSS
    wide_start = PUBLIC_CSS.find("/* Wide Amazon placements")
    wide_end = PUBLIC_CSS.find(".global-affiliate-rail--tool", wide_start)
    wide_contract = PUBLIC_CSS[wide_start:wide_end]
    require("amazon-single-card--wide .amazon-single-card__body" in PUBLIC_CSS, "wide body layout missing")
    require("grid-template-columns: minmax(0, 1fr) minmax(180px, 220px)" in PUBLIC_CSS, "wide text/CTA columns missing")
    require("max-width: none" in PUBLIC_CSS, "wide content width release missing")
    require("min-width: 180px" in PUBLIC_CSS and "max-width: 220px" in PUBLIC_CSS, "wide CTA width contract missing")
    require("amazon-single-card--rail" in PUBLIC_CSS and "grid-template-columns: 1fr !important" in PUBLIC_CSS, "vertical rail layout missing")
    require("@media (max-width: 640px)" in css and ".amazon-single-card" in css, "mobile stack contract missing")
    require("<br" not in TEMPLATE.lower(), "forced Amazon copy break detected")
    require(wide_start >= 0 and wide_end > wide_start, "wide Amazon contract block missing")
    require("white-space: nowrap" not in wide_contract, "unsafe Amazon nowrap detected")
    print("PASS: Amazon wide uses full text width, rail stays vertical, mobile stacks, forced breaks absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
