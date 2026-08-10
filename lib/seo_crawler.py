"""Bounded same-origin crawler used by the SEO utility."""

from __future__ import annotations

import time
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse

from lib.safe_http import SafeHttpClient, SafeHttpError, is_url_safe


EXCLUDED_EXTENSIONS = (
    ".pdf", ".zip", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff",
    ".css", ".js", ".mjs", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".mp3", ".webm", ".ogg", ".wav", ".avi", ".mov", ".m4a",
    ".xml", ".json", ".txt", ".rss", ".atom", ".yaml", ".yml",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dmg", ".apk", ".tar", ".gz", ".rar", ".7z",
)
ALLOWED_HTML_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml"})


def is_url_safe_for_crawl(url):
    """Validate a crawl target, including every resolved A/AAAA address."""
    return is_url_safe(url)


def _get_bs4():
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup
    except ImportError:
        return None


def normalize_url(url, strip_query=True):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    path = (parsed.path or "/").rstrip("/") or "/"
    query = "" if strip_query else parsed.query
    fragment = "" if strip_query else parsed.fragment
    return urlunparse((parsed.scheme, parsed.netloc.lower(), path, parsed.params, query, fragment))


def _should_exclude_by_extension(url):
    path = (urlparse(url).path or "/").lower().rstrip("/")
    return next((extension for extension in EXCLUDED_EXTENSIONS if path.endswith(extension)), None)


def _fetch_robots_disallow_prefixes(origin, request_timeout, client):
    prefixes = []
    try:
        response = client.get(
            urljoin(origin, "/robots.txt"),
            connect_timeout=min(3, request_timeout),
            read_timeout=request_timeout,
            max_bytes=256 * 1024,
            allowed_content_types=frozenset({"text/plain", "text/html"}),
            same_origin=origin,
        )
        if response.status != 200:
            return []
        for line in response.text.splitlines():
            line = line.strip()
            if line.lower().startswith("disallow:"):
                path = line[9:].strip()
                if path and path != "/":
                    prefixes.append(path if path.startswith("/") else f"/{path}")
    except SafeHttpError:
        return []
    return prefixes


def _is_disallowed(path, prefixes):
    path = path or "/"
    for prefix in prefixes:
        normalized = prefix.rstrip("*")
        if path == normalized or path.startswith(normalized.rstrip("/") + "/") or path.startswith(normalized):
            return True
    return False


def crawl(start_url, max_urls=300, max_depth=3, request_timeout=5, total_timeout=60):
    """Crawl one origin without cookies, proxies, authentication, or unsafe redirects."""
    BeautifulSoup = _get_bs4()
    if not BeautifulSoup:
        return [], ["beautifulsoup4 is not installed"]

    safe, error = is_url_safe_for_crawl(start_url)
    if not safe:
        return [], [f"Start URL rejected: {error}"]
    parsed_start = urlparse(start_url)
    origin = parsed_start.netloc.lower()
    start_normalized = normalize_url(start_url)
    if not start_normalized:
        return [], ["Start URL could not be normalized"]

    client = SafeHttpClient()
    origin_url = f"{parsed_start.scheme}://{parsed_start.netloc}"
    disallow_prefixes = _fetch_robots_disallow_prefixes(origin_url, request_timeout, client)
    visited = set()
    urls = []
    warnings = []
    queue = deque([(start_normalized, 0)])
    deadline = time.time() + min(max(1, total_timeout), 60)
    max_urls = min(max(1, int(max_urls)), 1000)
    max_depth = min(max(0, int(max_depth)), 10)

    while queue and time.time() < deadline and len(urls) < max_urls:
        current, depth = queue.popleft()
        if depth > max_depth:
            continue
        normalized = normalize_url(current)
        if not normalized or normalized in visited or urlparse(normalized).netloc.lower() != origin:
            continue
        path = urlparse(normalized).path or "/"
        if _is_disallowed(path, disallow_prefixes) or _should_exclude_by_extension(normalized):
            continue

        visited.add(normalized)
        urls.append(normalized)
        if len(urls) >= max_urls:
            warnings.append("Maximum URL count reached")
            break

        try:
            response = client.get(
                current,
                connect_timeout=min(3, request_timeout),
                read_timeout=request_timeout,
                max_bytes=2 * 1024 * 1024,
                max_redirects=3,
                allowed_content_types=ALLOWED_HTML_CONTENT_TYPES,
                same_origin=origin_url,
            )
        except SafeHttpError as exc:
            warnings.append(f"Fetch rejected: {exc.code}")
            continue
        if response.status != 200:
            warnings.append(f"HTTP status {response.status} was skipped")
            continue

        try:
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception:
            warnings.append("HTML parser rejected a response")
            continue
        for anchor in soup.find_all("a", href=True):
            href = (anchor.get("href") or "").strip()
            if not href or href.startswith("#") or href.lower().startswith("javascript:"):
                continue
            absolute = urljoin(response.url, href)
            parsed = urlparse(absolute)
            if parsed.scheme not in ("http", "https") or parsed.netloc.lower() != origin:
                continue
            child = normalize_url(absolute)
            if not child or child in visited or _is_disallowed(parsed.path or "/", disallow_prefixes):
                continue
            if _should_exclude_by_extension(child):
                continue
            queue.append((child, depth + 1))

    if time.time() >= deadline:
        warnings.append("Crawler time limit reached")
    return urls, warnings
