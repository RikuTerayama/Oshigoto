# 制約値 整合性レポート

**目的**: products_catalog / tools UI / validateFiles の制約値を「実装の真実」に揃え、矛盾をゼロにした。

**方針**: 実装を正とする。`templates/tools/<id>.html` の validateFiles 呼び出しおよびツール固有の定数（MAX_TEXT_LENGTH, MAX_PIXELS）を根拠に、catalog・UI・ガイド・FAQ を統一した。

---

## 1) ツール別 最終確定値（実装根拠付き）

### image-batch
| 項目 | 値 | 根拠 |
|------|-----|------|
| maxFiles | 50 | templates/tools/image-batch.html 572行 |
| maxFileSize | 20MB | 同 573行 20*1024*1024 |
| maxTotalSize | 200MB | 同 574行 |
| その他 | 最大ピクセル 80,000,000 | static/js/image-batch-convert.js MAX_PIXELS |

### pdf
| モード | maxFiles | maxFileSize | maxTotalSize | 根拠 |
|--------|----------|-------------|--------------|------|
| 結合・分割・抽出・圧縮 | 20 | 50MB | 300MB | templates/tools/pdf.html 611-621行 |
| PDF→画像 / 埋め込み画像抽出 | 10 | 50MB | 300MB | 同 612-614行（to-images, extract-images） |
| 画像→PDF | 100 | 20MB | 200MB | 同 602-608行（images-to-pdf） |

### image-cleanup
| 条件 | maxFiles | maxFileSize | maxTotalSize | 根拠 |
|------|----------|-------------|--------------|------|
| 通常 | 50 | 20MB | 200MB | templates/tools/image-cleanup.html 519-528行（bgRemovalEnabled false） |
| 背景除去ON | 20 | 20MB | 100MB | 同（bgRemovalEnabled true） |
| その他 | 最大ピクセル 80,000,000 | — | — | static/js/image-cleanup.js MAX_PIXELS |

### minutes
| 項目 | 値 | 根拠 |
|------|-----|------|
| テキスト長 | 20万文字 | templates/tools/minutes.html MAX_TEXT_LENGTH = 200000（412行） |
| ファイル数/サイズ | なし（テキスト貼り付けまたはファイル1本読み込み） | ファイルは .txt/.md を text() で読み、文字数で打ち切り |

### seo
| 項目 | 値 | 根拠 |
|------|-----|------|
| ファイル数/サイズ | validateFiles 未使用 | メタタグ検査は HTML ファイル選択あり。上限は未実装のため catalog には「ファイル数制限」を記載していない。 |

---

## 2) 修正したファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| lib/products_catalog.py | image-batch: 合計200MBを追加。pdf: 操作別の制約に修正（20/10ファイル、50MB/20MB、300MB/200MB）。image-cleanup: 50/20ファイル・合計200/100MBに修正。pdf FAQ の「PDFを画像に」に「最大10ファイルまで」を追加。 |
| templates/tools/pdf.html | 初期 dropzone-hint を「操作により最大10または20ファイル」に変更。updateSubOptions 内で to-images/extract-images のとき最大10ファイルと表示するよう修正。 |
| templates/guide/pdf.html | 制限事項を3行に分割（PDF結合等 20ファイル/50MB/300MB、PDF→画像 10ファイル、画像→PDF 100ファイル/20MB/200MB）。FAQ「PDFを画像に変換」に「最大10ファイルまで」を追加。 |
| templates/guide/image-cleanup.html | 制限事項に合計200MB/100MBを追加。FAQ「何枚まで」に合計の文言を追加。 |
| templates/guide/image-batch.html | 制限事項の1ファイル・合計の表記を「合計200MBまで」を含む形に統一。 |

---

## 3) ユーザー向け表記の統一ルール

- **ファイル数**: 「最大Nファイル」と明記。操作により変わる場合は「通常N、〇〇時はM」または「操作により最大NまたはMファイル」と記載。
- **1ファイルサイズ**: 「1ファイル〇〇MBまで」。
- **合計サイズ**: ツールで maxTotalSize を検証している場合は「合計〇〇MBまで」を制限事項に含める。
- **ピクセル上限**: 画像ツールで MAX_PIXELS がある場合は「最大ピクセル数 80,000,000（幅×高さ）」をガイドに記載。
- **テキスト長**: 議事録は「最大20万文字」のまま。
- **根拠**: ガイドの制限事項では「（実装に基づく）」とし、可能なら該当テンプレまたはJSファイル名を併記する。

---

*本レポートは実装（validateFiles 呼び出し・定数）に基づき 2026-02-06 に整合した。今後の仕様変更時は本ドキュメントと実装・catalog・UI・ガイドを同時に更新すること。*
