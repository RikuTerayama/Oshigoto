# Phase 9.10A Final Integration / Release Candidate Hardening

Date: 2026-08-08

Decision: **GO for merge and staged production deploy, with the post-deploy checks below**

## Release boundary

- Repository: `RikuTerayama/Oshigoto`
- Starting point: `origin/main` at merge commit `a44ec00`
- Required Phase 9.9 commit: `7a66688` is contained in the starting commit.
- Release branch: `release/phase-9-final-hardening`
- Scope: integration checks and low-risk hardening only. No new public tool, ad inventory, or monetization placement was added.

## Public route and SEO result

- 28 public HTML routes return 200 in the local release audit.
- 24 indexable routes are present in `sitemap.xml`.
- `/privacy`, `/terms`, `/contact`, and `/sitemap.html` remain public and `noindex,follow`.
- The release fixes an inconsistency where `/privacy`, `/terms`, and `/contact` were both `noindex` and listed in the XML sitemap. They are now excluded from the sitemap.
- Every public HTML page has one H1, one non-empty title, one non-empty meta description, and a self-referencing HTTPS canonical on `oshigoto.onrender.com`.
- Titles and meta descriptions are unique across the audited public HTML inventory.
- All non-home pages expose BreadcrumbList JSON-LD.
- Tool pages expose WebApplication or SoftwareApplication JSON-LD.
- Guide and article pages expose Article JSON-LD.
- No Review or AggregateRating schema is emitted.
- The audit resolved 28 distinct internal link targets; none returned 404.
- `/autofill` remains a 301 redirect to `/tools`, is absent from the sitemap, and remains disallowed in `robots.txt`.
- `robots.txt` advertises `https://oshigoto.onrender.com/sitemap.xml`.

## Affiliate and advertising result

- The shared head loads the AdSense ownership script exactly once per audited HTML page.
- Publisher ID remains `ca-pub-4232725615106709`.
- No ad slot or ad density change was made in this phase.
- Eligible routes render at most one Amazon recommendation and exactly one when the release test tag is present.
- Hard-excluded business, about, contact, privacy, and terms routes render no Amazon recommendation.
- The page-render path uses the deterministic single-recommendation builder and does not call the Creators API.
- Obsolete recent-history cookie handling, unused API-result normalization, and unused legacy context payloads were removed from `app.py`.
- Creators API service functions remain in `lib/amazon_creators.py` as non-rendering compatibility code; deleting that module surface was intentionally deferred.
- Eligible routes render at most one A8 creative.
- Hard-excluded routes render no A8 creative.
- A8 exact creative HTML was not edited.
- A8 creative checksums remain:
  - `a8-01`: `63CB848BAADDAEB5F4BE77F4A56CDEC9EEB8A2F6882F46F64F2E5B179C07C8B8`
  - `a8-02`: `96CC5C6909169CEB8DE511B572118149DC11B37315A20460096C5562AFE8AB05`
  - `a8-03`: `E6D9F2692A1A94E1ED6E1939AB2598369FF12C91838CC94ADF60C58ABD6F016C`
  - `a8-04`: `ACB6ADB31D5D0662FB5D14A9A8D8C8A09FE1C754022F061EBFD416E971265A29`
  - `a8-05`: `035C1ED40219AC565559BFE1A9F4550BD8B86D3A51F68EA6AD2F1CE2039F93B9`
- The legacy `rot3.a8.net` fallback remains only in the explicit fallback partial and is not rendered by catalog-eligible release pages.

## NO-GO features

- OCR remains NO-GO and non-public: tool, guide, API, and internal spike paths return 404.
- Background removal remains NO-GO and non-public: tool, guide, API, and internal spike paths return 404.
- Temporary OCR and background-removal vendor payloads are absent.
- `/api/pdf/unlock` returns 404.
- Public PDF pages contain no unlock/decrypt route contract.

## PDF and multi-user safety

- Browser PDF page deletion and rotation pure-function tests pass.
- Browser console inspection found a release-blocking JavaScript scope collision on `/tools/pdf`: three classic scripts declared the same top-level encrypted-PDF message constant. Later compression and image-extraction scripts stopped at parse time.
- Fix: PDF render, compression, and image-extraction helpers now use feature-specific constant and function names.
- `scripts/test_pdf_script_scope.js` executes the six PDF operation scripts in one shared classic-script scope and prevents the collision from returning.
- `PDF_LIB_PATH` is not a Render or production runtime variable. It is only an optional input for `scripts/test_pdf_page_ops_real.js`, which injects a local `pdf-lib 1.17.1` CommonJS build into a Node-only integration test.
- Production loads `pdf-lib 1.17.1` in the browser from the existing cdnjs URL; the optional real Node test cannot run locally unless that matching build is supplied.
- The deterministic PDF page-operation test remains in predeploy and does not claim the optional real-library integration test passed.
- The multi-user safety test previously stalled before Flask received an oversized multipart request.
- Root cause: the test replaced Python's global `tempfile.tempdir` with a newly created process-local directory. Werkzeug spools multipart bodies above 500 KB through `TemporaryFile`, which blocked on this Windows/OneDrive setup.
- Fix: the test no longer overrides global temporary-file settings and explicitly closes each upload stream.
- Production PDF limits and route behavior were not changed.
- Full multi-user safety test now completes in approximately 4 seconds in this environment.
- Verified outcomes: valid requests 200, busy guard 429, oversized upload 413, extra file 400, invalid PDF 422, encrypted input 400, excessive page count 413.

## Responsive and browser result

- Browser QA covered 28 public pages at 9 viewports: 320x568, 375x667, 390x844, 393x852, 430x932, 768x1024, 1220x900, 1366x900, and 1440x900.
- Total page/viewport combinations: 252.
- Every combination rendered one visible H1 and non-empty body content.
- No horizontal document overflow was found when measured against `window.innerWidth`.
- The apparent 15 px difference on `/tools/image-compress` at mobile widths was the reserved vertical scrollbar gutter, not horizontal overflow.
- No responsive CSS change was required.
- A fresh `/tools/pdf` load after the scope fix produced no browser console errors.

## Predeploy and CI result

- `scripts/test_release_candidate.py` now enforces the public route, SEO, schema, internal-link, AdSense, Amazon, A8, and NO-GO contracts.
- `scripts/predeploy.py` now runs compile/import, manifest, smoke, deploy smoke, release audit, AdSense preflight, A8, Amazon, PDF page operations, image compression, image format, QR, OCR NO-GO, and background-removal NO-GO checks.
- The predeploy workflow now installs Node 20 and calls the same local predeploy entry point.
- Python bytecode output is redirected to the OS temporary directory during predeploy so OneDrive locks on repository `__pycache__` files do not create false failures.
- The full multi-user safety test remains an explicit release test rather than an unconditional PR gate.
- The optional real `pdf-lib` integration test remains explicit and must not be reported as passing without `PDF_LIB_PATH`.

## Post-deploy checklist

1. Confirm Render deployed the release merge commit, not an earlier cached build.
2. Confirm `/healthz`, `/`, `/tools`, `/tools/pdf`, `/tools/image-compress`, and `/tools/qr-code` return 200.
3. Confirm `/autofill` returns 301 to `/tools`.
4. Confirm OCR and background-removal public paths return 404.
5. Confirm `/api/pdf/unlock` returns 404.
6. Confirm `sitemap.xml` contains the 24 indexable routes and excludes privacy, terms, contact, OCR, background removal, and autofill.
7. Confirm the production environment contains the intended `AMAZON_ASSOCIATE_TAG`; missing tags fail closed by hiding Amazon.
8. Confirm one Amazon recommendation and one A8 creative at most on eligible pages, with no affiliate output on hard-excluded pages.
9. Confirm the AdSense account recognizes the unchanged publisher loader; site approval and serving status remain external console checks.
10. Run one real browser PDF deletion/rotation operation in production because those operations depend on existing external cdnjs resources.

## Remaining risks

- Browser PDF functionality still depends on existing third-party CDN availability for pdf-lib, pdf.js, and JSZip. This phase did not vendor or add SRI for those assets.
- The optional real Node pdf-lib integration test is not self-contained in the repository.
- Legacy Amazon grid/template compatibility branches and related CSS remain dormant. Removing them would be broader than release hardening and should be a separate cleanup with visual regression coverage.
- AdSense approval, fill, policy status, and A8 advertiser-side availability cannot be established by repository tests.
- Render deploy freshness and production response headers require post-merge live verification.

## Release conclusion

The repository is a release candidate. The two confirmed integration defects found in this phase were fixed: noindex URLs are no longer emitted in the XML sitemap, and the Windows multipart safety test no longer blocks before reaching Flask. Public route, SEO, affiliate, NO-GO, and responsive contracts are now executable predeploy checks rather than report-only observations.
