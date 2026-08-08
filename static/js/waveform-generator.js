/**
 * WaveformUI - A reusable utility for decoding audio and rendering interactive real waveforms.
 */

class WaveformUI {
    constructor(options) {
        this.container = options.container;
        this.reflectionContainer = options.reflectionContainer || null;
        this.numBars = options.numBars || 100;
        this.onSeek = options.onSeek || null;
        this.peaks = [];
        this.isDragging = false;

        this._setupEvents();
    }

    _setupEvents() {
        if (!this.container) return;

        const seekHandler = (clientX) => {
            if (!this.onSeek) return;
            const rect = this.container.getBoundingClientRect();
            const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
            this.onSeek(ratio);
        };

        this.container.addEventListener('mousedown', (e) => {
            this.isDragging = true;
            seekHandler(e.clientX);
        });

        document.addEventListener('mousemove', (e) => {
            if (this.isDragging) seekHandler(e.clientX);
        });

        document.addEventListener('mouseup', () => {
            this.isDragging = false;
        });

        this.container.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.isDragging = true;
            seekHandler(e.touches[0].clientX);
        }, { passive: false });

        this.container.addEventListener('touchmove', (e) => {
            e.preventDefault();
            if (this.isDragging) seekHandler(e.touches[0].clientX);
        }, { passive: false });

        this.container.addEventListener('touchend', () => {
            this.isDragging = false;
        });
    }

    _extractPeaks(audioBuffer) {
        const rawData = audioBuffer.getChannelData(0);
        const samplesPerBar = Math.floor(rawData.length / this.numBars);
        const peaks = [];
        
        for (let i = 0; i < this.numBars; i++) {
            const start = i * samplesPerBar;
            const end = Math.min(start + samplesPerBar, rawData.length);
            let peak = 0;
            for (let j = start; j < end; j++) {
                const abs = Math.abs(rawData[j]);
                if (abs > peak) peak = abs;
            }
            peaks.push(peak);
        }

        let maxPeak = 0.01;
        for (let i = 0; i < peaks.length; i++) {
            if (peaks[i] > maxPeak) maxPeak = peaks[i];
        }

        for (let i = 0; i < peaks.length; i++) {
            // Normalize to 0-1
            let normalized = peaks[i] / maxPeak;
            
            // Exaggerate differences by applying a power curve.
            // This pulls lower values down while keeping high values high,
            // resulting in a much more dynamic and spiky waveform.
            normalized = Math.pow(normalized, 1.8);
            
            // Add a small minimum height
            peaks[i] = Math.max(0.05, normalized);
        }
        
        return peaks;
    }

    buildFakeWaveform() {
        this.peaks = [];
        for (let i = 0; i < this.numBars; i++) {
            this.peaks.push(0.15 + Math.random() * 0.6);
        }
        this.render();
    }

    loadRealWaveform(audioUrl) {
        if (!audioUrl) return;

        // Initialize static cache if it doesn't exist
        if (!WaveformUI.cache) {
            WaveformUI.cache = new Map();
        }

        // If we already decoded this audio, render it instantly!
        if (WaveformUI.cache.has(audioUrl)) {
            this.peaks = WaveformUI.cache.get(audioUrl);
            this.render();
            this.updateProgress(0);
            return;
        }

        // Immediately show a fake waveform so the user doesn't see the previous track's waveform
        // while the new audio is being downloaded and decoded (which takes 1-2 seconds).
        this.buildFakeWaveform();

        const xhr = new XMLHttpRequest();
        xhr.open('GET', audioUrl, true);
        xhr.responseType = 'arraybuffer';
        
        xhr.onload = () => {
            if (xhr.status !== 200) {
                this.buildFakeWaveform();
                return;
            }
            const tempCtx = new (window.AudioContext || window.webkitAudioContext)();
            tempCtx.decodeAudioData(xhr.response, (buffer) => {
                this.peaks = this._extractPeaks(buffer);
                
                // Cache the peaks for instant loading next time
                WaveformUI.cache.set(audioUrl, this.peaks);
                
                this.render();
                this.updateProgress(0);
                tempCtx.close();
            }, () => {
                this.buildFakeWaveform();
                tempCtx.close();
            });
        };
        
        xhr.onerror = () => {
            this.buildFakeWaveform();
        };
        
        xhr.send();
    }

    render() {
        if (!this.container) return;
        this.container.innerHTML = '';
        if (this.reflectionContainer) this.reflectionContainer.innerHTML = '';

        const generateSvg = (peaks, baseClass, isReflection = false) => {
            const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.setAttribute('viewBox', '0 0 1000 100');
            svg.setAttribute('preserveAspectRatio', 'none');
            svg.style.width = '100%';
            svg.style.height = '100%';
            svg.style.display = 'block';

            let d = ``;
            const spacing = 1000 / Math.max(1, peaks.length - 1);
            const strokeWidth = Math.max(2, spacing * 0.65); // 65% of the space is bar, 35% is gap

            for (let i = 0; i < peaks.length; i++) {
                const x = (i * 1000) / (Math.max(1, peaks.length - 1));
                let h = peaks[i] * 50;
                if (h < 2) h = 2; // min height so silence is still a visible line
                
                // For a reflection, we might just draw the top half, but symmetrical looks best.
                // Draw a vertical line for each peak
                d += `M ${x.toFixed(1)} ${(50 - h).toFixed(1)} L ${x.toFixed(1)} ${(50 + h).toFixed(1)} `;
            }

            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute('d', d);
            path.setAttribute('class', baseClass);
            
            // Style as thick rounded strokes
            path.style.stroke = 'currentColor';
            path.style.strokeWidth = strokeWidth.toFixed(1);
            path.style.strokeLinecap = 'round';
            path.style.fill = 'none';

            svg.appendChild(path);
            return svg;
        };

        // Create base layers
        const baseLayer = document.createElement('div');
        baseLayer.className = 'wave-layer-base';
        baseLayer.style.position = 'absolute';
        baseLayer.style.top = '0';
        baseLayer.style.left = '0';
        baseLayer.style.width = '100%';
        baseLayer.style.height = '100%';
        baseLayer.appendChild(generateSvg(this.peaks, 'wave-path-base'));

        // Create progress layer (clipped by width)
        const progressLayer = document.createElement('div');
        progressLayer.className = 'wave-layer-progress';
        progressLayer.style.position = 'absolute';
        progressLayer.style.top = '0';
        progressLayer.style.left = '0';
        progressLayer.style.width = '0%'; // initial progress
        progressLayer.style.height = '100%';
        progressLayer.style.overflow = 'hidden';
        
        // Inner SVG container needs to stay fixed relative to parent to stretch properly
        const progressInner = document.createElement('div');
        progressInner.style.width = this.container.offsetWidth + 'px';
        progressInner.style.height = '100%';
        
        // Update inner width on resize
        const resizeObserver = new ResizeObserver(entries => {
            for (let entry of entries) {
                progressInner.style.width = entry.contentRect.width + 'px';
                if (this.reflectionContainer) {
                    const refInner = this.reflectionContainer.querySelector('.wave-layer-progress > div');
                    if (refInner) refInner.style.width = entry.contentRect.width + 'px';
                }
            }
        });
        resizeObserver.observe(this.container);

        progressInner.appendChild(generateSvg(this.peaks, 'wave-path-progress'));
        progressLayer.appendChild(progressInner);

        this.container.appendChild(baseLayer);
        this.container.appendChild(progressLayer);
        
        // Save reference for updateProgress
        this.progressLayer = progressLayer;

        if (this.reflectionContainer) {
            const refBaseLayer = document.createElement('div');
            refBaseLayer.className = 'wave-layer-base';
            refBaseLayer.style.position = 'absolute';
            refBaseLayer.style.top = '0';
            refBaseLayer.style.left = '0';
            refBaseLayer.style.width = '100%';
            refBaseLayer.style.height = '100%';
            refBaseLayer.appendChild(generateSvg(this.peaks, 'wave-path-base', true));

            const refProgressLayer = document.createElement('div');
            refProgressLayer.className = 'wave-layer-progress';
            refProgressLayer.style.position = 'absolute';
            refProgressLayer.style.top = '0';
            refProgressLayer.style.left = '0';
            refProgressLayer.style.width = '0%';
            refProgressLayer.style.height = '100%';
            refProgressLayer.style.overflow = 'hidden';

            const refProgressInner = document.createElement('div');
            refProgressInner.style.width = this.reflectionContainer.offsetWidth + 'px';
            refProgressInner.style.height = '100%';
            refProgressInner.appendChild(generateSvg(this.peaks, 'wave-path-progress', true));
            refProgressLayer.appendChild(refProgressInner);

            this.reflectionContainer.appendChild(refBaseLayer);
            this.reflectionContainer.appendChild(refProgressLayer);
            
            this.refProgressLayer = refProgressLayer;
        }
    }

    updateProgress(percent) {
        if (this.progressLayer) {
            this.progressLayer.style.width = percent + '%';
        }
        if (this.refProgressLayer) {
            this.refProgressLayer.style.width = percent + '%';
        }
    }
}

window.WaveformUI = WaveformUI;
