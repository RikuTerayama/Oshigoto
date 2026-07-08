# ヘルスチェックエンドポイント検証スクリプト（PowerShell版）- 503エラー対策版
# Usage: .\test_health_fixed.ps1 https://jobcan-automation.onrender.com

param(
    [string]$Domain = "https://jobcan-automation.onrender.com"
)

Write-Host "🔍 ヘルスチェックエンドポイント検証" -ForegroundColor Cyan
Write-Host "Domain: $Domain"
Write-Host ""

# テストするエンドポイント
$endpoints = @(
    @{Path="/healthz"; Name="Render Health Check"; ExpectedStatus=200},
    @{Path="/livez"; Name="Process Liveness"; ExpectedStatus=200},
    @{Path="/readyz"; Name="Readiness Check"; ExpectedStatus=200},
    @{Path="/ping"; Name="UptimeRobot Monitor"; ExpectedStatus=200},
    @{Path="/"; Name="Main Page"; ExpectedStatus=200}
)

$totalTests = $endpoints.Count
$successCount = 0
$failCount = 0
$times = @()

Write-Host "🧪 基本ヘルスチェックテスト:" -ForegroundColor Yellow
Write-Host "---"

foreach ($endpoint in $endpoints) {
    $url = "$Domain$($endpoint.Path)"
    Write-Host -NoNewline "Testing $($endpoint.Name) ($($endpoint.Path))... "
    
    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 30 -UseBasicParsing
        $stopwatch.Stop()
        
        $responseTime = $stopwatch.Elapsed.TotalSeconds
        $times += $responseTime
        
        if ($response.StatusCode -eq $endpoint.ExpectedStatus) {
            Write-Host "✅ OK (${responseTime}s)" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "❌ FAIL - Expected $($endpoint.ExpectedStatus), got $($response.StatusCode)" -ForegroundColor Red
            $failCount++
        }
    } catch {
        Write-Host "❌ ERROR - $($_.Exception.Message)" -ForegroundColor Red
        $failCount++
    }
}

Write-Host ""
Write-Host "📊 基本テスト結果: $successCount/$totalTests 成功" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Red" })

if ($failCount -gt 0) {
    Write-Host "⚠️  基本テストでエラーが発生しました。詳細を確認してください。" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "🔧 トラブルシューティング:" -ForegroundColor Cyan
    Write-Host "1. Render Dashboard でログを確認"
    Write-Host "2. メモリ使用率を確認"
    Write-Host "3. デプロイ状況を確認"
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "🚀 連続負荷テスト (100リクエスト):" -ForegroundColor Yellow
Write-Host "---"

# 連続テスト用のカウンターをリセット
$successCount = 0
$failCount = 0
$times = @()

for ($i = 1; $i -le 100; $i++) {
    $url = "$Domain/healthz"
    
    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 10 -UseBasicParsing
        $stopwatch.Stop()
        
        $responseTime = $stopwatch.Elapsed.TotalSeconds
        $times += $responseTime
        
        if ($response.StatusCode -eq 200) {
            $successCount++
        } else {
            $failCount++
        }
        
        # 進捗表示（10回ごと）
        if ($i % 10 -eq 0) {
            Write-Host "Progress: $i/100 (Success: $successCount, Failed: $failCount)" -ForegroundColor Cyan
        }
        
        # 短い間隔でリクエスト
        Start-Sleep -Milliseconds 100
        
    } catch {
        $failCount++
        if ($i % 10 -eq 0) {
            Write-Host "Progress: $i/100 (Success: $successCount, Failed: $failCount)" -ForegroundColor Cyan
        }
    }
}

Write-Host ""
Write-Host "📈 結果サマリ:" -ForegroundColor Yellow
Write-Host "---"

$successRate = [math]::Round((100 - $failCount) / 100 * 100, 2)
$avgTime = if ($times.Count -gt 0) { [math]::Round(($times | Measure-Object -Average).Average, 4) } else { 0 }
$p95Time = if ($times.Count -gt 0) { [math]::Round(($times | Sort-Object)[[math]::Floor($times.Count * 0.95)], 4) } else { 0 }

Write-Host "Total requests: 100"
Write-Host "Success: $(100 - $failCount)"
Write-Host "Failed: $failCount"
Write-Host "Success rate: ${successRate}%"
Write-Host "Average response time: ${avgTime}s"
Write-Host "p95 response time: ${p95Time}s"

Write-Host ""

if ($failCount -eq 0) {
    Write-Host "✅ すべてのテストに合格しました！" -ForegroundColor Green
    if ($avgTime -lt 0.1) {
        Write-Host "🚀 レスポンスタイムも excellent (<0.1s)" -ForegroundColor Green
    } elseif ($avgTime -lt 0.5) {
        Write-Host "👍 レスポンスタイムは良好 (<0.5s)" -ForegroundColor Green
    } else {
        Write-Host "⚠️  レスポンスタイムがやや遅い (>0.5s) - 要確認" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ テスト失敗: $failCount 件のエラー" -ForegroundColor Red
    Write-Host "🔧 以下を確認してください:" -ForegroundColor Yellow
    Write-Host "   - Renderのデプロイ状況"
    Write-Host "   - メモリ使用率"
    Write-Host "   - Renderログ"
}

Write-Host ""
Write-Host "🔗 詳細確認:" -ForegroundColor Cyan
Write-Host "   Render Logs: https://dashboard.render.com/"
Write-Host "   UptimeRobot: https://uptimerobot.com/"
