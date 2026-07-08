"""
P1-1: 実行時メトリクス計測ユーティリティ

循環importを避けるため、app.pyとautomation.pyの両方から安全にimport可能な独立モジュール。
メモリ使用量、ブラウザインスタンス数、ジョブ数などの計測ログを出力する。
"""

import os
import time
import threading
import logging

logger = logging.getLogger(__name__)

# P1-1: スレッドセーフなカウンタ
_browser_active_count = 0
_browser_count_lock = threading.Lock()

_job_active_count = 0
_job_count_lock = threading.Lock()


def increment_browser_count():
    """ブラウザ起動数をインクリメント"""
    global _browser_active_count
    with _browser_count_lock:
        _browser_active_count += 1
        logger.info(f"browser_count increment count={_browser_active_count}")


def decrement_browser_count():
    """ブラウザ終了数をデクリメント"""
    global _browser_active_count
    with _browser_count_lock:
        _browser_active_count = max(0, _browser_active_count - 1)
        logger.info(f"browser_count decrement count={_browser_active_count}")


def get_browser_count():
    """現在のブラウザ起動数を取得"""
    with _browser_count_lock:
        return _browser_active_count


def increment_job_count():
    """アクティブジョブ数をインクリメント"""
    global _job_active_count
    with _job_count_lock:
        _job_active_count += 1
        logger.info(f"job_count increment count={_job_active_count}")


def decrement_job_count():
    """アクティブジョブ数をデクリメント"""
    global _job_active_count
    with _job_count_lock:
        _job_active_count = max(0, _job_active_count - 1)
        logger.info(f"job_count decrement count={_job_active_count}")


def get_job_count():
    """現在のアクティブジョブ数を取得"""
    with _job_count_lock:
        return _job_active_count


def log_memory(tag, job_id=None, session_id=None, extra=None):
    """
    P1-1: メモリ使用量と関連メトリクスをログ出力
    
    Args:
        tag: 計測ポイントのタグ（例: "upload_done", "excel_before", "browser_start"）
        job_id: ジョブID（オプション）
        session_id: セッションID（オプション）
        extra: 追加情報の辞書（オプション）
    """
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        rss_mb = memory_info.rss / 1024 / 1024
    except (ImportError, Exception):
        rss_mb = 0
    
    # jobs数とsessions数は外部から取得する必要があるため、extraで渡す
    jobs_count = extra.get('jobs_count', 0) if extra else 0
    sessions_count = extra.get('sessions_count', 0) if extra else 0
    browser_count = get_browser_count()
    
    # 主要env変数を取得
    web_concurrency = os.getenv('WEB_CONCURRENCY', 'unknown')
    web_threads = os.getenv('WEB_THREADS', 'unknown')
    max_active_sessions = os.getenv('MAX_ACTIVE_SESSIONS', 'unknown')
    memory_limit_mb = os.getenv('MEMORY_LIMIT_MB', 'unknown')
    memory_warning_mb = os.getenv('MEMORY_WARNING_MB', 'unknown')
    
    # ログメッセージを構築
    log_parts = [
        f"memory_check tag={tag}",
        f"rss_mb={rss_mb:.1f}",
        f"jobs_count={jobs_count}",
        f"sessions_count={sessions_count}",
        f"browser_count={browser_count}",
        f"env_WEB_CONCURRENCY={web_concurrency}",
        f"env_WEB_THREADS={web_threads}",
        f"env_MAX_ACTIVE_SESSIONS={max_active_sessions}",
        f"env_MEMORY_LIMIT_MB={memory_limit_mb}",
        f"env_MEMORY_WARNING_MB={memory_warning_mb}"
    ]
    
    if job_id:
        log_parts.append(f"job_id={job_id}")
    if session_id:
        log_parts.append(f"session_id={session_id}")
    
    if extra:
        for key, value in extra.items():
            if key not in ('jobs_count', 'sessions_count'):  # 既に出力済み
                log_parts.append(f"{key}={value}")
    
    logger.info(" ".join(log_parts))
