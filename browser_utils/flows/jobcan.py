import asyncio
import uuid
from typing import Optional, Tuple
from playwright.async_api import TimeoutError as PWTimeout, Page

from browser_utils.browser_utils import (
    new_browser, wait_any, navigate_with_retries, 
    mem, guard_memory, save_debug_info
)
from browser_utils.concurrency import browser_sem

# 定数定義
LOGIN_URL = "https://id.jobcan.jp/users/sign_in"
TIMESHEET_URL = "https://ssl.jobcan.jp/employee/attendance"

# ログイン成功判定用セレクタ（OR条件）
TIMESHEET_SELECTORS = [
    "text=出勤簿",
    "#timesheet", 
    "text=ログアウト",
    ".logout-button",
    "a[href*='/employee/attendance']",
    "text=勤怠管理"
]

# 出勤簿ページ確認用セレクタ
TIMESHEET_PAGE_SELECTORS = [
    "#timesheet",
    "text=出勤簿",
    "text=勤怠入力",
    "input[name='date']",
    "input[name='start_time']"
]

class JobcanCredentials:
    """Jobcanの認証情報を保持するクラス"""
    def __init__(self, email: str, password: str, company_id: Optional[str] = None):
        self.email = email
        self.password = password
        self.company_id = company_id

async def do_login_and_go_timesheet(
    creds: JobcanCredentials, 
    session_id: str, 
    optional_company_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Jobcanにログインして出勤簿ページに遷移
    
    Returns:
        Tuple[bool, str]: (成功フラグ, メッセージ)
    """
    # 同時実行制御
    async with browser_sem:
        async with new_browser() as (page, ctx, br):
            mem("start")
            success = False
            message = ""
            
            try:
                # 1) ログインページへ（リトライ付き）
                await navigate_with_retries(
                    page, 
                    LOGIN_URL, 
                    check_ok=lambda p: p.url.startswith(LOGIN_URL)
                )
                guard_memory()
                
                # 2) 認証情報入力
                mem("fill_login START")
                await page.fill('input[name="email"]', creds.email)
                await page.fill('input[name="password"]', creds.password)
                
                # 会社ID欄があれば入力
                company_id_to_use = optional_company_id or creds.company_id
                if company_id_to_use:
                    company_id_input = page.locator('input[name="client_id"]')
                    if await company_id_input.count() > 0:
                        await company_id_input.fill(company_id_to_use)
                        print(f"[info] Company ID filled: {company_id_to_use}")
                
                # ログインボタンクリック
                await page.click('button[type="submit"]')
                mem("fill_login END")
                
                # 3) ログイン後の到達確認（ORセレクタ）
                try:
                    sel = await wait_any(page, selectors=TIMESHEET_SELECTORS, timeout=60000)
                    print(f"[ok] Login succeeded via selector: {sel}")
                except PWTimeout:
                    # ログイン失敗の可能性
                    error_selectors = [
                        "text=メールアドレスまたはパスワードが正しくありません",
                        "text=認証に失敗しました",
                        "text=ログインに失敗しました",
                        ".alert-error",
                        ".error-message"
                    ]
                    
                    for error_sel in error_selectors:
                        if await page.locator(error_sel).count() > 0:
                            error_text = await page.locator(error_sel).first.text_content()
                            raise RuntimeError(f"Login failed: {error_text}")
                    
                    # エラーメッセージが見つからない場合はタイムアウト
                    raise PWTimeout("Login verification timeout - no success or error indicators found")
                
                # 4) 出勤簿ページへ遷移
                async def _is_timesheet_page(p: Page) -> bool:
                    """出勤簿ページかどうかを判定"""
                    try:
                        for sel in TIMESHEET_PAGE_SELECTORS:
                            if await p.locator(sel).count() > 0:
                                return True
                        return False
                    except Exception:
                        return False
                
                try:
                    # 直接URLで遷移を試行
                    await navigate_with_retries(
                        page, 
                        TIMESHEET_URL, 
                        check_ok=_is_timesheet_page, 
                        max_attempts=3
                    )
                except PWTimeout:
                    # 直接URLがダメなら、メニュー遷移にフォールバック
                    print("[info] Direct URL failed, trying menu navigation")
                    
                    # メニューから出勤簿へのリンクを探す
                    menu_selectors = [
                        "a[href*='/employee/attendance']",
                        "text=出勤簿",
                        "text=勤怠管理",
                        "a:has-text('出勤簿')"
                    ]
                    
                    menu_clicked = False
                    for menu_sel in menu_selectors:
                        try:
                            if await page.locator(menu_sel).count() > 0:
                                await page.click(menu_sel, timeout=30000)
                                menu_clicked = True
                                break
                        except Exception:
                            continue
                    
                    if menu_clicked:
                        # 出勤簿ページの読み込みを待機
                        await wait_any(page, TIMESHEET_PAGE_SELECTORS, timeout=60000)
                    else:
                        raise RuntimeError("Could not find navigation menu to timesheet")
                
                # 最終確認：出勤簿ページにいるかチェック
                if not await _is_timesheet_page(page):
                    raise RuntimeError("Failed to reach timesheet page after navigation")
                
                mem("timesheet ready")
                guard_memory()
                
                # 成功フラグを設定
                success = True
                message = "ログインと出勤簿遷移が完了しました"
                
                return success, message
                
            except Exception as e:
                # デバッグ情報を保存
                try:
                    await save_debug_info(page, session_id, "failed")
                except Exception as dump_err:
                    print(f"[dump_error] Failed to save debug info: {dump_err}")
                
                # エラーメッセージを構築
                if isinstance(e, PWTimeout):
                    message = f"タイムアウトエラー: {str(e)}"
                elif isinstance(e, RuntimeError):
                    message = f"実行エラー: {str(e)}"
                else:
                    message = f"予期しないエラー: {type(e).__name__}: {str(e)}"
                
                print(f"[error] Jobcan flow failed: {message}")
                return False, message

async def fill_timesheet_data(
    page: Page, 
    data: list, 
    session_id: str
) -> Tuple[bool, str]:
    """
    出勤簿にデータを入力
    
    Args:
        page: Playwrightのページオブジェクト
        data: 勤怠データのリスト
        session_id: セッションID
    
    Returns:
        Tuple[bool, str]: (成功フラグ, メッセージ)
    """
    try:
        mem("fill_timesheet START")
        
        # データ入力処理（既存のロジックを統合予定）
        # TODO: 既存のautomation.pyの入力ロジックを移植
        
        mem("fill_timesheet END")
        return True, "勤怠データの入力が完了しました"
        
    except Exception as e:
        # デバッグ情報を保存
        try:
            await save_debug_info(page, session_id, "timesheet_failed")
        except Exception as dump_err:
            print(f"[dump_error] Failed to save debug info: {dump_err}")
        
        message = f"勤怠データ入力エラー: {str(e)}"
        print(f"[error] Timesheet fill failed: {message}")
        return False, message
