"""WAV → compressed MP3 preview generator."""
import os
from pydub import AudioSegment

# Dynamically find the app root to locate the local FFmpeg binaries
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ffmpeg_path = os.path.join(BASE_DIR, "ffmpeg")
ffprobe_path = os.path.join(BASE_DIR, "ffprobe")

# Add the app directory to PATH so pydub can always find ffmpeg/ffprobe
import os
if BASE_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] += os.pathsep + BASE_DIR

if os.path.exists(ffmpeg_path):
    AudioSegment.converter = ffmpeg_path
if os.path.exists(ffprobe_path):
    import pydub.utils
    pydub.utils.get_prober_name = lambda: ffprobe_path

PREVIEW_DIR = os.path.join('static', 'data', 'previews')
PREVIEW_BITRATE = '128k'
PREVIEW_MAX_SECONDS = 90
FADE_OUT_MS = 3000


def convert_wav_to_preview(wav_path, beat_id):
    """
    Read a WAV file, trim/fade, export as MP3.
    Returns the relative path (from static/) for preview_audio, or None.
    """
    if not wav_path or not os.path.exists(wav_path):
        return None

    try:
        audio = AudioSegment.from_wav(wav_path)

        # Trim to preview length
        max_ms = PREVIEW_MAX_SECONDS * 1000
        if len(audio) > max_ms:
            audio = audio[:max_ms]

        # Fade out at the end
        fade = min(FADE_OUT_MS, len(audio))
        audio = audio.fade_out(fade)

        os.makedirs(PREVIEW_DIR, exist_ok=True)
        mp3_filename = f"preview_{beat_id}.mp3"
        mp3_path = os.path.join(PREVIEW_DIR, mp3_filename)

        audio.export(mp3_path, format='mp3', bitrate=PREVIEW_BITRATE)

        # Return path relative to static/
        return f"data/previews/{mp3_filename}"

    except Exception as e:
        print(f"[audio_utils] WAV→MP3 conversion failed for beat {beat_id}: {e}")
        return None