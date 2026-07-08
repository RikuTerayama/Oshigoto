# リリース手順: image-cleanup 枠・余白・角丸（image-style v1）

## 前提

- 機能は **feature/image-style-v1** ブランチにあり、**main にはまだ無い**。
- 本番は **main をデプロイしている**想定（Render の Production ブランチが main の場合、本手順の通りでよい。別ブランチを本番にしている場合は Dashboard で確認し、本番ブランチへマージする）。

---

## 1) ローカル状況確認（実施結果の例）

```bash
git branch --show-current   # → feature/image-style-v1
git status                  # 未コミット変更の有無を確認
git log -1 --oneline        # → aa9b635 feat: add image padding border rounded corners (client-side)
```

---

## 2) main に未入りであることの最終確認（根拠）

| 確認項目 | コマンド / 結果 |
|----------|------------------|
| image-style.js が main に無い | `git show main:static/js/image-style.js` → **fatal: path '...' exists on disk, but not in 'main'**（exit 128） |
| image-cleanup に「枠・余白・角丸」が無い | `git show main:templates/tools/image-cleanup.html` を検索 → 見出し「枠・余白・角丸」や `image-style.js` の script タグは **存在しない**。main には「余白トリム」「縦横比統一」「背景除去」までの文言のみ。 |

---

## 3) PR 準備の確認（差分の混入チェック）

- **main との差分一覧**:  
  `git diff --name-only main...feature/image-style-v1`  
  → 多数のファイルが表示される（100 件以上）。

- **理由**: feature/image-style-v1 は main より**古いベース**から分岐しており、その上に複数コミット（feature-gap レポート、ガイド充実、ナビ整理、image-style v1 など）が乗っている。このため「main にのみある変更」が diff に含まれ、**image-style 以外の変更も一緒に PR に含まれる**。

- **今回の image-style v1 で触っているファイル（想定）**:  
  `docs/feature-plans/01_image-style-v1.md`  
  `static/js/image-style.js`（新規）  
  `static/js/image-cleanup.js`  
  `templates/tools/image-cleanup.html`  
  `templates/guide/image-cleanup.html`  
  `templates/faq.html`  

- **取り込み方の選択肢**  
  - **A) feature/image-style-v1 をそのまま main にマージする**  
    → image-style v1 に加え、feature-gap レポート・ガイド・ナビ等の変更もまとめて本番に入る。  
  - **B) image-style v1 だけ main に入れたい場合**  
    → main から新ブランチを切り、コミット `aa9b635` を cherry-pick し、そのブランチで PR を作成する。  
    ```bash
    git checkout main
    git pull origin main
    git checkout -b release/image-style-v1-only
    git cherry-pick aa9b635
    git push -u origin release/image-style-v1-only
    ```  
    その後、GitHub で `release/image-style-v1-only` → main の PR を出す。

---

## 4) マージ後に本番で見えることの検証手順

### 4.1 GitHub で PR を main にマージする

1. GitHub で **feature/image-style-v1**（または release/image-style-v1-only）→ **main** の PR を開く。
2. コンフリクトが無いことを確認し、**Merge pull request** でマージ。
3. 必要に応じて「Delete branch」で feature ブランチを削除。

### 4.2 Render のブランチ設定と Auto Deploy 確認

1. [Render Dashboard](https://dashboard.render.com/) で該当 Web サービスを開く。
2. **Settings** → **Build & deploy** の **Branch** が **main** になっていることを確認（本番が main の場合）。
3. **Auto-Deploy** が **Yes** なら、main への push/マージで自動デプロイが走る。手動の場合は **Manual Deploy** → **Deploy latest commit**。

### 4.3 デプロイ後の確認 URL

- **確認URL**: `https://<本番ドメイン>/tools/image-cleanup`  
  例: `https://jobcan-automation.onrender.com/tools/image-cleanup`

### 4.4 見つけるべき UI

- ページ内の **「⚙️ 処理設定」** セクション内に、見出し **「枠・余白・角丸」** があること。
- その下に「余白（px）」「角丸（px）」「枠の幅（px）」「枠の色」「余白・角の背景色」の入力があること。
- 「縦横比統一」の下、「出力形式」の上に配置されていること。

### 4.5 キャッシュ対策

- ブラウザで古い JS/CSS が残っていると、変更が反映されたように見えない場合がある。
- **シークレットウィンドウ（プライベートブラウジング）** で同じ URL を開くか、**ハードリロード**（Ctrl+Shift+R / Cmd+Shift+R）で再読み込みして確認する。

---

## 5) 発見性を上げる最小改善案（1つ・実装はしない）

- **案 A**: `/tools` 一覧の「画像ユーティリティ」カードに **“New” バッジ**を付ける。  
  - 例: `templates/tools/index.html` の product ループ内で、`product.id == 'image-cleanup'` のときだけバッジ用 span を表示。  
  - 数週間〜1ヶ月運用したらバッジを外す運用を想定。

- **案 B**: **image-cleanup ページ冒頭**に「新機能: 枠・余白・角丸」の 1 行コールアウトを入れる。  
  - 例: ファイル選択ドロップゾーンの直上に、`<p class="info-text">新機能: 枠・余白・角丸 — 処理設定から余白・角丸・枠を指定できます。</p>` を追加。  
  - 目立たせたい場合は背景色付きの小さなバナーにしてもよい。

どちらか 1 つ採用すれば、本番で「どこに機能があるか」の認知がしやすくなる。

---

## マージ後の確認チェックリスト（10行以内）

- [ ] GitHub で PR を main にマージした。
- [ ] Render のデプロイが完了している（Dashboard で Logs/Events を確認）。
- [ ] 本番URL `https://<ドメイン>/tools/image-cleanup` が 200 で開ける。
- [ ] 「⚙️ 処理設定」内に「枠・余白・角丸」の見出しと入力がある。
- [ ] 余白・角丸・枠を 0 より大きくして 1 枚処理し、出力画像に反映される。
- [ ] シークレット or ハードリロードでキャッシュを外して再確認した。
- [ ] 既存機能（透過→白背景、余白トリム、縦横比、背景除去）が問題なく動く。
- [ ] `/guide/image-cleanup` が 200 で、FAQ に「枠・余白・角丸は付けられますか？」がある。
