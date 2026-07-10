#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Route and page-type keyword mapping for Amazon recommendations.
Keep this file small and explicit so keyword tuning is easy in future PRs.
"""

from typing import Dict, List, Tuple

# Approved theme pool for Amazon recommendation cards.
# - Only entries with enabled=True are eligible for production rendering.
# - Keep display copy (title/category_label) separate from search query.
# - Future flow: AI proposes candidates -> human approves by toggling enabled.
AMAZON_THEME_POOL: List[Dict[str, object]] = [
    {
        "id": "remote-work-comfort",
        "enabled": True,
        "category_label": "快適ワーク環境",
        "title": "在宅勤務を快適にするおすすめ",
        "query": "在宅勤務 快適 グッズ",
        "query_variants": ["在宅勤務 快適化 アイテム", "リモートワーク 快適 グッズ"],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "guide", "tool", "tool_index", "trust_sensitive"],
        "priority_path_prefixes": ["/", "/guide", "/tools"],
    },
    {
        "id": "desk-organization-productivity",
        "enabled": True,
        "category_label": "仕事効率化",
        "title": "デスク整理・仕事効率化のおすすめ",
        "query": "デスク整理 仕事効率化 グッズ",
        "query_variants": ["デスク周り 整理 便利グッズ", "作業効率アップ デスクアイテム"],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "tool", "tool_index", "info", "generic"],
        "priority_path_prefixes": ["/", "/tools", "/faq", "/about"],
    },
    {
        "id": "business-books-ai",
        "enabled": True,
        "category_label": "学び・インプット",
        "title": "仕事に効くビジネス書・AI活用本",
        "query": "ビジネス書 おすすめ",
        "query_variants": ["生成AI 本", "仕事術 本"],
        "cta": "Amazonで見る",
        "priority_page_types": ["blog_index", "article", "guide", "info"],
        "priority_path_prefixes": ["/blog", "/guide", "/glossary", "/best-practices"],
    },
    {
        "id": "pdf-document-work",
        "enabled": True,
        "category_label": "PDF・書類作業",
        "title": "PDF・書類作業まわりを整える道具",
        "query": "PDF 書類整理 アイテム",
        "query_variants": ["書類整理 グッズ", "契約書 PDF 作業 本"],
        "cta": "書類作業アイテムを見る",
        "priority_page_types": ["tool", "tool_index", "landing", "guide"],
        "priority_path_prefixes": ["/tools/pdf", "/guide/pdf", "/tools", "/"],
    },
    {
        "id": "spreadsheet-desk-work",
        "enabled": True,
        "category_label": "表計算・デスク作業",
        "title": "表作業を少し楽にする道具",
        "query": "Excel 表計算 本",
        "query_variants": ["デスク作業 効率化 アイテム", "仕事効率化 本"],
        "cta": "表作業の道具を見る",
        "priority_page_types": ["tool", "tool_index", "landing", "guide"],
        "priority_path_prefixes": ["/tools/csv", "/guide/csv", "/tools"],
    },
    {
        "id": "image-material-work",
        "enabled": True,
        "category_label": "画像・資料作成",
        "title": "画像・資料作成まわりを整える道具",
        "query": "画像整理 アイテム",
        "query_variants": ["資料作成 本", "デスク環境 整理 グッズ"],
        "cta": "画像作業アイテムを見る",
        "priority_page_types": ["tool", "tool_index", "landing", "guide"],
        "priority_path_prefixes": ["/tools/image-batch", "/guide/image-batch", "/tools"],
    },
    {
        "id": "product-photo-work",
        "enabled": True,
        "category_label": "撮影・画像整備",
        "title": "商品画像・資料画像を整える道具",
        "query": "商品撮影 小物",
        "query_variants": ["撮影背景 シート", "資料作成 アイテム"],
        "cta": "撮影まわりを見る",
        "priority_page_types": ["tool", "tool_index", "guide"],
        "priority_path_prefixes": ["/tools/image-cleanup", "/guide/image-cleanup"],
    },
    {
        "id": "seo-marketing-books",
        "enabled": True,
        "category_label": "Web運用・マーケティング",
        "title": "Web運用とマーケティングを学ぶ本",
        "query": "SEO 本",
        "query_variants": ["Webマーケティング 本", "SNS運用 本"],
        "cta": "Web運用の本を見る",
        "priority_page_types": ["tool", "tool_index", "guide", "article"],
        "priority_path_prefixes": ["/tools/seo", "/guide/seo", "/blog"],
    },
    {
        "id": "long-hours-deskwork",
        "enabled": True,
        "category_label": "長時間作業対策",
        "title": "長時間デスクワークをラクにするおすすめ",
        "query": "長時間 デスクワーク 疲労軽減 グッズ",
        "query_variants": ["デスクワーク 疲れ対策 アイテム", "仕事中 疲労軽減 グッズ"],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "guide", "tool", "trust_sensitive"],
        "priority_path_prefixes": ["/", "/guide", "/tools"],
    },
    {
        "id": "posture-shoulder-back",
        "enabled": True,
        "category_label": "姿勢ケア",
        "title": "姿勢改善・肩腰対策のおすすめ",
        "query": "姿勢改善 肩こり 腰痛 対策 グッズ",
        "query_variants": ["肩こり 腰痛 デスクワーク 対策", "姿勢サポート アイテム"],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "guide", "info", "trust_sensitive"],
        "priority_path_prefixes": ["/", "/guide", "/faq", "/about"],
    },
    {
        "id": "space-saving-desk",
        "enabled": True,
        "category_label": "省スペース整備",
        "title": "省スペースで整うデスク環境のおすすめ",
        "query": "省スペース デスク環境 整理 グッズ",
        "query_variants": ["狭いデスク 整理 便利グッズ", "デスク収納 省スペース おすすめ"],
        "cta": "Amazonで見る",
        "priority_page_types": ["tool", "tool_index", "landing", "generic"],
        "priority_path_prefixes": ["/tools", "/", "/contact"],
    },
    # Reserved candidates (disabled by default until human review/approval).
    {
        "id": "focus-sound-environment",
        "enabled": True,
        "category_label": "集中環境",
        "title": "集中しやすい作業環境をつくるおすすめ",
        "query": "集中力 作業環境 グッズ",
        "query_variants": [],
        "cta": "集中環境を整える",
        "priority_page_types": ["landing", "tool_index", "guide"],
        "priority_path_prefixes": ["/", "/tools", "/guide"],
    },
]

# Backward-compat alias for older imports.
AMAZON_PURPOSE_GENRES = AMAZON_THEME_POOL

PATH_KEYWORD_RULES: List[Tuple[str, List[str]]] = [
    ("/guide", ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/tools/image-cleanup", ["商品撮影 小物", "撮影背景 シート", "資料作成 アイテム"]),
    ("/tools/image-batch", ["画像整理 アイテム", "資料作成 本", "デスク環境 整理 グッズ"]),
    ("/tools/image", ["画像整理 アイテム", "資料作成 本", "デスク環境 整理 グッズ"]),
    ("/tools/pdf", ["PDF 書類整理 アイテム", "書類整理 グッズ", "契約書 PDF 作業 本"]),
    ("/tools/seo", ["SEO 本", "Webマーケティング 本", "SNS運用 本"]),
    ("/tools/csv", ["Excel 表計算 本", "デスク作業 効率化 アイテム", "仕事効率化 本"]),
    ("/tools", ["PDF 書類整理 アイテム", "Excel 表計算 本", "デスク環境 整理 グッズ"]),
    ("/blog", ["ビジネス書 AI活用本 おすすめ", "業務効率化 本", "デスク整理 仕事効率化 グッズ"]),
    ("/case", ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/faq", ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/glossary", ["ビジネス書 AI活用本 おすすめ", "在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ"]),
]

PAGE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "landing": ["PDF 書類整理 アイテム", "デスク環境 整理 グッズ", "ビジネス書 おすすめ"],
    "guide": ["在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ", "デスク整理 仕事効率化 グッズ"],
    "tool": ["PDF 書類整理 アイテム", "Excel 表計算 本", "画像整理 アイテム"],
    "tool_index": ["PDF 書類整理 アイテム", "Excel 表計算 本", "デスク環境 整理 グッズ"],
    "article": ["ビジネス書 AI活用本 おすすめ", "デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ"],
    "blog_index": ["ビジネス書 AI活用本 おすすめ", "業務効率化 本", "デスク整理 仕事効率化 グッズ"],
    "case_index": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "info": ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "trust_sensitive": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "legal": ["ビジネス書 AI活用本 おすすめ", "デスク整理 仕事効率化 グッズ"],
    "contact": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ"],
    "generic": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"],
}
