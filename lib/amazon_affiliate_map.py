#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Route policy and approved themes for Amazon recommendations."""

from typing import Dict, List, Tuple


VISIBLE_AMAZON_MAX_PER_PAGE = 1
LANDING_VISIBLE_AMAZON_MAX_PER_PAGE = 2

AMAZON_HIGH_CONTENT_EXACT_PATHS = frozenset(
    (
        "/tools",
        "/tools/pdf",
        "/tools/csv",
        "/tools/image-batch",
        "/tools/image-compress",
        "/tools/image-cleanup",
        "/tools/qr-code",
        "/tools/seo",
        "/guide",
        "/guide/pdf",
        "/guide/csv",
        "/guide/image-batch",
        "/guide/image-compress",
        "/guide/image-cleanup",
        "/guide/qr-code",
        "/guide/seo",
        "/best-practices",
        "/glossary",
        "/blog",
    )
)
AMAZON_HIGH_CONTENT_PREFIXES = ("/blog/",)

AMAZON_HARD_EXCLUDED_PATHS = frozenset(
    ("/about", "/business", "/contact", "/privacy", "/terms")
)

AMAZON_ELIGIBLE_EXACT_PATHS = frozenset(
    (
        "/",
        "/tools",
        "/tools/pdf",
        "/tools/csv",
        "/tools/image-batch",
        "/tools/image-compress",
        "/tools/image-cleanup",
        "/tools/qr-code",
        "/tools/seo",
        "/guide",
        "/guide/pdf",
        "/guide/csv",
        "/guide/image-batch",
        "/guide/image-compress",
        "/guide/image-cleanup",
        "/guide/qr-code",
        "/guide/seo",
        "/faq",
        "/glossary",
        "/best-practices",
        "/blog",
    )
)

AMAZON_ELIGIBLE_PREFIXES = ("/blog/",)

AMAZON_CONTENT_PATHS = frozenset(
    (
        "/",
        "/tools",
        "/tools/pdf",
        "/tools/csv",
        "/tools/image-batch",
        "/tools/image-compress",
        "/tools/image-cleanup",
        "/tools/seo",
    )
)

AMAZON_ICON_ALLOWLIST = frozenset(
    ("book", "document", "spreadsheet", "image", "desk", "stationery", "web")
)

AMAZON_THEME_ICON_MAP = {
    "kindle-productivity": "book",
    "kindle-excel": "spreadsheet",
    "kindle-seo-marketing": "web",
    "kindle-writing-documents": "document",
    "pdf-document-work": "document",
    "spreadsheet-desk-work": "spreadsheet",
    "image-material-work": "image",
    "desk-organization": "desk",
    "office-stationery": "stationery",
    "desk-focus-environment": "desk",
    "pdf-workflow-tools": "document",
    "pdf-workflow-books": "book",
    "csv-data-tools": "spreadsheet",
    "csv-excel-books": "book",
    "image-batch-tools": "image",
    "image-batch-books": "book",
    "image-compress-tools": "image",
    "image-compress-books": "book",
    "image-cleanup-tools": "image",
    "image-cleanup-books": "book",
    "qr-code-tools": "stationery",
    "qr-code-books": "book",
    "seo-web-tools": "web",
    "seo-learning-books": "book",
}


def normalize_amazon_path(path: str | None) -> str:
    normalized = str(path or "/").split("?", 1)[0].split("#", 1)[0]
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized


def get_amazon_page_policy(path: str | None) -> Dict[str, object] | None:
    """Return the sole allowed Amazon placement for a public page."""
    normalized = normalize_amazon_path(path)
    if normalized in AMAZON_HARD_EXCLUDED_PATHS:
        return None
    if normalized not in AMAZON_ELIGIBLE_EXACT_PATHS and not any(
        normalized.startswith(prefix) for prefix in AMAZON_ELIGIBLE_PREFIXES
    ):
        return None

    if normalized == "/":
        return {"enabled": True, "render_target": "content", "placement": "top-primary-amazon"}
    if normalized == "/tools":
        return {"enabled": True, "render_target": "content", "placement": "tools-primary-amazon"}
    if normalized in AMAZON_CONTENT_PATHS:
        return {"enabled": True, "render_target": "content", "placement": "tool-primary-amazon"}
    if normalized.startswith("/blog/"):
        return {"enabled": True, "render_target": "content", "placement": "article-primary-amazon"}
    return {"enabled": True, "render_target": "content", "placement": "content-primary-amazon"}


def get_amazon_visible_limit(path: str | None) -> int:
    """Return the route-level visibility cap for approved editorial placements."""
    normalized = normalize_amazon_path(path)
    if normalized == "/":
        return LANDING_VISIBLE_AMAZON_MAX_PER_PAGE
    if normalized in AMAZON_HIGH_CONTENT_EXACT_PATHS or any(
        normalized.startswith(prefix) for prefix in AMAZON_HIGH_CONTENT_PREFIXES
    ):
        return 2
    return VISIBLE_AMAZON_MAX_PER_PAGE

AMAZON_THEME_POOL: List[Dict[str, object]] = [
    {
        "id": "kindle-productivity",
        "enabled": True,
        "category_label": "Kindle 仕事効率化",
        "title": "仕事効率化を学ぶKindle本",
        "query": "Kindle 仕事効率化",
        "query_variants": ["Kindle タスク管理", "Kindle 業務改善"],
        "cta": "Amazonで見る",
        "priority_page_types": ["landing", "tool_index", "guide", "info"],
        "priority_path_prefixes": ["/", "/tools", "/guide", "/faq"],
    },
    {
        "id": "kindle-excel",
        "enabled": True,
        "category_label": "Kindle Excel",
        "title": "Excel・表作業のKindle本",
        "query": "Kindle Excel",
        "query_variants": ["Kindle データ分析", "Excel 表計算 Kindle"],
        "cta": "Excel本を見る",
        "priority_page_types": ["tool", "tool_index", "guide", "article"],
        "priority_path_prefixes": ["/tools/csv", "/guide/csv", "/tools", "/blog"],
    },
    {
        "id": "kindle-seo-marketing",
        "enabled": True,
        "category_label": "Kindle SEO",
        "title": "SEO・WebマーケティングのKindle本",
        "query": "Kindle SEO",
        "query_variants": ["Kindle Webマーケティング", "SNS運用 Kindle"],
        "cta": "SEO本を見る",
        "priority_page_types": ["tool", "tool_index", "guide", "article"],
        "priority_path_prefixes": ["/tools/seo", "/guide/seo", "/blog"],
    },
    {
        "id": "kindle-writing-documents",
        "enabled": True,
        "category_label": "Kindle 文章・資料",
        "title": "文章作成・資料作成のKindle本",
        "query": "Kindle 文章術",
        "query_variants": ["資料作成 Kindle", "ビジネス文書 Kindle"],
        "cta": "資料作成本を見る",
        "priority_page_types": ["landing", "guide", "article", "info"],
        "priority_path_prefixes": ["/", "/guide", "/blog", "/glossary"],
    },
    {
        "id": "pdf-document-work",
        "enabled": True,
        "category_label": "PDF・書類作業",
        "title": "PDF・書類作業を整える仕事道具",
        "query": "PDF 書類整理 文房具",
        "query_variants": ["書類整理 文房具", "デスク整理 収納"],
        "cta": "書類作業の道具を見る",
        "priority_page_types": ["tool", "tool_index", "landing", "guide"],
        "priority_path_prefixes": ["/tools/pdf", "/guide/pdf", "/tools", "/"],
    },
    {
        "id": "spreadsheet-desk-work",
        "enabled": True,
        "category_label": "表計算・デスク作業",
        "title": "表作業を進めやすくする仕事道具",
        "query": "テンキー オフィス用品",
        "query_variants": ["デスク作業 文房具", "オフィス用品 書類整理"],
        "cta": "表作業の道具を見る",
        "priority_page_types": ["tool", "tool_index", "landing", "guide"],
        "priority_path_prefixes": ["/tools/csv", "/guide/csv", "/tools"],
    },
    {
        "id": "image-material-work",
        "enabled": True,
        "category_label": "画像・資料作成",
        "title": "画像整理・資料作成に役立つ仕事道具",
        "query": "資料作成 文房具",
        "query_variants": ["画像編集 Kindle", "撮影 小物 仕事道具"],
        "cta": "資料作成の道具を見る",
        "priority_page_types": ["tool", "tool_index", "landing", "guide"],
        "priority_path_prefixes": ["/tools/image-batch", "/tools/image-cleanup", "/guide/image", "/tools"],
    },
    {
        "id": "desk-organization",
        "enabled": True,
        "category_label": "デスク整理",
        "title": "デスクまわりを整える仕事道具",
        "query": "デスク整理 収納",
        "query_variants": ["ケーブル収納 デスク", "文房具 ファイル整理"],
        "cta": "デスク整理を見る",
        "priority_page_types": ["landing", "tool_index", "tool", "contact", "generic"],
        "priority_path_prefixes": ["/", "/tools", "/contact"],
    },
    {
        "id": "office-stationery",
        "enabled": True,
        "category_label": "文房具・オフィス用品",
        "title": "毎日の作業に使う文房具・オフィス用品",
        "query": "文房具 オフィス用品",
        "query_variants": ["ファイル整理 文房具", "書類整理 オフィス用品"],
        "cta": "文房具を見る",
        "priority_page_types": ["landing", "tool_index", "tool", "info"],
        "priority_path_prefixes": ["/", "/tools", "/faq"],
    },
    {
        "id": "desk-focus-environment",
        "enabled": True,
        "category_label": "作業環境",
        "title": "集中しやすいデスク環境をつくる道具",
        "query": "デスク環境 集中",
        "query_variants": ["姿勢 デスクワーク", "作業環境 グッズ"],
        "cta": "作業環境を見る",
        "priority_page_types": ["landing", "tool_index", "guide", "info"],
        "priority_path_prefixes": ["/", "/tools", "/guide", "/about"],
    },
    {
        "id": "pdf-workflow-tools",
        "enabled": True,
        "category_label": "PDF・資料作成",
        "title": "PDF・資料作成をもっと効率化する仕事道具",
        "lead": "PDF編集、資料整理、文書作成に関連する仕事道具をAmazonで探せます。",
        "query": "PDF 書類整理 仕事道具",
        "query_variants": ["書類整理 ファイル用品", "PDF 資料整理"],
        "cta": "PDF・資料作成の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/pdf"],
    },
    {
        "id": "pdf-workflow-books",
        "enabled": True,
        "category_label": "PDF・資料作成",
        "title": "PDF・資料作成をもっと効率化する本",
        "lead": "PDF編集、資料整理、文書作成に関連する本をAmazonで探せます。",
        "query": "Kindle PDF 仕事効率化",
        "query_variants": ["Kindle 文書管理", "Kindle 書類整理"],
        "cta": "PDF・資料作成の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/pdf"],
    },
    {
        "id": "csv-data-tools",
        "enabled": True,
        "category_label": "Excel・データ整理",
        "title": "Excel・データ整理をもっと効率化する仕事道具",
        "lead": "Excel、CSV、データ整理や業務改善に関連する仕事道具をAmazonで探せます。",
        "query": "Excel CSV データ入力 仕事道具",
        "query_variants": ["Excel テンキー", "表計算 デスク用品"],
        "cta": "Excel・データ整理の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/csv"],
    },
    {
        "id": "csv-excel-books",
        "enabled": True,
        "category_label": "Excel・データ整理",
        "title": "Excel・データ整理を学べる本",
        "lead": "Excel、CSV、データ整理や業務改善に関連する本をAmazonで探せます。",
        "query": "Kindle Excel CSV",
        "query_variants": ["Kindle Excel データ整理", "Kindle 表計算"],
        "cta": "Excel・データ整理の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/csv"],
    },
    {
        "id": "image-batch-tools",
        "enabled": True,
        "category_label": "画像編集・制作",
        "title": "画像の一括整理・制作に役立つ仕事道具",
        "lead": "変換後の画像をまとめて管理しやすくする道具を探せます。",
        "query": "画像 データ整理 仕事道具",
        "query_variants": ["画像保存 ストレージ", "写真整理 仕事道具"],
        "cta": "画像編集・制作の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/image-batch"],
    },
    {
        "id": "image-batch-books",
        "enabled": True,
        "category_label": "画像編集・制作",
        "title": "画像の一括整理・制作を学べる本",
        "lead": "PNG・JPEG・WebPなどの扱い方や画像整理を学べる本を探せます。",
        "query": "Kindle 画像形式 資料作成",
        "query_variants": ["Kindle 画像編集 基本", "Kindle 写真整理"],
        "cta": "画像編集・制作の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/image-batch"],
    },
    {
        "id": "image-compress-tools",
        "enabled": True,
        "category_label": "画像・Web制作",
        "title": "画像軽量化・Web制作に役立つ仕事道具",
        "lead": "圧縮した画像の確認やWeb掲載を進めやすくする道具を探せます。",
        "query": "画像圧縮 Web制作 仕事道具",
        "query_variants": ["Web制作 画像 仕事道具", "画像最適化 ツール 本"],
        "cta": "画像・Web制作の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/image-compress"],
    },
    {
        "id": "image-compress-books",
        "enabled": True,
        "category_label": "画像・Web制作",
        "title": "画像軽量化・Web制作を学べる本",
        "lead": "画質とファイルサイズの考え方やWeb画像の基本を学べる本を探せます。",
        "query": "Kindle 画像最適化 Web",
        "query_variants": ["Kindle Web画像", "Kindle 画像圧縮"],
        "cta": "画像・Web制作の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/image-compress"],
    },
    {
        "id": "image-cleanup-tools",
        "enabled": True,
        "category_label": "画像・EC・資料作成",
        "title": "画像整理・商品画像づくりに役立つ仕事道具",
        "lead": "余白や背景を整えた画像の確認・資料化に役立つ道具を探せます。",
        "query": "商品画像 撮影 仕事道具",
        "query_variants": ["資料画像 撮影 小物", "画像 背景 撮影用品"],
        "cta": "画像整理の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/image-cleanup"],
    },
    {
        "id": "image-cleanup-books",
        "enabled": True,
        "category_label": "画像・EC・資料作成",
        "title": "画像整理・商品画像づくりを学べる本",
        "lead": "背景・余白・見せ方を整える画像補正の基本を学べる本を探せます。",
        "query": "Kindle 画像補正 デザイン",
        "query_variants": ["Kindle 商品画像", "Kindle 画像編集"],
        "cta": "画像整理の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/image-cleanup"],
    },
    {
        "id": "qr-code-tools",
        "enabled": True,
        "category_label": "QR・Web運用",
        "title": "QRコード・販促・Web運用に役立つ仕事道具",
        "lead": "作成したQRコードを掲示物や配布資料で活用する道具を探せます。",
        "query": "QRコード 案内 掲示 仕事道具",
        "query_variants": ["QRコード ラベル 用紙", "案内表示 オフィス用品"],
        "cta": "QR・Web運用の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/qr-code"],
    },
    {
        "id": "qr-code-books",
        "enabled": True,
        "category_label": "QR・Web運用",
        "title": "QRコード・販促・Web運用を学べる本",
        "lead": "店舗案内・資料共有・販促でQRコードを使う方法を学べる本を探せます。",
        "query": "Kindle QRコード 活用",
        "query_variants": ["Kindle QRコード 販促", "Kindle 店舗 集客"],
        "cta": "QR・Web運用の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/qr-code"],
    },
    {
        "id": "seo-web-tools",
        "enabled": True,
        "category_label": "SEO・Web運用",
        "title": "SEO・Web運用を進める仕事道具",
        "lead": "title・meta・OGP・URLの確認作業を進めやすくする道具を探せます。",
        "query": "SEO Web運用 仕事道具",
        "query_variants": ["Webサイト 運用 仕事道具", "SEO チェック 本"],
        "cta": "SEO・Web運用の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/seo"],
    },
    {
        "id": "seo-learning-books",
        "enabled": True,
        "category_label": "SEO・Webマーケティング",
        "title": "SEO・Web運用を学ぶ本",
        "lead": "検索表示やメタ情報、サイト改善の考え方を学べる本を探せます。",
        "query": "Kindle SEO Web運用",
        "query_variants": ["Kindle SEO 入門", "Kindle Webマーケティング"],
        "cta": "SEO・Web運用の関連商品を見る",
        "priority_page_types": ["tool"],
        "priority_path_prefixes": ["/tools/seo"],
    },
]

AMAZON_PURPOSE_GENRES = AMAZON_THEME_POOL

AMAZON_EXACT_PATH_THEME_IDS: Dict[str, Tuple[str, str]] = {
    "/tools/pdf": ("pdf-workflow-tools", "pdf-workflow-books"),
    "/tools/csv": ("csv-data-tools", "csv-excel-books"),
    "/tools/image-batch": ("image-batch-tools", "image-batch-books"),
    "/tools/image-compress": ("image-compress-tools", "image-compress-books"),
    "/tools/image-cleanup": ("image-cleanup-tools", "image-cleanup-books"),
    "/tools/qr-code": ("qr-code-tools", "qr-code-books"),
    "/tools/seo": ("seo-web-tools", "seo-learning-books"),
}

PATH_KEYWORD_RULES: List[Tuple[str, List[str]]] = [
    ("/tools/pdf", ["Kindle PDF 仕事効率化", "PDF 書類整理 文房具", "デスク整理 収納"]),
    ("/guide/pdf", ["Kindle PDF 仕事効率化", "書類整理 文房具", "ビジネス文書 Kindle"]),
    ("/tools/csv", ["Kindle Excel", "Kindle データ分析", "テンキー オフィス用品"]),
    ("/guide/csv", ["Kindle Excel", "Excel 表計算 Kindle", "デスク作業 文房具"]),
    ("/tools/image-cleanup", ["Kindle 画像編集", "撮影 小物 仕事道具", "資料作成 文房具"]),
    ("/tools/image-batch", ["Kindle 画像編集", "資料作成 Kindle", "画像整理 文房具"]),
    ("/tools/image-compress", ["画像 素材整理 仕事道具", "資料作成 デザイン 本", "画像編集 Kindle"]),
    ("/guide/image", ["Kindle 画像編集", "資料作成 Kindle", "撮影 小物 仕事道具"]),
    ("/tools/qr-code", ["文房具 オフィス用品", "書類整理 オフィス用品", "デスク整理 収納"]),
    ("/guide/qr-code", ["文房具 オフィス用品", "資料作成 Kindle", "書類整理 文房具"]),
    ("/tools/seo", ["Kindle SEO", "Kindle Webマーケティング", "SNS運用 Kindle"]),
    ("/guide/seo", ["Kindle SEO", "Kindle Webマーケティング", "文章術 Kindle"]),
    ("/tools", ["Kindle 仕事効率化", "Kindle Excel", "Kindle SEO", "デスク整理 文房具"]),
    ("/blog", ["Kindle Excel", "Kindle 仕事効率化", "文章術 Kindle"]),
    ("/guide", ["Kindle 仕事効率化", "資料作成 Kindle", "デスク整理 収納"]),
    ("/faq", ["Kindle 仕事効率化", "文房具 オフィス用品", "デスク整理 収納"]),
    ("/glossary", ["Kindle 仕事効率化", "Kindle Excel", "Kindle SEO"]),
    ("/contact", ["デスク整理 収納", "文房具 オフィス用品", "Kindle 仕事効率化"]),
]

PAGE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "landing": ["Kindle 仕事効率化", "Kindle Excel", "Kindle SEO", "デスク整理 文房具"],
    "guide": ["Kindle 仕事効率化", "資料作成 Kindle", "文房具 オフィス用品"],
    "tool": ["Kindle Excel", "Kindle SEO", "PDF 書類整理 文房具"],
    "tool_index": ["Kindle 仕事効率化", "Kindle Excel", "Kindle SEO", "デスク整理 文房具"],
    "article": ["Kindle Excel", "Kindle 仕事効率化", "文章術 Kindle"],
    "blog_index": ["Kindle 仕事効率化", "Kindle Excel", "文章術 Kindle"],
    "case_index": ["Kindle 仕事効率化", "デスク整理 文房具", "資料作成 Kindle"],
    "info": ["Kindle 仕事効率化", "文房具 オフィス用品", "デスク整理 収納"],
    "trust_sensitive": ["Kindle 仕事効率化", "文房具 オフィス用品", "デスク整理 収納"],
    "legal": ["Kindle 仕事効率化", "文房具 オフィス用品"],
    "contact": ["文房具 オフィス用品", "デスク整理 収納"],
    "generic": ["Kindle 仕事効率化", "デスク整理 収納", "文房具 オフィス用品"],
}
