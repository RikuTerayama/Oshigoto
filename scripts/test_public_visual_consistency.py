#!/usr/bin/env python3
"""Static contracts for the canonical public visual system."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")


def main() -> int:
    required = (
        "--public-section-gap: clamp(48px, 5vw, 64px)",
        "margin: var(--public-section-gap) auto",
        ".guide-detail-page .guide-section-card",
        "background: transparent",
        ".amazon-single-card__cta",
        "text-align: left",
        "text-align: center",
    )
    for marker in required:
        assert marker in CSS, marker
    assert CSS.count("--public-section-gap") >= 3

    tools = ("pdf", "csv", "image-batch", "image-compress", "image-cleanup", "qr-code", "seo")
    for tool in tools:
        source = (ROOT / f"templates/tools/{tool}.html").read_text(encoding="utf-8")
        assert "tool-flow" in source and "public_system_styles.html" in source, tool
        assert any(value in source for value in ("tool-workspace", "compress-app", "qr-app", "main-layout")), tool

    guides = ("pdf", "csv", "image-batch", "image-compress", "image-cleanup", "qr-code", "seo")
    for guide in guides:
        source = (ROOT / f"templates/guide/{guide}.html").read_text(encoding="utf-8")
        assert "guide-hero" in source and "public_system_styles.html" in source, guide
        assert "guide-section-card" in source or '<div class="container guide-content">' in source, guide
    print("PASS: canonical section spacing, surfaces, and affiliate alignment contracts present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
