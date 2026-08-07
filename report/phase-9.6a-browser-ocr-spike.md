# Phase 9.6A Browser OCR Technical Spike

Date: 2026-08-07
Decision: **NO-GO for public release**

## Executive summary

Tesseract.js 7.0.0 can run entirely in Chromium with local worker, WASM, and language models. Cancellation by worker termination and stale-result suppression worked, and English OCR was accurate on generated fixtures. However, Japanese exact/normalized CER remained 54.46-58.65% because of inserted spaces and some substitutions. Physical mobile, Firefox, and Safari/WebKit were not available. The public OCR feature must therefore remain absent. Per the Phase policy, the temporary 9.07 MB OCR vendor payload and internal harness were removed before commit; only this report and public non-exposure regression checks remain.

## Accuracy matrix

Normalization is fixed to CRLF-to-LF, trailing-space removal per line, and NFC. It does not remove internal spaces or correct OCR output.

| Fixture | Preprocess | CER | Load | OCR | Total | Confidence |
|---|---:|---:|---:|---:|---:|---:|
| English clean | original | 0.34% | 218 ms | 891 ms | 2,161 ms | 95% |
| English clean | grayscale | 0.34% | 196 ms | 888 ms | 1,156 ms | 95% |
| English small | original | 0.34% | 200 ms | 761 ms | 1,011 ms | 95% |
| English small | grayscale | 0.34% | 228 ms | 823 ms | 1,114 ms | 95% |
| English low contrast | original | 0.33% | 232 ms | 848 ms | 1,117 ms | 95% |
| English low contrast | grayscale | 0.33% | 219 ms | 828 ms | 1,135 ms | 95% |
| English tilted | original | 0.71% | 237 ms | 766 ms | 1,047 ms | 95% |
| English tilted | grayscale | 0.71% | 184 ms | 872 ms | 1,122 ms | 95% |
| Japanese clean | original | 58.65% | 244 ms | 907 ms | 1,291 ms | 91% |
| Japanese clean | grayscale | 58.65% | 242 ms | 917 ms | 1,211 ms | 91% |
| Japanese small | original | 57.02% | 233 ms | 746 ms | 1,039 ms | 92% |
| Japanese small | grayscale | 58.77% | 228 ms | 811 ms | 1,097 ms | 92% |
| Japanese low contrast | original | 56.45% | 249 ms | 732 ms | 1,036 ms | 91% |
| Japanese low contrast | grayscale | 56.45% | 280 ms | 838 ms | 1,176 ms | 93% |
| Japanese tilted | original | 54.46% | 269 ms | 631 ms | 967 ms | 90% |
| Japanese tilted | grayscale | 56.25% | 240 ms | 843 ms | 1,140 ms | 92% |
| Mixed jpn+eng | original | 3.59% | 299 ms | 994 ms | 1,346 ms | 91% |
| Mixed jpn+eng | grayscale | 4.10% | 257 ms | 1,065 ms | 1,376 ms | 91% |

The final newline contributes roughly 0.3-0.7 percentage points to English CER. Japanese CER is not explained by the final newline; inserted inter-character/inter-word spaces and substitutions dominate.

## Size and special fixtures

| Fixture | Image | File | CER | Load | OCR | Total | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| 1MP | 1000x1000 | 36.1 KB | 6.12% | 265 ms | 393 ms | 689 ms | completed |
| 4MP | 2000x2000 | 102.5 KB | 5.56% | 311 ms | 669 ms | 1,077 ms | completed |
| 8MP | 3200x2500 | 184.1 KB | 5.00% | 344 ms | 1,049 ms | 1,575 ms | completed |
| Mobile screenshot style | 1170x2532 | 108.0 KB | 6.30% | 336 ms | 821 ms | 1,254 ms | completed |
| Table style | 1800x1200 | 85.0 KB | 40.51% | 258 ms | 1,050 ms | 1,359 ms | text only; structure not preserved |

## Assets and integrity observed during the spike

| Asset | Bytes | SHA-256 |
|---|---:|---|
| tesseract.min.js | 62,961 | `000c27d9cd0def655f77b36c72a389c0ab13793aa31cb4d7aab56d09c0afbc7e` |
| worker.min.js | 111,307 | `576b7df7e3393e137e51849357c9adb53fe7ac1bb69bfa06cf3d61520f182c6d` |
| SIMD LSTM core | 3,899,472 | `c58b46a4c796c0b8afccf77591d5b875b6896b45d402bbce8caa6f5362447b38` |
| eng traineddata.gz | 2,952,873 | `45b4cb346724ac1774f1c36f42f182b887bcdb28ebe63e6fff90ac41f3fcff91` |
| jpn traineddata.gz | 2,030,256 | `2b63ebfbf1484de4a08ce53b29ef98a1c17658a93cbd38acb665d7d316d0be88` |

Temporary vendor payload was 9,068,226 bytes including license. The JS/CSS/template harness added about 40 KB. These files are intentionally absent from the final No-Go commit.

Official sources: [Tesseract.js repository](https://github.com/naptha/tesseract.js), [Tesseract.js npm package](https://www.npmjs.com/package/tesseract.js), [tessdata repository](https://github.com/naptha/tessdata).

## Required 75-point report

1. Repo/remote: `C:\Users\YCP\OneDrive - YCP Holdings\Desktop\Oshigoto`; `https://github.com/RikuTerayama/Oshigoto.git`.
2. Phase 9.5 main: `01fc602` is contained in `origin/main` via merge `15bff84`.
3. origin/main start: `15bff84`.
4. Branch: `spike/browser-ocr`.
5. Public OCR: `/tools/ocr`, `/guide/ocr`, and `/api/ocr` remain 404 and no public catalog/nav/SEO/sitemap entry was added.
6. Internal route: a temporary `/_internal/ocr-spike` route was used only for local measurement, then removed after No-Go.
7. Default 404: confirmed with the flag unset; Render checks also treated the route as 404.
8. OCR library: Tesseract.js.
9. Version: 7.0.0, stable at audit time.
10. License: Apache-2.0 for Tesseract.js/core; language package metadata and tessdata provenance were reviewed.
11. Official source: naptha/tesseract.js and naptha/tessdata links above.
12. JS bundle: 62,961 bytes.
13. Worker: 111,307 bytes.
14. WASM/core: 3,899,472 bytes for the vendored SIMD LSTM core wrapper.
15. English model: 2,952,873 bytes gzip.
16. Japanese model: 2,030,256 bytes gzip.
17. jpn+eng model transfer: 4,983,129 bytes; minimum runtime asset set was about 9.06 MB.
18. Asset delivery: all resources were same-origin local files during the spike; no CDN was used.
19. Repository increase: temporary vendor payload 9,068,226 bytes plus about 40 KB harness; final committed increase excludes these assets.
20. Build impact: no OCR build/native dependency; retaining assets would increase checkout/deploy/static transfer, not server CPU build work.
21. Input formats: JPEG, PNG, WebP only.
22. Input limits: one file, 5 MB, 8 MP, 4,096 px longest edge; decoded dimensions were revalidated.
23. Languages: `eng`, `jpn`, `jpn+eng`; default during spike was `jpn+eng`.
24. Worker lifecycle: create per run, recognize, terminate on success/error/cancel/timeout.
25. Cancel: generation gate plus actual worker termination; stale results were not rendered.
26. Timeout: 60-second ceiling with worker termination; deterministic timeout helper passed.
27. Browser-only: confirmed; Flask served static files only and no OCR/upload endpoint existed.
28. Image upload network: zero requests; application code scan found no fetch/XHR/FormData/WebSocket/sendBeacon path and server logs showed only static resources.
29. Resource network: HTML, spike CSS/JS, image-format core, Tesseract bundle, worker, SIMD core, and selected `eng`/`jpn` model files, all same-origin.
30. Cache: normal HTTP browser cache produced 304 responses; Tesseract `cacheMethod: none` disabled language persistence.
31. Storage: no localStorage/sessionStorage/IndexedDB/cookie/service worker; input/result existed only in memory and textarea.
32. Security/CSP: strict same-origin CSP worked in Chromium with blob workers disabled; no source maps were vendored. SIMD-only core limits compatibility; vendor fallback code contains dynamic-function fallback paths that require future browser/CSP review.
33. English clean CER: 0.34% exact and normalized.
34. English difficult CER: tilted 0.71%; small 0.34%; low contrast 0.33%.
35. Japanese clean CER: 58.65% exact and normalized.
36. Japanese difficult CER: tilted 54.46%, small 57.02%, low contrast 56.45% using original images.
37. Mixed jpn+eng CER: 3.59% original; 4.10% grayscale.
38. Grayscale: no accuracy improvement on clean/low-contrast English or Japanese, slightly worsened Japanese small/tilted and mixed; it increased JS heap pressure.
39. Initial load: first observed jpn+eng worker/model load 635 ms; first total 2,538 ms on local same-origin delivery.
40. Second load: same-language Japanese load 250 ms; cached matrix loads were 184-344 ms.
41. OCR processing: 393-1,065 ms in the final matrix; 8MP was 1,049 ms.
42. Total: 627-2,161 ms in the final matrix; first observed cold-ish total was 2,538 ms.
43. Memory before: reported JS heap ranged about 4.8-16.2 MB across sequential runs.
44. Memory peak: reported JS heap reached about 16.2 MB; this does not include complete worker/WASM process memory.
45. After terminate: reported JS heap ranged 5.4-17.2 MB and did not consistently drop immediately because GC is nondeterministic.
46. 1MP: completed in 689 ms, OCR 393 ms, CER 6.12%.
47. 4MP: completed in 1,077 ms, OCR 669 ms, CER 5.56%.
48. 8MP: completed in 1,575 ms, OCR 1,049 ms, CER 5.00%; desktop Chromium only.
49. CPU throttling: not available in the controlled browser, so 4x throttling was not measured.
50. Chromium: more than 25 sequential runs completed without tab/worker crash; cancel and rerun worked.
51. Firefox: not tested; browser binary was unavailable.
52. WebKit/Safari: not tested; browser binary was unavailable.
53. iPhone: no physical-device test.
54. Android: no physical-device test.
55. Untested: low-end phones, 4x CPU throttling, slow network, Firefox, Safari/WebKit, and non-SIMD browsers.
56. Consecutive runs: 18 original/grayscale accuracy runs plus size/special runs completed without a crash.
57. Rerun after cancel: completed successfully; one observed rerun took about 7.3 seconds including teardown/new-worker transition.
58. Timeout: pure timeout/generation tests passed; a full 60-second engine timeout was not forced, so browser recovery remains partly unverified.
59. Malformed image: generated truncated PNG was rejected, result stayed empty, and the page remained usable; unsupported formats/limits passed pure validation tests.
60. Privacy: strong browser-only posture is technically possible with local assets and persistence disabled.
61. License: no blocking issue found, but notices/checksums would be required if assets were reintroduced.
62. Render/server: only static delivery would be added; no OCR CPU, temp file, upload, semaphore, or API. Final No-Go branch retains no OCR assets.
63. Preflight: passed with OCR public-route/catalog/nav/SEO/sitemap/landing prohibitions.
64. Smoke: local and deploy smoke passed; internal/public OCR routes were 404 by default.
65. Multi-user standard: timed out after 310 seconds in the known oversized-PDF branch; this predates and is unrelated to browser-only OCR.
66. Supplemental: PDF concurrency 200/200, busy 429, single-file 400, invalid 422, encrypted 400, page limit 413, and temp cleanup passed with oversize branch excluded; not reported as standard PASS.
67. Decision: **NO-GO**.
68. Reasons: Japanese CER is not practical, table-style recognition is poor, mobile/Firefox/Safari are unverified, memory figures undercount worker/WASM, and the tested core was SIMD-only.
69. Recommended limits if revisited: one file, 3 MB, 4 MP, 4,096 px edge, 45-second timeout, desktop beta, English first; do not claim Japanese support until spacing/accuracy is fixed.
70. Phase 9.6B: do not start. First run a focused Japanese segmentation/spacing experiment and physical mobile/cross-browser QA.
71. Commit hash: filled in final delivery report after commit.
72. Push: filled in final delivery report after push.
73. PR: filled in final delivery report after PR attempt.
74. Final git status: filled in final delivery report after commit/push.
75. Residual risks: generated fixtures are not representative of scans/photos, Chromium memory telemetry is incomplete, cold-network timing was local, full timeout recovery and model/core load failures were not end-to-end forced.

## Test command notes

- Standard compile/import, image compression, image format, QR, smoke, deploy smoke, AdSense preflight (tag unset/set), sitemap check, and diff checks passed during the spike.
- The real PDF page-ops test requires `PDF_LIB_PATH`; without that environment variable it exited before testing. This is unrelated to OCR.
- The standard multi-user timeout is recorded exactly and is not relabeled as a pass.
