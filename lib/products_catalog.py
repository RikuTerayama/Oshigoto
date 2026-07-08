# -*- coding: utf-8 -*-
"""
製品カタログ（外部依存なし・LP/context_processor 用）。
playwright 等の重い import に巻き込まれないよう、このモジュールには import を一切置かない。
"""
# Public版「しごと道具箱」で表側に出すツール。
# Jobcan AutoFill本体は次Phaseまで残すが、公開導線ではこの5件だけを主役にする。
PUBLIC_TOOL_IDS = ('pdf', 'csv', 'image-batch', 'image-cleanup', 'seo')


def get_public_products():
    by_id = {
        product.get('id'): product for product in PRODUCTS
        if isinstance(product, dict)
        and product.get('status') == 'available'
        and product.get('id') in PUBLIC_TOOL_IDS
    }
    return [by_id[product_id] for product_id in PUBLIC_TOOL_IDS if product_id in by_id]


# 製品一覧（lib.routes と同期が必要な場合は lib.routes から参照する形に変更可）
PRODUCTS = [
    {
        'id': 'autofill',
        'name': 'Jobcan AutoFill',
        'description': 'Jobcanへの勤怠データをExcelから一括入力。月次締め作業を大幅に短縮します。',
        'path': '/autofill',
        'guide_path': '/guide/autofill',
        'status': 'available',
        'icon': '🕒',
        'category': 'attendance'
    },
    {
        'id': 'image-batch',
        'name': '画像一括変換',
        'description': 'png/jpg/webpの一括変換、リサイズ、品質圧縮、複数サイズ同時出力。ローカル処理でアップロード不要。',
        'path': '/tools/image-batch',
        'guide_path': '/guide/image-batch',
        'status': 'available',
        'icon': '🖼️',
        'category': 'image',
        'tags': ['File', 'Image'],
        'features': ['複数サイズ同時出力', 'プリセット', '品質調整'],
        'capabilities': [
            'PNG、JPG、WebP形式の画像を一括変換',
            '複数サイズ（バリアント）を同時出力',
            'リサイズ・品質圧縮・形式変換を一度に処理',
            'SNS/Web/EC用のプリセット設定',
            'ブラウザ内で完結し、サーバーにアップロードしない'
        ],
        'recommended_for': [
            'ECサイト運営者（商品画像の最適化）',
            'Webデザイナー（複数サイズの一括生成）',
            'SNS運用担当者（投稿用画像のリサイズ）',
            'マーケター（広告素材の最適化）'
        ],
        'usage_steps': [
            '画像ファイルをドラッグ&ドロップまたは選択',
            '出力サイズ（バリアント）と形式を設定',
            'プリセットを選択（オプション）',
            '変換を実行',
            '変換後の画像をダウンロード'
        ],
        'constraints': [
            '対応形式: PNG、JPG、WebP（最大50ファイル、1ファイル20MB、合計200MBまで）',
            'ブラウザ内処理のため、大量ファイルは時間がかかる場合があります',
            '処理はローカルで完結し、サーバーには送信されません'
        ],
        'faq': [
            {'q': '複数サイズを同時に出力できますか？', 'a': 'はい、バリアント機能で複数のサイズを一度に変換できます。'},
            {'q': 'サーバーに画像がアップロードされますか？', 'a': 'いいえ、すべてブラウザ内で処理され、サーバーには送信されません。'},
            {'q': '対応していない形式はありますか？', 'a': 'PNG、JPG、WebP以外の形式（GIF、BMP等）には対応していません。'}
        ]
    },
    {
        'id': 'pdf',
        'name': 'PDFユーティリティ',
        'description': 'PDFの結合・分割・ページ抽出、PDF→画像zip変換、圧縮、画像→PDF変換。ローカル処理でアップロード不要。',
        'path': '/tools/pdf',
        'guide_path': '/guide/pdf',
        'status': 'available',
        'icon': '📄',
        'category': 'document',
        'tags': ['File', 'PDF'],
        'features': ['結合・分割', '圧縮', '画像変換'],
        'capabilities': [
            '複数のPDFファイルを1つに結合',
            'PDFを指定ページで分割',
            '特定ページを抽出',
            'PDFを画像（PNG/JPEG）に変換',
            'PDFを圧縮してファイルサイズを削減',
            '画像ファイルをPDFに変換'
        ],
        'recommended_for': [
            '事務職（複数PDFの統合・整理）',
            'デザイナー（PDFから画像への変換）',
            '営業担当（資料の圧縮・分割）',
            '経理担当（請求書の結合・整理）'
        ],
        'usage_steps': [
            'PDFファイルをアップロード',
            '操作モードを選択（結合・分割・抽出・変換等）',
            '設定を調整（ページ範囲、品質等）',
            '処理を実行',
            '結果をダウンロード'
        ],
        'constraints': [
            '操作により異なります。PDF（結合・分割・抽出・圧縮）は最大20ファイル、PDF→画像は10ファイル。1ファイル50MB、合計300MB。画像→PDFは最大100ファイル、1ファイル20MB、合計200MBまで。',
            'ブラウザ内処理のため、大きなファイルは時間がかかる場合があります',
            '処理はローカルで完結し、サーバーには送信されません'
        ],
        'faq': [
            {'q': '複数のPDFを結合できますか？', 'a': 'はい、複数のPDFファイルを1つのPDFに結合できます。最大20ファイルまでです。'},
            {'q': 'PDFを画像に変換できますか？', 'a': 'はい、PDFをPNGまたはJPEG形式の画像に変換できます。PDF→画像は最大10ファイルまでです。'},
            {'q': 'サーバーにPDFがアップロードされますか？', 'a': 'いいえ、すべてブラウザ内で処理され、サーバーには送信されません。'}
        ]
    },
    {
        'id': 'image-cleanup',
        'name': '画像ユーティリティ',
        'description': '透過→白背景JPEG変換、余白トリム、縦横比統一、背景除去。ローカル処理でアップロード不要。',
        'path': '/tools/image-cleanup',
        'guide_path': '/guide/image-cleanup',
        'status': 'available',
        'icon': '✨',
        'category': 'image',
        'tags': ['File', 'Image'],
        'features': ['背景除去', '余白トリム', '縦横比統一'],
        'capabilities': [
            '透過PNGを白背景JPEGに変換',
            '画像の余白を自動トリミング',
            '縦横比を統一（1:1、4:5、16:9等）',
            '背景を除去（自動検出）',
            '複数画像を一括処理'
        ],
        'recommended_for': [
            'ECサイト運営者（商品画像の統一）',
            'SNS運用担当者（投稿画像の整形）',
            'デザイナー（画像の前処理）',
            'マーケター（広告素材の統一）'
        ],
        'usage_steps': [
            '画像ファイルをアップロード',
            '処理モードを選択（背景除去・余白トリム・縦横比統一等）',
            '設定を調整（しきい値、縦横比等）',
            '処理を実行',
            '変換後の画像をダウンロード'
        ],
        'constraints': [
            '通常は最大50ファイル、背景除去時は20ファイル。1ファイル20MB。合計は通常200MB、背景除去時100MBまで。',
            '背景除去は自動検出のため、複雑な背景は完全に除去できない場合があります',
            '処理はローカルで完結し、サーバーには送信されません'
        ],
        'faq': [
            {'q': '透過PNGを白背景に変換できますか？', 'a': 'はい、透過PNGを白背景のJPEGに変換できます。'},
            {'q': '背景除去は自動でできますか？', 'a': 'はい、自動検出機能で背景を除去できます。'},
            {'q': 'サーバーに画像がアップロードされますか？', 'a': 'いいえ、すべてブラウザ内で処理され、サーバーには送信されません。'}
        ]
    },
    {
        'id': 'seo',
        'name': 'Web/SEOユーティリティ',
        'description': 'OGP画像ジェネレーター、PageSpeedチェックリスト、メタタグ検査、sitemap.xml/robots.txt生成。ローカル処理でアップロード不要。',
        'path': '/tools/seo',
        'guide_path': '/guide/seo',
        'status': 'available',
        'icon': '🔍',
        'category': 'web',
        'tags': ['Web', 'SEO'],
        'features': ['OGP生成', 'メタタグ検査', 'sitemap生成'],
        'capabilities': [
            'OGP画像を自動生成',
            'PageSpeed改善チェックリストを生成',
            'メタタグを検査・検証',
            'sitemap.xml/robots.txtを生成',
            'SEO最適化のためのチェックリスト作成'
        ],
        'recommended_for': [
            'Webマスター（SEO最適化）',
            'Webデザイナー（OGP画像生成）',
            'マーケター（SNS共有最適化）',
            '開発者（サイト構造の最適化）'
        ],
        'usage_steps': [
            '機能を選択（OGP生成・PageSpeedチェック・メタタグ検査・sitemap生成）',
            '必要な情報を入力',
            '処理を実行',
            '結果を確認・ダウンロード'
        ],
        'constraints': [
            'OGP画像生成はブラウザ内で完結します',
            'メタタグ検査はHTMLを貼り付けるか、URLを入力（CORS制約あり）',
            '処理はローカルで完結し、サーバーには送信されません'
        ],
        'faq': [
            {'q': 'OGP画像を自動生成できますか？', 'a': 'はい、タイトルとサブタイトルからOGP画像を自動生成できます。'},
            {'q': 'sitemap.xmlを生成できますか？', 'a': 'はい、sitemap.xmlとrobots.txtを生成できます。'},
            {'q': 'サーバーにデータがアップロードされますか？', 'a': 'いいえ、すべてブラウザ内で処理され、サーバーには送信されません。'}
        ]
    },
    {
        'id': 'csv',
        'name': 'CSV/Excelユーティリティ',
        'description': 'CSVの文字コード変換、CSV⇄XLSX変換、重複削除、列の抽出・並べ替え、分割。ブラウザ内処理でアップロード不要。',
        'path': '/tools/csv',
        'guide_path': '/guide/csv',
        'status': 'available',
        'icon': '📊',
        'category': 'data',
        'tags': ['File', 'CSV', 'Excel'],
        'features': ['文字コード変換', 'CSV⇄XLSX', '重複削除', '列操作', '分割'],
        'capabilities': [
            'CSVの文字コード変換（Shift-JIS/UTF-8）',
            'CSVとXLSXの相互変換',
            'キー列指定での重複削除',
            '列の抽出・並べ替え・ヘッダ名置換',
            'N行ごと・列値ごとの分割'
        ],
        'recommended_for': [
            '事務職（CSV/Excelの整形）',
            'データ分析担当（前処理）',
            '営業担当（名簿の重複削除）'
        ],
        'usage_steps': [
            'CSVまたはExcelファイルを選択',
            '操作モードを選択',
            'オプションを設定',
            '処理を実行',
            '結果をダウンロード'
        ],
        'constraints': [
            '対応形式: CSV、XLSX（最大10ファイル、1ファイル10MB、合計50MBまで）',
            '処理はブラウザ内で完結し、サーバーには送信されません'
        ],
        'faq': [
            {'q': 'サーバーにファイルがアップロードされますか？', 'a': 'いいえ。すべてブラウザ内で処理され、ファイルはサーバーに送信されません。'},
            {'q': 'Shift-JISのCSVに対応していますか？', 'a': 'はい。入力文字コードでShift-JISを選択できます。'},
            {'q': 'Excel形式で出力できますか？', 'a': 'はい。CSV→XLSX変換でExcel形式でダウンロードできます。'}
        ]
    }
]
