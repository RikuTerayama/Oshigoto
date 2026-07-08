#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E: /tools/csv の CDN ロード・Console エラー・ファイル送信なし を Playwright で検証し証跡を残す。
証跡: グローバル変数 (Papa, XLSX, Encoding, JSZip)、Console メッセージ、origin への POST/PUT/PATCH 件数。
使用例:
  python scripts/e2e_tools_csv_playwright.py
  BASE_URL=http://127.0.0.1:5000 python scripts/e2e_tools_csv_playwright.py
  python scripts/e2e_tools_csv_playwright.py --output evidence_e2e.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:5000').rstrip('/')


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed. pip install playwright && playwright install chromium")
        return 2

    output_file = None
    if '--output' in sys.argv:
        i = sys.argv.index('--output')
        if i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]

    evidence = {
        'base_url': BASE_URL,
        'url': f'{BASE_URL}/tools/csv',
        'globals_ok': False,
        'globals': {},
        'console_errors': [],
        'origin_mutating_requests': [],
        'passed': False,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context()
            # リクエスト記録（origin への POST/PUT/PATCH）
            requests_log = []

            def on_request(req):
                url = req.url
                method = req.method.upper()
                if method in ('POST', 'PUT', 'PATCH') and url.startswith(BASE_URL):
                    requests_log.append({'method': method, 'url': url})

            context.on('request', on_request)
            page = context.new_page()
            console_msgs = []

            def on_console(msg):
                if msg.type in ('error', 'warning'):
                    console_msgs.append({'type': msg.type, 'text': msg.text})

            page.on('console', on_console)
            page.goto(f'{BASE_URL}/tools/csv', wait_until='networkidle')
            page.wait_for_timeout(1500)

            # グローバル確認
            globals_check = page.evaluate("""() => ({
                Papa: typeof Papa !== 'undefined',
                XLSX: typeof XLSX !== 'undefined',
                Encoding: typeof Encoding !== 'undefined',
                JSZip: typeof JSZip !== 'undefined',
            })""")
            evidence['globals'] = globals_check
            evidence['globals_ok'] = all(globals_check.values())

            # Console エラー（未定義系を記録）
            evidence['console_errors'] = [m for m in console_msgs if 'undefined' in m.get('text', '') or m.get('type') == 'error']

            # サンプルCSVで「実行」まで行い、その後のリクエストを確認
            sample_csv = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'docs', 'dev-samples', 'csv', 'sample_utf8.csv'
            )
            if os.path.isfile(sample_csv):
                try:
                    file_input = page.locator('#file-input')
                    file_input.set_input_files(sample_csv)
                    page.wait_for_timeout(500)
                    page.locator('#run-btn').click()
                    page.wait_for_timeout(2000)
                except Exception as e:
                    evidence['run_step_error'] = str(e)
            else:
                evidence['run_skipped'] = 'sample_utf8.csv not found'

            evidence['origin_mutating_requests'] = requests_log
            evidence['passed'] = (
                evidence['globals_ok']
                and len(evidence['origin_mutating_requests']) == 0
                and len([e for e in evidence['console_errors'] if e.get('type') == 'error']) == 0
            )
        finally:
            browser.close()

    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(evidence, f, indent=2, ensure_ascii=False)
        print(f"(written to {output_file})", file=sys.stderr)
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
