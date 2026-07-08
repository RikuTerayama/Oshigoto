#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase1 実装の受け入れ確認: fallback / canonical / CTA."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()
    failed = []

    # 1) canonical / og:url に BASE_URL が反映（デフォルト時は現行ドメイン）
    r = client.get('/')
    body = r.data.decode('utf-8')
    if r.status_code != 200:
        failed.append(f"/ status={r.status_code}")
    if 'jobcan-automation.onrender.com' not in body:
        failed.append("/: canonical/og:url default domain not found")
    if '/contact' not in body or 'お問い合わせ' not in body:
        failed.append("/: LP contact CTA not found")

    # 2) /about: OPERATOR_* 未設定時も問い合わせ導線
    r2 = client.get('/about')
    b2 = r2.data.decode('utf-8')
    if r2.status_code != 200:
        failed.append(f"/about status={r2.status_code}")
    if '/contact' not in b2:
        failed.append("/about: /contact link not found")
    if '運営者情報' not in b2:
        failed.append("/about: 運営者情報 section missing")

    # 3) /contact: OPERATOR_EMAIL 未設定時はフォーム主導線の案内
    r3 = client.get('/contact')
    b3 = r3.data.decode('utf-8')
    if r3.status_code != 200:
        failed.append(f"/contact status={r3.status_code}")
    # フォールバック時は「受け付けについて」または「主な窓口」が含まれる
    if '受け付け' not in b3 and '主な窓口' not in b3:
        failed.append("/contact: fallback copy (受け付け/主な窓口) not found")

    if failed:
        for f in failed:
            print("FAIL:", f)
        return 1
    print("OK: Phase1 verification (canonical default, LP CTA, about/contact fallback)")
    return 0

if __name__ == '__main__':
    sys.exit(main())
