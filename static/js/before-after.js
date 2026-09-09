document.addEventListener('DOMContentLoaded', function() {
    const containers = document.querySelectorAll('.ba-player-container');
    
    containers.forEach(container => {
        const audioBefore = container.querySelector('.baAudioBefore');
        const audioAfter = container.querySelector('.baAudioAfter');
        
        if (!audioBefore || !audioAfter) return;

        const playBtn = container.querySelector('.baPlayBtn');
        const toggleBtn = container.querySelector('.baToggleBtn');
        const waveformContainer = container.querySelector('.baWaveformContainer');
        const waveformVisual = container.querySelector('.baWaveformVisual');
        const stateLabel = container.querySelector('.baWaveformText');
        const timeCurrent = container.querySelector('.baTimeCurrent');
        const timeTotal = container.querySelector('.baTimeTotal');

        let isPlaying = false;
        let isAfter = false;
        let bothLoaded = false;

        // ─── Helper: format seconds → m:ss ───
        function formatTime(sec) {
            if (!sec || isNaN(sec)) return '0:00';
            const m = Math.floor(sec / 60);
            const s = Math.floor(sec % 60);
            return m + ':' + (s < 10 ? '0' : '') + s;
        }

        // ─── Initialize WaveformUI ───
        let waveformUI = null;
        if (waveformVisual && typeof WaveformUI !== 'undefined') {
            waveformUI = new WaveformUI({
                container: waveformVisual,
                numBars: 150,
                onSeek: function(ratio) {
                    if (!bothLoaded) return;
                    const duration = audioBefore.duration || 0;
                    if (!duration) return;
                    
                    const targetTime = ratio * duration;
                    audioBefore.currentTime = targetTime;
                    audioAfter.currentTime = targetTime;
                    
                    if (waveformUI) waveformUI.updateProgress(ratio * 100);
                    if (timeCurrent) timeCurrent.textContent = formatTime(targetTime);
                }
            });
        }

        // Set initial volumes
        audioBefore.volume = 1;
        audioAfter.volume = 0;

        // ─── Loading State & Server Range Fix ───
        let loadedCount = 0;
        bothLoaded = false;
        if (playBtn) playBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        function checkLoaded() {
            loadedCount++;
            if (loadedCount >= 2) {
                bothLoaded = true;
                if (playBtn) playBtn.innerHTML = '<i class="fas fa-play"></i>';
                if (timeTotal) timeTotal.textContent = formatTime(audioBefore.duration);
            }
        }

        audioBefore.addEventListener('canplaythrough', checkLoaded);
        audioAfter.addEventListener('canplaythrough', checkLoaded);

        async function loadAudioAsBlob(audioElement) {
            try {
                const sourceEl = audioElement.querySelector('source');
                if (!sourceEl) return null;
                
                const originalSrc = sourceEl.src;
                const response = await fetch(originalSrc);
                if (!response.ok) throw new Error("Network response was not ok");
                
                const blob = await response.blob();
                const blobUrl = URL.createObjectURL(blob);
                
                audioElement.src = blobUrl;
                audioElement.load();
                return blobUrl;
            } catch (error) {
                console.warn("Failed to load audio as blob, falling back to original src:", error);
                return null;
            }
        }

        Promise.all([
            loadAudioAsBlob(audioBefore),
            loadAudioAsBlob(audioAfter)
        ]).then(([beforeBlobUrl, afterBlobUrl]) => {
            if (beforeBlobUrl && waveformUI) {
                waveformUI.loadRealWaveform(beforeBlobUrl);
            }
        });

        // ─── Play / Pause ───
        if (playBtn) {
            playBtn.addEventListener('click', () => {
                // Pause all other players
                containers.forEach(other => {
                    if (other !== container) {
                        const otherBefore = other.querySelector('.baAudioBefore');
                        const otherAfter = other.querySelector('.baAudioAfter');
                        const otherPlayBtn = other.querySelector('.baPlayBtn');
                        if (otherBefore && !otherBefore.paused) {
                            otherBefore.pause();
                            if (otherAfter) otherAfter.pause();
                            if (otherPlayBtn) otherPlayBtn.innerHTML = '<i class="fas fa-play"></i>';
                            // We don't reset their 'isPlaying' variable directly since it's scoped, but their UI resets.
                            // Actually wait, their isPlaying variable won't sync. It's fine for simple use cases.
                            // Let's just dispatch a custom event to pause others properly.
                            other.dispatchEvent(new Event('stopAudio'));
                        }
                    }
                });

                if (!bothLoaded) return;

                if (isPlaying) {
                    audioBefore.pause();
                    audioAfter.pause();
                    playBtn.innerHTML = '<i class="fas fa-play"></i>';
                    isPlaying = false;
                } else {
                    if (isAfter) {
                        audioBefore.currentTime = audioAfter.currentTime;
                    } else {
                        audioAfter.currentTime = audioBefore.currentTime;
                    }
                    
                    audioBefore.play();
                    audioAfter.play();
                    playBtn.innerHTML = '<i class="fas fa-pause"></i>';
                    isPlaying = true;
                }
            });
        }
        
        container.addEventListener('stopAudio', () => {
            if (isPlaying) {
                audioBefore.pause();
                audioAfter.pause();
                if (playBtn) playBtn.innerHTML = '<i class="fas fa-play"></i>';
                isPlaying = false;
            }
        });

        // ─── Toggle Before / After ───
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                isAfter = !isAfter;
                
                if (isAfter) {
                    audioBefore.volume = 0;
                    audioAfter.volume = 1;
                    
                    if (waveformContainer) waveformContainer.classList.add('is-after');
                    if (stateLabel) stateLabel.textContent = 'AFTER';
                    toggleBtn.innerHTML = '<i class="fas fa-arrow-right-arrow-left"></i><span>Before</span>';
                    toggleBtn.classList.add('is-active');
                    
                    if (isPlaying) {
                        const t = audioBefore.currentTime;
                        if (Math.abs(audioAfter.currentTime - t) > 0.1) audioAfter.currentTime = t;
                    }
                } else {
                    audioBefore.volume = 1;
                    audioAfter.volume = 0;
                    
                    if (waveformContainer) waveformContainer.classList.remove('is-after');
                    if (stateLabel) stateLabel.textContent = 'BEFORE';
                    toggleBtn.innerHTML = '<i class="fas fa-arrow-right-arrow-left"></i><span>After</span>';
                    toggleBtn.classList.remove('is-active');

                    if (isPlaying) {
                        const t = audioAfter.currentTime;
                        if (Math.abs(audioBefore.currentTime - t) > 0.1) audioBefore.currentTime = t;
                    }
                }
            });
        }

        // ─── Progress + Time Updates ───
        function updateProgress(audio) {
            if (audio.duration) {
                const percent = (audio.currentTime / audio.duration) * 100;
                if (waveformUI) waveformUI.updateProgress(percent);
                if (timeCurrent) timeCurrent.textContent = formatTime(audio.currentTime);
            }
        }

        audioBefore.addEventListener('timeupdate', () => {
            if (!isAfter) updateProgress(audioBefore);
        });

        audioAfter.addEventListener('timeupdate', () => {
            if (isAfter) updateProgress(audioAfter);
        });

        // ─── End of Track ───
        function resetPlayer() {
            isPlaying = false;
            if (playBtn) playBtn.innerHTML = '<i class="fas fa-play"></i>';
            audioBefore.currentTime = 0;
            audioAfter.currentTime = 0;
            if (waveformUI) waveformUI.updateProgress(0);
            if (timeCurrent) timeCurrent.textContent = '0:00';
        }

        audioBefore.addEventListener('ended', resetPlayer);
        audioAfter.addEventListener('ended', resetPlayer);
    });
});
