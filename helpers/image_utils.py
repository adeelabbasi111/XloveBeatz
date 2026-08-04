"""Image upload + compression for beat cover art."""
import os
from PIL import Image

BEAT_IMAGE_DIR = os.path.join('static', 'data', 'beat_images')
MAX_WIDTH = 600
MAX_HEIGHT = 600
QUALITY = 72


def save_compressed_beat_image(file_storage, beat_id):
    """
    Accept a Werkzeug FileStorage, compress it, save to disk.
    Returns the relative path (from static/) or None.
    """
    if not file_storage or not file_storage.filename:
        return None

    ext = file_storage.filename.rsplit('.', 1)[-1].lower()
    if ext not in ('jpg', 'jpeg', 'png', 'webp'):
        return None

    os.makedirs(BEAT_IMAGE_DIR, exist_ok=True)
    filename = f"beat_{beat_id}.{ext}"
    filepath = os.path.join(BEAT_IMAGE_DIR, filename)

    img = Image.open(file_storage.stream)

    # Convert palette / RGBA to RGB for JPEG
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    # Resize if larger than max dimensions (preserves aspect ratio)
    if img.width > MAX_WIDTH or img.height > MAX_HEIGHT:
        img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)

    # Save with compression
    save_kwargs = {'optimize': True}
    if ext in ('jpg', 'jpeg'):
        save_kwargs['quality'] = QUALITY
    elif ext == 'webp':
        save_kwargs['quality'] = QUALITY
    elif ext == 'png':
        save_kwargs['optimize'] = True

    img.save(filepath, **save_kwargs)

    return f"data/beat_images/{filename}"