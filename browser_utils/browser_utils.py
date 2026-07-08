import os
import gc
import time
import psutil
import asyncio
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# 環境変数から設定値を取得（デフォルト値付き）
NAV_TIMEOUT_MS = int(os.getenv("NAV_TIMEOUT_MS", "90000"))
STEP_TIMEOUT_MS = int(os.getenv("STEP_TIMEOUT_MS", "60000"))
MAX_MEM_MB = int(os.getenv("MAX_MEM_MB", "450"))

# 重いアセットの拡張子とブロックするホスト
HEAVY_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", 
                  ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".webm", ".avi")
BLOCK_HOSTS = ("googletagmanager.com", "google-analytics.com", "doubleclick.net", 
               "facebook.com", "twitter.com", "instagram.com")

def rss_mb():
    """現在のプロセスのRSSメモリ使用量をMBで返す"""
    try:
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except:
        return 0

def mem(tag):
    """重要ステップでメモリ使用量をログ出力"""
    print(f"[mem] {tag}: rss={rss_mb():.1f} MiB")

def guard_memory():
    """メモリ使用量が閾値を超えた場合に例外を発生"""
    current_mem = rss_mb()
    if current_mem > MAX_MEM_MB:
        raise RuntimeError(f"Memory guard tripped: {current_mem:.1f} MiB > {MAX_MEM_MB} MiB")

async def block_heavy_assets(route):
    """重いアセットとトラッキングスクリプトをブロック"""
    url = route.request.url
    if url.endswith(HEAVY_SUFFIXES) or any(h in url for h in BLOCK_HOSTS):
        await route.abort()
    else:
        await route.continue_()

async def wait_any(page, selectors: list[str], timeout=STEP_TIMEOUT_MS):
    """複数セレクタのOR待ち（いずれかが見つかるまで待機）"""
    start = time.time()
    while (time.time() - start) * 1000 < timeout:
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible():
                    return sel
            except Exception:
                pass
        await asyncio.sleep(0.2)
    
    # タイムアウト時は最後にセレクタの存在確認を試行
    for sel in selectors:
        try:
            if await page.locator(sel).count() > 0:
                return sel
        except Exception:
            pass
    
    raise PWTimeout(f"wait_any timeout after {timeout}ms: {selectors}")

async def navigate_with_retries(page, url, check_ok, max_attempts=3):
    """ナビゲーションの再試行付き実行"""
    for i in range(1, max_attempts + 1):
        mem(f"goto[{i}] before")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            
            # ネットワークアイドル状態を待機（一部サイトは常時通信のため失敗は無視）
            try:
                await page.wait_for_load_state("networkidle", timeout=STEP_TIMEOUT_MS)
            except Exception:
                pass
            
            if await check_ok(page):
                mem(f"goto[{i}] ok")
                return
                
        except PWTimeout:
            print(f"[warn] Navigation attempt {i} timed out: {url}")
            pass
        
        # リトライ準備：軽いreload
        if i < max_attempts:
            try:
                await page.reload(timeout=NAV_TIMEOUT_MS)
            except Exception:
                pass
    
    raise PWTimeout(f"navigate_with_retries failed after {max_attempts} attempts: {url}")

@asynccontextmanager
async def new_browser():
    """Playwrightブラウザの起動と軽量化設定"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",
                "--disable-javascript-harmony-shipping",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-field-trial-config",
                "--disable-ipc-flooding-protection"
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        page.set_default_timeout(STEP_TIMEOUT_MS)
        page.set_default_navigation_timeout(NAV_TIMEOUT_MS)
        
        # 重いアセットをブロック
        await page.route("**/*", block_heavy_assets)
        
        try:
            yield page, context, browser
        finally:
            # 確実にリソースを解放
            try:
                await page.close()
            except Exception:
                pass
            try:
                await context.close()
            except Exception:
                pass
            try:
                await browser.close()
            except Exception:
                pass
            
            # ガベージコレクション
            gc.collect()
            mem("browser_closed")

async def save_debug_info(page, session_id, error_type="failed"):
    """デバッグ情報（スクリーンショット、HTML）を保存"""
    try:
        # logsディレクトリが存在しない場合は作成
        os.makedirs("logs", exist_ok=True)
        
        # スクリーンショット保存
        screenshot_path = f"logs/{error_type}_{session_id}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        
        # HTML保存
        html_path = f"logs/{error_type}_{session_id}.html"
        html_content = await page.content()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"[debug] Saved debug info: {screenshot_path}, {html_path}")
        return screenshot_path, html_path
        
    except Exception as e:
        print(f"[debug_error] Failed to save debug info: {e}")
        return None, None
