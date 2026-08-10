"""Validated A8 creative catalog and deterministic page-level rotation."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG_PATH = REPO_ROOT / "data" / "a8_creative_catalog.json"
TEMPLATE_ROOT = REPO_ROOT / "templates"
JST = timezone(timedelta(hours=9))
VISIBLE_A8_MAX_PER_PAGE = 1
LANDING_VISIBLE_A8_MAX_PER_PAGE = 2

A8_HIGH_CONTENT_EXACT_PATHS = frozenset(
    (
        "/tools",
        "/tools/pdf",
        "/tools/csv",
        "/tools/image-batch",
        "/tools/image-compress",
        "/tools/image-cleanup",
        "/tools/qr-code",
        "/tools/seo",
        "/guide",
        "/guide/pdf",
        "/guide/csv",
        "/guide/image-batch",
        "/guide/image-compress",
        "/guide/image-cleanup",
        "/guide/qr-code",
        "/guide/seo",
        "/best-practices",
        "/glossary",
        "/blog",
    )
)
A8_HIGH_CONTENT_PREFIXES = ("/blog/",)

ALLOWED_A8_TEMPLATES = frozenset(
    f"includes/a8/creative_{index:02d}.html" for index in range(1, 6)
)
A8_HARD_EXCLUDED_PATHS = frozenset(
    ("/about", "/business", "/contact", "/privacy", "/terms")
)
A8_ELIGIBLE_EXACT_PATHS = frozenset(
    (
        "/",
        "/tools",
        "/tools/pdf",
        "/tools/csv",
        "/tools/image-batch",
        "/tools/image-compress",
        "/tools/image-cleanup",
        "/tools/qr-code",
        "/tools/seo",
        "/guide",
        "/guide/pdf",
        "/guide/csv",
        "/guide/image-batch",
        "/guide/image-compress",
        "/guide/image-cleanup",
        "/guide/qr-code",
        "/guide/seo",
        "/faq",
        "/glossary",
        "/best-practices",
        "/blog",
    )
)
A8_ELIGIBLE_PREFIXES = ("/blog/",)
A8_AFTER_EXPLANATION_PATHS = frozenset(
    (
        "/tools/pdf",
        "/tools/csv",
        "/tools/image-batch",
        "/tools/image-cleanup",
        "/tools/seo",
    )
)


def _normalize_path(path: str | None) -> str:
    normalized = str(path or "/").split("?", 1)[0].split("#", 1)[0]
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized


def get_a8_allowed_placements(path: str | None) -> tuple[str, ...]:
    """Return the allowlisted A8 placements for a public path."""
    normalized = _normalize_path(path)
    if normalized in A8_HARD_EXCLUDED_PATHS:
        return ()
    if normalized not in A8_ELIGIBLE_EXACT_PATHS and not any(
        normalized.startswith(prefix) for prefix in A8_ELIGIBLE_PREFIXES
    ):
        return ()
    if normalized == "/":
        return ("top-lower-a8", "landing-lower-a8")
    if normalized == "/tools":
        return ("tools-primary-a8", "tools-lower-a8")
    if normalized in A8_AFTER_EXPLANATION_PATHS:
        return ("tool-after-explanation", "content-lower-a8")
    if normalized in A8_HIGH_CONTENT_EXACT_PATHS or any(
        normalized.startswith(prefix) for prefix in A8_HIGH_CONTENT_PREFIXES
    ):
        return ("global-footer-a8", "content-lower-a8")
    return ("global-footer-a8",)


def get_a8_placement(path: str | None) -> str | None:
    """Return the primary A8 placement retained for compatibility."""
    placements = get_a8_allowed_placements(path)
    return placements[0] if placements else None


def get_a8_visible_limit(path: str | None) -> int:
    normalized = _normalize_path(path)
    if normalized == "/":
        return LANDING_VISIBLE_A8_MAX_PER_PAGE
    if normalized in A8_HIGH_CONTENT_EXACT_PATHS or any(
        normalized.startswith(prefix) for prefix in A8_HIGH_CONTENT_PREFIXES
    ):
        return 2
    return VISIBLE_A8_MAX_PER_PAGE


def a8_can_render_placement(path: str | None, placement: str | None) -> bool:
    return bool(placement and placement in get_a8_allowed_placements(path))


def _template_checksum(template_path: str) -> str:
    return hashlib.sha256((TEMPLATE_ROOT / template_path).read_bytes()).hexdigest()


def load_a8_creative_catalog(catalog_path: str | Path | None = None) -> list[dict]:
    """Load verified creatives; any malformed catalog fails closed."""
    path = Path(catalog_path) if catalog_path else DEFAULT_CATALOG_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != 1 or not isinstance(payload.get("creatives"), list):
            raise ValueError("unsupported catalog structure")

        validated = []
        seen_ids = set()
        seen_templates = set()
        for raw in payload["creatives"]:
            if not isinstance(raw, dict):
                raise ValueError("creative must be an object")
            creative_id = raw.get("id")
            template_path = raw.get("template")
            weight = raw.get("weight")
            if not re.fullmatch(r"a8-0[1-5]", str(creative_id or "")):
                raise ValueError("invalid creative id")
            if creative_id in seen_ids or template_path in seen_templates:
                raise ValueError("duplicate creative")
            if template_path not in ALLOWED_A8_TEMPLATES or ".." in template_path:
                raise ValueError("template is not allowlisted")
            if raw.get("size") != "300x250":
                raise ValueError("unexpected creative size")
            if raw.get("source") != "user_supplied_a8_material":
                raise ValueError("unexpected creative source")
            if not isinstance(raw.get("enabled"), bool):
                raise ValueError("enabled must be boolean")
            if not isinstance(weight, int) or isinstance(weight, bool) or weight < 0:
                raise ValueError("weight must be a non-negative integer")
            if raw.get("sha256") != _template_checksum(template_path):
                raise ValueError(f"checksum mismatch for {creative_id}")
            seen_ids.add(creative_id)
            seen_templates.add(template_path)
            validated.append(dict(raw))
        if len(validated) != 5:
            raise ValueError("catalog must contain exactly five creatives")
        return validated
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("a8_catalog_disabled reason=%s", str(exc))
        return []


def select_a8_creative(
    request_path: str | None,
    date_key: str | None = None,
    creatives: list[dict] | None = None,
    placement: str | None = None,
    exclude_creative_ids: set[str] | list[str] | tuple[str, ...] | None = None,
) -> dict | None:
    """Select one enabled creative using a stable JST-date and path seed."""
    normalized_path = _normalize_path(request_path)
    primary_placement = get_a8_placement(normalized_path)
    selected_placement = placement or primary_placement
    if selected_placement not in get_a8_allowed_placements(normalized_path):
        return None
    if date_key is None:
        date_key = datetime.now(JST).date().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date_key)):
        return None

    source = creatives if creatives is not None else load_a8_creative_catalog()
    excluded_ids = {str(value) for value in (exclude_creative_ids or ()) if value}
    enabled = [
        item for item in source
        if item.get("enabled") is True
        and isinstance(item.get("weight"), int)
        and item["weight"] > 0
        and str(item.get("id") or "") not in excluded_ids
    ]
    total_weight = sum(item["weight"] for item in enabled)
    if total_weight <= 0:
        return None

    if selected_placement == primary_placement:
        seed = f"{date_key}:{normalized_path}:a8-v1"
    else:
        seed = f"{date_key}:{normalized_path}:{selected_placement}:a8-v1"
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    position = int.from_bytes(digest, "big") % total_weight
    cumulative = 0
    for item in enabled:
        cumulative += item["weight"]
        if position < cumulative:
            selected = dict(item)
            selected["placement"] = selected_placement
            return selected
    return None
