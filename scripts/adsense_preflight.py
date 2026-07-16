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
MAJOR_PATHS = ['/', '/tools', '/privacy', '/terms', '/contact', '/about', '/faq', '/guide', '/blog', '/glossary', '/best-practices']
TOOL_PATHS = ['/tools/pdf', '/tools/csv', '/tools/image-batch', '/tools/image-cleanup', '/tools/seo']
GUIDE_PATHS = ['/guide/pdf', '/guide/csv', '/guide/image-batch', '/guide/image-cleanup', '/guide/seo']
INDEXABLE_PATHS = ['/', '/tools', '/guide', '/blog', '/glossary'] + TOOL_PATHS + GUIDE_PATHS
PUBLIC_AFFILIATE_PATHS = ['/', '/tools'] + TOOL_PATHS
ADSENSE_SCRIPT_SRC = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4232725615106709'
ADSENSE_HEAD_PATHS = ['/', '/tools', '/tools/pdf']
A8_SCRIPT_SRC = 'https://rot3.a8.net/jsa/fdf80b714de10cbdd802fd2333444e15/c6f057b86584942e415435ffb1fa93d4.js'
A8_PUBLIC_PATHS = MAJOR_PATHS + TOOL_PATHS + GUIDE_PATHS
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
        # PDF password protection is allowed; only unlock/decrypt surfaces are forbidden.
        if path == '/tools/pdf':
            leaks = [s for s in leaks if s not in ('unlock', 'decrypt')]
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
