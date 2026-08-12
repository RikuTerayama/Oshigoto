#!/usr/bin/env python3
"""Verify the canonical connector-free tool flow and secondary CTA contract."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
TOOLS = ("pdf", "csv", "image-batch", "image-compress", "image-cleanup", "qr-code", "seo")


def main() -> int:
    assert ".tool-step-list > li:not(:last-child)::after" not in CSS
    assert ".tool-kb-anchor-link > a" in CSS
    assert "min-height: 44px" in CSS

    for tool in TOOLS:
        source = (ROOT / f"templates/tools/{tool}.html").read_text(encoding="utf-8")
        soup = BeautifulSoup(source, "html.parser")
        flow = soup.select_one(".tool-flow")
        assert flow is not None, f"{tool}: flow missing"
        assert flow.find_parent(class_="tool-intro-layout__content") is not None, f"{tool}: flow outside main intro column"
        assert len(flow.select(".tool-step-list > li")) == 4, f"{tool}: expected four steps"
        assert "position: absolute" not in (flow.get("style") or ""), f"{tool}: absolute flow positioning"

    cta_partial = (ROOT / "templates/includes/tool_kb_cta.html").read_text(encoding="utf-8")
    assert "tool-kb-anchor-link" in cta_partial and "href=" in cta_partial
    print("PASS: all seven tool flows are connector-free inside the main column with a 44px CTA contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
