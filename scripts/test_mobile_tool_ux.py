#!/usr/bin/env python3
"""Contract checks for task-first tool detail markup."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["AMAZON_AFFILIATE_ENABLED"] = "true"
os.environ["AMAZON_ASSOCIATE_TAG"] = "mobile-tool-check-22"
os.environ.setdefault("AFFILIATE_ENABLED", "true")
os.environ.setdefault("AFFILIATE_BANNERS_ENABLED", "true")

from app import app  # noqa: E402


TOOL_PATHS = (
    "/tools/pdf",
    "/tools/csv",
    "/tools/image-batch",
    "/tools/image-compress",
    "/tools/image-cleanup",
    "/tools/qr-code",
    "/tools/seo",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app.config["TESTING"] = True
    with app.test_client() as client:
        for path in TOOL_PATHS:
            response = client.get(path)
            require(response.status_code == 200, f"{path}: expected 200")
            soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
            hero = soup.select_one("[data-tool-hero]")
            flow = soup.select_one("[data-tool-flow]")
            workspace = soup.select_one("[data-tool-workspace]")
            affiliate = soup.select_one("[data-tool-affiliate]")
            require(all((hero, flow, workspace, affiliate)), f"{path}: canonical marker missing")
            require(
                hero.sourceline < flow.sourceline < workspace.sourceline < affiliate.sourceline,
                f"{path}: expected hero, flow, workspace, affiliate DOM order",
            )
            require(not affiliate.select(".global-affiliate-rail__publisher"), f"{path}: publisher guide rendered")
            require(not soup.select_one("[data-tool-affiliate] ~ [data-tool-workspace]"), f"{path}: workspace follows affiliate")
            require(len(flow.select(".tool-step-list > li")) == 4, f"{path}: expected four canonical steps")

    css = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
    require("grid-template-columns: 37px minmax(0, 1fr) !important" in css, "desktop step size missing")
    require("grid-template-columns: 33px minmax(0, 1fr) !important" in css, "mobile step size missing")
    require("connector" not in css.lower(), "connector line must not return")
    print(f"PASS: {len(TOOL_PATHS)} tool routes keep workspace before affiliate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
