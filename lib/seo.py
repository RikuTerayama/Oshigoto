# -*- coding: utf-8 -*-
"""Shared SEO defaults and helpers for metadata, breadcrumbs, and schema."""

from copy import deepcopy


SEO_DEFAULTS = {
    '/': {
        'title': 'しごと道具箱｜PDF・CSV・画像・URL確認の軽量ツール集',
        'description': 'PDF、CSV、画像、URL確認など、仕事でたまに必要になる小さな作業をブラウザでさっと片づける無料ツール集です。',
        'og_type': 'website',
    },
    '/autofill': {
        'title': '道具箱一覧 | しごと道具箱',
        'description': '旧ページです。PDF、CSV、画像、URL確認などの軽量ツール一覧へ移動します。',
        'og_type': 'website',
        'robots': 'noindex,follow',
    },
    '/tools': {
        'title': '道具箱一覧 | しごと道具箱',
        'description': 'PDF、CSV/Excel、画像一括変換、画像クリーンアップ、SEO/URL確認など、仕事でたまに必要になる軽量ツールを用途別に選べます。',
        'og_type': 'website',
    },
    '/guide': {
        'title': 'ガイド一覧 | しごと道具箱',
        'description': 'PDF、CSV/Excel、画像、SEO/URL確認ツールの使い方や注意点をまとめたガイド一覧です。',
        'og_type': 'website',
        'breadcrumb_title': 'ガイド一覧',
    },
    '/guide/autofill': {
        'description': 'Jobcan AutoFill の使い方ガイドです。Excel から Jobcan へ勤怠データを自動入力する手順、制約、FAQ をまとめています。',
        'og_type': 'article',
    },
    '/guide/getting-started': {
        'description': 'Jobcan AutoFill のはじめての使い方ガイドです。テンプレート準備から実行前チェックまで順番に確認できます。',
        'og_type': 'article',
    },
    '/guide/excel-format': {
        'description': 'Jobcan AutoFill 用 Excel ファイルの形式ガイドです。日付、時刻、列構成、よくある形式エラーを確認できます。',
        'og_type': 'article',
    },
    '/guide/troubleshooting': {
        'description': 'Jobcan AutoFill のトラブルシューティングです。ログインエラー、形式エラー、タイムアウトなどの対処方法をまとめています。',
        'og_type': 'article',
    },
    '/guide/complete': {
        'description': 'Jobcan AutoFill の完全ガイドです。使い方、注意点、セキュリティ、導入判断の観点を 1 ページで確認できます。',
        'og_type': 'article',
    },
    '/guide/comprehensive-guide': {
        'description': 'Jobcan 勤怠入力の効率化を検討する方向けの総合ガイドです。導入背景、比較観点、運用設計まで整理しています。',
        'og_type': 'article',
    },
    '/guide/image-batch': {
        'description': '画像一括処理ツールの使い方ガイドです。複数画像のまとめ処理、対応形式、注意点、よくある質問を確認できます。',
        'og_type': 'article',
    },
    '/guide/pdf': {
        'description': 'PDF ツールの使い方ガイドです。結合、分割、圧縮、ページ整理の手順と注意点をまとめています。',
        'og_type': 'article',
    },
    '/guide/image-cleanup': {
        'description': '画像クリーンアップツールの使い方ガイドです。トリミングや不要部分の整理、利用時の注意点を確認できます。',
        'og_type': 'article',
    },
    '/guide/minutes': {
        'description': '議事録作成ツールの使い方ガイドです。入力の流れ、出力の整え方、業務で使う際の注意点をまとめています。',
        'og_type': 'article',
    },
    '/guide/seo': {
        'description': 'Web/SEO ツールの使い方ガイドです。メタ情報、OGP、sitemap、robots.txt を確認するときの進め方を整理しています。',
        'og_type': 'article',
    },
    '/guide/csv': {
        'description': 'CSV/Excel ツールの使い方ガイドです。変換、整形、列の確認、業務データを扱う際の注意点をまとめています。',
        'og_type': 'article',
    },
    '/faq': {
        'title': 'FAQ | しごと道具箱',
        'description': 'しごと道具箱のFAQです。ファイル処理、ブラウザ内処理、PDFパスワード付与、SEO/URL確認、広告表示についてまとめています。',
        'og_type': 'website',
        'breadcrumb_title': 'FAQ',
    },
    '/glossary': {
        'description': '勤怠管理、Jobcan、自動入力に関連する用語集です。打刻、勤務時間、Playwright などの用語をわかりやすく整理しています。',
        'og_type': 'website',
    },
    '/best-practices': {
        'title': 'ベストプラクティスガイド | Jobcan AutoFill',
        'description': 'Jobcan AutoFill を安全かつ効率的に使うためのベストプラクティスです。Excel 設計、運用、セキュリティの勘所をまとめています。',
        'og_type': 'article',
    },
    '/about': {
        'description': 'Jobcan AutoFill とは何か、このサイトの目的、対象ユーザー、運用方針をまとめたページです。',
        'og_type': 'website',
    },
    '/case-studies': {
        'title': '導入事例一覧 | Jobcan AutoFill',
        'description': 'Jobcan AutoFill の導入事例一覧です。勤怠入力の時短、月次締めの効率化、バックオフィス DX に関する実例を確認できます。',
        'og_type': 'website',
        'breadcrumb_title': '導入事例',
    },
    '/case-study/contact-center': {
        'description': 'コンタクトセンター部門での Jobcan AutoFill 導入事例です。月次処理の時短と運用改善の進め方をまとめています。',
        'og_type': 'article',
        'breadcrumb_title': 'コンタクトセンターの導入事例',
    },
    '/case-study/consulting-firm': {
        'description': 'コンサルティングファームでの Jobcan AutoFill 導入事例です。月次締めの短縮と社内展開の進め方を整理しています。',
        'og_type': 'article',
        'breadcrumb_title': 'コンサルティングファームの導入事例',
    },
    '/case-study/remote-startup': {
        'description': 'リモート中心のスタートアップでの Jobcan AutoFill 導入事例です。分散チームの勤怠入力を効率化した実例をまとめています。',
        'og_type': 'article',
        'breadcrumb_title': 'リモートスタートアップの導入事例',
    },
    '/blog': {
        'title': 'ブログ | Jobcan AutoFill',
        'description': 'Jobcan 自動入力、勤怠効率化、バックオフィス DX に関するブログ一覧です。導入判断や運用改善に役立つ記事を掲載しています。',
        'og_type': 'website',
        'breadcrumb_title': 'ブログ',
    },
    '/blog/implementation-checklist': {
        'description': 'Jobcan AutoFill 導入前に確認したい 10 のチェックポイントを整理した記事です。セキュリティ、社内運用、導入判断の論点をまとめています。',
        'og_type': 'article',
    },
    '/blog/automation-roadmap': {
        'description': '勤怠自動化を進めるためのロードマップ記事です。小さく始めて運用へつなげる進め方を整理しています。',
        'og_type': 'article',
    },
    '/blog/workstyle-reform-automation': {
        'description': '働き方改革とバックオフィス効率化を両立する自動化の考え方をまとめた記事です。勤怠 DX のヒントを確認できます。',
        'og_type': 'article',
    },
    '/blog/excel-attendance-limits': {
        'description': 'Excel だけで勤怠管理を続ける限界と、自動入力ツール導入で解消できる課題を整理した記事です。',
        'og_type': 'article',
    },
    '/blog/playwright-security': {
        'description': 'Playwright を使った自動入力のセキュリティ論点を整理した記事です。ブラウザ自動化を業務で扱う際の注意点を確認できます。',
        'og_type': 'article',
    },
    '/blog/month-end-closing-hell-and-automation': {
        'description': '月末処理が重くなる原因と自動化で改善できるポイントを整理した記事です。勤怠入力の時短策を具体的に確認できます。',
        'og_type': 'article',
    },
    '/blog/excel-format-mistakes-and-design': {
        'description': '勤怠 Excel で起きやすい形式ミスと、AutoFill で扱いやすい設計の考え方をまとめた記事です。',
        'og_type': 'article',
    },
    '/blog/convince-it-and-hr-for-automation': {
        'description': 'IT 部門や人事に自動化導入を説明するときの論点を整理した記事です。社内調整や稟議づくりに役立ちます。',
        'og_type': 'article',
    },
    '/blog/playwright-jobcan-challenges-and-solutions': {
        'description': 'Jobcan 自動入力で直面しやすい技術課題と対策をまとめた記事です。Playwright 運用の現実的なポイントを確認できます。',
        'og_type': 'article',
    },
    '/blog/jobcan-auto-input-tools-overview': {
        'description': 'Jobcan の勤怠入力を自動化する方法を比較した記事です。Excel マクロ、RPA、ブラウザ自動化の違いを整理しています。',
        'og_type': 'article',
    },
    '/blog/reduce-manual-work-checklist': {
        'description': '手作業を減らすための業務効率化チェックリストです。勤怠入力の自動化と運用改善の観点を整理しています。',
        'og_type': 'article',
    },
    '/blog/jobcan-month-end-tips': {
        'description': 'Jobcan の月末処理を楽にするためのチェックポイントをまとめた記事です。締め日前後の作業を効率化するヒントを紹介しています。',
        'og_type': 'article',
    },
    '/blog/jobcan-auto-input-dos-and-donts': {
        'description': 'Jobcan 自動入力でやってよいこと、避けたいことを整理した記事です。安全な運用と効率化のバランスを確認できます。',
        'og_type': 'article',
    },
    '/blog/month-end-closing-checklist': {
        'description': '月末の勤怠入力締めを楽にするための実務チェックリストです。混乱を減らし、入力作業を時短する観点をまとめています。',
        'og_type': 'article',
    },
    '/privacy': {
        'description': 'しごと道具箱のプライバシーポリシーです。ファイル処理、Cookie、アフィリエイト広告の取り扱いを説明しています。',
        'og_type': 'website',
        'robots': 'noindex,follow',
    },
    '/terms': {
        'description': 'しごと道具箱の利用規約です。サービスの利用条件、免責事項、外部リンクに関する方針をまとめています。',
        'og_type': 'website',
        'robots': 'noindex,follow',
    },
    '/contact': {
        'description': 'しごと道具箱のお問い合わせページです。ご質問や掲載内容に関する連絡先を案内しています。',
        'og_type': 'website',
        'robots': 'noindex,follow',
    },
    '/sitemap.html': {
        'description': 'しごと道具箱の HTML サイトマップです。主要ページ、ツール、ガイドへの導線を一覧で確認できます。',
        'og_type': 'website',
        'robots': 'noindex,follow',
    },
}


LEGACY_JOBCAN_PUBLIC_PATHS = frozenset(('/guide/autofill', '/guide/getting-started', '/guide/excel-format', '/guide/troubleshooting', '/guide/complete', '/guide/comprehensive-guide', '/best-practices', '/case-studies', '/case-study/contact-center', '/case-study/consulting-firm', '/case-study/remote-startup', '/blog/implementation-checklist', '/blog/automation-roadmap', '/blog/workstyle-reform-automation', '/blog/excel-attendance-limits', '/blog/playwright-security', '/blog/month-end-closing-hell-and-automation', '/blog/convince-it-and-hr-for-automation', '/blog/playwright-jobcan-challenges-and-solutions', '/blog/jobcan-auto-input-tools-overview', '/blog/reduce-manual-work-checklist', '/blog/jobcan-month-end-tips', '/blog/jobcan-auto-input-dos-and-donts', '/blog/month-end-closing-checklist'))


# Phase 1 public Oshigoto surface overrides.
SEO_DEFAULTS.update({
    '/about': {
        'title': 'サイトについて | しごと道具箱',
        'description': 'PDF、CSV、画像、ページ確認など、仕事でたまに必要になる作業をまとめた軽量ツール集です。',
        'og_type': 'website',
    },
    '/blog': {
        'title': 'ブログ | しごと道具箱',
        'description': 'Small notes for PDF, CSV, image, and page-check work.',
        'og_type': 'website',
        'breadcrumb_title': 'ブログ',
    },
    '/glossary': {
        'title': 'Glossary | しごと道具箱',
        'description': 'Glossary for PDF, CSV, image, and SEO/URL tool terms.',
        'og_type': 'website',
    },
})
for _legacy_path in LEGACY_JOBCAN_PUBLIC_PATHS:
    SEO_DEFAULTS[_legacy_path] = {
        'title': '道具箱一覧 | しごと道具箱',
        'description': 'Legacy page. The public site now focuses on PDF, CSV, image, and SEO/URL tools.',
        'og_type': 'website',
        'robots': 'noindex,follow',
    }

NOINDEX_PATHS = frozenset(
    path for path, config in SEO_DEFAULTS.items() if config.get('robots', '').startswith('noindex')
)


TOOL_APPLICATIONS = {
    '/tools/csv': {
        'name': 'CSV/Excel ツール',
        'category': 'BusinessApplication',
        'feature_list': [
            'CSV と XLSX の変換・整形',
            '列の確認や簡易加工をブラウザで実行',
        ],
    },
    '/tools/pdf': {
        'name': 'PDF ツール',
        'category': 'UtilitiesApplication',
        'feature_list': [
            '結合、分割、圧縮、ページ整理などの PDF 処理',
        ],
    },
    '/tools/image-batch': {
        'name': '画像一括処理ツール',
        'category': 'UtilitiesApplication',
        'feature_list': [
            '複数画像の一括リサイズや形式変換',
        ],
    },
    '/tools/image-cleanup': {
        'name': '画像クリーンアップツール',
        'category': 'UtilitiesApplication',
        'feature_list': [
            '画像整理、トリミング、不要部分のクリーニング',
        ],
    },
    '/tools/seo': {
        'name': 'Web/SEO ツール',
        'category': 'BusinessApplication',
        'feature_list': [
            'OGP、メタ情報、sitemap、robots.txt の確認と改善',
        ],
    },
    '/tools/minutes': {
        'name': '議事録作成ツール',
        'category': 'BusinessApplication',
        'feature_list': [
            '会議メモから議事録のたたき台を整理',
            '要点、決定事項、ToDo をまとめて出力',
        ],
    },
}


BLOG_ARTICLES = [
    {
        'path': '/blog/playwright-security',
        'title': 'Playwrightによるブラウザ自動化のセキュリティ 企業の安全性を守るための技術解説',
        'description': 'Playwrightによるブラウザ自動化のセキュリティ対策を詳しく解説。企業が安心して利用できる自動化ツールの技術的基盤、認証の安全性、データ保護の仕組みについて、開発者の視点から説明します。',
        'date_published': '2025-12-27',
        'section': 'セキュリティ・技術スタック',
    },
    {
        'path': '/blog/workstyle-reform-automation',
        'title': '勤怠管理の自動化が「働き方改革」を加速させる理由と、その本質的な価値',
        'description': '働き方改革の真の鍵は、勤怠入力のような見えない付帯業務の削減にあります。勤怠管理の自動化がなぜ企業のDXを加速させ、コンプライアンス強化につながるのかを解説します。',
        'date_published': '2025-12-25',
        'section': '業務効率化・DX',
    },
    {
        'path': '/blog/excel-attendance-limits',
        'title': 'Excelで勤怠を管理する限界と、API・自動化ツールを併用すべき理由',
        'description': 'Excelでの勤怠管理に残る手入力ミス、データ整合性、セキュリティ面の課題を整理し、自動化ツールと組み合わせて改善する考え方をまとめています。',
        'date_published': '2025-12-23',
        'section': '業務改善・効率化',
    },
    {
        'path': '/blog/implementation-checklist',
        'title': 'Jobcan AutoFill導入チェックリスト（10項目）',
        'description': '社内合意から運用定着までに確認したい10項目をまとめたセルフレビュー用リストです。稟議資料やセキュリティ審査の整理にも活用できます。',
        'date_published': '2025-02-17',
        'section': '導入・運用ガイド',
    },
    {
        'path': '/blog/automation-roadmap',
        'title': 'Jobcan自動化を社内展開するための90日ロードマップ',
        'description': 'トライアルから本番展開までの90日間で押さえるべきマイルストーンを、担当者・決裁者・現場メンバーの視点から整理した記事です。',
        'date_published': '2025-02-12',
        'section': '導入・運用ガイド',
    },
    {
        'path': '/blog/month-end-closing-checklist',
        'title': '月末の勤怠締め地獄を減らすための現実的なチェックリスト',
        'description': '月末の勤怠締めで起きがちな地獄パターンと、月の前半・中盤でやっておくと楽になる工夫を、開発者RTの実体験を交えて解説します。',
        'date_published': '2025-01-29',
        'section': '業務効率化・実務ノウハウ',
    },
    {
        'path': '/blog/jobcan-auto-input-dos-and-donts',
        'title': 'Jobcan 自動入力のやり方と、やってはいけないNG自動化',
        'description': 'Jobcanの自動入力方法と、やってはいけないNGパターンを整理した記事です。コンプライアンスとセキュリティを守りながら効率化する考え方をまとめています。',
        'date_published': '2025-01-28',
        'section': '実務ノウハウ・セキュリティ',
    },
    {
        'path': '/blog/jobcan-auto-input-tools-overview',
        'title': 'Jobcanの勤怠入力を楽にする方法まとめ 自動入力ツールの考え方と Jobcan AutoFill が目指しているもの',
        'description': 'Excelマクロ、汎用RPA、ブラウザ自動化ツールの違いを比較しながら、Jobcanの勤怠入力を自動化する方法を整理した比較ガイドです。',
        'date_published': '2025-01-25',
        'section': '自動化ツール・選定ガイド',
    },
    {
        'path': '/blog/reduce-manual-work-checklist',
        'title': 'まだ手入力していませんか 勤怠管理のムダを減らすための実務チェックリスト',
        'description': 'データ集め、整形、システム入力、確認の各フェーズで自動化できる部分とできない部分を整理した、勤怠管理の業務効率化チェックリストです。',
        'date_published': '2025-01-23',
        'section': '業務効率化・実務ノウハウ',
    },
    {
        'path': '/blog/jobcan-month-end-tips',
        'title': 'Jobcanの月末締めを少しでもラクにするための 7 つの実践テクニック',
        'description': '申請漏れや修正依頼を減らすリマインド運用、Excelテンプレ共有、固定パターンの整理など、月末締めを少しでも軽くする実践テクニックを紹介します。',
        'date_published': '2025-01-21',
        'section': '業務効率化・実務ノウハウ',
    },
    {
        'path': '/blog/month-end-closing-hell-and-automation',
        'title': 'Jobcanの月末締めが地獄になる3つの理由と、自動化で中和する方法',
        'description': '月末締めで起きやすい負荷の高いシナリオと、Jobcan AutoFillによる自動化で改善できるポイントを、具体例とともに解説します。',
        'date_published': '2025-01-20',
        'section': '業務効率化・実務ノウハウ',
    },
    {
        'path': '/blog/excel-format-mistakes-and-design',
        'title': '勤怠Excelで人がよくやるミス10選と、AutoFill側で潰している工夫',
        'description': '日付形式、時刻形式、空白行、全角・半角など、勤怠Excelで起こりやすいミスと、その対策としてAutoFill側で行っている工夫をまとめています。',
        'date_published': '2025-01-18',
        'section': '実務ノウハウ・技術解説',
    },
    {
        'path': '/blog/convince-it-and-hr-for-automation',
        'title': '情シス・人事・上長を味方につけて勤怠自動化を導入するための5ステップ',
        'description': '情シス・人事・上長を説得するための論点整理、稟議づくり、社内調整の進め方を実務目線でまとめた導入ガイドです。',
        'date_published': '2025-01-15',
        'section': '導入ガイド・実務ノウハウ',
    },
    {
        'path': '/blog/playwright-jobcan-challenges-and-solutions',
        'title': 'PlaywrightでJobcanを自動操作する時にハマったポイントと、その解決パターン',
        'description': 'PlaywrightでJobcanを自動操作する際に遭遇した技術的な課題と、その解決パターンをエンジニア向けにまとめています。',
        'date_published': '2025-01-12',
        'section': '技術スタック・Playwright',
    },
]


BLOG_ARTICLE_MAP = {
    article['path']: article
    for article in BLOG_ARTICLES
}


ARTICLE_SCHEMA_PAGES = {
    **BLOG_ARTICLE_MAP,
    '/case-study/contact-center': {
        'title': 'コンタクトセンターで月末処理を平準化した導入ケース',
        'description': 'コンタクトセンターが Jobcan AutoFill の導入を想定したケーススタディです。シフト変更が集中する現場で、入力前チェックと差し戻し削減をどう整理したかをまとめています。',
        'date_published': '2025-02-24',
        'section': '導入事例',
    },
    '/case-study/consulting-firm': {
        'title': 'コンサルティングファームで月末締めを平準化した導入ケース',
        'description': 'コンサルティングファームが Jobcan AutoFill の導入を想定したケーススタディです。月末の集中作業をどう分散し、社内展開と確認フローを整えたかを整理しています。',
        'date_published': '2025-01-10',
        'section': '導入事例',
    },
    '/case-study/remote-startup': {
        'title': 'リモート中心チームで入力負荷を分散した導入ケース',
        'description': 'リモート中心のスタートアップが Jobcan AutoFill の導入を想定したケーススタディです。非同期運用でも締め日前の確認負荷を下げる進め方をまとめています。',
        'date_published': '2025-01-08',
        'section': '導入事例',
    },
    '/guide/autofill': {
        'title': 'Jobcan AutoFill の使い方ガイド',
        'description': 'Jobcan AutoFill の使い方ガイドです。Excel から Jobcan へ勤怠データを自動入力する手順、制約、FAQ をまとめています。',
        'section': 'ガイド',
    },
    '/guide/getting-started': {
        'title': 'はじめての使い方',
        'description': 'Jobcan AutoFill のはじめての使い方ガイドです。テンプレート準備から実行前チェックまで順番に確認できます。',
        'section': 'ガイド',
    },
    '/guide/excel-format': {
        'title': 'Excelファイルの作成方法',
        'description': 'Jobcan AutoFill 用 Excel ファイルの形式ガイドです。日付、時刻、列構成、よくある形式エラーを確認できます。',
        'section': 'ガイド',
    },
    '/guide/troubleshooting': {
        'title': 'トラブルシューティング',
        'description': 'Jobcan AutoFill のトラブルシューティングです。ログインエラー、形式エラー、タイムアウトなどの対処方法をまとめています。',
        'section': 'ガイド',
    },
    '/guide/csv': {
        'title': 'CSV/Excelツールの使い方ガイド',
        'description': 'CSV/Excel ツールの使い方ガイドです。変換、整形、列の確認、業務データを扱う際の注意点をまとめています。',
        'section': 'ガイド',
    },
    '/guide/image-batch': {
        'title': '画像一括変換ツールの使い方ガイド',
        'description': '画像一括処理ツールの使い方ガイドです。複数画像のまとめ処理、対応形式、注意点、よくある質問を確認できます。',
        'section': 'ガイド',
    },
    '/guide/image-cleanup': {
        'title': '画像クリーンアップツールの使い方ガイド',
        'description': '画像クリーンアップツールの使い方ガイドです。トリミングや不要部分の整理、利用時の注意点を確認できます。',
        'section': 'ガイド',
    },
    '/guide/pdf': {
        'title': 'PDFツールの使い方ガイド',
        'description': 'PDF ツールの使い方ガイドです。結合、分割、圧縮、ページ整理の手順と注意点をまとめています。',
        'section': 'ガイド',
    },
    '/guide/seo': {
        'title': 'Web/SEOツールの使い方ガイド',
        'description': 'Web/SEO ツールの使い方ガイドです。メタ情報、OGP、sitemap、robots.txt を確認するときの進め方を整理しています。',
        'section': 'ガイド',
    },
    '/guide/complete': {
        'title': 'Jobcan AutoFill 完全ガイド',
        'description': 'Jobcan AutoFill の完全ガイドです。使い方、注意点、セキュリティ、導入判断の観点を 1 ページで確認できます。',
        'section': 'ガイド',
    },
    '/guide/comprehensive-guide': {
        'title': 'Jobcan勤怠管理を効率化する総合ガイド',
        'description': 'Jobcan 勤怠入力の効率化を検討する方向けの総合ガイドです。導入背景、比較観点、運用設計まで整理しています。',
        'section': 'ガイド',
    },
    '/best-practices': {
        'title': 'ベストプラクティスガイド',
        'description': 'Jobcan AutoFill を安全かつ効率的に使うためのベストプラクティスです。Excel 設計、運用、セキュリティの勘所をまとめています。',
        'section': 'ベストプラクティス',
    },
}


RELATED_CONTENT = {
    '/': {
        'title': 'まず使いたい道具',
        'intro': '仕事でたまに必要になる小さな作業を、用途別に選べます。',
        'links': [
            {'path': '/tools/pdf', 'label': 'PDFツール', 'description': '結合、分割、抽出、圧縮、パスワード付与を扱えます。'},
            {'path': '/tools/csv', 'label': 'CSV/Excelツール', 'description': 'CSVやExcelの変換、重複削除、列整理に使えます。'},
            {'path': '/tools/image-batch', 'label': '画像一括変換', 'description': '画像形式変換やリサイズをまとめて処理できます。'},
            {'path': '/tools/seo', 'label': 'SEO/URL確認', 'description': 'OGP、meta、sitemap、robotsを確認できます。'},
        ],
    },
    '/blog': {
        'title': 'ブログから次に広げる',
        'intro': '記事を読んだあとに、手順や事例もあわせて確認しやすいページです。',
        'links': [
            {'path': '/guide', 'label': 'ガイド一覧', 'description': 'PDF、CSV、画像、SEO確認の使い方を確認できます。'},
            {'path': '/tools', 'label': '道具箱一覧', 'description': '仕事でたまに必要になる軽量ツールを比較できます。'},
            {'path': '/glossary', 'label': '用語集', 'description': 'ファイル変換やWeb確認まわりの基本用語を整理できます。'},
            {'path': '/faq', 'label': 'FAQ', 'description': 'ファイル処理や広告表示の考え方を確認できます。'},
        ],
    },
    '/guide': {
        'title': 'ガイドとあわせて見る',
        'intro': '実務に落とし込むときに見比べたいページをまとめています。',
        'links': [
            {'path': '/faq', 'label': 'FAQ', 'description': '利用前に確認したい質問と回答をまとめています。'},
            {'path': '/glossary', 'label': '用語集', 'description': '用語の意味や文脈を短時間で確認できます。'},
            {'path': '/blog', 'label': 'ブログ', 'description': '導入判断や運用改善の背景を記事で補足できます。'},
            {'path': '/tools', 'label': 'ツール一覧', 'description': '関連する周辺ツールを用途別に確認できます。'},
        ],
    },
    '/glossary': {
        'title': '用語集の次に見る',
        'intro': '言葉の意味を押さえたあとに、手順や実務への落とし込みを確認できるページです。',
        'links': [
            {'path': '/guide/autofill', 'label': 'AutoFillガイド', 'description': '実際の使い方と入力前の確認事項をまとめています。'},
            {'path': '/guide/excel-format', 'label': 'Excel形式ガイド', 'description': 'よくある形式ミスと修正ポイントを確認できます。'},
            {'path': '/blog/reduce-manual-work-checklist', 'label': '手作業削減チェックリスト', 'description': '実務改善の観点から自動化対象を整理できます。'},
            {'path': '/tools/csv', 'label': 'CSV/Excelツール', 'description': 'ExcelやCSVの整形に使える補助ツールです。'},
        ],
    },
    '/best-practices': {
        'title': '運用設計とあわせて見る',
        'intro': 'ベストプラクティスを読んだあとに、具体的な手順や事例を確認しやすいページです。',
        'links': [
            {'path': '/guide/excel-format', 'label': 'Excel形式ガイド', 'description': '入力前に整えておきたいファイル設計の要点を確認できます。'},
            {'path': '/guide/complete', 'label': '完全ガイド', 'description': '導入判断、使い方、注意点をまとめて確認できます。'},
            {'path': '/blog/jobcan-auto-input-dos-and-donts', 'label': '自動入力の注意点', 'description': '避けたい運用パターンと安全な進め方を整理できます。'},
            {'path': '/case-studies', 'label': '導入事例', 'description': '運用ルールを定着させるイメージをケース形式で確認できます。'},
        ],
    },
    '/case-studies': {
        'title': '事例とあわせて確認する',
        'intro': '事例を読んだあとに、手順や関連ツールを確認しやすいページです。',
        'links': [
            {'path': '/autofill', 'label': 'Jobcan AutoFill', 'description': '実際の入力フローとアップロード要件を確認できます。'},
            {'path': '/guide/getting-started', 'label': 'はじめての使い方', 'description': '初回導入時の流れを順番に確認できます。'},
            {'path': '/tools', 'label': 'ツール一覧', 'description': '周辺業務の効率化に使える関連ツールも確認できます。'},
            {'path': '/blog/jobcan-auto-input-tools-overview', 'label': '自動入力ツール比較', 'description': '方式ごとの違いと選び方の整理に役立ちます。'},
        ],
    },
    '/tools': {
        'title': 'ツール利用前後に役立つページ',
        'intro': '使い方や関連情報を補足するページをまとめています。',
        'links': [
            {'path': '/guide', 'label': 'ガイド一覧', 'description': '使い方や注意点をまとめて確認できます。'},
            {'path': '/tools/pdf', 'label': 'PDFツール', 'description': 'PDFの結合・分割・圧縮に使えます。'},
            {'path': '/faq', 'label': 'FAQ', 'description': '利用前によくある疑問を整理できます。'},
            {'path': '/privacy', 'label': 'プライバシーポリシー', 'description': 'ファイル処理と広告の取り扱いを確認できます。'},
        ],
    },
    '/blog/month-end-closing-checklist': {
        'title': '月末締めの改善に役立つ関連ページ',
        'intro': 'チェックリストを実務に落とし込むときに一緒に確認したいページです。',
        'links': [
            {'path': '/guide/excel-format', 'label': 'Excel形式ガイド', 'description': '入力前に整えておきたいExcelの設計ポイントを確認できます。'},
            {'path': '/autofill', 'label': 'Jobcan AutoFill', 'description': '月末の一括入力をどう短縮するかを具体的に確認できます。'},
            {'path': '/case-studies', 'label': '導入事例', 'description': '月末負荷の改善イメージを他社事例から確認できます。'},
            {'path': '/blog/jobcan-month-end-tips', 'label': '月末締めテクニック', 'description': '月次運用の細かな改善アイデアを補足できます。'},
        ],
    },
    '/blog/jobcan-auto-input-dos-and-donts': {
        'title': '安全な運用に役立つ関連ページ',
        'intro': 'やってよいこと・避けたいことを整理したあとに見ておきたいページです。',
        'links': [
            {'path': '/guide/autofill', 'label': 'AutoFillガイド', 'description': '使い方、制約、FAQをまとめて確認できます。'},
            {'path': '/best-practices', 'label': 'ベストプラクティス', 'description': '現場運用に落とし込むときの基本方針を確認できます。'},
            {'path': '/faq', 'label': 'FAQ', 'description': '運用前に確認したい疑問点を整理できます。'},
            {'path': '/glossary', 'label': '用語集', 'description': '関連用語や前提知識を短時間で確認できます。'},
        ],
    },
    '/blog/jobcan-auto-input-tools-overview': {
        'title': '比較検討の次に見るページ',
        'intro': 'ツールの違いを把握したあとに、関連ガイドや事例も確認しやすいページです。',
        'links': [
            {'path': '/tools', 'label': 'ツール一覧', 'description': 'AutoFill以外の周辺ツールも含めて比較できます。'},
            {'path': '/guide/getting-started', 'label': 'はじめての使い方', 'description': '導入前に押さえるべき手順を確認できます。'},
            {'path': '/case-studies', 'label': '導入事例', 'description': '業種別の活用パターンを比較できます。'},
            {'path': '/autofill', 'label': 'Jobcan AutoFill', 'description': '実際の入力フローと注意点を確認できます。'},
        ],
    },
}


RELATED_CONTENT_PREFIXES = (
    (
        '/blog/',
        {
            'title': '関連記事と道具箱',
            'intro': '記事を読んだあとに、関連ツールや用語もあわせて確認できます。',
            'links': [
                {'path': '/tools', 'label': '道具箱一覧', 'description': 'PDF、CSV、画像、SEO確認の各ツールを選べます。'},
                {'path': '/guide', 'label': 'ガイド一覧', 'description': '使い方や注意点をまとめています。'},
                {'path': '/glossary', 'label': '用語集', 'description': '関連する基本用語を短時間で整理できます。'},
                {'path': '/faq', 'label': 'FAQ', 'description': 'ファイル処理や広告表示の考え方を確認できます。'},
            ],
        },
    ),
    (
        '/guide/',
        {
            'title': 'ガイドとあわせて確認する',
            'intro': '手順確認のあとに、用語や関連ツールまで広げて確認しやすいページです。',
            'links': [
                {'path': '/blog', 'label': 'ブログ', 'description': '導入判断や運用改善の背景を記事で補足できます。'},
                {'path': '/glossary', 'label': '用語集', 'description': '前提知識を短時間で確認できます。'},
                {'path': '/faq', 'label': 'FAQ', 'description': 'よくある疑問をまとめて確認できます。'},
                {'path': '/tools', 'label': 'ツール一覧', 'description': '周辺業務に使える関連ツールも確認できます。'},
            ],
        },
    ),
    (
        '/case-study/',
        {
            'title': '事例の次に確認したいページ',
            'intro': '事例を読んだあとに、手順や比較記事も確認しやすいページです。',
            'links': [
                {'path': '/tools', 'label': '道具箱一覧', 'description': 'PDF、CSV、画像、SEO確認の各ツールを選べます。'},
                {'path': '/guide', 'label': 'ガイド一覧', 'description': '使い方や注意点をまとめています。'},
                {'path': '/faq', 'label': 'FAQ', 'description': 'ファイル処理や広告表示の考え方を確認できます。'},
                {'path': '/privacy', 'label': 'プライバシーポリシー', 'description': 'データの扱いを確認できます。'},
            ],
        },
    ),
)


def get_seo_defaults(path):
    config = deepcopy(SEO_DEFAULTS.get(path, {}))
    if 'og_type' not in config:
        config['og_type'] = get_og_type(path)
    if 'robots' not in config:
        config['robots'] = 'index,follow'
    return config


def is_noindex_path(path):
    return path in NOINDEX_PATHS


def get_og_type(path):
    if path.startswith('/blog/') or path.startswith('/case-study/') or (path.startswith('/guide/') and path != '/guide'):
        return 'article'
    return 'website'


def get_page_kind(path):
    if path == '/':
        return 'homepage'
    if path in ('/blog', '/case-studies', '/guide'):
        return 'collection'
    if path.startswith('/blog/') or path.startswith('/case-study/') or (path.startswith('/guide/') and path != '/guide'):
        return 'article'
    if path in ('/faq', '/glossary', '/best-practices', '/about'):
        return 'resource'
    if path == '/autofill' or path.startswith('/tools/'):
        return 'tool'
    return 'page'


def build_breadcrumb_items(path, page_title='', breadcrumb_title=''):
    label = (breadcrumb_title or page_title or path.split('/')[-1] or 'ホーム').strip()
    items = [{'name': 'ホーム', 'url': '/'}]

    if path == '/':
        return items
    if path == '/tools':
        items.append({'name': 'ツール一覧', 'url': '/tools'})
        return items
    if path.startswith('/tools/'):
        items.append({'name': 'ツール一覧', 'url': '/tools'})
        items.append({'name': label, 'url': path})
        return items
    if path == '/guide':
        items.append({'name': 'ガイド一覧', 'url': '/guide'})
        return items
    if path.startswith('/guide/'):
        items.append({'name': 'ガイド一覧', 'url': '/guide'})
        items.append({'name': label, 'url': path})
        return items
    if path == '/blog':
        items.append({'name': 'ブログ', 'url': '/blog'})
        return items
    if path.startswith('/blog/'):
        items.append({'name': 'ブログ', 'url': '/blog'})
        items.append({'name': label, 'url': path})
        return items
    if path == '/case-studies':
        items.append({'name': '導入事例', 'url': '/case-studies'})
        return items
    if path.startswith('/case-study/'):
        items.append({'name': '導入事例', 'url': '/case-studies'})
        items.append({'name': label, 'url': path})
        return items

    items.append({'name': label, 'url': path})
    return items


def get_web_application_schema(path, title, description, base_url):
    config = TOOL_APPLICATIONS.get(path)
    if not config:
        return None
    return {
        '@context': 'https://schema.org',
        '@type': 'WebApplication',
        'name': config['name'],
        'url': f'{base_url}{path}',
        'applicationCategory': config['category'],
        'operatingSystem': 'Web Browser',
        'isAccessibleForFree': True,
        'description': description,
        'offers': {
            '@type': 'Offer',
            'price': '0',
            'priceCurrency': 'JPY',
        },
        'featureList': config['feature_list'],
    }


def get_blog_articles(limit=None):
    articles = sorted(
        BLOG_ARTICLES,
        key=lambda article: article['date_published'],
        reverse=True,
    )
    if limit is not None:
        return deepcopy(articles[:limit])
    return deepcopy(articles)


def get_article_schema(path, base_url, default_title='', default_description=''):
    article = ARTICLE_SCHEMA_PAGES.get(path)
    if not article:
        return None

    title = article.get('title') or default_title
    description = article.get('description') or default_description
    published = article.get('date_published')
    modified = article.get('date_modified', published)
    url = f'{base_url}{path}'
    schema = {
        '@context': 'https://schema.org',
        '@type': 'Article',
        'headline': title,
        'description': description,
        'inLanguage': 'ja-JP',
        'mainEntityOfPage': {
            '@type': 'WebPage',
            '@id': url,
        },
        'url': url,
        'author': {
            '@type': 'Organization',
            'name': 'しごと道具箱',
        },
        'publisher': {
            '@type': 'Organization',
            'name': 'しごと道具箱',
        },
    }
    if published:
        schema['datePublished'] = published
    if modified:
        schema['dateModified'] = modified
    if article.get('section'):
        schema['articleSection'] = article['section']
    return schema


PUBLIC_RELATED_CONTENT_OVERRIDES = {
    '/glossary': {
        'title': 'Related public pages',
        'intro': 'After checking terms, open the public tools or guides.',
        'links': [
            {'path': '/tools', 'label': 'Tools', 'description': 'Open the public tool list.'},
            {'path': '/guide', 'label': 'Guides', 'description': 'Read public tool guides.'},
            {'path': '/faq', 'label': 'FAQ', 'description': 'Check file and ad handling.'},
            {'path': '/privacy', 'label': 'Privacy', 'description': 'Check data handling.'},
        ],
    },
}


def get_related_content(path):
    if path in LEGACY_JOBCAN_PUBLIC_PATHS:
        return None
    if path in PUBLIC_RELATED_CONTENT_OVERRIDES:
        return deepcopy(PUBLIC_RELATED_CONTENT_OVERRIDES[path])
    section = RELATED_CONTENT.get(path)
    if section:
        return deepcopy(section)

    for prefix, config in RELATED_CONTENT_PREFIXES:
        if path.startswith(prefix):
            return deepcopy(config)

    return None

# Phase 6 public-surface cleanup overrides.
# Keep legacy route records for redirects, but make indexable public pages generic.
_PHASE6_PUBLIC_SEO_OVERRIDES = {
    '/blog': {
        'title': 'ブログ | しごと道具箱',
        'description': 'PDF、CSV/Excel、画像、SEO/URL確認など、仕事でたまに必要になる小さな作業のヒントをまとめるブログです。',
        'og_type': 'website',
        'breadcrumb_title': 'ブログ',
    },
    '/glossary': {
        'title': '用語集 | しごと道具箱',
        'description': 'PDF、CSV/Excel、画像、SEO/URL確認など、しごと道具箱で扱うファイル処理とWeb確認の基本用語を短く整理した用語集です。',
        'og_type': 'website',
    },
    '/blog/excel-format-mistakes-and-design': {
        'title': 'CSV/Excelファイルを扱うときのよくあるミス | しごと道具箱',
        'description': 'CSVやExcelファイルで起きやすい文字化け、列ずれ、空白行、日付形式の揺れなどを、作業前に見直しやすいチェックリストとして整理します。',
        'og_type': 'article',
    },
}
SEO_DEFAULTS.update(_PHASE6_PUBLIC_SEO_OVERRIDES)

_PHASE6_PUBLIC_BLOG_ARTICLE = {
    'path': '/blog/excel-format-mistakes-and-design',
    'title': 'CSV/Excelファイルを扱うときのよくあるミス',
    'description': 'CSVやExcelファイルで起きやすい文字化け、列ずれ、空白行、日付形式の揺れなどを、作業前に見直しやすいチェックリストとして整理します。',
    'date_published': '2025-01-18',
    'section': 'CSV/Excel',
}
for _idx, _article in enumerate(BLOG_ARTICLES):
    if _article.get('path') == _PHASE6_PUBLIC_BLOG_ARTICLE['path']:
        BLOG_ARTICLES[_idx] = dict(_PHASE6_PUBLIC_BLOG_ARTICLE)
        break
BLOG_ARTICLE_MAP[_PHASE6_PUBLIC_BLOG_ARTICLE['path']] = dict(_PHASE6_PUBLIC_BLOG_ARTICLE)
ARTICLE_SCHEMA_PAGES[_PHASE6_PUBLIC_BLOG_ARTICLE['path']] = dict(_PHASE6_PUBLIC_BLOG_ARTICLE)

PUBLIC_RELATED_CONTENT_OVERRIDES['/glossary'] = {
    'title': '用語集の次に見る',
    'intro': '言葉の意味を確認したら、実際のツールやガイドもあわせて開けます。',
    'links': [
        {'path': '/tools/pdf', 'label': 'PDFツール', 'description': '結合、分割、圧縮、ページ整理に使えます。'},
        {'path': '/tools/csv', 'label': 'CSV/Excelツール', 'description': 'CSVやExcelの変換、重複削除、列整理に使えます。'},
        {'path': '/tools/image-batch', 'label': '画像一括変換', 'description': '画像形式変換やリサイズをまとめて処理できます。'},
        {'path': '/tools/seo', 'label': 'SEO/URL確認', 'description': 'OGP、meta、sitemap、robotsを確認できます。'},
    ],
}
