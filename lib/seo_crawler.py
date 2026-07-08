# -*- coding: utf-8 -*-
"""
SEO sitemap 用 URL クローラ（同一ホスト・BFS・制限付き）
SSRF対策: is_url_safe_for_crawl で開始URL・リダイレクト先を検証
"""

import socket
import time
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse

try:
    import ipaddress
except ImportError:
    ipaddress = None

# 許可しないホスト名（小文字）
BLOCKED_HOSTNAMES = frozenset({
    'localhost', 'localhost.localdomain', '0.0.0.0', '::1', '::',
    'ip6-localhost', 'ip6-loopback', 'ip6-localnet', 'ip6-mcastprefix',
})

# 収集対象から除外する拡張子（小文字）
EXCLUDED_EXTENSIONS = (
    '.pdf', '.zip', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff',
    '.css', '.js', '.mjs', '.ico', '.svg', '.woff', '.woff2', '.ttf', '.eot',
    '.mp4', '.mp3', '.webm', '.ogg', '.wav', '.avi', '.mov', '.m4a',
    '.xml', '.json', '.txt', '.rss', '.atom', '.yaml', '.yml',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.exe', '.dmg', '.apk', '.tar', '.gz', '.rar', '.7z',
)

# User-Agent（robots.txt 取得・ページ取得で使用）
USER_AGENT = 'JobcanAutomationBot/1.0 (+contact)'

# HTML として解析する Content-Type（メイン部分のみ一致）
ALLOWED_HTML_CONTENT_TYPES = frozenset({'text/html', 'application/xhtml+xml'})


def is_url_safe_for_crawl(url):
    """
    SSRF対策: URL がクロール許可対象か検証する。
    - scheme は http/https のみ
    - hostname が禁止リストまたは .local なら拒否
    - DNS解決したIPが private/loopback/link-local/unspecified なら拒否

    Returns:
        (True, None) または (False, error_message: str)
    """
    if not url or not isinstance(url, str):
        return False, 'URLが空です'
    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception:
        return False, 'URLの解析に失敗しました'
    if parsed.scheme not in ('http', 'https'):
        return False, 'http または https のURLのみ許可されています'
    if getattr(parsed, 'username', None) or getattr(parsed, 'password', None) or ('@' in (parsed.netloc or '')):
        return False, 'URLに認証情報（user:pass@）を含めることはできません'
    if not parsed.netloc:
        return False, 'ホストが指定されていません'
    hostname = (parsed.hostname or '').strip().lower()
    if not hostname:
        return False, 'ホスト名が取得できません'
    if hostname in BLOCKED_HOSTNAMES:
        return False, 'このホストは許可されていません'
    if hostname.endswith('.local'):
        return False, 'このホストは許可されていません'
    if not ipaddress:
        return False, 'IPアドレス検証に必要なモジュールがありません'
    try:
        if hostname.startswith('[') and hostname.endswith(']'):
            hostname = hostname[1:-1]
        ips = set()
        for res in socket.getaddrinfo(hostname, None):
            sockaddr = res[4]
            ip = sockaddr[0] if isinstance(sockaddr, (list, tuple)) else sockaddr
            ips.add(ip)
    except socket.gaierror:
        return False, 'ホスト名の解決に失敗しました'
    except Exception:
        return False, 'ホスト名の解決に失敗しました'
    for ip in ips:
        try:
            addr = ipaddress.ip_address(ip)
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_unspecified:
                return False, '内部・ローカル用のアドレスにはアクセスできません'
        except ValueError:
            return False, '無効なIPアドレスが解決されました'
    return True, None


def _get_requests():
    try:
        import requests
        return requests
    except ImportError:
        return None


def _get_bs4():
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup
    except ImportError:
        return None


def normalize_url(url, strip_query=True):
    """URLを正規化（フラグメント除去、クエリ除去、パス末尾スラッシュ統一）"""
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return None
    path = parsed.path or '/'
    path = path.rstrip('/') or '/'
    if strip_query:
        query = ''
        fragment = ''
    else:
        query = parsed.query
        fragment = parsed.fragment
    normalized = urlunparse((parsed.scheme, parsed.netloc.lower(), path, parsed.params, query, fragment))
    return normalized


def _should_exclude_by_extension(url):
    """除外拡張子に該当する場合、その拡張子を返す。該当しなければ None を返す。"""
    path = urlparse(url).path or '/'
    path_lower = path.lower()
    base = path_lower.rstrip('/')
    for ext in EXCLUDED_EXTENSIONS:
        if path_lower.endswith(ext) or base.endswith(ext):
            return ext
    return None


def _fetch_robots_disallow_prefixes(origin, request_timeout, requests_mod):
    """robots.txt を取得し、Disallow のパスプレフィックスを返す（簡易）"""
    prefixes = []
    try:
        robots_url = f"https://{origin}/robots.txt" if not origin.startswith('http') else urljoin(origin, '/robots.txt')
        if not robots_url.startswith('http'):
            robots_url = f"https://{origin}/robots.txt"
        r = requests_mod.get(robots_url, timeout=request_timeout, headers={'User-Agent': USER_AGENT})
        if r.status_code != 200:
            return []
        for line in r.text.splitlines():
            line = line.strip()
            if line.lower().startswith('disallow:'):
                path = line[9:].strip()
                if path and path != '/':
                    prefixes.append(path if path.startswith('/') else '/' + path)
    except Exception:
        pass
    return prefixes


def _is_disallowed(path, disallow_prefixes):
    """パスが Disallow のいずれかにマッチするか（プレフィックス一致）"""
    path = path or '/'
    for prefix in disallow_prefixes:
        p = prefix.rstrip('*')
        if path == p or path.startswith(p.rstrip('/') + '/') or path.startswith(p):
            return True
    return False


def crawl(start_url, max_urls=300, max_depth=3, request_timeout=5, total_timeout=60):
    """
    同一ホスト内で BFS クロールし、URL 一覧を返す。

    Args:
        start_url: 開始URL
        max_urls: 最大収集URL数
        max_depth: 最大深さ（0が開始URLのみ）
        request_timeout: 1リクエストあたりのタイムアウト（秒）
        total_timeout: 全体のタイムアウト（秒）

    Returns:
        (urls: list[str], warnings: list[str])
    """
    requests_mod = _get_requests()
    BeautifulSoup = _get_bs4()
    if not requests_mod or not BeautifulSoup:
        return [], ['requests または beautifulsoup4 がインストールされていません']

    try:
        parsed_start = urlparse(start_url)
        if parsed_start.scheme not in ('http', 'https') or not parsed_start.netloc:
            return [], ['開始URLが無効です（http/https の完全なURLを指定してください）']
        origin = parsed_start.netloc.lower()
        start_normalized = normalize_url(start_url)
        if not start_normalized:
            return [], ['開始URLの正規化に失敗しました']
    except Exception as e:
        return [], [f'開始URLの解析エラー: {e}']

    disallow_prefixes = _fetch_robots_disallow_prefixes(
        f"{parsed_start.scheme}://{parsed_start.netloc}",
        request_timeout,
        requests_mod
    )

    visited = set()
    urls = []
    warnings = []
    queue = deque([(start_url, 0)])
    deadline = time.time() + total_timeout

    while queue and time.time() < deadline and len(urls) < max_urls:
        current, depth = queue.popleft()

        if depth > max_depth:
            continue

        try:
            norm = normalize_url(current)
        except Exception:
            continue
        if not norm or norm in visited:
            continue
        if urlparse(norm).netloc.lower() != origin:
            continue

        path = urlparse(norm).path or '/'
        if _is_disallowed(path, disallow_prefixes):
            warnings.append(f'robots.txt により除外: {norm}')
            continue
        ext_reason = _should_exclude_by_extension(norm)
        if ext_reason:
            warnings.append(f'除外（拡張子 {ext_reason}）: {norm}')
            continue

        visited.add(norm)
        urls.append(norm)

        if len(urls) >= max_urls:
            warnings.append(f'最大URL数（{max_urls}）に達したため打ち切りました')
            break

        try:
            fetch_url = current
            r = None
            max_redirects = 5
            redirect_count = 0
            while redirect_count <= max_redirects:
                r = requests_mod.get(
                    fetch_url,
                    timeout=request_timeout,
                    headers={'User-Agent': USER_AGENT},
                    allow_redirects=False
                )
                if r.status_code in (301, 302, 303, 307, 308):
                    if redirect_count >= max_redirects:
                        warnings.append(f'リダイレクトが最大回数（{max_redirects}回）を超えました: {fetch_url}')
                        r = None
                        break
                    location = r.headers.get('Location') or r.headers.get('location') or ''
                    if not location.strip():
                        warnings.append(f'リダイレクト先（Location）が空です: {fetch_url}')
                        r = None
                        break
                    next_url = urljoin(fetch_url, location.strip())
                    safe, err = is_url_safe_for_crawl(next_url)
                    if not safe:
                        warnings.append(f'リダイレクト先が許可されていません: {next_url} ({err})')
                        r = None
                        break
                    if urlparse(next_url).netloc.lower() != origin:
                        warnings.append(f'リダイレクト先が別ホストのためスキップ: {next_url}')
                        r = None
                        break
                    fetch_url = next_url
                    redirect_count += 1
                    continue
                if r.status_code != 200:
                    warnings.append(f'取得失敗 HTTP {r.status_code}: {fetch_url}')
                    r = None
                    break
                break
            if r is None:
                continue
            ct = r.headers.get('Content-Type', '')
            ct_main = (ct.split(';')[0].strip().lower() if ct else '') or 'application/octet-stream'
            if ct_main not in ALLOWED_HTML_CONTENT_TYPES:
                warnings.append(f'除外（HTML以外のContent-Type: {ct_main}）: {current}')
                continue
        except requests_mod.exceptions.Timeout:
            warnings.append(f'タイムアウト: {current}')
            continue
        except requests_mod.exceptions.RequestException as e:
            warnings.append(f'取得失敗 {current}: {getattr(e, "message", str(e))}')
            continue
        except Exception as e:
            warnings.append(f'エラー {current}: {e}')
            continue

        try:
            soup = BeautifulSoup(r.text, 'html.parser')
        except Exception:
            continue

        final_url = fetch_url
        for a in soup.find_all('a', href=True):
            href = (a.get('href') or '').strip()
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            try:
                abs_url = urljoin(final_url, href)
            except Exception:
                continue
            abs_parsed = urlparse(abs_url)
            if abs_parsed.scheme not in ('http', 'https') or not abs_parsed.netloc:
                continue
            if abs_parsed.netloc.lower() != origin:
                continue
            try:
                child_norm = normalize_url(abs_url)
            except Exception:
                continue
            if not child_norm or child_norm in visited:
                continue
            if _is_disallowed(abs_parsed.path or '/', disallow_prefixes):
                continue
            if _should_exclude_by_extension(child_norm):
                continue
            queue.append((abs_url, depth + 1))

    if time.time() >= deadline:
        warnings.append('全体のタイムアウト（60秒）に達しました')

    return urls, warnings
