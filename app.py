#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
import threading
import tempfile
import shutil
import psutil
import time
import logging
import hashlib
import re
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file, Response, redirect, g, has_request_context
from werkzeug.exceptions import NotFound, MethodNotAllowed
from werkzeug.middleware.proxy_fix import ProxyFix

from utils import allowed_file, create_template_excel, create_previous_month_template_excel
from automation import process_jobcan_automation
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
    build_rotating_theme_cards as build_amazon_rotating_theme_cards,
    get_recommendations as get_amazon_recommendations,
)

# P1-1: 計測ログユーティリティ（循環import回避）
try:
    from diagnostics.runtime_metrics import log_memory
    metrics_available = True
except ImportError:
    metrics_available = False
    def log_memory(tag, job_id=None, session_id=None, extra=None):
        pass

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# メモリ制限設定（環境変数から取得、デフォルト値付き）
# P0-4: 閾値の整合性を修正（WARNING < LIMIT）
MEMORY_LIMIT_MB = int(os.getenv("MEMORY_LIMIT_MB", "450"))
MEMORY_WARNING_MB = int(os.getenv("MEMORY_WARNING_MB", "400"))

# P0-4: 起動時に閾値矛盾を検知して警告
if MEMORY_WARNING_MB >= MEMORY_LIMIT_MB:
    logger.warning(f"memory_threshold_mismatch WARNING_MB={MEMORY_WARNING_MB} >= LIMIT_MB={MEMORY_LIMIT_MB} - auto_correcting")
    # 自動補正: WARNINGをLIMITの90%に設定
    MEMORY_WARNING_MB = int(MEMORY_LIMIT_MB * 0.9)
    logger.warning(f"memory_threshold_auto_corrected WARNING_MB={MEMORY_WARNING_MB} LIMIT_MB={MEMORY_LIMIT_MB}")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
# Render本番では同時実行を直列化（512MB/0.5CPUで複数Playwrightは高リスク）。未設定時はRENDER検知で1に寄せる
_default_sessions = "1" if os.getenv("RENDER") else "20"
MAX_ACTIVE_SESSIONS = int(os.getenv("MAX_ACTIVE_SESSIONS", _default_sessions))
# ジョブ全体のハードタイムアウト（秒）。超過でstatus=timeoutに遷移
JOB_TIMEOUT_SEC = int(os.getenv("JOB_TIMEOUT_SEC", "300"))  # 5分

app = Flask(__name__)
# Phase 5: Render 等プロキシ配下で実クライアント IP を request.remote_addr に反映（単段プロキシ前提）
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# 起動時の検証（恒久対策：テンプレートとモジュールの存在確認）
def validate_startup():
    """アプリケーション起動時に主要リソースの存在を確認"""
    errors = []
    
    # 主要テンプレートの存在確認
    required_templates = [
        'landing.html',
        'error.html',
        'includes/header.html',
        'includes/footer.html',
        'includes/head_meta.html',
        'includes/structured_data.html',
        'includes/affiliate_disclosure.html',
        'includes/affiliate_slot.html',
        'includes/affiliate_text_links.html'
    ]
    for template in required_templates:
        try:
            app.jinja_env.get_template(template)
        except Exception as e:
            errors.append(f"Template not found or invalid: {template} - {str(e)}")
    
    # 製品カタログ（products_catalog）のインポート確認（LP/500 根本対策）
    try:
        from lib.products_catalog import PRODUCTS, get_public_products
        if not isinstance(PRODUCTS, list):
            errors.append("products_catalog.PRODUCTS is not a list")
        elif len(PRODUCTS) == 0:
            errors.append("products_catalog.PRODUCTS is empty")
    except Exception as e:
        errors.append(f"Failed to import products_catalog.PRODUCTS: {type(e).__name__}: {str(e)}")
    
    if errors:
        logger.error(f"startup_validation_failed errors={errors}")
        # エラーがあっても起動は続行（本番環境で起動できないのを防ぐ）
    else:
        logger.info("startup_validation_passed all checks OK")

# 起動時に検証を実行
validate_startup()

# アップロードフォルダの設定
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === Phase 5: インメモリレート制限（固定窓） ===
from collections import deque as _deque

def _rate_limit_path_group(path, method):
    """path と method からレート制限グループを返す。除外なら None。"""
    if path.startswith(('/healthz', '/livez', '/readyz', '/ping', '/health', '/ready', '/static/')):
        return None
    if path in ('/robots.txt', '/sitemap.xml', '/ads.txt'):
        return None
    if path == '/upload' and method == 'POST':
        return 'upload'
    if path.startswith('/status/'):
        return 'status'
    if path.startswith('/api/'):
        if path.startswith('/api/seo/crawl-urls'):
            return None  # 既存の 1/min 制限に任せる
        return 'api'
    return None

class RateLimiter:
    """固定窓: (key -> deque of timestamps)。窓秒を超えた古いものを捨ててから件数判定。"""
    def __init__(self, window_sec=60):
        self.window_sec = window_sec
        self._data = {}
        self._lock = threading.Lock()

    def is_allowed(self, key, max_per_window):
        with self._lock:
            now = time.time()
            if key not in self._data:
                self._data[key] = _deque(maxlen=max_per_window * 2)
            q = self._data[key]
            while q and now - q[0] > self.window_sec:
                q.popleft()
            if len(q) >= max_per_window:
                return False, self.window_sec
            q.append(now)
            return True, self.window_sec

# 制限値（弱めから）: upload 10/min, status 120/min, api 60/min
_RATE_LIMITS = {'upload': 10, 'status': 120, 'api': 60}
_rate_limiter = RateLimiter(window_sec=60)

@app.before_request
def rate_limit_check():
    """Phase 5: レート制限。超過時は 429 + Retry-After。"""
    path = request.path
    method = request.method
    group = _rate_limit_path_group(path, method)
    if group is None:
        return None
    client_ip = request.remote_addr or 'unknown'
    key = f"{client_ip}:{group}"
    max_per = _RATE_LIMITS.get(group, 60)
    allowed, window_sec = _rate_limiter.is_allowed(key, max_per)
    if not allowed:
        resp = jsonify(
            error='リクエストが多すぎます。しばらく待ってからお試しください。',
            error_code='RATE_LIMIT_EXCEEDED',
            retry_after_sec=window_sec
        )
        resp.status_code = 429
        resp.headers['Retry-After'] = str(int(window_sec))
        return resp
    return None

# === リクエストロギングミドルウェア ===
# P1: prune_jobs実行頻度制御（メモリ最適化）
_last_prune_time = 0
PRUNE_INTERVAL_SECONDS = 300  # 5分ごとにprune_jobsを実行
# get_status 内での prune 間引き（ポーリング負荷軽減）
_last_status_prune_time = 0
STATUS_PRUNE_INTERVAL_SEC = 30  # 30秒に1回まで

@app.before_request
def before_request():
    """リクエスト開始時の処理"""
    global _last_prune_time
    
    g.start_time = time.time()
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:8])
    
    # P1: 定期的にprune_jobsを実行（メモリ最適化）
    # ヘルスチェックや静的ファイルリクエストは除外
    if not request.path.startswith(('/healthz', '/livez', '/readyz', '/static')):
        current_time = time.time()
        if current_time - _last_prune_time >= PRUNE_INTERVAL_SECONDS:
            try:
                prune_jobs(current_time=current_time)
                _last_prune_time = current_time
            except Exception as prune_error:
                # prune_jobsのエラーはログに記録するが、リクエスト処理は続行
                logger.warning(f"prune_jobs_error in before_request: {prune_error}")
    
    # ヘルスチェック以外のリクエストをログ（Phase 5: ua/ref 追加、200文字で切る）
    if not request.path.startswith(('/healthz', '/livez', '/readyz')):
        ua = (request.headers.get('User-Agent') or '')[:200]
        ref = (request.headers.get('Referer') or '')[:200]
        logger.info(
            f"req_start rid={g.request_id} method={request.method} path={request.path} "
            f"ip={request.remote_addr} ua={ua!r} ref={ref!r}"
        )

@app.after_request
def after_request(response):
    """リクエスト終了時の処理"""
    if hasattr(g, 'start_time') and hasattr(g, 'request_id'):
        duration_ms = (time.time() - g.start_time) * 1000
        response.headers['X-Request-ID'] = g.request_id
        deploy_commit = (os.getenv('RENDER_GIT_COMMIT') or os.getenv('GIT_COMMIT') or '').strip()
        if deploy_commit:
            response.headers['X-Deploy-Commit'] = deploy_commit[:12]
        
        # ヘルスチェック以外のリクエストをログ
        if not request.path.startswith(('/healthz', '/livez', '/readyz')):
            level = logging.WARNING if duration_ms > 1000 else logging.INFO
            logger.log(
                level,
                f"req_end rid={g.request_id} method={request.method} path={request.path} "
                f"status={response.status_code} ms={duration_ms:.1f}"
            )
            
            # 遅延警告
            if duration_ms > 5000:
                logger.warning(f"SLOW_REQUEST rid={g.request_id} path={request.path} ms={duration_ms:.1f}")
    
    # キャッシュ対策: text/html のみ no-store（静的ファイルには適用しない）
    if not request.path.startswith('/static/'):
        ct = response.content_type or ''
        if 'text/html' in ct:
            response.headers['Cache-Control'] = 'no-store, max-age=0'
    
    return response

# グローバルエラーハンドラー
def _generate_error_id():
    """エラーIDを生成（短いUUID）"""
    return str(uuid.uuid4())[:8]

def _render_error_page(status_code, error_message, error_id=None):
    """エラーページをレンダリング（共通関数）"""
    if error_id is None:
        error_id = _generate_error_id()
    
    try:
        response = render_template(
            'error.html',
            error_message=error_message,
            error_id=error_id,
            status_code=status_code
        ), status_code
        # レスポンスヘッダにX-Error-Idを付与（恒久対策：エラーIDの追跡強化）
        from flask import make_response
        resp = make_response(response)
        resp.headers['X-Error-Id'] = error_id
        return resp
    except Exception as render_error:
        # エラーテンプレートもレンダリングできない場合はシンプルなHTMLを返す
        import traceback
        logger.exception(f"error_page_render_failed error_id={error_id} render_error={str(render_error)}")
        from flask import make_response
        html_content = f'''<html><head><meta charset="utf-8"><title>エラー {status_code}</title></head>
<body><h1>エラーが発生しました</h1>
<p>{error_message}</p>
<p>エラーID: {error_id}</p>
<p>お問い合わせの際は、このエラーIDをお伝えください。</p>
</body></html>'''
        resp = make_response((html_content, status_code))
        resp.headers['X-Error-Id'] = error_id
        return resp

@app.errorhandler(404)
def not_found(error):
    """404エラーのハンドリング"""
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    logger.warning(
        f"not_found error_id={error_id} rid={request_id} "
        f"path={request.path} method={request.method} "
        f"user_agent={request.headers.get('User-Agent', 'Unknown')} error={str(error)}"
    )
    return _render_error_page(
        404,
        'お探しのページが見つかりませんでした。URLを確認してください。',
        error_id
    )

@app.errorhandler(500)
def internal_error(error):
    """500エラーのハンドリング"""
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    
    # スタックトレースをログに記録（恒久対策：例外ログの強化）
    # logger.exception()を使用してスタックトレースを確実に記録
    # user-agent、remote_addr、例外型も含める
    try:
        path = request.path if request else 'unknown'
        method = request.method if request else 'unknown'
        user_agent = request.headers.get('User-Agent', 'Unknown') if request else 'Unknown'
        remote_addr = request.remote_addr if request else 'unknown'
    except Exception:
        path = 'unknown'
        method = 'unknown'
        user_agent = 'Unknown'
        remote_addr = 'unknown'
    
    logger.exception(
        f"internal_server_error error_id={error_id} rid={request_id} "
        f"path={path} method={method} "
        f"user_agent={user_agent} remote_addr={remote_addr} "
        f"exception_type={type(error).__name__} error={str(error)}"
    )
    
    return _render_error_page(
        500,
        'サーバー側でエラーが発生しました。しばらく待ってから再試行してください。',
        error_id
    )

@app.errorhandler(503)
def service_unavailable(error):
    """503エラーのハンドリング"""
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    try:
        path = request.path if request else 'unknown'
        method = request.method if request else 'unknown'
    except Exception:
        path, method = 'unknown', 'unknown'
    logger.exception(
        f"service_unavailable error_id={error_id} rid={request_id} path={path} method={method} error={str(error)}"
    )
    return _render_error_page(
        503,
        'サービスが一時的に利用できません。しばらく待ってから再試行してください。',
        error_id
    )

@app.errorhandler(Exception)
def handle_exception(e):
    """未処理例外のハンドリング（404以外）"""
    from werkzeug.exceptions import HTTPException
    
    # HTTPException（404, 500等）は適切なハンドラーに委譲
    if isinstance(e, HTTPException):
        # FlaskのHTTPExceptionはそのまま通す（適切なハンドラーが処理する）
        return e
    
    # 404エラーは上記のハンドラーで処理されるため、ここでは処理しない
    if hasattr(e, 'code') and e.code == 404:
        raise e  # 404エラーハンドラーに委譲
    
    error_id = _generate_error_id()
    request_id = getattr(g, 'request_id', 'unknown')
    
    # 詳細なエラー情報をログに記録（恒久対策：例外ログの強化）
    # logger.exception()を使用してスタックトレースを確実に記録
    # user-agent、remote_addr、例外型も含める
    try:
        path = request.path if request else 'unknown'
        method = request.method if request else 'unknown'
        user_agent = request.headers.get('User-Agent', 'Unknown') if request else 'Unknown'
        remote_addr = request.remote_addr if request else 'unknown'
    except Exception:
        path = 'unknown'
        method = 'unknown'
        user_agent = 'Unknown'
        remote_addr = 'unknown'
    
    logger.exception(
        f"unhandled_exception error_id={error_id} rid={request_id} "
        f"path={path} method={method} "
        f"user_agent={user_agent} remote_addr={remote_addr} "
        f"exception_type={type(e).__name__} error={str(e)}"
    )
    
    # HTMLエラーページを返す（APIエンドポイントでもHTMLを返す）
    return _render_error_page(
        500,
        '予期しないエラーが発生しました。しばらく待ってから再試行してください。',
        error_id
    )

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
    normalized = (value or 'rakuten').strip().lower()
    if normalized in ('rakuten', 'rakuten_widget'):
        return 'rakuten'
    if normalized in ('a8_rotation', 'rotation', 'a8'):
        return 'a8_rotation'
    return 'rakuten'


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

NON_UI_AFFILIATE_PATH_PREFIXES = ('/api/', '/status/', '/admin/', '/static/')
NON_UI_AFFILIATE_PATHS = frozenset((
    '/sessions',
    '/cleanup-sessions',
    '/download-template',
    '/download-previous-template',
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

    kind = 'rakuten_widget'
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


AMAZON_RECENT_HISTORY_COOKIE = 'jobcan_recent_affiliate_context'
AMAZON_RECENT_HISTORY_LIMIT = 8


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
        page_type = str(entry.get('page_type') or entry.get('t') or '').strip()
        keywords = entry.get('keywords') or entry.get('k') or []
        if not isinstance(keywords, list):
            keywords = []
        keywords = _dedupe_keep_order([str(v) for v in keywords])[:4]
        cleaned.append({
            'path': path,
            'page_type': page_type,
            'keywords': keywords,
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
        tags.extend(['勤怠', '自動入力', '業務効率化'])
    elif normalized_path.startswith('/guide'):
        tags.extend(['ガイド', '運用', '手順'])
    elif normalized_path.startswith('/blog'):
        tags.extend(['ブログ', '解説', 'ノウハウ'])
    elif normalized_path.startswith('/case'):
        tags.extend(['導入事例', '業務改善'])
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


def _prepare_recent_affiliate_history_cookie(path, page_type, keywords, history):
    if not has_request_context():
        return
    if not _is_public_affiliate_html_path(path):
        return

    entry = {
        'path': path,
        'page_type': page_type,
        'keywords': _dedupe_keep_order([str(v) for v in (keywords or [])])[:4],
    }
    updated = [entry]
    for item in history or []:
        if not isinstance(item, dict):
            continue
        if item.get('path') == path:
            continue
        updated.append({
            'path': str(item.get('path') or ''),
            'page_type': str(item.get('page_type') or ''),
            'keywords': _dedupe_keep_order([str(v) for v in (item.get('keywords') or [])])[:4],
        })
        if len(updated) >= AMAZON_RECENT_HISTORY_LIMIT:
            break

    try:
        g.amazon_recent_history_cookie = json.dumps(updated, separators=(',', ':'))
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
    try:
        response.set_cookie(
            AMAZON_RECENT_HISTORY_COOKIE,
            cookie_value,
            max_age=60 * 60 * 24 * 14,
            secure=request.is_secure,
            httponly=False,
            samesite='Lax',
            path='/',
        )
    except Exception as exc:
        logger.warning("amazon_history_cookie_write_error type=%s detail=%s", type(exc).__name__, str(exc))
    return response


# 環境変数をテンプレートコンテキストに注入（AdSense / Affiliate 設定用）
@app.context_processor
def inject_env_vars():
    """環境変数をテンプレートで使えるようにする。製品一覧は products_catalog から取得（外部依存なし）。"""
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
        base_url = os.getenv('BASE_URL', 'https://jobcan-automation.onrender.com').rstrip('/')
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
            keywords=amazon_affiliate.get('keywords'),
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
            'BASE_URL': os.getenv('BASE_URL', 'https://jobcan-automation.onrender.com').rstrip('/'),
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
            'seo_breadcrumb_items': [{'name': 'ホーム', 'url': '/'}],
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


# P0-1 SEO: 末尾スラッシュ正規化（重複URL対策）。存在するルートのみ 301 で canonical へ。存在しない URL はリダイレクトしない。
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
        return None  # 存在しないルートにはリダイレクトしない（404のまま）
    location = new_path + ('?' + request.query_string.decode() if request.query_string else '')
    return redirect(location, code=301)


# P0-2 SEO: 動的・一時的URLのインデックス制御（X-Robots-Tag）
_NOINDEX_PATHS = frozenset((
    '/download-template', '/download-previous-template', '/sessions', '/cleanup-sessions'
))

@app.after_request
def add_noindex_for_dynamic(response):
    path = request.path
    if path.startswith('/status/') or path.startswith('/api/'):
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    elif path in _NOINDEX_PATHS:
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    elif is_noindex_path(path):
        response.headers['X-Robots-Tag'] = 'noindex, follow'
    return response


# ジョブの状態を管理（スレッドセーフな辞書）
jobs = {}
jobs_lock = threading.Lock()

# 直列実行＋待機キュー（インメモリFIFO）。サーバ再起動でキューは消える
from collections import deque
job_queue = deque()
# queued ジョブの実行用パラメータ（start時にpopして使用。資格情報はstart後即参照しない）
queued_job_params = {}
# queued の最大待機時間（超過でtimeout扱い・ファイル削除）
QUEUED_MAX_WAIT_SEC = int(os.getenv("QUEUED_MAX_WAIT_SEC", "1800"))  # 30分
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "50"))  # キュー上限（メモリ保護）
QUEUE_HEARTBEAT_TIMEOUT_SEC = int(os.getenv("QUEUE_HEARTBEAT_TIMEOUT_SEC", "90"))
QUEUE_DISCONNECT_GRACE_SEC = int(os.getenv("QUEUE_DISCONNECT_GRACE_SEC", "15"))
ACTIVE_CLIENT_STALE_WARNING_SEC = int(os.getenv("ACTIVE_CLIENT_STALE_WARNING_SEC", "180"))

# P0-3: 完了ジョブの保持期間（秒）
JOB_RETENTION_SECONDS = 1800  # 30分

# P1: ジョブログの上限設定（メモリ最適化）。utils.MAX_JOB_LOGSと同期（500）
MAX_JOB_LOGS = 500  # 1ジョブあたりの最大ログ件数
TERMINAL_JOB_STATUSES = frozenset(('completed', 'error', 'timeout', 'cancelled', 'expired', 'failed'))
QUEUE_LIVE_STATUSES = frozenset(('queued', 'running'))
queue_identity_index = {}

# セッション管理とリソース監視
session_manager = {
    'active_sessions': {},
    'session_lock': threading.Lock(),
    'resource_monitor': {
        'last_check': time.time(),
        'memory_usage': 0,
        'cpu_usage': 0,
        'active_browsers': 0
    }
}

def get_system_resources():
    """システムリソースの使用状況を取得（強化版）"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        # メモリ使用量が危険域の場合はログに記録
        if memory_mb > MEMORY_WARNING_MB:
            logger.warning(f"high_memory_usage memory_mb={memory_mb:.1f} warning_threshold={MEMORY_WARNING_MB}")
        if memory_mb > MEMORY_LIMIT_MB:
            logger.error(f"memory_limit_exceeded memory_mb={memory_mb:.1f} limit={MEMORY_LIMIT_MB}")
        
        return {
            'memory_mb': memory_mb,
            'cpu_percent': cpu_percent,
            'active_sessions': len(session_manager['active_sessions'])
        }
    except ImportError:
        logger.warning("psutil_not_available resource_monitoring_disabled")
        return {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': len(session_manager['active_sessions'])}
    except Exception as e:
        logger.error(f"resource_monitoring_error error={str(e)}")
        return {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': len(session_manager['active_sessions'])}

def get_elapsed_sec(job):
    """ジョブの経過秒数を返す。start_time が無い/不正なら None。"""
    if not job:
        return None
    st = job.get('start_time')
    if not st:
        return None
    try:
        return int(time.time() - st)
    except Exception:
        return None


def normalize_queue_identity(email, company_id):
    """同一ユーザー判定用の安定キーを生成する。"""
    normalized_email = (email or '').strip().lower()
    normalized_company = (company_id or '').strip().lower()
    raw_key = f"{normalized_email}|{normalized_company}"
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()


def compact_job_queue_locked():
    """キュー内の欠損・重複・非queuedを取り除く。jobs_lock前提。"""
    global job_queue

    new_queue = deque()
    seen_job_ids = set()
    mutated = False

    for queued_job_id in list(job_queue):
        if queued_job_id in seen_job_ids:
            mutated = True
            continue

        queued_job = jobs.get(queued_job_id)
        if not queued_job or queued_job.get('status') != 'queued':
            queued_job_params.pop(queued_job_id, None)
            mutated = True
            continue

        seen_job_ids.add(queued_job_id)
        new_queue.append(queued_job_id)

    if mutated:
        job_queue = new_queue

    return list(job_queue)


def get_queue_position_locked(job_id):
    qlist = compact_job_queue_locked()
    if job_id in qlist:
        return 1 + qlist.index(job_id)
    return None


def find_live_job_for_queue_key_locked(queue_key):
    """同一待機キーの queued / running ジョブを返す。jobs_lock前提。"""
    if not queue_key:
        return None, None

    indexed_job_id = queue_identity_index.get(queue_key)
    if indexed_job_id:
        indexed_job = jobs.get(indexed_job_id)
        if indexed_job and indexed_job.get('status') in QUEUE_LIVE_STATUSES:
            return indexed_job_id, indexed_job
        queue_identity_index.pop(queue_key, None)

    matches = []
    for existing_job_id, job_info in jobs.items():
        if job_info.get('queue_key') != queue_key:
            continue
        if job_info.get('status') not in QUEUE_LIVE_STATUSES:
            continue
        status_rank = 0 if job_info.get('status') == 'running' else 1
        created_at = job_info.get('queued_at') or job_info.get('start_time') or 0
        matches.append((status_rank, created_at, existing_job_id, job_info))

    if not matches:
        return None, None

    matches.sort(key=lambda item: (item[0], item[1]))
    _, _, job_id, job_info = matches[0]
    queue_identity_index[queue_key] = job_id
    return job_id, job_info


def release_queue_identity_locked(job_id, job_info=None):
    """ジョブ終了時に待機キーの参照を外す。jobs_lock前提。"""
    job_info = job_info or jobs.get(job_id) or {}
    queue_key = job_info.get('queue_key')
    if not queue_key:
        return

    if queue_identity_index.get(queue_key) == job_id:
        queue_identity_index.pop(queue_key, None)
        replacement_job_id, _ = find_live_job_for_queue_key_locked(queue_key)
        if replacement_job_id:
            queue_identity_index[queue_key] = replacement_job_id


def touch_job_lease_locked(job_info, current_time=None):
    """queued / running ジョブの heartbeat を更新する。jobs_lock前提。"""
    if not job_info or job_info.get('status') not in QUEUE_LIVE_STATUSES:
        return

    current_time = current_time or time.time()
    job_info['last_heartbeat_at'] = current_time
    job_info['lease_expires_at'] = current_time + QUEUE_HEARTBEAT_TIMEOUT_SEC
    job_info['disconnect_hint_at'] = None
    job_info['client_attached'] = True
    job_info['last_updated'] = current_time


def build_existing_job_response_locked(job_id, job_info):
    """同一ユーザーの既存ジョブを再利用するときのレスポンスを組み立てる。"""
    status = job_info.get('status') or 'queued'
    payload = {
        'job_id': job_id,
        'session_id': job_info.get('session_id', ''),
        'status': status,
        'existing_job': True,
        'status_url': f'/status/{job_id}',
        'message': '既存の順番待ちを再利用しています。'
        if status == 'queued'
        else '既存の処理状態を再利用しています。'
    }
    if status == 'queued':
        payload['queue_position'] = get_queue_position_locked(job_id)
    return payload


def expire_queued_job_locked(job_id, current_time, cleanup_targets, reason):
    """queued ジョブを expired に遷移させてキューから除外する。jobs_lock前提。"""
    global job_queue

    job_info = jobs.get(job_id)
    if not job_info or job_info.get('status') != 'queued':
        return None

    messages = {
        'duplicate_wait': '同一ユーザーの重複待機を整理したため、この順番待ちは自動的に終了しました。',
        'disconnect': 'タブを閉じたか通信が途切れたため、順番待ちは自動的に終了しました。',
        'heartbeat_timeout': '一定時間操作が確認できなかったため、順番待ちは自動的に終了しました。',
    }

    job_queue = deque([queued_job_id for queued_job_id in job_queue if queued_job_id != job_id])
    queued_job_params.pop(job_id, None)
    job_info['status'] = 'expired'
    job_info['login_status'] = 'expired'
    job_info['login_message'] = messages.get(reason, messages['heartbeat_timeout'])
    job_info['end_time'] = current_time
    job_info['last_updated'] = current_time
    job_info['expired_reason'] = reason
    job_info['client_attached'] = False
    release_queue_identity_locked(job_id, job_info)

    cleanup_targets.append((job_info.get('file_path'), job_info.get('session_id')))
    return {
        'job_id': job_id,
        'reason': reason,
        'elapsed_sec': get_elapsed_sec(job_info),
    }


def get_queue_position(job_id):
    """queued 時のキュー内位置（1-based）。見つからなければ None。jobs_lock で保護。"""
    with jobs_lock:
        qlist = compact_job_queue_locked()
        if job_id in qlist:
            return 1 + qlist.index(job_id)
    return None


def log_job_event(event, job_id, status=None, queue_position=None, elapsed_sec=None, queue_length=None, running_count=None, extra=None):
    """AutoFill ジョブのライフサイクルイベントを構造化ログに出力。秘匿情報は絶対に含めない。"""
    payload = {
        "event": event,
        "job_id": job_id,
        "status": status,
        "queue_position": queue_position,
        "elapsed_sec": elapsed_sec,
    }
    if queue_length is not None:
        payload["queue_length"] = queue_length
    if running_count is not None:
        payload["running_count"] = running_count
    if extra:
        payload.update(extra)
    logger.info("autofill_event %s", payload)


def count_running_jobs():
    """statusがrunningのジョブ数（同時実行数）を返す。"""
    with jobs_lock:
        return sum(1 for j in jobs.values() if j.get('status') == 'running')

def check_resource_limits():
    """リソース制限のチェック（readyz/sessions 等の健全性用）。上限超過時は RuntimeError を投げる。"""
    resources = get_system_resources()
    running_count = count_running_jobs()
    session_count = resources['active_sessions']
    warnings = []
    
    if resources['memory_mb'] > MEMORY_LIMIT_MB:
        raise RuntimeError(f"メモリ制限を超過しました: {resources['memory_mb']:.1f}MB > {MEMORY_LIMIT_MB}MB")
    elif resources['memory_mb'] > MEMORY_WARNING_MB:
        warnings.append(f"メモリ使用量が高いです: {resources['memory_mb']:.1f}MB")
    
    if running_count >= MAX_ACTIVE_SESSIONS:
        raise RuntimeError(
            f"同時処理数の上限に達しています（実行中: {running_count}/{MAX_ACTIVE_SESSIONS}）。"
            f"しばらく待ってから再試行してください。"
        )
    elif running_count > MAX_ACTIVE_SESSIONS * 0.8:
        warnings.append(f"実行中ジョブが多いです: {running_count}/{MAX_ACTIVE_SESSIONS}件")
    if session_count != running_count:
        logger.warning(f"jobs_session_mismatch running_jobs={running_count} active_sessions={session_count}")
    
    return warnings


def get_resource_warnings():
    """例外を投げずに警告のみ返す。 /upload の即時開始パスで使用し、成功を阻害しない。"""
    warnings = []
    try:
        resources = get_system_resources()
        running_count = count_running_jobs()
        if resources['memory_mb'] > MEMORY_WARNING_MB:
            warnings.append(f"メモリ使用量が高いです: {resources['memory_mb']:.1f}MB")
        if running_count > MAX_ACTIVE_SESSIONS * 0.8:
            warnings.append(f"実行中ジョブが多いです: {running_count}/{MAX_ACTIVE_SESSIONS}件")
    except Exception as e:
        logger.warning(f"get_resource_warnings error: {e}")
    return warnings

def create_unique_session_id():
    """ユニークなセッションIDを生成"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    session_id = f"session_{uuid.uuid4().hex}_{timestamp}"
    return session_id

def get_user_session_dir(session_id):
    """ユーザーごとの一時ディレクトリを取得（完全分離）"""
    session_dir = os.path.join(tempfile.gettempdir(), f'jobcan_session_{session_id}')
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    return session_dir

def cleanup_user_session(session_id):
    """ユーザーセッションのクリーンアップ（完全削除）"""
    try:
        session_dir = get_user_session_dir(session_id)
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            print(f"セッションクリーンアップ完了: {session_id}")
    except Exception as e:
        print(f"セッションクリーンアップエラー {session_id}: {e}")

def register_session(session_id, job_id):
    """セッションを登録"""
    with session_manager['session_lock']:
        session_manager['active_sessions'][session_id] = {
            'job_id': job_id,
            'start_time': time.time(),
            'status': 'active'
        }
        print(f"セッション登録: {session_id} (ジョブ: {job_id})")

def unregister_session(session_id):
    """セッションを登録解除"""
    with session_manager['session_lock']:
        if session_id in session_manager['active_sessions']:
            del session_manager['active_sessions'][session_id]
            print(f"セッション解除: {session_id}")


def maybe_start_next_job():
    """running が 0 のときキュー先頭を running にしてスレッド起動。jobs_lock は内部で取得。"""
    with jobs_lock:
        compact_job_queue_locked()
        running_count = sum(1 for j in jobs.values() if j.get('status') == 'running')
        if running_count >= MAX_ACTIVE_SESSIONS:
            return
        if not job_queue:
            return
        queue_position = 1  # 先頭を開始する
        job_id = None
        params = None
        session_id = None
        session_dir = None
        email = None
        password = None
        file_path = None
        company_id = ''
        file_size = 0
        elapsed = None

        while job_queue:
            next_job_id = job_queue.popleft()
            next_params = queued_job_params.pop(next_job_id, None)
            next_job = jobs.get(next_job_id)
            if not next_params or not next_job or next_job.get('status') != 'queued':
                release_queue_identity_locked(next_job_id, next_job)
                continue

            queue_key = next_job.get('queue_key')
            existing_job_id, _ = find_live_job_for_queue_key_locked(queue_key)
            if existing_job_id and existing_job_id != next_job_id:
                # 同一ユーザーの duplicate waiting が残っていても開始しない。
                cleanup_targets = []
                expired_meta = expire_queued_job_locked(next_job_id, time.time(), cleanup_targets, reason='duplicate_wait')
                for fp, sid in cleanup_targets:
                    try:
                        if fp and os.path.exists(fp):
                            os.remove(fp)
                        if sid:
                            cleanup_user_session(sid)
                    except Exception as cleanup_error:
                        logger.warning(f"duplicate_wait_cleanup_error job_id={next_job_id} error={cleanup_error}")
                if expired_meta:
                    log_job_event("job_expired", next_job_id, status="expired", elapsed_sec=expired_meta.get('elapsed_sec'), extra={'reason': 'duplicate_wait'})
                continue

            job_id = next_job_id
            params = next_params
            jobs[job_id]['status'] = 'running'
            jobs[job_id]['step_name'] = 'initializing'
            jobs[job_id]['login_status'] = 'initializing'
            jobs[job_id]['login_message'] = '🔄 処理を初期化中...'
            jobs[job_id]['start_time'] = time.time()
            touch_job_lease_locked(jobs[job_id], current_time=time.time())
            elapsed = get_elapsed_sec(jobs[job_id])
            email = params['email']
            password = params['password']
            file_path = params['file_path']
            session_dir = params['session_dir']
            session_id = params['session_id']
            company_id = params.get('company_id', '')
            file_size = params.get('file_size', 0)
            queue_identity_index[queue_key] = job_id
            break

        if not job_id:
            return

        jobs[job_id]['status'] = 'running'
        jobs[job_id]['last_updated'] = time.time()
    register_session(session_id, job_id)
    log_job_event("job_started", job_id, status="running", queue_position=queue_position, elapsed_sec=elapsed, extra={"source": "queue"})
    # ロック外でスレッド起動（run_automation_impl 内で process が重い）
    thread = threading.Thread(
        target=run_automation_impl,
        args=(job_id, email, password, file_path, session_dir, session_id, company_id, file_size)
    )
    thread.daemon = True
    thread.start()


def run_automation_impl(job_id, email, password, file_path, session_dir, session_id, company_id, file_size):
    """1ジョブ分の自動化実行。完了後 maybe_start_next_job で次を起動。"""
    from automation import process_jobcan_automation
    bg_start_time = time.time()
    logger.info(f"bg_job_start job_id={job_id} session_id={session_id} file_size={file_size}")
    try:
        process_jobcan_automation(
            job_id, email, password, file_path, jobs, session_dir, session_id, company_id,
            job_timeout_sec=JOB_TIMEOUT_SEC
        )
        duration = time.time() - bg_start_time
        logger.info(f"bg_job_success job_id={job_id} duration_sec={duration:.1f}")
        with jobs_lock:
            job = jobs.get(job_id)
            st = job.get('status') if job else None
            elapsed = get_elapsed_sec(job)
        if st == 'completed':
            log_job_event("job_completed", job_id, status="completed", elapsed_sec=elapsed)
        elif st == 'timeout':
            log_job_event("job_timeout", job_id, status="timeout", elapsed_sec=elapsed)
        else:
            log_job_event("job_completed", job_id, status=st or "completed", elapsed_sec=elapsed)
    except Exception as e:
        error_message = f'処理中にエラーが発生しました: {str(e)}'
        duration = time.time() - bg_start_time
        logger.error(f"bg_job_error job_id={job_id} duration_sec={duration:.1f} error={str(e)}")
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]['status'] = 'error'
                jobs[job_id]['login_status'] = 'error'
                jobs[job_id]['login_message'] = error_message
                from utils import add_job_log
                add_job_log(job_id, f"❌ {error_message}", jobs)
                jobs[job_id]['last_updated'] = time.time()
                jobs[job_id]['end_time'] = time.time()
            err_elapsed = get_elapsed_sec(jobs.get(job_id))
        log_job_event("job_error", job_id, status="error", elapsed_sec=err_elapsed, extra={"error": str(e)[:200]})
    finally:
        with jobs_lock:
            j = jobs.get(job_id, {})
            st = j.get('status')
            if st in TERMINAL_JOB_STATUSES:
                release_queue_identity_locked(job_id, j)
            el = get_elapsed_sec(j)
            rcount = sum(1 for x in jobs.values() if x.get('status') == 'running')
            qlen = len(compact_job_queue_locked())
        log_job_event("cleanup_started", job_id, status=st, elapsed_sec=el, running_count=rcount, queue_length=qlen)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"cleanup_file job_id={job_id} path={file_path}")
            cleanup_user_session(session_id)
            unregister_session(session_id)
            prune_jobs()
        except Exception as cleanup_error:
            logger.error(f"cleanup_error job_id={job_id} session_id={session_id} error={str(cleanup_error)}")
            try:
                prune_jobs()
            except Exception:
                pass
        log_job_event("cleanup_finished", job_id, status=st, elapsed_sec=get_elapsed_sec(jobs.get(job_id)))
        maybe_start_next_job()


def prune_jobs(current_time=None, retention_sec=JOB_RETENTION_SECONDS):
    """完了済み・失効済みジョブを掃除し、stale waiting を queue から除外する。"""
    global job_queue
    if current_time is None:
        current_time = time.time()

    cleanup_targets = []
    expired_events = []
    stale_active_job_ids = []

    with jobs_lock:
        compact_job_queue_locked()

        # running 中の同一待機キーを優先し、queued の重複は stale 扱いで掃除する。
        running_queue_keys = {
            job_info.get('queue_key')
            for job_info in jobs.values()
            if job_info.get('status') == 'running' and job_info.get('queue_key')
        }
        seen_waiting_keys = set()

        for queued_job_id in list(job_queue):
            queued_job = jobs.get(queued_job_id)
            if not queued_job or queued_job.get('status') != 'queued':
                continue

            queue_key = queued_job.get('queue_key')
            if not queue_key:
                continue

            if queue_key in running_queue_keys or queue_key in seen_waiting_keys:
                expired_meta = expire_queued_job_locked(queued_job_id, current_time, cleanup_targets, reason='duplicate_wait')
                if expired_meta:
                    expired_events.append(expired_meta)
                continue

            seen_waiting_keys.add(queue_key)
            queue_identity_index[queue_key] = queued_job_id

        compact_job_queue_locked()

        # queued の最大待機時間 / heartbeat 切れ / disconnect hint を整理
        for job_id, job_info in list(jobs.items()):
            status = job_info.get('status')
            if status == 'queued':
                queued_at = job_info.get('queued_at') or job_info.get('start_time') or 0
                last_heartbeat_at = job_info.get('last_heartbeat_at') or queued_at
                lease_expires_at = job_info.get('lease_expires_at') or (last_heartbeat_at + QUEUE_HEARTBEAT_TIMEOUT_SEC)
                disconnect_hint_at = job_info.get('disconnect_hint_at')

                if disconnect_hint_at and last_heartbeat_at <= disconnect_hint_at and current_time - disconnect_hint_at > QUEUE_DISCONNECT_GRACE_SEC:
                    expired_meta = expire_queued_job_locked(job_id, current_time, cleanup_targets, reason='disconnect')
                    if expired_meta:
                        expired_events.append(expired_meta)
                    continue

                if current_time > lease_expires_at:
                    expired_meta = expire_queued_job_locked(job_id, current_time, cleanup_targets, reason='heartbeat_timeout')
                    if expired_meta:
                        expired_events.append(expired_meta)
                    continue

                if current_time - queued_at > QUEUED_MAX_WAIT_SEC:
                    job_queue = deque([queued_job_id for queued_job_id in job_queue if queued_job_id != job_id])
                    queued_job_params.pop(job_id, None)
                    jobs[job_id]['status'] = 'timeout'
                    jobs[job_id]['login_status'] = 'timeout'
                    jobs[job_id]['login_message'] = '待機時間が上限を超えたためキャンセルされました。'
                    jobs[job_id]['end_time'] = current_time
                    jobs[job_id]['last_updated'] = current_time
                    release_queue_identity_locked(job_id, jobs[job_id])
                    cleanup_targets.append((job_info.get('file_path'), job_info.get('session_id')))
                    expired_events.append({
                        'job_id': job_id,
                        'reason': 'queued_timeout',
                        'elapsed_sec': get_elapsed_sec(job_info),
                    })
                    continue

                if queue_key:
                    queue_identity_index[queue_key] = job_id

            elif status == 'running':
                last_heartbeat_at = job_info.get('last_heartbeat_at') or job_info.get('start_time') or current_time
                if current_time - last_heartbeat_at > ACTIVE_CLIENT_STALE_WARNING_SEC and not job_info.get('client_stale_warned'):
                    jobs[job_id]['client_stale_warned'] = True
                    jobs[job_id]['client_attached'] = False
                    stale_active_job_ids.append(job_id)

    removed_count = 0
    removed_job_ids = []

    with jobs_lock:
        jobs_to_remove = []

        for job_id, job_info in list(jobs.items()):
            # completed / error / timeout / cancelled / expired を削除対象
            if job_info.get('status') not in TERMINAL_JOB_STATUSES:
                continue

            # タイムスタンプを取得
            end_time = job_info.get('end_time')
            if end_time is None:
                # end_timeがない場合はstart_timeから推定（処理時間が長い場合のフォールバック）
                start_time = job_info.get('start_time', 0)
                if start_time > 0:
                    # 開始から30分以上経過していれば削除対象
                    if current_time - start_time > retention_sec:
                        jobs_to_remove.append(job_id)
                continue
            
            # 完了/エラーから一定時間経過したジョブを削除対象に
            if current_time - end_time > retention_sec:
                jobs_to_remove.append(job_id)
        
            # 削除実行
        for job_id in jobs_to_remove:
            job_info = jobs.get(job_id, {})
            log_count = len(job_info.get('logs', []))
            age_sec = current_time - job_info.get('end_time', current_time)
            release_queue_identity_locked(job_id, job_info)
            del jobs[job_id]
            removed_count += 1
            removed_job_ids.append(job_id)

            logger.info(f"job_prune removed job_id={job_id} status={job_info.get('status')} log_count={log_count} age_sec={age_sec:.1f}")

    for fp, sid in cleanup_targets:
        try:
            if fp and os.path.exists(fp):
                os.remove(fp)
            if sid:
                cleanup_user_session(sid)
                unregister_session(sid)
        except Exception as cleanup_error:
            logger.error(f"prune_queued_cleanup_error error={cleanup_error}")

    for expired_meta in expired_events:
        reason = expired_meta.get('reason')
        status = 'timeout' if reason == 'queued_timeout' else 'expired'
        log_job_event("job_expired", expired_meta['job_id'], status=status, elapsed_sec=expired_meta.get('elapsed_sec'), extra={'reason': reason})

    for stale_active_job_id in stale_active_job_ids:
        logger.warning(f"active_client_stale job_id={stale_active_job_id} threshold_sec={ACTIVE_CLIENT_STALE_WARNING_SEC}")

    if removed_count > 0:
        logger.info(f"job_prune summary removed={removed_count} remaining={len(jobs)}")

        # P1-1: prune_jobs実行前後のメモリ計測（削除があった場合のみ）
        if metrics_available:
            jobs_count_before = len(jobs) + removed_count
            log_memory("prune_jobs_before", extra={
                'jobs_count': jobs_count_before,
                'sessions_count': len(session_manager['active_sessions']),
                'removed_count': removed_count
            })
            log_memory("prune_jobs_after", extra={
                'jobs_count': len(jobs),
                'sessions_count': len(session_manager['active_sessions']),
                'removed_count': removed_count
            })

    return removed_count

def validate_input_data(email, password, file):
    """入力データの検証"""
    errors = []
    
    # メールアドレスの検証
    if not email or '@' not in email or '.' not in email:
        errors.append("有効なメールアドレスを入力してください")
    
    # パスワードの検証
    if not password or len(password) < 1:
        errors.append("パスワードを入力してください")
    
    # ファイルサイズの検証（10MB制限）
    if file and hasattr(file, 'content_length'):
        if file.content_length > 10 * 1024 * 1024:  # 10MB
            errors.append("ファイルサイズが大きすぎます（10MB以下にしてください）")
    
    return errors

@app.route('/')
def index():
    """ランディングページ（製品ハブ）"""
    # 恒久対策：トップページを絶対に落とさない（依存データが取れない場合でも劣化表示で耐える）
    # context_processorで既にproductsが注入されているため、明示的に渡す必要はない
    # ただし、テンプレートでproductsが未定義の場合に備えて、明示的に渡す
    
    # ステップ1: 製品一覧は products_catalog から取得（外部依存なし・落ちない）
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
    
    # ステップ2: テンプレートレンダリング（失敗しても劣化表示を返す）
    try:
        # テンプレートに明示的に渡す（context_processorのフォールバック）
        # productsが空のリストでも、テンプレートで安全に処理される
        return render_template('landing.html', products=products)
    except Exception as render_error:
        # テンプレートレンダリング時の例外をログに記録
        request_id = getattr(g, 'request_id', 'unknown')
        logger.exception(
            f"landing_page_render_failed rid={request_id} path={request.path if request else 'unknown'} "
            f"error={str(render_error)} exception_type={type(render_error).__name__}"
        )
        
        # 恒久対策：エラーページではなく、劣化表示のHTMLを直接返す
        # これにより、トップページは常に200を返す
        from flask import make_response
        degraded_html = f'''<!doctype html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>しごと道具箱</title>
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
        <h1>しごと道具箱</h1>
        <p>しごとの小さな面倒を、さっと片づける軽量ツール集です。</p>
        
        <div class="warning">
            <p><strong>⚠️ 一時的な表示の問題</strong></p>
            <p>現在、製品情報の読み込みに問題が発生しています。しばらく待ってから再度お試しください。</p>
            <p>以下のリンクから直接アクセスできます：</p>
            <ul>
                <li><a href="/tools">道具箱一覧</a></li>
                <li><a href="/tools/pdf">PDFツール</a></li>
                <li><a href="/tools/csv">CSV/Excelツール</a></li>
                <li><a href="/about">サイトについて</a></li>
            </ul>
        </div>
        
        <p style="margin-top: 40px; font-size: 0.9em; color: rgba(255, 255, 255, 0.7);">
            問題が解決しない場合は、<a href="/contact">お問い合わせ</a>からご連絡ください。
        </p>
    </div>
</body>
</html>'''
        resp = make_response(degraded_html, 200)
        resp.headers['X-Degraded-Mode'] = 'true'
        return resp

@app.route('/autofill')
def autofill():
    """旧Jobcan導線: public版では道具箱一覧へ集約する。"""
    return redirect('/tools', code=301)

@app.route('/privacy')
def privacy():
    """プライバシーポリシーページ"""
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    """利用規約ページ"""
    return render_template('terms.html')

@app.route('/contact')
def contact():
    """お問い合わせページ"""
    return render_template('contact.html')

@app.route('/guide')
def guide_index():
    """ガイド一覧ページ（public版は汎用ツール中心）"""
    try:
        from lib.products_catalog import get_public_products
        products = get_public_products()
    except Exception:
        products = []
    return render_template('guide/index.html', products=products)


@app.route('/guide/autofill')
def guide_autofill():
    """Jobcan AutoFill 統合ガイド（他ツールと同粒度の1ツール=1ガイド）"""
    return render_template('guide/autofill.html')


@app.route('/guide/getting-started')
def guide_getting_started():
    """はじめての使い方ガイド"""
    return render_template('guide/getting-started.html')


@app.route('/guide/excel-format')
def guide_excel_format():
    """Excelファイルの作成方法ガイド"""
    return render_template('guide/excel-format.html')


@app.route('/guide/troubleshooting')
def guide_troubleshooting():
    """トラブルシューティングガイド"""
    return render_template('guide/troubleshooting.html')

@app.route('/guide/complete')
def guide_complete():
    """完全ガイド"""
    return render_template('guide/complete-guide.html')

@app.route('/guide/comprehensive-guide')
def guide_comprehensive_guide():
    """Jobcan勤怠管理を効率化する総合ガイド"""
    return render_template('guide/comprehensive-guide.html')

@app.route('/guide/image-batch')
def guide_image_batch():
    """画像一括変換ツールガイド"""
    return render_template('guide/image-batch.html')

@app.route('/guide/pdf')
def guide_pdf():
    """PDFユーティリティガイド"""
    return render_template('guide/pdf.html')

@app.route('/guide/image-cleanup')
def guide_image_cleanup():
    """画像ユーティリティガイド"""
    return render_template('guide/image-cleanup.html')

@app.route('/guide/minutes')
def guide_minutes():
    """旧議事録ガイドURL: 301で /guide へ"""
    return redirect('/guide', code=301)

@app.route('/guide/seo')
def guide_seo():
    """Web/SEOユーティリティガイド"""
    return render_template('guide/seo.html')

@app.route('/guide/csv')
def guide_csv():
    """CSV/Excelユーティリティガイド"""
    return render_template('guide/csv.html')

@app.route('/tools/image-batch')
def tools_image_batch():
    """画像一括変換ツール"""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/image-batch')
    return render_template('tools/image-batch.html', product=product)

@app.route('/tools/pdf')
def tools_pdf():
    """PDFユーティリティ"""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/pdf')
    return render_template('tools/pdf.html', product=product)


# PDF ロック付与 API（案B: サーバ併用）
# パスワードはログ・永続化しない。
# エラー時は error_code と request_id を返す（message は返さない。パスワードは絶対に出さない）。
PDF_API_MAX_BYTES = 50 * 1024 * 1024  # 50MB

def _pdf_api_error(error_code, status=400):
    rid = uuid.uuid4().hex[:12]
    return jsonify(success=False, error_code=error_code, request_id=rid), status


@app.route('/api/pdf/lock', methods=['POST'])
def api_pdf_lock():
    """PDFにパスワードを付与して暗号化して返す。password は form で受け取り、ログに出さない。"""
    try:
        file = request.files.get('file')
        password = (request.form.get('password') or '').strip()
        if not file or file.filename == '':
            return _pdf_api_error('file_required')
        if not password:
            return _pdf_api_error('missing_password')
        try:
            pdf_bytes = file.read()
        except Exception:
            return _pdf_api_error('read_failed')
        if len(pdf_bytes) > PDF_API_MAX_BYTES:
            return _pdf_api_error('file_too_large')
        try:
            from lib.pdf_lock_unlock import encrypt_pdf
            out_bytes = encrypt_pdf(pdf_bytes, password)
        except ValueError as e:
            err = str(e)
            if err == 'already_encrypted':
                return _pdf_api_error('already_encrypted')
            if err == 'corrupt_pdf':
                return _pdf_api_error('corrupt_pdf')
            if err == 'unsupported_pdf':
                return _pdf_api_error('unsupported_pdf')
            return _pdf_api_error('encrypt_failed')
        except Exception as e:
            rid = uuid.uuid4().hex[:12]
            logging.getLogger(__name__).warning('pdf lock encrypt_failed request_id=%s %s', rid, type(e).__name__)
            logging.getLogger(__name__).debug('pdf lock encrypt_failed traceback', exc_info=True)
            return jsonify(success=False, error_code='encrypt_failed', request_id=rid), 400
        from io import BytesIO
        name = file.filename or 'document.pdf'
        if not name.lower().endswith('.pdf'):
            name += '.pdf'
        base = name[:-4] if name.lower().endswith('.pdf') else name
        return send_file(
            BytesIO(out_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{base}_locked.pdf'
        )
    except Exception as e:
        rid = uuid.uuid4().hex[:12]
        logging.getLogger(__name__).exception('pdf lock request_id=%s %s', rid, type(e).__name__)
        return jsonify(success=False, error_code='unsupported', request_id=rid), 500


@app.route('/tools/image-cleanup')
def tools_image_cleanup():
    """画像ユーティリティ"""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/image-cleanup')
    return render_template('tools/image-cleanup.html', product=product)

@app.route('/tools/minutes')
def tools_minutes():
    """旧議事録ツールURL: 301で /tools へ"""
    return redirect('/tools', code=301)


@app.route('/api/minutes/format', methods=['POST'])
def api_minutes_format():
    """旧議事録API: 410 Gone"""
    return jsonify(error_code='gone'), 410


@app.route('/tools/seo')
def tools_seo():
    """Web/SEOユーティリティ"""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/seo')
    return render_template('tools/seo.html', product=product)

@app.route('/tools/csv')
def tools_csv():
    """CSV/Excelユーティリティ"""
    from lib.routes import get_product_by_path
    product = get_product_by_path('/tools/csv')
    return render_template('tools/csv.html', product=product)


# 簡易レート制限: /api/seo/crawl-urls を IP ごとに 60 秒に 1 回まで
_crawl_rate_by_ip = {}
_crawl_rate_lock = threading.Lock()
_CRAWL_RATE_SEC = 60


def _is_valid_ip(s):
    """妥当な IPv4/IPv6 形式なら True。"""
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    try:
        import ipaddress
        ipaddress.ip_address(s)
        return True
    except (ValueError, TypeError):
        return False


def _get_client_ip_for_crawl():
    """request.access_route / X-Forwarded-For から妥当なIPを採用し、なければ remote_addr。"""
    candidates = []
    if getattr(request, 'access_route', None):
        candidates.extend(request.access_route)
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        candidates.extend(p.strip() for p in xff.split(',') if p.strip())
    if request.remote_addr:
        candidates.append(request.remote_addr)
    for c in candidates:
        if _is_valid_ip(c):
            return c
    return request.remote_addr or 'unknown'


@app.route('/api/seo/crawl-urls', methods=['POST'])
def api_seo_crawl_urls():
    """同一ホスト内でURLをクロールし、URL一覧を返す。sitemap用。SSRF対策・レート制限あり。"""
    client_ip = _get_client_ip_for_crawl()
    now = time.time()
    with _crawl_rate_lock:
        last = _crawl_rate_by_ip.get(client_ip, 0)
        if now - last < _CRAWL_RATE_SEC:
            resp = jsonify(
                success=False,
                error='しばらく待ってから再度お試しください（1分に1回まで）',
                retry_after_sec=_CRAWL_RATE_SEC
            )
            resp.status_code = 429
            resp.headers['Retry-After'] = str(_CRAWL_RATE_SEC)
            return resp
        _crawl_rate_by_ip[client_ip] = now

    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}
    start_url = (data.get('start_url') or '').strip()
    if not start_url:
        return jsonify(success=False, error='start_url を指定してください'), 400

    from lib.seo_crawler import crawl, is_url_safe_for_crawl
    safe, err_msg = is_url_safe_for_crawl(start_url)
    if not safe:
        return jsonify(success=False, error=err_msg or 'このURLは許可されていません'), 400

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
    """道具箱一覧ページ"""
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
    """よくある質問（FAQ）"""
    return render_template('faq.html')

@app.route('/glossary')
def glossary():
    """用語集"""
    return render_template('glossary.html')

@app.route('/about')
def about():
    """サイトについて"""
    return render_template('about.html')

@app.route('/best-practices')
def best_practices():
    """ベストプラクティス"""
    return render_template('best-practices.html')

@app.route('/case-studies')
def case_studies_index():
    """導入事例一覧"""
    return render_template('case-studies.html')

@app.route('/case-study/contact-center')
def case_study_contact_center():
    """導入事例：コンタクトセンター"""
    return render_template('case-study-contact-center.html')

@app.route('/blog')
def blog_index():
    """ブログ一覧"""
    return render_template('blog/index.html')

@app.route('/blog/implementation-checklist')
def blog_implementation_checklist():
    """ブログ記事：導入チェックリスト"""
    return render_template('blog/implementation-checklist.html')

@app.route('/blog/automation-roadmap')
def blog_automation_roadmap():
    """ブログ記事：90日ロードマップ"""
    return render_template('blog/automation-roadmap.html')

@app.route('/blog/workstyle-reform-automation')
def blog_workstyle_reform_automation():
    """ブログ記事：働き方改革と自動化"""
    return render_template('blog/workstyle-reform-automation.html')

@app.route('/blog/excel-attendance-limits')
def blog_excel_attendance_limits():
    """ブログ記事：Excel管理の限界と自動化ツール"""
    return render_template('blog/excel-attendance-limits.html')

@app.route('/blog/playwright-security')
def blog_playwright_security():
    """ブログ記事：Playwrightによるブラウザ自動化のセキュリティ"""
    return render_template('blog/playwright-security.html')

@app.route('/blog/month-end-closing-hell-and-automation')
def blog_month_end_closing_hell_and_automation():
    """ブログ記事：月末締めが地獄になる理由と自動化"""
    return render_template('blog/month-end-closing-hell-and-automation.html')

@app.route('/blog/excel-format-mistakes-and-design')
def blog_excel_format_mistakes_and_design():
    """ブログ記事：Excelフォーマットのミス10選"""
    return render_template('blog/excel-format-mistakes-and-design.html')

@app.route('/blog/convince-it-and-hr-for-automation')
def blog_convince_it_and_hr_for_automation():
    """ブログ記事：情シス・人事を説得する5ステップ"""
    return render_template('blog/convince-it-and-hr-for-automation.html')

@app.route('/blog/playwright-jobcan-challenges-and-solutions')
def blog_playwright_jobcan_challenges_and_solutions():
    """ブログ記事：Playwrightでハマったポイント"""
    return render_template('blog/playwright-jobcan-challenges-and-solutions.html')

@app.route('/blog/jobcan-auto-input-tools-overview')
def blog_jobcan_auto_input_tools_overview():
    """ブログ記事：Jobcan自動入力ツールの全体像と選び方"""
    return render_template('blog/jobcan-auto-input-tools-overview.html')

@app.route('/blog/reduce-manual-work-checklist')
def blog_reduce_manual_work_checklist():
    """ブログ記事：勤怠管理の手入力を減らすための実務チェックリスト"""
    return render_template('blog/reduce-manual-work-checklist.html')

@app.route('/blog/jobcan-month-end-tips')
def blog_jobcan_month_end_tips():
    """ブログ記事：Jobcan月末締めをラクにするための7つの実践テクニック"""
    return render_template('blog/jobcan-month-end-tips.html')

@app.route('/blog/jobcan-auto-input-dos-and-donts')
def blog_jobcan_auto_input_dos_and_donts():
    """ブログ記事：Jobcan自動入力のやり方と、やってはいけないNG自動化"""
    return render_template('blog/jobcan-auto-input-dos-and-donts.html')

@app.route('/blog/month-end-closing-checklist')
def blog_month_end_closing_checklist():
    """ブログ記事：月末の勤怠締め地獄を減らすための現実的なチェックリスト"""
    return render_template('blog/month-end-closing-checklist.html')

@app.route('/case-study/consulting-firm')
def case_study_consulting_firm():
    """導入事例：コンサルティングファーム"""
    return render_template('case-study-consulting-firm.html')

@app.route('/case-study/remote-startup')
def case_study_remote_startup():
    """導入事例：小規模スタートアップ"""
    return render_template('case-study-remote-startup.html')

@app.route('/sitemap.html')
def sitemap_html():
    """HTMLサイトマップ"""
    return render_template('sitemap.html')

# === ヘルスチェックエンドポイント（Render用・超軽量） ===
@app.route('/healthz')
def healthz():
    """超軽量ヘルスチェック - Render Health Check用（堅牢化）"""
    try:
        # 最小限のチェック：アプリケーションが応答可能か
        return Response('ok', mimetype='text/plain', headers={'Cache-Control': 'no-store'})
    except Exception as e:
        # ログに記録してから503を返す
        logger.error(f"healthz_check_failed error={str(e)}")
        return Response(f'health check failed: {str(e)}', status=503, mimetype='text/plain')

@app.route('/livez')
def livez():
    """プロセス生存確認 - 即座にOK"""
    return Response('ok', mimetype='text/plain', headers={'Cache-Control': 'no-store'})

@app.route('/readyz')
def readyz():
    """準備完了確認 - 軽量チェックのみ（堅牢化）"""
    try:
        # 最小限のチェック：jobsディクショナリが存在するか
        _ = len(jobs)
        # 追加チェック：メモリ使用量が安全範囲内か
        resources = get_system_resources()
        if resources['memory_mb'] > MEMORY_LIMIT_MB:
            logger.error(f"memory_limit_exceeded current={resources['memory_mb']:.1f}MB limit={MEMORY_LIMIT_MB}MB")
            return Response(f'memory limit exceeded: {resources["memory_mb"]:.1f}MB', status=503, mimetype='text/plain')
        
        # 同時実行数チェック（runningジョブ数で判定）
        running_count = count_running_jobs()
        if running_count > MAX_ACTIVE_SESSIONS:
            logger.error(f"max_sessions_exceeded running={running_count} limit={MAX_ACTIVE_SESSIONS}")
            return Response(f'max sessions exceeded: {running_count}/{MAX_ACTIVE_SESSIONS}', status=503, mimetype='text/plain')
        
        # リソース使用率をログに記録（詳細版）
        memory_usage_percent = (resources['memory_mb'] / MEMORY_LIMIT_MB) * 100
        logger.info(f"system_resources memory={resources['memory_mb']:.1f}MB/{MEMORY_LIMIT_MB}MB ({memory_usage_percent:.1f}%) cpu={resources['cpu_percent']:.1f}% running_jobs={running_count}/{MAX_ACTIVE_SESSIONS}")
        
        # メモリ使用率が高い場合は警告
        if memory_usage_percent > 80:
            logger.warning(f"high_memory_usage memory={resources['memory_mb']:.1f}MB ({memory_usage_percent:.1f}%) - approaching limit")
        
        return Response('ok', mimetype='text/plain', headers={'Cache-Control': 'no-store'})
    except Exception as e:
        # ログに記録してから503を返す
        logger.error(f"readyz_check_failed error={str(e)}")
        return Response(f'not ready: {str(e)}', status=503, mimetype='text/plain')

# === 後方互換性のため既存エンドポイントを維持（ただし軽量化） ===
@app.route('/ping')
def ping():
    """後方互換 - UptimeRobot用"""
    return jsonify({'status': 'ok', 'message': 'pong', 'timestamp': datetime.now().isoformat()})

@app.route('/health')
def health():
    """詳細ヘルスチェック - デバッグ用（重いので監視には使わない）"""
    try:
        from utils import pandas_available, openpyxl_available, playwright_available
        resources = get_system_resources()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'dependencies': {
                'pandas': pandas_available,
                'openpyxl': openpyxl_available,
                'playwright': playwright_available
            },
            'resources': resources,
            'active_sessions': len(session_manager['active_sessions'])
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/ready')
def ready():
    """後方互換 - 既存依存関係チェック"""
    from utils import pandas_available, openpyxl_available, playwright_available
    return jsonify({
        'status': 'ready',
        'timestamp': datetime.now().isoformat(),
        'dependencies': {
            'pandas': pandas_available,
            'openpyxl': openpyxl_available,
            'playwright': playwright_available
        }
    })

@app.route('/health/memory', methods=['GET'])
def health_memory():
    """
    メモリ計測用エンドポイント（DEBUG時のみ有効、本番影響なし）
    ローカル/ステージング環境でメモリ使用状況を確認するためのエンドポイント
    """
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        rss_mb = memory_info.rss / 1024 / 1024
        vms_mb = memory_info.vms / 1024 / 1024
        
        # システム全体のメモリ情報も取得
        system_memory = psutil.virtual_memory()
        
        # ジョブとセッションの統計
        with jobs_lock:
            jobs_count = len(jobs)
            jobs_status = {}
            for job_id, job_info in jobs.items():
                status = job_info.get('status', 'unknown')
                jobs_status[status] = jobs_status.get(status, 0) + 1
        
        with session_manager['session_lock']:
            sessions_count = len(session_manager['active_sessions'])
        
        from diagnostics.runtime_metrics import get_browser_count
        browser_count = get_browser_count()
        
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'process_memory': {
                'rss_mb': round(rss_mb, 2),
                'vms_mb': round(vms_mb, 2),
                'percent': round(process.memory_percent(), 2)
            },
            'system_memory': {
                'total_mb': round(system_memory.total / 1024 / 1024, 2),
                'available_mb': round(system_memory.available / 1024 / 1024, 2),
                'used_mb': round(system_memory.used / 1024 / 1024, 2),
                'percent': round(system_memory.percent, 2)
            },
            'limits': {
                'memory_limit_mb': MEMORY_LIMIT_MB,
                'memory_warning_mb': MEMORY_WARNING_MB,
                'max_file_size_mb': MAX_FILE_SIZE_MB,
                'max_active_sessions': MAX_ACTIVE_SESSIONS
            },
            'resources': {
                'jobs_count': jobs_count,
                'jobs_by_status': jobs_status,
                'sessions_count': sessions_count,
                'browser_count': browser_count
            },
            'config': {
                'web_concurrency': os.getenv('WEB_CONCURRENCY', 'unknown'),
                'web_threads': os.getenv('WEB_THREADS', 'unknown'),
                'web_timeout': os.getenv('WEB_TIMEOUT', 'unknown')
            }
        })
    except ImportError:
        return jsonify({
            'status': 'error',
            'error': 'psutil not available'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/test')
def test():
    return jsonify({
        'status': 'ok',
        'message': 'Test endpoint working',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/download-template')
def download_template():
    try:
        print("テンプレートダウンロード開始")
        template_file, error_message = create_template_excel()
        
        if error_message:
            print(f"テンプレート作成エラー: {error_message}")
            return jsonify({'error': f'テンプレートファイルの作成に失敗しました: {error_message}'}), 500
        
        if not template_file or not os.path.exists(template_file):
            print(f"テンプレートファイルが存在しません: {template_file}")
            return jsonify({'error': 'テンプレートファイルの生成に失敗しました'}), 500
        
        print(f"テンプレートファイル作成成功: {template_file}")
        return send_file(
            template_file,
            as_attachment=True,
            download_name='jobcan_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        print(f"テンプレートダウンロード例外: {str(e)}")
        return jsonify({'error': f'テンプレートファイルの作成に失敗しました: {str(e)}'}), 500

@app.route('/download-previous-template')
def download_previous_template():
    try:
        print("先月テンプレートダウンロード開始")
        template_file, error_message = create_previous_month_template_excel()
        
        if error_message:
            print(f"先月テンプレート作成エラー: {error_message}")
            return jsonify({'error': f'先月テンプレートファイルの作成に失敗しました: {error_message}'}), 500
        
        if not template_file or not os.path.exists(template_file):
            print(f"先月テンプレートファイルが存在しません: {template_file}")
            return jsonify({'error': '先月テンプレートファイルの生成に失敗しました'}), 500
        
        print(f"先月テンプレートファイル作成成功: {template_file}")
        return send_file(
            template_file,
            as_attachment=True,
            download_name='jobcan_previous_month_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        print(f"先月テンプレートダウンロード例外: {str(e)}")
        return jsonify({'error': f'先月テンプレートファイルの作成に失敗しました: {str(e)}'}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    session_id = None
    file_path = None
    try:
        # 入力データの検証
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルが選択されていません'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'})
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Excelファイル（.xlsx, .xls）のみアップロード可能です'})
        
        # ファイルサイズ制限（環境変数で設定可能）
        file.seek(0, 2)  # ファイルの末尾に移動
        file_size = file.tell()  # ファイルサイズを取得
        file.seek(0)  # ファイルの先頭に戻す
        
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            return jsonify({'error': f'ファイルサイズが{MAX_FILE_SIZE_MB}MBを超えています。より小さいファイルを使用してください。'})
        
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        company_id = request.form.get('company_id', '').strip()
        
        # 入力データの詳細検証
        validation_errors = validate_input_data(email, password, file)
        if validation_errors:
            return jsonify({'error': '入力エラー: ' + '; '.join(validation_errors)})
        queue_key = normalize_queue_identity(email, company_id)
        prune_jobs(current_time=time.time())

        with jobs_lock:
            existing_job_id, existing_job = find_live_job_for_queue_key_locked(queue_key)
            if existing_job_id and existing_job:
                touch_job_lease_locked(existing_job, current_time=time.time())
                existing_payload = build_existing_job_response_locked(existing_job_id, existing_job)
                log_job_event(
                    "job_reused",
                    existing_job_id,
                    status=existing_job.get('status'),
                    queue_position=existing_payload.get('queue_position'),
                    elapsed_sec=get_elapsed_sec(existing_job),
                    extra={'reason': 'same_user_reuse'}
                )
                status_code = 202 if existing_job.get('status') == 'queued' else 200
                return jsonify(existing_payload), status_code

        # 直列実行＋キュー: running が上限でも 503 にせず、後続で queued に積む（キュー満杯時のみ 503 QUEUE_FULL）

        # P0-P1: メモリガード（新規ジョブ開始前チェック）。job_idは未生成のためログには含めない
        try:
            resources = get_system_resources()
            if resources['memory_mb'] > MEMORY_WARNING_MB:
                logger.warning(f"memory_guard_blocked memory_mb={resources['memory_mb']:.1f} warning_threshold={MEMORY_WARNING_MB}")
                return jsonify({
                    'error': f'メモリ使用量が高いため、現在新しい処理を開始できません。',
                    'message': f'現在のメモリ使用量: {resources["memory_mb"]:.1f}MB（警告閾値: {MEMORY_WARNING_MB}MB）',
                    'retry_after': 60,  # 60秒後にリトライを推奨
                    'status_code': 503
                }), 503
        except Exception as memory_check_error:
            # メモリチェックのエラーはログに記録するが、処理は続行（安全側に倒す）
            logger.error(f"memory_guard_check_error: {memory_check_error}")
            # エラー時は警告のみ（処理は継続）
        
        # ユニークなセッションIDを生成
        session_id = create_unique_session_id()
        job_id = str(uuid.uuid4())
        
        # 完全分離されたセッションディレクトリを作成
        session_dir = get_user_session_dir(session_id)
        
        # ファイルを保存（セッションID付きで一意性を確保）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"{session_id}_{timestamp}.xlsx"
        file_path = os.path.join(session_dir, filename)
        file.save(file_path)
        
        # P0-P1: ファイルアップロード直後のメモリ計測（重要イベント）
        if metrics_available:
            log_memory("upload_done", job_id=job_id, session_id=session_id, extra={
                'jobs_count': len(jobs),
                'sessions_count': len(session_manager['active_sessions'])
            })
        
        # 直列実行＋キュー: running が上限なら queued に積み、そうでなければ即 running で開始
        with jobs_lock:
            existing_job_id, existing_job = find_live_job_for_queue_key_locked(queue_key)
            if existing_job_id and existing_job:
                touch_job_lease_locked(existing_job, current_time=time.time())
                existing_payload = build_existing_job_response_locked(existing_job_id, existing_job)
                log_job_event(
                    "job_reused",
                    existing_job_id,
                    status=existing_job.get('status'),
                    queue_position=existing_payload.get('queue_position'),
                    elapsed_sec=get_elapsed_sec(existing_job),
                    extra={'reason': 'same_user_race_reuse'}
                )
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                cleanup_user_session(session_id)
                status_code = 202 if existing_job.get('status') == 'queued' else 200
                return jsonify(existing_payload), status_code

            compact_job_queue_locked()
            running_count = sum(1 for j in jobs.values() if j.get('status') == 'running')
            if running_count >= MAX_ACTIVE_SESSIONS:
                if len(job_queue) >= MAX_QUEUE_SIZE:
                    cleanup_user_session(session_id)
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass
                    return jsonify({
                        'error': '現在混雑しています。しばらくしてからお試しください。',
                        'error_code': 'QUEUE_FULL',
                        'status_code': 503
                    }), 503
                # キューに登録
                jobs[job_id] = {
                    'status': 'queued',
                    'logs': deque(maxlen=MAX_JOB_LOGS),
                    'progress': 0,
                    'step_name': '待機中',
                    'current_data': 0,
                    'total_data': 0,
                    'start_time': time.time(),
                    'queued_at': time.time(),
                    'end_time': None,
                    'login_status': 'initializing',
                    'login_message': '現在、他ユーザーが作業中。順番に処理します。',
                    'session_id': session_id,
                    'session_dir': session_dir,
                    'file_path': file_path,
                    'email_hash': hash(email),
                    'company_id': company_id,
                    'queue_key': queue_key,
                    'resource_warnings': [],
                    'last_updated': time.time(),
                    'last_heartbeat_at': time.time(),
                    'lease_expires_at': time.time() + QUEUE_HEARTBEAT_TIMEOUT_SEC,
                    'disconnect_hint_at': None,
                    'client_attached': True,
                }
                job_queue.append(job_id)
                queued_job_params[job_id] = {
                    'email': email,
                    'password': password,
                    'file_path': file_path,
                    'session_dir': session_dir,
                    'session_id': session_id,
                    'company_id': company_id,
                    'file_size': file_size,
                    'queue_key': queue_key,
                }
                queue_identity_index[queue_key] = job_id
                queue_position = get_queue_position_locked(job_id)
                log_job_event("job_created", job_id, status="queued", elapsed_sec=0)
                log_job_event("job_queued", job_id, status="queued", queue_position=queue_position, elapsed_sec=0)
                return jsonify({
                    'job_id': job_id,
                    'session_id': session_id,
                    'status': 'queued',
                    'queue_position': queue_position,
                    'message': '現在、他ユーザーが作業中です。順番に処理します。このまま開いておくと自動で開始します。',
                    'status_url': f'/status/{job_id}'
                }), 202
            
            # 即時開始
            jobs[job_id] = {
                'status': 'running',
                'logs': deque(maxlen=MAX_JOB_LOGS),
                'progress': 0,
                'step_name': 'initializing',
                'current_data': 0,
                'total_data': 0,
                'start_time': time.time(),
                'end_time': None,
                'login_status': 'initializing',
                'login_message': '🔄 処理を初期化中...',
                'session_id': session_id,
                'session_dir': session_dir,
                'file_path': file_path,
                'email_hash': hash(email),
                'company_id': company_id,
                'queue_key': queue_key,
                'resource_warnings': [],
                'last_updated': time.time(),
                'last_heartbeat_at': time.time(),
                'lease_expires_at': time.time() + QUEUE_HEARTBEAT_TIMEOUT_SEC,
                'disconnect_hint_at': None,
                'client_attached': True,
            }
        log_job_event("job_created", job_id, status="running", elapsed_sec=0)
        register_session(session_id, job_id)
        
        resource_warnings = get_resource_warnings()
        if resource_warnings:
            print(f"リソース警告: {', '.join(resource_warnings)}")
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]['resource_warnings'] = resource_warnings
                queue_identity_index[queue_key] = job_id
        
        thread = threading.Thread(
            target=run_automation_impl,
            args=(job_id, email, password, file_path, session_dir, session_id, company_id, file_size)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'session_id': session_id,
            'message': '処理を開始しました',
            'status_url': f'/status/{job_id}',
            'resource_warnings': resource_warnings
        })
        
    except Exception as e:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        if session_id:
            try:
                cleanup_user_session(session_id)
                unregister_session(session_id)
            except Exception:
                pass
        return jsonify({'error': f'予期しないエラーが発生しました: {str(e)}'})

@app.route('/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id):
    """queued のジョブのみキャンセル可能。running は 409。"""
    global job_queue
    with jobs_lock:
        if job_id not in jobs:
            return jsonify({'ok': False, 'error': 'ジョブが見つかりません'}), 404
        job = jobs[job_id]
        if job.get('status') in ('cancelled', 'expired'):
            return jsonify({'ok': True, 'status': job.get('status')}), 200
        if job.get('status') != 'queued':
            return jsonify({'ok': False, 'error': '実行中はキャンセルできません。待機中のみキャンセル可能です。', 'status': job.get('status')}), 409
        # キューから除去
        job_queue = deque([x for x in job_queue if x != job_id])
        queued_job_params.pop(job_id, None)
        jobs[job_id]['status'] = 'cancelled'
        jobs[job_id]['login_status'] = 'cancelled'
        jobs[job_id]['end_time'] = time.time()
        jobs[job_id]['login_message'] = 'キャンセルされました。'
        jobs[job_id]['last_updated'] = time.time()
        jobs[job_id]['client_attached'] = False
        release_queue_identity_locked(job_id, jobs[job_id])
        fp = job.get('file_path')
        sid = job.get('session_id')
        qlen = len(compact_job_queue_locked())
        rcount = sum(1 for j in jobs.values() if j.get('status') == 'running')
    elapsed = get_elapsed_sec(job)
    log_job_event("cancelled", job_id, status="cancelled", elapsed_sec=elapsed, queue_length=qlen, running_count=rcount)
    if fp and os.path.exists(fp):
        try:
            os.remove(fp)
            logger.info(f"cancel_cleanup_file job_id={job_id} path={fp}")
        except Exception as e:
            logger.warning(f"cancel_cleanup_file_error job_id={job_id} error={e}")
    if sid:
        try:
            cleanup_user_session(sid)
            unregister_session(sid)
        except Exception as e:
            logger.warning(f"cancel_cleanup_session_error job_id={job_id} session_id={sid} error={e}")
    return jsonify({'ok': True, 'status': 'cancelled'})


@app.route('/api/queue/detach/<job_id>', methods=['POST'])
def detach_queue_job(job_id):
    """タブ close / reload の補助シグナル。最終的な除外判断は heartbeat timeout で行う。"""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({'ok': True, 'status': 'missing'}), 200
        if job.get('status') not in QUEUE_LIVE_STATUSES:
            return jsonify({'ok': True, 'status': job.get('status'), 'ignored': True}), 200

        current_time = time.time()
        job['disconnect_hint_at'] = current_time
        job['client_attached'] = False
        job['last_updated'] = current_time
        status = job.get('status')
        queue_position = get_queue_position_locked(job_id) if status == 'queued' else None
        elapsed_sec = get_elapsed_sec(job)

    log_job_event("job_detached", job_id, status=status, queue_position=queue_position, elapsed_sec=elapsed_sec)
    return jsonify({'ok': True, 'status': status}), 200


@app.route('/status/<job_id>')
def get_status(job_id):
    try:
        # P0-3: 完了ジョブの間引きは間隔制御（ポーリング負荷軽減）
        global _last_status_prune_time
        now = time.time()
        if now - _last_status_prune_time >= STATUS_PRUNE_INTERVAL_SEC:
            try:
                prune_jobs(current_time=now)
                _last_status_prune_time = now
            except Exception as prune_err:
                logger.warning(f"prune_jobs_error in get_status: {prune_err}")
        
        with jobs_lock:
            if job_id not in jobs:
                print(f"ジョブが見つかりません: {job_id}")
                print(f"現在のジョブ一覧: {list(jobs.keys())}")
                return jsonify({
                    'error': 'ジョブが見つかりません',
                    'job_id': job_id,
                    'available_jobs': list(jobs.keys())
                }), 404
            
            job = jobs[job_id]
            if job.get('status') in QUEUE_LIVE_STATUSES:
                touch_job_lease_locked(job, current_time=now)
            
            # P1: ログページングパラメータを取得
            last_n = request.args.get('last_n', type=int)
            if last_n is not None and (last_n < 1 or last_n > 1000):
                last_n = 1000  # 最大値に制限
            
            # P1: ログを取得（dequeの場合はlistに変換、ページング対応）
            job_logs = job.get('logs', [])
            from collections import deque
            if isinstance(job_logs, deque):
                job_logs = list(job_logs)
            elif not isinstance(job_logs, list):
                job_logs = list(job_logs) if job_logs else []
            
            # P1: ページング対応（最新last_n件のみ返す）
            if last_n is not None and len(job_logs) > last_n:
                job_logs = job_logs[-last_n:]
            
            # ログイン結果の詳細情報を取得
            login_status = job.get('login_status', 'unknown')
            login_message = job.get('login_message', 'ログイン状態が不明です')
            
            # ユーザー向けの詳細メッセージを生成
            user_message = generate_user_message(job['status'], login_status, login_message, job.get('progress', 0))
            
            # リソース情報を追加（エラーが発生しても処理を続行）
            try:
                resources = get_system_resources()
            except Exception as resource_error:
                print(f"リソース情報取得エラー: {resource_error}")
                resources = {'memory_mb': 0, 'cpu_percent': 0, 'active_sessions': 0}
            
            # P0-4: 経過秒数を含める（止まった原因の切り分け用）
            start_ts = job.get('start_time') or 0
            elapsed_sec = round(time.time() - start_ts, 1) if start_ts else 0
            # queued のときキュー内位置を算出（jobs_lock 内のため get_queue_position は使わず自前で取得）
            queue_position = None
            if job.get('status') == 'queued':
                queue_position = get_queue_position_locked(job_id)
            # レスポンスデータを構築
            response_data = {
                'status': job['status'],
                'progress': job.get('progress', 0),
                'step_name': job.get('step_name', ''),
                'current_data': job.get('current_data', 0),
                'total_data': job.get('total_data', 0),
                'logs': job_logs,  # P1: ページング対応済みログ
                'start_time': start_ts,
                'elapsed_sec': elapsed_sec,
                'login_status': login_status,
                'login_message': login_message,
                'user_message': user_message,
                'session_id': job.get('session_id', ''),
                'resources': resources,
                'resource_warnings': job.get('resource_warnings', [])
            }
            if queue_position is not None:
                response_data['queue_position'] = queue_position
            
            # ステータスに応じたHTTPステータスコードを設定
            if job['status'] == 'error':
                return jsonify(response_data), 500
            elif job['status'] == 'completed':
                return jsonify(response_data), 200
            else:
                return jsonify(response_data), 200
                
    except Exception as e:
        print(f"ステータス取得で予期しないエラー: {e}")
        return jsonify({
            'error': 'ステータス取得エラー',
            'status': 'error',
            'progress': 0,
            'login_status': 'error',
            'login_message': 'システムエラーが発生しました'
        }), 500

@app.route('/sessions')
def get_active_sessions():
    """アクティブセッション情報を取得"""
    try:
        with session_manager['session_lock']:
            active_sessions = session_manager['active_sessions'].copy()
        with jobs_lock:
            compact_job_queue_locked()
            queued_jobs = [job_id for job_id in job_queue if jobs.get(job_id, {}).get('status') == 'queued']
            stale_waiting = [
                job_id for job_id, job_info in jobs.items()
                if job_info.get('status') == 'queued'
                and (job_info.get('lease_expires_at') or 0) < time.time()
            ]
            detached_active = [
                job_id for job_id, job_info in jobs.items()
                if job_info.get('status') == 'running'
                and not job_info.get('client_attached', True)
            ]
        
        resources = get_system_resources()
        warnings = check_resource_limits()
        
        return jsonify({
            'active_sessions': len(active_sessions),
            'sessions': [
                {
                    'session_id': session_id,
                    'job_id': session_info['job_id'],
                    'start_time': session_info['start_time'],
                    'duration': time.time() - session_info['start_time']
                }
                for session_id, session_info in active_sessions.items()
            ],
            'queue': {
                'queued_jobs': len(queued_jobs),
                'stale_waiting_candidates': len(stale_waiting),
                'detached_active_jobs': len(detached_active),
            },
            'resources': resources,
            'warnings': warnings
        })
    except Exception as e:
        return jsonify({'error': f'セッション情報取得エラー: {str(e)}'})

@app.route('/cleanup-sessions')
def cleanup_expired_sessions():
    """期限切れセッションのクリーンアップ"""
    try:
        current_time = time.time()
        expired_sessions = []
        
        with session_manager['session_lock']:
            for session_id, session_info in list(session_manager['active_sessions'].items()):
                # 30分以上経過したセッションを期限切れとする
                if current_time - session_info['start_time'] > 1800:
                    expired_sessions.append(session_id)
                    del session_manager['active_sessions'][session_id]
        
        # 期限切れセッションのクリーンアップ
        for session_id in expired_sessions:
            cleanup_user_session(session_id)
        
        return jsonify({
            'cleaned_sessions': len(expired_sessions),
            'remaining_sessions': len(session_manager['active_sessions']),
            'message': f'{len(expired_sessions)}個のセッションをクリーンアップしました'
        })
    except Exception as e:
        return jsonify({'error': f'セッションクリーンアップエラー: {str(e)}'})

def generate_user_message(status, login_status, login_message, progress):
    """ユーザー向けメッセージを生成（二重表示防止: processing時はlogin_messageが「ログイン処理中」系なら1文のみ返す）"""
    if status == 'running':
        if login_status == 'success':
            return f"✅ ログイン成功 - {login_message}"
        elif login_status == 'failed':
            return f"❌ ログイン失敗 - {login_message}"
        elif login_status == 'captcha':
            return f"🔄 画像認証が必要です - {login_message}"
        elif login_status == 'processing':
            # 監査対応: login_messageがすでに「ログイン処理中」系ならprefixを付けず重複を防ぐ
            if login_message and 'ログイン処理中' in (login_message or ''):
                return login_message.strip()
            return f"🔄 ログイン処理中... - {login_message}" if login_message else "🔄 ログイン処理中..."
        else:
            return f"🔄 処理中... - {login_message}" if login_message else "🔄 処理中..."
    elif status == 'completed':
        return "✅ 処理完了 勤怠データの入力が完了しました。"
    elif status == 'error':
        return f"❌ エラーが発生しました: {login_message}"
    elif status == 'timeout':
        return f"⏱ タイムアウト - {login_message}" if login_message else "⏱ 処理が時間切れになりました"
    elif status == 'expired':
        return login_message or "⏳ 順番待ちは自動的に終了しました。"
    elif status == 'queued':
        return login_message or "現在、他ユーザーが作業中。順番に処理します。"
    elif status == 'cancelled':
        return login_message or "キャンセルされました。"
    else:
        return "🔄 処理中..."

@app.route('/ads.txt')
def ads_txt():
    """ads.txt を配信（Google AdSense用）"""
    content = "google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0"
    return Response(content, mimetype='text/plain')

@app.route('/robots.txt')
def robots_txt():
    """robots.txt を配信（Sitemap 行は BASE_URL から動的生成）"""
    base_url = (os.getenv('BASE_URL') or 'https://jobcan-automation.onrender.com').rstrip('/')
    content = f"""User-agent: *
Allow: /
Disallow: /status/
Disallow: /autofill
Disallow: /api/
Disallow: /sessions
Disallow: /download-template
Disallow: /download-previous-template
Disallow: /cleanup-sessions

User-agent: Googlebot
Allow: /
Disallow: /status/
Disallow: /autofill
Disallow: /api/
Disallow: /sessions
Disallow: /download-template
Disallow: /download-previous-template
Disallow: /cleanup-sessions

User-agent: AdsBot-Google
Allow: /
Disallow: /status/
Disallow: /autofill
Disallow: /api/
Disallow: /sessions
Disallow: /download-template
Disallow: /download-previous-template
Disallow: /cleanup-sessions

Sitemap: {base_url}/sitemap.xml
"""
    return Response(content, mimetype='text/plain')

_SITEMAP_LASTMOD_MANIFEST = None


def _load_sitemap_lastmod_manifest():
    """data/sitemap_lastmod.json を読み込む。存在しなければ空 dict。"""
    global _SITEMAP_LASTMOD_MANIFEST
    if _SITEMAP_LASTMOD_MANIFEST is not None:
        return _SITEMAP_LASTMOD_MANIFEST
    import json
    manifest_path = os.path.join(app.root_path, 'data', 'sitemap_lastmod.json')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            _SITEMAP_LASTMOD_MANIFEST = json.load(f)
    except (OSError, TypeError, json.JSONDecodeError):
        _SITEMAP_LASTMOD_MANIFEST = {}
    return _SITEMAP_LASTMOD_MANIFEST


def _sitemap_lastmod_for_path(url_path):
    """url_path に対応する lastmod を YYYY-MM-DD で返す。manifest 優先、取得できない場合は None。"""
    path = (url_path or '').strip('/') or ''
    special = {
        '': 'landing.html',
        'autofill': 'autofill.html',
        'guide': 'guide/index.html',
        'guide/complete': 'guide/complete-guide.html',
        'guide/comprehensive-guide': 'guide/comprehensive-guide.html',
        'blog': 'blog/index.html',
        'tools': 'tools/index.html',
        'sitemap.html': 'sitemap.html',
        'case-studies': 'case-studies.html',
        'case-study/contact-center': 'case-study-contact-center.html',
        'case-study/consulting-firm': 'case-study-consulting-firm.html',
        'case-study/remote-startup': 'case-study-remote-startup.html',
    }
    if path in special:
        rel = special[path]
    elif path.startswith('guide/'):
        rel = 'guide/' + path.split('/', 1)[1] + '.html'
    elif path.startswith('blog/'):
        rel = 'blog/' + path.split('/', 1)[1] + '.html'
    elif path.startswith('tools/'):
        rel = 'tools/' + path.split('/', 1)[1] + '.html'
    else:
        rel = (path + '.html') if path else 'landing.html'
    manifest = _load_sitemap_lastmod_manifest()
    if rel in manifest:
        return manifest[rel]
    fpath = os.path.join(app.root_path, 'templates', rel.replace('/', os.sep))
    try:
        mtime = os.path.getmtime(fpath)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
    except (OSError, TypeError):
        return None


@app.route('/sitemap.xml')
def sitemap():
    """XMLサイトマップを動的生成（P0-1: PRODUCTSから自動生成）"""
    from flask import url_for
    from datetime import datetime
    
    # PRODUCTSのインポート（失敗しても続行）
    try:
        from lib.products_catalog import get_public_products
        PRODUCTS = get_public_products()
    except Exception as import_error:
        logger.warning(f"sitemap_import_failed error={str(import_error)} - using empty list")
        PRODUCTS = []
    
    # ベースURL（環境変数があれば採用、末尾スラッシュは除去して二重スラッシュを防ぐ）
    base_url = (os.getenv('BASE_URL') or 'https://jobcan-automation.onrender.com').rstrip('/')
    
    # 現在日付を取得（lastmod のフォールバック）
    today = datetime.now().strftime('%Y-%m-%d')
    
    # サイトマップに含めるURLのリスト
    # 形式: (url_path, changefreq, priority, lastmod)
    # P0-1: 固定ページは維持
    urls = [
        # 主要ページ
        ('/', 'daily', '1.0', today),
        ('/about', 'monthly', '0.8', today),
        ('/faq', 'weekly', '0.8', today),
        ('/glossary', 'monthly', '0.7', today),
        ('/best-practices', 'monthly', '0.8', today),
        
        # ガイドページ（一覧＋固定）
        ('/guide', 'weekly', '0.9', today),
        
        # ツール一覧ページ
        ('/tools', 'weekly', '0.9', today),
        
        # ブログ一覧
        ('/blog', 'daily', '0.8', today),
        
        ('/blog/excel-format-mistakes-and-design', 'monthly', '0.7', today),
    ]
    
    # P0-1: PRODUCTSから利用可能なツールページとガイドページを自動生成
    # URL重複を防ぐために、既存のURLパスを集合で管理
    seen_urls = {url_path for url_path, _, _, _ in urls}
    
    # PRODUCTSがリストであることを確認（恒久対策：型安全性）
    products_list = PRODUCTS if isinstance(PRODUCTS, list) else []
    for product in products_list:
        if product.get('status') == 'available':
            # product.pathを追加（重複チェック）
            product_path = product.get('path')
            if product_path and product_path not in seen_urls:
                # ツールページの優先度と更新頻度を設定
                changefreq = 'monthly'
                priority = '0.7'
                urls.append((product_path, changefreq, priority, today))
                seen_urls.add(product_path)
            
            # guide_pathを追加（重複チェック）
            guide_path = product.get('guide_path')
            if guide_path and guide_path not in seen_urls:
                urls.append((guide_path, 'monthly', '0.8', today))
                seen_urls.add(guide_path)
    
    # XMLサイトマップを生成
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
    """データ処理中のリソース監視（4番目以降で強化）"""
    try:
        resources = get_system_resources()
        memory_usage_percent = (resources['memory_mb'] / MEMORY_LIMIT_MB) * 100
        
        # 4番目のデータ以降はより厳密に監視
        if data_index >= 4:
            logger.info(f"processing_monitor data={data_index}/{total_data} memory={resources['memory_mb']:.1f}MB/{MEMORY_LIMIT_MB}MB ({memory_usage_percent:.1f}%) cpu={resources['cpu_percent']:.1f}%")
            
            # メモリ使用率が85%を超えた場合は警告
            if memory_usage_percent > 85:
                logger.warning(f"critical_memory_usage data={data_index} memory={resources['memory_mb']:.1f}MB ({memory_usage_percent:.1f}%) - approaching OOM")
                
                # メモリ使用率が90%を超えた場合は緊急停止
                if memory_usage_percent > 90:
                    logger.error(f"emergency_memory_stop data={data_index} memory={resources['memory_mb']:.1f}MB ({memory_usage_percent:.1f}%) - preventing OOM")
                    raise RuntimeError(f"メモリ使用率が危険域に達しました: {memory_usage_percent:.1f}%")
        
        return True
    except Exception as e:
        logger.error(f"processing_monitor_failed data={data_index} error={str(e)}")
        raise

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 
