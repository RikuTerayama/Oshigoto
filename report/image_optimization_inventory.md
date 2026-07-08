# 画像最適化棚卸しレポート

**作成日**: 2026-02-04  
**目的**: テンプレート全体の画像使用箇所を一覧化し、最適化状況を確認

---

## 画像一覧テーブル

| ファイル | 行番号 | 用途 | alt属性 | width/height | loading | 対応状況 |
|---------|--------|------|---------|--------------|---------|----------|
| `templates/autofill.html` | 747 | ロゴ画像（非表示、SEO用） | ✅ "Jobcan AutoFill ロゴ" | ✅ 900x240 | ❌ なし | 要修正 |
| `templates/index.html` | 793 | ロゴ画像（非表示、SEO用） | ✅ "Jobcan AutoFill ロゴ" | ✅ 900x240 | ❌ なし | 要修正 |

---

## 画像の詳細

### 1. JobcanAutofill.png

- **ファイルパス**: `static/JobcanAutofill.png`
- **用途**: ロゴ画像（OGP/Twitterカード用、SEO用）
- **表示方法**: 
  - `autofill.html`: 背景画像として使用（CSS `background-image`）+ 非表示の`<img>`タグ（SEO用）
  - `index.html`: 背景画像として使用（CSS `background-image`）+ 非表示の`<img>`タグ（SEO用）
- **サイズ**: 900x240（既存コードより）
- **現在の状態**:
  - ✅ `alt`属性: あり（"Jobcan AutoFill ロゴ"）
  - ✅ `width/height`: あり（900x240）
  - ✅ `loading`: `eager`（非表示画像なので`loading="lazy"`は不要。SEO用なので`loading="eager"`を明示的に設定）

---

## 最適化方針

### 1. ファーストビューのヒーロー画像

- **対象**: `autofill.html`と`index.html`の`.header`セクションの背景画像
- **方針**: ファーストビューに表示されるため、`loading="lazy"`は適用しない
- **対応**: 非表示の`<img>`タグはSEO用なので、`loading="eager"`を明示的に設定（またはそのまま）

### 2. 非表示画像（SEO用）

- **対象**: `style="display: none;"`の`<img>`タグ
- **方針**: SEO用の非表示画像なので、`loading`属性は不要（または`loading="eager"`を明示）
- **対応**: 現状維持または`loading="eager"`を追加

### 3. CSSでのCLS対策

- **方針**: `img { height: auto; max-width: 100%; }`を追加して、アスペクト比を維持し、レスポンシブ対応
- **対応**: `static/css/common.css`に追加 ✅ 完了

---

## 修正内容

### 1. 非表示画像の最適化

- `templates/autofill.html:747`
- `templates/index.html:793`
- `loading="eager"`を追加（SEO用の非表示画像なので、明示的に設定）

### 2. CSSでのCLS対策

- `static/css/common.css`に`img { height: auto; max-width: 100%; }`を追加 ✅ 完了

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
grep -A 2 "img {" static/css/common.css
```

**期待される出力**:
```css
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
   - ファーストビューの画像は即座に読み込まれる（`loading="eager"`または未指定）
   - 非表示画像も即座に読み込まれる（SEO用）

---

## 注意点

### 1. 非表示画像の扱い

- `style="display: none;"`の画像は、SEO用の非表示画像
- `loading="lazy"`は適用しない（SEO用なので即座に読み込む必要がある）
- `loading="eager"`を明示的に設定するか、そのままでも可

### 2. 背景画像の扱い

- CSS `background-image`で使用されている画像は、`<img>`タグではないため、`loading`属性は適用できない
- 背景画像は通常、ファーストビューに表示されるため、遅延読み込みは不要

### 3. CLS対策

- `img { height: auto; }`により、アスペクト比を維持
- `max-width: 100%;`により、レスポンシブ対応

---

## 実装完了確認

✅ **画像一覧の作成**: 全画像を一覧化  
✅ **属性の追加**: `loading="eager"`を追加（非表示画像用）  
✅ **CSSでのCLS対策**: `img { height: auto; }`を追加
