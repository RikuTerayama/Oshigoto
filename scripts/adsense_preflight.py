#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public preflight checks for AdSense, affiliate, SEO, and removed legacy surfaces."""
import argparse
import hashlib
import os
import re
import sys
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL_DEFAULT = 'https://oshigoto.onrender.com'
MAJOR_PATHS = ['/', '/tools', '/business', '/privacy', '/terms', '/contact', '/about', '/faq', '/guide', '/blog', '/glossary', '/best-practices']
TOOL_PATHS = ['/tools/pdf', '/tools/csv', '/tools/image-batch', '/tools/image-compress', '/tools/qr-code', '/tools/image-cleanup', '/tools/seo']
GUIDE_PATHS = ['/guide/pdf', '/guide/csv', '/guide/image-batch', '/guide/image-compress', '/guide/qr-code', '/guide/image-cleanup', '/guide/seo']
INDEXABLE_PATHS = ['/', '/tools', '/business', '/guide', '/blog', '/glossary'] + TOOL_PATHS + GUIDE_PATHS
PUBLIC_AFFILIATE_PATHS = ['/', '/tools'] + TOOL_PATHS
ADSENSE_SCRIPT_SRC = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4232725615106709'
ADSENSE_HEAD_PATHS = ['/', '/tools', '/tools/pdf', '/tools/image-compress', '/tools/qr-code']
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

    for path in ('/tools/ocr', '/guide/ocr', '/api/ocr', '/_internal/ocr-spike'):
        resp = get(path)
        add('ocr_not_public', path, _status(resp) == 404, f'status={_status(resp)}')

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    public_ocr_files = (
        os.path.join(repo_root, 'lib', 'products_catalog.py'),
        os.path.join(repo_root, 'lib', 'nav.py'),
        os.path.join(repo_root, 'lib', 'seo.py'),
        os.path.join(repo_root, 'templates', 'landing.html'),
        os.path.join(repo_root, 'templates', 'tools', 'index.html'),
        os.path.join(repo_root, 'templates', 'guide', 'index.html'),
    )
    for path in public_ocr_files:
        with open(path, encoding='utf-8') as handle:
            text = handle.read().lower()
        add('ocr_absent_from_public_config', path, '/tools/ocr' not in text and '/guide/ocr' not in text)

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

    batch_body = _body(get('/tools/image-batch'))
    batch_guide_body = _body(get('/guide/image-batch'))
    batch_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    batch_script_paths = [
        os.path.join(batch_root, 'static', 'js', 'image-format-core.js'),
        os.path.join(batch_root, 'static', 'js', 'image-batch-convert.js'),
    ]
    batch_scripts = ''
    for batch_script_path in batch_script_paths:
        with open(batch_script_path, encoding='utf-8') as handle:
            batch_scripts += handle.read()
    add('image_batch_canonical', '/tools/image-batch', 'https://oshigoto.onrender.com/tools/image-batch' in batch_body)
    add('image_batch_guaranteed_formats', '/tools/image-batch', all(term in batch_body for term in ('JPEG', 'PNG', 'WebP')))
    add('image_batch_conditional_formats', '/tools/image-batch', all(term in batch_body for term in ('静止GIF', 'BMP', 'AVIF', 'ブラウザ')))
    add('image_batch_runtime_avif', '/tools/image-batch', 'detectAvifEncodeSupport' in batch_body and 'output-avif-option' in batch_body)
    add('image_batch_limits', '/tools/image-batch', all(term in batch_body for term in (
        'data-max-files="50"', 'data-max-file-mb="20"', 'data-max-total-mb="200"',
        'data-max-pixels="40000000"', 'data-max-long-edge="16384"'
    )))
    add('image_batch_guide_scope', '/guide/image-batch', all(term in batch_guide_body for term in (
        '正式対応する入力形式', 'ブラウザ依存の入力形式', '非対応形式', 'アニメーションGIF'
    )))
    add('image_batch_no_false_claims', '/tools/image-batch', not any(term in batch_body for term in (
        '全形式対応', 'すべての形式', 'どの形式にも対応', 'あらゆる画像形式', 'HEIC対応', 'TIFF対応', 'SVG対応', 'アニメーションGIF対応'
    )))
    add('image_batch_no_upload_api', 'image batch scripts', not any(term in batch_scripts for term in (
        'fetch(', 'XMLHttpRequest', 'FormData', 'localStorage', 'sessionStorage', 'indexedDB'
    )))
    add('image_batch_output_verification', 'static/js/image-format-core.js', 'validateEncodedBuffer' in batch_scripts and 'blob.type' in batch_scripts)
    add('image_batch_no_debug_logging', 'image batch scripts', 'console.log' not in batch_scripts and 'console.debug' not in batch_scripts)

    qr_body = _body(get('/tools/qr-code'))
    qr_guide_body = _body(get('/guide/qr-code'))
    qr_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    qr_core_path = os.path.join(qr_root, 'static', 'js', 'qr-code-core.js')
    qr_ui_path = os.path.join(qr_root, 'static', 'js', 'qr-code.js')
    qr_vendor_path = os.path.join(qr_root, 'static', 'vendor', 'qrcode', '1.5.4', 'qrcode.min.js')
    qr_license_path = os.path.join(qr_root, 'static', 'vendor', 'qrcode', '1.5.4', 'LICENSE')
    qr_notice_path = os.path.join(qr_root, 'THIRD_PARTY_NOTICES.md')
    with open(qr_core_path, encoding='utf-8') as handle:
        qr_core = handle.read()
    with open(qr_ui_path, encoding='utf-8') as handle:
        qr_ui = handle.read()
    with open(qr_vendor_path, 'rb') as handle:
        qr_vendor = handle.read()
    with open(qr_license_path, encoding='utf-8') as handle:
        qr_license = handle.read()
    with open(qr_notice_path, encoding='utf-8') as handle:
        qr_notice = handle.read()
    add('qr_h1', '/tools/qr-code', '<h1>QRコードを作る</h1>' in qr_body)
    add('qr_canonical', '/tools/qr-code', 'https://oshigoto.onrender.com/tools/qr-code' in qr_body)
    add('qr_guide_canonical', '/guide/qr-code', 'https://oshigoto.onrender.com/guide/qr-code' in qr_guide_body)
    add('qr_web_application_schema', '/tools/qr-code', '"@type": "WebApplication"' in qr_body and 'QRコード作成' in qr_body)
    add('qr_guide_article_schema', '/guide/qr-code', '"@type": "Article"' in qr_guide_body)
    add('qr_guide_faq_schema', '/guide/qr-code', '"@type": "FAQPage"' in qr_guide_body and qr_guide_body.count('"@type": "Question"') == 7)
    add('qr_five_types_only', '/tools/qr-code', qr_body.count('name="qr-type"') == 5 and all(f'value="{value}"' in qr_body for value in ('url', 'text', 'email', 'phone', 'wifi')))
    add('qr_browser_only', '/tools/qr-code', 'Oshigotoのサーバーへ送信されません' in qr_body and '/api/qr' not in qr_body)
    add('qr_byte_limit', '/tools/qr-code', '1,000 bytes' in qr_body and 'MAX_PAYLOAD_BYTES = 1000' in qr_core)
    add('qr_wifi_warning', '/tools/qr-code', 'Wi-Fi用QRコードには接続パスワードが含まれます' in qr_body)
    add('qr_no_url_safety_claim', '/tools/qr-code', 'リンク先の安全性はこのツールでは確認しません' in qr_body)
    add('qr_png_svg_outputs', '/tools/qr-code', all(marker in qr_body for marker in ('PNGで保存', 'SVGで保存')) and all(marker in qr_ui for marker in ('verifyPng', 'verifySvg')))
    add('qr_blob_cleanup', 'static/js/qr-code.js', 'revokeObjectURL' in qr_ui and 'pagehide' in qr_ui and 'clearOutput' in qr_ui)
    add('qr_no_upload_or_storage', 'QR scripts', not any(term in qr_core + qr_ui for term in (
        'fetch(', 'XMLHttpRequest', 'FormData', 'WebSocket', 'sendBeacon', 'localStorage', 'sessionStorage', 'indexedDB', 'document.cookie'
    )))
    add('qr_safe_dom', 'QR scripts', 'innerHTML' not in qr_core + qr_ui and 'insertAdjacentHTML' not in qr_core + qr_ui)
    add('qr_no_debug_logging', 'QR scripts', 'console.log' not in qr_core + qr_ui and 'console.debug' not in qr_core + qr_ui)
    add('qr_no_extra_features', '/tools/qr-code', not any(term in qr_body + qr_guide_body for term in (
        'QRコードを読み取る', 'QRコードスキャナー', 'カメラで読み取る', '動的QR', 'アクセス解析QR', '決済QR', 'vCard', '短縮URL', 'ロゴ埋め込み'
    )))
    add('qr_local_vendor', '/tools/qr-code', 'vendor/qrcode/1.5.4/qrcode.min.js' in qr_body and not any(term in qr_body for term in ('unpkg.com/qrcode', 'cdn.jsdelivr.net/npm/qrcode')))
    add('qr_vendor_checksum', qr_vendor_path, hashlib.sha256(qr_vendor).hexdigest() == '7706f84597d8466955504c52eab2e9dd9c345626509ea13476863649d01f81dd')
    add('qr_vendor_license', qr_license_path, 'The MIT License (MIT)' in qr_license and 'Copyright (c) 2012 Ryan Day' in qr_license)
    add('qr_vendor_notice', qr_notice_path, all(marker in qr_notice for marker in ('qrcode 1.5.4', '3848ed2c17de5bcdead487417dbf14c5dd017f8d', '0c7274f0c299f39c2fddf54a2e0039b785977b0173c02d0b3f65fad68923e2b0')))
    qr_template_path = os.path.join(qr_root, 'templates', 'tools', 'qr-code.html')
    with open(qr_template_path, encoding='utf-8') as handle:
        qr_template = handle.read()
    add('qr_no_inline_affiliate_near_controls', qr_template_path, 'affiliate_' not in qr_template and "includes/footer.html" in qr_template)
    add('qr_fixed_colors', qr_template_path, 'type="color"' not in qr_template and '#000000' in qr_ui and '#FFFFFF' in qr_ui)


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
    add('sitemap_excludes_ocr', '/sitemap.xml', '/tools/ocr' not in sitemap and '/guide/ocr' not in sitemap)
    landing = _body(get('/'))
    add('landing_excludes_ocr', '/', '/tools/ocr' not in landing and '/guide/ocr' not in landing)
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
