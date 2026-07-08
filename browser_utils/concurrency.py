import os
import asyncio

# 環境変数から同時実行数を取得（デフォルトは1で直列実行）
_conc = int(os.getenv("BROWSER_CONCURRENCY", "1"))
browser_sem = asyncio.Semaphore(_conc)

def get_concurrency_limit():
    """現在の同時実行制限を返す"""
    return _conc

def is_serial_execution():
    """直列実行モードかどうかを返す"""
    return _conc == 1
