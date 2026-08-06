/** Browser-only JPEG, PNG, and WebP compression controller. */
(function () {
    'use strict';

    const root = document.getElementById('image-compress-app');
    if (!root || !window.ImageCompressCore) return;

    const Core = window.ImageCompressCore;
    const limits = Object.freeze({
        maxFiles: Number(root.dataset.maxFiles),
        maxFileBytes: Number(root.dataset.maxFileMb) * 1024 * 1024,
        maxTotalBytes: Number(root.dataset.maxTotalMb) * 1024 * 1024,
        maxPixels: Number(root.dataset.maxPixels),
        maxLongEdge: Number(root.dataset.maxLongEdge),
    });
    const elements = {
        dropzone: document.getElementById('compress-dropzone'),
        fileInput: document.getElementById('compress-files'),
        fileList: document.getElementById('compress-file-list'),
        outputFormat: document.getElementById('compress-output-format'),
        quality: document.getElementById('compress-quality'),
        qualityValue: document.getElementById('compress-quality-value'),
        qualityHelp: document.getElementById('compress-quality-help'),
        maxWidth: document.getElementById('compress-max-width'),
        maxHeight: document.getElementById('compress-max-height'),
        run: document.getElementById('compress-run'),
        cancel: document.getElementById('compress-cancel'),
        progress: document.getElementById('compress-progress'),
        errors: document.getElementById('compress-errors'),
        resultsSection: document.getElementById('compress-results-section'),
        results: document.getElementById('compress-results'),
        zip: document.getElementById('compress-zip'),
    };
    const state = { files: [], results: [], running: false, cancelled: false, previewUrls: [] };

    function formatBytes(bytes) {
        return FileUtils.formatBytes(bytes);
    }

    function setStatus(message) {
        elements.progress.textContent = message;
    }

    function clearErrors() {
        elements.errors.hidden = true;
        elements.errors.replaceChildren();
    }

    function showErrors(messages) {
        elements.errors.replaceChildren();
        const heading = document.createElement('strong');
        heading.textContent = '確認してください';
        elements.errors.appendChild(heading);
        const list = document.createElement('ul');
        messages.forEach((message) => {
            const item = document.createElement('li');
            item.textContent = message;
            list.appendChild(item);
        });
        elements.errors.appendChild(list);
        elements.errors.hidden = false;
    }

    function revokePreviews() {
        state.previewUrls.forEach((url) => URL.revokeObjectURL(url));
        state.previewUrls = [];
    }

    function clearResults() {
        revokePreviews();
        state.results = [];
        elements.results.replaceChildren();
        elements.resultsSection.hidden = true;
        elements.zip.hidden = true;
        elements.zip.disabled = false;
    }

    function basicFileError(file) {
        if (!file || file.size === 0) return '0 byteのファイルは処理できません。';
        if (file.size > limits.maxFileBytes) return `1ファイル${root.dataset.maxFileMb}MB以下の画像を選択してください。`;
        const extensionFormat = Core.EXTENSION_FORMAT[Core.getExtension(file.name)] || null;
        const mimeFormat = Core.MIME_FORMAT[String(file.type || '').toLowerCase()] || null;
        if (!extensionFormat) return '対応形式は静止画のJPEG・PNG・WebPです。';
        if (file.type && !mimeFormat) return '対応形式は静止画のJPEG・PNG・WebPです。';
        if (mimeFormat && extensionFormat !== mimeFormat) return '拡張子とMIMEタイプが一致していません。';
        return null;
    }

    function acceptFiles(fileList) {
        if (state.running) return;
        const incoming = Array.from(fileList || []);
        clearErrors();
        try {
            Core.validateSelectionLimits(incoming, limits.maxFiles, limits.maxFileBytes, limits.maxTotalBytes);
        } catch (error) {
            state.files = [];
            renderFiles();
            updateControls();
            showErrors([error.message]);
            return;
        }
        const errors = [];
        incoming.forEach((file) => {
            const reason = basicFileError(file);
            if (reason) errors.push(`${Core.sanitizeFilename(file.name)}: ${reason}`);
        });
        if (errors.length) {
            state.files = [];
            renderFiles();
            showErrors(errors);
            return;
        }
        state.files = incoming;
        clearResults();
        renderFiles();
        updateControls();
        setStatus(incoming.length ? `${incoming.length}件を選択しました。` : '画像を選択してください。');
    }

    function renderFiles() {
        elements.fileList.replaceChildren();
        state.files.forEach((file, index) => {
            const row = document.createElement('div');
            row.className = 'compress-file-row';
            const copy = document.createElement('div');
            copy.className = 'compress-file-row__copy';
            const name = document.createElement('strong');
            name.textContent = Core.sanitizeFilename(file.name);
            const size = document.createElement('span');
            size.textContent = formatBytes(file.size);
            copy.append(name, size);
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'compress-file-row__remove';
            remove.textContent = '削除';
            remove.setAttribute('aria-label', `${Core.sanitizeFilename(file.name)}を選択から外す`);
            remove.addEventListener('click', () => {
                if (state.running) return;
                state.files.splice(index, 1);
                clearResults();
                renderFiles();
                updateControls();
            });
            row.append(copy, remove);
            elements.fileList.appendChild(row);
        });
    }

    function updateQualityUi() {
        const selection = elements.outputFormat.value;
        const allPng = state.files.length > 0 && state.files.every((file) => Core.getExtension(file.name) === 'png');
        const disabled = selection === 'png' || (selection === 'original' && allPng);
        elements.quality.disabled = disabled;
        elements.qualityValue.textContent = elements.quality.value;
        elements.quality.setAttribute('aria-valuetext', `${elements.quality.value}%`);
        if (selection === 'png') {
            elements.qualityHelp.textContent = 'PNGでは品質値を指定できません。寸法の縮小やWebP/JPEGへの変換で容量が小さくなる場合があります。';
        } else if (selection === 'original') {
            elements.qualityHelp.textContent = '元の形式がJPEGまたはWebPの画像に適用します。PNGには品質値を適用しません。';
        } else {
            elements.qualityHelp.textContent = `${selection === 'jpeg' ? 'JPEG' : 'WebP'}出力へ適用します。数値を下げるほど容量が小さくなる傾向があります。`;
        }
    }

    function updateControls() {
        elements.run.disabled = state.running || state.files.length === 0;
        elements.cancel.hidden = !state.running;
        elements.cancel.disabled = false;
        elements.fileInput.disabled = state.running;
        elements.outputFormat.disabled = state.running;
        elements.maxWidth.disabled = state.running;
        elements.maxHeight.disabled = state.running;
        updateQualityUi();
        if (state.running) elements.quality.disabled = true;
    }

    async function inspectFile(file) {
        let buffer;
        try {
            buffer = await file.arrayBuffer();
            return Core.validateIdentity(file.name, file.type, buffer);
        } finally {
            buffer = null;
        }
    }

    async function decodeImage(file) {
        if (typeof createImageBitmap === 'function') {
            try {
                const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
                return { source: bitmap, width: bitmap.width, height: bitmap.height, close: () => bitmap.close() };
            } catch (_) {
                // Fall back to HTMLImageElement for browsers without the option.
            }
        }
        const image = await ImageConverter.loadImageElement(file);
        return { source: image, width: image.naturalWidth || image.width, height: image.naturalHeight || image.height, close: () => {} };
    }

    function canvasToBlob(canvas, mime, quality) {
        return new Promise((resolve, reject) => {
            canvas.toBlob((blob) => {
                if (!blob) reject(new Error('画像を書き出せませんでした。設定を変えてお試しください。'));
                else if (blob.type !== mime) reject(new Error('このブラウザでは選択した出力形式を作成できません。'));
                else resolve(blob);
            }, mime, quality == null ? undefined : quality);
        });
    }

    async function compressOne(file, settings, usedNames) {
        const inputFormat = await inspectFile(file);
        if (state.cancelled) throw new Error('キャンセルされました。');
        const decoded = await decodeImage(file);
        let canvas;
        try {
            Core.validateImageLimits(decoded.width, decoded.height, limits.maxPixels, limits.maxLongEdge);
            const dimensions = Core.calculateDimensions(decoded.width, decoded.height, settings.maxWidth, settings.maxHeight);
            const outputFormat = Core.resolveOutputFormat(settings.outputFormat, inputFormat);
            const quality = Core.normalizeQuality(settings.quality, outputFormat);
            canvas = document.createElement('canvas');
            canvas.width = dimensions.width;
            canvas.height = dimensions.height;
            const context = canvas.getContext('2d', { alpha: outputFormat !== 'jpeg' });
            if (!context) throw new Error('画像処理を開始できませんでした。');
            if (outputFormat === 'jpeg') {
                context.fillStyle = '#ffffff';
                context.fillRect(0, 0, dimensions.width, dimensions.height);
            }
            context.drawImage(decoded.source, 0, 0, dimensions.width, dimensions.height);
            const blob = await canvasToBlob(canvas, Core.FORMAT_MIME[outputFormat], quality);
            if (state.cancelled) throw new Error('キャンセルされました。');
            const filename = Core.generateOutputFilename(file.name, outputFormat, usedNames);
            return {
                blob,
                filename,
                displayName: Core.sanitizeFilename(file.name),
                inputFormat,
                outputFormat,
                originalWidth: decoded.width,
                originalHeight: decoded.height,
                outputWidth: dimensions.width,
                outputHeight: dimensions.height,
                originalBytes: file.size,
                outputBytes: blob.size,
                change: Core.describeSizeChange(file.size, blob.size),
            };
        } finally {
            decoded.close();
            if (canvas) {
                canvas.width = 1;
                canvas.height = 1;
                canvas.remove();
            }
        }
    }

    function formatName(format) {
        return format === 'jpeg' ? 'JPEG' : format === 'png' ? 'PNG' : 'WebP';
    }

    function addDetail(list, label, value) {
        const wrapper = document.createElement('div');
        const term = document.createElement('dt');
        term.textContent = label;
        const detail = document.createElement('dd');
        detail.textContent = value;
        wrapper.append(term, detail);
        list.appendChild(wrapper);
    }

    function renderResults() {
        elements.results.replaceChildren();
        revokePreviews();
        state.results.forEach((result) => {
            const card = document.createElement('article');
            card.className = 'compress-result-card';
            const preview = document.createElement('img');
            preview.className = 'compress-result-card__preview';
            preview.alt = '';
            const previewUrl = URL.createObjectURL(result.blob);
            state.previewUrls.push(previewUrl);
            preview.src = previewUrl;
            const title = document.createElement('h3');
            title.textContent = result.displayName;
            const details = document.createElement('dl');
            details.className = 'compress-result-card__details';
            addDetail(details, '形式', `${formatName(result.inputFormat)} → ${formatName(result.outputFormat)}`);
            addDetail(details, '寸法', `${result.originalWidth}×${result.originalHeight}px → ${result.outputWidth}×${result.outputHeight}px`);
            addDetail(details, '容量', `${formatBytes(result.originalBytes)} → ${formatBytes(result.outputBytes)}`);
            const change = document.createElement('p');
            change.className = `compress-result-card__change compress-result-card__change--${result.change.kind}`;
            change.textContent = result.change.text;
            if (result.change.kind === 'increased') {
                const hint = document.createElement('p');
                hint.className = 'compress-result-card__hint';
                hint.textContent = '品質を下げる、最大幅を設定する、またはWebPへ変換すると小さくなる場合があります。';
                card.append(preview, title, details, change, hint);
            } else {
                card.append(preview, title, details, change);
            }
            const download = document.createElement('button');
            download.type = 'button';
            download.className = 'btn btn-primary compress-result-card__download';
            download.textContent = '個別にダウンロード';
            download.addEventListener('click', () => FileUtils.downloadBlob(result.blob, result.filename));
            card.appendChild(download);
            elements.results.appendChild(card);
        });
        elements.resultsSection.hidden = state.results.length === 0;
        elements.zip.hidden = state.results.length < 2;
    }

    async function runCompression() {
        if (state.running || state.files.length === 0) return;
        clearErrors();
        clearResults();
        let maxWidth;
        let maxHeight;
        try {
            maxWidth = Core.parsePositiveInteger(elements.maxWidth.value, limits.maxLongEdge, '最大幅');
            maxHeight = Core.parsePositiveInteger(elements.maxHeight.value, limits.maxLongEdge, '最大高さ');
            Core.normalizeQuality(elements.quality.value, elements.outputFormat.value === 'png' ? 'png' : 'jpeg');
        } catch (error) {
            showErrors([error.message]);
            return;
        }
        state.running = true;
        state.cancelled = false;
        updateControls();
        const errors = [];
        const usedNames = new Set();
        const settings = { outputFormat: elements.outputFormat.value, quality: elements.quality.value, maxWidth, maxHeight };
        for (let index = 0; index < state.files.length; index += 1) {
            if (state.cancelled) break;
            setStatus(`${index + 1}/${state.files.length}件目を処理しています。`);
            try {
                const result = await compressOne(state.files[index], settings, usedNames);
                state.results.push(result);
            } catch (error) {
                if (state.cancelled) break;
                errors.push(`${Core.sanitizeFilename(state.files[index].name)}: ${error.message || '画像を処理できませんでした。'}`);
            }
            await new Promise((resolve) => setTimeout(resolve, 0));
        }
        state.running = false;
        updateControls();
        renderResults();
        if (errors.length) showErrors(errors);
        setStatus(state.cancelled
            ? `キャンセルしました。完了済みの${state.results.length}件は保存できます。`
            : `${state.results.length}/${state.files.length}件の処理が完了しました。`);
    }

    async function downloadZip() {
        if (state.results.length < 2 || elements.zip.disabled) return;
        const total = state.results.reduce((sum, result) => sum + result.outputBytes, 0);
        if (total > limits.maxTotalBytes) {
            showErrors([`出力合計が${root.dataset.maxTotalMb}MBを超えるためZIPを作成できません。個別に保存してください。`]);
            return;
        }
        elements.zip.disabled = true;
        elements.zip.textContent = 'ZIPを作成しています…';
        try {
            const blob = await ZipUtils.createZip(state.results, 'compressed-images.zip');
            FileUtils.downloadBlob(blob, 'compressed-images.zip');
        } catch (_) {
            showErrors(['ZIPを作成できませんでした。個別ダウンロードをお使いください。']);
        } finally {
            elements.zip.disabled = false;
            elements.zip.textContent = 'まとめてZIPでダウンロード';
        }
    }

    elements.fileInput.addEventListener('change', (event) => acceptFiles(event.target.files));
    elements.dropzone.addEventListener('click', () => { if (!state.running) elements.fileInput.click(); });
    elements.dropzone.addEventListener('keydown', (event) => {
        if ((event.key === 'Enter' || event.key === ' ') && !state.running) {
            event.preventDefault();
            elements.fileInput.click();
        }
    });
    ['dragenter', 'dragover'].forEach((name) => elements.dropzone.addEventListener(name, (event) => {
        event.preventDefault();
        if (!state.running) elements.dropzone.classList.add('is-dragging');
    }));
    ['dragleave', 'drop'].forEach((name) => elements.dropzone.addEventListener(name, (event) => {
        event.preventDefault();
        elements.dropzone.classList.remove('is-dragging');
    }));
    elements.dropzone.addEventListener('drop', (event) => { if (!state.running) acceptFiles(event.dataTransfer.files); });
    elements.outputFormat.addEventListener('change', updateQualityUi);
    elements.quality.addEventListener('input', updateQualityUi);
    elements.run.addEventListener('click', runCompression);
    elements.cancel.addEventListener('click', () => {
        state.cancelled = true;
        elements.cancel.disabled = true;
        setStatus('現在の処理を終えてから停止します。');
    });
    elements.zip.addEventListener('click', downloadZip);
    window.addEventListener('beforeunload', revokePreviews);
    updateQualityUi();
    updateControls();
})();
