// ═══════════════════════════════════════════════════════
//  WAVEFORM TRIMMER — admin beat upload preview selector
// ═══════════════════════════════════════════════════════

(function () {
    'use strict';

    // ── Config ──
    var BAR_W = 3, BAR_GAP = 1, HANDLE_HIT = 14, DEFAULT_PREVIEW = 30;

    // ── State ──
    var trimState = {
        buffer: null,
        duration: 0,
        selStart: 0,
        selEnd: 0,
        waveform: [],
        canvas: null,
        ctx: null,
        width: 0,
        height: 100,
        isPlaying: false,
        playSource: null,
        playCtx: null,
        dragType: null,
        dragOffset: 0
    };

    // ── Helpers ──
    function formatDuration(seconds) {
        var m = Math.floor(seconds / 60);
        var s = Math.floor(seconds % 60);
        return m + ':' + (s < 10 ? '0' : '') + s;
    }

    function formatTime(seconds) {
        var m = Math.floor(seconds / 60);
        var s = Math.floor(seconds % 60);
        var ms = Math.floor((seconds % 1) * 10);
        return m + ':' + (s < 10 ? '0' : '') + s + '.' + ms;
    }

    // ── Canvas init (safe — only call after wrapper is visible) ──
    function initCanvas() {
        var wrapper = document.getElementById('trimmerCanvasWrapper');
        var canvas = document.getElementById('trimmerCanvas');
        if (!wrapper || !canvas) return;

        var dpr = window.devicePixelRatio || 1;
        var w = wrapper.clientWidth;

        // If wrapper still has 0 width, skip — rAF will retry
        if (w < 1) return false;

        var h = trimState.height;

        canvas.width = w * dpr;
        canvas.height = h * dpr;
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';

        trimState.canvas = canvas;
        trimState.ctx = canvas.getContext('2d');
        trimState.ctx.scale(dpr, dpr);
        trimState.width = w;
        return true;
    }

    // ── Build waveform peaks ──
    function computeWaveform() {
        if (!trimState.buffer) return;
        var data = trimState.buffer.getChannelData(0);
        var w = trimState.width;
        if (w < 1) return;

        var numBars = Math.floor(w / (BAR_W + BAR_GAP));
        var step = Math.ceil(data.length / numBars);
        var peaks = [];

        for (var i = 0; i < numBars; i++) {
            var peak = 0;
            var start = i * step;
            for (var j = 0; j < step && (start + j) < data.length; j++) {
                var v = Math.abs(data[start + j]);
                if (v > peak) peak = v;
            }
            peaks.push(peak);
        }
        trimState.waveform = peaks;
    }

    // ── Draw everything ──
    function drawTrimmer() {
        var ts = trimState;
        var ctx = ts.ctx;
        var w = ts.width;
        var h = ts.height;
        var peaks = ts.waveform;
        var dur = ts.duration;

        if (!ctx || !peaks.length || w < 1) return;

        ctx.clearRect(0, 0, w, h);

        var maxPeak = 0.01;
        for (var i = 0; i < peaks.length; i++) {
            if (peaks[i] > maxPeak) maxPeak = peaks[i];
        }

        var startPx = (ts.selStart / dur) * w;
        var endPx   = (ts.selEnd / dur) * w;

        // Selection background
        ctx.fillStyle = 'rgba(201, 174, 116, 0.06)';
        ctx.fillRect(startPx, 0, endPx - startPx, h);

        // Bars
        for (var i = 0; i < peaks.length; i++) {
            var x = i * (BAR_W + BAR_GAP);
            var barH = Math.max(2, (peaks[i] / maxPeak) * (h * 0.82));
            var y = (h - barH) / 2;
            var inSel = (x + BAR_W) >= startPx && x <= endPx;

            ctx.fillStyle = inSel
                ? 'rgba(201, 174, 116, 0.85)'
                : 'rgba(201, 174, 116, 0.2)';
            ctx.fillRect(x, y, BAR_W, barH);
        }

        // Dim outside selection
        ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
        ctx.fillRect(0, 0, startPx, h);
        ctx.fillRect(endPx, 0, w - endPx, h);

        // Handles
        drawHandle(ctx, startPx, h);
        drawHandle(ctx, endPx, h);

        // Update labels
        var startLabel = document.getElementById('trimStartTime');
        var endLabel   = document.getElementById('trimEndTime');
        var durLabel   = document.getElementById('trimDuration');
        if (startLabel) startLabel.textContent = formatTime(ts.selStart);
        if (endLabel)   endLabel.textContent   = formatTime(ts.selEnd);
        if (durLabel)   durLabel.textContent   = formatTime(ts.selEnd - ts.selStart);
    }

    function drawHandle(ctx, x, h) {
        var hw = 5;
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(x - hw / 2, 0, hw, h);

        ctx.fillStyle = 'rgba(0,0,0,0.4)';
        for (var i = -1; i <= 1; i++) {
            ctx.beginPath();
            ctx.arc(x, h / 2 + i * 8, 2.5, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    // ── Drag helpers ──
    function getCanvasX(e) {
        if (!trimState.canvas) return 0;
        var rect = trimState.canvas.getBoundingClientRect();
        return Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    }

    function onTrimDown(e) {
        var ts = trimState;
        var x = getCanvasX(e);
        if (!ts.canvas) return;
        var w = ts.canvas.getBoundingClientRect().width;
        var startPx = (ts.selStart / ts.duration) * w;
        var endPx   = (ts.selEnd / ts.duration) * w;

        if (Math.abs(x - startPx) < HANDLE_HIT) {
            ts.dragType = 'start';
        } else if (Math.abs(x - endPx) < HANDLE_HIT) {
            ts.dragType = 'end';
        } else if (x > startPx && x < endPx) {
            ts.dragType = 'selection';
            ts.dragOffset = x - startPx;
        }
    }

    function onTrimMove(e) {
        var ts = trimState;
        if (!ts.dragType || !ts.canvas) return;

        var x = getCanvasX(e);
        var w = ts.canvas.getBoundingClientRect().width;
        var time = (x / w) * ts.duration;

        if (ts.dragType === 'start') {
            ts.selStart = Math.max(0, Math.min(time, ts.selEnd - 0.5));
        } else if (ts.dragType === 'end') {
            ts.selEnd = Math.min(ts.duration, Math.max(time, ts.selStart + 0.5));
        } else if (ts.dragType === 'selection') {
            var selDur = ts.selEnd - ts.selStart;
            var newStart = ((x - ts.dragOffset) / w) * ts.duration;
            newStart = Math.max(0, Math.min(ts.duration - selDur, newStart));
            ts.selStart = newStart;
            ts.selEnd = newStart + selDur;
        }

        updateHiddenFields();
        drawTrimmer();
    }

    function onTrimUp() {
        trimState.dragType = null;
    }

    function updateHiddenFields() {
        var startEl = document.getElementById('previewStart');
        var endEl   = document.getElementById('previewEnd');
        if (startEl) startEl.value = trimState.selStart.toFixed(2);
        if (endEl)   endEl.value   = trimState.selEnd.toFixed(2);
    }

    function initTrimmerEvents() {
        var canvas = document.getElementById('trimmerCanvas');
        if (!canvas) return;

        canvas.addEventListener('mousedown', function (e) { onTrimDown(e); });
        document.addEventListener('mousemove', function (e) { onTrimMove(e); });
        document.addEventListener('mouseup', function () { onTrimUp(); });

        canvas.addEventListener('touchstart', function (e) {
            e.preventDefault();
            onTrimDown(e.touches[0]);
        }, { passive: false });
        document.addEventListener('touchmove', function (e) {
            if (trimState.dragType) {
                e.preventDefault();
                onTrimMove(e.touches[0]);
            }
        }, { passive: false });
        document.addEventListener('touchend', function () { onTrimUp(); });
    }

    // ── Preview playback ──
    function updatePlayBtn() {
        var btn = document.getElementById('trimPlayBtn');
        if (!btn) return;
        if (trimState.isPlaying) {
            btn.innerHTML = '<i class="fas fa-stop"></i> Stop';
        } else {
            btn.innerHTML = '<i class="fas fa-play"></i> Preview Selection';
        }
    }

    window.togglePreview = function () {
        if (trimState.isPlaying) {
            stopPreview();
        } else {
            playPreview();
        }
    };

    function playPreview() {
        var ts = trimState;
        if (!ts.buffer) return;

        var AudioCtx = window.AudioContext || window.webkitAudioContext;
        var ctx = new AudioCtx();
        var source = ctx.createBufferSource();
        source.buffer = ts.buffer;
        source.connect(ctx.destination);

        var dur = ts.selEnd - ts.selStart;
        source.start(0, ts.selStart, dur);

        ts.isPlaying = true;
        ts.playSource = source;
        ts.playCtx = ctx;
        updatePlayBtn();

        source.onended = function () {
            ts.isPlaying = false;
            ts.playSource = null;
            try { ctx.close(); } catch (e) {}
            ts.playCtx = null;
            updatePlayBtn();
        };
    }

    function stopPreview() {
        var ts = trimState;
        if (ts.playSource) {
            try { ts.playSource.stop(); } catch (e) {}
        }
        if (ts.playCtx) {
            try { ts.playCtx.close(); } catch (e) {}
        }
        ts.isPlaying = false;
        ts.playSource = null;
        ts.playCtx = null;
        updatePlayBtn();
    }

    // ═══════════════════════════════════════════════════════
    //  THE FIX — safeInitAndDraw()
    //  Waits until the wrapper is visible AND has width,
    //  then inits canvas, computes waveform, draws.
    // ═══════════════════════════════════════════════════════
    function safeInitAndDraw() {
        // Use double rAF: first frame = layout computed, second frame = painted
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                var ok = initCanvas();
                if (!ok) {
                    // Still 0 width — try one more time with a small timeout
                    setTimeout(function () {
                        initCanvas();
                        computeWaveform();
                        drawTrimmer();
                    }, 50);
                    return;
                }
                computeWaveform();
                drawTrimmer();
            });
        });
    }

    // ═══════════════════════════════════════════════════════
    //  MP3 UPLOAD HANDLER
    // ═══════════════════════════════════════════════════════
    window.handleMp3Upload = function (input) {
        var file = input.files[0];
        if (!file) return;

        // Hide existing preview info
        var existingInfo = document.getElementById('existingPreviewInfo');
        if (existingInfo) existingInfo.style.display = 'none';

        // Show trimmer wrapper (triggers repaint)
        var wrapper = document.getElementById('trimmerWrapper');
        var loading = document.getElementById('trimmerLoading');
        var content = document.getElementById('trimmerContent');

        if (wrapper) wrapper.style.display = '';
        if (loading) loading.style.display = '';
        if (content) content.style.display = 'none';

        // Auto-detect duration from <audio> metadata
        var audioEl = new Audio();
        var objUrl = URL.createObjectURL(file);
        audioEl.addEventListener('loadedmetadata', function () {
            var dur = audioEl.duration;
            var durInput = document.getElementById('duration');
            var durHidden = document.getElementById('durationHidden');
            if (durInput) durInput.value = formatDuration(dur);
            if (durHidden) durHidden.value = formatDuration(dur);
            URL.revokeObjectURL(objUrl);
        });
        audioEl.src = objUrl;

        // Decode audio for waveform
        var reader = new FileReader();
        reader.onload = function (e) {
            var AudioCtx = window.AudioContext || window.webkitAudioContext;
            var actx = new AudioCtx();
            actx.decodeAudioData(e.target.result.slice(0), function (buffer) {
                trimState.buffer = buffer;
                trimState.duration = buffer.duration;
                trimState.selStart = 0;
                trimState.selEnd = Math.min(DEFAULT_PREVIEW, buffer.duration);

                var durInput = document.getElementById('duration');
                var durHidden = document.getElementById('durationHidden');
                if (durInput) durInput.value = formatDuration(buffer.duration);
                if (durHidden) durHidden.value = formatDuration(buffer.duration);

                updateHiddenFields();

                // Hide loading, show content
                if (loading) loading.style.display = 'none';
                if (content) content.style.display = '';

                // THE FIX: wait for repaint before reading clientWidth
                safeInitAndDraw();

                actx.close();
            }, function (err) {
                if (loading) {
                    loading.innerHTML =
                        '<i class="fas fa-exclamation-triangle" style="color:#ef4444;"></i> Could not decode audio file.';
                }
                console.error('Audio decode error:', err);
                actx.close();
            });
        };
        reader.readAsArrayBuffer(file);
    };

    // ═══════════════════════════════════════════════════════
    //  INIT on DOM ready
    // ═══════════════════════════════════════════════════════
    document.addEventListener('DOMContentLoaded', function () {
        initTrimmerEvents();

        // Handle window resize
        var resizeTimer;
        window.addEventListener('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function () {
                if (trimState.buffer && document.getElementById('trimmerCanvasWrapper')) {
                    initCanvas();
                    computeWaveform();
                    drawTrimmer();
                }
            }, 250);
        });
    });

})();