// player.js — Beat player: audio, visualizer, tracklist, license modal, beat images, download
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
var downloadBtn      = document.getElementById('downloadPreviewBtn');
var categoryTabs     = document.getElementById('categoryTabs');
var tracklistScroll  = document.getElementById('tracklistScroll');
var trackCount       = document.getElementById('trackCount');
var toastEl          = document.getElementById('toast');
var tracklistTitle   = document.getElementById('tracklistTitle');
var tracklistHeading = document.getElementById('tracklistHeading');

// NEW: Image and glow elements
var playerCoverImage = document.getElementById('playerCoverImage');
var playerGlow       = document.getElementById('playerGlow');
var artworkGlowRing  = document.getElementById('artworkGlowRing');

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
var currentBeatColor  = null;

// Waveform
var realWaveformData = null;
var WAVEFORM_BARS    = 70;

// Visualizer
var NUM_RINGS        = 8;
var POINTS_PER_RING  = 140;
var BASE_RADIUS_STEP = 0.08;
var ringBaseRadii    = [];
var ringDistortions  = new Array(NUM_RINGS).fill(0);
var ringTargets      = new Array(NUM_RINGS).fill(0);
var time = 0;
var is808Active = false;
var bassThreshold = 0.6; // Adjust threshold for 808 detection
var bassEnergy = 0;

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
// TRACKLIST HEADING
// ════════════════════════════════════════════════════════════
function updateTracklistHeading(category) {
  if (!tracklistTitle) return;
  if (category === 'all') {
    tracklistTitle.textContent = 'All Beats';
  } else {
    var displayName = category.charAt(0).toUpperCase() + category.slice(1);
    tracklistTitle.textContent = displayName + ' Beats';
  }
}

// ════════════════════════════════════════════════════════════
// COLOR EXTRACTION — Get dominant color from image
// ════════════════════════════════════════════════════════════
function extractDominantColor(imageUrl, callback) {
  var img = new Image();
  img.crossOrigin = 'Anonymous';
  img.onload = function () {
    try {
      var canvas = document.createElement('canvas');
      var size = 40;
      canvas.width = size;
      canvas.height = size;
      var ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, size, size);
      var data = ctx.getImageData(0, 0, size, size).data;
      var r = 0, g = 0, b = 0, count = 0;
      for (var i = 0; i < data.length; i += 16) {
        r += data[i];
        g += data[i + 1];
        b += data[i + 2];
        count++;
      }
      r = Math.round(r / count);
      g = Math.round(g / count);
      b = Math.round(b / count);
      callback(r, g, b);
    } catch (e) {
      callback(124, 141, 240); // fallback blue
    }
  };
  img.onerror = function () {
    callback(124, 141, 240);
  };
  img.src = imageUrl;
}

// ════════════════════════════════════════════════════════════
// BEAT IMAGE — Update artwork zone, glow, and visualizer tint
// ════════════════════════════════════════════════════════════
function updateBeatImage(imagePath) {
  if (!artworkZone) return;

  // Reset playing state briefly to prevent animation glitch
  artworkZone.classList.remove("playing");

  var hasImage = imagePath && imagePath.length > 0;

  if (hasImage && playerCoverImage) {
    var fullUrl = "/static/" + imagePath;
    playerCoverImage.src = fullUrl;
    playerCoverImage.style.display = "block";
    artworkZone.classList.add("has-image");

    // Extract color for glow effects
    extractDominantColor(fullUrl, function (r, g, b) {
      var rgb = r + "," + g + "," + b;
      currentBeatColor = { r: r, g: g, b: b };

      if (playerGlow) {
        playerGlow.style.backgroundColor = "rgba(" + rgb + ", 0.18)";
        playerGlow.style.opacity = "1";
      }

      if (artworkGlowRing) {
        artworkGlowRing.style.backgroundColor = "rgba(" + rgb + ", 0.5)";
      }

      if (vizCtx) {
        window.__beatColor = { r: r, g: g, b: b };
      }
    });
  } else {
    if (playerCoverImage) {
      playerCoverImage.src = "";
      playerCoverImage.style.display = "none";
    }
    artworkZone.classList.remove("has-image");
    currentBeatColor = null;
    window.__beatColor = null;

    if (playerGlow) {
      playerGlow.style.opacity = "0";
    }
    if (artworkGlowRing) {
      artworkGlowRing.style.backgroundColor = "transparent";
    }
  }

  // Restore playing state if audio is playing
  if (isPlaying) {
    setTimeout(function () {
      artworkZone.classList.add("playing");
    }, 50);
  }
}

// ════════════════════════════════════════════════════════════
// WAVEFORM — Using WaveformUI
// ════════════════════════════════════════════════════════════
var waveformUI = null;
if (waveformProgress) {
  waveformUI = new WaveformUI({
    container: waveformProgress,
    reflectionContainer: document.querySelector('.waveform-reflection'),
    numBars: WAVEFORM_BARS,
    onSeek: function(ratio) {
      if (!audio || !audio.duration || isNaN(audio.duration)) return;
      audio.currentTime = ratio * audio.duration;
      waveformUI.updateProgress(ratio * 100);
    }
  });
}

function loadRealWaveform(audioUrl) {
  if (waveformUI) {
    waveformUI.loadRealWaveform(audioUrl);
  }
}

function updateWaveformProgress(percent) {
  if (waveformUI) {
    waveformUI.updateProgress(percent);
  }
}

// ════════════════════════════════════════════════════════════
// VOLUME CONTROL
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
// VISUALIZER — Topographic rings (color-tinted by beat image)
// ════════════════════════════════════════════════════════════
function hslToRgb(h, s, l) {
  var r, g, b;
  if (s === 0) {
    r = g = b = l;
  } else {
    var hue2rgb = function hue2rgb(p, q, t) {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };
    var q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    var p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }
  return { r: Math.round(r * 255), g: Math.round(g * 255), b: Math.round(b * 255) };
}

function rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  var max = Math.max(r, g, b), min = Math.min(r, g, b);
  var h, s, l = (max + min) / 2;
  if (max === min) { h = s = 0; }
  else {
    var d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
      case g: h = ((b - r) / d + 2) / 6; break;
      case b: h = ((r - g) / d + 4) / 6; break;
    }
  }
  return { h: h, s: s, l: l };
}

var _lastBeatColorKey = '';
var _boostedColor = null;

function getBoostedVizColor() {
  var c = window.__beatColor || { r: 124, g: 141, b: 240 };
  var key = c.r + ',' + c.g + ',' + c.b;
  if (key === _lastBeatColorKey && _boostedColor) return _boostedColor;
  _lastBeatColorKey = key;
  var hsl = rgbToHsl(c.r, c.g, c.b);
  hsl.l = Math.max(hsl.l, 0.65); // prevent color from blending into dark background
  hsl.s = Math.max(hsl.s, 0.60); // keep it vibrant
  _boostedColor = hslToRgb(hsl.h, hsl.s, hsl.l);
  return _boostedColor;
}

function getVizColor(opacity) {
  var bc = getBoostedVizColor();
  return 'rgba(' + bc.r + ',' + bc.g + ',' + bc.b + ',' + opacity + ')';
}

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
      vizCtx.strokeStyle = getVizColor(opacity);
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
      var bassExpand = Math.max(0, (bassEnergy - 0.45) * 2.0); // 0.0 when low, scales up smoothly
      var baseR = ringBaseRadii[idx] * (1 + bassExpand * 0.15); // Max 15% bigger, very contained
      var distortion = ringDistortions[idx];
      var opacity = 0.09 + idx * 0.03 + Math.min(distortion * 0.5, 0.4);
      var lineWidth = 1 + distortion * 0.04 + (bassExpand * 1.5);
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
      vizCtx.strokeStyle = getVizColor(Math.min(opacity, 0.8));
      vizCtx.lineWidth = lineWidth;
      vizCtx.stroke();
    }
    var innerR = ringBaseRadii[0];
    if (innerR > 5 && isFinite(cx) && isFinite(cy)) {
      var gradR = innerR * 0.5;
      if (isFinite(gradR) && gradR > 0) {
        var grad = vizCtx.createRadialGradient(cx, cy, gradR, cx, cy, innerR);
        var bc = getBoostedVizColor();
        grad.addColorStop(0, 'rgba(' + bc.r + ',' + bc.g + ',' + bc.b + ',0.06)');
        grad.addColorStop(1, 'rgba(' + bc.r + ',' + bc.g + ',' + bc.b + ',0)');
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
    // After processing all rings, compute bass energy for 808 detection (once per call)
    if (r === NUM_RINGS - 1) {
      var bassBins = Math.max(1, Math.floor(bins * 0.05));
      var bassSum = 0;
      for (var b = 0; b < bassBins; b++) {
        bassSum += freqData[b];
      }
      var currentBassEnergy = bassBins > 0 ? bassSum / bassBins / 255 : 0;
      bassEnergy += (currentBassEnergy - bassEnergy) * 0.25; // smooths the bass reading so it doesn't flutter
      is808Active = bassEnergy > bassThreshold;
    }
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
// PLAYER UI — UPDATED with beat image support
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

  // Update beat image + glow
  updateBeatImage(trackData.beatImage || '');

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
// PLAYBACK
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

  stopCurrentAudio();

  // Pass dataset including beatImage
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

// ── Download Preview ──
if (downloadBtn) {
  downloadBtn.addEventListener('click', function () {
    var trackItem = allTrackItems.find(function (t) {
      return parseInt(t.dataset.index, 10) === currentTrackIndex;
    });
    if (!trackItem) {
      showToast('No track selected');
      return;
    }
    var previewUrl = trackItem.dataset.preview || '';
    if (!previewUrl) {
      showToast('No preview available');
      return;
    }
    var link = document.createElement('a');
    link.href = previewUrl;
    link.download = (trackItem.dataset.name || 'preview') + '_preview.mp3';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Downloading preview...');
  });
}

// ── Audio events ──
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
    if (filesEl) {
      // filesEl is now a <ul class="card-features"> — render as list items
      var fileStr = typeof tierData.files === 'string' ? tierData.files : '';
      if (fileStr) {
        var parts = fileStr.split(/[+,]/);
        filesEl.innerHTML = parts.map(function(f) {
          return '<li><i class="fas fa-check"></i> ' + f.trim() + '</li>';
        }).join('');
      }
    }
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

/* ============================================================
VOLUME POPOVER — hover with delay
============================================================ */
(function () {
  var wrapper = document.getElementById('volumeWrapper');
  if (!wrapper) return;

  var hideTimeout = null;
  var isDragging = false;

  function showPopover() {
    if (hideTimeout) {
      clearTimeout(hideTimeout);
      hideTimeout = null;
    }
    wrapper.classList.add('popover-open');
  }

  function scheduleHide() {
    // Don't hide while slider is being dragged
    if (isDragging) return;
    hideTimeout = setTimeout(function () {
      wrapper.classList.remove('popover-open');
      hideTimeout = null;
    }, 400);
  }

  wrapper.addEventListener('mouseenter', showPopover);
  wrapper.addEventListener('mouseleave', scheduleHide);

  // Track slider dragging so it doesn't close mid-drag
  var slider = document.getElementById('volumeSlider');
  if (slider) {
    slider.addEventListener('mousedown', function () {
      isDragging = true;
    });
    slider.addEventListener('touchstart', function () {
      isDragging = true;
    });

    document.addEventListener('mouseup', function () {
      if (isDragging) {
        isDragging = false;
        // Start hide timer only if cursor is outside the wrapper
        if (!wrapper.matches(':hover')) {
          scheduleHide();
        }
      }
    });
    document.addEventListener('touchend', function () {
      if (isDragging) {
        isDragging = false;
        scheduleHide();
      }
    });
  }
})();