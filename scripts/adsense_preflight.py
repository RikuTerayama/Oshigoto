#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AdSense 再申請前ゲート: 不承認要因ゼロを自動チェック。
- テストクライアント使用（サーバ不要）: デフォルト
- 本番確認: --live https://jobcan-automation.onrender.com

NG があれば exit 1 で終了。
使用例:
  python scripts/adsense_preflight.py
  python scripts/adsense_preflight.py --live https://jobcan-automation.onrender.com
"""
import os
import sys
import argparse
import json
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL_DEFAULT = 'https://oshigoto.onrender.com'
MAJOR_PATHS = ['/', '/tools', '/privacy', '/contact', '/about', '/faq']
INDEXABLE_PATHS = ['/', '/blog', '/glossary', '/guide', '/tools/image-batch', '/tools/pdf', '/tools/seo', '/tools/csv', '/tools/image-cleanup']

# 主要ページ（GSC 404 解消対象含む）
MAJOR_PATHS = ['/', '/tools', '/privacy', '/contact', '/about', '/faq']
PUBLIC_AFFILIATE_PATHS = ['/', '/tools', '/privacy', '/terms', '/contact', '/about', '/faq', '/guide', '/blog']
NON_UI_AFFILIATE_PATHS = ['/sitemap.xml', '/robots.txt', '/ads.txt', '/api/seo/crawl-urls']
TWO_AMAZON_SECTION_PATHS = ['/', '/tools', '/guide']
HEADER_PATHS = ['/', '/tools', '/guide', '/blog']
A8_ROTATION_SRC_FRAGMENT = 'rot3.a8.net/jsa/fdf80b714de10cbdd802fd2333444e15/c6f057b86584942e415435ffb1fa93d4.js'
RAKUTEN_SMALL_CARD_IMAGE_FRAGMENT = '0eb4bbcf.7ab43877.0eb4bbaa.95151395'
AMAZON_FORBIDDEN_QUERY_FRAGMENTS = ['jobcan autofill |', 'jobcan autofill']
AMAZON_MAX_QUERY_LENGTH = 48
AMAZON_EXPECTED_ASSOCIATE_TAG = (os.getenv('AMAZON_ASSOCIATE_TAG') or '').strip()
AMAZON_DEPRECATED_ASSOCIATE_TAGS = {
    tag.strip()
    for tag in (os.getenv('AMAZON_DEPRECATED_ASSOCIATE_TAGS', '') or '').split(',')
    if tag.strip()
}

# sitemap.xml に含まれるべき重要URL（完全一致：末尾スラッシュなし）
SITEMAP_REQUIRED_URLS = ['/', '/tools', '/blog', '/glossary', '/guide', '/tools/pdf', '/tools/csv', '/tools/image-batch', '/tools/image-cleanup', '/tools/seo']

# インデックス対象ページ（noindex なし・canonical 自己参照の確認用）
INDEXABLE_PATHS = ['/', '/blog', '/glossary', '/guide', '/guide/csv', '/guide/pdf', '/guide/image-batch', '/guide/image-cleanup', '/guide/seo', '/tools/image-batch', '/tools/pdf', '/tools/seo', '/tools/csv', '/tools/image-cleanup']
NOINDEX_SELF_CANONICAL_PATHS = ['/privacy', '/terms', '/contact']
INDEXABILITY_TARGET_PATHS = [
    '/', '/blog', '/faq', '/guide', '/guide/csv', '/guide/image-batch',
    '/guide/image-cleanup', '/guide/pdf', '/guide/seo', '/glossary',
    '/tools', '/tools/csv', '/tools/image-batch', '/tools/image-cleanup',
    '/tools/pdf', '/tools/seo',
]
ARTICLE_SCHEMA_REQUIRED_PATHS = [
    '/guide/csv', '/guide/image-batch', '/guide/image-cleanup', '/guide/pdf',
    '/guide/seo',
]
HUB_LINK_REQUIREMENTS = {
    '/': [
        '/guide',
        '/tools',
        '/blog',
        '/faq',
        ],
    '/blog': [
        '/tools',
        '/guide',
        '/tools/pdf',
        '/tools/image-batch',
    ],
    '/guide': [
        '/guide/pdf',
        '/guide/csv',
        '/guide/image-batch',
        '/guide/image-cleanup',
        '/guide/seo',
        ],
    '/tools': [
        '/tools/csv',
        '/tools/image-batch',
        '/tools/image-cleanup',
        '/tools/pdf',
        '/tools/seo',
    ],
}
RELATED_CONTENT_REQUIRED_PATHS = ['/glossary']
INTENTIONALLY_EXCLUDED_PATHS = ['/privacy', '/terms', '/contact', '/sitemap.html']

# 不整合文字列（ヒット0が必須）
DISALLOWED_STRINGS = [
    'github.com/your-repo',
    'example.com',
    'ローカル処理優先',
    'ファイルやテキストはアップロードせず、ブラウザ内で処理します。サーバーには保存されません。',
    '検索条件に一致するツールが見つかりませんでした。',
]

# /tools サーバ返却HTMLに含まれてはいけない文言（本文・script 含む）
NO_RESULTS_FORBIDDEN = '検索条件に一致するツールが見つかりませんでした。'
VISIBLE_TEXT_INTEGRITY_PATHS = [
    '/', '/faq', '/guide',
    '/guide/csv', '/guide/image-batch', '/guide/image-cleanup', '/guide/pdf',
    '/guide/seo', '/blog', '/glossary',     '/privacy', '/terms', '/contact',
]
VISIBLE_TEXT_FORBIDDEN = ['</h1>', '</h2>', '</h3>', '</p>', '</li>', '</a>', '/h1>', '/h2>', '/h3>', '/p>', '/li>', '/a>', '/strong>', '�']
FOOTER_INTEGRITY_PATHS = ['/', '/privacy', '/terms', '/contact', '/blog']
FOOTER_REQUIRED_TEXT = [
    'プライバシーポリシー',
    '利用規約',
    'お問い合わせ',
    'ご利用にあたって',
]
TOP_INLINE_REQUIREMENTS = {
    '/autofill': {
        'slot': 'public_top_inline',
        'selector': '.content > [data-affiliate-slot="public_top_inline"]',
    },
    '/tools': {
        'slot': 'public_top_inline',
        'selector': '.page-header + [data-affiliate-slot="public_top_inline"]',
    },
    '/tools/image-batch': {
        'slot': 'public_top_inline',
        'selector': '.tool-intro + [data-affiliate-slot="public_top_inline"]',
    },
    '/tools/pdf': {
        'slot': 'public_top_inline',
        'selector': '.tool-intro + [data-affiliate-slot="public_top_inline"]',
    },
    '/tools/seo': {
        'slot': 'public_top_inline',
        'selector': '.tool-intro + [data-affiliate-slot="public_top_inline"]',
    },
    '/guide': {
        'slot': 'public_top_inline',
        'selector': '.affiliate-top-shell [data-affiliate-slot="public_top_inline"]',
    },
    '/faq': {
        'slot': 'public_top_inline',
        'selector': '.affiliate-top-shell [data-affiliate-slot="public_top_inline"]',
    },
    '/blog': {
        'slot': 'blog_index_after_intro',
        'selector': '.blog-index-hero + [data-affiliate-slot="blog_index_after_intro"]',
    },

}
NO_HEADER_TOP_SLOT_PATHS = ['/tools', '/tools/image-batch', '/tools/pdf', '/tools/seo']
HOME_GRID_EXPECTED_COUNT = 5
HOME_USE_CASE_MIN_COUNT = 4
GUIDE_CORE_CARD_COUNT = 5
GUIDE_HUB_CARD_COUNT = 0
HOME_HEADLINE_LINES = ['勤怠入力の自動化と、', '周辺業務の効率化を', '一つの導線で。']
HOME_LEAD_LINES = [
    'Jobcan の勤怠入力を楽にしたい人向けに、',
    'AutoFill、本番前の確認ガイド、画像・PDF・SEO の周辺ツール、',
    'FAQ、導入事例をまとめています。'
]
PUBLIC_UI_FORBIDDEN_COPY = [
    'トップページからそのまま比較、導入判断、運用設計に進めるための導線です。',
    '3 枚で中途半端に見えやすかった用途説明を、4 つの文脈に整理して視線誘導しやすくしました。',
    '本サイトのツールは、業務フローの見直しやブラウザ内処理を前提に、作業の手戻りを減らすための情報と機能をまとめています。',
    'Developed by RT',
    'Version:',
]
REMOVED_AFFILIATE_TEXT = ['Sponsored Picks', 'おすすめ情報', '本文の流れを崩さずに見られる、落ち着いたおすすめ導線です。']

PUBLIC_TEMPLATE_SOURCE_PATHS = [
    'templates/index.html',
    'templates/landing.html',
    'templates/landing_v2.html',
    'templates/includes/footer.html',
    'templates/includes/seo_link_hub.html',
    'templates/includes/related_content.html',
    'templates/tools/index.html',
]

TOP_INLINE_REQUIREMENTS.pop('/autofill', None)
TOP_INLINE_REQUIREMENTS.pop('/case-studies', None)
MAJOR_PATHS = ['/', '/tools', '/privacy', '/contact', '/about', '/faq']
HOME_HEADLINE_LINES = ['しごとの小さな面倒を、', 'さっと片づける。']
HOME_LEAD_LINES = [
    'PDF、CSV、画像、ページ確認など、',
    '仕事でたまに必要になる作業をまとめた軽量ツール集です。',
]
HOME_HUB_GRID_EXPECTED_COUNT = 6

# Googlebot UA
GOOGLEBOT_UA = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'

# 本文テキストの最小長（Googlebot 取得想定）
MIN_BODY_CHARS = 1000


def run_local():
    """Flask test client でチェック"""
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()

    def get_fn(path, headers=None):
        if headers:
            return client.get(path, headers=headers)
        return client.get(path)

    return _run_checks(get_fn, 'http://test', use_headers=True)


def _run_checks(get_fn, base_url, use_headers=True):
    """共通チェックロジック。get_fn(path, headers?) -> (status, body, headers_dict)"""
    from bs4 import BeautifulSoup
    rows = []
    all_ok = True

    def get(path, headers=None):
        if use_headers and headers:
            return get_fn(path, headers=headers)
        return get_fn(path)

    def canonical_for_path(path):
        base = BASE_URL_DEFAULT.rstrip('/')
        return base + ('/' if path == '/' else path)

    # 1) 主要ページ 200
    for path in MAJOR_PATHS:
        try:
            resp = get(path)
            status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            ok = status == 200
            rows.append(('1_page_200', path, 'OK' if ok else f'FAIL status={status}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('1_page_200', path, f'ERROR {e}', False))
            all_ok = False

    # 1b) /best-practices と /best-practices/ が 404 でないこと（200 または 301）
    for path in ('/best-practices', '/best-practices/'):
        try:
            resp = get(path)
            status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
            ok = status in (200, 301)
            rows.append(('1b_best_practices', path, f'OK {status}' if ok else f'FAIL {status} (404)', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('1b_best_practices', path, f'ERROR {e}', False))
            all_ok = False

    # 2) Googlebot UA で 200 かつ本文長
    try:
        h = {'User-Agent': GOOGLEBOT_UA} if use_headers else None
        resp = get('/', h) if h else get('/')
        status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        ok = status == 200 and len(body) >= MIN_BODY_CHARS
        rows.append(('2_googlebot', '/', f'OK status={status} len={len(body)}' if ok else f'FAIL status={status} len={len(body)}', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('2_googlebot', '/', f'ERROR {e}', False))
        all_ok = False

    # 3a) /tools サーバ返却HTMLに no-results 日本語文言が含まれないこと（必須）
    try:
        resp = get('/tools')
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        found = NO_RESULTS_FORBIDDEN in body
        rows.append(('3a_tools_no_results', '/tools', 'OK HTML has no no-results text' if not found else 'FAIL no-results text in server HTML', not found))
        if found:
            all_ok = False
    except Exception as e:
        rows.append(('3a_tools_no_results', '/tools', f'ERROR {e}', False))
        all_ok = False

    # 3b) 不整合文字列 0 件（/tools, /, /privacy）
    disallow_found = []
    for path in ['/tools', '/', '/privacy']:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            for s in DISALLOWED_STRINGS:
                if s in body:
                    disallow_found.append((path, s[:40]))
        except Exception as e:
            disallow_found.append((path, str(e)))
    if disallow_found:
        for path, msg in disallow_found[:5]:
            rows.append(('3b_disallowed', path, f'FAIL found: {msg}...', False))
        all_ok = False
    else:
        rows.append(('3b_disallowed', '/, /tools, /privacy', 'OK 0 disallowed strings', True))

    # 4) Cache-Control
    try:
        resp = get('/tools')
        headers = resp.headers if hasattr(resp, 'headers') else {}
        cc = headers.get('Cache-Control') or headers.get('cache-control', '')
        ok = 'no-store' in cc.lower() or 'max-age=0' in cc
        rows.append(('4_cache_control', '/tools', f'OK {cc}' if ok else f'FAIL missing no-store {cc}', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('4_cache_control', '/tools', f'ERROR {e}', False))
        all_ok = False

    # 5) ads.txt は 200 必須。Google AdSense publisher 行（pub-）を含むこと
    try:
        resp = get('/ads.txt')
        status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        has_pub = 'pub-' in body or 'google.com' in body
        ok = status == 200 and has_pub
        rows.append(('5_ads_txt', '/ads.txt', f'OK 200 pub_id' if ok else f'FAIL status={status} (200 required) pub={has_pub}', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('5_ads_txt', '/ads.txt', f'FAIL ERROR {e}', False))
        all_ok = False

    # 6) robots.txt は 200 必須。主要ページをブロックしていないこと
    try:
        resp = get('/robots.txt')
        status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        blocks_main = 'Disallow: /' in body and 'Allow: /' not in body.split('Disallow: /')[0]
        ok = status == 200 and not blocks_main
        rows.append(('6_robots_txt', '/robots.txt', f'OK 200 allow /' if ok else f'FAIL status={status} (200 required)', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('6_robots_txt', '/robots.txt', f'FAIL ERROR {e}', False))
        all_ok = False

    # 7) sitemap.xml に重要URLが含まれること（完全一致）+ lastmod ユニーク数
    import re
    try:
        resp = get('/sitemap.xml')
        status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        if status != 200:
            rows.append(('7_sitemap', '/sitemap.xml', f'FAIL status={status}', False))
            all_ok = False
        else:
            base = BASE_URL_DEFAULT.rstrip('/')
            missing = []
            for u in SITEMAP_REQUIRED_URLS:
                loc_url = base + (u if u != '/' else '/')
                if f'<loc>{loc_url}</loc>' not in body:
                    missing.append(u)
            if missing:
                rows.append(('7_sitemap', '/sitemap.xml', f'FAIL missing in sitemap: {missing[:3]}', False))
                all_ok = False
            else:
                rows.append(('7_sitemap', '/sitemap.xml', 'OK required URLs in sitemap', True))
            lastmods = re.findall(r'<lastmod>([^<]+)</lastmod>', body)
            lastmods_unique = len(set(lastmods)) if lastmods else 0
            ok_lastmod = lastmods_unique >= 1
            rows.append(('7b_sitemap_lastmod', '/sitemap.xml', f'OK lastmod unique={lastmods_unique}' if ok_lastmod else f'FAIL lastmod unique={lastmods_unique} (need >=1)', ok_lastmod))
            if not ok_lastmod:
                all_ok = False
    except Exception as e:
        rows.append(('7_sitemap', '/sitemap.xml', f'FAIL ERROR {e}', False))
        all_ok = False

    # 8) robots.txt が複数行形式で Sitemap が改行付きで含まれること
    try:
        resp = get('/robots.txt')
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        has_newlines = '\n' in body
        # Sitemap 行が独立した行で存在（\nSitemap: または Sitemap:\n）
        has_sitemap_line = '\nSitemap:' in body or body.strip().startswith('Sitemap:') or 'Sitemap:' in body
        ok = has_newlines and has_sitemap_line
        rows.append(('8_robots_format', '/robots.txt', f'OK multiline+Sitemap' if ok else f'FAIL multiline={has_newlines} Sitemap={has_sitemap_line}', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('8_robots_format', '/robots.txt', f'FAIL ERROR {e}', False))
        all_ok = False

    # 9) インデックス対象ページに noindex が無く canonical が自己参照であること
    for path in INDEXABLE_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            has_noindex = 'noindex, nofollow' in body or ('name="robots"' in body and 'noindex' in body)
            # canonical 自己参照: BASE_URL + path が含まれる（path が / のときは base/ または base/）
            base = BASE_URL_DEFAULT.rstrip('/')
            expected_canonical_url = base + (path if path != '/' else '') or '/'
            if path == '/':
                expected_canonical_url = base + '/'
            has_canonical_self = expected_canonical_url in body and 'rel="canonical"' in body
            ok = not has_noindex and has_canonical_self
            rows.append(('9_indexable', path, 'OK no noindex, canonical self' if ok else f'FAIL noindex={has_noindex} canonical={has_canonical_self}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9_indexable', path, f'ERROR {e}', False))
            all_ok = False

    for path in VISIBLE_TEXT_INTEGRITY_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            visible_text = soup.get_text('\n', strip=True)
            found = [token for token in VISIBLE_TEXT_FORBIDDEN if token in visible_text]
            ok = not found
            rows.append(('9a_visible_text', path, 'OK no broken tags/text' if ok else f'FAIL found {found[:3]}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9a_visible_text', path, f'ERROR {e}', False))
            all_ok = False

    for path in FOOTER_INTEGRITY_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            footer = soup.find('footer')
            footer_text = footer.get_text('\n', strip=True) if footer else ''
            found = [token for token in VISIBLE_TEXT_FORBIDDEN if token in footer_text]
            missing_required = [token for token in FOOTER_REQUIRED_TEXT if token not in footer_text]
            forbidden_footer_copy = [token for token in PUBLIC_UI_FORBIDDEN_COPY if token in footer_text]
            ok = bool(footer) and not found and not missing_required and not forbidden_footer_copy
            rows.append(
                (
                    '9b_footer_text',
                    path,
                    'OK footer text intact'
                    if ok else
                    f'FAIL found={found[:3]} missing={missing_required[:3]} forbidden={forbidden_footer_copy[:2]}',
                    ok,
                )
            )
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9b_footer_text', path, f'ERROR {e}', False))
            all_ok = False

    for path in HEADER_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            header = soup.select_one('.site-header .site-nav__inner')
            logo = soup.select_one('.site-header .site-logo')
            link_count = len(soup.select('.site-header .site-nav__links > .site-nav__link, .site-header .site-nav__dropdown-wrap'))
            ok = bool(header) and bool(logo) and link_count >= 4
            rows.append(('9ba_header', path, f'OK links={link_count}' if ok else f'FAIL header={bool(header)} logo={bool(logo)} links={link_count}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9ba_header', path, f'ERROR {e}', False))
            all_ok = False

    try:
        resp = get('/')
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        soup = BeautifulSoup(body, 'html.parser')
        page_cards = len(soup.select('.landing-tool-grid .landing-tool-card'))
        hub_cards = len(soup.select('.seo-link-hub__grid .seo-link-hub__card'))
        use_cards = len(soup.select('.landing-use-grid .landing-use-card'))
        page_grid_ok = bool(soup.select_one('.landing-tool-grid')) and page_cards == HOME_GRID_EXPECTED_COUNT
        hub_grid_ok = bool(soup.select_one('.seo-link-hub__grid.seo-link-hub__grid--three')) and hub_cards == HOME_HUB_GRID_EXPECTED_COUNT
        use_grid_ok = bool(soup.select_one('.landing-use-grid')) and use_cards >= HOME_USE_CASE_MIN_COUNT
        rows.append(('9bb_home_grid', '/', f'OK cards={page_cards}' if page_grid_ok else f'FAIL cards={page_cards}', page_grid_ok))
        rows.append(('9bbb_home_hub_grid', '/', f'OK cards={hub_cards}' if hub_grid_ok else f'FAIL cards={hub_cards}', hub_grid_ok))
        rows.append(('9bc_home_use_cases', '/', f'OK cards={use_cards}' if use_grid_ok else f'FAIL cards={use_cards}', use_grid_ok))
        if not page_grid_ok or not hub_grid_ok or not use_grid_ok:
            all_ok = False
    except Exception as e:
        rows.append(('9bb_home_grid', '/', f'ERROR {e}', False))
        rows.append(('9bbb_home_hub_grid', '/', f'ERROR {e}', False))
        rows.append(('9bc_home_use_cases', '/', f'ERROR {e}', False))
        all_ok = False

    try:
        resp = get('/guide')
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        soup = BeautifulSoup(body, 'html.parser')
        primary_cards = len(soup.select('.page .grid .card'))
        hub_cards = len(soup.select('.seo-link-hub__grid .seo-link-hub__card'))
        primary_ok = primary_cards >= GUIDE_CORE_CARD_COUNT
        hub_ok = hub_cards >= GUIDE_HUB_CARD_COUNT
        rows.append(('9bd_guide_primary_grid', '/guide', f'OK cards={primary_cards}' if primary_ok else f'FAIL cards={primary_cards}', primary_ok))
        rows.append(('9be_guide_hub_grid', '/guide', f'OK cards={hub_cards}' if hub_ok else f'FAIL cards={hub_cards}', hub_ok))
        if not primary_ok or not hub_ok:
            all_ok = False
    except Exception as e:
        rows.append(('9bd_guide_primary_grid', '/guide', f'ERROR {e}', False))
        rows.append(('9be_guide_hub_grid', '/guide', f'ERROR {e}', False))
        all_ok = False

    for path in PUBLIC_AFFILIATE_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            headers = resp.headers if hasattr(resp, 'headers') else {}
            content_type = (headers.get('Content-Type') or headers.get('content-type') or '').lower()
            soup = BeautifulSoup(body, 'html.parser')
            meta_utf8 = bool(soup.select_one('meta[charset="utf-8"]'))
            stack_count = len(soup.select('.affiliate-stack'))
            disclosure_count = len(soup.select('.affiliate-disclosure'))
            removed_text_found = [text for text in REMOVED_AFFILIATE_TEXT if text in body]
            slot_count = len(soup.select('[data-affiliate-slot]'))
            row_nodes = soup.select('.affiliate-stack .affiliate-stack__row[data-affiliate-network]')
            normalized_rows = [node.get('data-affiliate-network') for node in row_nodes if node.get('data-affiliate-network')]
            has_rakuten = 'rakuten' in normalized_rows
            has_a8 = 'a8' in normalized_rows
            has_amazon = 'amazon' in normalized_rows
            has_rotation_script = A8_ROTATION_SRC_FRAGMENT in body
            has_small_rakuten_card_image = RAKUTEN_SMALL_CARD_IMAGE_FRAGMENT in body
            amazon_card_count = len(soup.select('.amazon-recommendation-grid .amazon-recommendation-card'))
            amazon_hrefs = [
                a.get('href', '')
                for a in soup.select('.amazon-recommendation-grid .amazon-recommendation-card__anchor')
            ]
            amazon_queries = []
            amazon_tags = []
            for href in amazon_hrefs:
                parsed = urlparse(href or '')
                if 'amazon.' not in (parsed.netloc or ''):
                    continue
                query_value = parse_qs(parsed.query).get('k', [''])[0].strip()
                tag_value = parse_qs(parsed.query).get('tag', [''])[0].strip()
                if query_value:
                    amazon_queries.append(query_value)
                if tag_value:
                    amazon_tags.append(tag_value)
            invalid_amazon_queries = [
                query
                for query in amazon_queries
                if (
                    '|' in query
                    or '｜' in query
                    or len(query) > AMAZON_MAX_QUERY_LENGTH
                    or any(fragment in query.lower() for fragment in AMAZON_FORBIDDEN_QUERY_FRAGMENTS)
                )
            ]
            invalid_amazon_tags = []
            for tag in amazon_tags:
                if AMAZON_EXPECTED_ASSOCIATE_TAG and tag != AMAZON_EXPECTED_ASSOCIATE_TAG:
                    invalid_amazon_tags.append(tag)
                    continue
                if tag in AMAZON_DEPRECATED_ASSOCIATE_TAGS:
                    invalid_amazon_tags.append(tag)
            rakuten_card_count = len(soup.select('.affiliate-stack [data-affiliate-network="rakuten"] .affiliate-link-card'))
            amazon_indices = [idx for idx, network in enumerate(normalized_rows) if network == 'amazon']
            rakuten_indices = [idx for idx, network in enumerate(normalized_rows) if network == 'rakuten']
            a8_indices = [idx for idx, network in enumerate(normalized_rows) if network == 'a8']
            has_upper_amazon = bool(soup.select_one('[data-affiliate-tier="upper-amazon"] .affiliate-stack__row--amazon'))
            has_mid_amazon = bool(soup.select_one('[data-affiliate-tier="mid-amazon"] .affiliate-stack__row--amazon'))
            has_mid_rakuten = bool(soup.select_one('[data-affiliate-tier="mid-rakuten"] .affiliate-stack__row--rakuten'))
            has_lower_a8 = bool(soup.select_one('[data-affiliate-tier="lower-a8"] .affiliate-stack__row--a8'))
            amazon_before_rakuten = bool(amazon_indices and rakuten_indices and amazon_indices[0] < rakuten_indices[0]) if has_amazon and has_rakuten else (not has_amazon)
            rakuten_before_a8 = bool(rakuten_indices and a8_indices and rakuten_indices[0] < a8_indices[0]) if has_rakuten and has_a8 else False
            two_amazon_ok = True
            if path in TWO_AMAZON_SECTION_PATHS and has_amazon:
                two_amazon_ok = (
                    has_upper_amazon
                    and has_mid_amazon
                    and len(amazon_indices) >= 2
                    and amazon_indices[1] < (rakuten_indices[0] if rakuten_indices else 999)
                )
            has_removed_a8_text = any('A8.net のおすすめを見る' in link.get_text(' ', strip=True) for link in soup.select('a'))
            ok = (
                'text/html' in content_type
                and 'charset=utf-8' in content_type
                and meta_utf8
                and stack_count >= 2
                and disclosure_count <= 1
                and slot_count == 0
                and has_rakuten
                and has_a8
                and amazon_before_rakuten
                and rakuten_before_a8
                and two_amazon_ok
                and has_mid_rakuten
                and has_lower_a8
                and rakuten_card_count == 2
                and not has_small_rakuten_card_image
                and has_rotation_script
                and (not has_amazon or amazon_card_count >= 3)
                and (not has_amazon or len(invalid_amazon_queries) == 0)
                and (not has_amazon or len(invalid_amazon_tags) == 0)
                and not has_removed_a8_text
                and not removed_text_found
            )
            rows.append(
                (
                    '9c_affiliate_public',
                    path,
                    f'OK stack={stack_count} rows={normalized_rows} disclosures={disclosure_count} upper_amazon={has_upper_amazon} mid_amazon={has_mid_amazon} mid_rakuten={has_mid_rakuten} lower_a8={has_lower_a8}'
                    if ok else
                    f'FAIL ct={content_type or "missing"} meta={meta_utf8} stack={stack_count} rows={normalized_rows} disclosures={disclosure_count} slots={slot_count} upper_amazon={has_upper_amazon} mid_amazon={has_mid_amazon} mid_rakuten={has_mid_rakuten} lower_a8={has_lower_a8} two_amazon_ok={two_amazon_ok} amazon_cards={amazon_card_count} amazon_invalid_queries={invalid_amazon_queries[:2]} amazon_invalid_tags={invalid_amazon_tags[:2]} amazon_expected_tag={AMAZON_EXPECTED_ASSOCIATE_TAG or "unset"} rakuten_cards={rakuten_card_count} small_rakuten={has_small_rakuten_card_image} a8={has_rotation_script} removed_a8_text={has_removed_a8_text} removed={removed_text_found}',
                    ok,
                )
            )
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9c_affiliate_public', path, f'ERROR {e}', False))
            all_ok = False

    for path in NON_UI_AFFILIATE_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            slot_count = body.count('data-affiliate-slot=')
            has_stack = 'affiliate-stack' in body
            footer_block = 'affiliate-footer-block' in body
            side_rail = 'affiliate-side-rail' in body
            ok = slot_count == 0 and not footer_block and not side_rail and not has_stack
            rows.append(
                ('9d_affiliate_nonui', path,
                 f'OK slots={slot_count} footer={footer_block} rail={side_rail} stack={has_stack}' if ok else
                 f'FAIL slots={slot_count} footer={footer_block} rail={side_rail} stack={has_stack}',
                 ok)
            )
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9d_affiliate_nonui', path, f'ERROR {e}', False))
            all_ok = False

    for path in NOINDEX_SELF_CANONICAL_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            has_noindex = 'noindex, nofollow' in body or ('name="robots"' in body and 'noindex' in body)
            base = BASE_URL_DEFAULT.rstrip('/')
            expected_canonical_url = base + path
            has_canonical_self = expected_canonical_url in body and 'rel="canonical"' in body
            ok = has_noindex and has_canonical_self
            rows.append(('9e_noindex', path, 'OK noindex, canonical self' if ok else f'FAIL noindex={has_noindex} canonical={has_canonical_self}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('9e_noindex', path, f'ERROR {e}', False))
            all_ok = False

    try:
        resp = get('/')
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        soup = BeautifulSoup(body, 'html.parser')
        headline_lines = [node.get_text(strip=True) for node in soup.select('.landing-hero__headline-line')]
        ok = headline_lines == HOME_HEADLINE_LINES
        rows.append(('9fa_home_headline', '/', f'OK lines={headline_lines}' if ok else f'FAIL lines={headline_lines}', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('9fa_home_headline', '/', f'ERROR {e}', False))
        all_ok = False

    try:
        resp = get('/')
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        soup = BeautifulSoup(body, 'html.parser')
        lead_lines = [node.get_text(strip=True) for node in soup.select('.landing-hero__lead .copy-lines__line')]
        ok = lead_lines == HOME_LEAD_LINES
        rows.append(('9fb_home_lead', '/', f'OK lines={lead_lines}' if ok else f'FAIL lines={lead_lines}', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('9fb_home_lead', '/', f'ERROR {e}', False))
        all_ok = False

    try:
        for path in ['/', '/tools', '/guide', '/blog', '/faq', '/about']:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            found = [token for token in PUBLIC_UI_FORBIDDEN_COPY if token in body]
            ok = not found
            rows.append(('9fc_public_copy', path, 'OK no internal copy leakage' if ok else f'FAIL found={found[:2]}', ok))
            if not ok:
                all_ok = False
    except Exception as e:
        rows.append(('9fc_public_copy', '/', f'ERROR {e}', False))
        all_ok = False

    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source_hits = []
        for rel_path in PUBLIC_TEMPLATE_SOURCE_PATHS:
            abs_path = os.path.join(repo_root, *rel_path.split('/'))
            with open(abs_path, 'r', encoding='utf-8') as fh:
                source_text = fh.read()
            found = [token for token in PUBLIC_UI_FORBIDDEN_COPY if token in source_text]
            if found:
                source_hits.append((rel_path, found[:2]))
        ok = not source_hits
        rows.append(
            (
                '9fd_public_copy_source',
                'templates',
                'OK no forbidden public copy in source templates' if ok else f'FAIL found={source_hits[:3]}',
                ok,
            )
        )
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('9fd_public_copy_source', 'templates', f'ERROR {e}', False))
        all_ok = False

    try:
        common_css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'css', 'common.css')
        with open(common_css_path, 'r', encoding='utf-8') as fh:
            css_text = fh.read()
        side_rail_markup = 'Sponsored Picks' in css_text or '.affiliate-side-rail__panel' in css_text or '.affiliate-side-rail__intro' in css_text
        fixed_rule = 'position: fixed;' in css_text and '.affiliate-side-rail' in css_text
        sticky_rule = 'position: sticky;' in css_text and '.affiliate-side-rail' in css_text
        amazon_bar_rule = '.amazon-recommendation-grid' in css_text and '.amazon-recommendation-card' in css_text
        stack_rule = '.affiliate-stack__row' in css_text and '.affiliate-stack__label' in css_text
        rakuten_module_rule = '.affiliate-link-card--module .affiliate-link-card__anchor {' in css_text and 'flex-direction: row;' in css_text
        ok = amazon_bar_rule and stack_rule and rakuten_module_rule and not fixed_rule and not sticky_rule and not side_rail_markup
        rows.append(('9g_affiliate_css', 'static/css/common.css', 'OK affiliate stack styles and no fixed side rail' if ok else f'FAIL amazon_bar_rule={amazon_bar_rule} stack_rule={stack_rule} rakuten_module_rule={rakuten_module_rule} fixed_rule={fixed_rule} sticky_rule={sticky_rule} side_rail_markup={side_rail_markup}', ok))
        if not ok:
            all_ok = False
    except Exception as e:
        rows.append(('9g_affiliate_css', 'static/css/common.css', f'ERROR {e}', False))
        all_ok = False

    sitemap_locs = set()
    try:
        import re
        resp = get('/sitemap.xml')
        body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
        sitemap_locs = set(re.findall(r'<loc>([^<]+)</loc>', body))
    except Exception:
        sitemap_locs = set()

    title_index = {}
    h1_index = {}
    for path in INDEXABILITY_TARGET_PATHS:
        try:
            resp = get(path)
            status = resp.status_code if hasattr(resp, 'status_code') else resp[0]
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            robots = (soup.select_one('meta[name="robots"]') or {}).get('content', '') if soup.select_one('meta[name="robots"]') else ''
            canonical = (soup.select_one('link[rel="canonical"]') or {}).get('href', '') if soup.select_one('link[rel="canonical"]') else ''
            title = soup.title.get_text(strip=True) if soup.title else ''
            h1 = soup.find('h1').get_text(' ', strip=True) if soup.find('h1') else ''
            desc_count = len(soup.select('meta[name="description"]'))
            visible_text = soup.get_text('\n', strip=True)
            broken = [token for token in VISIBLE_TEXT_FORBIDDEN if token in visible_text]
            in_sitemap = canonical_for_path(path) in sitemap_locs
            ok = (
                status == 200
                and 'noindex' not in robots.lower()
                and canonical == canonical_for_path(path)
                and bool(title)
                and bool(h1)
                and desc_count == 1
                and not broken
                and in_sitemap
            )
            rows.append(
                ('10_indexability', path,
                 'OK canonical/self/indexable' if ok else
                 f'FAIL status={status} robots={robots or "missing"} canon={canonical or "missing"} title={bool(title)} h1={bool(h1)} desc={desc_count} sitemap={in_sitemap} broken={broken[:2]}',
                 ok)
            )
            if not ok:
                all_ok = False
            title_index.setdefault(title, []).append(path)
            h1_index.setdefault(h1, []).append(path)
        except Exception as e:
            rows.append(('10_indexability', path, f'ERROR {e}', False))
            all_ok = False

    for path in ARTICLE_SCHEMA_REQUIRED_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            schema_types = set()
            for tag in soup.select('script[type="application/ld+json"]'):
                raw = tag.get_text(strip=True)
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                payloads = payload if isinstance(payload, list) else [payload]
                for item in payloads:
                    if isinstance(item, dict):
                        item_type = item.get('@type')
                        if isinstance(item_type, list):
                            schema_types.update(item_type)
                        elif isinstance(item_type, str):
                            schema_types.add(item_type)
            ok = 'Article' in schema_types
            rows.append(('10b_article_schema', path, f'OK {sorted(schema_types)}' if ok else f'FAIL {sorted(schema_types)}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('10b_article_schema', path, f'ERROR {e}', False))
            all_ok = False

    duplicate_titles = {title: paths for title, paths in title_index.items() if title and len(paths) > 1}
    duplicate_h1 = {title: paths for title, paths in h1_index.items() if title and len(paths) > 1}
    titles_ok = not duplicate_titles
    h1_ok = not duplicate_h1
    rows.append(('11_title_dupes', 'indexable pages', 'OK unique titles' if titles_ok else f'FAIL {list(duplicate_titles.items())[:3]}', titles_ok))
    rows.append(('11_h1_dupes', 'indexable pages', 'OK unique h1' if h1_ok else f'FAIL {list(duplicate_h1.items())[:3]}', h1_ok))
    if not titles_ok or not h1_ok:
        all_ok = False

    for hub_path, required_links in HUB_LINK_REQUIREMENTS.items():
        try:
            resp = get(hub_path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            hrefs = {a.get('href') for a in soup.find_all('a', href=True)}
            missing = [href for href in required_links if href not in hrefs]
            ok = not missing
            rows.append(('12_hub_links', hub_path, 'OK all required links present' if ok else f'FAIL missing {missing[:4]}', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('12_hub_links', hub_path, f'ERROR {e}', False))
            all_ok = False

    for path in RELATED_CONTENT_REQUIRED_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            ok = bool(soup.select_one('.related-content'))
            rows.append(('13_related', path, 'OK related content rendered' if ok else 'FAIL related content missing', ok))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('13_related', path, f'ERROR {e}', False))
            all_ok = False

    for path in INTENTIONALLY_EXCLUDED_PATHS:
        try:
            resp = get(path)
            body = (resp.data if hasattr(resp, 'data') else resp[1]).decode('utf-8', errors='replace')
            soup = BeautifulSoup(body, 'html.parser')
            robots = (soup.select_one('meta[name="robots"]') or {}).get('content', '') if soup.select_one('meta[name="robots"]') else ''
            canonical = (soup.select_one('link[rel="canonical"]') or {}).get('href', '') if soup.select_one('link[rel="canonical"]') else ''
            desc_count = len(soup.select('meta[name="description"]'))
            in_sitemap = canonical_for_path(path) in sitemap_locs
            ok = 'noindex' in robots.lower() and canonical == canonical_for_path(path) and not in_sitemap and desc_count == 1
            rows.append((
                '14_excluded',
                path,
                'OK noindex+self canonical+not in sitemap'
                if ok else
                f'FAIL robots={robots or "missing"} canon={canonical or "missing"} sitemap={in_sitemap} desc={desc_count}',
                ok,
            ))
            if not ok:
                all_ok = False
        except Exception as e:
            rows.append(('14_excluded', path, f'ERROR {e}', False))
            all_ok = False

    return rows, all_ok


def run_live(base_url):
    """実サーバでチェック（urllib）"""
    import urllib.request
    import urllib.error

    def get(path, headers=None):
        url = base_url.rstrip('/') + path
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req) as r:
                body = r.read().decode('utf-8', errors='replace')
                h = dict(r.headers)
                return r.status, body, h
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            return e.code, body, dict(e.headers) if e.headers else {}

    # アダプタ: (status, body, headers) を返す形に
    def get_fn(path, headers=None):
        status, body, h = get(path, headers)
        class Resp:
            status_code = status
            data = body.encode('utf-8') if isinstance(body, str) else body
            headers = h
        return Resp()

    return _run_checks(lambda path, headers=None: get_fn(path, headers), base_url, use_headers=True)


def print_table(rows):
    """表形式で出力"""
    w1, w2, w3 = 16, 20, 50
    print(f"{'Check':<{w1}} {'Path':<{w2}} {'Result':<{w3}}")
    print('-' * (w1 + w2 + w3))
    for r in rows:
        status = 'OK' if r[3] else 'NG'
        print(f"{r[0]:<{w1}} {r[1]:<{w2}} [{status}] {r[2]}")


def main():
    parser = argparse.ArgumentParser(description='AdSense preflight check')
    parser.add_argument('--live', metavar='BASE_URL', default=None,
                        help=f'Use live server (default: {BASE_URL_DEFAULT})')
    args = parser.parse_args()

    base_url = args.live or 'http://test'
    if args.live:
        print(f"(live: {args.live})\n")
        rows, all_ok = run_live(args.live)
    else:
        print("(Flask test client)\n")
        rows, all_ok = run_local()

    print_table(rows)
    print()
    if all_ok:
        print("ALL CHECKS PASSED")
        return 0
    print("SOME CHECKS FAILED - fix before AdSense re-application")
    return 1


if __name__ == '__main__':
    sys.exit(main())
