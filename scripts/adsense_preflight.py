#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public preflight checks for AdSense, affiliate, SEO, and removed legacy surfaces."""
import argparse
import os
import re
import sys
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL_DEFAULT = 'https://oshigoto.onrender.com'
MAJOR_PATHS = ['/', '/tools', '/business', '/privacy', '/terms', '/contact', '/about', '/faq', '/guide', '/blog', '/glossary', '/best-practices']
TOOL_PATHS = ['/tools/pdf', '/tools/csv', '/tools/image-batch', '/tools/image-compress', '/tools/image-cleanup', '/tools/seo']
GUIDE_PATHS = ['/guide/pdf', '/guide/csv', '/guide/image-batch', '/guide/image-compress', '/guide/image-cleanup', '/guide/seo']
INDEXABLE_PATHS = ['/', '/tools', '/business', '/guide', '/blog', '/glossary'] + TOOL_PATHS + GUIDE_PATHS
PUBLIC_AFFILIATE_PATHS = ['/', '/tools'] + TOOL_PATHS
ADSENSE_SCRIPT_SRC = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4232725615106709'
ADSENSE_HEAD_PATHS = ['/', '/tools', '/tools/pdf', '/tools/image-compress']
A8_SCRIPT_SRC = 'https://rot3.a8.net/jsa/fdf80b714de10cbdd802fd2333444e15/c6f057b86584942e415435ffb1fa93d4.js'
NO_VISIBLE_AFFILIATE_PATHS = ['/business', '/contact', '/privacy', '/terms']
A8_PUBLIC_PATHS = [
    path for path in MAJOR_PATHS + TOOL_PATHS + GUIDE_PATHS
    if path not in NO_VISIBLE_AFFILIATE_PATHS
]
FORBIDDEN_PUBLIC_STRINGS = [
    'Jobcan',
    'AutoFill',
    'YCP',
    'unlock',
    'decrypt',
    'No.1',
    'ランキング1位',
    '星評価',
    'レビュー数',
    '在庫',
]
AMAZON_EXPECTED_ASSOCIATE_TAG = (os.getenv('AMAZON_ASSOCIATE_TAG') or '').strip()


def _local_getter():
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()

    def get(path, headers=None):
        return client.get(path, headers=headers or {}, follow_redirects=False)

    return get


def _body(resp):
    return resp.data.decode('utf-8', errors='replace') if hasattr(resp, 'data') else resp[1]


def _status(resp):
    return resp.status_code if hasattr(resp, 'status_code') else resp[0]


def _headers(resp):
    return resp.headers if hasattr(resp, 'headers') else resp[2]


def _amazon_urls(html):
    return re.findall(r'https://www\.amazon\.co\.jp/[^"\'<> ]+', html)


def run_checks(get):
    rows = []
    ok_all = True

    def add(name, target, ok, detail=''):
        nonlocal ok_all
        rows.append((name, target, 'OK' if ok else f'FAIL {detail}', ok))
        if not ok:
            ok_all = False

    for path in MAJOR_PATHS + TOOL_PATHS + GUIDE_PATHS:
        try:
            resp = get(path)
            add('route_200', path, _status(resp) == 200, f'status={_status(resp)}')
        except Exception as exc:
            add('route_200', path, False, str(exc))

    resp = get('/autofill')
    add('autofill_redirect', '/autofill', _status(resp) == 301 and (_headers(resp).get('Location') or '').endswith('/tools'), f'status={_status(resp)} loc={_headers(resp).get("Location")}')
    resp = get('/api/pdf/unlock')
    add('pdf_unlock_404', '/api/pdf/unlock', _status(resp) == 404, f'status={_status(resp)}')

    business_body = _body(get('/business'))
    add('business_title', '/business', '企業向け業務効率化支援' in business_body)
    add('business_h1', '/business', '企業の定型業務を' in business_body and '小さなツールから効率化' in business_body)
    add('business_canonical', '/business', 'https://oshigoto.onrender.com/business' in business_body)
    add('business_contact_cta', '/business', 'href="/contact"' in business_body)
    add('business_tools_cta', '/business', 'href="/tools"' in business_body)
    add('business_header_link', '/business', 'href="/business"' in business_body and '企業向け' in business_body)
    add('business_no_unverified_claims', '/business', not any(term in business_body for term in (
        '無料相談', '必ず削減', '必ず効率化', '導入事例', 'ISO認証', 'SOC2', 'ISMS', 'aggregateRating', 'reviewCount'
    )))
    landing_body = _body(get('/'))
    add('business_landing_link', '/', 'href="/business"' in landing_body and '企業向け支援を見る' in landing_body)

    pdf_body = _body(get('/tools/pdf'))
    browser_size = re.search(r'const BROWSER_PDF_MAX_FILE_SIZE_MB = (\d+);', pdf_body)
    browser_pages = re.search(r'const BROWSER_PDF_MAX_PAGES = (\d+);', pdf_body)
    lock_size = re.search(r'const PDF_LOCK_MAX_FILE_SIZE_MB = (\d+);', pdf_body)
    lock_pages = re.search(r'const PDF_LOCK_MAX_PAGES = (\d+);', pdf_body)
    browser_limit_copy = browser_size and browser_pages and f'ブラウザ内PDF処理: 1ファイル最大{browser_size.group(1)}MB・最大{browser_pages.group(1)}ページ' in pdf_body
    server_limit_copy = lock_size and lock_pages and f'パスワード設定: 1ファイル最大{lock_size.group(1)}MB・最大{lock_pages.group(1)}ページ' in pdf_body
    add('pdf_page_delete_mode', '/tools/pdf', 'data-mode="page-delete"' in pdf_body and 'id="delete-range"' in pdf_body)
    add('pdf_page_rotate_mode', '/tools/pdf', 'data-mode="page-rotate"' in pdf_body and 'id="rotate-angle"' in pdf_body)
    add('pdf_browser_limits', '/tools/pdf', bool(browser_limit_copy))
    add('pdf_server_limits', '/tools/pdf', bool(server_limit_copy))
    add('pdf_no_unlock_endpoint', '/tools/pdf', '/api/pdf/unlock' not in pdf_body)

    image_body = _body(get('/tools/image-compress'))
    image_guide_body = _body(get('/guide/image-compress'))
    max_files = re.search(r'data-max-files="(\d+)"', image_body)
    max_file_mb = re.search(r'data-max-file-mb="(\d+)"', image_body)
    max_total_mb = re.search(r'data-max-total-mb="(\d+)"', image_body)
    max_pixels = re.search(r'data-max-pixels="(\d+)"', image_body)
    max_long_edge = re.search(r'data-max-long-edge="(\d+)"', image_body)
    add('image_compress_h1', '/tools/image-compress', '<h1>画像を軽くする</h1>' in image_body)
    add('image_compress_canonical', '/tools/image-compress', 'https://oshigoto.onrender.com/tools/image-compress' in image_body)
    add('image_compress_guide_canonical', '/guide/image-compress', 'https://oshigoto.onrender.com/guide/image-compress' in image_guide_body)
    add('image_compress_browser_only', '/tools/image-compress', 'Oshigotoのサーバーへ送信されません' in image_body)
    add('image_compress_static_formats', '/tools/image-compress', all(term in image_body for term in ('image/jpeg', 'image/png', 'image/webp')))
    add('image_compress_limits_present', '/tools/image-compress', all((max_files, max_file_mb, max_total_mb, max_pixels, max_long_edge)))
    if all((max_files, max_file_mb, max_total_mb, max_pixels, max_long_edge)):
        limit_copy_ok = (
            f'最大{max_files.group(1)}件' in image_body
            and f'1件{max_file_mb.group(1)}MB' in image_body
            and f'合計{max_total_mb.group(1)}MB' in image_body
            and f'最大{int(max_pixels.group(1)):,}画素' in image_body
            and f'長辺{int(max_long_edge.group(1)):,}px' in image_body
        )
        add('image_compress_limit_copy', '/tools/image-compress', limit_copy_ok)
    add('image_compress_no_false_support', '/tools/image-compress', not any(term in image_body for term in (
        'GIF対応', 'HEIC対応', 'SVG対応', 'TIFF対応', 'OCR対応', '背景削除に対応'
    )))
    affiliate_blocks = re.findall(r'<section\b[^>]*class="[^"]*\baffiliate-context-block\b', image_body, flags=re.I | re.S)
    add('image_compress_affiliate_block_limit', '/tools/image-compress', len(affiliate_blocks) <= 1, f'count={len(affiliate_blocks)}')
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'js', 'image-compress.js')
    with open(script_path, encoding='utf-8') as handle:
        image_script = handle.read()
    add('image_compress_no_upload_api', 'static/js/image-compress.js', not any(term in image_script for term in (
        'fetch(', 'XMLHttpRequest', 'FormData', 'localStorage', 'sessionStorage', 'indexedDB'
    )))
    add('image_compress_safe_dom', 'static/js/image-compress.js', 'innerHTML' not in image_script and 'console.log' not in image_script and 'console.debug' not in image_script)


    for path in ADSENSE_HEAD_PATHS:
        body = _body(get(path))
        lower_body = body.lower()
        script_count = body.count(ADSENSE_SCRIPT_SRC)
        script_pos = body.find(ADSENSE_SCRIPT_SRC)
        head_end = lower_body.find('</head>')
        add('adsense_script_once', path, script_count == 1, f'count={script_count}')
        add('adsense_script_in_head', path, script_pos != -1 and head_end != -1 and script_pos < head_end, f'script_pos={script_pos} head_end={head_end}')
    for path in INDEXABLE_PATHS:
        resp = get(path)
        body = _body(resp)
        robots_meta = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', body, flags=re.I)
        content = robots_meta.group(1).lower() if robots_meta else ''
        add('indexable', path, 'noindex' not in content, f'robots={content}')

    for path in MAJOR_PATHS + TOOL_PATHS + GUIDE_PATHS:
        body = _body(get(path))
        leaks = [s for s in FORBIDDEN_PUBLIC_STRINGS if s in body]
        add('public_copy', path, not leaks, ','.join(leaks))

    sitemap = _body(get('/sitemap.xml'))
    for path in TOOL_PATHS + GUIDE_PATHS + ['/faq', '/privacy']:
        add('sitemap_required', path, path in sitemap)
    add('sitemap_excludes_autofill', '/autofill', '/autofill' not in sitemap)

    robots = _body(get('/robots.txt'))
    add('robots_sitemap', '/robots.txt', 'https://oshigoto.onrender.com/sitemap.xml' in robots or '/sitemap.xml' in robots)
    add('robots_autofill_disallow', '/robots.txt', 'Disallow: /autofill' in robots)

    for path in A8_PUBLIC_PATHS:
        body = _body(get(path))
        a8_count = body.count(A8_SCRIPT_SRC)
        add('a8_present_once', path, a8_count == 1, f'count={a8_count}')

    for path in NO_VISIBLE_AFFILIATE_PATHS:
        body = _body(get(path))
        add('affiliate_excluded_a8', path, A8_SCRIPT_SRC not in body)
        add('affiliate_excluded_amazon', path, not _amazon_urls(body))
        add('affiliate_excluded_wrapper', path, 'affiliate-cards-section' not in body and 'affiliate-context-block' not in body)

    for path in PUBLIC_AFFILIATE_PATHS:
        body = _body(get(path))
        urls = _amazon_urls(body)
        if AMAZON_EXPECTED_ASSOCIATE_TAG:
            missing = []
            duplicate = []
            for url in urls:
                parsed = urlparse(url.replace('&amp;', '&'))
                tags = parse_qs(parsed.query).get('tag', [])
                if AMAZON_EXPECTED_ASSOCIATE_TAG not in tags:
                    missing.append(url)
                if len(tags) > 1:
                    duplicate.append(url)
            add('amazon_tag', path, not missing and not duplicate, f'missing={len(missing)} duplicate={len(duplicate)}')
        else:
            add('amazon_tag_unset', path, True, 'tag not required when unset')
        add('affiliate_disclosure', path, 'Amazon' in body or 'affiliate' in body.lower())

    for name, target, result, _ in rows:
        print(f'[{name}] {target}: {result}')
    if ok_all:
        print('ALL CHECKS PASSED')
        return 0
    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', default=None, help='Optional live base URL. Local test client is used by default.')
    args = parser.parse_args()
    if args.live:
        import requests
        base = args.live.rstrip('/')
        def get(path, headers=None):
            return requests.get(base + path, headers=headers or {}, allow_redirects=False, timeout=20)
        return run_checks(get)
    return run_checks(_local_getter())


if __name__ == '__main__':
    sys.exit(main())
