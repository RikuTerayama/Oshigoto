# -*- coding: utf-8 -*-
"""
Shared navigation and footer link definitions.
Keep labels in UTF-8 so common layout text stays stable across pages.
"""
try:
    from lib.products_catalog import get_public_products
except Exception:
    get_public_products = lambda: []


def get_nav_sections():
    """
    Build header navigation sections.
    Each child entry is either a flat link list or grouped items for dropdowns.
    """
    products = get_public_products()

    tool_links = [{'name': 'すべてのツール', 'path': '/tools', 'icon': ''}]
    for p in products:
        tool_links.append({
            'name': p.get('name', ''),
            'path': p.get('path', '#'),
            'icon': p.get('icon', ''),
        })

    tool_guide_items = []
    for p in products:
        guide_path = p.get('guide_path') or ''
        if guide_path:
            tool_guide_items.append({
                'name': p.get('name', ''),
                'path': guide_path,
                'icon': p.get('icon', ''),
            })

    guide_links = []
    if tool_guide_items:
        guide_links.append({'group_label': 'ツール別ガイド', 'items': tool_guide_items})
    guide_links.append({'name': 'ガイド一覧', 'path': '/guide', 'icon': ''})

    resource_links = [
        {'name': 'よくある質問', 'path': '/faq', 'icon': ''},
        {'name': '用語集', 'path': '/glossary', 'icon': ''},
        {'name': 'ベストプラクティス', 'path': '/best-practices', 'icon': ''},
        {'name': 'ブログ', 'path': '/blog', 'icon': ''},
        {'name': 'サイトについて', 'path': '/about', 'icon': ''},
        {'name': 'サイトマップ', 'path': '/sitemap.html', 'icon': ''},
        {'name': 'プライバシーポリシー', 'path': '/privacy', 'icon': ''},
        {'name': '利用規約', 'path': '/terms', 'icon': ''},
        {'name': 'お問い合わせ', 'path': '/contact', 'icon': ''},
    ]

    return [
        {'id': 'home', 'label': 'ホーム', 'path': '/', 'children': None},
        {'id': 'tools', 'label': 'ツール', 'path': '/tools', 'children': tool_links},
        {'id': 'guide', 'label': 'ガイド', 'path': '/guide', 'children': guide_links},
        {'id': 'resource', 'label': 'リソース', 'path': '/faq', 'children': resource_links},
    ]


def get_nav_sections_fallback():
    """Fallback navigation used when PRODUCTS cannot be read."""
    return [
        {'id': 'home', 'label': 'ホーム', 'path': '/', 'children': None},
        {'id': 'tools', 'label': 'ツール', 'path': '/tools', 'children': [{'name': '道具箱一覧', 'path': '/tools', 'icon': ''}]},
        {'id': 'guide', 'label': 'ガイド', 'path': '/guide', 'children': [
            {'name': 'ガイド一覧', 'path': '/guide', 'icon': ''}
        ]},
        {'id': 'resource', 'label': 'リソース', 'path': '/faq', 'children': [
            {'name': 'よくある質問', 'path': '/faq', 'icon': ''},
            {'name': '用語集', 'path': '/glossary', 'icon': ''},
            {'name': 'ベストプラクティス', 'path': '/best-practices', 'icon': ''},
            {'name': 'ブログ', 'path': '/blog', 'icon': ''},
            {'name': 'サイトについて', 'path': '/about', 'icon': ''},
            {'name': 'サイトマップ', 'path': '/sitemap.html', 'icon': ''},
            {'name': 'プライバシーポリシー', 'path': '/privacy', 'icon': ''},
            {'name': '利用規約', 'path': '/terms', 'icon': ''},
            {'name': 'お問い合わせ', 'path': '/contact', 'icon': ''},
        ]},
    ]


def get_footer_columns():
    """Footer columns for tools, guides, resources, and legal pages."""
    products = get_public_products()

    tool_links = [{'name': '道具箱一覧', 'path': '/tools'}]
    for p in products:
        tool_links.append({'name': p.get('name', ''), 'path': p.get('path', '#'), 'icon': p.get('icon', '')})

    guide_links = [
        {'name': 'ガイド一覧', 'path': '/guide'},
    ]
    for p in products:
        guide_path = p.get('guide_path') or ''
        if guide_path:
            guide_links.append({'name': p.get('name', ''), 'path': guide_path, 'icon': p.get('icon', '')})

    return [
        {'title': 'ツール一覧', 'links': tool_links},
        {'title': 'ガイド', 'links': guide_links},
        {'title': 'リソース', 'links': [
            {'name': 'よくある質問', 'path': '/faq'},
            {'name': '用語集', 'path': '/glossary'},
            {'name': 'ベストプラクティス', 'path': '/best-practices'},
            {'name': 'ブログ', 'path': '/blog'},
            {'name': 'サイトについて', 'path': '/about'},
            {'name': 'サイトマップ', 'path': '/sitemap.html'},
        ]},
        {'title': '法務情報', 'links': [
            {'name': 'プライバシーポリシー', 'path': '/privacy'},
            {'name': '利用規約', 'path': '/terms'},
            {'name': 'お問い合わせ', 'path': '/contact'},
        ]},
    ]
