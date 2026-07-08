#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AdSense「有用性の低いコンテンツ」判定を覆すためのHTML分析スクリプト
"""

import os
import re
from pathlib import Path
from collections import Counter, defaultdict
from html.parser import HTMLParser
from typing import Dict, List, Tuple, Set
import json

class TextExtractor(HTMLParser):
    """HTMLからテキストを抽出するパーサー"""
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip_tags = {'script', 'style', 'noscript', 'meta', 'link', 'head'}
        self.in_skip = False
        self.current_tag = None
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in self.skip_tags:
            self.in_skip = True
            
    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.in_skip = False
        self.current_tag = None
            
    def handle_data(self, data):
        if not self.in_skip and self.current_tag not in self.skip_tags:
            # 空白を正規化
            text = re.sub(r'\s+', ' ', data.strip())
            if text:
                self.text.append(text)
    
    def get_text(self) -> str:
        return ' '.join(self.text)

def extract_text_from_html(html_content: str) -> str:
    """HTMLからテキストを抽出"""
    parser = TextExtractor()
    parser.feed(html_content)
    return parser.get_text()

def extract_meta_description(html_content: str) -> str:
    """meta descriptionを抽出"""
    # name="description" または property="og:description"
    patterns = [
        r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
        r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']',
        r'{%\s*block\s+description_meta\s*%}.*?<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
    
    return ""

def extract_title(html_content: str) -> str:
    """titleを抽出"""
    patterns = [
        r'<title>([^<]+)</title>',
        r'{%\s*block\s+title\s*%}([^%]+){%\s*endblock\s*%}',
        r'{%\s*set\s+page_title\s*=\s*["\']([^"\']+)["\']',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    
    return ""

def check_indexing_settings(html_content: str) -> Dict[str, bool]:
    """インデックス設定を確認"""
    result = {
        'has_noindex': False,
        'has_nofollow': False,
        'has_robots_meta': False,
        'has_canonical': False,
    }
    
    # robots metaタグをチェック
    robots_pattern = r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']+)["\']'
    robots_match = re.search(robots_pattern, html_content, re.IGNORECASE)
    if robots_match:
        result['has_robots_meta'] = True
        content = robots_match.group(1).lower()
        if 'noindex' in content:
            result['has_noindex'] = True
        if 'nofollow' in content:
            result['has_nofollow'] = True
    
    # canonicalタグをチェック
    canonical_pattern = r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']'
    if re.search(canonical_pattern, html_content, re.IGNORECASE):
        result['has_canonical'] = True
    
    return result

def count_keywords(text: str, keywords: List[str]) -> Dict[str, int]:
    """キーワードの出現頻度をカウント"""
    text_lower = text.lower()
    counts = {}
    for keyword in keywords:
        # 単語境界を考慮した検索
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        matches = len(re.findall(pattern, text_lower))
        counts[keyword] = matches
        
        # 複合語も検出（例：「勤怠管理」「データ入力」「自動化ツール」「業務効率化」）
        # ただし、既に単独で検出されている場合は追加しない
        if matches == 0:
            # 複合語パターンも検索
            compound_pattern = re.escape(keyword.lower())
            compound_matches = len(re.findall(compound_pattern, text_lower))
            if compound_matches > 0:
                counts[keyword] = compound_matches
    return counts

def analyze_html_file(file_path: Path) -> Dict:
    """単一のHTMLファイルを分析"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {'error': str(e)}
    
    # テキスト抽出
    text = extract_text_from_html(content)
    text_length = len(text)
    
    # meta description抽出
    meta_description = extract_meta_description(content)
    
    # title抽出
    title = extract_title(content)
    
    # インデックス設定確認
    indexing = check_indexing_settings(content)
    
    return {
        'file_path': str(file_path),
        'text_length': text_length,
        'meta_description': meta_description,
        'meta_description_length': len(meta_description),
        'title': title,
        'indexing': indexing,
        'text_sample': text[:200] + '...' if len(text) > 200 else text,
    }

def main():
    """メイン処理"""
    import sys
    import io
    # WindowsでのUnicode出力対応
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    templates_dir = Path('templates')
    
    # 分析対象のキーワード
    keywords = ['Jobcan', '自動化', '効率化', '勤怠', 'Excel', 'データ', '入力', 'ツール', 'Playwright', '業務']
    
    # 全HTMLファイルを取得
    html_files = list(templates_dir.rglob('*.html'))
    
    print("=" * 80)
    print("AdSense「有用性の低いコンテンツ」判定を覆すための分析レポート")
    print("=" * 80)
    print()
    
    # 分析結果を格納
    results = []
    meta_descriptions = []
    all_text = ""
    keyword_counts = Counter()
    
    for html_file in sorted(html_files):
        print(f"分析中: {html_file}")
        result = analyze_html_file(html_file)
        if 'error' not in result:
            results.append(result)
            if result['meta_description']:
                meta_descriptions.append((str(html_file), result['meta_description']))
            # 全文を取得（ファイルを再度読み込む）
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                full_text = extract_text_from_html(file_content)
                all_text += full_text
                
                # キーワードカウント（全文を使用）
                file_keywords = count_keywords(full_text, keywords)
            except Exception as e:
                # エラーが発生した場合はテキストサンプルを使用
                full_text = result.get('text_sample', '')
                all_text += full_text
                file_keywords = count_keywords(full_text, keywords)
            for kw, count in file_keywords.items():
                keyword_counts[kw] += count
    
    print()
    print("=" * 80)
    print("1. テキスト量分析（500文字未満の薄いページ）")
    print("=" * 80)
    print()
    
    thin_pages = []
    for result in results:
        if result['text_length'] < 500:
            thin_pages.append({
                'file': result['file_path'],
                'length': result['text_length'],
                'title': result.get('title', 'N/A'),
            })
    
    if thin_pages:
        print("⚠️  500文字未満のページが見つかりました:")
        print()
        for page in sorted(thin_pages, key=lambda x: x['length']):
            print(f"  - {page['file']}")
            print(f"    文字数: {page['length']}文字")
            print(f"    タイトル: {page['title']}")
            print()
    else:
        print("✅ すべてのページが500文字以上です。")
        print()
    
    # テキスト量の統計
    text_lengths = [r['text_length'] for r in results]
    if text_lengths:
        print(f"統計情報:")
        print(f"  平均文字数: {sum(text_lengths) / len(text_lengths):.0f}文字")
        print(f"  最小文字数: {min(text_lengths)}文字")
        print(f"  最大文字数: {max(text_lengths)}文字")
        print(f"  総ページ数: {len(results)}ページ")
        print()
    
    print("=" * 80)
    print("2. Meta Descriptionの重複チェック")
    print("=" * 80)
    print()
    
    # 重複チェック
    description_map = defaultdict(list)
    for file_path, desc in meta_descriptions:
        if desc:
            description_map[desc].append(file_path)
    
    duplicates = {desc: files for desc, files in description_map.items() if len(files) > 1}
    
    if duplicates:
        print("⚠️  重複しているmeta descriptionが見つかりました:")
        print()
        for desc, files in duplicates.items():
            print(f"  重複内容: {desc[:100]}...")
            print(f"  該当ファイル:")
            for f in files:
                print(f"    - {f}")
            print()
    else:
        print("✅ 重複しているmeta descriptionは見つかりませんでした。")
        print()
    
    # 独自性チェック
    unique_descriptions = len(description_map)
    total_with_description = len([r for r in results if r.get('meta_description')])
    
    print(f"統計情報:")
    print(f"  Meta descriptionが設定されているページ: {total_with_description}/{len(results)}")
    print(f"  ユニークなdescription数: {unique_descriptions}")
    print()
    
    # description未設定のページ
    no_description = [r for r in results if not r.get('meta_description')]
    if no_description:
        print("⚠️  Meta descriptionが設定されていないページ:")
        for r in no_description:
            print(f"  - {r['file_path']}")
        print()
    
    print("=" * 80)
    print("3. キーワード出現頻度分析")
    print("=" * 80)
    print()
    
    print("サイト全体のキーワード出現頻度:")
    print()
    for keyword, count in keyword_counts.most_common():
        print(f"  {keyword}: {count}回")
    print()
    
    # キーワードの偏りチェック
    total_keyword_count = sum(keyword_counts.values())
    if total_keyword_count > 0:
        print("キーワードの分布:")
        for keyword, count in keyword_counts.most_common():
            percentage = (count / total_keyword_count) * 100
            print(f"  {keyword}: {percentage:.1f}%")
        print()
        
        # 特定キーワードに偏りすぎていないかチェック
        max_percentage = max([(count / total_keyword_count) * 100 for count in keyword_counts.values()]) if keyword_counts else 0
        if max_percentage > 40:
            print(f"⚠️  特定のキーワードに偏りがあります（最大: {max_percentage:.1f}%）")
        else:
            print("✅ キーワードの分布は適切です。")
        print()
    
    print("=" * 80)
    print("4. インデックス設定の確認")
    print("=" * 80)
    print()
    
    # インデックスすべきでないページ
    should_not_index = ['error.html', 'contact.html']
    
    indexing_issues = []
    for result in results:
        file_name = Path(result['file_path']).name
        indexing = result.get('indexing', {})
        
        # インデックスすべきでないページのチェック
        if any(should_not in file_name.lower() for should_not in should_not_index):
            if not indexing.get('has_noindex'):
                indexing_issues.append({
                    'file': result['file_path'],
                    'issue': 'インデックスすべきでないページにnoindexが設定されていません',
                    'indexing': indexing,
                })
    
    if indexing_issues:
        print("⚠️  インデックス設定に問題があるページ:")
        print()
        for issue in indexing_issues:
            print(f"  - {issue['file']}")
            print(f"    問題: {issue['issue']}")
            print(f"    現在の設定: noindex={issue['indexing'].get('has_noindex')}, "
                  f"nofollow={issue['indexing'].get('has_nofollow')}, "
                  f"canonical={issue['indexing'].get('has_canonical')}")
            print()
    else:
        print("✅ インデックス設定は適切です。")
        print()
    
    # 全ページのインデックス設定統計
    noindex_count = sum(1 for r in results if r.get('indexing', {}).get('has_noindex'))
    canonical_count = sum(1 for r in results if r.get('indexing', {}).get('has_canonical'))
    
    print(f"統計情報:")
    print(f"  noindex設定ページ: {noindex_count}/{len(results)}")
    print(f"  canonical設定ページ: {canonical_count}/{len(results)}")
    print()
    
    print("=" * 80)
    print("5. 詳細なページ別レポート")
    print("=" * 80)
    print()
    
    for result in sorted(results, key=lambda x: x['text_length']):
        print(f"ファイル: {result['file_path']}")
        print(f"  文字数: {result['text_length']}文字")
        print(f"  タイトル: {result.get('title', 'N/A')}")
        print(f"  Meta description: {result.get('meta_description', '未設定')[:80]}...")
        print(f"  インデックス設定: noindex={result.get('indexing', {}).get('has_noindex')}, "
              f"canonical={result.get('indexing', {}).get('has_canonical')}")
        print()
    
    # JSON形式で結果を保存
    output = {
        'summary': {
            'total_pages': len(results),
            'thin_pages_count': len(thin_pages),
            'unique_descriptions': unique_descriptions,
            'total_keyword_count': total_keyword_count,
        },
        'thin_pages': thin_pages,
        'duplicate_descriptions': {desc: files for desc, files in duplicates.items()},
        'keyword_counts': dict(keyword_counts),
        'indexing_issues': indexing_issues,
        'all_results': results,
    }
    
    with open('adsense_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("=" * 80)
    print("分析完了。詳細な結果は 'adsense_analysis_report.json' に保存されました。")
    print("=" * 80)

if __name__ == '__main__':
    main()

