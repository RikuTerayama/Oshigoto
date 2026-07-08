#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1-Content: 薄いコンテンツ監査用。
主要URLをFlask test clientで取得し、以下を証跡化する:
- HTTP status, X-Robots-Tag
- 本文テキスト文字数（タグ除去後）
- h1/h2/h3 数
- FAQ/注意点の有無（キーワード検出）
- 本文が極端に短い（<200字）場合は警告

実行: python scripts/audit_content_thinness.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 監査対象URL（必須対象を網羅）
AUDIT_PATHS = [
    '/',
    '/autofill',
    '/tools',
    '/guide',
    '/privacy',
    '/terms',
    '/about',
    '/contact',
    '/tools/pdf',
    '/tools/csv',
    '/tools/seo',
    '/tools/image-batch',
    '/tools/image-cleanup',
    '/guide/pdf',
    '/guide/csv',
    '/guide/seo',
    '/guide/image-batch',
    '/guide/image-cleanup',
    '/guide/autofill',
    '/guide/getting-started',
]
def normalize_path(p):
    return p

def strip_html_text(html):
    """タグを除去してテキストのみの文字数を返す（改行・連続空白は1スペースに）"""
    if not html:
        return 0, ''
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return len(text), text

def count_headings(html):
    h1 = len(re.findall(r'<h1[\s>]', html, re.IGNORECASE))
    h2 = len(re.findall(r'<h2[\s>]', html, re.IGNORECASE))
    h3 = len(re.findall(r'<h3[\s>]', html, re.IGNORECASE))
    return h1, h2, h3

def has_faq(html):
    return bool(re.search(r'FAQ|よくある質問|faq-item|faq-question', html, re.IGNORECASE))

def has_notes(html):
    return bool(re.search(r'注意|※|重要|ワーニング|warning|info-box|注意点', html, re.IGNORECASE))

def main():
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()

    rows = []
    for path in AUDIT_PATHS:
        path_use = normalize_path(path)
        resp = client.get(path_use, follow_redirects=True)
        body = resp.data.decode('utf-8', errors='replace')
        status = resp.status_code
        x_robots = resp.headers.get('X-Robots-Tag', '')
        char_count, _ = strip_html_text(body)
        h1, h2, h3 = count_headings(body)
        faq = 'Y' if has_faq(body) else 'N'
        notes = 'Y' if has_notes(body) else 'N'
        thin = 'WARN' if char_count < 200 else ('LOW' if char_count < 500 else ('MID' if char_count < 1200 else 'OK'))
        rows.append({
            'path': path_use,
            'status': status,
            'x_robots': x_robots or '-',
            'chars': char_count,
            'h1': h1, 'h2': h2, 'h3': h3,
            'faq': faq, 'notes': notes,
            'thin': thin,
        })

    # TSV 出力
    print('path\tstatus\tX-Robots-Tag\tchars\th1\th2\th3\tFAQ\tnotes\tthin')
    for r in rows:
        print(f"{r['path']}\t{r['status']}\t{r['x_robots']}\t{r['chars']}\t{r['h1']}\t{r['h2']}\t{r['h3']}\t{r['faq']}\t{r['notes']}\t{r['thin']}")

    # 極端に短いページ
    short = [r for r in rows if r['chars'] < 200]
    if short:
        print('\n# WARN: body text < 200 chars:', [r['path'] for r in short])
    return 0

if __name__ == '__main__':
    sys.exit(main())
