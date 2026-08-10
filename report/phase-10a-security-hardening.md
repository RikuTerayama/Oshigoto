# Phase 10A Security Hardening Report

Date: 2026-08-10

Repository: `RikuTerayama/Oshigoto`

Branch: `security/phase-10-hardening`
Baseline: `origin/main` at `48a5ca8496f66d74f180a8fd9fa48c64cd66f853`

## Release decision

Phase 10A adds defense in depth without changing the product feature set or affiliate creatives. The release gate is satisfied: no BLOCKER or HIGH residual security issue was identified, the final production dependency audit reports no known vulnerability, and the deterministic predeploy suite passes.

The local workstation does not have Docker available. Docker runtime identity and build success therefore remain CI/deployment validation items; static checks verify the pinned digest, non-root user, hashed install, and Gunicorn limits.

## Threat model

| Surface | Principal threats | Implemented controls |
| --- | --- | --- |
| A. Public HTML | XSS, clickjacking, Host poisoning, information leakage | exact Host allowlist, output escaping/DOM `textContent`, security headers, staged CSP |
| B. `/api/pdf/*` | malicious PDF, upload DoS, oversized multipart, data caching | signature/type/size checks, parser caps, rate/concurrency caps, `no-store`, closed uploads |
| C. `/api/seo/crawl-urls` | SSRF, DNS rebinding, metadata access, response exhaustion | pinned-IP safe HTTP client, per-hop validation, redirect/size/time/depth caps |
| D. CSV conversion | spreadsheet formula injection | export-time neutralization of formula-leading cells |
| E. File uploads | path traversal, CRLF filenames, excessive files/bytes | filename/path validation, extension/MIME/magic checks, hard request ceilings |
| F. Browser PDF/image tools | CDN compromise, DOM XSS, worker substitution | same-origin vendoring, checksums, licenses, worker URL from trusted meta |
| G. Amazon/A8/AdSense | regression, disclosure breakage, CSP incompatibility | unchanged creatives/settings, regression tests, CSP Report-Only rollout |
| H. External CDN | third-party script replacement | critical processing libraries vendored and integrity-checked |
| I. Render reverse proxy | spoofed forwarded Host/scheme, unsafe runtime config | `ProxyFix(x_host=0)`, exact Host validation, capped environment values |
| J. GitHub Actions | action tag takeover, excessive token permissions | full commit SHA pins, read-only defaults, no persisted checkout credentials |
| K. Python supply chain | vulnerable/transitive dependency or mutable install | exact input pins, full hashed lock, pip-audit gate, Dependabot |

Explicit attack cases cover SSRF, DNS rebinding, localhost/cloud metadata access, XSS, Host poisoning, clickjacking, cross-site resource abuse, file and multipart exhaustion, malicious PDF input, CSV formula injection, path traversal, CRLF filenames, dependency and Action compromise, leaked credentials, and critical CDN substitution.

## Dependency audit

The audit sequence found six known issues across four packages before final pinning:

| Package | Affected | Advisory identifiers | Fixed |
| --- | --- | --- | --- |
| Flask | 2.3.3 | `PYSEC-2026-2151`, `GHSA-68rp-wp8r-4726`, `CVE-2026-27205` | 3.1.3 |
| Gunicorn | 21.2.0 | `PYSEC-2026-1434`, `GHSA-w3h3-4rj7-4ph4`, `CVE-2024-1135` | 22.0.0 |
| Gunicorn | 21.2.0 | `PYSEC-2026-1433`, `GHSA-hc5x-x2vx-497g`, `CVE-2024-6827` | 22.0.0 |
| Requests | 2.32.5 | `PYSEC-2026-2275`, `GHSA-gc5v-m9x4-r6x2`, `CVE-2026-25645` | 2.33.0 |
| pypdf | 6.14.2 | `CVE-2026-71852`, `GHSA-fwg2-594c-jp42` | 6.15.0 |
| pypdf | 6.14.2 | `CVE-2026-71870`, `GHSA-fp3f-mc75-235c` | 6.15.0 |

No vulnerability is ignored. `requirements.in` contains exact direct dependencies. `requirements.lock.txt` contains the full transitive graph with SHA-256 hashes. Production installation uses `--require-hashes` and binary wheels only. The final command, `python -m pip_audit --no-deps --disable-pip -r requirements.lock.txt`, reports `No known vulnerabilities found`.

## Application controls

- Production accepts only `oshigoto.onrender.com`; localhost hosts are enabled only outside production. Wildcard Render hosts are rejected.
- `ProxyFix` trusts one forwarding hop for client/protocol and does not trust forwarded Host.
- HTTPS responses include HSTS for one year without premature preload/subdomain scope, `nosniff`, frame protection, restrictive referrer/permissions policies, and cross-domain policy denial.
- `object-src 'none'`, `base-uri 'self'`, and `frame-ancestors 'self'` are enforced. Broader script/image/connect/frame directives are Report-Only pending production validation with Google and A8.
- Session cookies are Secure, HttpOnly, and SameSite=Lax. No application secret is hardcoded.
- TRACE, TRACK, and CONNECT return 405.
- Unsafe API requests with a cross-site fetch context or foreign Origin return 403. Missing Origin remains compatible with server clients.
- SEO JSON and PDF multipart media types are explicitly required. API responses, including errors and generated metadata, are non-cacheable.
- Environment-controlled resource and rate values have non-bypassable hard ceilings.
- PDF inputs are checked before processing and closed in `finally`; request parser limits reject excessive multipart bodies.
- Logs retain operational type/status information without intentionally recording passwords, file content, form values, or sensitive URL credentials.

## SSRF design

`lib/safe_http.py` centralizes outbound crawling. It accepts only HTTP(S) with default ports, rejects userinfo and local/reserved/non-global addresses including IPv4-mapped IPv6, resolves every A/AAAA answer, and connects directly to a validated public IP while preserving the original Host header and TLS SNI/certificate verification. This closes the validation-then-resolution DNS rebinding gap.

Redirects are manually followed and revalidated for at most three hops. Environment proxies, cookies, and authorization are not used. Connect/read timeouts, Content-Length checks, streamed decoded-byte caps, a 5 MB hard ceiling, content-type allowlisting, and same-origin crawl mode constrain resource use. Deterministic tests cover private targets, metadata, redirects to private addresses, rebinding, oversized responses, and a valid public HTTPS connection.

## Browser supply chain and XSS

Critical processing libraries are served from versioned same-origin paths: pdf-lib 1.17.1, pdf.js 3.11.174, JSZip 3.10.1, Papa Parse 5.4.1, Encoding Japanese 2.0.0, and SheetJS 0.20.3. `data/vendor_integrity.json` records version, path, source, SHA-256, and license; `THIRD_PARTY_NOTICES.md` contains notices. Predeploy fails on checksum drift or restoration of critical CDN URLs. Google/AdSense/A8 network scripts remain external by design.

The SEO tool's user-derived meta and warning rendering now uses node creation and `textContent` rather than `innerHTML`. CSV and XLSX exports neutralize cells beginning with formula control characters (`=`, `+`, `-`, `@`, tab, or carriage return).

## Runtime and CI hardening

- Docker uses the supported Python 3.11.15 slim Bookworm image pinned by digest.
- The container runs as fixed UID/GID 10001 with root-owned application source. Runtime writes are confined to temporary paths.
- Unused font packages and build tooling were removed; only CA certificates are installed with `--no-install-recommends`.
- Gunicorn has explicit request-line/header count/header size, worker/thread, timeout, keep-alive, and request recycling limits.
- GitHub workflows default to `contents: read`; checkout credentials are not persisted; all Actions are pinned to full verified SHAs.
- Dependabot covers pip, GitHub Actions, and Docker weekly with a five-PR limit.
- CodeQL scans Python and JavaScript on main pushes, pull requests, and schedule.
- The security workflow gates pip-audit and Bandit HIGH findings. Local predeploy runs deterministic security tests without depending on the network.
- `.dockerignore` excludes repository metadata, local environment/secrets, reports, tests, caches, and artifacts while retaining runtime application assets.
- `SECURITY.md` documents responsible reporting through the public contact page.

Bandit's full informational scan contains 5 MEDIUM and 97 LOW raw findings. The five MEDIUM findings were reviewed: two Amazon calls already pass explicit timeouts; the other three are deployment/test utilities operating on controlled inputs. The release gate fails on HIGH findings. After contextual review, none of these scanner findings is classified as a residual BLOCKER/HIGH/MEDIUM production vulnerability.

## Production configuration

Expected safe values are documented and capped in code:

| Setting | Expected production value/range |
| --- | --- |
| `WEB_CONCURRENCY` | 1 |
| `WEB_THREADS` | 1 |
| `RATE_LIMIT_LIGHT_PER_MIN` | 1-120 |
| `RATE_LIMIT_PDF_PER_MIN` | 1-30 |
| `RATE_LIMIT_SEO_PER_MIN` | 1-8 |
| `MAX_ACTIVE_PDF_JOBS` | 1-2 |
| `MAX_FILES_PER_REQUEST` | 1-25 |
| `MAX_TOTAL_UPLOAD_MB` | 1-100 |
| `MAX_OUTPUT_SIZE_MB` | 1-150 |
| `MAX_SEO_CRAWL_URLS` | 1-300 |
| `MAX_SEO_CRAWL_DEPTH` | 0-5 |

Rate and concurrency stores remain process-local. Production therefore intentionally stays at one Gunicorn worker. Scaling beyond one worker requires a shared atomic backend such as Redis; increasing workers without it would multiply the effective limits.

## GitHub repository settings requiring human verification

The following settings cannot be proven from repository code and must not be treated as PASS until verified in GitHub:

- account/organization 2FA or passkey enforcement
- main branch protection and required pull requests
- required predeploy/security status checks
- CodeQL enablement and alert handling
- Dependabot alerts and security updates
- secret scanning and push protection where available
- force-push and branch-deletion protection
- default Actions token set to read-only
- policy restricting Actions to approved/full-SHA references where available

## Validation

Passed locally:

- Python compile/import checks
- sitemap manifest check
- public and deploy smoke suites
- release-candidate route, SEO, schema, AdSense, Amazon, A8, 404, JSON-LD, and NO-GO checks
- multi-user and download-header safety tests
- dedicated security preflight and attack cases
- image compression/format, QR, OCR/background NO-GO, PDF scope, A8 catalog, and Amazon single-recommendation tests
- CSV formula injection test
- Bandit HIGH gate
- final online pip-audit with zero known vulnerabilities
- full `scripts/predeploy.py`
- `git diff --check`

Not locally executable: Docker build/container `id` because Docker is unavailable on this workstation. CI/deployment must confirm the image builds and reports UID 10001.

## Final 78-item closeout

1. **origin/main start:** `48a5ca8496f66d74f180a8fd9fa48c64cd66f853`; required hotfix is included.
2. **branch:** `security/phase-10-hardening`.
3. **threat model summary:** A-K surfaces and listed network, browser, upload, runtime, CI, secret, and supply-chain attacks assessed.
4. **pip-audit before:** vulnerable direct/resolved versions were audited before final lock.
5. **vulnerabilities found:** 6 known advisories across Flask, Gunicorn, Requests, and pypdf.
6. **vulnerabilities fixed:** all 6 upgraded to fixed versions; no ignore rules.
7. **dependency versions changed:** Flask 3.1.3, Gunicorn 22.0.0, Requests 2.33.0, pypdf 6.15.0; other direct pins reviewed.
8. **lock file:** `requirements.lock.txt` includes the transitive graph.
9. **hash mode:** SHA-256 hashes plus `pip --require-hashes --only-binary=:all:`.
10. **trusted hosts:** exact production host; local hosts only outside production; wildcards rejected.
11. **invalid Host result:** 400; canonical URLs cannot inherit attacker Host.
12. **ProxyFix result:** one forwarded client/protocol hop; forwarded Host not trusted.
13. **HSTS:** HTTPS only, `max-age=31536000`, no preload/subdomain expansion yet.
14. **CSP enforce directives:** `object-src 'none'; base-uri 'self'; frame-ancestors 'self'`.
15. **CSP Report-Only:** broader script/style/image/connect/frame allowlist staged for production compatibility review.
16. **cookie settings:** Secure, HttpOnly, SameSite=Lax.
17. **forbidden methods:** TRACE/TRACK/CONNECT return 405.
18. **cross-site POST result:** unsafe cross-site API requests return 403.
19. **Content-Type result:** wrong SEO/PDF request media types return 415.
20. **SSRF localhost:** rejected.
21. **SSRF IPv6:** loopback/private/mapped forms rejected.
22. **SSRF metadata:** link-local cloud metadata address rejected.
23. **SSRF redirect:** each target revalidated; public-to-private redirect rejected.
24. **DNS rebinding:** validated IP is pinned for the connection while Host/SNI remain the hostname.
25. **outbound proxy disabled:** environment proxies, cookies, and authorization are not used.
26. **response size cap:** streamed decoded bytes capped with preflight Content-Length check; hard maximum 5 MB.
27. **redirect limit:** 3.
28. **resource hard ceilings:** upload/file/output/PDF jobs/SEO depth and URL counts cannot be raised past safe caps by environment typo.
29. **multipart caps:** 512 KiB in-memory form data and 25 parts.
30. **SEO rate limit:** configurable but capped at 8 requests/minute; 429 and Retry-After tested.
31. **PDF rate limit:** configurable but capped at 30 requests/minute plus concurrent-job cap.
32. **worker limitation:** process-local controls require one production worker; shared storage is required before scale-out.
33. **file validation:** extension, filename, MIME, PDF signature, size, file count, and password checks.
34. **download headers:** attachment, no-store, and nosniff verified.
35. **CSV formula injection:** CSV and XLSX formula-leading cells are neutralized and tested.
36. **XSS sink audit:** user-derived SEO results moved from `innerHTML` to DOM/text rendering.
37. **external critical CDN before:** six browser processing libraries were externally loaded.
38. **local vendor after:** critical processing libraries are same-origin and versioned.
39. **vendor checksums:** SHA-256 manifest verified by predeploy.
40. **vendor licenses:** local license files and third-party notices included.
41. **Docker base:** official Python 3.11.15 slim Bookworm.
42. **Docker digest:** `sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3`.
43. **Docker user:** fixed non-root UID/GID 10001.
44. **container UID:** statically configured as 10001; runtime confirmation pending CI because local Docker is unavailable.
45. **Gunicorn limits:** explicit request line/header/count, worker/thread, timeout, keep-alive, and max-request settings.
46. **workflow permissions:** read-only contents by default; CodeQL alone receives security-events write.
47. **action SHA pins:** checkout, setup-python, setup-node, and CodeQL use full verified commit SHAs.
48. **Dependabot:** weekly pip, Actions, and Docker updates; maximum 5 open PRs each.
49. **CodeQL:** Python and JavaScript workflow added.
50. **Bandit:** HIGH gate passes; 5 MEDIUM/97 LOW raw findings reviewed contextually.
51. **secrets scan:** current tracked files scanned for common key/token/private-key patterns without printing secret material.
52. **secret history result:** GitHub token 0, AWS key 0, private-key marker 0; no credential rotation trigger found.
53. **SECURITY.md:** supported branch and responsible disclosure instructions added.
54. **dockerignore:** secrets, VCS, CI/local metadata, reports, tests, caches, and artifacts excluded from build context.
55. **security_preflight:** deterministic Host/header/method/cross-site/content-type/SSRF/upload/rate/vendor/Docker/CI/secret/NO-GO tests added.
56. **existing feature regression:** public pages and all browser tools pass release/predeploy checks.
57. **A8 checksum:** exact five approved snippets unchanged and test passes.
58. **Amazon regression:** single recommendation and tag behavior pass; no tag is hardcoded.
59. **AdSense regression:** publisher/configuration checks pass; no AdSense code changed.
60. **OCR/background guards:** hidden routes remain 404.
61. **PDF unlock guard:** `/api/pdf/unlock` remains 404 and no public unlock UI is present.
62. **smoke:** public and deploy smoke suites pass.
63. **release audit:** 28 public pages, 24 indexable/sitemap pages, and internal-link/schema/404 checks pass.
64. **multi-user:** rate, concurrency, limits, cleanup, and download-header safety suite passes.
65. **predeploy:** full `python scripts/predeploy.py` passes.
66. **dependency audit after:** no known vulnerabilities in the final hashed production lock.
67. **BLOCKER count:** 0.
68. **HIGH count:** 0.
69. **MEDIUM count:** 0 residual production vulnerabilities after contextual review; 5 raw Bandit findings are documented above.
70. **LOW count:** 0 accepted residual vulnerabilities; Docker runtime execution is tracked as a validation gap, not a code vulnerability.
71. **changed files:** application/runtime controls, safe HTTP crawler, dependency inputs/lock, Docker/Render configuration, CI/security automation, vendor assets/notices, templates/scripts/tests, and this report.
72. **commit hash:** populated after commit in the PR/final task report.
73. **push:** populated after branch push.
74. **PR URL:** populated after PR creation.
75. **final git status:** to be recorded after commit/push; only pre-existing `.claude/` should remain untracked.
76. **.claude status:** pre-existing, untouched, and explicitly excluded from staging.
77. **manual GitHub security settings remaining:** all items in the repository-settings checklist require human verification.
78. **Phase 10B CSP enforcement recommendation:** inspect production browser console/report-only violations across tools, AdSense, Amazon, and the exact A8 creatives; then migrate only observed necessary origins to an enforced CSP without adding broad wildcards.
