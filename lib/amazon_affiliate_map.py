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
        "enabled": False,
        "category_label": "集中環境",
        "title": "集中しやすい作業環境をつくるおすすめ",
        "query": "集中力 作業環境 グッズ",
        "query_variants": [],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "guide"],
        "priority_path_prefixes": ["/", "/guide"],
    },
]

# Backward-compat alias for older imports.
AMAZON_PURPOSE_GENRES = AMAZON_THEME_POOL

PATH_KEYWORD_RULES: List[Tuple[str, List[str]]] = [
    ("/guide", ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/tools/image", ["デスク整理 仕事効率化 グッズ", "ケーブル整理", "在宅勤務 快適 グッズ"]),
    ("/tools/pdf", ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "業務効率化 本"]),
    ("/tools/seo", ["ビジネス書 AI活用本 おすすめ", "デスク整理 仕事効率化 グッズ", "生成AI 活用"]),
    ("/tools/csv", ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/tools", ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/blog", ["ビジネス書 AI活用本 おすすめ", "業務効率化 本", "デスク整理 仕事効率化 グッズ"]),
    ("/case", ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/faq", ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"]),
    ("/glossary", ["ビジネス書 AI活用本 おすすめ", "在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ"]),
]

PAGE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "landing": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "guide": ["在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ", "デスク整理 仕事効率化 グッズ"],
    "tool": ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "tool_index": ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "article": ["ビジネス書 AI活用本 おすすめ", "デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ"],
    "blog_index": ["ビジネス書 AI活用本 おすすめ", "業務効率化 本", "デスク整理 仕事効率化 グッズ"],
    "case_index": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "info": ["デスク整理 仕事効率化 グッズ", "在宅勤務 快適 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "trust_sensitive": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"],
    "legal": ["ビジネス書 AI活用本 おすすめ", "デスク整理 仕事効率化 グッズ"],
    "contact": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ"],
    "generic": ["在宅勤務 快適 グッズ", "デスク整理 仕事効率化 グッズ", "ビジネス書 AI活用本 おすすめ"],
}
