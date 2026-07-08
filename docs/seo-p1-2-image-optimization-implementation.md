# P1-2: 画像最適化実装 - 実装サマリー

**実装日**: 2026-02-04  
**タスク**: 画像最適化（loading=lazy + width/height + altの棚卸し）

---

## 実装完了確認

### 変更ファイル
- ✅ `static/css/common.css` - CLS対策のCSS追加
- ✅ `templates/autofill.html:747` - `loading="eager"`追加
- ✅ `templates/index.html:793` - `loading="eager"`追加
- ✅ `report/image_optimization_inventory.md` - 画像一覧レポート作成

### 実装内容

1. ✅ **画像一覧の作成**
   - テンプレート全体を検索し、`<img`タグの使用箇所を一覧化
   - 画像一覧テーブルを作成（ファイル/行/用途/alt/サイズ/対応状況）

2. ✅ **画像属性の追加**
   - 非表示画像（SEO用）に`loading="eager"`を追加
   - 既存の`alt`、`width/height`属性は維持

3. ✅ **CSSでのCLS対策**
   - `img { height: auto; max-width: 100%; }`を追加
   - アスペクト比を維持し、レスポンシブ対応

---

## 画像一覧テーブル

| ファイル | 行番号 | 用途 | alt属性 | width/height | loading | 対応状況 |
|---------|--------|------|---------|--------------|---------|----------|
| `templates/autofill.html` | 747 | ロゴ画像（非表示、SEO用） | ✅ "Jobcan AutoFill ロゴ" | ✅ 900x240 | ✅ eager | ✅ 完了 |
| `templates/index.html` | 793 | ロゴ画像（非表示、SEO用） | ✅ "Jobcan AutoFill ロゴ" | ✅ 900x240 | ✅ eager | ✅ 完了 |

---

## 実装差分

### 変更: `static/css/common.css`

#### 変更前

```css
/* ============================================
   Utility Classes
   ============================================ */
```

#### 変更後

```css
/* ============================================
   Image Optimization (P1-2: CLS対策)
   ============================================ */
img {
    height: auto;
    max-width: 100%;
}

/* ============================================
   Utility Classes
   ============================================ */
```

### 変更: `templates/autofill.html:747`

#### 変更前

```html
<img src="{{ url_for('static', filename='JobcanAutofill.png') }}" alt="Jobcan AutoFill ロゴ" width="900" height="240" style="display: none;" />
```

#### 変更後

```html
<img src="{{ url_for('static', filename='JobcanAutofill.png') }}" alt="Jobcan AutoFill ロゴ" width="900" height="240" loading="eager" style="display: none;" />
```

### 変更: `templates/index.html:793`

#### 変更前

```html
<img src="{{ url_for('static', filename='JobcanAutofill.png') }}" alt="Jobcan AutoFill ロゴ" width="900" height="240" style="display: none;" />
```

#### 変更後

```html
<img src="{{ url_for('static', filename='JobcanAutofill.png') }}" alt="Jobcan AutoFill ロゴ" width="900" height="240" loading="eager" style="display: none;" />
```

---

## 実装詳細

### 1. 画像最適化の方針

#### 1.1 ファーストビューのヒーロー画像

- **対象**: `autofill.html`と`index.html`の`.header`セクションの背景画像
- **方針**: ファーストビューに表示されるため、`loading="lazy"`は適用しない
- **実装**: 背景画像はCSS `background-image`で使用されているため、`<img>`タグではない

#### 1.2 非表示画像（SEO用）

- **対象**: `style="display: none;"`の`<img>`タグ
- **方針**: SEO用の非表示画像なので、`loading="eager"`を明示的に設定
- **実装**: `loading="eager"`を追加

#### 1.3 CSSでのCLS対策

- **方針**: `img { height: auto; max-width: 100%; }`を追加
- **効果**: 
  - `height: auto;`により、アスペクト比を維持
  - `max-width: 100%;`により、レスポンシブ対応

---

## 検証手順

### 1. ローカル検証

#### 1.1 画像属性の確認

```bash
# Flaskアプリを起動
python app.py

# /autofill ページ
curl -s http://localhost:5000/autofill | grep -A 1 "<img"

# / ページ
curl -s http://localhost:5000/ | grep -A 1 "<img"
```

**期待される出力**:
```html
<img src="/static/JobcanAutofill.png" alt="Jobcan AutoFill ロゴ" width="900" height="240" loading="eager" style="display: none;" />
```

#### 1.2 CSSでのCLS対策確認

```bash
# common.cssを確認
grep -A 3 "Image Optimization" static/css/common.css
```

**期待される出力**:
```css
/* ============================================
   Image Optimization (P1-2: CLS対策)
   ============================================ */
img {
    height: auto;
    max-width: 100%;
}
```

#### 1.3 レイアウト崩れの確認

- `/`, `/tools`, `/autofill`, `/faq`の各ページをブラウザで開く
- レイアウトが崩れていないことを確認

---

### 2. DevToolsでの遅延読み込み確認

#### 2.1 画像読み込みの確認

1. **ブラウザのDevToolsを開く**
   - Chrome: `F12`または`Ctrl+Shift+I`
   - Networkタブを開く

2. **ページをリロード**
   - `/autofill`ページを開く
   - Networkタブで`JobcanAutofill.png`の読み込みを確認

3. **期待される動作**:
   - ファーストビューの画像は即座に読み込まれる（`loading="eager"`）
   - 非表示画像も即座に読み込まれる（SEO用）

#### 2.2 画像読み込みタイミングの確認

1. **Networkタブで画像をフィルタ**
   - Networkタブで「Img」を選択
   - ページをリロード

2. **読み込みタイミングを確認**
   - `JobcanAutofill.png`が即座に読み込まれることを確認
   - `loading="eager"`が正しく機能していることを確認

---

### 3. CLS対策の確認

#### 3.1 レイアウトシフトの確認

1. **Chrome DevToolsのPerformanceタブを開く**
   - `F12` → Performanceタブ
   - 「Record」をクリック
   - ページをリロード
   - 「Stop」をクリック

2. **CLS（Cumulative Layout Shift）を確認**
   - PerformanceタブでCLSスコアを確認
   - 画像読み込みによるレイアウトシフトが発生していないことを確認

#### 3.2 CSSの適用確認

1. **Elementsタブで画像を選択**
   - `F12` → Elementsタブ
   - `<img>`タグを選択

2. **Computedスタイルを確認**
   - Computedタブで`height: auto`と`max-width: 100%`が適用されていることを確認

---

## 検証チェックリスト

### ローカル検証

- [ ] 主要ページ（/ /tools /autofill /faq）でレイアウト崩れがない
- [ ] 画像に`alt`属性が設定されている
- [ ] 画像に`width/height`属性が設定されている
- [ ] 画像に`loading="eager"`が設定されている（非表示画像）
- [ ] CSSで`img { height: auto; max-width: 100%; }`が適用されている

### DevTools検証

- [ ] 画像読み込みが即座に行われる（`loading="eager"`）
- [ ] Networkタブで画像の読み込みタイミングを確認できる
- [ ] CLS（Cumulative Layout Shift）が発生していない

---

## 注意点

### 1. 非表示画像の扱い

- `style="display: none;"`の画像は、SEO用の非表示画像
- `loading="eager"`を明示的に設定（SEO用なので即座に読み込む必要がある）

### 2. 背景画像の扱い

- CSS `background-image`で使用されている画像は、`<img>`タグではないため、`loading`属性は適用できない
- 背景画像は通常、ファーストビューに表示されるため、遅延読み込みは不要

### 3. CLS対策

- `img { height: auto; }`により、アスペクト比を維持
- `max-width: 100%;`により、レスポンシブ対応
- `width/height`属性により、ブラウザが画像サイズを事前に把握できる

---

## 期待される効果

1. **CLS（Cumulative Layout Shift）の改善**: `width/height`属性とCSSにより、レイアウトシフトを防止
2. **パフォーマンスの向上**: 画像の読み込みタイミングを最適化
3. **アクセシビリティの向上**: `alt`属性により、スクリーンリーダー対応

---

## 実装完了確認

✅ **画像一覧の作成**: 全画像を一覧化（`report/image_optimization_inventory.md`）  
✅ **属性の追加**: `loading="eager"`を追加（非表示画像用）  
✅ **CSSでのCLS対策**: `img { height: auto; max-width: 100%; }`を追加
