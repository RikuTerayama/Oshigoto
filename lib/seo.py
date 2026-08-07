# -*- coding: utf-8 -*-
"""Shared SEO defaults and helpers for public metadata, breadcrumbs, and schema."""

from copy import deepcopy

SITE_NAME = 'しごと道具箱'
SITE_DESCRIPTION = 'PDF、CSV、画像、ページ確認など、仕事でたまに必要になる作業をまとめた軽量ツール集です。'

SEO_DEFAULTS = {
    '/': {
        'title': 'しごとの小さな面倒を、さっと片づける。 | しごと道具箱',
        'description': SITE_DESCRIPTION,
        'og_type': 'website',
    },
    '/autofill': {
        'title': 'ツール一覧 | しごと道具箱',
        'description': 'しごと道具箱の公開ツール一覧へ移動します。',
        'og_type': 'website',
        'robots': 'noindex,follow',
    },
    '/tools': {
        'title': 'ツール一覧 | しごと道具箱',
        'description': 'PDF、CSV/Excel、画像、SEO/URL確認など、仕事で使う軽量ツールを選べます。',
        'og_type': 'website',
    },
    '/tools/pdf': {'title': 'PDF結合・分割・ページ削除・回転 | しごと道具箱', 'description': 'PDFの結合、抽出、分割、ページ削除、回転、圧縮、画像変換を扱える無料ツールです。ページ削除と回転はブラウザ内で処理します。', 'og_type': 'website'},
    '/tools/csv': {'title': 'CSV/Excelツール | しごと道具箱', 'description': 'CSVとXLSXの変換、文字コード確認、列の整理を手早く進められます。', 'og_type': 'website'},
    '/tools/image-batch': {'title': '画像変換｜JPEG・PNG・WebPを一括変換・リサイズ｜しごと道具箱', 'description': 'JPEG・PNG・WebP画像の形式変換とリサイズをブラウザ内でまとめて実行できます。対応ブラウザでは静止GIF、BMP、AVIFの入力にも対応します。', 'og_type': 'website'},
    '/tools/image-compress': {'title': '画像圧縮｜JPEG・PNG・WebPをブラウザで軽量化｜しごと道具箱', 'description': 'JPEG・PNG・WebP画像の品質やサイズを調整し、ブラウザ内で軽量化できる無料ツールです。圧縮前後の容量を比較し、複数画像はZIPで保存できます。', 'og_type': 'website'},
    '/tools/qr-code': {'title': 'QRコード作成｜URL・テキスト・Wi-FiをブラウザでQR化｜しごと道具箱', 'description': 'URL、テキスト、メール、電話番号、Wi-Fi接続情報からQRコードをブラウザ内で作成し、PNGまたはSVGで保存できます。', 'og_type': 'website'},
    '/tools/image-cleanup': {'title': '画像クリーンアップ | しごと道具箱', 'description': '画像の白背景化、余白、比率を整え、資料に使いやすい画像として出力できます。', 'og_type': 'website'},
    '/tools/seo': {'title': 'SEO/URL確認 | しごと道具箱', 'description': 'OGP、meta、sitemap、robots.txtなど公開ページの基本情報を確認できます。', 'og_type': 'website'},
    '/guide': {'title': 'ガイド | しごと道具箱', 'description': 'PDF、CSV/Excel、画像、SEO/URL確認を迷わず使うためのガイドです。', 'og_type': 'website', 'breadcrumb_title': 'ガイド'},
    '/guide/pdf': {'title': 'PDFツールの使い方 | しごと道具箱', 'description': 'PDFの結合、抽出、分割、ページ削除、回転、圧縮、画像変換、保護付与を使い分けるためのガイドです。', 'og_type': 'article'},
    '/guide/csv': {'title': 'CSV/Excelツールの使い方 | しごと道具箱', 'description': 'CSVとExcelファイルを扱う前に確認したい文字コード、列、変換のポイントをまとめます。', 'og_type': 'article'},
    '/guide/image-batch': {'title': '画像一括変換の使い方 | しごと道具箱', 'description': 'JPEG・PNG・WebPの一括変換と、ブラウザ依存の静止GIF・BMP・AVIF入力を安全に使い分ける方法を説明します。', 'og_type': 'article'},
    '/guide/image-compress': {'title': '画像圧縮の使い方 | しごと道具箱', 'description': 'JPEG・PNG・WebP画像の品質、最大寸法、出力形式を調整し、容量を比較して保存する手順を説明します。', 'og_type': 'article'},
    '/guide/qr-code': {'title': 'QRコード作成の使い方 | しごと道具箱', 'description': 'URL、テキスト、メール、電話番号、Wi-Fi接続情報からQRコードを作り、PNG・SVGで保存する手順と注意点を説明します。', 'og_type': 'article'},
    '/guide/image-cleanup': {'title': '画像クリーンアップの使い方 | しごと道具箱', 'description': '資料に使う画像の白背景化、余白、比率を整える手順をまとめます。', 'og_type': 'article'},
    '/guide/seo': {'title': 'SEO/URL確認の使い方 | しごと道具箱', 'description': '公開前に確認したいOGP、sitemap、robots.txt、meta情報の見方をまとめます。', 'og_type': 'article'},
    '/blog': {'title': 'ブログ | しごと道具箱', 'description': 'PDF、CSV、画像、Web確認など、仕事の小さな作業を軽くするメモを掲載します。', 'og_type': 'website', 'breadcrumb_title': 'ブログ'},
    '/blog/excel-format-mistakes-and-design': {'title': 'CSV/Excelで崩れやすい形式と整え方 | しごと道具箱', 'description': 'CSV/Excelの形式崩れを減らすために、文字コード、日付、列名、空欄の扱いを整理します。', 'og_type': 'article'},
    '/glossary': {'title': '用語集 | しごと道具箱', 'description': 'PDF、CSV、画像、SEO/URL確認でよく出てくる用語を短く整理します。', 'og_type': 'website'},
    '/about': {'title': 'このサイトについて | しごと道具箱', 'description': '仕事でたまに必要になる小さな作業を軽く片づけるための公開ツール集です。', 'og_type': 'website'},
    '/business': {
        'title': '企業向け業務効率化支援｜小さなWebツール・定型作業の自動化｜しごと道具箱',
        'description': 'Excel・CSV、PDF、画像、Web確認などの定型業務を、小規模なWebツールや自動化処理へ落とし込む企業向け支援です。業務整理から試作、検証、導入までご相談いただけます。',
        'og_type': 'website',
        'breadcrumb_title': '企業向け支援',
    },
    '/faq': {'title': 'FAQ | しごと道具箱', 'description': 'しごと道具箱の使い方、ファイル処理、PDF保護、SEO/URL確認、affiliate表示についてのFAQです。', 'og_type': 'website', 'breadcrumb_title': 'FAQ'},
    '/privacy': {'title': 'プライバシーポリシー | しごと道具箱', 'description': 'しごと道具箱のファイル処理、アクセス解析、広告、Cookieの扱いについて説明します。', 'og_type': 'website', 'robots': 'noindex,follow'},
    '/terms': {'title': '利用規約 | しごと道具箱', 'description': 'しごと道具箱を利用する際の注意事項、免責事項、禁止事項について説明します。', 'og_type': 'website', 'robots': 'noindex,follow'},
    '/contact': {'title': 'お問い合わせ | しごと道具箱', 'description': 'しごと道具箱へのお問い合わせ、改善要望、不具合報告はこちらから送れます。', 'og_type': 'website', 'robots': 'noindex,follow'},
    '/sitemap.html': {'title': 'サイトマップ | しごと道具箱', 'description': 'しごと道具箱のHTMLサイトマップです。公開ページと主要ツールへの導線を確認できます。', 'og_type': 'website', 'robots': 'noindex,follow'},
}

NOINDEX_PATHS = frozenset(path for path, config in SEO_DEFAULTS.items() if config.get('robots', '').startswith('noindex'))

TOOL_APPLICATIONS = {
    '/tools/pdf': {'name': 'PDFツール', 'category': 'UtilitiesApplication', 'feature_list': ['PDFの結合、抽出、分割、ページ削除、ページ回転、圧縮、画像変換、保護付与']},
    '/tools/csv': {'name': 'CSV/Excelツール', 'category': 'BusinessApplication', 'feature_list': ['CSVとXLSXの変換、文字コード確認、列整理']},
    '/tools/image-batch': {'name': '画像一括変換', 'category': 'UtilitiesApplication', 'feature_list': ['JPEG・PNG・WebPの形式変換、複数サイズ、リネーム、ZIP保存。追加入力形式とAVIF出力は対応ブラウザのみ']},
    '/tools/image-compress': {'name': '画像圧縮', 'category': 'UtilitiesApplication', 'feature_list': ['JPEG・PNG・WebPの品質調整、リサイズ、容量比較、個別・ZIP保存']},
    '/tools/qr-code': {'name': 'QRコード作成', 'category': 'UtilitiesApplication', 'feature_list': ['URL、テキスト、メール、電話番号、Wi-Fi接続情報からのQRコード作成、PNG・SVG保存']},
    '/tools/image-cleanup': {'name': '画像クリーンアップ', 'category': 'UtilitiesApplication', 'feature_list': ['白背景化、余白調整、比率調整、PNG・JPEG・WebP出力']},
    '/tools/seo': {'name': 'SEO/URL確認', 'category': 'BusinessApplication', 'feature_list': ['OGP、meta、sitemap、robots.txtの確認']},
}

BLOG_ARTICLES = [
    {
        'path': '/blog/excel-format-mistakes-and-design',
        'title': 'CSV/Excelで崩れやすい形式と整え方',
        'description': 'CSV/Excelの形式崩れを減らすために、文字コード、日付、列名、空欄の扱いを整理します。',
        'date_published': '2026-07-10',
        'section': 'CSV/Excel',
    },
]

ARTICLE_SCHEMA_PAGES = {
    article['path']: article for article in BLOG_ARTICLES
}
ARTICLE_SCHEMA_PAGES.update({
    '/guide/pdf': {'title': 'PDFツールの使い方', 'description': SEO_DEFAULTS['/guide/pdf']['description'], 'section': 'ガイド'},
    '/guide/csv': {'title': 'CSV/Excelツールの使い方', 'description': SEO_DEFAULTS['/guide/csv']['description'], 'section': 'ガイド'},
    '/guide/image-batch': {'title': '画像一括変換の使い方', 'description': SEO_DEFAULTS['/guide/image-batch']['description'], 'section': 'ガイド'},
    '/guide/image-compress': {'title': '画像圧縮の使い方', 'description': SEO_DEFAULTS['/guide/image-compress']['description'], 'section': 'ガイド'},
    '/guide/qr-code': {'title': 'QRコード作成の使い方', 'description': SEO_DEFAULTS['/guide/qr-code']['description'], 'section': 'ガイド'},
    '/guide/image-cleanup': {'title': '画像クリーンアップの使い方', 'description': SEO_DEFAULTS['/guide/image-cleanup']['description'], 'section': 'ガイド'},
    '/guide/seo': {'title': 'SEO/URL確認の使い方', 'description': SEO_DEFAULTS['/guide/seo']['description'], 'section': 'ガイド'},
})

RELATED_CONTENT = {
    '/': {'title': 'よく使う道具', 'intro': '必要な作業に合わせてツールを選べます。', 'links': [
        {'path': '/tools/pdf', 'label': 'PDFツール', 'description': '結合、抽出、分割、ページ削除、回転、圧縮、保護付与に対応します。'},
        {'path': '/tools/csv', 'label': 'CSV/Excelツール', 'description': 'CSVとExcelファイルの変換や確認に使えます。'},
        {'path': '/tools/image-batch', 'label': '画像一括変換', 'description': 'JPEG・PNG・WebPの形式変換、複数サイズ、リネームをまとめて行えます。'},
        {'path': '/tools/seo', 'label': 'SEO/URL確認', 'description': 'OGP、meta、sitemap、robots.txtを確認できます。'},
    ]},
    '/blog': {'title': 'あわせて確認する', 'intro': '作業の前後に役立つページです。', 'links': [
        {'path': '/tools', 'label': 'ツール一覧', 'description': '目的別にツールを選べます。'},
        {'path': '/guide', 'label': 'ガイド', 'description': '使い方を手順で確認できます。'},
        {'path': '/glossary', 'label': '用語集', 'description': 'よく出てくる言葉を短く確認できます。'},
        {'path': '/faq', 'label': 'FAQ', 'description': 'よくある質問をまとめています。'},
    ]},
    '/guide': {'title': '次に見るページ', 'intro': '作業に迷ったときの確認先です。', 'links': [
        {'path': '/tools', 'label': 'ツール一覧', 'description': '目的別にツールを選べます。'},
        {'path': '/faq', 'label': 'FAQ', 'description': 'ファイル処理や広告表示の考え方を確認できます。'},
        {'path': '/glossary', 'label': '用語集', 'description': '基本用語を短く確認できます。'},
        {'path': '/blog', 'label': 'ブログ', 'description': '作業メモや考え方を読めます。'},
    ]},
    '/glossary': {'title': '関連するページ', 'intro': '用語を確認したら、実際のツールも使えます。', 'links': [
        {'path': '/guide', 'label': 'ガイド', 'description': '使い方を手順で確認できます。'},
        {'path': '/tools/csv', 'label': 'CSV/Excelツール', 'description': '表データの確認に使えます。'},
        {'path': '/tools/pdf', 'label': 'PDFツール', 'description': 'PDF作業をまとめて扱えます。'},
        {'path': '/tools/seo', 'label': 'SEO/URL確認', 'description': '公開ページの基本情報を確認できます。'},
    ]},
    '/tools': {'title': '迷ったときはこちら', 'intro': '使い方や安全性もあわせて確認できます。', 'links': [
        {'path': '/guide', 'label': 'ガイド', 'description': 'ツールの選び方と使い方を確認できます。'},
        {'path': '/tools/pdf', 'label': 'PDFツール', 'description': 'PDFの結合、ページ削除、回転、圧縮などに使えます。'},
        {'path': '/faq', 'label': 'FAQ', 'description': 'よくある質問を確認できます。'},
        {'path': '/privacy', 'label': 'プライバシーポリシー', 'description': 'ファイル処理と広告表示の考え方を確認できます。'},
    ]},
}

RELATED_CONTENT_PREFIXES = (
    ('/blog/', RELATED_CONTENT['/blog']),
    ('/guide/', RELATED_CONTENT['/guide']),
)


def get_seo_defaults(path):
    config = deepcopy(SEO_DEFAULTS.get(path, {}))
    if 'og_type' not in config:
        config['og_type'] = get_og_type(path)
    if 'robots' not in config:
        config['robots'] = 'index,follow'
    return config


def is_noindex_path(path):
    return path in NOINDEX_PATHS


def get_og_type(path):
    if path.startswith('/blog/') or (path.startswith('/guide/') and path != '/guide'):
        return 'article'
    return 'website'


def get_page_kind(path):
    if path == '/':
        return 'homepage'
    if path in ('/blog', '/guide'):
        return 'collection'
    if path.startswith('/blog/') or (path.startswith('/guide/') and path != '/guide'):
        return 'article'
    if path in ('/faq', '/glossary', '/about'):
        return 'resource'
    if path == '/autofill' or path.startswith('/tools/'):
        return 'tool'
    return 'page'


def build_breadcrumb_items(path, page_title='', breadcrumb_title=''):
    label = (breadcrumb_title or page_title or path.split('/')[-1] or 'ページ').strip()
    items = [{'name': 'ホーム', 'url': '/'}]
    if path == '/':
        return items
    if path == '/tools':
        items.append({'name': 'ツール一覧', 'url': '/tools'})
        return items
    if path.startswith('/tools/'):
        items.extend([{'name': 'ツール一覧', 'url': '/tools'}, {'name': label, 'url': path}])
        return items
    if path == '/guide':
        items.append({'name': 'ガイド', 'url': '/guide'})
        return items
    if path.startswith('/guide/'):
        items.extend([{'name': 'ガイド', 'url': '/guide'}, {'name': label, 'url': path}])
        return items
    if path == '/blog':
        items.append({'name': 'ブログ', 'url': '/blog'})
        return items
    if path.startswith('/blog/'):
        items.extend([{'name': 'ブログ', 'url': '/blog'}, {'name': label, 'url': path}])
        return items
    items.append({'name': label, 'url': path})
    return items


def get_web_application_schema(path, title, description, base_url):
    config = TOOL_APPLICATIONS.get(path)
    if not config:
        return None
    return {
        '@context': 'https://schema.org',
        '@type': 'WebApplication',
        'name': config['name'],
        'url': f'{base_url}{path}',
        'applicationCategory': config['category'],
        'operatingSystem': 'Web Browser',
        'isAccessibleForFree': True,
        'description': description,
        'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'JPY'},
        'featureList': config['feature_list'],
    }


def get_blog_articles(limit=None):
    articles = sorted(BLOG_ARTICLES, key=lambda article: article['date_published'], reverse=True)
    if limit is not None:
        return deepcopy(articles[:limit])
    return deepcopy(articles)


def get_article_schema(path, base_url, default_title='', default_description=''):
    article = ARTICLE_SCHEMA_PAGES.get(path)
    if not article:
        return None
    title = article.get('title') or default_title
    description = article.get('description') or default_description
    url = f'{base_url}{path}'
    schema = {
        '@context': 'https://schema.org',
        '@type': 'Article',
        'headline': title,
        'description': description,
        'inLanguage': 'ja-JP',
        'mainEntityOfPage': {'@type': 'WebPage', '@id': url},
        'url': url,
        'author': {'@type': 'Organization', 'name': SITE_NAME},
        'publisher': {'@type': 'Organization', 'name': SITE_NAME},
    }
    if article.get('date_published'):
        schema['datePublished'] = article['date_published']
        schema['dateModified'] = article.get('date_modified', article['date_published'])
    return schema


def get_related_content(path):
    if path in RELATED_CONTENT:
        return deepcopy(RELATED_CONTENT[path])
    for prefix, config in RELATED_CONTENT_PREFIXES:
        if path.startswith(prefix):
            return deepcopy(config)
    return None
