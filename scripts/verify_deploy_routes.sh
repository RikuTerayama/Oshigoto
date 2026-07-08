#!/usr/bin/env bash
# 本番デプロイ前ルート検証: 実サーバに対して curl -I を実行し証跡を残す。
# 事前に flask run などでサーバを起動しておくこと。
# 使用例: BASE_URL=http://127.0.0.1:5000 ./scripts/verify_deploy_routes.sh 2>&1 | tee evidence_curl.log

set -e
BASE_URL="${BASE_URL:-http://127.0.0.1:5000}"

echo "=== deploy route verification (curl) ==="
echo "git branch: $(git rev-parse --abbrev-ref HEAD)"
echo "git rev: $(git rev-parse HEAD)"
echo "BASE_URL: $BASE_URL"
echo ""

for path in /tools/seo /tools/csv /guide/csv /tools/minutes /guide/minutes /tools/pdf/; do
  echo "\$ curl -I $BASE_URL$path"
  curl -sI "$BASE_URL$path" || true
  echo ""
done
echo "=== end ==="
