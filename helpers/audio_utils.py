"""WAV → compressed MP3 preview generator."""
import os
# Dynamically find the app root to locate the local FFmpeg binaries
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ffmpeg_path = os.path.join(BASE_DIR, "ffmpeg")
ffprobe_path = os.path.join(BASE_DIR, "ffprobe")

# Add the app directory to PATH so pydub can always find ffmpeg/ffprobe
import os
if BASE_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] += os.pathsep + BASE_DIR



PREVIEW_DIR = os.path.join('static', 'data', 'previews')
PREVIEW_BITRATE = '128k'
PREVIEW_MAX_SECONDS = 90
FADE_OUT_MS = 3000


import subprocess
import json

def convert_wav_to_preview(wav_path, beat_id):
    """
    Read a WAV file, trim/fade, export as MP3 using raw FFmpeg to save RAM.
    Returns the relative path (from static/) for preview_audio, or an ERROR string.
    """
    if not wav_path or not os.path.exists(wav_path):
        return None

    try:
        os.makedirs(PREVIEW_DIR, exist_ok=True)
        mp3_filename = f"preview_{beat_id}.mp3"
        mp3_path = os.path.join(PREVIEW_DIR, mp3_filename)

        # 1. Get duration using ffprobe
        probe_cmd = [
            ffprobe_path, '-v', 'quiet', '-print_format', 'json', 
            '-show_format', '-show_streams', wav_path
        ]
        probe_res = subprocess.run(probe_cmd, capture_output=True, text=True)
        
        duration = 0
        if probe_res.returncode == 0:
            try:
                info = json.loads(probe_res.stdout)
                duration = float(info.get('format', {}).get('duration', 0))
            except:
                pass
                
        # If ffprobe fails, assume a long duration and let ffmpeg trim it.
        # But for fade out, we need to know the duration. If duration is 0, we can't fade out nicely.
        # But we'll try our best.
        
        trim_duration = min(duration, PREVIEW_MAX_SECONDS) if duration > 0 else PREVIEW_MAX_SECONDS
        
        # 2. Run ffmpeg
        # Command: ffmpeg -y -i input.wav -t 90 -af "afade=t=out:st=87:d=3" -b:a 128k output.mp3
        ffmpeg_cmd = [
            ffmpeg_path, '-y',
            '-i', wav_path,
            '-t', str(trim_duration),
            '-b:a', PREVIEW_BITRATE
        ]
        
        if duration > 0:
            fade_start = max(0, trim_duration - (FADE_OUT_MS / 1000.0))
            ffmpeg_cmd.extend(['-af', f'afade=t=out:st={fade_start}:d={FADE_OUT_MS / 1000.0}'])
            
        ffmpeg_cmd.append(mp3_path)
        
        conv_res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if conv_res.returncode != 0:
            return f"ERROR: ffmpeg failed with code {conv_res.returncode}. {conv_res.stderr[-200:]}"
            
        if not os.path.exists(mp3_path):
            return f"ERROR: Output MP3 file was not created by ffmpeg."

        # Return path relative to static/
        return f"data/previews/{mp3_filename}"

    except Exception as e:
        import traceback
        return f"ERROR (Python): {traceback.format_exc()[-200:]}"
