# 緊急遮断・事故時対応 Runbook（Phase 5）

無効トラフィックや AdSense 事故時に、最小手順で「止める」「見える」ための手順。

---

## 1. 広告だけ止める（AdSense 緊急停止）

**目的**: クリック不正疑義や無効トラ検知時に、広告表示だけ即時停止する。

**手順**:
1. Render のダッシュボードで該当サービスを開く。
2. **Environment** で以下を設定する。
   - `ADSENSE_ENABLED` = `false`（未設定の場合は追加して false）
3. **Save Changes** で保存。自動で再デプロイされる。
4. デプロイ完了後、任意のページの **view-source** で `adsbygoogle.js` が含まれていないことを確認する。

**戻し方**: `ADSENSE_ENABLED` を `true` に戻して再デプロイ。

---

## 2. レート制限値の調整

**目的**: ボット連打で 429 が多発している、または一般ユーザーが 429 になりすぎている場合に、制限値を変更する。

**手順**:
1. リポジトリ内 `app.py` を開く。
2. 定数 `_RATE_LIMITS` を検索する（Phase 5 で追加したインメモリレート制限の定義）。
3. 次の値を必要に応じて変更する。
   - `upload`: /upload への POST を何回/分まで許可するか（既定 10）。
   - `status`: /status/* への GET を何回/分まで許可するか（既定 120）。
   - `api`: /api/*（crawl-urls 除く）を何回/分まで許可するか（既定 60）。
4. 変更をコミット・プッシュし、Render で再デプロイする。

**注意**: 緩めすぎると連打対策が弱く、厳しすぎると正常ユーザーが 429 になりやすい。まずは既定値のまま運用し、ログで 429 の頻度を見てから調整することを推奨する。

---

## 3. メンテナンスモード（将来追加する場合）

**現状**: Phase 5 では **メンテナンスモード（全パス 503）は未実装**です。

**将来入れる場合の例**:
- 環境変数 `MAINTENANCE_MODE=true` のとき、before_request の早い段階で 503 を返す。
- 実装する場合は、レート制限の before_request より前で `os.getenv('MAINTENANCE_MODE') == 'true'` を判定し、503 レスポンスを返す。

---

## 4. ログで確認するもの

- **req_start**: `rid`, `method`, `path`, `ip`, `ua`, `ref` が出力される（Phase 5 以降）。異常な UA や同一 IP の短時間連打を追う材料になる。
- **429**: レート制限で弾かれたリクエストは、before_request で 429 を返すため、req_start/req_end は出ない（Flask の before_request で return した場合、以降の before_request とルートは実行されない）。429 の多発は Render のログで「429 を返した」事実は残らないため、必要なら 429 返却時に logger で 1 行出す改修を検討する。

---

## 5. 関連ドキュメント

- 無効トラ対策の棚卸し: `docs/invalid_traffic_audit_report.md`
- 実装バックログ: `docs/invalid_traffic_backlog.tsv`
- Phase 5 実装ログ: `docs/status-reports/2026-02-13_phase5_invalid_traffic_implementation.md`
