"""
トップページの簡易テスト
Flask test clientを使用して、トップページが200を返すことを確認
"""
import pytest
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

@pytest.fixture
def client():
    """Flask test clientを作成"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_returns_200(client):
    """トップページ（/）が200を返すことを確認"""
    response = client.get('/')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # レスポンスボディにエラーページ固有の文言が含まれないことを確認
    body = response.data.decode('utf-8')
    assert '⚠️ エラーが発生しました' not in body, "Error page should not be displayed"
    assert 'よくあるエラーと対処法' not in body, "Error page content should not be displayed"
    
    # 正常なランディングページのコンテンツが含まれることを確認
    assert '業務効率化ツール集' in body or '製品一覧' in body, "Landing page content should be present"

def test_index_returns_html(client):
    """トップページがHTMLを返すことを確認"""
    response = client.get('/')
    assert response.status_code == 200
    assert 'text/html' in response.content_type

def test_404_returns_404(client):
    """存在しないページが404を返すことを確認"""
    response = client.get('/this-page-does-not-exist')
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    # エラーページが表示されることを確認
    body = response.data.decode('utf-8')
    assert '⚠️ エラーが発生しました' in body, "Error page should be displayed for 404"
    assert 'エラーID' in body, "Error ID should be displayed"

def test_tools_returns_200(client):
    """/tools が200を返すことを確認"""
    response = client.get('/tools')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

def test_autofill_returns_200(client):
    """/autofill が200を返すことを確認"""
    response = client.get('/autofill')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

def test_about_returns_200(client):
    """/about が200を返すことを確認"""
    response = client.get('/about')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

def test_healthz_returns_200(client):
    """/healthz が常に200を返すことを確認"""
    response = client.get('/healthz')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

def test_smoke_multiple_requests_200(client):
    """/, /autofill, /about を複数回アクセスして全て200かつエラー表示が出ないこと"""
    paths = ['/', '/autofill', '/about', '/tools']
    error_phrase = '⚠️ エラーが発生しました'
    for path in paths:
        for i in range(3):
            response = client.get(path)
            assert response.status_code == 200, f"path={path} run={i+1} status={response.status_code}"
            body = response.data.decode('utf-8')
            assert error_phrase not in body, f"path={path} run={i+1} showed error page"

if __name__ == '__main__':
    # pytestがインストールされていない場合のフォールバック
    client = app.test_client()
    
    print("Testing / endpoint...")
    response = client.get('/')
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        body = response.data.decode('utf-8')
        if '⚠️ エラーが発生しました' not in body:
            print("✓ / returns 200 and shows landing page")
        else:
            print("✗ / returns 200 but shows error page")
    else:
        print(f"✗ / returns {response.status_code}")
    
    print("\nTesting /this-page-does-not-exist endpoint...")
    response = client.get('/this-page-does-not-exist')
    print(f"Status: {response.status_code}")
    if response.status_code == 404:
        print("✓ 404 returns correct status")
    else:
        print(f"✗ Expected 404, got {response.status_code}")
