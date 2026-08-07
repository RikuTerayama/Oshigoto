(function (root, factory) {
    'use strict';
    var api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.QrCodeCore = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    var MAX_PAYLOAD_BYTES = 1000;
    var SSID_MAX_BYTES = 128;
    var WIFI_PASSWORD_MAX_BYTES = 256;
    var ERROR_LEVELS = ['L', 'M', 'Q', 'H'];
    var OUTPUT_SIZES = [256, 512, 1024];
    var MARGINS = [2, 4, 8];
    var TYPE_LABELS = {
        url: 'URL',
        text: 'テキスト',
        email: 'メール',
        phone: '電話番号',
        wifi: 'Wi-Fi接続情報'
    };

    function QrInputError(code, message) {
        this.name = 'QrInputError';
        this.code = code;
        this.message = message;
        if (Error.captureStackTrace) Error.captureStackTrace(this, QrInputError);
    }
    QrInputError.prototype = Object.create(Error.prototype);
    QrInputError.prototype.constructor = QrInputError;

    function fail(code, message) {
        throw new QrInputError(code, message);
    }

    function byteLength(value) {
        var text = String(value == null ? '' : value);
        if (typeof TextEncoder !== 'undefined') return new TextEncoder().encode(text).length;
        if (typeof Buffer !== 'undefined') return Buffer.byteLength(text, 'utf8');
        return unescape(encodeURIComponent(text)).length;
    }

    function hasControlCharacters(value, allowTextWhitespace) {
        var pattern = allowTextWhitespace ? /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/ : /[\u0000-\u001F\u007F]/;
        return pattern.test(String(value == null ? '' : value));
    }

    function ensurePayloadSize(payload) {
        var bytes = byteLength(payload);
        if (bytes > MAX_PAYLOAD_BYTES) {
            fail('PAYLOAD_TOO_LARGE', 'QRコードに入れる内容は1,000バイト以内にしてください。');
        }
        return payload;
    }

    function buildUrlPayload(data) {
        var value = String(data.url == null ? '' : data.url).trim();
        if (!value) fail('URL_REQUIRED', 'URLを入力してください。');
        if (hasControlCharacters(value, false)) fail('URL_CONTROL_CHARACTER', 'URLに制御文字は使用できません。');
        var parsed;
        try {
            parsed = new URL(value);
        } catch (error) {
            fail('URL_INVALID', 'http:// または https:// から始まる正しいURLを入力してください。');
        }
        if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
            fail('URL_SCHEME_NOT_ALLOWED', 'URLは http:// または https:// のみ使用できます。');
        }
        return ensurePayloadSize(value);
    }

    function buildTextPayload(data) {
        var value = String(data.text == null ? '' : data.text);
        if (!value.trim()) fail('TEXT_REQUIRED', 'テキストを入力してください。');
        if (hasControlCharacters(value, true)) fail('TEXT_CONTROL_CHARACTER', 'テキストに使用できない制御文字が含まれています。');
        return ensurePayloadSize(value);
    }

    function buildEmailPayload(data) {
        var address = String(data.address == null ? '' : data.address).trim();
        var subject = String(data.subject == null ? '' : data.subject);
        var body = String(data.body == null ? '' : data.body);
        if (!address) fail('EMAIL_REQUIRED', 'メールアドレスを入力してください。');
        if (hasControlCharacters(address, false) || !/^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(address)) {
            fail('EMAIL_INVALID', '正しいメールアドレスを入力してください。');
        }
        if (hasControlCharacters(subject, false)) fail('EMAIL_SUBJECT_CONTROL_CHARACTER', '件名に改行や制御文字は使用できません。');
        if (hasControlCharacters(body, true)) fail('EMAIL_BODY_CONTROL_CHARACTER', '本文に使用できない制御文字が含まれています。');
        var query = [];
        if (subject) query.push('subject=' + encodeURIComponent(subject));
        if (body) query.push('body=' + encodeURIComponent(body));
        return ensurePayloadSize('mailto:' + address + (query.length ? '?' + query.join('&') : ''));
    }

    function buildPhonePayload(data) {
        var raw = String(data.phone == null ? '' : data.phone).trim();
        if (!raw) fail('PHONE_REQUIRED', '電話番号を入力してください。');
        if (hasControlCharacters(raw, false) || !/^\+?[0-9()\- ]+$/.test(raw)) {
            fail('PHONE_INVALID_CHARACTER', '電話番号には数字、先頭の+、空白、ハイフン、丸括弧だけを使用できます。');
        }
        var normalized = raw.replace(/[()\- ]/g, '');
        if ((normalized.match(/\+/g) || []).length > 1 || (normalized.indexOf('+') > 0)) {
            fail('PHONE_PLUS_POSITION', '+は電話番号の先頭にだけ使用できます。');
        }
        var digits = normalized.replace(/^\+/, '');
        if (!/^\d{3,20}$/.test(digits)) fail('PHONE_LENGTH', '電話番号は3〜20桁で入力してください。');
        return ensurePayloadSize('tel:' + normalized);
    }

    function escapeWifiValue(value) {
        return String(value == null ? '' : value).replace(/([\\;,:])/g, '\\$1');
    }

    function buildWifiPayload(data) {
        var ssid = String(data.ssid == null ? '' : data.ssid);
        var security = String(data.security || 'WPA');
        var password = String(data.password == null ? '' : data.password);
        var hidden = data.hidden === true || data.hidden === 'true';
        if (!ssid) fail('WIFI_SSID_REQUIRED', 'SSIDを入力してください。');
        if (hasControlCharacters(ssid, false)) fail('WIFI_SSID_CONTROL_CHARACTER', 'SSIDに制御文字は使用できません。');
        if (byteLength(ssid) > SSID_MAX_BYTES) fail('WIFI_SSID_TOO_LARGE', 'SSIDは128バイト以内にしてください。');
        if (['WPA', 'WEP', 'nopass'].indexOf(security) === -1) fail('WIFI_SECURITY_INVALID', 'Wi-Fiのセキュリティ方式を選択してください。');
        if (security !== 'nopass') {
            if (!password) fail('WIFI_PASSWORD_REQUIRED', 'Wi-Fiパスワードを入力してください。');
            if (hasControlCharacters(password, false)) fail('WIFI_PASSWORD_CONTROL_CHARACTER', 'Wi-Fiパスワードに制御文字は使用できません。');
            if (byteLength(password) > WIFI_PASSWORD_MAX_BYTES) fail('WIFI_PASSWORD_TOO_LARGE', 'Wi-Fiパスワードは256バイト以内にしてください。');
        }
        var payload = 'WIFI:T:' + security + ';S:' + escapeWifiValue(ssid) + ';';
        if (security !== 'nopass') payload += 'P:' + escapeWifiValue(password) + ';';
        payload += 'H:' + (hidden ? 'true' : 'false') + ';;';
        return ensurePayloadSize(payload);
    }

    function buildPayload(type, data) {
        var builders = {
            url: buildUrlPayload,
            text: buildTextPayload,
            email: buildEmailPayload,
            phone: buildPhonePayload,
            wifi: buildWifiPayload
        };
        if (!builders[type]) fail('TYPE_INVALID', '作成するQRコードの種類を選択してください。');
        return builders[type](data || {});
    }

    function normalizeColor(value, fallback) {
        var color = String(value || fallback || '').trim();
        if (!/^#[0-9a-f]{6}$/i.test(color)) fail('COLOR_INVALID', '色は6桁の16進カラーで指定してください。');
        return color.toUpperCase();
    }

    function validateSettings(settings) {
        var input = settings || {};
        var errorCorrectionLevel = String(input.errorCorrectionLevel || 'M').toUpperCase();
        var width = Number(input.width || 512);
        var margin = Number(input.margin == null ? 4 : input.margin);
        var dark = normalizeColor(input.dark, '#000000');
        var light = normalizeColor(input.light, '#FFFFFF');
        if (ERROR_LEVELS.indexOf(errorCorrectionLevel) === -1) fail('ERROR_LEVEL_INVALID', '誤り訂正レベルを選択してください。');
        if (OUTPUT_SIZES.indexOf(width) === -1) fail('OUTPUT_SIZE_INVALID', '出力サイズを選択してください。');
        if (MARGINS.indexOf(margin) === -1) fail('MARGIN_INVALID', '余白は2、4、8のいずれかを選択してください。');
        if (dark === light) fail('COLOR_CONTRAST_INVALID', '前景色と背景色は異なる色にしてください。');
        return { errorCorrectionLevel: errorCorrectionLevel, width: width, margin: margin, color: { dark: dark, light: light } };
    }

    function shorten(value, maxLength) {
        var text = String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
        return text.length > maxLength ? text.slice(0, maxLength) + '…' : text;
    }

    function summarizePayload(type, data) {
        var input = data || {};
        if (type === 'url') {
            var url = buildUrlPayload(input);
            try {
                return new URL(url).hostname;
            } catch (error) {
                return shorten(url, 40);
            }
        }
        if (type === 'text') return shorten(String(input.text == null ? '' : input.text), 40);
        if (type === 'email') return String(input.address == null ? '' : input.address).trim();
        if (type === 'phone') return buildPhonePayload(input).replace(/^tel:/, '');
        if (type === 'wifi') {
            var security = String(input.security || 'WPA');
            return 'SSID: ' + shorten(input.ssid, 40) + ' / ' + (security === 'nopass' ? 'パスワードなし' : security);
        }
        fail('TYPE_INVALID', '作成するQRコードの種類を選択してください。');
    }

    function getFilename(type, extension) {
        var safeType = TYPE_LABELS[type] ? type : 'text';
        var safeExtension = extension === 'svg' ? 'svg' : 'png';
        return 'qr-' + safeType + '.' + safeExtension;
    }

    function getTypeLabel(type) {
        return TYPE_LABELS[type] || 'QRコード';
    }

    return {
        MAX_PAYLOAD_BYTES: MAX_PAYLOAD_BYTES,
        SSID_MAX_BYTES: SSID_MAX_BYTES,
        WIFI_PASSWORD_MAX_BYTES: WIFI_PASSWORD_MAX_BYTES,
        QrInputError: QrInputError,
        byteLength: byteLength,
        buildPayload: buildPayload,
        buildUrlPayload: buildUrlPayload,
        buildTextPayload: buildTextPayload,
        buildEmailPayload: buildEmailPayload,
        buildPhonePayload: buildPhonePayload,
        buildWifiPayload: buildWifiPayload,
        escapeWifiValue: escapeWifiValue,
        validateSettings: validateSettings,
        summarizePayload: summarizePayload,
        getFilename: getFilename,
        getTypeLabel: getTypeLabel
    };
}));
