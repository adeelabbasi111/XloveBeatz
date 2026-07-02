// player.js — Beat player: audio, visualizer, tracklist, license modal
'use strict';
(function () {

// ════════════════════════════════════════════════════════════
// DOM REFERENCES
// ════════════════════════════════════════════════════════════
var audio            = document.getElementById('globalAudioPlayer');
var vizCanvas        = document.getElementById('vizCanvas');
var vizCtx           = vizCanvas ? vizCanvas.getContext('2d') : null;
var artworkZone      = document.getElementById('artworkZone');
var playingDots      = document.getElementById('playingDots');
var playerTrackName  = document.getElementById('playerTrackName');
var playerPriceBadge = document.getElementById('playerPriceBadge');
var currentBpm       = document.getElementById('currentBpm');
var currentKey       = document.getElementById('currentKey');
var currentGenre     = document.getElementById('currentGenre');
var totalTimeEl      = document.getElementById('totalTime');
var currentTimeEl    = document.getElementById('currentTime');
var waveformProgress = document.getElementById('waveformProgress');
var mainPlayBtn      = document.getElementById('mainPlayBtn');
var prevBtn          = document.getElementById('prevBtn');
var nextBtn          = document.getElementById('nextBtn');
var addToCartBtn     = document.getElementById('addToCartBtn');
var buyNowBtn        = document.getElementById('buyNowBtn');
var categoryTabs     = document.getElementById('categoryTabs');
var tracklistScroll  = document.getElementById('tracklistScroll');
var trackCount       = document.getElementById('trackCount');
var toastEl          = document.getElementById('toast');

// NEW: Tracklist heading elements
var tracklistTitle   = document.getElementById('tracklistTitle');
var tracklistHeading = document.getElementById('tracklistHeading');

// Volume controls
var volumeSlider  = document.getElementById('volumeSlider');
var volumeIcon    = document.getElementById('volumeIcon');
var volumeWrapper = document.getElementById('volumeWrapper');

// ════════════════════════════════════════════════════════════
// STATE
// ════════════════════════════════════════════════════════════
var allTrackItems    = Array.prototype.slice.call(document.querySelectorAll('.track-item'));
var currentTrackIndex = 0;
var isPlaying         = false;
var audioCtx          = null;
var analyser          = null;
var sourceNode        = null;
var animFrameId       = null;
var freqData          = null;
var activeCategory    = 'all';
var toastTimer        = null;
var cachedDpr         = Math.min(window.devicePixelRatio || 1, 2);
var isDraggingWaveform = false;
var lastVolume        = 0.7;
var isMuted           = false;

// Waveform
var realWaveformData = null;
var WAVEFORM_BARS    = 70;

// Visualizer
var VIZ_HUE          = 232;
var VIZ_SAT          = 68;
var VIZ_LIGHT        = 72;
var NUM_RINGS        = 6;
var POINTS_PER_RING  = 120;
var BASE_RADIUS_STEP = 0.10;
var ringBaseRadii    = [];
var ringDistortions  = new Array(NUM_RINGS).fill(0);
var ringTargets      = new Array(NUM_RINGS).fill(0);
var time             = 0;

// ════════════════════════════════════════════════════════════
// TOAST
// ════════════════════════════════════════════════════════════
function showToast(msg) {
  if (toastTimer) clearTimeout(toastTimer);
  if (!toastEl) return;
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  toastTimer = setTimeout(function () {
    toastEl.classList.remove('show');
  }, 2200);
}

// ════════════════════════════════════════════════════════════
// TRACKLIST HEADING — Update based on active category
// ════════════════════════════════════════════════════════════
function updateTracklistHeading(category) {
  if (!tracklistTitle) return;

  if (category === 'all') {
    tracklistTitle.textContent = 'All Beats';
  } else {
    // Capitalize first letter of category
    var displayName = category.charAt(0).toUpperCase() + category.slice(1);
    tracklistTitle.textContent = displayName + ' Beats';
  }
}

// ════════════════════════════════════════════════════════════
// WAVEFORM — Decode audio and extract peaks
// ════════════════════════════════════════════════════════════
function extractWaveformData(audioBuffer, numBars) {
  var rawData = audioBuffer.getChannelData(0);
  var samplesPerBar = Math.floor(rawData.length / numBars);
  var peaks = [];

  for (var i = 0; i < numBars; i++) {
    var start = i * samplesPerBar;
    var end = Math.min(start + samplesPerBar, rawData.length);
    var peak = 0;
    for (var j = start; j < end; j++) {
      var abs = Math.abs(rawData[j]);
      if (abs > peak) peak = abs;
    }
    peaks.push(peak);
  }

  var maxPeak = 0.01;
  for (var i = 0; i < peaks.length; i++) {
    if (peaks[i] > maxPeak) maxPeak = peaks[i];
  }
  for (var i = 0; i < peaks.length; i++) {
    peaks[i] = peaks[i] / maxPeak;
    peaks[i] = Math.max(0.12, peaks[i]);
  }

  return peaks;
}

function loadRealWaveform(audioUrl) {
  realWaveformData = null;

  if (!audioUrl) {
    buildWaveformUI(null);
    return;
  }

  var xhr = new XMLHttpRequest();
  xhr.open('GET', audioUrl, true);
  xhr.responseType = 'arraybuffer';

  xhr.onload = function () {
    if (xhr.status !== 200) {
      buildWaveformUI(null);
      return;
    }

    var tempCtx = new (window.AudioContext || window.webkitAudioContext)();
    tempCtx.decodeAudioData(xhr.response, function (buffer) {
      realWaveformData = extractWaveformData(buffer, WAVEFORM_BARS);
      buildWaveformUI(realWaveformData);
      updateWaveformProgress(0);
      tempCtx.close();
    }, function () {
      buildWaveformUI(null);
      tempCtx.close();
    });
  };

  xhr.onerror = function () {
    buildWaveformUI(null);
  };

  xhr.send();
}

function buildWaveformUI(peaks) {
  if (!waveformProgress) return;
  waveformProgress.innerHTML = '';

  var reflection = document.querySelector('.waveform-reflection');
  if (reflection) reflection.innerHTML = '';

  if (!peaks || peaks.length === 0) {
    peaks = [];
    for (var i = 0; i < WAVEFORM_BARS; i++) {
      peaks.push(0.15 + Math.random() * 0.6);
    }
  }

  for (var i = 0; i < peaks.length; i++) {
    var height = Math.max(0.1, peaks[i]);

    // Main bar
    var bar = document.createElement('div');
    bar.className = 'wave-bar';
    bar.style.height = (height * 100) + '%';
    waveformProgress.appendChild(bar);

    // Reflection bar
    if (reflection) {
      var refBar = document.createElement('div');
      refBar.className = 'wave-bar-ref';
      refBar.style.height = (height * 100) + '%';
      reflection.appendChild(refBar);
    }
  }
}

function updateWaveformProgress(percent) {
  if (!waveformProgress) return;
  var bars = waveformProgress.children;
  var total = bars.length;
  var activeCount = Math.floor((percent / 100) * total);

  var reflection = document.querySelector('.waveform-reflection');
  var refBars = reflection ? reflection.children : [];

  for (var i = 0; i < total; i++) {
    if (i < activeCount) {
      bars[i].classList.add('played');
      if (refBars[i]) refBars[i].classList.add('played');
    } else {
      bars[i].classList.remove('played');
      if (refBars[i]) refBars[i].classList.remove('played');
    }
  }
}

// ── Waveform seeking ──
function seekFromWaveform(clientX) {
  if (!audio || !audio.duration || isNaN(audio.duration)) return;
  var rect = waveformProgress.getBoundingClientRect();
  var ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
  audio.currentTime = ratio * audio.duration;
  updateWaveformProgress(ratio * 100);
}

if (waveformProgress) {
  waveformProgress.addEventListener('mousedown', function (e) {
    isDraggingWaveform = true;
    seekFromWaveform(e.clientX);
  });

  document.addEventListener('mousemove', function (e) {
    if (isDraggingWaveform) seekFromWaveform(e.clientX);
  });

  document.addEventListener('mouseup', function () {
    isDraggingWaveform = false;
  });

  waveformProgress.addEventListener('touchstart', function (e) {
    e.preventDefault();
    isDraggingWaveform = true;
    seekFromWaveform(e.touches[0].clientX);
  }, { passive: false });

  waveformProgress.addEventListener('touchmove', function (e) {
    e.preventDefault();
    if (isDraggingWaveform) seekFromWaveform(e.touches[0].clientX);
  }, { passive: false });

  waveformProgress.addEventListener('touchend', function () {
    isDraggingWaveform = false;
  });
}

// ════════════════════════════════════════════════════════════
// VOLUME CONTROL (vertical popover)
// ════════════════════════════════════════════════════════════
function setVolume(val) {
  if (!audio) return;
  val = Math.max(0, Math.min(1, val));
  audio.volume = val;
  isMuted = val === 0;
  lastVolume = val > 0 ? val : lastVolume;
  if (volumeSlider) volumeSlider.value = val;
  updateVolumeIcon(val);
}

function updateVolumeIcon(val) {
  if (!volumeIcon) return;
  var icon = volumeIcon.querySelector('i');
  if (!icon) return;
  if (val === 0 || isMuted) {
    icon.className = 'fas fa-volume-xmark';
  } else if (val < 0.4) {
    icon.className = 'fas fa-volume-low';
  } else {
    icon.className = 'fas fa-volume-high';
  }
}

function toggleMute() {
  if (isMuted) {
    setVolume(lastVolume || 0.7);
    isMuted = false;
  } else {
    lastVolume = audio ? audio.volume : 0.7;
    setVolume(0);
    isMuted = true;
  }
}

if (volumeSlider) {
  volumeSlider.addEventListener('input', function () {
    setVolume(parseFloat(this.value));
  });
}

if (volumeIcon) {
  volumeIcon.addEventListener('click', function (e) {
    e.stopPropagation();
    toggleMute();
  });
}

// ════════════════════════════════════════════════════════════
// VISUALIZER — Topographic rings
// ════════════════════════════════════════════════════════════
var NUM_RINGS        = 8;
var POINTS_PER_RING  = 140;
var BASE_RADIUS_STEP = 0.08;
var ringBaseRadii    = [];
var ringDistortions  = new Array(NUM_RINGS).fill(0);
var ringTargets      = new Array(NUM_RINGS).fill(0);
var time             = 0;

function setupCanvas() {
    if (!vizCanvas || !vizCtx) return;
    var stage = document.getElementById('visualizerStage');
    if (!stage) return;
    var rect = stage.getBoundingClientRect();
    var w = rect.width;
    var h = rect.height;
    if (w === 0 || h === 0) return;

    cachedDpr = Math.min(window.devicePixelRatio || 1, 2);
    vizCanvas.width = w * cachedDpr;
    vizCanvas.height = h * cachedDpr;
    vizCanvas.style.width = w + 'px';
    vizCanvas.style.height = h + 'px';
    vizCtx.setTransform(1, 0, 0, 1, 0, 0);
    vizCtx.scale(cachedDpr, cachedDpr);

    ringBaseRadii = [];
    var size = Math.min(w, h);
    for (var i = 0; i < NUM_RINGS; i++) {
        ringBaseRadii.push(size * (0.32 + i * BASE_RADIUS_STEP));
    }
}

function drawIdleTopography() {
    if (!vizCanvas || !vizCtx) return;
    try {
        var w = vizCanvas.width / cachedDpr;
        var h = vizCanvas.height / cachedDpr;
        var cx = w / 2;
        var cy = h / 2;
        if (w < 1 || h < 1 || ringBaseRadii.length === 0) return;
        vizCtx.clearRect(0, 0, w, h);

        for (var idx = 0; idx < ringBaseRadii.length; idx++) {
            var baseR = ringBaseRadii[idx];
            var opacity = 0.08 + idx * 0.02;

            vizCtx.beginPath();
            for (var j = 0; j <= POINTS_PER_RING; j++) {
                var angle = (j / POINTS_PER_RING) * Math.PI * 2;
                var x = cx + Math.cos(angle) * baseR;
                var y = cy + Math.sin(angle) * baseR;
                if (j === 0) vizCtx.moveTo(x, y);
                else vizCtx.lineTo(x, y);
            }
            vizCtx.closePath();
            vizCtx.strokeStyle = 'rgba(124,141,240,' + opacity + ')';
            vizCtx.lineWidth = 1.2;
            vizCtx.stroke();
        }
    } catch (e) {
        console.warn('Visualizer draw error:', e);
    }
}

function drawTopographyFrame() {
    if (!vizCanvas || !vizCtx) return;
    try {
        var w = vizCanvas.width / cachedDpr;
        var h = vizCanvas.height / cachedDpr;
        var cx = w / 2;
        var cy = h / 2;
        if (w < 1 || h < 1 || !isFinite(cx) || !isFinite(cy) || ringBaseRadii.length === 0) return;
        vizCtx.clearRect(0, 0, w, h);

        for (var idx = 0; idx < ringBaseRadii.length; idx++) {
            var baseR = ringBaseRadii[idx];
            var distortion = ringDistortions[idx];
            var opacity = 0.09 + idx * 0.03 + Math.min(distortion * 0.5, 0.4);
            var lineWidth = 1 + distortion * 0.04;

            vizCtx.beginPath();
            for (var j = 0; j <= POINTS_PER_RING; j++) {
                var angle = (j / POINTS_PER_RING) * Math.PI * 2;
                var noise = Math.sin(angle * 5 + idx) * 0.4 + Math.cos(angle * 3 - idx) * 0.3;
                var r = baseR + noise * distortion;
                var x = cx + Math.cos(angle) * r;
                var y = cy + Math.sin(angle) * r;
                if (j === 0) vizCtx.moveTo(x, y);
                else vizCtx.lineTo(x, y);
            }
            vizCtx.closePath();
            vizCtx.strokeStyle = 'rgba(124,141,240,' + Math.min(opacity, 0.8) + ')';
            vizCtx.lineWidth = lineWidth;
            vizCtx.stroke();
        }

        // Center glow
        var innerR = ringBaseRadii[0];
        if (innerR > 5 && isFinite(cx) && isFinite(cy)) {
            var gradR = innerR * 0.5;
            if (isFinite(gradR) && gradR > 0) {
                var grad = vizCtx.createRadialGradient(cx, cy, gradR, cx, cy, innerR);
                grad.addColorStop(0, 'rgba(124,141,240,0.06)');
                grad.addColorStop(1, 'rgba(124,141,240,0)');
                vizCtx.fillStyle = grad;
                vizCtx.beginPath();
                vizCtx.arc(cx, cy, innerR, 0, Math.PI * 2);
                vizCtx.fill();
            }
        }
    } catch (e) {
        console.warn('Visualizer draw error:', e);
    }
}

function updateRingDistortionsFromAudio() {
    if (!freqData || !analyser) return;
    var bins = freqData.length;

    for (var r = 0; r < NUM_RINGS; r++) {
        var startBin = Math.floor((r / NUM_RINGS) * bins);
        var endBin = Math.floor(((r + 1) / NUM_RINGS) * bins);
        var sum = 0;
        var count = 0;

        for (var b = startBin; b < endBin; b++) {
            sum += freqData[b];
            count++;
        }

        var avg = count > 0 ? sum / count / 255 : 0;
        var targetDist = avg * 70;
        ringDistortions[r] += (targetDist - ringDistortions[r]) * 0.55;
    }
}

function decayRingDistortions() {
    var allQuiet = true;
    for (var r = 0; r < NUM_RINGS; r++) {
        ringDistortions[r] *= 0.88;
        if (ringDistortions[r] < 0.3) ringDistortions[r] = 0;
        if (ringDistortions[r] > 0) allQuiet = false;
    }
    return allQuiet;
}

function startVisualizerLoop() {
    if (animFrameId) return;
    function loop() {
        if (isPlaying && analyser) {
            analyser.getByteFrequencyData(freqData);
            updateRingDistortionsFromAudio();
            drawTopographyFrame();
        } else {
            var quiet = decayRingDistortions();
            if (quiet) {
                drawIdleTopography();
                animFrameId = null;
                return;
            }
            drawTopographyFrame();
        }
        animFrameId = requestAnimationFrame(loop);
    }
    animFrameId = requestAnimationFrame(loop);
}

function stopVisualizerLoop() {
    if (animFrameId) {
        cancelAnimationFrame(animFrameId);
        animFrameId = null;
    }
}

// ════════════════════════════════════════════════════════════
// AUDIO CONTEXT
// ════════════════════════════════════════════════════════════
function ensureAudioContext() {
  if (!audioCtx) {
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    audioCtx = new AC();
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.6;
    sourceNode = audioCtx.createMediaElementSource(audio);
    sourceNode.connect(analyser);
    analyser.connect(audioCtx.destination);
    freqData = new Uint8Array(analyser.frequencyBinCount);
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
}

window.addEventListener('beforeunload', function () {
  stopVisualizerLoop();
  if (audio) {
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
  }
  if (audioCtx && audioCtx.state !== 'closed') {
    audioCtx.close().catch(function () {});
  }
});

// ════════════════════════════════════════════════════════════
// PLAYER UI
// ════════════════════════════════════════════════════════════
function updatePlayerUI(trackData) {
  if (playerTrackName) playerTrackName.textContent = trackData.name;
  if (playerPriceBadge) playerPriceBadge.textContent = '₹' + parseInt(trackData.price, 10);
  if (currentBpm) currentBpm.textContent = trackData.bpm + ' BPM';
  if (currentKey) currentKey.textContent = trackData.key;
  if (currentGenre) currentGenre.textContent = trackData.genre;
  if (totalTimeEl) totalTimeEl.textContent = trackData.duration || '0:00';
  if (currentTimeEl) currentTimeEl.textContent = '0:00';
  if (addToCartBtn) addToCartBtn.dataset.id = trackData.id;
  if (buyNowBtn) buyNowBtn.dataset.id = trackData.id;

  currentTrackIndex = parseInt(trackData.index, 10);

  // Reset progress
  updateWaveformProgress(0);

  // Load real waveform
  var previewUrl = trackData.preview || '';
  if (previewUrl) {
    loadRealWaveform(previewUrl);
  } else {
    buildWaveformUI(null);
  }
}

function setPlayingState(playing) {
  isPlaying = playing;
  if (mainPlayBtn) {
    mainPlayBtn.innerHTML = playing
      ? '<i class="fas fa-pause"></i>'
      : '<i class="fas fa-play"></i>';
  }
  if (artworkZone) artworkZone.classList.toggle('playing', playing);
  if (playingDots) playingDots.classList.toggle('active', playing);
}

function showLoadingState(loading) {
  if (mainPlayBtn) {
    mainPlayBtn.innerHTML = loading
      ? '<i class="fas fa-spinner fa-spin"></i>'
      : '<i class="fas fa-play"></i>';
  }
}

function highlightTrackItem(index) {
  for (var i = 0; i < allTrackItems.length; i++) {
    allTrackItems[i].classList.toggle(
      'active',
      parseInt(allTrackItems[i].dataset.index, 10) === index
    );
  }
  var activeItem = allTrackItems.find(function (t) {
    return parseInt(t.dataset.index, 10) === index;
  });
  if (activeItem) {
    activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

// ════════════════════════════════════════════════════════════
// PLAYBACK — FIXED: stops previous track properly
// ════════════════════════════════════════════════════════════
function stopCurrentAudio() {
  if (!audio) return;
  audio.pause();
  audio.currentTime = 0;
  isPlaying = false;
  setPlayingState(false);
  stopVisualizerLoop();
  drawIdleTopography();
  updateWaveformProgress(0);
  if (currentTimeEl) currentTimeEl.textContent = '0:00';
}

function loadAndPlayTrack(index) {
  var trackItem = allTrackItems.find(function (t) {
    return parseInt(t.dataset.index, 10) === index;
  });
  if (!trackItem) return;

  // KEY FIX: Stop previous audio BEFORE loading new one
  stopCurrentAudio();

  updatePlayerUI(trackItem.dataset);
  highlightTrackItem(index);
  showLoadingState(true);

  var previewUrl = trackItem.dataset.preview || '';
  if (!previewUrl) {
    showLoadingState(false);
    showToast('Preview not available');
    return;
  }

  audio.src = previewUrl;
  audio.load();

  // Auto-play the new track
  ensureAudioContext();
  var playPromise = audio.play();
  if (playPromise !== undefined) {
    playPromise.then(function () {
      showLoadingState(false);
      setPlayingState(true);
      startVisualizerLoop();
    }).catch(function (err) {
      console.warn('Auto-play blocked:', err);
      showLoadingState(false);
      showToast('Tap play to start');
    });
  }
}

function togglePlayPause() {
  if (!audio) return;

  // If no track loaded, load first one
  if (!audio.src || audio.src === window.location.href || audio.src === '') {
    if (allTrackItems.length > 0) {
      loadAndPlayTrack(currentTrackIndex);
    }
    return;
  }

  if (isPlaying) {
    audio.pause();
    setPlayingState(false);
    if (!animFrameId) startVisualizerLoop();
  } else {
    ensureAudioContext();
    audio.play().then(function () {
      setPlayingState(true);
      startVisualizerLoop();
    }).catch(function () {
      showToast('Cannot play');
    });
  }
}

// ── Playback controls ──
if (mainPlayBtn) mainPlayBtn.addEventListener('click', togglePlayPause);

if (prevBtn) prevBtn.addEventListener('click', function () {
  var filtered = getFilteredTracks();
  var idx = filtered.findIndex(function (t) {
    return parseInt(t.dataset.index, 10) === currentTrackIndex;
  });
  var prev = (idx - 1 + filtered.length) % filtered.length;
  loadAndPlayTrack(parseInt(filtered[prev].dataset.index, 10));
});

if (nextBtn) nextBtn.addEventListener('click', function () {
  var filtered = getFilteredTracks();
  var idx = filtered.findIndex(function (t) {
    return parseInt(t.dataset.index, 10) === currentTrackIndex;
  });
  var next = (idx + 1) % filtered.length;
  loadAndPlayTrack(parseInt(filtered[next].dataset.index, 10));
});

// ── Audio events (attached ONCE, outside loadAndPlayTrack) ──
if (audio) {
  audio.addEventListener('timeupdate', function () {
    if (!audio.duration || isNaN(audio.duration)) return;
    if (isDraggingWaveform) return;
    var pct = (audio.currentTime / audio.duration) * 100;
    updateWaveformProgress(pct);
    var cm = Math.floor(audio.currentTime / 60);
    var cs = Math.floor(audio.currentTime % 60);
    if (currentTimeEl) currentTimeEl.textContent = cm + ':' + (cs < 10 ? '0' : '') + cs;
  });

  audio.addEventListener('loadedmetadata', function () {
    showLoadingState(false);
    if (audio.duration && !isNaN(audio.duration)) {
      var tm = Math.floor(audio.duration / 60);
      var ts = Math.floor(audio.duration % 60);
      if (totalTimeEl) totalTimeEl.textContent = tm + ':' + (ts < 10 ? '0' : '') + ts;
    }
  });

  audio.addEventListener('ended', function () {
    setPlayingState(false);
    stopVisualizerLoop();
    drawIdleTopography();
    updateWaveformProgress(0);
    if (currentTimeEl) currentTimeEl.textContent = '0:00';
    var filtered = getFilteredTracks();
    var idx = filtered.findIndex(function (t) {
      return parseInt(t.dataset.index, 10) === currentTrackIndex;
    });
    var next = (idx + 1) % filtered.length;
    loadAndPlayTrack(parseInt(filtered[next].dataset.index, 10));
  });

  audio.addEventListener('error', function () {
    setPlayingState(false);
    showLoadingState(false);
    stopVisualizerLoop();
    drawIdleTopography();
    showToast('Audio file not found');
  });
}

// ── Tracklist click ──
if (tracklistScroll) {
  tracklistScroll.addEventListener('click', function (e) {
    var trackItem = e.target.closest('.track-item');
    if (!trackItem) return;
    var index = parseInt(trackItem.dataset.index, 10);

    if (e.target.closest('.play-track-icon')) {
      if (index === currentTrackIndex && isPlaying) {
        audio.pause();
        setPlayingState(false);
        if (!animFrameId) startVisualizerLoop();
      } else if (index === currentTrackIndex && !isPlaying) {
        togglePlayPause();
      } else {
        loadAndPlayTrack(index);
      }
    } else {
      if (index !== currentTrackIndex) {
        loadAndPlayTrack(index);
      } else {
        togglePlayPause();
      }
    }
  });
}

// ════════════════════════════════════════════════════════════
// CATEGORY FILTERS
// ════════════════════════════════════════════════════════════
function getFilteredTracks() {
  if (activeCategory === 'all') return allTrackItems;
  return allTrackItems.filter(function (t) {
    return t.dataset.genre &&
           t.dataset.genre.toLowerCase() === activeCategory.toLowerCase();
  });
}

function applyFilter(category) {
  activeCategory = category;
  allTrackItems.forEach(function (t) {
    var genreMatch = t.dataset.genre &&
                     t.dataset.genre.toLowerCase() === category.toLowerCase();
    t.style.display = (category === 'all' || genreMatch) ? '' : 'none';
  });

  var visible = getFilteredTracks();
  if (trackCount) trackCount.textContent = visible.length + ' tracks';

  document.querySelectorAll('.cat-tab').forEach(function (tab) {
    tab.classList.toggle('active', tab.dataset.category === category);
  });

  // NEW: Update heading based on category
  updateTracklistHeading(category);

  var currentTrackVisible = visible.find(function (t) {
    return parseInt(t.dataset.index, 10) === currentTrackIndex;
  });
  if (currentTrackVisible) {
    highlightTrackItem(currentTrackIndex);
  } else {
    allTrackItems.forEach(function (t) { t.classList.remove('active'); });
  }
}

function buildCategoryTabs() {
  var genres = {};
  allTrackItems.forEach(function (t) {
    if (t.dataset.genre) genres[t.dataset.genre] = true;
  });
  Object.keys(genres).sort().forEach(function (genre) {
    var tab = document.createElement('button');
    tab.className = 'cat-tab';
    tab.dataset.category = genre.toLowerCase();
    tab.textContent = genre;
    tab.addEventListener('click', function () {
      applyFilter(genre.toLowerCase());
    });
    if (categoryTabs) categoryTabs.appendChild(tab);
  });
}

buildCategoryTabs();
var allTab = document.querySelector('.cat-tab[data-category="all"]');
if (allTab) {
  allTab.addEventListener('click', function () { applyFilter('all'); });
}

// ════════════════════════════════════════════════════════════
// LICENSE MODAL + CART
// ════════════════════════════════════════════════════════════
var licenseModal      = document.getElementById('licenseModal');
var closeModalBtn     = document.getElementById('closeModalBtn');
var confirmLicenseBtn = document.getElementById('confirmLicenseBtn');
var confirmBtnText    = document.getElementById('confirmBtnText');
var modalBeatName     = document.getElementById('modalBeatName');

var currentModalBeat    = null;
var currentActionType   = 'cart';
var selectedLicenseType = 'basic';

window.selectLicense = function (licenseType) {
  selectedLicenseType = licenseType;
  document.querySelectorAll('.license-card').forEach(function (card) {
    card.classList.toggle('selected', card.dataset.license === licenseType);
  });
  if (confirmLicenseBtn) confirmLicenseBtn.disabled = false;
};

function openLicenseModal(beatData, action) {
  currentModalBeat = beatData;
  currentActionType = action;
  selectedLicenseType = 'basic';

  if (modalBeatName) modalBeatName.textContent = beatData.name;

  var tiers = ['basic', 'premium', 'exclusive'];
  tiers.forEach(function (tier) {
    var priceEl = document.getElementById('price-' + tier);
    var filesEl = document.getElementById('files-' + tier);
    if (!beatData.license_tiers[tier]) return;

    var tierData = beatData.license_tiers[tier];
    if (priceEl) {
      if (tier === 'exclusive' && (tierData.price === 0 || tierData.price === 'Negotiable')) {
        priceEl.textContent = 'Negotiable';
      } else {
        priceEl.textContent = '₹' + tierData.price;
      }
    }
    if (filesEl) filesEl.textContent = tierData.files;
  });

  document.querySelectorAll('.license-card').forEach(function (card) {
    card.classList.toggle('selected', card.dataset.license === 'basic');
  });

  if (confirmBtnText) {
    confirmBtnText.textContent = action === 'cart' ? 'Add to Cart' : 'Buy Now';
  }
  if (confirmLicenseBtn) confirmLicenseBtn.disabled = false;
  if (licenseModal) licenseModal.classList.add('active');
}

function closeLicenseModal() {
  if (licenseModal) licenseModal.classList.remove('active');
  currentModalBeat = null;
}

if (licenseModal) {
  licenseModal.addEventListener('click', function (e) {
    if (e.target === licenseModal) closeLicenseModal();
  });
}
if (closeModalBtn) closeModalBtn.addEventListener('click', closeLicenseModal);

if (confirmLicenseBtn) {
  confirmLicenseBtn.addEventListener('click', function () {
    if (!currentModalBeat) return;

    if (selectedLicenseType === 'exclusive') {
      var message = 'Hello, I am interested in buying the Exclusive License ' +
                    'for the beat "' + currentModalBeat.name + '". ' +
                    'Please let me know the price and further details.';
      var whatsappUrl = 'https://wa.me/918329189796?text=' + encodeURIComponent(message);
      window.open(whatsappUrl, '_blank');
      showToast('Opening WhatsApp...');
      closeLicenseModal();
      return;
    }

    var tierData = currentModalBeat.license_tiers[selectedLicenseType];
    if (!tierData) return;

    if (typeof window.addToGlobalCart === 'function') {
      window.addToGlobalCart({
        id: currentModalBeat.id,
        name: currentModalBeat.name,
        price: parseFloat(tierData.price),
        type: 'beat',
        license: selectedLicenseType
      }, currentActionType === 'buy');
    } else {
      showToast('Cart system not loaded');
    }
    closeLicenseModal();
  });
}

function triggerPurchaseFlow(beatId, action) {
  var trackItem = document.querySelector('.track-item[data-id="' + beatId + '"]');
  if (!trackItem) return;

  var d = trackItem.dataset;
  var basePrice = parseFloat(d.price) || 0;

  var beatData = {
    id: parseInt(d.id, 10),
    name: d.name,
    license_tiers: {
      basic: {
        price: parseFloat(d.priceBasic) || basePrice,
        files: d.filesBasic || 'MP3 + WAV'
      },
      premium: {
        price: parseFloat(d.pricePremium) || Math.round(basePrice * 1.7),
        files: d.filesPremium || 'MP3 + WAV + Stems'
      },
      exclusive: {
        price: parseFloat(d.priceExclusive) || 0,
        files: d.filesExclusive || 'WAV + Stems + Project File'
      }
    }
  };

  openLicenseModal(beatData, action);
}

if (addToCartBtn) {
  addToCartBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    triggerPurchaseFlow(addToCartBtn.dataset.id, 'cart');
  });
}
if (buyNowBtn) {
  buyNowBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    triggerPurchaseFlow(buyNowBtn.dataset.id, 'buy');
  });
}

// ════════════════════════════════════════════════════════════
// INIT
// ════════════════════════════════════════════════════════════
function init() {
  if (audio) {
    audio.volume = 0.7;
    lastVolume = 0.7;
    if (volumeSlider) volumeSlider.value = 0.7;
    updateVolumeIcon(0.7);
  }

  if (allTrackItems.length > 0) {
    updatePlayerUI(allTrackItems[0].dataset);
    highlightTrackItem(0);
    currentTrackIndex = 0;
  }
  if (trackCount) trackCount.textContent = allTrackItems.length + ' tracks';
  drawIdleTopography();
}

setupCanvas();
init();

var resizeDebounce;
window.addEventListener('resize', function () {
  clearTimeout(resizeDebounce);
  resizeDebounce = setTimeout(function () {
    setupCanvas();
    if (isPlaying && analyser) {
      drawTopographyFrame();
    } else {
      drawIdleTopography();
    }
  }, 200);
});

})();