#!/usr/bin/env python3
"""Guard canonical landing section spacing and full-width signals."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
LANDING = (ROOT / "templates/landing.html").read_text(encoding="utf-8")
RELATED = (ROOT / "templates/includes/related_content.html").read_text(encoding="utf-8")
CSS = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    soup = BeautifulSoup(LANDING, "html.parser")
    for selector in (".landing-tools-zone", ".landing-section-surface--policy", ".landing-section-surface--guide"):
        section = soup.select_one(selector)
        require(section is not None, f"{selector}: section missing")
        require(section.select_one(":scope > .landing-section-header") is not None, f"{selector}: canonical header missing")
    policy = soup.select_one(".landing-section-surface--policy")
    require(policy.select_one(":scope > .signal-track") is not None, "policy top signal missing")
    require("signal-track--short" not in RELATED, "related signal must span the content width")
    for token in (
        "--public-section-padding-block",
        "--public-section-padding-inline",
        "--public-section-kicker-gap",
        "--public-section-title-gap",
        "--public-section-content-gap",
    ):
        require(token in CSS, f"{token}: spacing token missing")
    require(".landing-monetization-band__publisher .related-content" in CSS, "related rhythm selector missing")
    require("right: var(--public-section-padding-inline)" in CSS and "left: var(--public-section-padding-inline)" in CSS, "full signal inset contract missing")
    print("PASS: landing Tools, Policy, Guide and Related share canonical header and signal rhythm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
