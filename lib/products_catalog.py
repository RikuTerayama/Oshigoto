# -*- coding: utf-8 -*-
"""Public tool catalog for しごと道具箱."""

PUBLIC_TOOL_IDS = ('pdf', 'csv', 'image-batch', 'image-compress', 'image-cleanup', 'seo')

PRODUCTS = [
    {
        'id': 'pdf',
        'name': 'PDFツール',
        'description': 'PDFの結合、抽出、分割、ページ削除、回転、圧縮、画像変換、保護付与をまとめて扱えます。',
        'path': '/tools/pdf',
        'guide_path': '/guide/pdf',
        'status': 'available',
        'icon': 'PDF',
        'category': '書類',
        'tags': ['PDF', '書類'],
        'features': ['結合', '抽出', '分割', 'ページ削除', 'ページ回転', '圧縮', '画像変換', '保護付与'],
    },
    {
        'id': 'csv',
        'name': 'CSV/Excelツール',
        'description': 'CSVとXLSXの変換、文字コード確認、重複削除、列整理をブラウザで進められます。',
        'path': '/tools/csv',
        'guide_path': '/guide/csv',
        'status': 'available',
        'icon': 'CSV',
        'category': '表',
        'tags': ['CSV', 'Excel', '表'],
        'features': ['CSV/XLSX変換', '文字コード確認', '重複削除', '列整理'],
    },
    {
        'id': 'image-batch',
        'name': '画像一括変換',
        'description': 'PNG、JPG、WebPなどの画像形式変換とリサイズをまとめて実行できます。',
        'path': '/tools/image-batch',
        'guide_path': '/guide/image-batch',
        'status': 'available',
        'icon': 'IMG',
        'category': '画像',
        'tags': ['画像', '変換'],
        'features': ['形式変換', 'リサイズ', '一括処理'],
    },
    {
        'id': 'image-compress',
        'name': '画像圧縮',
        'description': 'JPEG、PNG、WebPの品質やサイズを調整し、圧縮前後の容量を比較できます。',
        'path': '/tools/image-compress',
        'guide_path': '/guide/image-compress',
        'status': 'available',
        'icon': 'CMP',
        'category': '画像',
        'tags': ['画像', '圧縮', '軽量化'],
        'features': ['品質調整', 'リサイズ', '容量比較', 'ZIP保存'],
    },
    {
        'id': 'image-cleanup',
        'name': '画像クリーンアップ',
        'description': '余白や背景を整え、資料に使いやすいPNG画像として出力できます。',
        'path': '/tools/image-cleanup',
        'guide_path': '/guide/image-cleanup',
        'status': 'available',
        'icon': 'CLR',
        'category': '画像',
        'tags': ['画像', '整える'],
        'features': ['余白調整', '背景整理', 'PNG出力'],
    },
    {
        'id': 'seo',
        'name': 'SEO/URL確認',
        'description': 'title、meta、OGP、sitemap、robots.txtなど公開ページの基本情報を確認できます。',
        'path': '/tools/seo',
        'guide_path': '/guide/seo',
        'status': 'available',
        'icon': 'SEO',
        'category': 'Web確認',
        'tags': ['SEO', 'URL', 'Web確認'],
        'features': ['title確認', 'meta確認', 'OGP確認', 'sitemap確認'],
    },
]


def get_public_products():
    by_id = {p['id']: p for p in PRODUCTS if p.get('status') == 'available'}
    return [by_id[tool_id] for tool_id in PUBLIC_TOOL_IDS if tool_id in by_id]
