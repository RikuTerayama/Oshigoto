#!/usr/bin/env python3
"""Verify the shared seven-tool page contract without exercising tool logic."""

from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402


TOOLS = ("pdf", "csv", "image-batch", "image-compress", "image-cleanup", "qr-code", "seo")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app.config["TESTING"] = True
    with app.test_client() as client:
        for tool_id in TOOLS:
            path = f"/tools/{tool_id}"
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
            require(soup.select_one("body.tool-page") is not None, f"{path}: canonical body class missing")
            require(soup.select_one('link[href*="public-system.css"]') is not None, f"{path}: shared stylesheet missing")
            require(soup.select_one("h1") is not None, f"{path}: hero heading missing")
            require(
                soup.select_one(".tool-processing-note, .compress-privacy, .qr-privacy") is not None,
                f"{path}: processing note missing",
            )
            flow = soup.select_one(".tool-flow")
            require(flow is not None, f"{path}: tool flow missing")
            require(flow.select_one("h2") is not None and flow.select_one("h2").get_text(strip=True) == "使う順番", f"{path}: flow heading differs")
            require(len(flow.select(".tool-step-list > li")) == 4, f"{path}: overview must contain exactly four steps")
            require(
                soup.select_one(".tool-workspace, .compress-app, .qr-app, .main-layout") is not None,
                f"{path}: workspace missing",
            )
            require(soup.select_one(".amazon-single-card") is not None, f"{path}: Amazon placement missing")
            require(soup.select_one(".related-tools, .related-tools-grid, .related-content") is not None, f"{path}: related section missing")

    print("PASS: all seven tools use the canonical hero, note, four-step flow, workspace, and related sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
