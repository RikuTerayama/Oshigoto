(function () {
    'use strict';

    var root = document.getElementById('qr-code-app');
    if (!root || !window.QrCodeCore || !window.QRCode) return;

    var core = window.QrCodeCore;
    var form = document.getElementById('qr-code-form');
    var typeInputs = Array.prototype.slice.call(form.querySelectorAll('input[name="qr-type"]'));
    var panels = Array.prototype.slice.call(form.querySelectorAll('[data-qr-panel]'));
    var generateButton = document.getElementById('qr-generate');
    var status = document.getElementById('qr-status');
    var byteCounter = document.getElementById('qr-byte-count');
    var output = document.getElementById('qr-output');
    var canvas = document.getElementById('qr-preview-canvas');
    var pngDownload = document.getElementById('qr-download-png');
    var svgDownload = document.getElementById('qr-download-svg');
    var outputType = document.getElementById('qr-output-type');
    var outputSummary = document.getElementById('qr-output-summary');
    var outputLevel = document.getElementById('qr-output-level');
    var outputDimensions = document.getElementById('qr-output-dimensions');
    var recreateButton = document.getElementById('qr-recreate');
    var clearButton = document.getElementById('qr-clear');
    var wifiSecurity = document.getElementById('qr-wifi-security');
    var wifiPassword = document.getElementById('qr-wifi-password');
    var objectUrls = [];

    function selectedType() {
        var checked = form.querySelector('input[name="qr-type"]:checked');
        return checked ? checked.value : 'url';
    }

    function fieldValue(id) {
        var element = document.getElementById(id);
        return element ? element.value : '';
    }

    function collectData(type) {
        if (type === 'url') return { url: fieldValue('qr-url') };
        if (type === 'text') return { text: fieldValue('qr-text') };
        if (type === 'email') return { address: fieldValue('qr-email-address'), subject: fieldValue('qr-email-subject'), body: fieldValue('qr-email-body') };
        if (type === 'phone') return { phone: fieldValue('qr-phone') };
        return {
            ssid: fieldValue('qr-wifi-ssid'),
            security: fieldValue('qr-wifi-security'),
            password: wifiSecurity.value === 'nopass' ? '' : fieldValue('qr-wifi-password'),
            hidden: document.getElementById('qr-wifi-hidden').checked
        };
    }

    function collectSettings() {
        return {
            errorCorrectionLevel: fieldValue('qr-error-level'),
            width: Number(fieldValue('qr-output-size')),
            margin: Number(fieldValue('qr-margin')),
            dark: '#000000',
            light: '#FFFFFF'
        };
    }

    function fallbackByteCount(type, data) {
        if (type === 'url') return core.byteLength(data.url);
        if (type === 'text') return core.byteLength(data.text);
        if (type === 'email') return core.byteLength(data.address) + core.byteLength(data.subject) + core.byteLength(data.body);
        if (type === 'phone') return core.byteLength(data.phone);
        return core.byteLength(data.ssid) + (data.security === 'nopass' ? 0 : core.byteLength(data.password));
    }

    function updateByteCounter() {
        var type = selectedType();
        var data = collectData(type);
        var bytes;
        try {
            bytes = core.byteLength(core.buildPayload(type, data));
        } catch (error) {
            bytes = fallbackByteCount(type, data);
        }
        byteCounter.textContent = bytes.toLocaleString('ja-JP') + ' / ' + core.MAX_PAYLOAD_BYTES.toLocaleString('ja-JP') + ' bytes';
        byteCounter.classList.toggle('is-over', bytes > core.MAX_PAYLOAD_BYTES);
    }

    function updateWifiState() {
        var noPassword = wifiSecurity.value === 'nopass';
        wifiPassword.disabled = noPassword;
        wifiPassword.required = !noPassword;
        document.getElementById('qr-wifi-password-field').classList.toggle('is-disabled', noPassword);
        updateByteCounter();
    }

    function clearFieldErrors() {
        Array.prototype.slice.call(form.querySelectorAll('[aria-invalid="true"]')).forEach(function (field) {
            field.removeAttribute('aria-invalid');
            field.removeAttribute('aria-describedby');
        });
    }

    function markErrorField(code) {
        var fieldByPrefix = {
            EMAIL_SUBJECT: 'qr-email-subject', EMAIL_BODY: 'qr-email-body',
            URL: 'qr-url', TEXT: 'qr-text', EMAIL: 'qr-email-address', PHONE: 'qr-phone',
            WIFI_SSID: 'qr-wifi-ssid', WIFI_PASSWORD: 'qr-wifi-password', WIFI_SECURITY: 'qr-wifi-security',
            ERROR_LEVEL: 'qr-error-level', OUTPUT_SIZE: 'qr-output-size', MARGIN: 'qr-margin'
        };
        var fieldId = Object.keys(fieldByPrefix).find(function (prefix) { return String(code || '').indexOf(prefix) === 0; });
        var field = fieldId ? document.getElementById(fieldByPrefix[fieldId]) : null;
        if (field && !field.disabled) {
            field.setAttribute('aria-invalid', 'true');
            field.setAttribute('aria-describedby', 'qr-status qr-byte-count');
        }
    }

    function updateType() {
        var type = selectedType();
        panels.forEach(function (panel) {
            var active = panel.getAttribute('data-qr-panel') === type;
            panel.hidden = !active;
            panel.setAttribute('aria-hidden', active ? 'false' : 'true');
            Array.prototype.slice.call(panel.querySelectorAll('input, textarea, select')).forEach(function (field) {
                if (field.id !== 'qr-wifi-password') field.disabled = !active;
            });
        });
        updateWifiState();
        clearFieldErrors();
        clearOutput();
        status.textContent = '';
        updateByteCounter();
    }

    function revokeObjectUrls() {
        objectUrls.forEach(function (url) { URL.revokeObjectURL(url); });
        objectUrls = [];
    }

    function clearOutput() {
        revokeObjectUrls();
        output.hidden = true;
        outputType.textContent = '';
        outputSummary.textContent = '';
        outputLevel.textContent = '';
        outputDimensions.textContent = '';
        pngDownload.removeAttribute('href');
        svgDownload.removeAttribute('href');
        var context = canvas.getContext('2d');
        if (context) context.clearRect(0, 0, canvas.width, canvas.height);
    }

    function canvasToBlob(targetCanvas) {
        return new Promise(function (resolve, reject) {
            targetCanvas.toBlob(function (blob) {
                if (blob) resolve(blob);
                else reject(new Error('PNG_OUTPUT_FAILED'));
            }, 'image/png');
        });
    }

    function verifyPng(blob) {
        if (!blob || blob.type !== 'image/png') return Promise.resolve(false);
        return blob.slice(0, 8).arrayBuffer().then(function (buffer) {
            var bytes = new Uint8Array(buffer);
            var signature = [137, 80, 78, 71, 13, 10, 26, 10];
            return signature.every(function (value, index) { return bytes[index] === value; });
        });
    }

    function verifySvg(svgText) {
        if (typeof svgText !== 'string' || svgText.length > 500000) return false;
        var documentNode = new DOMParser().parseFromString(svgText, 'image/svg+xml');
        var rootNode = documentNode.documentElement;
        if (!rootNode || rootNode.localName !== 'svg' || documentNode.querySelector('parsererror')) return false;
        if (documentNode.querySelector('script, foreignObject, image, use, a')) return false;
        var nodes = documentNode.querySelectorAll('*');
        for (var index = 0; index < nodes.length; index += 1) {
            var node = nodes[index];
            for (var attributeIndex = 0; attributeIndex < node.attributes.length; attributeIndex += 1) {
                var attribute = node.attributes[attributeIndex];
                if (/^on/i.test(attribute.name)) return false;
                if (/(^|:)href$/i.test(attribute.name)) return false;
            }
        }
        return true;
    }

    function prepareDownload(anchor, blob, filename) {
        var url = URL.createObjectURL(blob);
        objectUrls.push(url);
        anchor.href = url;
        anchor.download = filename;
    }

    async function generate(event) {
        event.preventDefault();
        clearFieldErrors();
        clearOutput();
        status.textContent = '';
        generateButton.disabled = true;
        generateButton.textContent = '作成中…';
        try {
            var type = selectedType();
            var data = collectData(type);
            var payload = core.buildPayload(type, data);
            var settings = core.validateSettings(collectSettings());
            await window.QRCode.toCanvas(canvas, payload, settings);
            var pngBlob = await canvasToBlob(canvas);
            if (!(await verifyPng(pngBlob))) throw new Error('PNG_VERIFY_FAILED');
            var svgText = await window.QRCode.toString(payload, {
                type: 'svg',
                errorCorrectionLevel: settings.errorCorrectionLevel,
                width: settings.width,
                margin: settings.margin,
                color: settings.color
            });
            if (!verifySvg(svgText)) throw new Error('SVG_VERIFY_FAILED');
            var svgBlob = new Blob([svgText], { type: 'image/svg+xml' });
            prepareDownload(pngDownload, pngBlob, core.getFilename(type, 'png'));
            prepareDownload(svgDownload, svgBlob, core.getFilename(type, 'svg'));
            outputType.textContent = core.getTypeLabel(type);
            outputSummary.textContent = core.summarizePayload(type, data);
            outputLevel.textContent = settings.errorCorrectionLevel;
            outputDimensions.textContent = settings.width + 'px × ' + settings.width + 'px';
            output.hidden = false;
            status.textContent = 'QRコードを作成しました。実際に使用する前に、読み取りできることを確認してください。';
            output.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } catch (error) {
            if (error && error.name === 'QrInputError') {
                status.textContent = error.message;
                markErrorField(error.code);
            }
            else status.textContent = 'QRコードを作成できませんでした。入力内容や設定を確認してください。';
        } finally {
            generateButton.disabled = false;
            generateButton.textContent = 'QRコードを作成';
            updateByteCounter();
        }
    }

    typeInputs.forEach(function (input) { input.addEventListener('change', updateType); });
    form.addEventListener('input', function () {
        updateByteCounter();
        clearFieldErrors();
        if (!output.hidden) clearOutput();
    });
    form.addEventListener('change', function () {
        updateByteCounter();
        clearFieldErrors();
        if (!output.hidden) clearOutput();
    });
    wifiSecurity.addEventListener('change', updateWifiState);
    form.addEventListener('submit', generate);
    recreateButton.addEventListener('click', function () {
        clearOutput();
        form.querySelector('[data-qr-panel]:not([hidden]) input:not([disabled]), [data-qr-panel]:not([hidden]) textarea:not([disabled])').focus();
    });
    clearButton.addEventListener('click', function () {
        form.reset();
        updateType();
        form.querySelector('input[name="qr-type"]:checked').focus();
    });
    window.addEventListener('pagehide', revokeObjectUrls);
    updateType();
}());
