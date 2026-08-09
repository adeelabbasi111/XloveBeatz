document.addEventListener('DOMContentLoaded', function() {
    const audioBefore = document.getElementById('baAudioBefore');
    const audioAfter = document.getElementById('baAudioAfter');
    
    if (!audioBefore || !audioAfter) return;

    const playBtn = document.getElementById('baPlayBtn');
    const toggleBtn = document.getElementById('baToggleBtn');
    const waveformContainer = document.getElementById('baWaveformContainer');
    const waveformVisual = document.getElementById('baWaveformVisual');
    const stateLabel = document.getElementById('baWaveformText');
    const timeCurrent = document.getElementById('baTimeCurrent');
    const timeTotal = document.getElementById('baTimeTotal');

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
        
        // Note: Waveform is now loaded dynamically via the Blob URL below
        // to bypass server range request issues.
    }

    // Set initial volumes
    audioBefore.volume = 1;
    audioAfter.volume = 0;

    // ─── Loading State & Server Range Fix ───
    // Live servers sometimes don't support HTTP Range requests for static files,
    // which breaks audio seeking (currentTime). To fix this bulletproofly, we fetch
    // the audio into local memory (Blob) so seeking works instantly regardless of server config.
    
    let loadedCount = 0;
    bothLoaded = false;
    playBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    function checkLoaded() {
        loadedCount++;
        if (loadedCount >= 2) {
            bothLoaded = true;
            playBtn.innerHTML = '<i class="fas fa-play"></i>';
            if (timeTotal) timeTotal.textContent = formatTime(audioBefore.duration);
        }
    }

    // Fallback if fetch fails
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
            
            // Replace src with local memory blob URL
            audioElement.src = blobUrl;
            audioElement.load();
            return blobUrl;
        } catch (error) {
            console.warn("Failed to load audio as blob, falling back to original src:", error);
            return null;
        }
    }

    // Start loading both tracks into memory
    Promise.all([
        loadAudioAsBlob(audioBefore),
        loadAudioAsBlob(audioAfter)
    ]).then(([beforeBlobUrl, afterBlobUrl]) => {
        // If we successfully got a blob URL, feed that into the waveform generator too!
        // (WebAudio API decodeAudioData is much faster with a blob URL anyway)
        if (beforeBlobUrl && waveformUI) {
            waveformUI.loadRealWaveform(beforeBlobUrl);
        }
    });

    // ─── Play / Pause ───
    playBtn.addEventListener('click', () => {
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

    // ─── Toggle Before / After ───
    toggleBtn.addEventListener('click', () => {
        isAfter = !isAfter;
        
        if (isAfter) {
            audioBefore.volume = 0;
            audioAfter.volume = 1;
            
            waveformContainer.classList.add('is-after');
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
            
            waveformContainer.classList.remove('is-after');
            if (stateLabel) stateLabel.textContent = 'BEFORE';
            toggleBtn.innerHTML = '<i class="fas fa-arrow-right-arrow-left"></i><span>After</span>';
            toggleBtn.classList.remove('is-active');

            if (isPlaying) {
                const t = audioAfter.currentTime;
                if (Math.abs(audioBefore.currentTime - t) > 0.1) audioBefore.currentTime = t;
            }
        }
    });

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
    audioBefore.addEventListener('ended', resetPlayer);
    audioAfter.addEventListener('ended', resetPlayer);

    function resetPlayer() {
        isPlaying = false;
        playBtn.innerHTML = '<i class="fas fa-play"></i>';
        audioBefore.currentTime = 0;
        audioAfter.currentTime = 0;
        if (waveformUI) waveformUI.updateProgress(0);
        if (timeCurrent) timeCurrent.textContent = '0:00';
    }
});
