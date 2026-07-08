#!/bin/bash
# ヘルスチェックエンドポイント検証スクリプト
# Usage: ./test_health.sh https://jobcan-automation.onrender.com

DOMAIN=${1:-"http://localhost:5000"}

echo "🔍 ヘルスチェックエンドポイント検証"
echo "Domain: $DOMAIN"
echo ""

# === 基本ヘルスチェック ===
echo "📊 基本ヘルスチェック:"
echo "---"

echo -n "/healthz: "
response=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" $DOMAIN/healthz)
code=$(echo $response | cut -d'|' -f1)
time=$(echo $response | cut -d'|' -f2)
if [ "$code" = "200" ]; then
    echo "✅ OK (${time}s)"
else
    echo "❌ FAIL (code: $code)"
fi

echo -n "/livez: "
response=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" $DOMAIN/livez)
code=$(echo $response | cut -d'|' -f1)
time=$(echo $response | cut -d'|' -f2)
if [ "$code" = "200" ]; then
    echo "✅ OK (${time}s)"
else
    echo "❌ FAIL (code: $code)"
fi

echo -n "/readyz: "
response=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" $DOMAIN/readyz)
code=$(echo $response | cut -d'|' -f1)
time=$(echo $response | cut -d'|' -f2)
if [ "$code" = "200" ]; then
    echo "✅ OK (${time}s)"
else
    echo "❌ FAIL (code: $code)"
fi

echo -n "/ping: "
response=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" $DOMAIN/ping)
code=$(echo $response | cut -d'|' -f1)
time=$(echo $response | cut -d'|' -f2)
if [ "$code" = "200" ]; then
    echo "✅ OK (${time}s)"
else
    echo "❌ FAIL (code: $code)"
fi

echo ""

# === 連続テスト ===
echo "🔄 連続テスト（100回）:"
echo "---"

fail_count=0
total_time=0

for i in {1..100}; do
    response=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" $DOMAIN/healthz)
    code=$(echo $response | cut -d'|' -f1)
    time=$(echo $response | cut -d'|' -f2)
    
    if [ "$code" != "200" ]; then
        echo "❌ FAIL at request $i (code: $code)"
        ((fail_count++))
    fi
    
    total_time=$(echo "$total_time + $time" | bc)
    
    # プログレス表示（10回ごと）
    if [ $((i % 10)) -eq 0 ]; then
        echo -n "."
    fi
done

echo ""
echo ""

# === 結果サマリ ===
echo "📈 結果サマリ:"
echo "---"

success_rate=$(echo "scale=2; (100 - $fail_count) / 100 * 100" | bc)
avg_time=$(echo "scale=4; $total_time / 100" | bc)

echo "Total requests: 100"
echo "Success: $((100 - fail_count))"
echo "Failed: $fail_count"
echo "Success rate: ${success_rate}%"
echo "Average response time: ${avg_time}s"

echo ""

if [ $fail_count -eq 0 ]; then
    echo "✅ すべてのテストに合格しました！"
    if (( $(echo "$avg_time < 0.1" | bc -l) )); then
        echo "🚀 レスポンスタイムも excellent (<0.1s)"
    elif (( $(echo "$avg_time < 0.5" | bc -l) )); then
        echo "👍 レスポンスタイムは良好 (<0.5s)"
    else
        echo "⚠️  レスポンスタイムがやや遅い (>0.5s) - 要確認"
    fi
else
    echo "❌ テスト失敗: $fail_count 件のエラー"
    echo "🔧 以下を確認してください:"
    echo "   - Renderのデプロイ状況"
    echo "   - メモリ使用率"
    echo "   - Renderログ"
fi

echo ""
echo "🔗 詳細確認:"
echo "   Render Logs: https://dashboard.render.com/"
echo "   UptimeRobot: https://uptimerobot.com/"

