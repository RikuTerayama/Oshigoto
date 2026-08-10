# Third-Party Notices

## qrcode 1.5.4

- Project: soldair/node-qrcode
- License: MIT
- Official repository: https://github.com/soldair/node-qrcode
- Source tag: `v1.5.4`
- Source commit: `3848ed2c17de5bcdead487417dbf14c5dd017f8d`
- npm package: https://registry.npmjs.org/qrcode/-/qrcode-1.5.4.tgz
- npm integrity: `sha512-1ca71Zgiu6ORjHqFBDpnSMTR2ReToX4l1Au1VFLyVeBTFavzQnv5JxMFr3ukHVKpSrSA2MCk0lNJSykjUfz7Zg==`
- npm tarball SHA-256: `0c7274f0c299f39c2fddf54a2e0039b785977b0173c02d0b3f65fad68923e2b0`
- Vendored bundle: `static/vendor/qrcode/1.5.4/qrcode.min.js`
- Vendored bundle SHA-256: `7706f84597d8466955504c52eab2e9dd9c345626509ea13476863649d01f81dd`
- License copy: `static/vendor/qrcode/1.5.4/LICENSE`

The npm tarball for 1.5.4 declares `build/` but does not contain the browser bundle. The vendored file was therefore generated from the official `v1.5.4` tag without source edits by running `npm ci --ignore-scripts --no-audit --no-fund` followed by the project's own `npm run build` Rollup task. The generated `build/qrcode.js` file is already minified by the official configuration and was copied without content changes to `qrcode.min.js`.

## Browser tool dependencies

The following exact-version browser bundles are served locally. Their SHA-256 digests and source URLs are recorded in `data/vendor_integrity.json`; their license texts are stored beside each bundle.

- encoding-japanese 2.0.0 (MIT)
- JSZip 3.10.1 (MIT or GPL-3.0-or-later)
- Papa Parse 5.4.1 (MIT)
- pdf-lib 1.17.1 (MIT)
- pdfjs-dist 3.11.174 (Apache-2.0)
- SheetJS Community Edition 0.20.3 (Apache-2.0)
