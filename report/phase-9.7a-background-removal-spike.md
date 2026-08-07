# Phase 9.7A Background Removal Technical Spike

Date: 2026-08-07
Decision: **NO-GO for public release**

## Executive summary

The existing public checkbox was not a functioning browser integration. The page loaded a classic script that attempted `import('@imgly/background-removal')`, while the repository had no package dependency, import map, bundled module, or production `node_modules` serving. Production HTML exposed the control and script, but no model or WASM request occurred before invocation and the required module could not be resolved by the shipped page structure.

The unsupported AI control, its quality selector, its filename token, and the unused script were removed. White-background compositing, margin trimming, aspect crop/pad, borders, rounded corners, resize, and PNG/JPEG/WebP output remain. File names and processing errors in the touched UI now use DOM nodes and `textContent` instead of interpolated `innerHTML`.

No candidate clears the public gate. IMG.LY is technically the closest browser-only option, but its 1.7.0 package is AGPL-3.0, requires separate license review, and transfers roughly 44-88 MB of model data plus 12-23 MB of WASM. Server-side rembg is MIT but its official CPU container is about 1.6 GB before model files, making it inappropriate for the current Render Free architecture. BRIA RMBG weights are non-commercial without a separate agreement. Cross-browser, physical-mobile, quality, cancellation, and memory acceptance tests were not completed, so unmeasured fields are explicitly not treated as passes.

## Current public implementation audit

| Check | Finding |
|---|---|
| Public control | `id="background-removal"` was visible on `/tools/image-cleanup`. |
| Script order | `image-background-removal.js` loaded after `image-cleanup.js`; invocation happened later from the inline runner. |
| Global | The class was not intentionally exported through `globalThis`; the pipeline referenced its lexical global name. |
| Module resolution | Bare `@imgly/background-removal` import had no browser resolver. |
| Import map / bundle | Neither existed. |
| Package dependency | Neither `@imgly/background-removal` nor `onnxruntime-web` existed in `package.json`. |
| Static node_modules | Not served. |
| Production | HTML exposed the control and script. No supported package delivery path was present. |
| Public limits | The old 20-file/100-MB mode was unsafe for browser inference and has been removed. |
| Non-AI path | Existing white background and geometric cleanup remain independent and available. |

## Candidate matrix

| Candidate | Execution | Transfer/deploy impact | Privacy | Browser/mobile | Decision |
|---|---|---|---|---|---|
| A. `@imgly/background-removal` 1.7.0 | Browser ONNX Runtime, WASM or WebGPU | npm package 207,882 B compressed / 1,113,610 B unpacked; default fp16 model 88,152,708 B; quantized model 44,348,940 B; WASM 11,819,815 B CPU or 23,013,109 B JSEP | Image can remain local; model/WASM default to IMG.LY CDN, self-hosting supported | Not acceptance-tested on Firefox, Safari, iPhone, or Android | No-Go now; strongest candidate only after license and device QA |
| B. rembg 2.0.78 | Server Python/ONNX Runtime | Official CPU image about 1.6 GB before models; models download to ephemeral storage | Image must reach Oshigoto server | Browser-independent, but Render RAM/CPU/cold-start risk is high | No-Go for Render Free |
| C1. BRIA RMBG 2.0 | Browser/server model possible | Large model/runtime integration required | Browser-only is possible | Not tested | Excluded: commercial agreement required |
| C2. BiRefNet | Browser conversion or server | High model/GPU burden; official repo notes substantial inference GPU use for full model | Depends on architecture | Not tested | Research only; exact selected weights need separate provenance/license review |
| C3. U-2-Net/U2NetP | Browser conversion or server | Lighter variants exist; model distribution/version pinning still needs validation | Depends on architecture | Not tested | Research only |
| D. remove.bg / PhotoRoom API | External API | Low Render compute; paid per call/credit | User image leaves the browser and site | Broad client compatibility | Not implemented; requires contract, DPA/privacy and cost decision |

Official sources: [IMG.LY repository](https://github.com/imgly/background-removal-js), [IMG.LY npm package](https://www.npmjs.com/package/%40imgly/background-removal), [IMG.LY AGPL license](https://raw.githubusercontent.com/imgly/background-removal-js/main/LICENSE.md), [rembg repository](https://github.com/danielgatis/rembg), [rembg PyPI](https://pypi.org/project/rembg/), [BRIA RMBG-2.0 model card](https://huggingface.co/briaai/RMBG-2.0), [BiRefNet repository](https://github.com/ZhengPeng7/BiRefNet), [U-2-Net license](https://raw.githubusercontent.com/xuebinqin/U-2-Net/master/LICENSE), [remove.bg API](https://www.remove.bg/api), and [PhotoRoom API pricing](https://docs.photoroom.com/image-editing-api-plus-plan/whats-the-pricing).

## Candidate A package and asset metadata

- npm version: `1.7.0`.
- npm tarball: 207,882 bytes; unpacked 1,113,610 bytes; ESM bundle 171,349 bytes.
- npm shasum: `de210d26a545a09406b866f4f24c0479b154bb5c`.
- npm integrity: `sha512-/1ZryrMYg2ckIvJKoTu5Np50JfYMVffDMlVmppw/BdbN3pBTN7e6stI5/7E/LVh9DDzz6J588s7sWqul3fy5wA==`.
- peer runtime: `onnxruntime-web` 1.21.0; README install example uses a dated 1.21 development build, which needs reconciliation before adoption.
- default public path: `https://staticimgly.com/@imgly/background-removal-data/1.7.0/dist/`.
- models: `isnet_quint8` 44,348,940 bytes, `isnet_fp16` 88,152,708 bytes, `isnet` 176,149,806 bytes.
- runtime: CPU WASM 11,819,815 bytes; WebGPU/JSEP WASM 23,013,109 bytes plus small MJS loaders.
- model aliases: small -> `isnet_quint8`, medium/default -> `isnet_fp16`, large -> `isnet`.
- browser caching: normal HTTP cache plus an additional model cache is documented; exact persistence behavior must be verified before privacy copy is approved.
- capabilities: CPU/WASM fallback, optional WebGPU, progress callback, custom `publicPath`, and fetch options. No public acceptance claim is made for abort/session disposal because it was not verified end to end.
- cross-origin isolation: the package reports degraded multithreaded performance without it. Phase 9.7A intentionally does not add COOP/COEP because of possible effects on AdSense, A8, Amazon, external assets, forms, popups, and `window.opener`.

## License matrix

| Component | Observed license/terms | Gate |
|---|---|---|
| IMG.LY library | AGPL-3.0; vendor offers other licensing by contact | Formal legal/license review required; no legal conclusion made here |
| IMG.LY model assets | Distributed by IMG.LY data package; exact model-weight license and redistribution terms must be confirmed separately | Not cleared |
| ONNX Runtime Web | Runtime license must be retained and notices reviewed with the exact pinned package | Not cleared as a complete bundle |
| rembg | MIT | Library license is permissive; bundled model licenses remain model-specific |
| U-2-Net source | Apache-2.0 | Model file provenance, redistribution, checksum, and browser conversion still need review |
| BiRefNet source | MIT | Exact chosen model weights need separate review |
| BRIA RMBG-2.0 weights | CC BY-NC 4.0 / commercial agreement required | Excluded from monetized public use without agreement |
| External APIs | Commercial service terms | Contract, cost, retention, training-use, region, and DPA review required |

## Quality and performance matrix

No model passed the license/runtime gate far enough to justify committing a 40-176 MB asset or submitting user images to an external API. Therefore the following values are deliberately recorded as **not measured**, not zero and not pass.

| Area | IMG.LY | rembg | Browser model alternatives | External API |
|---|---|---|---|---|
| Person/product/hair/fur/thin/transparent/low contrast | Not measured | Not measured | Not measured | Not measured; no API key/contract |
| IoU / boundary score / visual rating | Not measured | Not measured | Not measured | Not measured |
| 0.5/1/2/4 MP inference | Not measured | Not measured | Not measured | Not measured |
| First/second run | Not measured | Not measured | Not measured | Not measured |
| Peak/after memory | Not measured | Not measured | Not measured | Not measured |
| Chromium/Firefox/Safari | Production integration broken / other browsers untested | Client-independent | Untested | Client-independent |
| iPhone/Android | Untested | Client-independent | Untested | Client-independent |

Pure metric tests cover IoU, Dice, pixel accuracy, mean alpha error, and exact-boundary F-score behavior so a future licensed candidate can be measured consistently. No copyrighted or confidential fixture images were committed.

## Recommended architecture if revisited

Use a browser-only, same-origin, version-pinned bundle only after license clearance. Start as a desktop beta with one JPEG/PNG/WebP image, 5 MB, 4 MP, 2,048 px longest edge, 30-second timeout, generation-ID stale-result suppression, worker termination, Blob URL revocation, bitmap/canvas cleanup, explicit model download progress, and a clear distinction between local image processing and model-asset download. Prefer the 44,348,940-byte quantized model for the first measurement, but do not infer acceptable quality from size alone.

Do not add site-wide COOP/COEP without a dedicated compatibility test of AdSense, A8, Amazon, external images, forms, fonts, popups, and third-party scripts. Do not use a Render-side inference API on the free plan. Do not enable BRIA weights on the monetized site without a commercial agreement.

## Required 89-point report

1. Repo/remote: `C:\Users\YCP\OneDrive - YCP Holdings\Desktop\Oshigoto`; `https://github.com/RikuTerayama/Oshigoto.git`.
2. Phase 9.6A main: `c5763eb` is contained in `origin/main` via merge `1124443`.
3. origin/main start: `1124443`.
4. Branch: `spike/background-removal`.
5. Existing audit: public control existed but had no resolvable package delivery path.
6. Public checkbox: removed.
7. Bare import: removed with the unused script.
8. Image-cleanup hotfix: AI path removed; white background and geometric cleanup retained; touched unsafe DOM replaced.
9. Public background route: tool, guide, and API remain 404.
10. Internal spike route: no retained route after No-Go; default and flag-on behavior are both 404.
11. Candidate A: `@imgly/background-removal`.
12. Candidate A version: 1.7.0.
13. Candidate A license: AGPL-3.0; formal review required.
14. Candidate A model size: 44,348,940 B quantized; 88,152,708 B default fp16; 176,149,806 B full.
15. Candidate A WASM/runtime: ONNX Runtime Web 1.21.0; 11,819,815 B CPU WASM or 23,013,109 B JSEP WASM.
16. Candidate A first run: not measured; requires model and WASM cold transfer.
17. Candidate A second run: not measured; browser/model cache is documented but not accepted here.
18. Candidate A memory: not measured.
19. Candidate A browser result: shipped Oshigoto integration failed structurally; candidate package itself was not accepted cross-browser.
20. Candidate A mobile result: not tested.
21. Candidate B rembg version: 2.0.78 at audit time.
22. Candidate B license: MIT; model licenses remain separate.
23. Candidate B model size: silueta is documented at 43 MB; other models vary and download separately.
24. Candidate B RSS: not measured because the official ~1.6 GB CPU image already fails the Render Free suitability gate.
25. Candidate B Render suitability: No-Go for the current free service.
26. Candidate C models: BRIA RMBG, BiRefNet, and U-2-Net/U2NetP reviewed.
27. Candidate C licenses: BRIA non-commercial without agreement; BiRefNet source MIT; U-2-Net source Apache-2.0; exact weights require review.
28. Commercial-use exclusions: BRIA RMBG-2.0 self-hosted weights excluded without agreement.
29. External API comparison: remove.bg and PhotoRoom require external upload, credentials, commercial terms, privacy review, and per-call cost/credits.
30. Fixture set: no image fixtures committed; future set must cover the 12 specified categories with clear reuse rights and masks.
31. Person quality: not measured.
32. Product quality: not measured.
33. Hair quality: not measured.
34. Fur quality: not measured.
35. Thin object quality: not measured.
36. Transparent object quality: not measured.
37. Low contrast: not measured.
38. IoU: helper tested; candidate score not measured.
39. Boundary score: exact-boundary helper tested; candidate score not measured.
40. Visual rating: not measured.
41. 0.5 MP performance: not measured.
42. 1 MP performance: not measured.
43. 2 MP performance: not measured.
44. 4 MP performance: not measured.
45. Cold asset bytes: minimum IMG.LY quantized CPU path is roughly 56 MB before package overhead; default CPU path roughly 100 MB.
46. Cached bytes: not measured; expected network reduction is not claimed.
47. WebGPU result: supported by IMG.LY configuration but not measured.
48. WASM result: supported by IMG.LY as fallback but not measured.
49. Memory before: not measured.
50. Memory peak: not measured.
51. Memory after: not measured.
52. Cancel: existing script only checked a local signal around opaque inference; actual inference termination was not guaranteed.
53. Rerun: not measured.
54. Timeout: no reliable public inference timeout existed; future ceiling recommendation is 30 seconds.
55. Chromium: production HTML audited; candidate inference not acceptance-tested.
56. Firefox: not tested.
57. Safari/WebKit: not tested.
58. iPhone: not tested.
59. Android: not tested.
60. Untested environments: physical mobile, low memory, throttled CPU/network, Firefox, and Safari/WebKit.
61. Network requests: current broken public integration had no valid package/model route; candidate defaults would fetch model/WASM from IMG.LY.
62. Image upload requests: none in current image-cleanup code; external APIs would require uploads.
63. Cache/storage: browser HTTP and model cache are documented; exact persistence/clear behavior remains unverified.
64. Privacy: browser-only can keep images local, but third-party model download must be described separately from image upload.
65. CSP: no production CSP change; candidate dynamic modules/workers/WASM require a dedicated review.
66. COOP/COEP impact: not enabled; may affect ads, affiliate assets, forms, popups, and cross-origin integrations.
67. AdSense impact: no loader or header change.
68. A8 impact: no integration or header change.
69. Amazon impact: no integration or header change.
70. Library license: IMG.LY AGPL-3.0; rembg MIT.
71. Model license: not uniformly cleared; BRIA is explicitly restricted for commercial self-hosting.
72. Commercial-use assessment: no candidate approved; legal/license owner review remains mandatory.
73. Repo size impact: final branch adds no model, WASM, ONNX, or experimental bundle and deletes 136 lines of dead script.
74. Render impact: hotfix reduces one static request; no inference API/semaphore/dependency added.
75. Preflight: background-removal routes, catalog/nav/sitemap absence, and public control absence are enforced.
76. Smoke: local/deploy smoke enforce 404s and absence of the public control/script.
77. Multi-user standard: `python scripts/test_multi_user_safety.py` was run unchanged. It confirmed parallel PDF lock `200/200`, busy rejection `429`, and single-file rejection `400`, then exceeded the 360-second command limit while constructing/posting the oversized-PDF case. This is recorded as a test-harness timeout, not a pass.
78. Supplemental test: the same module was rerun without the oversized payload branch. Parallel isolation, busy rejection, single-file rejection, corrupt PDF `422`, already-encrypted PDF `400`, page-limit `413`, and temporary-file cleanup passed. The background-removal spike test separately covers input limits, mask metrics, safe filenames, timeout handling, generation-ID stale-result suppression, and public non-exposure.
79. Decision: **NO-GO**.
80. Reason: broken current integration, uncleared license/model terms, large assets, missing quality/device/browser/memory/cancel evidence.
81. Recommended architecture: browser-only, same-origin pinned assets, worker isolation, no image upload, no site-wide headers until compatibility QA.
82. Recommended limits: one JPEG/PNG/WebP, 5 MB, 4 MP, 2,048 px edge, 30-second timeout; tighten to 3 MB/2 MP/1,536 px if mobile evidence requires it.
83. Phase 9.7B recommendation: do not start until license approval and representative desktop/mobile/cross-browser benchmark are available.
84. Commit hash: the commit containing this report is identified in the final delivery response and Git history; a commit cannot contain its own final hash.
85. Push: recorded in the final delivery response after the remote operation.
86. PR URL: recorded in the final delivery response after the PR creation attempt.
87. Final git status: recorded in the final delivery response after commit and push.
88. `.claude` status: remains untracked and excluded.
89. Residual risks: no real-model quality/performance evidence, no physical devices, incomplete model-weight license provenance, external API contracts unreviewed, and existing non-AI image cleanup still permits large batches by design.
