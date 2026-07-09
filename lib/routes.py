# -*- coding: utf-8 -*-
"""
ルート定義と製品情報を管理するモジュール。
製品一覧は lib.products_catalog から参照し、重い import に巻き込まれないようにする。
"""
from lib.products_catalog import PRODUCTS

# ベースURL
BASE_URL = 'https://oshigoto.onrender.com'

# ナビゲーション項目
NAV_ITEMS = [
    {'name': 'Home', 'path': '/', 'icon': '🏠'},
    {'name': 'AutoFill', 'path': '/autofill', 'icon': '🕒'},
    {'name': 'Tools', 'path': '/tools', 'icon': '🛠️'},
    {'name': 'Guide', 'path': '/guide/getting-started', 'icon': '📚'},
]

def get_product_by_id(product_id):
    """製品IDから製品情報を取得"""
    for product in PRODUCTS:
        if product['id'] == product_id:
            return product
    return None

def get_product_by_path(path):
    """パスから製品情報を取得"""
    for product in PRODUCTS:
        if product['path'] == path:
            return product
    return None

def get_available_products():
    """利用可能な製品一覧を取得"""
    return [p for p in PRODUCTS if p['status'] == 'available']

def get_coming_soon_products():
    """準備中の製品一覧を取得"""
    return [p for p in PRODUCTS if p['status'] == 'coming-soon']
