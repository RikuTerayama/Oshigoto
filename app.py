#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime
from collections import deque as _deque

from werkzeug.exceptions import HTTPException, MethodNotAllowed, NotFound
from flask import Flask, Response, g, has_request_context, jsonify, redirect, render_template, request, send_file
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

from lib.seo import (
    build_breadcrumb_items,
    get_article_schema,
    get_blog_articles,
    get_page_kind,
    get_related_content,
    get_seo_defaults,
    get_web_application_schema,
    is_noindex_path,
)
from lib.amazon_creators import (
    build_search_url as build_amazon_search_url,
    build_rotating_theme_cards as build_amazon_rotating_theme_cards,
    get_recommendations as get_amazon_recommendations,
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

def _env_int(name, default, minimum=1):
    """Read a positive integer environment variable with a safe fallback."""
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, value)


MEMORY_LIMIT_MB = _env_int("MEMORY_LIMIT_MB", 450)
MEMORY_WARNING_MB = _env_int("MEMORY_WARNING_MB", 400)
if MEMORY_WARNING_MB >= MEMORY_LIMIT_MB:
    MEMORY_WARNING_MB = int(MEMORY_LIMIT_MB * 0.9)
MAX_FILE_SIZE_MB = _env_int("MAX_FILE_SIZE_MB", 10)
MAX_TOTAL_UPLOAD_MB = _env_int("MAX_TOTAL_UPLOAD_MB", 50)
MAX_FILES_PER_REQUEST = _env_int("MAX_FILES_PER_REQUEST", 20)
MAX_PDF_PAGES = _env_int("MAX_PDF_PAGES", 500)
MAX_ACTIVE_PDF_JOBS = _env_int("MAX_ACTIVE_PDF_JOBS", 1)
MAX_OUTPUT_SIZE_MB = _env_int("MAX_OUTPUT_SIZE_MB", 100)

MAX_FILE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_TOTAL_UPLOAD_BYTES = MAX_TOTAL_UPLOAD_MB * 1024 * 1024
MAX_OUTPUT_BYTES = MAX_OUTPUT_SIZE_MB * 1024 * 1024
PDF_JOB_RETRY_AFTER_SEC = _env_int("PDF_JOB_RETRY_AFTER_SEC", 5)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["MAX_CONTENT_LENGTH"] = MAX_TOTAL_UPLOAD_BYTES

_PDF_JOB_SEMAPHORE = threading.BoundedSemaphore(MAX_ACTIVE_PDF_JOBS)

# === In-memory rate limiting ===
from collections import deque as _deque

def _rate_limit_path_group(path, method):
    """Return the rate-limit group for a request path, or None when exempt."""
    if path.startswith(('/healthz', '/livez', '/readyz', '/ping', '/health', '/ready', '/static/')):
        return None
    if path in ('/robots.txt', '/sitemap.xml', '/ads.txt'):
        return None
    if path.startswith('/api/'):
        if path.startswith('/api/seo/crawl-urls'):
            return 'seo_crawl'
        if path.startswith('/api/pdf/'):
            return 'pdf'
        return 'api'
    return None

class RateLimiter:
    """Fixed-window-ish in-memory rate limiter keyed by client and group."""
    def __init__(self, window_sec=60):
        self.window_sec = window_sec
        self._data = {}
        self._lock = threading.Lock()

    def _cleanup(self, now):
        stale_after = self.window_sec * 2
        stale_keys = [
            key for key, q in self._data.items()
            if not q or now - q[-1] > stale_after
        ]
        for key in stale_keys:
            self._data.pop(key, None)

    def is_allowed(self, key, max_per_window):
        with self._lock:
            now = time.time()
            self._cleanup(now)
            if key not in self._data:
                self._data[key] = _deque(maxlen=max_per_window * 2)
            q = self._data[key]
            while q and now - q[0] > self.window_sec:
                q.popleft()
            if len(q) >= max_per_window:
                return False, self.window_sec
            q.append(now)
            return True, self.window_sec

_RATE_LIMITS = {
    'api': _env_int("RATE_LIMIT_LIGHT_PER_MIN", 60),
    'pdf': _env_int("RATE_LIMIT_PDF_PER_MIN", 10),
    'seo_crawl': _env_int("RATE_LIMIT_SEO_PER_MIN", 8),
}
_rate_limiter = RateLimiter(window_sec=60)


def _get_rate_limit_client_key():
    """Use ProxyFix-normalized remote_addr without logging or storing request metadata."""
    return request.remote_addr or 'unknown'

@app.before_request
def rate_limit_check():
    """Return 429 + Retry-After when a request exceeds the per-minute API limit."""
    path = request.path
    method = request.method
    group = _rate_limit_path_group(path, method)
    if group is None:
        return None
    key = f"{_get_rate_limit_client_key()}:{group}"
    max_per = _RATE_LIMITS.get(group, 60)
    allowed, window_sec = _rate_limiter.is_allowed(key, max_per)
    if not allowed:
        resp = jsonify(
            error='Too many requests. Please wait a moment and try again.',
            error_code='RATE_LIMIT_EXCEEDED',
            retry_after_sec=window_sec
        )
        resp.status_code = 429
        resp.headers['Retry-After'] = str(int(window_sec))
        return resp
    return None


@app.before_request
def before_request():
    """Attach request metadata and log public requests."""
    g.start_time = time.time()
    g.request_id = uuid.uuid4().hex[:12]

    if not request.path.startswith(('/healthz', '/livez', '/readyz')):
        logger.info(
            "req_start rid=%s method=%s path=%s",
            g.request_id,
            request.method,
            request.path,
        )

@app.after_request
def after_request(response):
    """Add response headers and request logging."""
    if hasattr(g, 'start_time') and hasattr(g, 'request_id'):
        duration_ms = (time.time() - g.start_time) * 1000
        response.headers['X-Request-ID'] = g.request_id
        deploy_commit = (os.getenv('RENDER_GIT_COMMIT') or os.getenv('GIT_COMMIT') or '').strip()
        if deploy_commit:
            response.headers['X-Deploy-Commit'] = deploy_commit[:12]
        
        if not request.path.startswith(('/healthz', '/livez', '/readyz')):
            level = logging.WARNING if duration_ms > 1000 else logging.INFO
            logger.log(
                level,
                "req_end rid=%s method=%s path=%s status=%s ms=%.1f",
                g.request_id,
                request.method,
                request.path,
                response.status_code,
                duration_ms,
            )
            if duration_ms > 5000:
                logger.warning("slow_request rid=%s path=%s ms=%.1f", g.request_id, request.path, duration_ms)

    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=()')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')

    if not request.path.startswith('/static/'):
        ct = response.content_type or ''
        if 'text/html' in ct:
            response.headers['Cache-Control'] = 'no-store, max-age=0'
    
    return response

# 繧ｰ繝ｭ繝ｼ繝舌Ν繧ｨ繝ｩ繝ｼ繝上Φ繝峨Λ繝ｼ
# Shared error handlers
def _generate_error_id():
    """Generate a short error id for diagnostics."""
    return str(uuid.uuid4())[:8]


def _render_error_page(status_code, error_message, error_id=None):
    """Render a shared error page."""
    error_id = error_id or _generate_error_id()
    try:
        return render_template(
            'error.html',
            error_message=error_message,
            error_id=error_id,
            status_code=status_code,
        ), status_code
    except Exception as render_error:
        logger.exception("error_page_render_failed error_id=%s render_error=%s", error_id, render_error)
        html_content = (
            '<html><head><meta charset="utf-8"><title>Error</title></head>'
            f'<body><h1>Error {status_code}</h1><p>{error_message}</p>'
            f'<p>Error ID: {error_id}</p></body></html>'
        )
        return Response(html_content, status=status_code, mimetype='text/html')


@app.errorhandler(404)
def not_found(error):
    """Handle 404 responses."""
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    logger.warning(
        "not_found error_id=%s rid=%s path=%s method=%s error_type=%s",
        error_id,
        request_id,
        request.path,
        request.method,
        type(error).__name__,
    )
    return _render_error_page(404, 'The requested page was not found.', error_id)


@app.errorhandler(413)
def payload_too_large(error):
    """Handle upload payloads that exceed configured limits."""
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    path = request.path if request else 'unknown'
    logger.warning(
        "payload_too_large error_id=%s rid=%s path=%s method=%s error_type=%s",
        error_id,
        request_id,
        path,
        request.method if request else 'unknown',
        type(error).__name__,
    )
    if path.startswith('/api/'):
        return jsonify(success=False, error_code='payload_too_large', request_id=error_id), 413
    return _render_error_page(413, 'The uploaded data is too large.', error_id)


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 responses."""
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    logger.exception(
        "internal_server_error error_id=%s rid=%s path=%s method=%s error_type=%s",
        error_id,
        request_id,
        request.path if request else 'unknown',
        request.method if request else 'unknown',
        type(error).__name__,
    )
    return _render_error_page(500, 'An unexpected server error occurred. Please try again later.', error_id)


@app.errorhandler(503)
def service_unavailable(error):
    """Handle 503 responses."""
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    logger.exception(
        "service_unavailable error_id=%s rid=%s path=%s method=%s error_type=%s",
        error_id,
        request_id,
        request.path if request else 'unknown',
        request.method if request else 'unknown',
        type(error).__name__,
    )
    return _render_error_page(503, 'The service is temporarily unavailable. Please try again later.', error_id)


@app.errorhandler(Exception)
def handle_exception(error):
    """Handle unexpected exceptions as 500 responses."""
    if isinstance(error, HTTPException):
        return error
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    logger.exception(
        "unhandled_exception error_id=%s rid=%s path=%s method=%s error_type=%s",
        error_id,
        request_id,
        request.path if request else 'unknown',
        request.method if request else 'unknown',
        type(error).__name__,
    )
    return _render_error_page(500, 'An unexpected server error occurred. Please try again later.', error_id)

def _env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def _env_list(name, default=None):
    value = os.getenv(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]


def _normalize_affiliate_network(value):
    normalized = (value or 'a8_rotation').strip().lower()
    if normalized in ('a8_rotation', 'rotation', 'a8'):
        return 'a8_rotation'
    return 'a8_rotation'


def _path_matches_rule(path, rule):
    if not rule:
        return False
    normalized_path = path or '/'
    normalized_rule = rule.strip()
    if not normalized_rule:
        return False
    if normalized_rule == normalized_path:
        return True
    if normalized_rule.endswith('*'):
        prefix = normalized_rule[:-1]
        return normalized_path.startswith(prefix)
    if normalized_rule == '/':
        return normalized_path == '/'
    return normalized_path.startswith(normalized_rule.rstrip('/'))


AFFILIATE_SLOT_RULES = {
    'home_after_hero': {
        'page_types': ('landing',),
        'paths': ('/',),
        'default_size': '300x250',
        'breakpoint_policy': 'all',
        'allow_rotation': True,
    },
    'blog_index_after_intro': {
        'page_types': ('blog_index',),
        'paths': ('/blog',),
        'default_size': '300x250',
        'breakpoint_policy': 'all',
        'allow_rotation': True,
    },
    'case_index_after_intro': {
        'page_types': ('case_index',),
        'paths': ('/case-studies',),
        'default_size': '300x250',
        'breakpoint_policy': 'all',
        'allow_rotation': True,
    },
    'public_top_inline': {
        'page_types': ('article', 'guide', 'info', 'tool', 'tool_index', 'trust_sensitive', 'legal', 'contact', 'generic'),
        'default_size': '300x250',
        'breakpoint_policy': 'all',
        'allow_rotation': True,
    },
    'article_end_1': {
        'page_types': ('article',),
        'default_size': '300x250',
        'breakpoint_policy': 'tablet-up',
        'allow_rotation': True,
    },
    'guide_end_1': {
        'page_types': ('guide', 'info'),
        'default_size': '300x250',
        'breakpoint_policy': 'tablet-up',
        'allow_rotation': True,
    },
    'global_footer_banner': {
        'page_types': ('trust_sensitive', 'legal', 'contact', 'tool', 'tool_index', 'generic'),
        'default_size': '300x250',
        'breakpoint_policy': 'tablet-up',
        'allow_rotation': True,
    },
    'tool_post_result': {
        'page_types': ('tool',),
        'default_size': '300x250',
        'breakpoint_policy': 'tablet-up',
        'allow_rotation': False,
    },
}

PUBLIC_AFFILIATE_PAGE_TYPES = frozenset((
    'landing',
    'blog_index',
    'case_index',
    'article',
    'guide',
    'info',
    'tool',
    'tool_index',
    'trust_sensitive',
    'legal',
    'contact',
    'generic',
))

NON_UI_AFFILIATE_PATH_PREFIXES = ('/api/', '/admin/', '/static/')
NON_UI_AFFILIATE_PATHS = frozenset((
))


def get_affiliate_page_type(path):
    normalized_path = path or '/'
    if normalized_path == '/':
        return 'landing'
    if normalized_path == '/autofill':
        return 'trust_sensitive'
    if normalized_path == '/blog':
        return 'blog_index'
    if normalized_path.startswith('/blog/'):
        return 'article'
    if normalized_path == '/case-studies':
        return 'case_index'
    if normalized_path.startswith('/case-study/'):
        return 'article'
    if normalized_path == '/guide' or normalized_path.startswith('/guide/'):
        return 'guide'
    if normalized_path in ('/about', '/faq', '/glossary', '/best-practices'):
        return 'info'
    if normalized_path == '/tools':
        return 'tool_index'
    if normalized_path.startswith('/tools/'):
        return 'tool'
    if normalized_path in ('/privacy', '/terms'):
        return 'legal'
    if normalized_path == '/contact':
        return 'contact'
    return 'generic'


def get_affiliate_settings():
    return {
        'enabled': _env_flag('AFFILIATE_ENABLED', True),
        'textlinks_enabled': _env_flag('AFFILIATE_TEXTLINKS_ENABLED', True),
        'banners_enabled': _env_flag('AFFILIATE_BANNERS_ENABLED', True),
        'stack_only': _env_flag('AFFILIATE_STACK_ONLY', True),
        'network': _normalize_affiliate_network(os.getenv('AFFILIATE_NETWORK', 'a8_rotation')),
        'exclude_paths': tuple(_env_list(
            'AFFILIATE_EXCLUDE_PATHS',
            ()
        )),
        'allowed_page_types': tuple(_env_list(
            'AFFILIATE_ALLOWED_PAGE_TYPES',
            (
                'landing',
                'blog_index',
                'case_index',
                'article',
                'guide',
                'info',
                'tool',
                'tool_index',
                'trust_sensitive',
                'legal',
                'contact',
                'generic',
            )
        )),
        'widget_desktop_enabled': _env_flag('AFFILIATE_WIDGET_DESKTOP_ENABLED', True),
        'widget_tablet_enabled': _env_flag('AFFILIATE_WIDGET_TABLET_ENABLED', True),
        'widget_mobile_enabled': _env_flag('AFFILIATE_WIDGET_MOBILE_ENABLED', False),
        'rotation_banner_enabled': _env_flag('AFFILIATE_ROTATION_BANNER_ENABLED', True),
    }


def affiliate_is_path_excluded(path=None):
    settings = get_affiliate_settings()
    normalized_path = path or (request.path if has_request_context() else '/')
    if normalized_path.startswith(NON_UI_AFFILIATE_PATH_PREFIXES):
        return True
    if normalized_path in NON_UI_AFFILIATE_PATHS:
        return True
    if get_affiliate_page_type(normalized_path) in PUBLIC_AFFILIATE_PAGE_TYPES:
        return False
    return any(_path_matches_rule(normalized_path, rule) for rule in settings['exclude_paths'])


def affiliate_can_render_textlinks(path=None):
    settings = get_affiliate_settings()
    return settings['enabled'] and settings['textlinks_enabled']


def affiliate_get_slot_config(slot_id, path=None):
    settings = get_affiliate_settings()
    rule = AFFILIATE_SLOT_RULES.get(slot_id)
    if not rule:
        return None

    normalized_path = path or (request.path if has_request_context() else '/')
    page_type = get_affiliate_page_type(normalized_path)
    if page_type not in rule.get('page_types', ()):
        return None

    slot_paths = rule.get('paths')
    if slot_paths and not any(_path_matches_rule(normalized_path, slot_path) for slot_path in slot_paths):
        return None

    allowed_page_types = PUBLIC_AFFILIATE_PAGE_TYPES.union(settings['allowed_page_types'])
    if page_type not in allowed_page_types:
        return None

    kind = 'a8_rotation'
    size = rule.get('default_size', '300x250')
    if (
        settings['network'] == 'a8_rotation'
        and settings['rotation_banner_enabled']
        and rule.get('allow_rotation')
    ):
        kind = 'a8_rotation'
        size = '468x60'

    return {
        'slot_id': slot_id,
        'kind': kind,
        'size': size,
        'breakpoint_policy': rule.get('breakpoint_policy', 'tablet-up'),
        'desktop_enabled': settings['widget_desktop_enabled'],
        'tablet_enabled': settings['widget_tablet_enabled'],
        'mobile_enabled': settings['widget_mobile_enabled'],
        'page_type': page_type,
        'path': normalized_path,
    }


def affiliate_can_render_slot(slot_id, path=None):
    settings = get_affiliate_settings()
    if not (settings['enabled'] and settings['banners_enabled']):
        return False
    if settings.get('stack_only'):
        return False

    normalized_path = path or (request.path if has_request_context() else '/')
    if affiliate_is_path_excluded(normalized_path):
        return False

    return affiliate_get_slot_config(slot_id, normalized_path) is not None


def affiliate_footer_slot_id(path=None):
    normalized_path = path or (request.path if has_request_context() else '/')
    page_type = get_affiliate_page_type(normalized_path)
    slot_id = None
    if page_type == 'article':
        slot_id = 'article_end_1'
    elif page_type in ('guide', 'info'):
        slot_id = 'guide_end_1'
    elif page_type in ('trust_sensitive', 'legal', 'contact', 'tool', 'tool_index', 'generic'):
        slot_id = 'global_footer_banner'

    if slot_id and affiliate_can_render_slot(slot_id, normalized_path):
        return slot_id
    return None


def affiliate_top_slot_id(path=None):
    normalized_path = path or (request.path if has_request_context() else '/')
    page_type = get_affiliate_page_type(normalized_path)
    slot_id = None
    if page_type in ('article', 'guide', 'info', 'tool', 'tool_index', 'trust_sensitive', 'legal', 'contact', 'generic'):
        slot_id = 'public_top_inline'

    if slot_id and affiliate_can_render_slot(slot_id, normalized_path):
        return slot_id
    return None


def affiliate_top_slot_mode(path=None):
    normalized_path = path or (request.path if has_request_context() else '/')
    slot_id = affiliate_top_slot_id(normalized_path)
    if not slot_id:
        return 'none'
    if normalized_path == '/autofill':
        return 'autofill'
    if normalized_path == '/tools' or normalized_path.startswith('/tools/'):
        return 'tool'
    return 'header'


AMAZON_RECENT_HISTORY_COOKIE = 'oshigoto_recent_affiliate_context'
AMAZON_RECENT_HISTORY_LIMIT = 8
AMAZON_RECENT_HISTORY_COOKIE_MAX_BYTES = 1800


def _is_public_affiliate_html_path(path):
    normalized_path = path or '/'
    if normalized_path.startswith(NON_UI_AFFILIATE_PATH_PREFIXES):
        return False
    if normalized_path in NON_UI_AFFILIATE_PATHS:
        return False
    if normalized_path in ('/robots.txt', '/sitemap.xml', '/ads.txt'):
        return False
    if normalized_path.startswith(('/health', '/ready', '/live', '/ping')):
        return False
    return True


def _dedupe_keep_order(values):
    seen = set()
    output = []
    for value in values or []:
        cleaned = (value or '').strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output


def _load_recent_affiliate_history():
    if not has_request_context():
        return []
    raw = (request.cookies.get(AMAZON_RECENT_HISTORY_COOKIE) or '').strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []

    cleaned = []
    for entry in parsed[:AMAZON_RECENT_HISTORY_LIMIT]:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get('path') or entry.get('p') or '').strip()
        if not path or not _is_public_affiliate_html_path(path):
            continue
        category = str(entry.get('category') or entry.get('c') or entry.get('page_type') or entry.get('t') or '').strip()
        cleaned.append({
            'path': path,
            'page_type': category,
            'category': category,
            'keywords': [],
        })
    return cleaned


def _build_affiliate_page_tags(path, seo_defaults, products):
    tags = []
    normalized_path = path or '/'
    seo_defaults = seo_defaults or {}
    products = products if isinstance(products, list) else []

    category = seo_defaults.get('category')
    if category:
        tags.append(str(category))

    if normalized_path == '/autofill':
        tags.extend(['PDF', 'CSV', '画像', 'SEO'])
    elif normalized_path.startswith('/guide'):
        tags.extend(['ガイド', '使い方', '手順'])
    elif normalized_path.startswith('/blog'):
        tags.extend(['ブログ', '解説', 'ノウハウ'])
    elif normalized_path.startswith('/case'):
        tags.extend(['事例', '業務改善'])
    elif normalized_path.startswith('/tools'):
        tags.extend(['ツール', '効率化'])

    for product in products:
        if not isinstance(product, dict):
            continue
        product_paths = [product.get('path'), product.get('guide_path')]
        if normalized_path not in product_paths:
            continue
        if product.get('name'):
            tags.append(str(product.get('name')))
        if product.get('category'):
            tags.append(str(product.get('category')))
        product_tags = product.get('tags') or []
        if isinstance(product_tags, list):
            tags.extend([str(v) for v in product_tags])

    return _dedupe_keep_order(tags)[:8]


def _prepare_recent_affiliate_history_cookie(path, page_type, category, history):
    if not has_request_context():
        return
    if not _is_public_affiliate_html_path(path):
        return

    entry = {
        'p': path,
        'c': str(category or page_type or '')[:64],
    }
    updated = [entry]
    for item in history or []:
        if not isinstance(item, dict):
            continue
        item_path = str(item.get('path') or item.get('p') or '').strip()
        if item_path == path:
            continue
        updated.append({
            'p': item_path,
            'c': str(item.get('category') or item.get('c') or item.get('page_type') or '')[:64],
        })
        if len(updated) >= AMAZON_RECENT_HISTORY_LIMIT:
            break

    try:
        cookie_value = json.dumps(updated, separators=(',', ':'))
        while len(cookie_value.encode('utf-8')) > AMAZON_RECENT_HISTORY_COOKIE_MAX_BYTES and len(updated) > 1:
            updated.pop()
            cookie_value = json.dumps(updated, separators=(',', ':'))
        g.amazon_recent_history_cookie = cookie_value
    except Exception:
        g.amazon_recent_history_cookie = None


def _safe_get_amazon_affiliate(path, page_type, title, tags, recent_history):
    try:
        result = get_amazon_recommendations(
            path=path,
            page_type=page_type,
            title=title,
            tags=tags,
            recent_history=recent_history,
        )
    except Exception as exc:
        logger.warning("amazon_affiliate_unexpected_error type=%s detail=%s", type(exc).__name__, str(exc))
        result = None

    if not isinstance(result, dict):
        return {
            'enabled': False,
            'items': [],
            'keywords': [],
            'error': 'invalid_response',
            'source': 'none',
        }
    if not isinstance(result.get('items'), list):
        result['items'] = []
    if not isinstance(result.get('keywords'), list):
        result['keywords'] = []
    return result


def split_visible_sentences(text):
    """Visible copy only: split long Japanese text into sentence-level lines."""
    if not text:
        return []
    normalized = re.sub(r'\s+', ' ', str(text)).strip()
    if not normalized:
        return []
    if '。' not in normalized:
        return [normalized]

    lines = []
    current = ''
    for chunk in re.split(r'(。)', normalized):
        if not chunk:
            continue
        current += chunk
        if chunk == '。':
            lines.append(current.strip())
            current = ''
    if current.strip():
        lines.append(current.strip())
    return lines


def affiliate_side_rail_enabled(path=None):
    return False


@app.after_request
def persist_affiliate_history_cookie(response):
    cookie_value = getattr(g, 'amazon_recent_history_cookie', None) if has_request_context() else None
    if not cookie_value:
        return response
    if len(cookie_value.encode('utf-8')) > AMAZON_RECENT_HISTORY_COOKIE_MAX_BYTES:
        logger.warning("amazon_history_cookie_skipped reason=size_limit")
        return response
    try:
        response.set_cookie(
            AMAZON_RECENT_HISTORY_COOKIE,
            cookie_value,
            max_age=60 * 60 * 24 * 14,
            secure=request.is_secure,
            httponly=True,
            samesite='Lax',
            path='/',
        )
    except Exception as exc:
        logger.warning("amazon_history_cookie_write_error type=%s detail=%s", type(exc).__name__, str(exc))
    return response


# 迺ｰ蠅・､画焚繧偵ユ繝ｳ繝励Ξ繝ｼ繝医さ繝ｳ繝・く繧ｹ繝医↓豕ｨ蜈･・・dSense / Affiliate 險ｭ螳夂畑・・
@app.context_processor
def inject_env_vars():
    """Expose template variables for public tool and affiliate navigation."""
    try:
        import json
        from lib.products_catalog import PRODUCTS, get_public_products

        app_version = '1.0.0'
        try:
            with open('package.json', 'r', encoding='utf-8') as f:
                package_data = json.load(f)
                app_version = package_data.get('version', '1.0.0')
        except Exception:
            pass

        affiliate_settings = get_affiliate_settings()
        current_path = request.path if has_request_context() else '/'
        affiliate_page_type = get_affiliate_page_type(current_path)
        recent_affiliate_history = _load_recent_affiliate_history()
        seo_defaults = get_seo_defaults(current_path)
        base_url = os.getenv('BASE_URL', 'https://oshigoto.onrender.com').rstrip('/')
        seo_page_description = seo_defaults.get('description', '')
        seo_page_robots = seo_defaults.get('robots', 'index,follow')
        seo_page_kind = get_page_kind(current_path)
        web_application_schema = get_web_application_schema(
            current_path,
            seo_defaults.get('title', ''),
            seo_page_description,
            base_url,
        )
        article_schema = get_article_schema(
            current_path,
            base_url,
            seo_defaults.get('title', ''),
            seo_page_description,
        )
        seo_breadcrumb_items = build_breadcrumb_items(
            current_path,
            page_title='',
            breadcrumb_title=seo_defaults.get('breadcrumb_title', ''),
        )
        related_content_section = get_related_content(current_path)
        blog_articles = get_blog_articles()

        products_list = PRODUCTS
        if not isinstance(products_list, list):
            logger.warning(
                f"context_processor products_catalog not a list type={type(products_list).__name__} - using []"
            )
            products_list = []
        public_products = get_public_products()
        products_catalog = public_products
        amazon_tags = _build_affiliate_page_tags(current_path, seo_defaults, products_list)
        amazon_affiliate = _safe_get_amazon_affiliate(
            path=current_path,
            page_type=affiliate_page_type,
            title=seo_defaults.get('title', ''),
            tags=amazon_tags,
            recent_history=recent_affiliate_history,
        )
        amazon_affiliate_upper_items = build_amazon_rotating_theme_cards(
            path=current_path,
            page_type=affiliate_page_type,
            title=seo_defaults.get('title', ''),
            tags=amazon_tags,
            recent_history=recent_affiliate_history,
            slot_id='upper-amazon',
            count=3,
        )
        upper_theme_ids = [
            str(item.get('theme_id'))
            for item in amazon_affiliate_upper_items
            if isinstance(item, dict) and item.get('theme_id')
        ]
        amazon_affiliate_mid_items = build_amazon_rotating_theme_cards(
            path=current_path,
            page_type=affiliate_page_type,
            title=seo_defaults.get('title', ''),
            tags=amazon_tags,
            recent_history=recent_affiliate_history,
            slot_id='mid-amazon',
            count=3,
            exclude_theme_ids=upper_theme_ids,
        )
        _prepare_recent_affiliate_history_cookie(
            path=current_path,
            page_type=affiliate_page_type,
            category=seo_defaults.get('category'),
            history=recent_affiliate_history,
        )

        from lib.nav import get_nav_sections, get_footer_columns
        nav_sections = get_nav_sections()
        footer_columns = get_footer_columns()

        return {
            'ADSENSE_ENABLED': os.getenv('ADSENSE_ENABLED', 'false').lower() == 'true',
            'app_version': app_version,
            'products': public_products,
            'products_catalog': products_catalog,
            'nav_sections': nav_sections,
            'footer_columns': footer_columns,
            'BASE_URL': base_url,
            'GA_MEASUREMENT_ID': os.getenv('GA_MEASUREMENT_ID', ''),
            'GSC_VERIFICATION_CONTENT': os.getenv('GSC_VERIFICATION_CONTENT', ''),
            'OPERATOR_NAME': os.getenv('OPERATOR_NAME', ''),
            'OPERATOR_EMAIL': os.getenv('OPERATOR_EMAIL', ''),
            'OPERATOR_LOCATION': os.getenv('OPERATOR_LOCATION', ''),
            'OPERATOR_NOTE': os.getenv('OPERATOR_NOTE', ''),
            'seo_page_defaults': seo_defaults,
            'seo_page_description': seo_page_description,
            'seo_page_robots': seo_page_robots,
            'seo_page_kind': seo_page_kind,
            'seo_breadcrumb_items': seo_breadcrumb_items,
            'seo_web_application_schema': web_application_schema,
            'seo_article_schema': article_schema,
            'build_breadcrumb_items': build_breadcrumb_items,
            'split_visible_sentences': split_visible_sentences,
            'related_content_section': related_content_section,
            'blog_articles': blog_articles,
            'AFFILIATE_ENABLED': affiliate_settings['enabled'],
            'AFFILIATE_TEXTLINKS_ENABLED': affiliate_settings['textlinks_enabled'],
            'AFFILIATE_BANNERS_ENABLED': affiliate_settings['banners_enabled'],
            'AFFILIATE_STACK_ONLY': affiliate_settings['stack_only'],
            'AFFILIATE_NETWORK': affiliate_settings['network'],
            'AFFILIATE_EXCLUDE_PATHS': affiliate_settings['exclude_paths'],
            'AFFILIATE_ALLOWED_PAGE_TYPES': affiliate_settings['allowed_page_types'],
            'AFFILIATE_WIDGET_DESKTOP_ENABLED': affiliate_settings['widget_desktop_enabled'],
            'AFFILIATE_WIDGET_TABLET_ENABLED': affiliate_settings['widget_tablet_enabled'],
            'AFFILIATE_WIDGET_MOBILE_ENABLED': affiliate_settings['widget_mobile_enabled'],
            'AFFILIATE_ROTATION_BANNER_ENABLED': affiliate_settings['rotation_banner_enabled'],
            'AMAZON_AFFILIATE_ENABLED': bool(amazon_affiliate.get('enabled')),
            'amazon_affiliate': amazon_affiliate,
            'amazon_affiliate_items': amazon_affiliate.get('items', []),
            'amazon_affiliate_purpose_items': amazon_affiliate_upper_items,
            'amazon_affiliate_upper_items': amazon_affiliate_upper_items,
            'amazon_affiliate_mid_items': amazon_affiliate_mid_items,
            'amazon_search_url': build_amazon_search_url,
            'affiliate_page_type': affiliate_page_type,
            'affiliate_path_excluded': affiliate_is_path_excluded(current_path),
            'affiliate_top_slot_id': affiliate_top_slot_id(current_path),
            'affiliate_top_slot_mode': affiliate_top_slot_mode(current_path),
            'affiliate_footer_slot_id': affiliate_footer_slot_id(current_path),
            'affiliate_side_rail_enabled': affiliate_side_rail_enabled(current_path),
            'affiliate_can_render_textlinks': affiliate_can_render_textlinks,
            'affiliate_can_render_slot': affiliate_can_render_slot,
            'affiliate_get_slot_config': affiliate_get_slot_config
        }
    except Exception as e:
        request_id = getattr(g, 'request_id', 'unknown') if hasattr(g, 'request_id') else 'unknown'
        import traceback
        current_path = request.path if has_request_context() else '/'
        affiliate_settings = get_affiliate_settings()
        logger.exception(
            f"context_processor_error rid={request_id} products_empty_reason={type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        )
        from lib.nav import get_nav_sections_fallback, get_footer_columns
        return {
            'ADSENSE_ENABLED': False,
            'app_version': '1.0.0',
            'products': [],
            'products_catalog': [],
            'nav_sections': get_nav_sections_fallback(),
            'footer_columns': get_footer_columns(),
            'BASE_URL': os.getenv('BASE_URL', 'https://oshigoto.onrender.com').rstrip('/'),
            'GA_MEASUREMENT_ID': '',
            'GSC_VERIFICATION_CONTENT': '',
            'OPERATOR_NAME': '',
            'OPERATOR_EMAIL': '',
            'OPERATOR_LOCATION': '',
            'OPERATOR_NOTE': '',
            'seo_page_defaults': {},
            'seo_page_description': '',
            'seo_page_robots': 'index,follow',
            'seo_page_kind': 'page',
            'seo_breadcrumb_items': [{'name': '繝帙・繝', 'url': '/'}],
            'seo_web_application_schema': None,
            'seo_article_schema': None,
            'build_breadcrumb_items': build_breadcrumb_items,
            'split_visible_sentences': split_visible_sentences,
            'related_content_section': None,
            'blog_articles': [],
            'AFFILIATE_ENABLED': affiliate_settings['enabled'],
            'AFFILIATE_TEXTLINKS_ENABLED': affiliate_settings['textlinks_enabled'],
            'AFFILIATE_BANNERS_ENABLED': affiliate_settings['banners_enabled'],
            'AFFILIATE_STACK_ONLY': affiliate_settings['stack_only'],
            'AFFILIATE_NETWORK': affiliate_settings['network'],
            'AFFILIATE_EXCLUDE_PATHS': affiliate_settings['exclude_paths'],
            'AFFILIATE_ALLOWED_PAGE_TYPES': affiliate_settings['allowed_page_types'],
            'AFFILIATE_WIDGET_DESKTOP_ENABLED': affiliate_settings['widget_desktop_enabled'],
            'AFFILIATE_WIDGET_TABLET_ENABLED': affiliate_settings['widget_tablet_enabled'],
            'AFFILIATE_WIDGET_MOBILE_ENABLED': affiliate_settings['widget_mobile_enabled'],
            'AFFILIATE_ROTATION_BANNER_ENABLED': affiliate_settings['rotation_banner_enabled'],
            'AMAZON_AFFILIATE_ENABLED': False,
            'amazon_affiliate': {'enabled': False, 'items': [], 'keywords': [], 'error': 'context_fallback', 'source': 'none'},
            'amazon_affiliate_items': [],
            'amazon_affiliate_purpose_items': [],
            'amazon_affiliate_upper_items': [],
            'amazon_affiliate_mid_items': [],
            'amazon_search_url': build_amazon_search_url,
            'affiliate_page_type': get_affiliate_page_type(current_path),
            'affiliate_path_excluded': affiliate_is_path_excluded(current_path),
            'affiliate_top_slot_id': affiliate_top_slot_id(current_path),
            'affiliate_top_slot_mode': affiliate_top_slot_mode(current_path),
            'affiliate_footer_slot_id': affiliate_footer_slot_id(current_path),
            'affiliate_side_rail_enabled': affiliate_side_rail_enabled(current_path),
            'affiliate_can_render_textlinks': affiliate_can_render_textlinks,
            'affiliate_can_render_slot': affiliate_can_render_slot,
            'affiliate_get_slot_config': affiliate_get_slot_config
        }


# P0-1 SEO: 譛ｫ蟆ｾ繧ｹ繝ｩ繝・す繝･豁｣隕丞喧・磯㍾隍ⅡRL蟇ｾ遲厄ｼ峨ょｭ伜惠縺吶ｋ繝ｫ繝ｼ繝医・縺ｿ 301 縺ｧ canonical 縺ｸ縲ょｭ伜惠縺励↑縺・URL 縺ｯ繝ｪ繝繧､繝ｬ繧ｯ繝医＠縺ｪ縺・・
@app.before_request
def normalize_trailing_slash():
    path = request.path
    if path == '/' or not path.endswith('/'):
        return None
    if path.startswith('/static/') or path.startswith('/api/'):
        return None
    if request.method not in ('GET', 'HEAD'):
        return None
    new_path = path.rstrip('/') or '/'
    try:
        adapter = app.url_map.bind_to_environ(request.environ)
        adapter.match(new_path, method=request.method)
    except (NotFound, MethodNotAllowed):
        return None  # 蟄伜惠縺励↑縺・Ν繝ｼ繝医↓縺ｯ繝ｪ繝繧､繝ｬ繧ｯ繝医＠縺ｪ縺・ｼ・04縺ｮ縺ｾ縺ｾ・・
    location = new_path + ('?' + request.query_string.decode() if request.query_string else '')
    return redirect(location, code=301)


# P0-2 SEO: 蜍慕噪繝ｻ荳譎ら噪URL縺ｮ繧､繝ｳ繝・ャ繧ｯ繧ｹ蛻ｶ蠕｡・・-Robots-Tag・・
_NOINDEX_PATHS = frozenset()

@app.after_request
def add_noindex_for_dynamic(response):
    path = request.path
    if path.startswith('/api/'):
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    elif path in _NOINDEX_PATHS:
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    elif is_noindex_path(path):
        response.headers['X-Robots-Tag'] = 'noindex, follow'
    return response



def get_system_resources():
    """Return lightweight process resource usage for health endpoints."""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        if memory_mb > MEMORY_WARNING_MB:
            logger.warning(
                "high_memory_usage memory_mb=%.1f warning_threshold=%s",
                memory_mb,
                MEMORY_WARNING_MB,
            )
        if memory_mb > MEMORY_LIMIT_MB:
            logger.error(
                "memory_limit_exceeded memory_mb=%.1f limit=%s",
                memory_mb,
                MEMORY_LIMIT_MB,
            )
        return {'memory_mb': memory_mb, 'cpu_percent': cpu_percent}
    except Exception as exc:
        logger.error("resource_monitoring_error error=%s", exc)
        return {'memory_mb': 0, 'cpu_percent': 0}

@app.route('/')
def index():
    """Render the public landing page."""
    # 諱剃ｹ・ｯｾ遲厄ｼ壹ヨ繝・・繝壹・繧ｸ繧堤ｵｶ蟇ｾ縺ｫ關ｽ縺ｨ縺輔↑縺・ｼ井ｾ晏ｭ倥ョ繝ｼ繧ｿ縺悟叙繧後↑縺・ｴ蜷医〒繧ょ乾蛹冶｡ｨ遉ｺ縺ｧ閠舌∴繧具ｼ・
    # context_processor縺ｧ譌｢縺ｫproducts縺梧ｳｨ蜈･縺輔ｌ縺ｦ縺・ｋ縺溘ａ縲∵・遉ｺ逧・↓貂｡縺吝ｿ・ｦ√・縺ｪ縺・
    # 縺溘□縺励√ユ繝ｳ繝励Ξ繝ｼ繝医〒products縺梧悴螳夂ｾｩ縺ｮ蝣ｴ蜷医↓蛯吶∴縺ｦ縲∵・遉ｺ逧・↓貂｡縺・
    
    # 繧ｹ繝・ャ繝・: 陬ｽ蜩∽ｸ隕ｧ縺ｯ products_catalog 縺九ｉ蜿門ｾ暦ｼ亥､夜Κ萓晏ｭ倥↑縺励・關ｽ縺｡縺ｪ縺・ｼ・
    products = []
    try:
        from lib.products_catalog import PRODUCTS
        products = list(PRODUCTS) if isinstance(PRODUCTS, list) else []
    except Exception as import_error:
        request_id = getattr(g, 'request_id', 'unknown')
        logger.warning(
            f"landing_page_products_empty rid={request_id} reason=import_failed "
            f"exception={type(import_error).__name__} error={str(import_error)}"
        )
    
    # 繧ｹ繝・ャ繝・: 繝・Φ繝励Ξ繝ｼ繝医Ξ繝ｳ繝繝ｪ繝ｳ繧ｰ・亥､ｱ謨励＠縺ｦ繧ょ乾蛹冶｡ｨ遉ｺ繧定ｿ斐☆・・
    try:
        # 繝・Φ繝励Ξ繝ｼ繝医↓譏守､ｺ逧・↓貂｡縺呻ｼ・ontext_processor縺ｮ繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ・・
        # products縺檎ｩｺ縺ｮ繝ｪ繧ｹ繝医〒繧ゅ√ユ繝ｳ繝励Ξ繝ｼ繝医〒螳牙・縺ｫ蜃ｦ逅・＆繧後ｋ
        return render_template('landing.html', products=products)
    except Exception as render_error:
        # 繝・Φ繝励Ξ繝ｼ繝医Ξ繝ｳ繝繝ｪ繝ｳ繧ｰ譎ゅ・萓句､悶ｒ繝ｭ繧ｰ縺ｫ險倬鹸
        request_id = getattr(g, 'request_id', 'unknown')
        logger.exception(
            f"landing_page_render_failed rid={request_id} path={request.path if request else 'unknown'} "
            f"error={str(render_error)} exception_type={type(render_error).__name__}"
        )
        
        # 諱剃ｹ・ｯｾ遲厄ｼ壹お繝ｩ繝ｼ繝壹・繧ｸ縺ｧ縺ｯ縺ｪ縺上∝乾蛹冶｡ｨ遉ｺ縺ｮHTML繧堤峩謗･霑斐☆
        # 縺薙ｌ縺ｫ繧医ｊ縲√ヨ繝・・繝壹・繧ｸ縺ｯ蟶ｸ縺ｫ200繧定ｿ斐☆
        from flask import make_response
        degraded_html = f'''<!doctype html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>縺励＃縺ｨ驕灘・邂ｱ</title>
    <style>
        body {{
            font-family: 'Noto Sans JP', sans-serif;
            margin: 0;
            padding: 40px 20px;
            background: linear-gradient(135deg, #121212 0%, #1A1A1A 50%, #0F0F0F 100%);
            color: #FFFFFF;
            line-height: 1.8;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(0, 0, 0, 0.35);
            border-radius: 20px;
            padding: 40px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        h1 {{
            color: #FFFFFF;
            font-size: 2.5em;
            margin-bottom: 20px;
        }}
        p {{
            color: rgba(255, 255, 255, 0.9);
            margin-bottom: 20px;
        }}
        .warning {{
            background: rgba(255, 152, 0, 0.1);
            border-left: 4px solid #FF9800;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        a {{
            color: #4A9EFF;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>縺励＃縺ｨ驕灘・邂ｱ</h1>
        <p>縺励＃縺ｨ縺ｮ蟆上＆縺ｪ髱｢蛟偵ｒ縲√＆縺｣縺ｨ迚・▼縺代ｋ霆ｽ驥上ヤ繝ｼ繝ｫ髮・〒縺吶・/p>
        
        <div class="warning">
            <p><strong>笞・・荳譎ら噪縺ｪ陦ｨ遉ｺ縺ｮ蝠城｡・/strong></p>
            <p>迴ｾ蝨ｨ縲∬｣ｽ蜩∵ュ蝣ｱ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ蝠城｡後′逋ｺ逕溘＠縺ｦ縺・∪縺吶ゅ＠縺ｰ繧峨￥蠕・▲縺ｦ縺九ｉ蜀榊ｺｦ縺願ｩｦ縺励￥縺縺輔＞縲・/p>
            <p>莉･荳九・繝ｪ繝ｳ繧ｯ縺九ｉ逶ｴ謗･繧｢繧ｯ繧ｻ繧ｹ縺ｧ縺阪∪縺呻ｼ・/p>
            <ul>
                <li><a href="/tools">驕灘・邂ｱ荳隕ｧ</a></li>
                <li><a href="/tools/pdf">PDF繝・・繝ｫ</a></li>
                <li><a href="/tools/csv">CSV/Excel繝・・繝ｫ</a></li>
                <li><a href="/about">繧ｵ繧､繝医↓縺､縺・※</a></li>
            </ul>
        </div>
        
        <p style="margin-top: 40px; font-size: 0.9em; color: rgba(255, 255, 255, 0.7);">
            蝠城｡後′隗｣豎ｺ縺励↑縺・ｴ蜷医・縲・a href="/contact">縺雁撫縺・粋繧上○</a>縺九ｉ縺秘｣邨｡縺上□縺輔＞縲・
        </p>
    </div>
</body>
</html>'''
        resp = make_response(degraded_html, 200)
        resp.headers['X-Degraded-Mode'] = 'true'
        return resp

@app.route('/autofill')
def autofill():
    """Legacy public URL: redirect to the tools hub."""
    return redirect('/tools', code=301)

@app.route('/privacy')
def privacy():
    """Render the privacy policy page."""
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    """Render the terms page."""
    return render_template('terms.html')

@app.route('/contact')
def contact():
    """Render the contact page."""
    return render_template('contact.html')

@app.route('/guide')
def guide_index():
    """Render the public guide index."""
    try:
        from lib.products_catalog import get_public_products
        products = get_public_products()
    except Exception:
        products = []
    return render_template('guide/index.html', products=products)








@app.route('/guide/image-batch')
def guide_image_batch():
    """Render the image batch conversion guide."""
    return render_template('guide/image-batch.html')

@app.route('/guide/pdf')
def guide_pdf():
    """Render the PDF utility guide."""
    return render_template('guide/pdf.html')

@app.route('/guide/image-cleanup')
def guide_image_cleanup():
    """Render the image cleanup guide."""
    return render_template('guide/image-cleanup.html')


@app.route('/guide/seo')
def guide_seo():
    """Render the SEO utility guide."""
    return render_template('guide/seo.html')

@app.route('/guide/csv')
def guide_csv():
    """Render the CSV and Excel guide."""
    return render_template('guide/csv.html')

@app.route('/tools/image-batch')
def tools_image_batch():
    """Render the image batch conversion tool."""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/image-batch')
    return render_template('tools/image-batch.html', product=product)

@app.route('/tools/pdf')
def tools_pdf():
    """Render the PDF utility tool."""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/pdf')
    return render_template('tools/pdf.html', product=product)


# PDF lock API: request-scoped BytesIO only, no shared output directory.
PDF_API_MAX_BYTES = MAX_FILE_BYTES


def _pdf_api_error(error_code, status=400, retry_after=None):
    rid = getattr(g, 'request_id', None) or uuid.uuid4().hex[:12]
    response = jsonify(success=False, error_code=error_code, request_id=rid)
    response.status_code = status
    if retry_after is not None:
        response.headers['Retry-After'] = str(int(retry_after))
    return response


def _read_upload_bytes(file_storage, max_bytes):
    data = file_storage.stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError('file_too_large')
    if not data:
        raise ValueError('empty_file')
    return data


def _safe_locked_pdf_name(filename):
    safe_name = secure_filename(filename or 'document.pdf') or 'document.pdf'
    base = safe_name[:-4] if safe_name.lower().endswith('.pdf') else safe_name
    return f'{base}_locked.pdf'


@app.route('/api/pdf/lock', methods=['POST'])
def api_pdf_lock():
    """Encrypt an uploaded PDF with the supplied password."""
    acquired = False
    try:
        if request.content_length and request.content_length > MAX_TOTAL_UPLOAD_BYTES:
            return _pdf_api_error('total_upload_too_large', 413)
        files = [f for f in request.files.getlist('file') if f and f.filename]
        if len(files) > MAX_FILES_PER_REQUEST:
            return _pdf_api_error('too_many_files', 413)
        if len(files) > 1:
            return _pdf_api_error('single_file_only', 400)
        file = files[0] if files else None
        password = (request.form.get('password') or '').strip()
        if not file:
            return _pdf_api_error('file_required')
        if not password:
            return _pdf_api_error('missing_password')

        acquired = _PDF_JOB_SEMAPHORE.acquire(blocking=False)
        if not acquired:
            return _pdf_api_error('pdf_jobs_busy', 429, retry_after=PDF_JOB_RETRY_AFTER_SEC)

        try:
            pdf_bytes = _read_upload_bytes(file, PDF_API_MAX_BYTES)
        except ValueError as e:
            status = 413 if str(e) == 'file_too_large' else 400
            return _pdf_api_error(str(e), status)
        except Exception:
            return _pdf_api_error('read_failed', 400)

        try:
            from lib.pdf_lock import encrypt_pdf
            out_bytes = encrypt_pdf(
                pdf_bytes,
                password,
                max_pages=MAX_PDF_PAGES,
                max_output_bytes=MAX_OUTPUT_BYTES,
            )
        except ValueError as e:
            err = str(e)
            if err == 'already_encrypted':
                return _pdf_api_error('already_encrypted', 400)
            if err == 'corrupt_pdf':
                return _pdf_api_error('corrupt_pdf', 422)
            if err == 'unsupported_pdf':
                return _pdf_api_error('unsupported_pdf', 422)
            if err == 'too_many_pages':
                return _pdf_api_error('too_many_pages', 413)
            if err == 'output_too_large':
                return _pdf_api_error('output_too_large', 413)
            return _pdf_api_error('encrypt_failed', 400)
        except Exception as e:
            rid = getattr(g, 'request_id', None) or uuid.uuid4().hex[:12]
            logging.getLogger(__name__).warning('pdf_lock_encrypt_failed request_id=%s error_type=%s', rid, type(e).__name__)
            logging.getLogger(__name__).debug('pdf lock encrypt_failed traceback', exc_info=True)
            return jsonify(success=False, error_code='encrypt_failed', request_id=rid), 400
        from io import BytesIO
        return send_file(
            BytesIO(out_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=_safe_locked_pdf_name(file.filename),
        )
    except Exception as e:
        rid = getattr(g, 'request_id', None) or uuid.uuid4().hex[:12]
        logging.getLogger(__name__).exception('pdf_lock_failed request_id=%s error_type=%s', rid, type(e).__name__)
        return jsonify(success=False, error_code='unsupported', request_id=rid), 500
    finally:
        if acquired:
            _PDF_JOB_SEMAPHORE.release()


@app.route('/tools/image-cleanup')
def tools_image_cleanup():
    """Render the image cleanup tool."""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/image-cleanup')
    return render_template('tools/image-cleanup.html', product=product)



@app.route('/tools/seo')
def tools_seo():
    """Render the SEO utility tool."""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/seo')
    return render_template('tools/seo.html', product=product)

@app.route('/tools/csv')
def tools_csv():
    """Render the CSV and Excel utility tool."""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/csv')
    return render_template('tools/csv.html', product=product)


@app.route('/api/seo/crawl-urls', methods=['POST'])
def api_seo_crawl_urls():
    """Crawl URLs from the same host and return discovered URLs for sitemap checks."""
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}
    start_url = (data.get('start_url') or '').strip()
    if not start_url:
        return jsonify(success=False, error='start_url is required'), 400

    from lib.seo_crawler import crawl, is_url_safe_for_crawl
    safe, err_msg = is_url_safe_for_crawl(start_url)
    if not safe:
        return jsonify(success=False, error=err_msg or '縺薙・URL縺ｯ險ｱ蜿ｯ縺輔ｌ縺ｦ縺・∪縺帙ｓ'), 400

    max_urls = data.get('max_urls', 300)
    max_depth = data.get('max_depth', 3)
    try:
        max_urls = int(max_urls)
        max_depth = int(max_depth)
    except (TypeError, ValueError):
        max_urls = 300
        max_depth = 3
    max_urls = max(1, min(1000, max_urls))
    max_depth = max(0, min(10, max_depth))

    urls, warnings = crawl(
        start_url=start_url,
        max_urls=max_urls,
        max_depth=max_depth,
        request_timeout=5,
        total_timeout=60
    )
    return jsonify(success=True, urls=urls, warnings=warnings)


@app.route('/tools')
def tools_index():
    """Render the tools index page."""
    try:
        from lib.products_catalog import get_public_products
        products = get_public_products()
    except Exception as import_error:
        logger.warning(
            f"tools_page_products_empty reason=import_failed exception={type(import_error).__name__} error={str(import_error)}"
        )
        products = []
    return render_template('tools/index.html', products=products)

@app.route('/faq')
def faq():
    """Render the FAQ page."""
    return render_template('faq.html')

@app.route('/glossary')
def glossary():
    """Render the glossary page."""
    return render_template('glossary.html')

@app.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')





@app.route('/best-practices')
def best_practices():
    """Render the public best practices page."""
    return render_template('best-practices.html')

@app.route('/blog')
def blog_index():
    """Render the blog index."""
    return render_template('blog/index.html')







@app.route('/blog/excel-format-mistakes-and-design')
def blog_excel_format_mistakes_and_design():
    """Render the Excel formatting article."""
    return render_template('blog/excel-format-mistakes-and-design.html')








@app.route('/sitemap.html')
def sitemap_html():
    """Render the HTML sitemap page."""
    return render_template('sitemap.html')

# === 繝倥Ν繧ｹ繝√ぉ繝・け繧ｨ繝ｳ繝峨・繧､繝ｳ繝茨ｼ・ender逕ｨ繝ｻ雜・ｻｽ驥擾ｼ・===
@app.route('/healthz')
def healthz():
    """Lightweight health check for Render."""
    try:
        # 譛蟆城剞縺ｮ繝√ぉ繝・け・壹い繝励Μ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ縺悟ｿ懃ｭ泌庄閭ｽ縺・
        return Response('ok', mimetype='text/plain', headers={'Cache-Control': 'no-store'})
    except Exception as e:
        # 繝ｭ繧ｰ縺ｫ險倬鹸縺励※縺九ｉ503繧定ｿ斐☆
        logger.error(f"healthz_check_failed error={str(e)}")
        return Response(f'health check failed: {str(e)}', status=503, mimetype='text/plain')

@app.route('/livez')
def livez():
    """Liveness check for process monitoring."""
    return Response('ok', mimetype='text/plain', headers={'Cache-Control': 'no-store'})

@app.route('/readyz')
def readyz():
    """Readiness check for Render and uptime monitors."""
    try:
        resources = get_system_resources()
        if resources['memory_mb'] > MEMORY_LIMIT_MB:
            logger.error(
                "memory_limit_exceeded current=%.1fMB limit=%sMB",
                resources['memory_mb'],
                MEMORY_LIMIT_MB,
            )
            return Response(
                f'memory limit exceeded: {resources["memory_mb"]:.1f}MB',
                status=503,
                mimetype='text/plain',
            )
        return Response('ok', mimetype='text/plain', headers={'Cache-Control': 'no-store'})
    except Exception as exc:
        logger.error("readyz_check_failed error=%s", exc)
        return Response(f'not ready: {exc}', status=503, mimetype='text/plain')

@app.route('/ping')
def ping():
    """Simple ping endpoint for uptime monitors."""
    return jsonify({'status': 'ok', 'message': 'pong', 'timestamp': datetime.now().isoformat()})

@app.route('/health')
def health():
    """Detailed health check for diagnostics."""
    try:
        resources = get_system_resources()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'dependencies': {'openpyxl': True},
            'resources': resources,
        })
    except Exception as exc:
        return jsonify({'status': 'unhealthy', 'error': str(exc)}), 500

@app.route('/ready')
def ready():
    """Compatibility readiness endpoint."""
    return jsonify({
        'status': 'ready',
        'timestamp': datetime.now().isoformat(),
        'dependencies': {'openpyxl': True},
    })

@app.route('/health/memory', methods=['GET'])
def health_memory():
    """Process memory diagnostics without browser/session counters."""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        system_memory = psutil.virtual_memory()
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'process_memory': {
                'rss_mb': round(memory_info.rss / 1024 / 1024, 2),
                'vms_mb': round(memory_info.vms / 1024 / 1024, 2),
                'percent': round(process.memory_percent(), 2),
            },
            'system_memory': {
                'total_mb': round(system_memory.total / 1024 / 1024, 2),
                'available_mb': round(system_memory.available / 1024 / 1024, 2),
                'used_mb': round(system_memory.used / 1024 / 1024, 2),
                'percent': round(system_memory.percent, 2),
            },
            'limits': {
                'memory_limit_mb': MEMORY_LIMIT_MB,
                'memory_warning_mb': MEMORY_WARNING_MB,
                'max_file_size_mb': MAX_FILE_SIZE_MB,
            },
            'config': {
                'web_concurrency': os.getenv('WEB_CONCURRENCY', 'unknown'),
                'web_threads': os.getenv('WEB_THREADS', 'unknown'),
                'web_timeout': os.getenv('WEB_TIMEOUT', 'unknown'),
            },
        })
    except Exception as exc:
        return jsonify({'status': 'error', 'error': str(exc)}), 500

@app.route('/ads.txt')
def ads_txt():
    """Serve ads.txt for Google AdSense."""
    content = "google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0"
    return Response(content, mimetype='text/plain')

@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt with the current production sitemap URL."""
    base_url = (os.getenv('BASE_URL') or 'https://oshigoto.onrender.com').rstrip('/')
    content = f"""User-agent: *
Allow: /
Disallow: /autofill
Disallow: /api/

User-agent: Googlebot
Allow: /
Disallow: /autofill
Disallow: /api/

User-agent: Googlebot-Image
Allow: /static/img/

Sitemap: {base_url}/sitemap.xml
"""
    return Response(content, mimetype='text/plain')


_SITEMAP_LASTMOD_CACHE = None


def _sitemap_template_for_path(url_path):
    path = (url_path or '').strip('/')
    special = {
        '': 'landing.html',
        'guide': 'guide/index.html',
        'blog': 'blog/index.html',
        'tools': 'tools/index.html',
        'sitemap.html': 'sitemap.html',
    }
    if path in special:
        return special[path]
    if path.startswith('guide/'):
        return 'guide/' + path.split('/', 1)[1] + '.html'
    if path.startswith('blog/'):
        return 'blog/' + path.split('/', 1)[1] + '.html'
    if path.startswith('tools/'):
        return 'tools/' + path.split('/', 1)[1] + '.html'
    return path + '.html'


def _load_sitemap_lastmod_manifest():
    global _SITEMAP_LASTMOD_CACHE
    if _SITEMAP_LASTMOD_CACHE is not None:
        return _SITEMAP_LASTMOD_CACHE
    manifest_path = os.path.join(app.root_path, 'data', 'sitemap_lastmod.json')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _SITEMAP_LASTMOD_CACHE = data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning('sitemap_lastmod_manifest_load_failed error=%s', exc)
        _SITEMAP_LASTMOD_CACHE = {}
    return _SITEMAP_LASTMOD_CACHE


def _sitemap_lastmod_for_path(url_path):
    template_path = _sitemap_template_for_path(url_path)
    return _load_sitemap_lastmod_manifest().get(template_path)
@app.route('/sitemap.xml')
def sitemap():
    """Generate the XML sitemap from public product and guide routes."""
    from flask import url_for
    from datetime import datetime
    
    # PRODUCTS縺ｮ繧､繝ｳ繝昴・繝茨ｼ亥､ｱ謨励＠縺ｦ繧らｶ夊｡鯉ｼ・
    try:
        from lib.products_catalog import get_public_products
        PRODUCTS = get_public_products()
    except Exception as import_error:
        logger.warning(f"sitemap_import_failed error={str(import_error)} - using empty list")
        PRODUCTS = []
    
    # 繝吶・繧ｹURL・育腸蠅・､画焚縺後≠繧後・謗｡逕ｨ縲∵忰蟆ｾ繧ｹ繝ｩ繝・す繝･縺ｯ髯､蜴ｻ縺励※莠碁㍾繧ｹ繝ｩ繝・す繝･繧帝亟縺撰ｼ・
    base_url = (os.getenv('BASE_URL') or 'https://oshigoto.onrender.com').rstrip('/')
    
    # 迴ｾ蝨ｨ譌･莉倥ｒ蜿門ｾ暦ｼ・astmod 縺ｮ繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ・・
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 繧ｵ繧､繝医・繝・・縺ｫ蜷ｫ繧√ｋURL縺ｮ繝ｪ繧ｹ繝・
    # 蠖｢蠑・ (url_path, changefreq, priority, lastmod)
    # P0-1: 蝗ｺ螳壹・繝ｼ繧ｸ縺ｯ邯ｭ謖・
    urls = [
        # 荳ｻ隕√・繝ｼ繧ｸ
        ('/', 'daily', '1.0', today),
        ('/about', 'monthly', '0.8', today),
        ('/privacy', 'monthly', '0.5', today),
        ('/terms', 'monthly', '0.5', today),
        ('/contact', 'monthly', '0.5', today),
        ('/faq', 'weekly', '0.8', today),
        ('/glossary', 'monthly', '0.7', today),
        ('/best-practices', 'monthly', '0.7', today),
        
        # 繧ｬ繧､繝峨・繝ｼ繧ｸ・井ｸ隕ｧ・句崋螳夲ｼ・
        ('/guide', 'weekly', '0.9', today),
        
        # 繝・・繝ｫ荳隕ｧ繝壹・繧ｸ
        ('/tools', 'weekly', '0.9', today),
        
        # 繝悶Ο繧ｰ荳隕ｧ
        ('/blog', 'daily', '0.8', today),
        
        ('/blog/excel-format-mistakes-and-design', 'monthly', '0.7', today),
    ]
    
    # P0-1: PRODUCTS縺九ｉ蛻ｩ逕ｨ蜿ｯ閭ｽ縺ｪ繝・・繝ｫ繝壹・繧ｸ縺ｨ繧ｬ繧､繝峨・繝ｼ繧ｸ繧定・蜍慕函謌・
    # URL驥崎､・ｒ髦ｲ縺舌◆繧√↓縲∵里蟄倥・URL繝代せ繧帝寔蜷医〒邂｡逅・
    seen_urls = {url_path for url_path, _, _, _ in urls}
    
    # PRODUCTS縺後Μ繧ｹ繝医〒縺ゅｋ縺薙→繧堤｢ｺ隱搾ｼ域￡荵・ｯｾ遲厄ｼ壼梛螳牙・諤ｧ・・
    products_list = PRODUCTS if isinstance(PRODUCTS, list) else []
    for product in products_list:
        if product.get('status') == 'available':
            # product.path繧定ｿｽ蜉・磯㍾隍・メ繧ｧ繝・け・・
            product_path = product.get('path')
            if product_path and product_path not in seen_urls:
                # 繝・・繝ｫ繝壹・繧ｸ縺ｮ蜆ｪ蜈亥ｺｦ縺ｨ譖ｴ譁ｰ鬆ｻ蠎ｦ繧定ｨｭ螳・
                changefreq = 'monthly'
                priority = '0.7'
                urls.append((product_path, changefreq, priority, today))
                seen_urls.add(product_path)
            
            # guide_path繧定ｿｽ蜉・磯㍾隍・メ繧ｧ繝・け・・
            guide_path = product.get('guide_path')
            if guide_path and guide_path not in seen_urls:
                urls.append((guide_path, 'monthly', '0.8', today))
                seen_urls.add(guide_path)
    
    # XML繧ｵ繧､繝医・繝・・繧堤函謌・
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    for url_path, changefreq, priority, lastmod_default in urls:
        lastmod = _sitemap_lastmod_for_path(url_path) or lastmod_default
        full_url = base_url + url_path
        xml_parts.append('  <url>')
        xml_parts.append(f'    <loc>{full_url}</loc>')
        xml_parts.append(f'    <changefreq>{changefreq}</changefreq>')
        xml_parts.append(f'    <priority>{priority}</priority>')
        xml_parts.append(f'    <lastmod>{lastmod}</lastmod>')
        xml_parts.append('  </url>')
    
    xml_parts.append('</urlset>')
    
    xml_content = '\n'.join(xml_parts)
    
    return Response(xml_content, mimetype='application/xml')

def monitor_processing_resources(data_index, total_data):
    """Monitor process resources during a request."""
    try:
        resources = get_system_resources()
        memory_usage_percent = (resources['memory_mb'] / MEMORY_LIMIT_MB) * 100
        
        # 4逡ｪ逶ｮ縺ｮ繝・・繧ｿ莉･髯阪・繧医ｊ蜴ｳ蟇・↓逶｣隕・
        if data_index >= 4:
            logger.info(f"processing_monitor data={data_index}/{total_data} memory={resources['memory_mb']:.1f}MB/{MEMORY_LIMIT_MB}MB ({memory_usage_percent:.1f}%) cpu={resources['cpu_percent']:.1f}%")
            
            # 繝｡繝｢繝ｪ菴ｿ逕ｨ邇・′85%繧定ｶ・∴縺溷ｴ蜷医・隴ｦ蜻・
            if memory_usage_percent > 85:
                logger.warning(f"critical_memory_usage data={data_index} memory={resources['memory_mb']:.1f}MB ({memory_usage_percent:.1f}%) - approaching OOM")
                
                # 繝｡繝｢繝ｪ菴ｿ逕ｨ邇・′90%繧定ｶ・∴縺溷ｴ蜷医・邱頑･蛛懈ｭ｢
                if memory_usage_percent > 90:
                    logger.error(f"emergency_memory_stop data={data_index} memory={resources['memory_mb']:.1f}MB ({memory_usage_percent:.1f}%) - preventing OOM")
                    raise RuntimeError(f"繝｡繝｢繝ｪ菴ｿ逕ｨ邇・′蜊ｱ髯ｺ蝓溘↓驕斐＠縺ｾ縺励◆: {memory_usage_percent:.1f}%")
        
        return True
    except Exception as e:
        logger.error(f"processing_monitor_failed data={data_index} error={str(e)}")
        raise

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
