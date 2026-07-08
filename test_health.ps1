# ヘルスチェックエンドポイント検証スクリプト（PowerShell版）- 503エラー対策版
# Usage: .\test_health.ps1 https://jobcan-automation.onrender.com

param(
    [string]$Domain = "https://jobcan-automation.onrender.com"
)

Write-Host "🔍 ヘルスチェックエンドポイント検証" -ForegroundColor Cyan
Write-Host "Domain: $Domain"
Write-Host ""

# === 基本ヘルスチェック ===
Write-Host "📊 基本ヘルスチェック:" -ForegroundColor Yellow
Write-Host "---"

function Test-Endpoint {
    param([string]$Path, [string]$Name)
    
    try {
        $start = Get-Date
        $response = Invoke-WebRequest -Uri "$Domain$Path" -TimeoutSec 10 -UseBasicParsing
        $end = Get-Date
        $duration = ($end - $start).TotalSeconds
        
        if ($response.StatusCode -eq 200) {
            Write-Host "$Name : ✅ OK ($([math]::Round($duration, 3))s)" -ForegroundColor Green
            return $true
        } else {
            Write-Host "$Name : ❌ FAIL (code: $($response.StatusCode))" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "$Name : ❌ ERROR ($($_.Exception.Message))" -ForegroundColor Red
        return $false
    }
}

Test-Endpoint -Path "/healthz" -Name "/healthz"
Test-Endpoint -Path "/livez" -Name "/livez  "
Test-Endpoint -Path "/readyz" -Name "/readyz "
Test-Endpoint -Path "/ping" -Name "/ping   "

Write-Host ""

# === 連続テスト ===
Write-Host "🔄 連続テスト（100回）:" -ForegroundColor Yellow
Write-Host "---"

$failCount = 0
$totalTime = 0
$times = @()

for ($i = 1; $i -le 100; $i++) {
    try {
        $start = Get-Date
        $response = Invoke-WebRequest -Uri "$Domain/healthz" -TimeoutSec 5 -UseBasicParsing
        $end = Get-Date
        $duration = ($end - $start).TotalSeconds
        $times += $duration
        $totalTime += $duration
        
        if ($response.StatusCode -ne 200) {
            Write-Host "❌ FAIL at request $i (code: $($response.StatusCode))" -ForegroundColor Red
            $failCount++
        }
    } catch {
        Write-Host "❌ FAIL at request $i (error: $($_.Exception.Message))" -ForegroundColor Red
        $failCount++
    }
    
    # プログレス表示（10回ごと）
    if ($i % 10 -eq 0) {
        Write-Host "." -NoNewline
    }
}

Write-Host ""
Write-Host ""

# === 結果サマリ ===
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

