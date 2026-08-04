import logging
import os
import subprocess
import zipfile
import shutil
import time
import glob
import uuid
import io
import json

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app, send_file, jsonify, session
)
from werkzeug.utils import secure_filename
from PIL import Image

from helpers.models import (
    db, Product, BeatDetail, BeatPack, VocalPreset,
    License, BeatLicensePrice, Order, OrderItem, User,
    Download, DiscountCode, ActivityLog, GeneratedLicense, Offer,
)
from helpers.utils import (
    admin_required, get_current_user,
    generate_unique_slug, allowed_file, save_upload, login_required
)
from helpers.services import (
    log_activity, get_site_setting, set_site_setting,
    get_admin_stats, get_monthly_revenue, get_top_products,
    get_genre_distribution,
)
from datetime import datetime
# ═══════════════════════════════════════════════════════════════
#  FILE STORAGE HELPERS
# ═══════════════════════════════════════════════════════════════

FOLDER_PREVIEWS    = 'previews'
FOLDER_WAV         = 'wav'
FOLDER_FLP         = 'flps'
FOLDER_IMAGES      = 'images'
FOLDER_BEAT_IMAGES = 'beat_images'
FOLDER_PRESETS     = 'presets'
FOLDER_PACKS       = 'packs'
FOLDER_LICENSES    = 'licenses'

ALL_DATA_FOLDERS = [
    FOLDER_PREVIEWS, FOLDER_WAV,
    FOLDER_FLP, FOLDER_IMAGES, FOLDER_BEAT_IMAGES,
    FOLDER_PRESETS, FOLDER_PACKS, FOLDER_LICENSES
]

TEMP_UPLOAD_DIR = os.path.join('static', 'data', 'temp_uploads')

# Image compression settings
IMG_MAX_WIDTH  = 600
IMG_MAX_HEIGHT = 600
IMG_QUALITY    = 72

logger = logging.getLogger(__name__)
bp = Blueprint('admin', __name__)


# ═══════════════════════════════════════════════════════════════
#  IMAGE COMPRESSION
# ═══════════════════════════════════════════════════════════════

def compress_image_at_path(abs_path, max_w=IMG_MAX_WIDTH, max_h=IMG_MAX_HEIGHT, quality=IMG_QUALITY):
    """Compress an image file in-place. Returns True on success."""
    try:
        img = Image.open(abs_path)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        if img.width > max_w or img.height > max_h:
            img.thumbnail((max_w, max_h), Image.LANCZOS)

        ext = os.path.splitext(abs_path)[1].lower()
        save_kwargs = {'optimize': True}
        if ext in ('.jpg', '.jpeg', '.webp'):
            save_kwargs['quality'] = quality

        img.save(abs_path, **save_kwargs)
        return True
    except Exception as e:
        logger.error("Image compression failed for %s: %s", abs_path, e)
        return False


def compress_and_save_image(file_storage, dest_abs_path, max_w=IMG_MAX_WIDTH, max_h=IMG_MAX_HEIGHT, quality=IMG_QUALITY):
    """
    Save a Werkzeug FileStorage to dest_abs_path with compression.
    Returns True on success, False on failure.
    """
    try:
        img = Image.open(file_storage.stream)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        if img.width > max_w or img.height > max_h:
            img.thumbnail((max_w, max_h), Image.LANCZOS)

        ext = os.path.splitext(dest_abs_path)[1].lower()
        save_kwargs = {'optimize': True}
        if ext in ('.jpg', '.jpeg', '.webp'):
            save_kwargs['quality'] = quality

        os.makedirs(os.path.dirname(dest_abs_path), exist_ok=True)
        img.save(dest_abs_path, **save_kwargs)
        return True
    except Exception as e:
        logger.error("Image compress+save failed: %s", e)
        return False


# ═══════════════════════════════════════════════════════════════
#  TEMP FILE HANDLING — upload on select, move on submit
# ═══════════════════════════════════════════════════════════════

def move_temp_file(form, field_name, dest_subfolder, app, readable_name=None):
    """
    Move a previously-uploaded temp file to its final destination.
    Falls back to direct file upload if no temp path is provided.
    """
    temp_path = form.get(f'{field_name}_temp_path', '').strip()

    if temp_path:
        abs_temp = os.path.join(app.root_path, temp_path)
        if not os.path.exists(abs_temp):
            logger.warning("Temp file not found: %s", abs_temp)
            return None

        ext = os.path.splitext(temp_path)[1]

        if readable_name:
            safe_name = secure_filename(readable_name)
            filename = f"{safe_name}{ext}"
        else:
            filename = f"{uuid.uuid4().hex}{ext}"

        dest_dir = os.path.join(app.root_path, 'static', 'data', dest_subfolder)
        os.makedirs(dest_dir, exist_ok=True)

        abs_dest = os.path.join(dest_dir, filename)
        shutil.move(abs_temp, abs_dest)

        return f"data/{dest_subfolder}/{filename}"

    file = request.files.get(field_name)
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1]

        if readable_name:
            safe_name = secure_filename(readable_name)
            filename = f"{safe_name}{ext}"
        else:
            filename = f"{uuid.uuid4().hex}{ext}"

        dest_dir = os.path.join(app.root_path, 'static', 'data', dest_subfolder)
        os.makedirs(dest_dir, exist_ok=True)

        abs_path = os.path.join(dest_dir, filename)
        file.save(abs_path)
        return f"data/{dest_subfolder}/{filename}"

    return None


def move_temp_image_compressed(form, field_name, dest_subfolder, app, readable_name=None):
    """
    Like move_temp_file but compresses the image after moving.
    If the file comes from temp, it's moved then compressed in-place.
    If it's a direct upload, it's saved compressed.
    """
    temp_path = form.get(f'{field_name}_temp_path', '').strip()

    if temp_path:
        abs_temp = os.path.join(app.root_path, temp_path)
        if not os.path.exists(abs_temp):
            logger.warning("Temp image not found: %s", abs_temp)
            return None

        ext = os.path.splitext(temp_path)[1]

        if readable_name:
            safe_name = secure_filename(readable_name)
            filename = f"{safe_name}{ext}"
        else:
            filename = f"{uuid.uuid4().hex}{ext}"

        dest_dir = os.path.join(app.root_path, 'static', 'data', dest_subfolder)
        os.makedirs(dest_dir, exist_ok=True)

        abs_dest = os.path.join(dest_dir, filename)
        shutil.move(abs_temp, abs_dest)

        # Compress in-place
        compress_image_at_path(abs_dest)

        return f"data/{dest_subfolder}/{filename}"

    file = request.files.get(field_name)
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1]
        if ext.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
            return None

        if readable_name:
            safe_name = secure_filename(readable_name)
            filename = f"{safe_name}{ext}"
        else:
            filename = f"{uuid.uuid4().hex}{ext}"

        dest_dir = os.path.join(app.root_path, 'static', 'data', dest_subfolder)
        os.makedirs(dest_dir, exist_ok=True)

        abs_path = os.path.join(dest_dir, filename)
        compress_and_save_image(file, abs_path)

        return f"data/{dest_subfolder}/{filename}"

    return None


def cleanup_old_temp_files(app):
    """Delete temp uploads older than 1 hour."""
    temp_dir = os.path.join(app.root_path, TEMP_UPLOAD_DIR)
    if not os.path.exists(temp_dir):
        return

    cutoff = time.time() - 3600
    for f in glob.glob(os.path.join(temp_dir, '*')):
        if os.path.isfile(f) and os.path.getmtime(f) < cutoff:
            try:
                os.remove(f)
                logger.info("Cleaned old temp file: %s", f)
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════
#  EXISTING FILE HELPERS
# ═══════════════════════════════════════════════════════════════

def get_data_path(subfolder):
    path = os.path.join(current_app.config['DATA_DIR'], subfolder)
    os.makedirs(path, exist_ok=True)
    return path


def make_filename(product_slug, label, original_filename):
    ext = os.path.splitext(original_filename)[1].lower()
    if not ext:
        ext = '.bin'
    safe_slug = secure_filename(product_slug) or 'file'
    return f"{safe_slug}_{label}{ext}"


def save_data_file(file_obj, subfolder, filename):
    dir_path = get_data_path(subfolder)
    abs_path = os.path.join(dir_path, filename)
    file_obj.save(abs_path)
    return f"data/{subfolder}/{filename}"


def delete_old_file(db_relative_path):
    if not db_relative_path:
        return
    abs_path = os.path.join(current_app.root_path, 'static', db_relative_path)
    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except OSError:
        pass


# ═══════════════════════════════════════════════════════════════
#  AUDIO PREVIEW GENERATOR (WAV → MP3 preview via ffmpeg)
# ═══════════════════════════════════════════════════════════════

def create_audio_preview(full_audio_abs_path, start_sec, end_sec, output_filename):
    """
    Create a trimmed MP3 preview from any audio file (WAV, MP3, etc.)
    using ffmpeg. Returns the relative path (from static/).
    """
    duration = end_sec - start_sec
    if duration <= 0:
        raise ValueError("End time must be after start time")

    preview_dir = get_data_path(FOLDER_PREVIEWS)
    abs_output = os.path.join(preview_dir, output_filename)

    cmd = [
        'ffmpeg', '-y',
        '-i', full_audio_abs_path,
        '-ss', str(start_sec),
        '-t', str(duration),
        '-acodec', 'libmp3lame',
        '-b:a', '192k',
        '-loglevel', 'error',
        abs_output,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    return f"data/{FOLDER_PREVIEWS}/{output_filename}"


def convert_wav_to_full_preview(wav_abs_path, beat_slug, max_seconds=90):
    """
    Convert a WAV file to a full-length (or capped) MP3 preview.
    If the WAV is longer than max_seconds, trim it with a fade-out.
    Returns the relative path (from static/) or None.
    """
    if not wav_abs_path or not os.path.exists(wav_abs_path):
        return None

    try:
        preview_dir = get_data_path(FOLDER_PREVIEWS)
        output_filename = f"{secure_filename(beat_slug)}_preview.mp3"
        abs_output = os.path.join(preview_dir, output_filename)

        # Use ffmpeg to convert WAV → MP3 with optional trimming
        cmd = [
            'ffmpeg', '-y',
            '-i', wav_abs_path,
            '-t', str(max_seconds),
            '-af', f'afade=t=out:st={max_seconds - 3}:d=3',
            '-acodec', 'libmp3lame',
            '-b:a', '128k',
            '-loglevel', 'error',
            abs_output,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("WAV→MP3 preview failed: %s", result.stderr)
            return None

        return f"data/{FOLDER_PREVIEWS}/{output_filename}"

    except Exception as e:
        logger.error("WAV→MP3 conversion error for %s: %s", beat_slug, e)
        return None


# ═══════════════════════════════════════════════════════════════
#  BEAT PACK ZIP GENERATOR
# ═══════════════════════════════════════════════════════════════

def _regenerate_pack_zip(pack):
    """
    Regenerate the pack ZIP. Includes WAV files and project files.
    No separate MP3 — preview MP3s are not included in the pack.
    """
    pack_product = Product.query.get(pack.product_id)
    if not pack_product:
        return

    slug = pack_product.slug
    pack_name = pack_product.name

    delete_old_file(pack.zip_path)

    beats = BeatDetail.query.filter_by(pack_id=pack.id).all()
    pack.total_beats = len(beats)

    if not beats:
        pack.zip_path = ''
        return

    packs_dir = get_data_path(FOLDER_PACKS)
    safe_slug = secure_filename(slug) or 'pack'
    zip_filename = f"{safe_slug}.zip"
    zip_abs_path = os.path.join(packs_dir, zip_filename)
    static_root = os.path.join(current_app.root_path, 'static')

    with zipfile.ZipFile(zip_abs_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        readme_text = (
            f"{pack_name}\n"
            f"{'=' * len(pack_name)}\n\n"
            f"This pack contains {len(beats)} beat(s).\n"
            f"Provided by XLoveBeatz\n"
        )
        zf.writestr("README.txt", readme_text)

        for beat in beats:
            beat_product = Product.query.get(beat.product_id)
            if not beat_product:
                continue

            beat_name = secure_filename(beat_product.name) or 'beat'
            folder_in_zip = f"{pack_name}/{beat_name}"

            # Include WAV file
            if beat.wav_file:
                wav_abs = os.path.join(static_root, beat.wav_file)
                if os.path.exists(wav_abs):
                    zf.write(wav_abs, f"{folder_in_zip}/{beat_name}.wav")

            # Include project file if present
            if beat.project_file:
                proj_abs = os.path.join(static_root, beat.project_file)
                if os.path.exists(proj_abs):
                    proj_ext = os.path.splitext(beat.project_file)[1]
                    zf.write(proj_abs, f"{folder_in_zip}/{beat_name}_project{proj_ext}")

    pack.zip_path = f"data/{FOLDER_PACKS}/{zip_filename}"
    logger.info("Pack ZIP regenerated: %s (%d beats)", zip_filename, len(beats))


# ═══════════════════════════════════════════════════════════════
#  TEMP UPLOAD API ROUTES
# ═══════════════════════════════════════════════════════════════

@bp.route('/api/admin/upload-temp', methods=['POST'])
def upload_temp_file():
    """Upload a file to temp folder immediately. Returns temp path."""

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.get(user_id)
    if not user or not user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'Empty file'}), 400

    abs_temp_dir = os.path.join(current_app.root_path, TEMP_UPLOAD_DIR)
    os.makedirs(abs_temp_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1]
    temp_name = f"{uuid.uuid4().hex}{ext}"
    temp_path = os.path.join(abs_temp_dir, temp_name)

    file.save(temp_path)

    relative_path = os.path.join(TEMP_UPLOAD_DIR, temp_name).replace('\\', '/')

    return jsonify({
        'success': True,
        'temp_path': relative_path,
        'original_name': file.filename,
        'size': os.path.getsize(temp_path)
    })


@bp.route('/api/admin/cleanup-temp', methods=['POST'])
def cleanup_temp():
    """Delete a temp file if user removes it from form."""

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.get(user_id)
    if not user or not user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    temp_path = data.get('temp_path', '')
    if not temp_path:
        return jsonify({'error': 'No path'}), 400

    abs_path = os.path.join(current_app.root_path, temp_path)
    if os.path.exists(abs_path):
        os.remove(abs_path)

    return jsonify({'success': True})


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin')
@admin_required
def admin_dashboard():
    cleanup_old_temp_files(current_app)

    stats = get_admin_stats()
    limit = current_app.config['ADMIN_RECENT_LIMIT']
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(limit).all()
    recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
    return render_template('admin/dashboard.html',
                           stats=stats, recent_orders=recent_orders,
                           recent_activities=recent_activities)


# ═══════════════════════════════════════════════════════════════
#  PRODUCTS — LIST
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/products')
@admin_required
def admin_products():
    product_type = request.args.get('type')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['PRODUCTS_PER_PAGE']

    query = Product.query
    if product_type:
        query = query.filter_by(product_type=product_type)

    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False,
    )
    return render_template('admin/products.html',
                           products=pagination.items, pagination=pagination,
                           current_type=product_type)


# ═══════════════════════════════════════════════════════════════
#  PRODUCT — ADD
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/product/add', methods=['GET', 'POST'])
@admin_required
def admin_product_add():
    if request.method == 'POST':
        try:
            product_type = request.form.get('product_type')
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '')
            price = request.form.get('price', type=float)

            if not name or not product_type:
                flash('Name and product type are required', 'error')
                return redirect(url_for('admin.admin_product_add'))

            slug = generate_unique_slug(name, Product)

            if product_type == 'beat':
                price_cents = 0
                description = ''
            else:
                if price is None or price < 0:
                    flash('Price must be non-negative', 'error')
                    return redirect(url_for('admin.admin_product_add'))
                price_cents = int(price * 100)

            # ── Cover image (temp or direct) — non-beat products only ──
            cover_image_path = None
            if product_type != 'beat':
                cover_image_path = move_temp_file(
                    request.form, 'cover_image', FOLDER_IMAGES, current_app
                )

            product = Product(
                product_type=product_type, name=name, slug=slug,
                description=description, price_cents=price_cents,
                cover_image=cover_image_path, is_active=True,
            )
            db.session.add(product)
            db.session.flush()

            if product_type == 'beat':
                _create_beat_details(product)
            elif product_type == 'pack':
                db.session.add(BeatPack(
                    product_id=product.id,
                    genre=request.form.get('pack_genre', '').strip(),
                    total_beats=0,
                    zip_path='',
                ))
            elif product_type == 'preset':
                _create_preset_details(product, slug)

            db.session.commit()
            log_activity(get_current_user().id, 'create', 'product',
                         product.id, f"Created {product_type}: {name}",
                         request.remote_addr)
            flash(f'{name} added successfully!', 'success')
            return redirect(url_for('admin.admin_products'))

        except Exception as e:
            db.session.rollback()
            logger.error("Error creating product: %s", e)
            flash('An error occurred while creating the product', 'error')

    packs = Product.query.filter_by(product_type='pack').all()
    return render_template('admin/product_form.html', packs=packs,
                           product=None, beat_detail=None, beat_pack=None,
                           vocal_preset=None, license_prices={},
                           basic_files_text='', premium_files_text='',
                           exclusive_files_text='',
                           basic_tags='Non-Exclusive',
                           premium_tags='Non-Exclusive',
                           exclusive_tags='100% Ownership')


# ═══════════════════════════════════════════════════════════════
#  PRODUCT — EDIT
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/product/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_product_edit(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        try:
            product.name = request.form.get('name', '').strip()

            if product.product_type != 'beat':
                product.description = request.form.get('description', '')
                price = request.form.get('price', type=float)
                if price is not None and price >= 0:
                    product.price_cents = int(price * 100)

                # ── Cover image (temp or direct) ──
                new_cover = move_temp_file(
                    request.form, 'cover_image', FOLDER_IMAGES, current_app
                )
                if new_cover:
                    delete_old_file(product.cover_image)
                    product.cover_image = new_cover

            if product.product_type == 'beat':
                detail = BeatDetail.query.filter_by(product_id=product.id).first()
                if detail:
                    old_pack_id = detail.pack_id

                    detail.bpm = request.form.get('bpm', type=int)
                    detail.musical_key = request.form.get('musical_key', '').strip()
                    detail.genre = request.form.get('beat_genre', '').strip()
                    detail.pack_id = request.form.get('pack_id', type=int) or None

                    _update_beat_files(product.slug, detail)

                    new_pack_id = detail.pack_id
                    packs_to_update = set()
                    if old_pack_id:
                        packs_to_update.add(old_pack_id)
                    if new_pack_id:
                        packs_to_update.add(new_pack_id)

                    for pid in packs_to_update:
                        pack = BeatPack.query.get(pid)
                        if pack:
                            _regenerate_pack_zip(pack)

                _update_beat_licenses(product.id)

                basic_price = request.form.get('basic_price', type=float)
                if basic_price is not None and basic_price > 0:
                    product.price_cents = int(basic_price * 100)

            elif product.product_type == 'pack':
                pack = BeatPack.query.filter_by(product_id=product.id).first()
                if pack:
                    pack.genre = request.form.get('pack_genre', '').strip()

            elif product.product_type == 'preset':
                preset = VocalPreset.query.filter_by(product_id=product.id).first()
                if preset:
                    preset.supported_daw = request.form.get('supported_daw')

                    new_zip = move_temp_file(
                        request.form, 'preset_zip', FOLDER_PRESETS, current_app
                    )
                    if new_zip:
                        delete_old_file(preset.preset_zip)
                        preset.preset_zip = new_zip

            db.session.commit()
            log_activity(get_current_user().id, 'update', 'product',
                         product.id, f"Updated: {product.name}", request.remote_addr)
            flash(f'{product.name} updated successfully!', 'success')
            return redirect(url_for('admin.admin_products'))

        except Exception as e:
            db.session.rollback()
            logger.error("Error updating product %s: %s", product_id, e)
            flash('An error occurred while updating the product', 'error')

    packs = Product.query.filter_by(product_type='pack').all()
    beat_detail = BeatDetail.query.filter_by(product_id=product.id).first() if product.product_type == 'beat' else None
    beat_pack = BeatPack.query.filter_by(product_id=product.id).first() if product.product_type == 'pack' else None
    vocal_preset = VocalPreset.query.filter_by(product_id=product.id).first() if product.product_type == 'preset' else None

    license_prices = {}
    license_files = {}
    license_tags = {}
    if product.product_type == 'beat':
        for blp in BeatLicensePrice.query.filter_by(beat_id=product.id).all():
            key = blp.license.name.lower()
            license_prices[key] = blp.price_cents / 100
            license_files[key] = blp.included_files or ''
            license_tags[key] = blp.tags or ''

    return render_template('admin/product_form.html', product=product,
                           beat_detail=beat_detail, beat_pack=beat_pack,
                           vocal_preset=vocal_preset, packs=packs,
                           license_prices=license_prices,
                           basic_files_text=license_files.get('basic', ''),
                           premium_files_text=license_files.get('premium', ''),
                           exclusive_files_text=license_files.get('exclusive', ''),
                           basic_tags=license_tags.get('basic', 'Non-Exclusive'),
                           premium_tags=license_tags.get('premium', 'Non-Exclusive'),
                           exclusive_tags=license_tags.get('exclusive', '100% Ownership'))


# ═══════════════════════════════════════════════════════════════
#  PRODUCT — DELETE / TOGGLE
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/product/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_product_delete(product_id):
    product = Product.query.get_or_404(product_id)
    name = product.name
    try:
        if product.product_type == 'beat':
            detail = BeatDetail.query.filter_by(product_id=product.id).first()
            if detail:
                affected_pack_id = detail.pack_id

                # Delete audio files (preview, wav, project — no separate mp3)
                delete_old_file(detail.preview_audio)
                delete_old_file(detail.wav_file)
                delete_old_file(detail.project_file)

                # Delete beat image
                delete_old_file(detail.beat_image)

                BeatDetail.query.filter_by(product_id=product.id).delete()

                if affected_pack_id:
                    pack = BeatPack.query.get(affected_pack_id)
                    if pack:
                        _regenerate_pack_zip(pack)

            BeatLicensePrice.query.filter_by(beat_id=product.id).delete()

        elif product.product_type == 'pack':
            pack = BeatPack.query.filter_by(product_id=product.id).first()
            if pack:
                delete_old_file(pack.zip_path)
            delete_old_file(product.cover_image)
            BeatPack.query.filter_by(product_id=product.id).delete()

        elif product.product_type == 'preset':
            preset = VocalPreset.query.filter_by(product_id=product.id).first()
            if preset:
                delete_old_file(preset.preset_zip)
            delete_old_file(product.cover_image)
            VocalPreset.query.filter_by(product_id=product.id).delete()

        db.session.delete(product)
        db.session.commit()
        log_activity(get_current_user().id, 'delete', 'product',
                     product_id, f"Deleted: {name}", request.remote_addr)
        flash(f'{name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error("Error deleting product %s: %s", product_id, e)
        flash('An error occurred while deleting the product', 'error')

    return redirect(url_for('admin.admin_products'))


@bp.route('/admin/product/<int:product_id>/toggle', methods=['POST'])
@admin_required
def admin_product_toggle(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    status = "activated" if product.is_active else "deactivated"
    flash(f'{product.name} {status}!', 'success')
    return redirect(url_for('admin.admin_products'))


# ═══════════════════════════════════════════════════════════════
#  PRIVATE HELPERS — FILE CREATION (TEMP-AWARE)
# ═══════════════════════════════════════════════════════════════

def _create_beat_details(product):
    """
    Create beat detail record. Workflow:
    1. Upload WAV file
    2. Auto-convert WAV → MP3 preview (trimmed + faded)
    3. Upload beat cover image (compressed)
    4. Upload project file
    5. Create license price records
    6. Regenerate pack ZIP if assigned
    """
    slug = product.slug

    # ── 1. WAV → data/wav/ ──
    wav_db_path = move_temp_file(
        request.form, 'wav_file', FOLDER_WAV, current_app,
        readable_name=f"{slug}_beat"
    )

    # ── 2. Auto-generate MP3 preview from WAV ──
    preview_db_path = ''
    if wav_db_path:
        abs_wav = os.path.join(current_app.root_path, 'static', wav_db_path)

        # Check if user specified custom preview start/end
        preview_start = request.form.get('preview_start', '').strip()
        preview_end = request.form.get('preview_end', '').strip()

        if preview_start and preview_end:
            try:
                preview_fname = f"{secure_filename(slug)}_preview.mp3"
                preview_db_path = create_audio_preview(
                    abs_wav,
                    float(preview_start),
                    float(preview_end),
                    preview_fname,
                )
            except Exception as e:
                logger.error("Trimmed preview creation failed for %s: %s", slug, e)
        else:
            # Default: convert entire WAV to 90-second preview with fade
            preview_db_path = convert_wav_to_full_preview(abs_wav, slug) or ''

    # ── 3. Beat cover image (compressed) ──
    beat_image_path = move_temp_image_compressed(
        request.form, 'beat_image', FOLDER_BEAT_IMAGES, current_app,
        readable_name=f"{slug}_cover"
    )

    # ── 4. Project file → data/flps/ ──
    project_db_path = move_temp_file(
        request.form, 'project_file', FOLDER_FLP, current_app,
        readable_name=f"{slug}_project"
    )

    # ── 5. Duration ──
    duration = request.form.get('duration_hidden', '').strip()

    # ── 6. Pack assignment ──
    pack_id = request.form.get('pack_id', type=int) or None

    beat_detail = BeatDetail(
        product_id=product.id,
        bpm=request.form.get('bpm', type=int),
        musical_key=request.form.get('musical_key', '').strip(),
        genre=request.form.get('beat_genre', '').strip(),
        duration=duration,
        preview_audio=preview_db_path,
        wav_file=wav_db_path or '',
        project_file=project_db_path or '',
        beat_image=beat_image_path or None,
        pack_id=pack_id,
    )
    db.session.add(beat_detail)
    db.session.flush()

    # ── 7. Create license price records ──
    _update_beat_licenses(product.id)

    # ── 7b. Sync product price with basic license price ──
    basic_price = request.form.get('basic_price', type=float)
    if basic_price is not None and basic_price > 0:
        product.price_cents = int(basic_price * 100)

    # ── 8. Regenerate pack ZIP if assigned ──
    if pack_id:
        pack = BeatPack.query.get(pack_id)
        if pack:
            _regenerate_pack_zip(pack)


def _update_beat_files(slug, beat_detail):
    """
    Update beat files during edit. Handles:
    - WAV upload (+ auto-regenerate MP3 preview)
    - Beat cover image (compressed)
    - Project file
    No separate MP3 handling.
    """
    files_changed = False

    # ── WAV (temp or direct) ──
    new_wav = move_temp_file(
        request.form, 'wav_file', FOLDER_WAV, current_app,
        readable_name=f"{slug}_beat"
    )
    if new_wav:
        delete_old_file(beat_detail.wav_file)
        beat_detail.wav_file = new_wav
        files_changed = True

        # Auto-regenerate MP3 preview from new WAV
        abs_wav = os.path.join(current_app.root_path, 'static', new_wav)

        # Delete old preview
        delete_old_file(beat_detail.preview_audio)

        preview_start = request.form.get('preview_start', '').strip()
        preview_end = request.form.get('preview_end', '').strip()

        if preview_start and preview_end:
            try:
                preview_fname = f"{secure_filename(slug)}_preview.mp3"
                beat_detail.preview_audio = create_audio_preview(
                    abs_wav,
                    float(preview_start),
                    float(preview_end),
                    preview_fname,
                )
            except Exception as e:
                logger.error("Preview regeneration failed for %s: %s", slug, e)
                beat_detail.preview_audio = ''
        else:
            beat_detail.preview_audio = convert_wav_to_full_preview(abs_wav, slug) or ''

    # ── Beat cover image (compressed) ──
    new_beat_image = move_temp_image_compressed(
        request.form, 'beat_image', FOLDER_BEAT_IMAGES, current_app,
        readable_name=f"{slug}_cover"
    )
    if new_beat_image:
        delete_old_file(beat_detail.beat_image)
        beat_detail.beat_image = new_beat_image

    # ── PROJECT FILE (temp or direct) ──
    new_project = move_temp_file(
        request.form, 'project_file', FOLDER_FLP, current_app,
        readable_name=f"{slug}_project"
    )
    if new_project:
        delete_old_file(beat_detail.project_file)
        beat_detail.project_file = new_project
        files_changed = True
        logger.info("Project file saved: %s", beat_detail.project_file)

    # ── Regenerate pack ZIP if files changed ──
    if files_changed and beat_detail.pack_id:
        pack = BeatPack.query.get(beat_detail.pack_id)
        if pack:
            _regenerate_pack_zip(pack)


def _create_preset_details(product, slug):
    """Create preset with file from temp or direct upload."""
    supported_daw = request.form.get('supported_daw')

    preset_zip_path = move_temp_file(
        request.form, 'preset_zip', FOLDER_PRESETS, current_app,
        readable_name=f"{slug}_preset"
    ) or ''

    db.session.add(VocalPreset(
        product_id=product.id,
        supported_daw=supported_daw,
        preset_zip=preset_zip_path,
    ))


def _update_beat_licenses(product_id):
    """Create or update Basic/Premium/Exclusive license prices for a beat."""
    licenses = {l.name: l for l in License.query.all()}
    for tier in ('Basic', 'Premium', 'Exclusive'):
        tier_price = request.form.get(f"{tier.lower()}_price", type=float)
        tier_files = request.form.get(f"{tier.lower()}_files", '')
        tier_tags = request.form.get(f"{tier.lower()}_tags", '')
        if tier_price is not None and tier in licenses:
            blp = BeatLicensePrice.query.filter_by(
                beat_id=product_id, license_id=licenses[tier].id).first()
            if blp:
                blp.price_cents = int(tier_price * 100)
                if tier_files:
                    blp.included_files = tier_files
                if tier_tags:
                    blp.tags = tier_tags
            else:
                new_blp = BeatLicensePrice(
                    beat_id=product_id,
                    license_id=licenses[tier].id,
                    price_cents=int(tier_price * 100),
                    included_files=tier_files,
                    tags=tier_tags,
                )
                db.session.add(new_blp)


# ═══════════════════════════════════════════════════════════════
#  ORDERS
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/orders')
@admin_required
def admin_orders():
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ORDERS_PER_PAGE']

    query = Order.query
    if status:
        query = query.filter_by(payment_status=status)

    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False,
    )
    return render_template('admin/orders.html',
                           orders=pagination.items, pagination=pagination,
                           current_status=status)


@bp.route('/admin/order/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    order = (
        Order.query
        .options(
            db.joinedload(Order.items).joinedload(OrderItem.product),
            db.joinedload(Order.items).joinedload(OrderItem.license),
        )
        .get_or_404(order_id)
    )
    return render_template('admin/order_detail.html', order=order)


@bp.route('/admin/order/<int:order_id>/status', methods=['POST'])
@admin_required
def admin_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    valid = ('pending', 'paid', 'failed', 'refunded')
    if new_status in valid:
        order.payment_status = new_status
        db.session.commit()
        log_activity(get_current_user().id, 'update', 'order',
                     order_id, f"Status -> {new_status}", request.remote_addr)
        flash(f'Order status updated to {new_status}!', 'success')
    else:
        flash('Invalid status', 'error')
    return redirect(url_for('admin.admin_order_detail', order_id=order_id))


# ═══════════════════════════════════════════════════════════════
#  USERS
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/users')
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ORDERS_PER_PAGE', 20)

    pagination = User.query.filter(User.email != os.getenv('ADMIN_EMAIL')) \
        .order_by(User.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    user_ids = [u.id for u in pagination.items]
    order_counts = {}
    if user_ids:
        rows = (
            db.session.query(Order.user_id, db.func.count(Order.id))
            .filter(Order.user_id.in_(user_ids))
            .group_by(Order.user_id)
            .all()
        )
        order_counts = {uid: cnt for uid, cnt in rows}

    return render_template('admin/users.html',
                           users=pagination.items, pagination=pagination,
                           order_counts=order_counts)


@bp.route('/admin/user/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    user = User.query.get_or_404(user_id)
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    downloads = Download.query.filter_by(user_id=user.id).all()
    return render_template('admin/user_detail.html',
                           user=user, orders=orders, downloads=downloads)


@bp.route('/admin/user/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def admin_user_toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == get_current_user().id:
        flash('You cannot change your own admin status', 'error')
        return redirect(url_for('admin.admin_user_detail', user_id=user_id))

    user.is_admin = not user.is_admin
    db.session.commit()
    status = "granted admin" if user.is_admin else "removed from admin"
    flash(f'{user.username} {status}!', 'success')
    return redirect(url_for('admin.admin_user_detail', user_id=user_id))


# ═══════════════════════════════════════════════════════════════
#  DISCOUNT CODES
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/discounts')
@admin_required
def admin_discounts():
    codes = DiscountCode.query.order_by(DiscountCode.created_at.desc()).all()
    return render_template('admin/discounts.html', codes=codes,now=datetime.utcnow())


@bp.route('/admin/discount/add', methods=['POST'])
@admin_required
def admin_discount_add():
    code = request.form.get('code', '').strip().upper()
    if not code:
        flash('Discount code is required', 'error')
        return redirect(url_for('admin.admin_discounts'))
    if DiscountCode.query.filter_by(code=code).first():
        flash('Code already exists!', 'error')
        return redirect(url_for('admin.admin_discounts'))

    discount_type = request.form.get('discount_type')
    discount_value = request.form.get('discount_value', 0, type=int)
    max_discount = request.form.get('max_discount', 0, type=float)
    expires_str = request.form.get('expires_at', '').strip()
    strip_message = request.form.get('strip_message', '').strip()
    post_to_strip = request.form.get('post_to_strip') == 'on'

    expires_at = None
    if expires_str:
        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
            try:
                expires_at = datetime.strptime(expires_str, fmt)
                break
            except ValueError:
                continue

    discount = DiscountCode(
        code=code,
        discount_type=discount_type,
        discount_value=discount_value,
        min_order_cents=int(request.form.get('min_order', 0, type=float) * 100),
        max_discount_cents=int(max_discount * 100),
        max_uses=request.form.get('max_uses', 0, type=int),
        expires_at=expires_at,
        strip_message=strip_message,
        post_to_strip=post_to_strip,
        is_active=True,
    )
    db.session.add(discount)
    db.session.commit()

    # Auto-post to strip if enabled
    if post_to_strip and strip_message:
        _sync_strip_messages()

    flash(f'Discount code {code} created!', 'success')
    return redirect(url_for('admin.admin_discounts'))


@bp.route('/admin/discount/<int:discount_id>/toggle', methods=['POST'])
@admin_required
def admin_discount_toggle(discount_id):
    discount = DiscountCode.query.get_or_404(discount_id)
    discount.is_active = not discount.is_active
    db.session.commit()

    # Sync strip when toggling
    if discount.post_to_strip:
        _sync_strip_messages()

    status = "activated" if discount.is_active else "deactivated"
    flash(f'Code {discount.code} {status}!', 'success')
    return redirect(url_for('admin.admin_discounts'))


@bp.route('/admin/discount/<int:discount_id>/delete', methods=['POST'])
@admin_required
def admin_discount_delete(discount_id):
    discount = DiscountCode.query.get_or_404(discount_id)
    code = discount.code
    had_strip = discount.post_to_strip and discount.strip_message

    db.session.delete(discount)
    db.session.commit()

    if had_strip:
        _sync_strip_messages()

    flash(f'Discount code {code} deleted!', 'success')
    return redirect(url_for('admin.admin_discounts'))


def _sync_strip_messages():
    """
    Collect strip_message from all active coupons AND active offers with post_to_strip=True,
    merge them with manual strip_messages, and save.
    """
    # Collect all auto-generated messages (from coupons + offers)
    auto_msgs = set()

    # Active coupon messages
    for c in DiscountCode.query.filter_by(post_to_strip=True, is_active=True).all():
        if c.strip_message:
            auto_msgs.add(c.strip_message.strip())

    # Active offer messages
    for o in Offer.query.filter_by(post_to_strip=True, is_active=True).all():
        if o.strip_message:
            auto_msgs.add(o.strip_message.strip())

    # Collect ALL auto messages ever (to know which to purge from manual list)
    all_auto = set()
    for c in DiscountCode.query.filter_by(post_to_strip=True).all():
        if c.strip_message:
            all_auto.add(c.strip_message.strip())
    for o in Offer.query.filter_by(post_to_strip=True).all():
        if o.strip_message:
            all_auto.add(o.strip_message.strip())

    # Get current strip, keep only manually-typed messages
    raw_all = get_site_setting('strip_messages', '[]')
    try:
        current_all = json.loads(raw_all)
    except (json.JSONDecodeError, TypeError):
        current_all = []

    manual_messages = [m for m in current_all if m.strip() not in all_auto]

    # Final: manual first, then sorted active auto messages
    final = manual_messages + sorted(auto_msgs)
    set_site_setting('strip_messages', json.dumps(final))


# ═══════════════════════════════════════════════════════════════
#  OFFERS
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/offers')
@admin_required
def admin_offers():
    offers = Offer.query.order_by(Offer.created_at.desc()).all()
    return render_template('admin/offers.html', offers=offers)


@bp.route('/admin/offers/add', methods=['POST'])
@admin_required
def admin_offer_add():
    name = request.form.get('name', '').strip()
    offer_type = request.form.get('offer_type', '').strip()
    applicable = request.form.get('applicable_product_type', 'all')
    stacks = request.form.get('stacks_with_coupons') == 'on'
    strip_message = request.form.get('strip_message', '').strip()
    post_to_strip = request.form.get('post_to_strip') == 'on'

    if not name or not offer_type:
        flash('Name and offer type are required.', 'error')
        return redirect(url_for('admin.admin_offers'))

    offer = Offer(
        name=name,
        offer_type=offer_type,
        applicable_product_type=applicable,
        stacks_with_coupons=stacks,
        strip_message=strip_message,
        post_to_strip=post_to_strip,
        is_active=True,
    )

    if offer_type == 'bogo':
        offer.buy_quantity = request.form.get('buy_quantity', 1, type=int)
        offer.get_quantity = request.form.get('get_quantity', 1, type=int)
    elif offer_type == 'bulk_percent':
        offer.buy_quantity = request.form.get('bulk_min_qty', 2, type=int)
        offer.discount_percentage = request.form.get('discount_percentage', 20, type=int)
    elif offer_type == 'spend_amount_off':
        offer.min_spend_cents = int(request.form.get('min_spend', 0, type=float) * 100)
        offer.discount_fixed_cents = int(request.form.get('discount_fixed', 0, type=float) * 100)

    db.session.add(offer)
    db.session.commit()

    if post_to_strip and strip_message:
        _sync_strip_messages()

    flash(f'Offer "{name}" created!', 'success')
    return redirect(url_for('admin.admin_offers'))


@bp.route('/admin/offers/<int:offer_id>/toggle', methods=['POST'])
@admin_required
def admin_offer_toggle(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    offer.is_active = not offer.is_active
    db.session.commit()

    if offer.post_to_strip:
        _sync_strip_messages()

    status = 'activated' if offer.is_active else 'deactivated'
    flash(f'Offer "{offer.name}" {status}!', 'success')
    return redirect(url_for('admin.admin_offers'))


@bp.route('/admin/offers/<int:offer_id>/delete', methods=['POST'])
@admin_required
def admin_offer_delete(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    name = offer.name
    had_strip = offer.post_to_strip and offer.strip_message
    db.session.delete(offer)
    db.session.commit()
    if had_strip:
        _sync_strip_messages()
    flash(f'Offer "{name}" deleted!', 'success')
    return redirect(url_for('admin.admin_offers'))

# ═══════════════════════════════════════════════════════════════
#  GENERATED LICENSES
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/licenses')
@admin_required
def admin_licenses():
    page = request.args.get('page', 1, type=int)
    pagination = (
        GeneratedLicense.query
        .options(db.joinedload(GeneratedLicense.order_item).joinedload(OrderItem.order))
        .order_by(GeneratedLicense.generated_at.desc())
        .paginate(page=page, per_page=25, error_out=False)
    )
    return render_template('admin/licenses.html',
                           licenses=pagination.items, pagination=pagination)


@bp.route('/admin/licenses/<int:lic_id>/download')
@admin_required
def admin_license_download(lic_id):
    gen_lic = GeneratedLicense.query.get_or_404(lic_id)

    if not gen_lic.pdf_path:
        flash('No PDF file associated with this license', 'error')
        return redirect(url_for('admin.admin_licenses'))

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    abs_path = os.path.join(project_root, gen_lic.pdf_path)

    if not os.path.exists(abs_path):
        flash('PDF file not found on disk', 'error')
        return redirect(url_for('admin.admin_licenses'))

    return send_file(abs_path, as_attachment=True,
                     download_name=os.path.basename(abs_path))


# ═══════════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    keys = ['site_title', 'site_slogan', 'contact_email',
            'whatsapp_number', 'instagram_url', 'spotify_url', 'youtube_url']

    if request.method == 'POST':
        # Handle regular text settings
        for key in keys:
            val = request.form.get(key)
            if val is not None:
                set_site_setting(key, val.strip())

        # Handle strip messages (dynamic list)
        strip_messages = request.form.getlist('strip_message')
        # Remove empty entries
        strip_messages = [m.strip() for m in strip_messages if m.strip()]
        set_site_setting('strip_messages', json.dumps(strip_messages))

        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin.admin_settings'))

    settings = {k: get_site_setting(k, '') for k in keys}

    # Parse strip messages for the template
    raw = get_site_setting('strip_messages', '[]')
    try:
        strip_messages = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        strip_messages = []

    if not strip_messages:
        strip_messages = [
            '🔥 NEW BEAT PACK "MIDNIGHT TRAP" OUT NOW',
            '⚡ INSTANT DELIVERY & SECURE CHECKOUT',
            '🎧 50% OFF ALL VOCAL PRESETS',
        ]

    return render_template('admin/settings.html',
                           settings=settings,
                           strip_messages=strip_messages)

# ═══════════════════════════════════════════════════════════════
#  ACTIVITY LOGS
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/logs')
@admin_required
def admin_logs():
    page = request.args.get('page', 1, type=int)
    pagination = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=current_app.config['LOGS_PER_PAGE'], error_out=False,
    )
    return render_template('admin/logs.html', logs=pagination.items, pagination=pagination)


# ═══════════════════════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/analytics')
@admin_required
def admin_analytics():
    days = current_app.config['ANALYTICS_PERIOD_DAYS']
    return render_template(
        'admin/analytics.html',
        monthly_revenue=get_monthly_revenue(days),
        top_products=get_top_products(),
        genre_stats=get_genre_distribution(),
    )