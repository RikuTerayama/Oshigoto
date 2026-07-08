# 追加機能候補 ギャップ分析・優先順位レポート

本レポートは `npm run report:feature-gap` によりリポジトリ解析から生成されています。

## 0. 前提

### 現状ツール一覧（/tools 配下）
| id | path | テンプレ | 主なJS |
|----|------|----------|--------|
| image-batch | /tools/image-batch | templates/tools/image-batch.html | static/js/file-validation.js, static/js/file-utils.js, static/js/image-convert.js, static/js/image-batch-presets.js, static/js/image-batch-convert.js |
| pdf | /tools/pdf | templates/tools/pdf.html | static/js/file-validation.js, static/js/file-utils.js, static/js/zip-utils.js, static/js/tool-runner.js, static/js/pdf-range.js |
| image-cleanup | /tools/image-cleanup | templates/tools/image-cleanup.html | static/js/file-validation.js, static/js/file-utils.js, static/js/zip-utils.js, static/js/tool-runner.js, static/js/image-load.js |
| minutes | /tools/minutes | templates/tools/minutes.html | static/js/file-validation.js, static/js/file-utils.js, static/js/minutes-parse.js, static/js/minutes-normalize.js, static/js/minutes-date.js |
| seo | /tools/seo | templates/tools/seo.html | static/js/file-validation.js, static/js/file-utils.js, static/js/minutes-export.js, static/js/seo-ogp-presets.js, static/js/seo-ogp-canvas.js |

### 技術構成
- **一覧生成元**: `lib/products_catalog.py` の PRODUCTS。ナビは `lib/nav.py` の get_nav_sections / get_footer_columns。
- **ツールページ**: `templates/tools/<id>.html`。各テンプレから `static/js/*.js` を参照。
- **サーバーAPI**: `app.py` に `/tools/*` はGETのみ。`/api/minutes/format` は 501 Not Implemented。`/api/seo/crawl-urls` は POST で start_url を受けサーバー側でクロール。
- **ファイル受信・保存**: `app.py` で `request.files` と `file.save(file_path)` を使用しているのは **Jobcan AutoFill 用の `/upload` ルートのみ**（行: 1251 付近）。`/tools/*` 向けのファイルアップロードルートは存在しない。

### クライアント処理 vs サーバー処理
| ツール | 処理の主体 | 根拠 |
|--------|------------|------|
| image-batch | ブラウザ内 | テンプレ・image-batch-convert.js のみ。app.py にアップロードなし |
| pdf | ブラウザ内 | pdf-lib / pdf.js CDN、pdf-ops.js 等。app.py にアップロードなし |
| image-cleanup | ブラウザ内 | image-cleanup.js / image-background-removal.js。app.py にアップロードなし |
| minutes | ブラウザ内 | minutes-parse.js / minutes-export.js。api/minutes/format は 501 |
| seo | 主にブラウザ。URLクロールのみサーバー | OGP等はクライアント。crawl-urls のみ app.py 850 行付近でサーバーがURL取得 |

## 1. 現状のツール別機能一覧（入力/処理/出力/送信/保存）

### image-batch
| 項目 | 内容 | 根拠 |
|------|------|------|
| 入力 | accept: image/png,image/jpeg,image/webp、複数可、maxFiles: 50、maxFileSize: 20 * 1024 * 1024 | templates/tools/image-batch.html の input と validateFiles 呼び出し |
| 処理 | （本文参照） | static/js/file-validation.js, static/js/file-utils.js, static/js/image-convert.js, static/js/image-batch-presets.js, static/js/image-batch-convert.js, static/js/zip-utils.js, static/js/tool-runner.js |
| 出力 | ツールにより PDF/PNG/JPEG/ZIP/MD/CSV/JSON 等 | 各JSの Blob / downloadBlob |
| サーバー送信 | なし（seo の URL クロール除く） | app.py に /tools 向け POST ファイル受信なし |
| サーバー保存 | なし | app.py の file.save は /upload（Jobcan）のみ |

### pdf
| 項目 | 内容 | 根拠 |
|------|------|------|
| 入力 | accept: application/pdf、複数可、maxFiles: 100、maxFileSize: 20 * 1024 * 1024 | templates/tools/pdf.html の input と validateFiles 呼び出し |
| 処理 | （本文参照） | static/js/file-validation.js, static/js/file-utils.js, static/js/zip-utils.js, static/js/tool-runner.js, static/js/pdf-range.js, static/js/pdf-ops.js, static/js/pdf-render.js, static/js/pdf-compress.js, static/js/pdf-images-to-pdf.js, static/js/pdf-extract-images.js |
| 出力 | ツールにより PDF/PNG/JPEG/ZIP/MD/CSV/JSON 等 | 各JSの Blob / downloadBlob |
| サーバー送信 | なし（seo の URL クロール除く） | app.py に /tools 向け POST ファイル受信なし |
| サーバー保存 | なし | app.py の file.save は /upload（Jobcan）のみ |

### image-cleanup
| 項目 | 内容 | 根拠 |
|------|------|------|
| 入力 | accept: image/png,image/jpeg,image/webp、複数可、maxFiles: 未確認、maxFileSize: 20 * 1024 * 1024 | templates/tools/image-cleanup.html の input と validateFiles 呼び出し |
| 処理 | （本文参照） | static/js/file-validation.js, static/js/file-utils.js, static/js/zip-utils.js, static/js/tool-runner.js, static/js/image-load.js, static/js/image-export.js, static/js/image-cleanup.js, static/js/image-background-removal.js, static/js/image-aspect.js |
| 出力 | ツールにより PDF/PNG/JPEG/ZIP/MD/CSV/JSON 等 | 各JSの Blob / downloadBlob |
| サーバー送信 | なし（seo の URL クロール除く） | app.py に /tools 向け POST ファイル受信なし |
| サーバー保存 | なし | app.py の file.save は /upload（Jobcan）のみ |

### minutes
| 項目 | 内容 | 根拠 |
|------|------|------|
| 入力 | accept: .txt,.md,text/plain,text/markdown、複数可、maxFiles: 未確認、maxFileSize: 未確認 | templates/tools/minutes.html の input と validateFiles 呼び出し |
| 処理 | （本文参照） | static/js/file-validation.js, static/js/file-utils.js, static/js/minutes-parse.js, static/js/minutes-normalize.js, static/js/minutes-date.js, static/js/minutes-extract.js, static/js/minutes-templates.js, static/js/minutes-export.js, static/js/minutes-export-v2.js |
| 出力 | ツールにより PDF/PNG/JPEG/ZIP/MD/CSV/JSON 等 | 各JSの Blob / downloadBlob |
| サーバー送信 | なし（seo の URL クロール除く） | app.py に /tools 向け POST ファイル受信なし |
| サーバー保存 | なし | app.py の file.save は /upload（Jobcan）のみ |

### seo
| 項目 | 内容 | 根拠 |
|------|------|------|
| 入力 | accept: text/html、複数可、maxFiles: 未確認、maxFileSize: 未確認 | templates/tools/seo.html の input と validateFiles 呼び出し |
| 処理 | （本文参照） | static/js/file-validation.js, static/js/file-utils.js, static/js/minutes-export.js, static/js/seo-ogp-presets.js, static/js/seo-ogp-canvas.js, static/js/seo-ogp-export.js, static/js/seo-pagespeed-checklist.js, static/js/seo-html-inspector.js, static/js/seo-sitemap.js, static/js/seo-robots.js |
| 出力 | ツールにより PDF/PNG/JPEG/ZIP/MD/CSV/JSON 等 | 各JSの Blob / downloadBlob |
| サーバー送信 | なし（seo の URL クロール除く） | app.py に /tools 向け POST ファイル受信なし |
| サーバー保存 | なし | app.py の file.save は /upload（Jobcan）のみ |

（PDF: merge/split/extract は pdf-ops.js、compress は pdf-compress.js、PDF→画像は pdf-render.js、画像→PDF は pdf-images-to-pdf.js。画像一括: image-batch-convert.js + file-validation.js。議事録: minutes-export.js で .md/.txt、minutes-export-v2.js で .csv/.json。）

## 2. 候補10機能との対応表（ステータスと根拠）

| # | 候補 | ステータス | 根拠（ファイル・要素） |
|---|------|------------|------------------------|
| 1 | PDFテーブル抽出（PDF→Excel/CSV） | **ない** | テーブル構造の抽出・Excel/CSV出力は未実装。pdf-render.js でページ描画はあるが表データ抽出は未確認。pdf-lib/pdf.js のみでは表セル認識は別実装が必要 |
| 2 | PDF分割・結合・ページ抽出 | **既にある** | pdf-ops.js: mergePdfs (L12付近)、splitPdf (L127付近)、extractPdf (L68付近)。templates/tools/pdf.html で mode=merge/extract/split |
| 3 | PDF圧縮（メール添付向け） | **既にある** | pdf-compress.js: compressPdfByRasterize（レンダリング→画像→再PDF化）。templates/tools/pdf.html で mode=compress |
| 4 | PDF→画像、画像→PDF | **既にある** | pdf-render.js: pdfToImages。pdf-images-to-pdf.js: 画像→PDF。pdf.html で mode=to-images / images-to-pdf |
| 5 | OCR（スキャンPDFの文字起こし、検索可能PDF化） | **ない** | リポジトリ内に OCR/Tesseract/textract 等の実装・参照なし。未確認: 外部API利用の有無 |
| 6 | PDFの黒塗り、個人情報マスク | **ない** | redact/mask/黒塗り/マスク 等の実装なし。pdf-lib の描画マスクは別途実装が必要 |
| 7 | 画像の一括リサイズ・容量圧縮・形式変換 | **既にある** | image-batch-convert.js: リサイズ・品質・形式変換。file-validation.js: maxFiles 50, maxFileSize 20MB。templates/tools/image-batch.html |
| 8 | 透過PNGの白背景化、背景除去 | **既にある** | image-cleanup.js: applyWhiteBackground, trimMargins。image-background-removal.js: 背景除去。templates/tools/image-cleanup.html |
| 9 | 画像に枠・余白・角丸・比率整形 | **一部ある** | image-aspect.js: padToAspect（1:1, 4:5, 16:9）。image-cleanup.js: 余白トリム。枠・角丸の専用UI/処理は未確認（未確認: image-export.js 等） |
| 10 | Markdown→docx（議事録出力拡張） | **ない** | 議事録は .md / .txt / .csv / .json 出力のみ。minutes-export.js, minutes-export-v2.js に docx 参照なし。mammoth 等の利用なし |

## 3. ギャップ詳細（不足点と追加で必要な設計）

- **1. PDFテーブル抽出**: ページを描画したうえでテーブル領域検出・セル認識が必要。ブラウザでは pdf.js の getTextContent でテキストと位置は取れるが、表構造の推定は別ロジック。Excel/CSV 出力フォーマットの設計が必要。
- **5. OCR**: ブラウザでは Tesseract.js 等の利用が現実的。サーバーなら Python + pytesseract / pdf2image 等。検索可能PDF化はテキストレイヤー追加の実装が必要。
- **6. 黒塗り/マスク**: 領域指定（座標または選択）と、その領域を塗りつぶす処理。pdf-lib で矩形描画で対応可能。個人情報の検出は手動指定か別AI。
- **9. 枠・角丸**: 現状は縦横比と余白トリムまで。角丸は Canvas の clip や描画で追加可能。枠（ボーダー）も同様。
- **10. Markdown→docx**: ブラウザでは docx 生成に docx ライブラリ等が必要。サーバーなら python-docx。議事録テンプレとの対応付けが必要。

## 4. 優先順位（スコア表と上位提案）

スコアは 1〜5（需要: 高=5、コスト: 低=5、リスク: 低=5、負荷: 低=5、SEO: 高=5）。

| 候補 | 需要 | コスト | リスク | 負荷 | SEO | 合計 |
|------|------|--------|--------|------|-----|------|
| 1. PDFテーブル抽出 | 5 | 2 | 4 | 4 | 5 | 20 |
| 2. PDF分割・結合・抽出 | - | - | - | - | - | **既存** |
| 3. PDF圧縮 | - | - | - | - | - | **既存** |
| 4. PDF→画像/画像→PDF | - | - | - | - | - | **既存** |
| 5. OCR | 5 | 2 | 3 | 2 | 5 | 17 |
| 6. PDF黒塗り・マスク | 4 | 3 | 3 | 4 | 4 | 18 |
| 7. 画像一括（既存強化） | 4 | 4 | 5 | 5 | 4 | 22 |
| 8. 透過/背景除去 | - | - | - | - | - | **既存** |
| 9. 枠・角丸・比率 | 3 | 4 | 5 | 5 | 3 | 20 |
| 10. Markdown→docx | 4 | 3 | 5 | 4 | 4 | 20 |

### 次にやる候補（上位）
1. **画像一括の既存強化（7）** — 既存資産の拡張。プリセット追加・解像度上限の明示・バッチサイズ調整など。コスト低・リスク低。
2. **PDFテーブル抽出（1）** — 需要・SEOともに高いが実装コスト大。まずは「表形式のテキストをCSVに落とす」最小版をブラウザで検討。
3. **Markdown→docx（10）** — 議事録と相性が良く、需要あり。ブラウザで docx 生成ライブラリを導入する案が現実的。
4. **枠・角丸・比率（9）** — 既存 image-aspect / image-cleanup の延長。角丸・枠のオプション追加で完了に近い。
5. **PDF黒塗り・マスク（6）** — 個人情報保護ニーズ。領域指定＋矩形塗りつぶしで実装可能。AI検出はオプション。

## 5. 実装方式の推奨

| 候補 | 推奨方式 | 理由 |
|------|----------|------|
| PDFテーブル抽出 | ブラウザ内（pdf.js getTextContent + 表構造推定） | アップロード不要でプライバシーリスク低。重い場合は Worker で非同期 |
| OCR | ブラウザ内（Tesseract.js） または サーバー（Python） | ブラウザならアップロード不要。精度・言語は Tesseract に依存。サーバーなら負荷・コスト増 |
| 黒塗り・マスク | ブラウザ内（pdf-lib で矩形描画） | 領域はユーザー指定。外部API不要 |
| 画像強化・枠角丸 | ブラウザ内（既存 Canvas 拡張） | 既存と同じ方針で一貫 |
| Markdown→docx | ブラウザ内（docx 等のライブラリ） | 議事録データは既にクライアントにある。サーバーに送らない方針維持 |

## 6. 次フェーズで作るべきガイド記事の増え方

- 候補 1（PDFテーブル）を追加する場合: `/guide/pdf` に「テーブル抽出の使い方」を追加。FAQ に 1〜2 問追加。
- 候補 5（OCR）を追加する場合: 新規ガイド `/guide/ocr` または PDF ガイド内セクション。データ取扱い（画像送信の有無）を明記。
- 候補 6（黒塗り）: PDF ガイドに「マスク・黒塗り」セクション追加。
- 候補 9（枠・角丸）: 画像ユーティリティガイドに「枠・角丸の付け方」追加。
- 候補 10（docx）: 議事録ガイドに「Word（docx）で出力する」を追加。

---
*Generated by scripts/generate-feature-gap-report.mjs*
