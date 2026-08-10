#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke tests for the public Oshigoto routes."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.a8_affiliate_catalog import (  # noqa: E402
    A8_ELIGIBLE_EXACT_PATHS,
    A8_HARD_EXCLUDED_PATHS,
    get_a8_visible_limit,
)


def _looks_like_error_page(body):
    lowered = body.lower()
    return (
        '<title>error' in lowered
        or '<h1>error' in lowered
        or 'internal server error' in lowered
        or 'traceback (most recent call last)' in lowered
    )


def _check_a8_catalog_rendering(client, failed):
    eligible_paths = sorted(A8_ELIGIBLE_EXACT_PATHS) + ['/blog/excel-format-mistakes-and-design']
    for path in eligible_paths:
        response = client.get(path, follow_redirects=False)
        body = response.data.decode('utf-8', errors='replace')
        if response.status_code != 200:
            failed.append(f'A8 path={path} expected=200 status={response.status_code}')
            continue
        maximum = get_a8_visible_limit(path)
        actual_count = body.count('data-a8-creative-id="')
        checks = {
            'slot_count': 1 <= actual_count <= maximum,
            'link_count': body.count('https://px.a8.net/svt/ejp') == actual_count,
            'banner_count': body.count('width="300" height="250"') == actual_count,
            'tracker_count': len(re.findall(r'https://www\d+\.a8\.net/0\.gif\?a8mat=', body)) == actual_count,
            'legacy_absent': 'rot3.a8.net' not in body,
        }
        for name, ok in checks.items():
            if not ok:
                failed.append(f'A8 path={path} failed={name}')
    for path in sorted(A8_HARD_EXCLUDED_PATHS):
        body = client.get(path, follow_redirects=False).data.decode('utf-8', errors='replace')
        if any(marker in body for marker in ('data-a8-creative-id="', 'https://px.a8.net/svt/ejp', 'rot3.a8.net')):
            failed.append(f'A8 excluded path={path} contains affiliate creative')


def run_with_test_client():
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()
    expected = {
        '/': 200,
        '/autofill': 301,
        '/about': 200,
        '/business': 200,
        '/tools': 200,
        '/tools/pdf': 200,
        '/tools/csv': 200,
        '/tools/image-batch': 200,
        '/tools/image-compress': 200,
        '/tools/qr-code': 200,
        '/tools/image-cleanup': 200,
        '/tools/seo': 200,
        '/guide': 200,
        '/guide/image-batch': 200,
        '/guide/image-compress': 200,
        '/guide/qr-code': 200,
        '/blog': 200,
        '/glossary': 200,
        '/healthz': 200,
    }
    private_ocr_paths = (
        '/tools/ocr',
        '/guide/ocr',
        '/api/ocr',
        '/_internal/ocr-spike',
    )
    private_background_removal_paths = (
        '/tools/background-removal',
        '/guide/background-removal',
        '/api/background-removal',
        '/_internal/background-removal-spike',
    )
    failed = []
    for path, expected_status in expected.items():
        for i in range(10):
            response = client.get(path, follow_redirects=False)
            body = response.data.decode('utf-8', errors='replace')
            if response.status_code != expected_status:
                failed.append(f"path={path} run={i+1} expected={expected_status} status={response.status_code}")
            elif path != '/healthz' and _looks_like_error_page(body):
                failed.append(f"path={path} run={i+1} body contains error page")
    for path in private_ocr_paths:
        response = client.get(path, follow_redirects=False)
        if response.status_code != 404:
            failed.append(f"path={path} expected=404 status={response.status_code}")
    for path in private_background_removal_paths:
        response = client.get(path, follow_redirects=False)
        if response.status_code != 404:
            failed.append(f"path={path} expected=404 status={response.status_code}")
    cleanup_body = client.get('/tools/image-cleanup', follow_redirects=False).data.decode('utf-8', errors='replace')
    if 'id="background-removal"' in cleanup_body or 'js/image-background-removal.js' in cleanup_body:
        failed.append('path=/tools/image-cleanup exposes unsupported AI background removal')
    _check_a8_catalog_rendering(client, failed)
    if failed:
        for item in failed:
            print(f"FAIL: {item}")
        print(f"Total failures: {len(failed)}")
        return 1
    business = client.get('/business', follow_redirects=False)
    business_body = business.data.decode('utf-8', errors='replace')
    business_checks = {
        'title': '企業向け業務効率化支援' in business_body,
        'h1': '企業の定型業務を' in business_body and '小さなツールから効率化' in business_body,
        'canonical': 'https://oshigoto.onrender.com/business' in business_body,
        'contact_cta': 'href="/contact"' in business_body,
        'tools_cta': 'href="/tools"' in business_body,
        'no_a8': 'rot3.a8.net' not in business_body,
        'no_amazon': 'amazon.co.jp' not in business_body,
    }
    failed_business = [name for name, ok in business_checks.items() if not ok]
    if failed_business:
        print('FAIL: /business checks: ' + ', '.join(failed_business))
        return 1
    pdf_body = client.get('/tools/pdf', follow_redirects=False).data.decode('utf-8', errors='replace')
    browser_size = re.search(r'const BROWSER_PDF_MAX_FILE_SIZE_MB = (\d+);', pdf_body)
    browser_pages = re.search(r'const BROWSER_PDF_MAX_PAGES = (\d+);', pdf_body)
    lock_size = re.search(r'const PDF_LOCK_MAX_FILE_SIZE_MB = (\d+);', pdf_body)
    lock_pages = re.search(r'const PDF_LOCK_MAX_PAGES = (\d+);', pdf_body)
    browser_limit_copy = browser_size and browser_pages and f'ブラウザ内PDF処理: 1ファイル最大{browser_size.group(1)}MB・最大{browser_pages.group(1)}ページ' in pdf_body
    server_limit_copy = lock_size and lock_pages and f'パスワード設定: 1ファイル最大{lock_size.group(1)}MB・最大{lock_pages.group(1)}ページ' in pdf_body
    pdf_checks = {
        'page_delete_mode': 'data-mode="page-delete"' in pdf_body and 'id="delete-range"' in pdf_body,
        'page_rotate_mode': 'data-mode="page-rotate"' in pdf_body and 'id="rotate-angle"' in pdf_body,
        'browser_limits': bool(browser_limit_copy),
        'server_limits': bool(server_limit_copy),
        'unlock_api_absent': '/api/pdf/unlock' not in pdf_body,
    }
    failed_pdf = [name for name, ok in pdf_checks.items() if not ok]
    if failed_pdf:
        print('FAIL: /tools/pdf checks: ' + ', '.join(failed_pdf))
        return 1
    image_body = client.get('/tools/image-compress', follow_redirects=False).data.decode('utf-8', errors='replace')
    image_checks = {
        'h1': '<h1>画像を軽くする</h1>' in image_body,
        'browser_only': 'Oshigotoのサーバーへ送信されません' in image_body,
        'formats': all(marker in image_body for marker in ('image/jpeg', 'image/png', 'image/webp')),
        'core_script': 'js/image-compress-core.js' in image_body and 'js/image-compress.js' in image_body,
        'canonical': 'https://oshigoto.onrender.com/tools/image-compress' in image_body,
    }
    failed_image = [name for name, ok in image_checks.items() if not ok]
    if failed_image:
        print('FAIL: /tools/image-compress checks: ' + ', '.join(failed_image))
        return 1
    batch_body = client.get('/tools/image-batch').data.decode('utf-8', errors='replace')
    batch_checks = {
        'format_core': 'js/image-format-core.js' in batch_body,
        'guaranteed_formats': all(marker in batch_body for marker in ('JPEG', 'PNG', 'WebP')),
        'conditional_formats': all(marker in batch_body for marker in ('静止GIF', 'BMP', 'AVIF', 'ブラウザ')),
        'runtime_avif': 'id="output-avif-option" disabled hidden' in batch_body and 'detectAvifEncodeSupport' in batch_body,
        'limits': all(marker in batch_body for marker in ('data-max-pixels="40000000"', 'data-max-long-edge="16384"')),
        'safe_dom': 'innerHTML' not in batch_body,
    }
    failed_batch = [name for name, ok in batch_checks.items() if not ok]
    if failed_batch:
        print('FAIL: /tools/image-batch checks: ' + ', '.join(failed_batch))
        return 1
    qr_body = client.get('/tools/qr-code').data.decode('utf-8', errors='replace')
    qr_guide_body = client.get('/guide/qr-code').data.decode('utf-8', errors='replace')
    qr_checks = {
        'h1': '<h1>QRコードを作る</h1>' in qr_body,
        'five_types': all(f'value="{value}"' in qr_body for value in ('url', 'text', 'email', 'phone', 'wifi')),
        'local_vendor': 'vendor/qrcode/1.5.4/qrcode.min.js' in qr_body and 'cdn.' not in qr_body,
        'scripts': 'js/qr-code-core.js' in qr_body and 'js/qr-code.js' in qr_body,
        'browser_only': 'Oshigotoのサーバーへ送信されません' in qr_body,
        'wifi_warning': 'Wi-Fi用QRコードには接続パスワードが含まれます' in qr_body,
        'byte_limit': '1,000 bytes' in qr_body,
        'outputs': 'PNGで保存' in qr_body and 'SVGで保存' in qr_body,
        'guide': '基本の手順' in qr_guide_body and '読み取りやすくするために' in qr_guide_body,
        'guide_faq': qr_guide_body.count('<details>') == 7 and '"@type": "FAQPage"' in qr_guide_body,
        'canonical': 'https://oshigoto.onrender.com/tools/qr-code' in qr_body,
    }
    failed_qr = [name for name, ok in qr_checks.items() if not ok]
    if failed_qr:
        print('FAIL: /tools/qr-code checks: ' + ', '.join(failed_qr))
        return 1
    for path in ('/business/',):
        response = client.get(path, follow_redirects=False)
        if response.status_code != 301 or not (response.headers.get('Location') or '').endswith('/business'):
            print(f'FAIL: {path} expected 301 to /business got {response.status_code} {response.headers.get("Location")}')
            return 1
    print(f"OK: {len(expected)} paths x 10 requests = expected statuses, no error page")
    return 0


def run_deploy_verification():
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()
    failed = []
    for path in ['/', '/business', '/tools', '/tools/seo', '/tools/csv', '/tools/pdf', '/tools/image-batch', '/tools/image-compress', '/tools/qr-code', '/tools/image-cleanup', '/guide/csv', '/guide/image-batch', '/guide/image-compress', '/guide/qr-code']:
        resp = client.get(path, follow_redirects=False)
        body = resp.data.decode('utf-8', errors='replace')
        if resp.status_code != 200:
            failed.append(f"path={path} expected 200 got {resp.status_code}")
        elif _looks_like_error_page(body):
            failed.append(f"path={path} body contains error page")
    resp = client.get('/autofill', follow_redirects=False)
    loc = (resp.headers.get('Location') or '').strip()
    if resp.status_code != 301 or not loc.endswith('/tools'):
        failed.append(f"path=/autofill expected 301 to /tools got {resp.status_code} {loc}")
    resp = client.get('/api/pdf/unlock', follow_redirects=False)
    if resp.status_code != 404:
        failed.append(f"path=/api/pdf/unlock expected 404 got {resp.status_code}")
    resp = client.get('/tools/pdf/', follow_redirects=False)
    loc = (resp.headers.get('Location') or '').strip()
    if resp.status_code != 301 or '/tools/pdf' not in loc:
        failed.append(f"path=/tools/pdf/ expected 301 to /tools/pdf got {resp.status_code} {loc}")
    pdf_body = client.get('/tools/pdf').data.decode('utf-8', errors='replace')
    for marker in ('data-mode="page-delete"', 'data-mode="page-rotate"', 'PdfOps.deletePages', 'PdfOps.rotatePages'):
        if marker not in pdf_body:
            failed.append(f'path=/tools/pdf missing marker {marker}')
    image_body = client.get('/tools/image-compress').data.decode('utf-8', errors='replace')
    for marker in ('<h1>画像を軽くする</h1>', 'data-max-files="20"', 'js/image-compress.js', 'Oshigotoのサーバーへ送信されません'):
        if marker not in image_body:
            failed.append(f'path=/tools/image-compress missing marker {marker}')
    batch_body = client.get('/tools/image-batch').data.decode('utf-8', errors='replace')
    for marker in ('js/image-format-core.js', 'id="output-avif-option" disabled hidden', 'data-max-pixels="40000000"', '静止GIF'):
        if marker not in batch_body:
            failed.append(f'path=/tools/image-batch missing marker {marker}')
    qr_body = client.get('/tools/qr-code').data.decode('utf-8', errors='replace')
    for marker in ('<h1>QRコードを作る</h1>', 'value="wifi"', '1,000 bytes', 'vendor/qrcode/1.5.4/qrcode.min.js', 'js/qr-code-core.js', 'PNGで保存', 'SVGで保存'):
        if marker not in qr_body:
            failed.append(f'path=/tools/qr-code missing marker {marker}')
    for path in (
        '/tools/ocr', '/guide/ocr', '/api/ocr', '/_internal/ocr-spike',
        '/tools/background-removal', '/guide/background-removal',
        '/api/background-removal', '/_internal/background-removal-spike',
    ):
        resp = client.get(path, follow_redirects=False)
        if resp.status_code != 404:
            failed.append(f'path={path} expected 404 got {resp.status_code}')
    cleanup_body = client.get('/tools/image-cleanup').data.decode('utf-8', errors='replace')
    if 'id="background-removal"' in cleanup_body or 'js/image-background-removal.js' in cleanup_body:
        failed.append('path=/tools/image-cleanup exposes unsupported AI background removal')
    _check_a8_catalog_rendering(client, failed)
    if failed:
        for item in failed:
            print(f"FAIL: {item}")
        print(f"Total: {len(failed)}")
        return 1
    print("OK: deploy verification public routes, /autofill 301, /api/pdf/unlock 404")
    return 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', action='store_true')
    args = parser.parse_args()
    sys.exit(run_deploy_verification() if args.deploy else run_with_test_client())
