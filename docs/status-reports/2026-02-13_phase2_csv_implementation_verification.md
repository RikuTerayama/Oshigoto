# Phase 2 CSV 実装・検証メモ

**日付**: 2026-02-13  
**対象**: /tools/csv のみ（P1/P2 最小差分実装）

## 実装内容（5コミット相当）

1. **fix(csv): eliminate innerHTML for file lists** — rejected と fileList を ul/li + textContent に変更。
2. **fix(csv): show user-facing error when deps fail** — change リスナーを try/catch、checkDeps() で FileValidation/FileUtils/CsvOps/ZipUtils/Papa/XLSX/Encoding/JSZip をチェック。欠けていれば runBtn/fileInput 無効化とメッセージ表示（textContent）。
3. **fix(csv): prevent double run and improve running UI** — isRunning フラグ、クリック時 disabled + 「処理中...」、finally で復旧。
4. **refactor(csv): render output and preview using textContent** — setOutput と renderPreview を createElement + textContent に変更。
5. **docs(csv): clarify no file upload with analytics note** — ページヘッダに「ファイル内容はサーバーに送信しません。計測・広告のために外部サービス（Google等）へ通信することがあります。」を1行追加。

## 自動検証

| コマンド | 結果 |
|----------|------|
| `python scripts/smoke_test.py --deploy` | exit 0 |
| `python scripts/verify_deploy_routes.py` | exit 0 |

## 手動確認（実施手順と期待）

- **(1) ファイル選択**: /tools/csv を開き、.csv または .xlsx を選択 → ファイル一覧・プレビューが表示されること。
- **(2) 実行連打**: 1ファイル選択 → 「実行」を連打 → ダウンロードは1回だけ。完了後に「実行」が再度押せること。
- **(3) 異常ファイル名**: ファイル名を `test<img src=x onerror=alert(1)>.csv` にした CSV を選択（拒否されても「拒否理由」に名前が出る）→ alert が発火しないこと。名前がテキストとして表示されること。

**上記3ケースはローカルブラウザで実施し、挙動をメモに残すこと。**
