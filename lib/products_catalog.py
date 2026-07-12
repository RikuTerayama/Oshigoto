# -*- coding: utf-8 -*-
"""Public tool catalog for しごと道具箱."""

PUBLIC_TOOL_IDS = ('pdf', 'csv', 'image-batch', 'image-cleanup', 'seo')

PRODUCTS = [
    {
        'id': 'pdf',
        'name': 'PDFツール',
        'description': 'PDFの結合、分割、抽出、圧縮、画像変換、保護付与をまとめて扱えます。',
        'path': '/tools/pdf',
        'guide_path': '/guide/pdf',
        'status': 'available',
        'icon': 'PDF',
        'category': 'document',
        'tags': ['File', 'PDF'],
        'features': ['結合', '分割', '圧縮', '保護付与'],
    },
    {
        'id': 'csv',
        'name': 'CSV/Excelツール',
        'description': 'CSVとXLSXの変換、文字コード確認、列の整理をブラウザで手早く進められます。',
        'path': '/tools/csv',
        'guide_path': '/guide/csv',
        'status': 'available',
        'icon': 'CSV',
        'category': 'data',
        'tags': ['File', 'CSV', 'Excel'],
        'features': ['CSV/XLSX変換', '文字コード確認', '列整理'],
    },
    {
        'id': 'image-batch',
        'name': '画像一括変換',
        'description': 'PNG、JPG、WebPなどの画像形式変換とリサイズをまとめて実行できます。',
        'path': '/tools/image-batch',
        'guide_path': '/guide/image-batch',
        'status': 'available',
        'icon': 'IMG',
        'category': 'image',
        'tags': ['File', 'Image'],
        'features': ['形式変換', 'リサイズ', '一括処理'],
    },
    {
        'id': 'image-cleanup',
        'name': '画像クリーンアップ',
        'description': '余白や背景を整え、資料に使いやすいPNG画像として出力できます。',
        'path': '/tools/image-cleanup',
        'guide_path': '/guide/image-cleanup',
        'status': 'available',
        'icon': 'CLR',
        'category': 'image',
        'tags': ['File', 'Image'],
        'features': ['余白調整', '背景整理', 'PNG出力'],
    },
    {
        'id': 'seo',
        'name': 'SEO/URL確認',
        'description': 'OGP、meta、sitemap、robots.txtなど公開ページの基本情報を確認できます。',
        'path': '/tools/seo',
        'guide_path': '/guide/seo',
        'status': 'available',
        'icon': 'SEO',
        'category': 'web',
        'tags': ['Web', 'SEO'],
        'features': ['OGP確認', 'meta確認', 'sitemap確認'],
    },
]


def get_public_products():
    by_id = {p['id']: p for p in PRODUCTS if p.get('status') == 'available'}
    return [by_id[tool_id] for tool_id in PUBLIC_TOOL_IDS if tool_id in by_id]
