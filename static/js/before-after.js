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
        
        // Load real waveform from the before audio source
        const beforeSrc = audioBefore.querySelector('source').src;
        waveformUI.loadRealWaveform(beforeSrc);
    }

    // Set initial volumes
    audioBefore.volume = 1;
    audioAfter.volume = 0;

    // ─── Loading State ───
    let loadedCount = 0;
    function checkLoaded() {
        loadedCount++;
        if (loadedCount >= 2) {
            bothLoaded = true;
            playBtn.innerHTML = '<i class="fas fa-play"></i>';
            // Set total duration from the before track
            if (timeTotal) timeTotal.textContent = formatTime(audioBefore.duration);
        }
    }

    playBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    audioBefore.addEventListener('canplaythrough', checkLoaded);
    audioAfter.addEventListener('canplaythrough', checkLoaded);

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
