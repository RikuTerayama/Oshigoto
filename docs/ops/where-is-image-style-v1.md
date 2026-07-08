# 枠・余白・角丸（image-cleanup 候補9 v1）機能の所在

## 1) 結論（見つからない原因の特定）

**原因: 未マージ / 未デプロイ**

- 当機能は **main ブランチに存在しません**。本番（main をデプロイしている環境）では表示されません。
- **根拠**
  - `main` 上に `static/js/image-style.js` が存在しない（`git show main:static/js/image-style.js` → エラー）。
  - `main` の `templates/tools/image-cleanup.html` には「枠・余白・角丸」の見出しブロックがなく、タイトルも「透過→白背景・余白トリム・縦横比統一・背景除去」のみ（枠・角丸の文言なし）。
- **機能が存在する場所**: ブランチ **feature/image-style-v1**、コミット例: `aa9b635 feat: add image padding border rounded corners (client-side)`。
- 導線不足・折りたたみ・条件付き表示が原因ではありません。枠・余白・角丸のUIは折りたたまれておらず、表示条件もありません（常時表示）。

---

## 2) ユーザー向け「ここにある」案内

**（feature/image-style-v1 をデプロイしている、またはローカルでそのブランチを実行している場合）**

- **クリック手順**:  
  ホーム（/）→ **Tools**（/tools）→ **画像ユーティリティ**（/tools/image-cleanup）→ ページ内の **「⚙️ 処理設定」** セクション内、**「枠・余白・角丸」** 見出しのブロック。
- **直接URL**:  
  `https://<あなたのドメイン>/tools/image-cleanup`
- **ページ内で探すキーワード**:  
  - 見出し: **「枠・余白・角丸」**  
  - その下に「余白（px）」「角丸（px）」「枠の幅（px）」「枠の色」「余白・角の背景色」の入力があります。  
  - セクションは「縦横比統一」の下、「出力形式」の上です。

---

## 3) 開発者向け根拠（ファイルと要点）

| 種類 | ファイルパス | 要点 |
|------|--------------|------|
| **UI** | `templates/tools/image-cleanup.html` | 397–434行目。`<!-- v1: 枠・余白・角丸 -->` のコメント付き。見出し `<h4>枠・余白・角丸</h4>`、id: `style-padding`, `style-radius`, `style-border-width`, `style-border-color`, `style-bg-color` 等。折りたたみ・`display:none` はこのブロックにはない（`display: none` は「枠の色＝任意」「背景色＝任意」時のカラーピッカー用のみ）。 |
| **JS（スタイル処理）** | `static/js/image-style.js` | `ImageStyle.applyPadding`, `applyRoundedCorners`, `applyBorder` を定義。`roundRect` のフォールバックあり。 |
| **JS（読み込み）** | `templates/tools/image-cleanup.html` | 501行目: `<script src="{{ url_for('static', filename='js/image-style.js') }}"></script>`。`image-export.js` の後、`image-cleanup.js` の前。 |
| **呼び出し元** | `static/js/image-cleanup.js` | `ImageCleanup.runCleanupPipeline` 内。縦横比統一の後・書き出しの前に「(5b) 枠・余白・角丸」として、`ImageStyle.applyPadding` → `applyRoundedCorners` → `applyBorder` を順に実行（290–296行付近）。`style` オプションは `runCleanup()` で DOM から読み、`runCleanupPipeline` に渡している（`templates/tools/image-cleanup.html` 内の `processor` で `style: { paddingPx, radiusPx, borderWidthPx, borderColor, bgColor }`）。 |
| **一覧・導線** | `templates/tools/index.html` | `products` をループし、`product.path` で各ツールへリンク（243行目等）。`lib/products_catalog.py` の `image-cleanup` は `path: '/tools/image-cleanup'`, `name: '画像ユーティリティ'`。 |
| **ナビ** | `lib/nav.py` | `get_nav_sections()` が PRODUCTS から `tool_links` を組み立て、ヘッダー/フッターで「Tools」→「すべてのツール」＋各ツール名（画像ユーティリティ含む）へのリンクを生成。 |

---

## 4) 導線不足時の最小改善案（任意）

**原因が未マージのため、現時点では必須ではありません。** main マージ・デプロイ後、発見性を上げたい場合の案です。

- **/tools 一覧**: 画像ユーティリティのカードに「枠・余白・角丸」などの機能ワードを説明文に含める、または短期的に「New」バッジを付与。
- **image-cleanup ページ**: 冒頭（ファイル選択の上）に「新機能: 枠・余白・角丸」の1行コールアウトを追加し、アンカーで `#style-section` 等に飛ばす。
- **ガイド**: `templates/guide/image-cleanup.html` の目次または冒頭に「枠・余白・角丸」へのアンカーリンクを追加。

---

*本ドキュメントは、コード上のファイルパスと該当行・関数名に基づいて特定した結果です。*
