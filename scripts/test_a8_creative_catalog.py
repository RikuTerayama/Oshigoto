#!/usr/bin/env python3
"""Regression tests for the exact A8 creative catalog and page policy."""

import copy
import hashlib
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.a8_affiliate_catalog import (  # noqa: E402
    A8_AFTER_EXPLANATION_PATHS,
    A8_ELIGIBLE_EXACT_PATHS,
    A8_HARD_EXCLUDED_PATHS,
    A8_HIGH_CONTENT_EXACT_PATHS,
    ALLOWED_A8_TEMPLATES,
    TEMPLATE_ROOT,
    VISIBLE_A8_MAX_PER_PAGE,
    a8_can_render_placement,
    get_a8_allowed_placements,
    get_a8_placement,
    get_a8_visible_limit,
    load_a8_creative_catalog,
    select_a8_creative,
)


EXPECTED_PARAMETERS = {
    "a8-01": ("4B3SMZ+5RSAWI+5B0Y+63WO1", "260517563349", "s00000024757001026000"),
    "a8-02": ("4B3SMZ+5RSAWI+5B0Y+5ZU29", "260517563349", "s00000024757001007000"),
    "a8-03": ("4B3SMZ+61B8KY+5O7E+BXYE9", "260517563365", "s00000026465002006000"),
    "a8-04": ("4AZMKE+EF60AA+5OEW+5ZEMP", "260323070872", "s00000026492001005000"),
    "a8-05": ("4AZMKE+EF60AA+5OEW+601S1", "260323070872", "s00000026492001008000"),
}


def _assert_catalog():
    creatives = load_a8_creative_catalog()
    assert len(creatives) == 5
    assert VISIBLE_A8_MAX_PER_PAGE == 1
    assert get_a8_visible_limit("/") == 2
    assert get_a8_visible_limit("/tools") == 2
    assert get_a8_visible_limit("/guide/pdf") == 2
    assert get_a8_visible_limit("/faq") == 1
    assert {item["id"] for item in creatives} == set(EXPECTED_PARAMETERS)
    assert {item["template"] for item in creatives} == ALLOWED_A8_TEMPLATES
    assert all(item["enabled"] is True and item["weight"] == 1 for item in creatives)

    for item in creatives:
        template_bytes = (TEMPLATE_ROOT / item["template"]).read_bytes()
        template = template_bytes.decode("utf-8")
        a8mat, aid, mid = EXPECTED_PARAMETERS[item["id"]]
        assert item["sha256"] == hashlib.sha256(template_bytes).hexdigest()
        assert template.count("https://px.a8.net/svt/ejp") == 1
        assert f"a8mat={a8mat}" in template
        assert f"aid={aid}" in template
        assert "wid=001" in template and "eno=01" in template
        assert f"mid={mid}" in template and "mc=1" in template
        assert 'width="300" height="250" alt=""' in template
        assert 'width="1" height="1"' in template
        assert 'rel="nofollow"' in template
        assert "sponsored" not in template


def _assert_selection():
    creatives = load_a8_creative_catalog()
    selected = select_a8_creative("/tools/pdf", "2026-08-08", creatives)
    assert selected == select_a8_creative("/tools/pdf", "2026-08-08", creatives)
    assert selected["id"] == "a8-02"
    assert selected["placement"] == "tool-after-explanation"
    assert a8_can_render_placement("/tools/pdf", "tool-after-explanation")
    assert not a8_can_render_placement("/tools/pdf", "global-footer-a8")
    assert get_a8_allowed_placements("/") == ("top-lower-a8", "landing-lower-a8")
    assert get_a8_allowed_placements("/tools") == ("tools-primary-a8", "tools-lower-a8")
    assert get_a8_allowed_placements("/tools/pdf") == ("tool-after-explanation", "content-lower-a8")
    landing_primary = select_a8_creative("/", "2026-08-08", creatives)
    landing_secondary = select_a8_creative(
        "/",
        "2026-08-08",
        creatives,
        placement="landing-lower-a8",
        exclude_creative_ids=[landing_primary["id"]],
    )
    assert landing_secondary is not None
    assert landing_secondary["id"] != landing_primary["id"]
    assert landing_secondary["placement"] == "landing-lower-a8"

    seen = set()
    start = date(2026, 1, 1)
    for offset in range(90):
        key = (start + timedelta(days=offset)).isoformat()
        for path in A8_ELIGIBLE_EXACT_PATHS:
            item = select_a8_creative(path, key, creatives)
            assert item is not None
            seen.add(item["id"])
    assert seen == set(EXPECTED_PARAMETERS)
    assert any(
        select_a8_creative(path, "2026-08-08", creatives)["id"]
        != select_a8_creative(path, "2026-08-09", creatives)["id"]
        for path in A8_ELIGIBLE_EXACT_PATHS
    )

    modified = copy.deepcopy(creatives)
    modified[0]["enabled"] = False
    modified[1]["weight"] = 0
    for offset in range(30):
        item = select_a8_creative("/", (start + timedelta(days=offset)).isoformat(), modified)
        assert item is not None
        assert item["id"] not in {"a8-01", "a8-02"}
    single = copy.deepcopy(creatives)
    for item in single:
        item["enabled"] = item["id"] == "a8-03"
    assert select_a8_creative("/", "2026-08-08", single)["id"] == "a8-03"
    for item in single:
        item["enabled"] = False
    assert select_a8_creative("/", "2026-08-08", single) is None
    assert select_a8_creative("/", "bad-date", creatives) is None
    assert select_a8_creative("/", "2026-08-08", []) is None
    for path in A8_HARD_EXCLUDED_PATHS:
        assert select_a8_creative(path, "2026-08-08", creatives) is None
    assert select_a8_creative("/api/status", "2026-08-08", creatives) is None
    assert select_a8_creative("/blog/example", "2026-08-08", creatives) is not None


def _assert_invalid_catalog_fails_closed():
    catalog = json.loads((ROOT / "data" / "a8_creative_catalog.json").read_text(encoding="utf-8"))
    catalog["creatives"][0]["template"] = "../unsafe.html"
    with patch("pathlib.Path.read_text", return_value=json.dumps(catalog)):
        assert load_a8_creative_catalog(ROOT / "invalid-catalog.json") == []

    catalog = json.loads((ROOT / "data" / "a8_creative_catalog.json").read_text(encoding="utf-8"))
    catalog["creatives"][0]["weight"] = -1
    with patch("pathlib.Path.read_text", return_value=json.dumps(catalog)):
        assert load_a8_creative_catalog(ROOT / "invalid-catalog.json") == []


def _assert_placement_spacing():
    footer = (ROOT / "templates" / "includes" / "footer.html").read_text(encoding="utf-8")
    amazon_block = footer.index("{% if footer_primary_amazon %}")
    related_block = footer.index("includes/related_content.html", amazon_block)
    primary_a8_block = footer.index("{% if footer_primary_a8 %}")
    secondary_amazon_block = footer.index("{% if footer_secondary_amazon %}")
    navigation_block = footer.index("{% for col in footer_columns|default([]) %}")
    secondary_a8_block = footer.index("{% if footer_secondary_a8 and a8_can_render_placement")
    assert amazon_block < related_block < primary_a8_block < secondary_amazon_block < navigation_block < secondary_a8_block

    tools = (ROOT / "templates" / "tools" / "index.html").read_text(encoding="utf-8")
    tools_amazon = tools.index("tools-affiliate-rail__primary")
    tools_publisher = tools.index("tools-affiliate-rail__related")
    tools_a8 = tools.index("tools-primary-a8")
    tools_lower_amazon = tools.index("secondary_amazon_recommendation", tools_a8)
    tools_lower_publisher = tools.index("includes/related_content.html", tools_lower_amazon)
    tools_lower_a8 = tools.index("tools-lower-a8")
    assert tools_amazon < tools_publisher < tools_a8 < tools_lower_amazon < tools_lower_publisher < tools_lower_a8

    landing = (ROOT / "templates" / "landing.html").read_text(encoding="utf-8")
    amazon_block = landing.index("affiliate_context_placement='top-late-amazon'")
    publisher_block = landing.index('class="landing-affiliate-rail__related"')
    a8_block = landing.index("affiliate_section_placement='top-lower-a8'")
    assert amazon_block < publisher_block < a8_block < landing.index('id="safety"')
    lower_amazon = landing.index("landing_secondary_amazon_recommendation")
    lower_publisher = landing.index("includes/related_content.html", lower_amazon)
    lower_a8 = landing.index("affiliate_section_placement='landing-lower-a8'")
    assert lower_amazon < lower_publisher < lower_a8

    for path in A8_AFTER_EXPLANATION_PATHS:
        template = (ROOT / "templates" / f"{path.lstrip('/')}.html").read_text(encoding="utf-8")
        assert template.index("includes/tool_content_blocks.html") < template.index("a8_slot_placement='tool-after-explanation'")
        assert template.index("includes/related_tools.html") < template.index("a8_slot_placement='tool-after-explanation'")


def _assert_rendering():
    from app import app

    app.config["TESTING"] = True
    eligible = sorted(A8_ELIGIBLE_EXACT_PATHS)
    excluded = sorted(A8_HARD_EXCLUDED_PATHS)
    with app.test_client() as client:
        for path in eligible:
            response = client.get(path, follow_redirects=False)
            assert response.status_code == 200, (path, response.status_code)
            body = response.data.decode("utf-8", errors="replace")
            expected_count = get_a8_visible_limit(path)
            assert body.count('data-a8-creative-id="') == expected_count, path
            assert body.count("https://px.a8.net/svt/ejp") == expected_count, path
            assert body.count('width="300" height="250"') == expected_count, path
            assert body.count('width="1" height="1"') == expected_count, path
            assert "rot3.a8.net" not in body, path
            if path == "/":
                creative_ids = re.findall(r'data-a8-creative-id="([^"]+)"', body)
                assert len(set(creative_ids)) == 2
        article_path = "/blog/excel-format-mistakes-and-design"
        article_body = client.get(article_path).data.decode("utf-8", errors="replace")
        assert article_body.count('data-a8-creative-id="') == get_a8_visible_limit(article_path), article_path
        assert article_body.count("https://px.a8.net/svt/ejp") == get_a8_visible_limit(article_path), article_path
        for path in excluded:
            response = client.get(path, follow_redirects=False)
            assert response.status_code == 200, (path, response.status_code)
            body = response.data.decode("utf-8", errors="replace")
            assert 'data-a8-creative-id="' not in body, path
            assert "https://px.a8.net/svt/ejp" not in body, path

        previous = os.environ.get("AFFILIATE_ENABLED")
        os.environ["AFFILIATE_ENABLED"] = "false"
        try:
            body = client.get("/").data.decode("utf-8", errors="replace")
            assert 'data-a8-creative-id="' not in body
            assert 'class="a8-creative-slot"' not in body
        finally:
            if previous is None:
                os.environ.pop("AFFILIATE_ENABLED", None)
            else:
                os.environ["AFFILIATE_ENABLED"] = previous


def main():
    _assert_catalog()
    _assert_selection()
    _assert_invalid_catalog_fails_closed()
    _assert_placement_spacing()
    _assert_rendering()
    assert len(A8_HIGH_CONTENT_EXACT_PATHS) >= 18
    print("A8 creative catalog checks passed")


if __name__ == "__main__":
    main()
