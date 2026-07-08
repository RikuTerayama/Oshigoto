/**
 * 共通ツール実行ランナー
 * 複数ファイルの並列処理、進捗管理、キャンセル機能を提供
 */

class ToolRunner {
    constructor(options = {}) {
        this.maxConcurrency = options.maxConcurrency || 2;
        this.selectedFiles = [];
        this.tasksState = new Map(); // file index -> {status, message, progress}
        this.isRunning = false;
        this.cancelled = false;
        this.outputs = []; // {blob, filename, mime, sourceIndex}
        this.errors = []; // {sourceIndex, message}
        this.onProgress = options.onProgress || (() => {});
        this.onComplete = options.onComplete || (() => {});
        this.onError = options.onError || (() => {});
    }

    /**
     * ファイルを追加
     * @param {File[]} files - 追加するファイル
     */
    addFiles(files) {
        const startIndex = this.selectedFiles.length;
        this.selectedFiles.push(...files);
        files.forEach((file, i) => {
            const index = startIndex + i;
            this.tasksState.set(index, {
                status: 'queued',
                message: '',
                progress: 0
            });
        });
        this.onProgress(this.getProgress());
    }

    /**
     * ファイルを削除
     * @param {number} index - 削除するファイルのインデックス
     */
    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.tasksState.delete(index);
        // インデックスを再構築
        this.rebuildState();
        this.onProgress(this.getProgress());
    }

    /**
     * すべてのファイルをクリア
     */
    clearFiles() {
        this.selectedFiles = [];
        this.tasksState.clear();
        this.outputs = [];
        this.errors = [];
        this.onProgress(this.getProgress());
    }

    /**
     * ファイルは維持し、実行状態のみリセット（モード変更時用）
     */
    resetRunState() {
        this.tasksState.clear();
        this.outputs = [];
        this.errors = [];
        this.selectedFiles.forEach((file, index) => {
            this.tasksState.set(index, {
                status: 'queued',
                message: '',
                progress: 0
            });
        });
        this.onProgress(this.getProgress());
    }

    /**
     * 状態を再構築（ファイル削除後に呼ぶ）
     */
    rebuildState() {
        const newState = new Map();
        this.selectedFiles.forEach((file, newIndex) => {
            const oldState = Array.from(this.tasksState.values())[newIndex];
            if (oldState) {
                newState.set(newIndex, oldState);
            } else {
                newState.set(newIndex, {
                    status: 'queued',
                    message: '',
                    progress: 0
                });
            }
        });
        this.tasksState = newState;
    }

    /**
     * 処理を実行
     * @param {Function} processor - 処理関数 (file, ctx) => Promise<OutputFile[]>
     */
    async run(processor) {
        if (this.isRunning) {
            throw new Error('既に処理が実行中です');
        }

        if (this.selectedFiles.length === 0) {
            throw new Error('ファイルが選択されていません');
        }

        // GA4 イベント: ツール実行開始
        if (typeof window !== 'undefined' && window.gtag) {
            const toolId = this.toolId || 'unknown';
            window.gtag('event', 'tool_run_start', {
                tool_id: toolId,
                file_count: this.selectedFiles.length
            });
        }

        this.isRunning = true;
        this.cancelled = false;
        this.outputs = [];
        this.errors = [];

        // すべてのタスクをqueuedにリセット
        this.selectedFiles.forEach((file, index) => {
            this.tasksState.set(index, {
                status: 'queued',
                message: '',
                progress: 0
            });
        });

        try {
            await this.processFiles(processor);
        } catch (error) {
            if (typeof window !== 'undefined' && typeof window.gaEvent === 'function') {
                window.gaEvent('tool_action_fail', {
                    tool_id: this.toolId || 'unknown',
                    error_type: (error && error.name) || 'error'
                });
            }
            this.onError(error);
        } finally {
            if (!this.cancelled && this.errors.length === 0 && typeof window !== 'undefined' && typeof window.gaEvent === 'function') {
                window.gaEvent('tool_action_success', {
                    tool_id: this.toolId || 'unknown',
                    file_count: this.selectedFiles.length
                });
            }
            this.isRunning = false;
            this.onComplete({
                outputs: this.outputs,
                errors: this.errors,
                cancelled: this.cancelled
            });
        }
    }

    /**
     * ファイルを並列処理
     * @param {Function} processor - 処理関数
     */
    async processFiles(processor) {
        const queue = [...this.selectedFiles.keys()];
        const running = new Set();
        const results = [];

        while (queue.length > 0 || running.size > 0) {
            if (this.cancelled) {
                // キャンセルされた場合、実行中のタスクを待つ
                await Promise.all(Array.from(running));
                break;
            }

            // 並列実行数を満たすまでタスクを開始
            while (running.size < this.maxConcurrency && queue.length > 0) {
                const index = queue.shift();
                const file = this.selectedFiles[index];

                const task = this.processFile(file, index, processor)
                    .then(result => {
                        running.delete(task);
                        results.push(result);
                    })
                    .catch(error => {
                        running.delete(task);
                        this.errors.push({
                            sourceIndex: index,
                            message: error.message || '処理に失敗しました'
                        });
                        this.tasksState.set(index, {
                            status: 'error',
                            message: error.message || '処理に失敗しました',
                            progress: 0
                        });
                        this.onProgress(this.getProgress());
                    });

                running.add(task);
            }

            // 1つでも完了するまで待つ
            if (running.size > 0) {
                await Promise.race(Array.from(running));
            }
        }
    }

    /**
     * 1つのファイルを処理
     * @param {File} file - 処理するファイル
     * @param {number} index - ファイルのインデックス
     * @param {Function} processor - 処理関数
     * @returns {Promise}
     */
    async processFile(file, index, processor) {
        this.tasksState.set(index, {
            status: 'running',
            message: '処理中...',
            progress: 0
        });
        this.onProgress(this.getProgress());

        const ctx = {
            index,
            signal: { cancelled: this.cancelled }
        };

        try {
            const outputFiles = await processor(file, ctx);
            
            if (this.cancelled) {
                this.tasksState.set(index, {
                    status: 'error',
                    message: 'キャンセルされました',
                    progress: 0
                });
                return;
            }

            // 出力ファイルを追加
            outputFiles.forEach(output => {
                this.outputs.push({
                    ...output,
                    sourceIndex: index
                });
            });

            this.tasksState.set(index, {
                status: 'success',
                message: '完了',
                progress: 100
            });
            this.onProgress(this.getProgress());
        } catch (error) {
            this.tasksState.set(index, {
                status: 'error',
                message: error.message || '処理に失敗しました',
                progress: 0
            });
            this.onProgress(this.getProgress());
            throw error;
        }
    }

    /**
     * バッチ処理を実行（複数ファイルを一括処理）
     * @param {Function} batchProcessor - バッチ処理関数 (files, ctx) => Promise<OutputFile[]>
     */
    async runBatch(batchProcessor) {
        if (this.isRunning) {
            throw new Error('既に処理が実行中です');
        }

        if (this.selectedFiles.length === 0) {
            throw new Error('ファイルが選択されていません');
        }

        this.isRunning = true;
        this.cancelled = false;
        this.outputs = [];
        this.errors = [];

        // すべてのタスクをqueuedにリセット
        this.selectedFiles.forEach((file, index) => {
            this.tasksState.set(index, {
                status: 'queued',
                message: '',
                progress: 0
            });
        });

        try {
            const ctx = {
                signal: { cancelled: this.cancelled },
                setTaskState: (index, patch) => {
                    const current = this.tasksState.get(index) || { status: 'queued', message: '', progress: 0 };
                    this.tasksState.set(index, { ...current, ...patch });
                    this.onProgress(this.getProgress());
                },
                setProgress: (progress0to100) => {
                    // 全体進捗を更新（全ファイルに均等に配分）
                    const perFile = progress0to100 / this.selectedFiles.length;
                    this.selectedFiles.forEach((file, index) => {
                        const current = this.tasksState.get(index) || { status: 'queued', message: '', progress: 0 };
                        this.tasksState.set(index, {
                            ...current,
                            progress: Math.min(100, Math.round(perFile * (index + 1)))
                        });
                    });
                    this.onProgress(this.getProgress());
                }
            };

            const outputFiles = await batchProcessor(this.selectedFiles, ctx);

            if (this.cancelled) {
                // キャンセルされた場合、すべてのタスクをエラー状態に
                this.selectedFiles.forEach((file, index) => {
                    this.tasksState.set(index, {
                        status: 'error',
                        message: 'キャンセルされました',
                        progress: 0
                    });
                });
                this.onProgress(this.getProgress());
                return;
            }

            // 出力ファイルを追加
            outputFiles.forEach((output, index) => {
                this.outputs.push({
                    ...output,
                    sourceIndex: index
                });
            });

            // すべてのタスクをsuccessに
            this.selectedFiles.forEach((file, index) => {
                this.tasksState.set(index, {
                    status: 'success',
                    message: '完了',
                    progress: 100
                });
            });
            this.onProgress(this.getProgress());
        } catch (error) {
            this.errors.push({ sourceIndex: -1, message: error.message || 'batch_failed' });
            if (typeof window !== 'undefined' && typeof window.gaEvent === 'function') {
                window.gaEvent('tool_action_fail', {
                    tool_id: this.toolId || 'unknown',
                    error_type: (error && error.name) || 'error'
                });
            }
            this.onError(error);
        } finally {
            if (!this.cancelled && this.errors.length === 0 && typeof window !== 'undefined' && typeof window.gaEvent === 'function') {
                window.gaEvent('tool_action_success', {
                    tool_id: this.toolId || 'unknown',
                    file_count: this.selectedFiles.length
                });
            }
            this.isRunning = false;
            this.onComplete({
                outputs: this.outputs,
                errors: this.errors,
                cancelled: this.cancelled
            });
        }
    }

    /**
     * 処理をキャンセル
     */
    cancel() {
        this.cancelled = true;
        this.isRunning = false;
    }

    /**
     * 進捗情報を取得
     * @returns {Object}
     */
    getProgress() {
        const total = this.selectedFiles.length;
        if (total === 0) {
            return {
                total: 0,
                completed: 0,
                running: 0,
                queued: 0,
                errors: 0,
                progress: 0,
                tasksState: Array.from(this.tasksState.entries())
            };
        }

        let completed = 0;
        let running = 0;
        let queued = 0;
        let errors = 0;

        this.tasksState.forEach(state => {
            switch (state.status) {
                case 'success':
                    completed++;
                    break;
                case 'running':
                    running++;
                    break;
                case 'queued':
                    queued++;
                    break;
                case 'error':
                    errors++;
                    break;
            }
        });

        const progress = Math.round((completed / total) * 100);

        return {
            total,
            completed,
            running,
            queued,
            errors,
            progress,
            tasksState: Array.from(this.tasksState.entries())
        };
    }

    /**
     * 単一ファイルをダウンロード
     * @param {number} outputIndex - 出力ファイルのインデックス
     */
    downloadSingle(outputIndex) {
        const output = this.outputs[outputIndex];
        if (!output) {
            throw new Error('出力ファイルが見つかりません');
        }

        // GA4 イベント: ダウンロード
        if (typeof window !== 'undefined' && window.gtag) {
            const toolId = this.toolId || 'unknown';
            const fileType = output.filename.split('.').pop() || 'unknown';
            window.gtag('event', 'tool_download', {
                tool_id: toolId,
                file_type: fileType,
                download_type: 'single'
            });
        }

        FileUtils.downloadBlob(output.blob, output.filename);
    }

    /**
     * すべての出力をZIPでダウンロード
     * @param {string} zipName - ZIPファイル名
     */
    async downloadAllZip(zipName = 'output.zip') {
        if (this.outputs.length === 0) {
            throw new Error('ダウンロード可能なファイルがありません');
        }
        if (typeof ZipUtils === 'undefined') {
            throw new Error('ZIP機能の読み込みに失敗しました（zip-utils.js）。ページを再読み込みしてください。');
        }

        try {
            const zipBlob = await ZipUtils.createZip(
                this.outputs.map(o => ({
                    blob: o.blob,
                    filename: o.filename
                })),
                zipName
            );

            // GA4 イベント: ZIPダウンロード
            if (typeof window !== 'undefined' && window.gtag) {
                const toolId = this.toolId || 'unknown';
                window.gtag('event', 'tool_download', {
                    tool_id: toolId,
                    file_type: 'zip',
                    download_type: 'zip',
                    file_count: this.outputs.length
                });
            }

            FileUtils.downloadBlob(zipBlob, zipName);
        } catch (error) {
            throw new Error(`ZIP作成に失敗しました: ${error.message}`);
        }
    }
}
