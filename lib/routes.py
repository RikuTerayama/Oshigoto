# -*- coding: utf-8 -*-
"""Small route helpers for the public site."""
from lib.products_catalog import PRODUCTS, get_public_products

BASE_URL = 'https://oshigoto.onrender.com'

NAV_ITEMS = [
    {'name': 'Home', 'path': '/', 'icon': ''},
    {'name': 'Tools', 'path': '/tools', 'icon': ''},
    {'name': 'Guide', 'path': '/guide', 'icon': ''},
    {'name': 'Blog', 'path': '/blog', 'icon': ''},
]


def get_product_by_id(product_id):
    for product in PRODUCTS:
        if product['id'] == product_id:
            return product
    return None


def get_product_by_path(path):
    for product in PRODUCTS:
        if product['path'] == path:
            return product
    return None


def get_available_products():
    return get_public_products()


def get_coming_soon_products():
    return []
