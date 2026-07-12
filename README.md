# Oshigoto / しごと道具箱

しごとの小さな面倒を、さっと片づけるための軽量ツール集です。

PDF、CSV、画像、ページ確認など、仕事でたまに必要になる作業をまとめています。public版では汎用ツールだけを主役にします。

## 主な機能

- PDFツール: 結合、分割、抽出、圧縮、画像変換、保護付与
- CSV/Excelツール: CSV/XLSX変換、文字コード確認、列整理
- 画像一括変換: 形式変換、リサイズ、一括処理
- 画像クリーンアップ: 余白調整、背景整理、PNG出力
- SEO/URL確認: OGP、meta、sitemap、robots.txt確認

## 公開URL

- Production: https://oshigoto.onrender.com
- Health check: `/healthz`

## Render設定

Render Dashboard > Environment で環境変数を設定し、Manual Deploy または Restart で反映します。

```text
BASE_URL=https://oshigoto.onrender.com
AMAZON_ASSOCIATE_TAG=<configured tag>
AMAZON_AFFILIATE_ENABLED=true
ADSENSE_ENABLED=true
PORT=10000
WEB_CONCURRENCY=1
WEB_THREADS=1
MEMORY_LIMIT_MB=450
MEMORY_WARNING_MB=400
MAX_FILE_SIZE_MB=10
```

`AMAZON_ASSOCIATE_TAG` を設定すると、Amazonリンクにassociate tagが付与されます。タグ値は環境変数で管理し、READMEには実値を固定記載しません。

## ローカル起動

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## テスト

```bash
python scripts\smoke_test.py
python scripts\smoke_test.py --deploy
python scripts\adsense_preflight.py
python scripts\generate_sitemap_lastmod_manifest.py --check
python -m py_compile app.py lib\seo.py lib\products_catalog.py
```

## 確認ポイント

- `/` と `/tools` が200で表示される
- 5つのツールrouteが200で表示される
- `/autofill` は `/tools` へ301 redirectする
- PDFのパスワード解除UI/APIは公開しない
- `/api/pdf/lock` はPDF保護付与APIとして維持する
- `/api/seo/crawl-urls` はURL制限とtimeoutを維持する
- sitemapに5ツールが含まれる
- sitemapに `/autofill` が含まれない
- Amazon/A8/AdSenseの開示と安全条件を維持する
- 実績風の数値表示や順位づけを行わない

## 残す安全方針

- PDF解除UI/APIは公開しない
- 汎用ツール以外の公開導線は追加しない
- SEO URL確認ではSSRF対策、timeout、URL検証を維持する
- A8は承認済み案件だけを表示する
- Amazonリンクはassociate tag付与と開示文言を維持する
