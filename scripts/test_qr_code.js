'use strict';

const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const core = require('../static/js/qr-code-core.js');

function expectError(code, callback) {
    assert.throws(callback, error => error && error.name === 'QrInputError' && error.code === code);
}

assert.strictEqual(core.byteLength('abc'), 3);
assert.strictEqual(core.byteLength('日本語'), 9);
assert.strictEqual(core.byteLength('😀'), 4);
assert.strictEqual(core.buildTextPayload({ text: 'a'.repeat(1000) }).length, 1000);
expectError('PAYLOAD_TOO_LARGE', () => core.buildTextPayload({ text: 'a'.repeat(1001) }));
assert.strictEqual(core.buildTextPayload({ text: '日本語\n😀' }), '日本語\n😀');
assert.strictEqual(core.buildTextPayload({ text: '<img src=x onerror=alert(1)>' }), '<img src=x onerror=alert(1)>');
expectError('TEXT_REQUIRED', () => core.buildTextPayload({ text: '  \n ' }));
expectError('TEXT_CONTROL_CHARACTER', () => core.buildTextPayload({ text: 'ok\u0000bad' }));

const url = 'https://example.com/path?q=日本語&x=1#section';
assert.strictEqual(core.buildUrlPayload({ url: '  ' + url + '  ' }), url);
expectError('URL_SCHEME_NOT_ALLOWED', () => core.buildUrlPayload({ url: 'javascript:alert(1)' }));
expectError('URL_SCHEME_NOT_ALLOWED', () => core.buildUrlPayload({ url: 'data:text/plain,test' }));
expectError('URL_SCHEME_NOT_ALLOWED', () => core.buildUrlPayload({ url: 'file:///tmp/test' }));
expectError('URL_INVALID', () => core.buildUrlPayload({ url: 'example.com' }));
expectError('URL_CONTROL_CHARACTER', () => core.buildUrlPayload({ url: 'https://example.com/\npath' }));

assert.strictEqual(
    core.buildEmailPayload({ address: 'name+qr@example.com', subject: '資料 確認', body: '本文\n2行目' }),
    'mailto:name+qr@example.com?subject=%E8%B3%87%E6%96%99%20%E7%A2%BA%E8%AA%8D&body=%E6%9C%AC%E6%96%87%0A2%E8%A1%8C%E7%9B%AE'
);
assert.strictEqual(core.buildEmailPayload({ address: 'name@example.com' }), 'mailto:name@example.com');
expectError('EMAIL_INVALID', () => core.buildEmailPayload({ address: 'not-an-email' }));
expectError('EMAIL_INVALID', () => core.buildEmailPayload({ address: 'name@example.com\r\nBcc:test@example.com' }));
expectError('EMAIL_SUBJECT_CONTROL_CHARACTER', () => core.buildEmailPayload({ address: 'name@example.com', subject: 'a\r\nBcc:test@example.com' }));

assert.strictEqual(core.buildPhonePayload({ phone: '+81 (90) 1234-5678' }), 'tel:+819012345678');
assert.strictEqual(core.buildPhonePayload({ phone: '03-1234-5678' }), 'tel:0312345678');
expectError('PHONE_INVALID_CHARACTER', () => core.buildPhonePayload({ phone: '03/1234/5678' }));
expectError('PHONE_INVALID_CHARACTER', () => core.buildPhonePayload({ phone: '81+9012345678' }));
expectError('PHONE_LENGTH', () => core.buildPhonePayload({ phone: '12' }));

assert.strictEqual(core.escapeWifiValue('A\\B;C,D:E'), 'A\\\\B\\;C\\,D\\:E');
assert.strictEqual(
    core.buildWifiPayload({ ssid: 'Office;2,4:GHz\\East', security: 'WPA', password: 'p;a,s:s\\word', hidden: true }),
    'WIFI:T:WPA;S:Office\\;2\\,4\\:GHz\\\\East;P:p\\;a\\,s\\:s\\\\word;H:true;;'
);
assert.strictEqual(
    core.buildWifiPayload({ ssid: 'Guest', security: 'nopass', password: 'must-not-appear', hidden: false }),
    'WIFI:T:nopass;S:Guest;H:false;;'
);
expectError('WIFI_SSID_REQUIRED', () => core.buildWifiPayload({ ssid: '', security: 'WPA', password: 'test' }));
expectError('WIFI_SSID_TOO_LARGE', () => core.buildWifiPayload({ ssid: 'あ'.repeat(43), security: 'WPA', password: 'test' }));
expectError('WIFI_PASSWORD_REQUIRED', () => core.buildWifiPayload({ ssid: 'Office', security: 'WPA', password: '' }));
expectError('WIFI_PASSWORD_TOO_LARGE', () => core.buildWifiPayload({ ssid: 'Office', security: 'WPA', password: 'a'.repeat(257) }));

assert.deepStrictEqual(core.validateSettings({}), {
    errorCorrectionLevel: 'M', width: 512, margin: 4, color: { dark: '#000000', light: '#FFFFFF' }
});
assert.deepStrictEqual(core.validateSettings({ errorCorrectionLevel: 'h', width: 1024, margin: 8, dark: '#123456', light: '#abcdef' }), {
    errorCorrectionLevel: 'H', width: 1024, margin: 8, color: { dark: '#123456', light: '#ABCDEF' }
});
expectError('ERROR_LEVEL_INVALID', () => core.validateSettings({ errorCorrectionLevel: 'X' }));
expectError('OUTPUT_SIZE_INVALID', () => core.validateSettings({ width: 300 }));
expectError('MARGIN_INVALID', () => core.validateSettings({ margin: 0 }));
expectError('COLOR_CONTRAST_INVALID', () => core.validateSettings({ dark: '#ffffff', light: '#ffffff' }));
assert.strictEqual(core.getFilename('wifi', 'png'), 'qr-wifi.png');
assert.strictEqual(core.getFilename('email', 'svg'), 'qr-email.svg');
assert.strictEqual(core.summarizePayload('url', { url: 'https://example.com/path?q=1' }), 'example.com');
assert.strictEqual(core.summarizePayload('text', { text: 'a'.repeat(45) }), 'a'.repeat(40) + '…');
assert.strictEqual(core.summarizePayload('email', { address: 'name@example.com', body: 'secret body' }), 'name@example.com');
assert.strictEqual(core.summarizePayload('phone', { phone: '+81 (90) 1234-5678' }), '+819012345678');
assert.strictEqual(core.summarizePayload('wifi', { ssid: 'Office', security: 'WPA', password: 'secret' }), 'SSID: Office / WPA');
assert.ok(!core.summarizePayload('wifi', { ssid: 'Office', security: 'WPA', password: 'secret' }).includes('secret'));

const repoRoot = path.resolve(__dirname, '..');
const bundlePath = path.join(repoRoot, 'static', 'vendor', 'qrcode', '1.5.4', 'qrcode.min.js');
const licensePath = path.join(repoRoot, 'static', 'vendor', 'qrcode', '1.5.4', 'LICENSE');
const noticePath = path.join(repoRoot, 'THIRD_PARTY_NOTICES.md');
assert.ok(fs.existsSync(bundlePath), 'qrcode browser bundle must exist');
assert.ok(fs.existsSync(licensePath), 'qrcode license must exist');
assert.ok(fs.existsSync(noticePath), 'third-party notice must exist');
const bundle = fs.readFileSync(bundlePath);
assert.strictEqual(crypto.createHash('sha256').update(bundle).digest('hex'), '7706f84597d8466955504c52eab2e9dd9c345626509ea13476863649d01f81dd');
assert.match(fs.readFileSync(licensePath, 'utf8'), /The MIT License \(MIT\)/);
assert.match(fs.readFileSync(noticePath, 'utf8'), /qrcode 1\.5\.4/);

const sandbox = { Promise, Uint8Array, Uint8ClampedArray, ArrayBuffer, TextEncoder };
vm.createContext(sandbox);
vm.runInContext(bundle.toString('utf8'), sandbox, { filename: 'qrcode.min.js' });
assert.ok(sandbox.QRCode && typeof sandbox.QRCode.toString === 'function');

sandbox.QRCode.toString('<script>alert(1)</script>', { type: 'svg', margin: 4, errorCorrectionLevel: 'M' })
    .then(svg => {
        assert.match(svg, /^<svg/);
        assert.ok(!/<script|<foreignObject|<image|<use|<a(?:\s|>)/i.test(svg));
        assert.ok(!/(?:href|xlink:href)=/i.test(svg));
        assert.ok(!svg.includes('<script>alert(1)</script>'));
        process.stdout.write('QR code tests passed\n');
    })
    .catch(error => {
        process.stderr.write('QR code tests failed: ' + error.message + '\n');
        process.exitCode = 1;
    });
