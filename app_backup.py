import os
import uuid
import threading
from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime
import time

# カスタムモジュールをインポート
from jobcan_automation import JobcanAutomation
from utils import load_excel_data, allowed_file, ensure_playwright_browser

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# アップロードフォルダが存在しない場合は作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# アプリケーション起動時のログ
print("🚀 Jobcan自動化アプリケーションを初期化中...")
print(f"🔧 環境変数 PORT: {os.environ.get('PORT', '5000')}")
print(f"🔧 環境変数 RAILWAY_ENVIRONMENT: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
print("✅ アプリケーションの初期化が完了しました")

# グローバル変数
jobs = {}

def add_job_log(job_id: str, message: str):
    """ジョブログを追加"""
    if job_id not in jobs:
        jobs[job_id] = {
            'status': 'pending',
            'logs': [],
            'diagnosis': {},
            'start_time': datetime.now().isoformat(),
            'progress': {
                'current_step': 0,
                'total_steps': 0,
                'current_data': 0,
                'total_data': 0
            }
        }
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    jobs[job_id]['logs'].append(f"[{timestamp}] {message}")
    print(f"[{job_id}] {message}")
    
    # 進捗情報を更新
    if "ステップ" in message:
        if "ステップ1" in message:
            jobs[job_id]['progress']['current_step'] = 1
        elif "ステップ2" in message:
            jobs[job_id]['progress']['current_step'] = 2
        elif "ステップ3" in message:
            jobs[job_id]['progress']['current_step'] = 3
        elif "ステップ4" in message:
            jobs[job_id]['progress']['current_step'] = 4
        elif "ステップ5" in message:
            jobs[job_id]['progress']['current_step'] = 5
        elif "ステップ6" in message:
            jobs[job_id]['progress']['current_step'] = 6

def get_job_logs(job_id: str):
    """ジョブログを取得"""
    return jobs.get(job_id, {}).get('logs', [])

def get_job_progress(job_id: str):
    """ジョブ進捗を取得"""
    return jobs.get(job_id, {}).get('progress', {})

def add_job_diagnosis(job_id: str, diagnosis_data: dict):
    """ジョブ診断データを追加"""
    if job_id not in jobs:
        jobs[job_id] = {
            'status': 'pending',
            'logs': [],
            'diagnosis': {},
            'start_time': datetime.now().isoformat()
        }
    
    jobs[job_id]['diagnosis'] = diagnosis_data

def get_job_diagnosis(job_id: str):
    """ジョブ診断データを取得"""
    return jobs.get(job_id, {}).get('diagnosis', {})

def run_automation(job_id: str, email: str, password: str, file_path: str):
    """自動化を実行"""
    try:
        add_job_log(job_id, "🔄 自動化処理を開始中...")
        add_job_log(job_id, f"🔧 引数確認 - job_id: {job_id}, email: {email[:3]}***, file_path: {file_path}")
        
        # ファイルの存在確認
        if not os.path.exists(file_path):
            add_job_log(job_id, f"❌ ファイルが存在しません: {file_path}")
            jobs[job_id]['status'] = 'error'
            return False
        
        add_job_log(job_id, f"✅ ファイルが存在します: {file_path}")
        
        # メモリ使用量の確認
        memory_info = psutil.virtual_memory()
        add_job_log(job_id, f"🔧 メモリ使用量: {memory_info.percent}% ({memory_info.available // (1024**3)} GB 利用可能)")
        
        result = process_jobcan_automation(job_id, email, password, file_path)
        add_job_log(job_id, f"✅ 自動化処理が完了しました: {result}")
        return result
        
    except Exception as e:
        error_msg = f"❌ 自動化処理でエラーが発生しました: {e}"
        add_job_log(job_id, error_msg)
        add_job_log(job_id, f"🔧 エラーの詳細: {type(e).__name__}")
        add_job_log(job_id, f"🔧 エラーメッセージ: {str(e)}")
        
        # エラーの詳細情報をログに出力
        import traceback
        error_traceback = traceback.format_exc()
        add_job_log(job_id, f"🔧 エラートレースバック: {error_traceback}")
        
        jobs[job_id]['status'] = 'error'
        return False

def process_jobcan_automation(job_id: str, email: str, password: str, file_path: str):
    """Jobcan自動化処理（同期版）"""
    try:
        add_job_log(job_id, "=== Jobcan自動化を開始します ===")
        jobs[job_id]['status'] = 'running'
        
        # Railway環境の情報をログに出力
        add_job_log(job_id, f"🔧 実行環境: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
        add_job_log(job_id, f"🔧 Python バージョン: {os.sys.version}")
        
        # Playwrightブラウザを確保
        add_job_log(job_id, "🔧 Playwrightブラウザを確保中...")
        try:
            browser_result = ensure_playwright_browser()
            if browser_result:
                add_job_log(job_id, "✅ Playwrightブラウザの確保が完了しました")
            else:
                add_job_log(job_id, "⚠️ Playwrightブラウザの確保に問題がありましたが、続行します")
        except Exception as browser_error:
            add_job_log(job_id, f"⚠️ Playwrightブラウザの確保でエラー: {browser_error}")
            add_job_log(job_id, "🔄 ブラウザの確保をスキップして続行します")
        
        # Railway環境での追加情報をログに出力
        add_job_log(job_id, f"🔧 現在のディレクトリ: {os.getcwd()}")
        add_job_log(job_id, f"🔧 利用可能なメモリ: {psutil.virtual_memory().available // (1024**3)} GB")
        add_job_log(job_id, f"🔧 CPU使用率: {psutil.cpu_percent()}%")
        add_job_log(job_id, f"🔧 総メモリ: {psutil.virtual_memory().total // (1024**3)} GB")
        add_job_log(job_id, f"🔧 メモリ使用率: {psutil.virtual_memory().percent}%")
        
        # 環境変数の確認
        add_job_log(job_id, f"🔧 RAILWAY_ENVIRONMENT: {os.environ.get('RAILWAY_ENVIRONMENT', '未設定')}")
        add_job_log(job_id, f"🔧 PORT: {os.environ.get('PORT', '未設定')}")
        add_job_log(job_id, f"🔧 NODE_ENV: {os.environ.get('NODE_ENV', '未設定')}")
        add_job_log(job_id, f"🔧 PYTHONPATH: {os.environ.get('PYTHONPATH', '未設定')}")
        add_job_log(job_id, f"🔧 PATH: {os.environ.get('PATH', '未設定')[:200]}...")
        
        # システム情報の詳細確認
        try:
            import platform
            add_job_log(job_id, f"🔧 OS: {platform.system()} {platform.release()}")
            add_job_log(job_id, f"🔧 アーキテクチャ: {platform.machine()}")
            add_job_log(job_id, f"🔧 Python実行パス: {sys.executable}")
        except Exception as e:
            add_job_log(job_id, f"⚠️ システム情報の取得でエラー: {e}")
        
        # Playwrightの利用可能性をチェック
        try:
            from playwright.sync_api import sync_playwright
            add_job_log(job_id, "✅ Playwrightモジュールが利用可能です")
        except ImportError as e:
            add_job_log(job_id, f"❌ Playwrightモジュールのインポートに失敗: {e}")
            jobs[job_id]['status'] = 'error'
            return False
        
        # システムのブラウザの存在をチェック
        try:
            import subprocess
            browsers_to_check = [
                '/usr/bin/chromium-browser',
                '/usr/bin/google-chrome',
                '/usr/bin/chromium',
                '/usr/bin/firefox',
                '/usr/bin/chrome',
                '/snap/bin/chromium'
            ]
            
            for browser_path in browsers_to_check:
                try:
                    result = subprocess.run(['which', browser_path], capture_output=True, text=True)
                    if result.returncode == 0:
                        add_job_log(job_id, f"✅ システムブラウザが見つかりました: {browser_path}")
                    else:
                        add_job_log(job_id, f"❌ システムブラウザが見つかりません: {browser_path}")
                except Exception as browser_check_error:
                    add_job_log(job_id, f"⚠️ ブラウザチェックでエラー: {browser_check_error}")
        except Exception as e:
            add_job_log(job_id, f"⚠️ システムブラウザのチェックでエラー: {e}")
        
        # Playwrightのインストール状況をチェック
        try:
            import subprocess
            result = subprocess.run([sys.executable, '-m', 'playwright', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                add_job_log(job_id, f"✅ Playwrightバージョン: {result.stdout.strip()}")
            else:
                add_job_log(job_id, f"❌ Playwrightのバージョン確認に失敗: {result.stderr}")
        except Exception as e:
            add_job_log(job_id, f"⚠️ Playwrightのバージョン確認でエラー: {e}")
        
        # 自動化インスタンスを作成
        add_job_log(job_id, "🤖 自動化インスタンスを作成中...")
        try:
            automation = JobcanAutomation(headless=True)
            add_job_log(job_id, "✅ 自動化インスタンスの作成が完了しました")
        except Exception as automation_error:
            add_job_log(job_id, f"❌ 自動化インスタンスの作成に失敗: {automation_error}")
            add_job_log(job_id, f"🔧 エラーの詳細: {type(automation_error).__name__}")
            add_job_log(job_id, f"🔧 エラーメッセージ: {str(automation_error)}")
            
            # エラーの詳細情報をログに出力
            import traceback
            error_traceback = traceback.format_exc()
            add_job_log(job_id, f"🔧 エラートレースバック: {error_traceback}")
            
            jobs[job_id]['status'] = 'error'
            return False
        
        try:
            # ブラウザを起動
            add_job_log(job_id, "🌐 ブラウザを起動中...")
            try:
                automation.start_browser()
                add_job_log(job_id, "✅ ブラウザの起動が完了しました")
            except Exception as browser_start_error:
                add_job_log(job_id, f"❌ ブラウザの起動に失敗: {browser_start_error}")
                add_job_log(job_id, f"🔧 エラーの詳細: {type(browser_start_error).__name__}")
                add_job_log(job_id, f"🔧 エラーメッセージ: {str(browser_start_error)}")
                
                # Railway環境での追加情報をログに出力
                try:
                    import subprocess
                    browsers_to_check = ['chromium', 'chromium-browser', 'google-chrome', 'firefox', 'chrome']
                    for browser in browsers_to_check:
                        result = subprocess.run(['which', browser], capture_output=True, text=True)
                        add_job_log(job_id, f"🔧 {browser}の場所: {result.stdout.strip() if result.stdout else '見つかりません'}")
                    
                    # Playwrightのブラウザインストール状況をチェック
                    result = subprocess.run([sys.executable, '-m', 'playwright', 'install', '--dry-run'], 
                                          capture_output=True, text=True)
                    add_job_log(job_id, f"🔧 Playwrightブラウザインストール状況: {result.stdout.strip() if result.stdout else result.stderr}")
                except Exception as e:
                    add_job_log(job_id, f"🔧 ブラウザの場所確認でエラー: {e}")
                
                jobs[job_id]['status'] = 'error'
                return False
            
            # Jobcanにログイン
            add_job_log(job_id, "🔐 Jobcanにログイン中...")
            try:
                login_success = automation.login_to_jobcan(email, password)
                
                if not login_success:
                    add_job_log(job_id, "❌ ログインに失敗しました")
                    jobs[job_id]['status'] = 'error'
                    return False
                
                add_job_log(job_id, "✅ ログインに成功しました")
            except Exception as login_error:
                add_job_log(job_id, f"❌ ログイン処理でエラー: {login_error}")
                jobs[job_id]['status'] = 'error'
                return False
            
            # 勤怠ページに移動
            add_job_log(job_id, "📊 勤怠ページに移動中...")
            try:
                automation.navigate_to_attendance()
                add_job_log(job_id, "✅ 勤怠ページへの移動が完了しました")
            except Exception as navigation_error:
                add_job_log(job_id, f"❌ 勤怠ページへの移動に失敗: {navigation_error}")
                jobs[job_id]['status'] = 'error'
                return False
            
            # Excelファイルを読み込み
            add_job_log(job_id, "📁 Excelファイルを読み込み中...")
            try:
                data = load_excel_data(file_path)
                
                if not data:
                    add_job_log(job_id, "❌ Excelファイルの読み込みに失敗しました")
                    jobs[job_id]['status'] = 'error'
                    return False
                
                # 進捗情報を更新
                jobs[job_id]['progress']['total_data'] = len(data)
                add_job_log(job_id, f"📊 処理対象データ数: {len(data)}")
                
                # 勤怠データを処理
                add_job_log(job_id, "🔄 勤怠データを処理中...")
                processed_data = automation.process_attendance_data(data)
                
            except Exception as data_error:
                add_job_log(job_id, f"❌ データ処理でエラー: {data_error}")
                jobs[job_id]['status'] = 'error'
                return False
            
            # 結果を分析
            try:
                success_count = len([d for d in processed_data if d.get('status') == 'success'])
                error_count = len(processed_data) - success_count
                
                add_job_log(job_id, f"✅ 処理が完了しました")
                add_job_log(job_id, f"📊 成功: {success_count}件, 失敗: {error_count}件")
                jobs[job_id]['status'] = 'completed'
                return True
                
            except Exception as analysis_error:
                add_job_log(job_id, f"❌ 結果分析でエラー: {analysis_error}")
                jobs[job_id]['status'] = 'error'
                return False
            
        except Exception as process_error:
            add_job_log(job_id, f"❌ 処理中にエラーが発生: {process_error}")
            add_job_log(job_id, f"🔧 エラーの詳細: {type(process_error).__name__}")
            add_job_log(job_id, f"🔧 エラーメッセージ: {str(process_error)}")
            
            # エラーの詳細情報をログに出力
            import traceback
            error_traceback = traceback.format_exc()
            add_job_log(job_id, f"🔧 エラートレースバック: {error_traceback}")
            
            jobs[job_id]['status'] = 'error'
            return False
        finally:
            # ブラウザを閉じる
            try:
                add_job_log(job_id, "🔒 ブラウザを閉じています...")
                automation.close()
                add_job_log(job_id, "✅ ブラウザを正常に閉じました")
            except Exception as close_error:
                add_job_log(job_id, f"⚠️ ブラウザの終了でエラー: {close_error}")
                add_job_log(job_id, f"🔧 終了エラーの詳細: {type(close_error).__name__}")
                add_job_log(job_id, f"🔧 終了エラーメッセージ: {str(close_error)}")
            
    except Exception as e:
        error_msg = f"❌ 予期しないエラーが発生しました: {e}"
        add_job_log(job_id, error_msg)
        add_job_log(job_id, f"🔧 予期しないエラーの詳細: {type(e).__name__}")
        add_job_log(job_id, f"🔧 予期しないエラーメッセージ: {str(e)}")
        
        # 予期しないエラーの詳細情報をログに出力
        import traceback
        error_traceback = traceback.format_exc()
        add_job_log(job_id, f"🔧 予期しないエラートレースバック: {error_traceback}")
        
        jobs[job_id]['status'] = 'error'
        return False

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """ファイルアップロード処理"""
    try:
        # フォームデータを取得
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'メールアドレスとパスワードを入力してください'
            })
        
        # ファイルが存在するかチェック
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'ファイルが選択されていません'
            })
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'ファイルが選択されていません'
            })
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Excelファイル（.xlsx）を選択してください'
            })
        
        # ファイルを保存
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # ジョブIDを生成
        job_id = str(uuid.uuid4())
        
        # ジョブを開始
        add_job_log(job_id, "アップロード処理を開始")
        
        # バックグラウンドで処理を実行
        try:
            add_job_log(job_id, "🔄 バックグラウンド処理を開始中...")
            
            # スレッド作成前の詳細ログ
            add_job_log(job_id, f"🔧 スレッド作成前のメモリ使用量: {psutil.virtual_memory().percent}%")
            add_job_log(job_id, f"🔧 現在のプロセス数: {len(psutil.pids())}")
            
            thread = threading.Thread(
                target=run_automation,
                args=(job_id, email, password, file_path)
            )
            thread.daemon = True
            
            add_job_log(job_id, "🔄 スレッドを開始中...")
            thread.start()
            
            add_job_log(job_id, "✅ バックグラウンド処理を開始しました")
            
        except Exception as e:
            error_msg = f"❌ バックグラウンド処理の開始に失敗: {e}"
            add_job_log(job_id, error_msg)
            add_job_log(job_id, f"🔧 エラーの詳細: {type(e).__name__}")
            add_job_log(job_id, f"🔧 エラーメッセージ: {str(e)}")
            
            # エラーの詳細情報をログに出力
            import traceback
            error_traceback = traceback.format_exc()
            add_job_log(job_id, f"🔧 エラートレースバック: {error_traceback}")
            
            return jsonify({
                'success': False,
                'error': error_msg
            })
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': '処理を開始しました。進捗は下記で確認できます。'
        })
        
    except Exception as e:
        error_msg = f"アップロード処理でエラーが発生しました: {e}"
        return jsonify({
            'success': False,
            'error': error_msg
        })

@app.route('/status/<job_id>')
def get_status(job_id):
    """ジョブステータスを取得"""
    try:
        job_data = jobs.get(job_id, {})
        return jsonify({
            'status': job_data.get('status', 'not_found'),
            'logs': job_data.get('logs', []),
            'diagnosis': job_data.get('diagnosis', {}),
            'progress': job_data.get('progress', {}),
            'start_time': job_data.get('start_time', ''),
            'current_time': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/')
def root():
    """ルートエンドポイント（起動確認用）"""
    try:
        return jsonify({
            'status': 'running',
            'message': 'Jobcan Automation Service',
            'timestamp': time.time(),
            'port': os.environ.get('PORT', 'N/A'),
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local'),
            'health_check': '/health',
            'detailed_health': '/health/detailed'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/health')
def health_check():
    """ヘルスチェックエンドポイント（最適化版）"""
    try:
        # 最小限のチェックのみ実行
        return jsonify({
            'status': 'healthy',
            'message': 'Service is running',
            'timestamp': time.time(),
            'port': os.environ.get('PORT', '5000'),
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local')
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/ping')
def ping():
    """シンプルなpingエンドポイント"""
    return "pong"

@app.route('/health/detailed')
def detailed_health_check():
    """詳細ヘルスチェックエンドポイント"""
    try:
        # 詳細なシステム情報を取得
        import psutil
        import os
        
        system_info = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'python_version': os.sys.version,
            'memory_usage': psutil.virtual_memory().percent,
            'cpu_usage': psutil.cpu_percent(),
            'disk_usage': psutil.disk_usage('/').percent,
            'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'local'),
            'port': os.environ.get('PORT', '5000'),
            'uptime': 'running'
        }
        
        return jsonify(system_info)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# アプリケーション初期化ログ（Railway環境対応）
try:
    print(f"🚀 アプリケーションを初期化中...")
    print(f"🔧 環境: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
    print(f"🔧 Python バージョン: {os.sys.version}")
    print(f"🔧 ポート: {os.environ.get('PORT', '5000')}")
    print(f"🔧 作業ディレクトリ: {os.getcwd()}")
    print(f"🔧 環境変数: PORT={os.environ.get('PORT', 'N/A')}, RAILWAY_ENVIRONMENT={os.environ.get('RAILWAY_ENVIRONMENT', 'N/A')}")
    print(f"🔧 プロセスID: {os.getpid()}")
    print(f"🔧 メモリ使用量: {psutil.virtual_memory().percent}%")
    print(f"✅ アプリケーション初期化完了")
except Exception as e:
    print(f"❌ アプリケーション初期化でエラー: {e}")
    import traceback
    traceback.print_exc()

# アプリケーション起動確認
@app.before_first_request
def before_first_request():
    """最初のリクエスト前の処理"""
    try:
        print(f"🌐 最初のリクエストを受信しました")
        print(f"🔧 現在のポート: {os.environ.get('PORT', 'N/A')}")
        print(f"🔧 アプリケーションが正常に起動しています")
        print(f"🔧 プロセスID: {os.getpid()}")
        print(f"🔧 メモリ使用量: {psutil.virtual_memory().percent}%")
    except Exception as e:
        print(f"❌ 最初のリクエスト処理でエラー: {e}")
        import traceback
        traceback.print_exc()

# アプリケーション起動時のログ
@app.before_request
def before_request():
    """各リクエスト前の処理"""
    try:
        print(f"📝 リクエスト受信: {request.path}")
    except Exception as e:
        print(f"❌ リクエスト処理でエラー: {e}")

if __name__ == '__main__':
    try:
        # 開発環境ではデバッグモードで実行
        debug_mode = os.environ.get('FLASK_ENV') == 'development'
        port = int(os.environ.get('PORT', 5000))
        
        print(f"🚀 アプリケーションを起動中...")
        print(f"🔧 ポート: {port}")
        print(f"🔧 デバッグモード: {debug_mode}")
        print(f"🔧 環境: {os.environ.get('RAILWAY_ENVIRONMENT', 'local')}")
        print(f"🔧 Python バージョン: {os.sys.version}")
        
        # アプリケーションが正常に起動したことを確認
        print(f"✅ アプリケーションが正常に起動しました")
        print(f"✅ ヘルスチェックエンドポイント: http://localhost:{port}/health")
        
        app.run(host='0.0.0.0', port=port, debug=debug_mode)
    except Exception as e:
        print(f"❌ アプリケーション起動でエラー: {e}")
        import traceback
        traceback.print_exc() 
