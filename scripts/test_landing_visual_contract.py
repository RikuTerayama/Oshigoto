#!/usr/bin/env python3
"""Guard the directional small-tasks-to-ready landing visual."""

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
        response = client.get("/")
        require(response.status_code == 200, "Landing must return 200")
        soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
        visual = soup.select_one(".work-signal-visual")
        require(visual is not None, "directional visual missing")
        require(len(visual.select(".work-signal-stage--inputs > span")) == 5, "five input tasks required")
        require(visual.select_one(".work-signal-stage--process .work-signal-stage__icon") is not None, "central toolbox node missing")
        require(visual.select_one(".work-signal-stage--ready .work-signal-stage__check") is not None, "ready output missing")
        require(visual.select_one(".work-signal-visual__input-line") is not None, "input direction lines missing")
        require(visual.select_one(".work-signal-visual__output-line") is not None, "output direction line missing")
        require(soup.select_one(".work-signal-strip") is not None, "compact mobile signal missing")
        require("WORK SIGNAL" not in response.get_data(as_text=True), "ambiguous WORK SIGNAL copy returned")
        require(not visual.select(".work-signal-node"), "old orbital nodes returned")

    css = (ROOT / "static/css/public-system.css").read_text(encoding="utf-8")
    require("@keyframes work-signal-input" in css and "@keyframes work-signal-output" in css, "directional pulse motion missing")
    print("PASS: Landing communicates five small inputs through Oshigoto to a ready state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
