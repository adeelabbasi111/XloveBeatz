import logging
import os
import subprocess
import zipfile

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app, send_file,
)
from werkzeug.utils import secure_filename

from helpers.models import (
    db, Product, BeatDetail, BeatPack, VocalPreset,
    License, BeatLicensePrice, Order, OrderItem, User,
    Download, DiscountCode, ActivityLog, GeneratedLicense,
)
from helpers.utils import (
    admin_required, get_current_user,
    generate_unique_slug, allowed_file, save_upload,
)
from helpers.services import (
    log_activity, get_site_setting, set_site_setting,
    get_admin_stats, get_monthly_revenue, get_top_products,
    get_genre_distribution,
)


# ═══════════════════════════════════════════════════════════════
#  FILE STORAGE HELPERS
# ═══════════════════════════════════════════════════════════════

FOLDER_PREVIEWS = 'previews'
FOLDER_MP3      = 'mp3'
FOLDER_WAV      = 'wav'
FOLDER_FLP      = 'flps'
FOLDER_IMAGES   = 'images'
FOLDER_PRESETS  = 'presets'
FOLDER_PACKS    = 'packs'
Folder_Licenses        = 'licenses'

ALL_DATA_FOLDERS = [
    FOLDER_PREVIEWS, FOLDER_MP3, FOLDER_WAV,
    FOLDER_FLP, FOLDER_IMAGES, FOLDER_PRESETS,
    FOLDER_PACKS,Folder_Licenses
]


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
#  AUDIO PREVIEW TRIMMER
# ═══════════════════════════════════════════════════════════════

def create_audio_preview(full_mp3_abs_path, start_sec, end_sec, output_filename):
    duration = end_sec - start_sec
    if duration <= 0:
        raise ValueError("End time must be after start time")

    preview_dir = get_data_path(FOLDER_PREVIEWS)
    abs_output = os.path.join(preview_dir, output_filename)

    cmd = [
        'ffmpeg', '-y',
        '-i', full_mp3_abs_path,
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


# ═══════════════════════════════════════════════════════════════
#  BEAT PACK ZIP GENERATOR
# ═══════════════════════════════════════════════════════════════

def _regenerate_pack_zip(pack):
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

            if beat.mp3_file:
                mp3_abs = os.path.join(static_root, beat.mp3_file)
                if os.path.exists(mp3_abs):
                    zf.write(mp3_abs, f"{folder_in_zip}/{beat_name}.mp3")

            if beat.wav_file:
                wav_abs = os.path.join(static_root, beat.wav_file)
                if os.path.exists(wav_abs):
                    zf.write(wav_abs, f"{folder_in_zip}/{beat_name}.wav")

    pack.zip_path = f"data/{FOLDER_PACKS}/{zip_filename}"
    logger.info("Pack ZIP regenerated: %s (%d beats)", zip_filename, len(beats))


# ═══════════════════════════════════════════════════════════════
#  BLUEPRINT SETUP
# ═══════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)
bp = Blueprint('admin', __name__)


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin')
@admin_required
def admin_dashboard():
    stats = get_admin_stats()
    limit = current_app.config['ADMIN_RECENT_LIMIT']
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(limit).all()
    recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
    return render_template('admin/dashboard.html',
                           stats=stats, recent_orders=recent_orders,
                           recent_activities=recent_activities)


# ═══════════════════════════════════════════════════════════════
#  PRODUCTS
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

            cover_image_path = None
            if product_type != 'beat':
                cover_file = request.files.get('cover_image')
                if cover_file and cover_file.filename and allowed_file(
                        cover_file.filename, current_app.config['ALLOWED_IMAGE_EXTENSIONS']):
                    fname = make_filename(slug, 'cover', cover_file.filename)
                    cover_image_path = save_data_file(cover_file, FOLDER_IMAGES, fname)

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

                cover_file = request.files.get('cover_image')
                if cover_file and cover_file.filename and allowed_file(
                        cover_file.filename, current_app.config['ALLOWED_IMAGE_EXTENSIONS']):
                    delete_old_file(product.cover_image)
                    fname = make_filename(product.slug, 'cover', cover_file.filename)
                    product.cover_image = save_data_file(cover_file, FOLDER_IMAGES, fname)

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

                # 7b. Sync product price with basic license price
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
                    zip_file = request.files.get('preset_zip')
                    if zip_file and zip_file.filename:
                        delete_old_file(preset.preset_zip)
                        fname = make_filename(product.slug, 'preset', zip_file.filename)
                        preset.preset_zip = save_data_file(zip_file, FOLDER_PRESETS, fname)

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

                delete_old_file(detail.mp3_file)
                delete_old_file(detail.preview_audio)
                delete_old_file(detail.wav_file)
                delete_old_file(detail.project_file)

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
#  PRIVATE HELPERS — FILE CREATION
# ═══════════════════════════════════════════════════════════════

def _create_beat_details(product):
    slug = product.slug

    # 1. Full MP3 → data/mp3/
    mp3_db_path = ''
    mp3_abs_path = ''
    mp3_file = request.files.get('mp3_file')
    if mp3_file and mp3_file.filename:
        fname = make_filename(slug, 'full', mp3_file.filename)
        mp3_db_path = save_data_file(mp3_file, FOLDER_MP3, fname)
        mp3_abs_path = os.path.join(get_data_path(FOLDER_MP3), fname)

    # 2. Preview → data/previews/
    preview_db_path = ''
    preview_start = request.form.get('preview_start', '').strip()
    preview_end = request.form.get('preview_end', '').strip()

    if mp3_abs_path and preview_start and preview_end:
        try:
            preview_fname = make_filename(slug, 'preview', mp3_file.filename)
            preview_db_path = create_audio_preview(
                mp3_abs_path,
                float(preview_start),
                float(preview_end),
                preview_fname,
            )
        except Exception as e:
            logger.error("Preview creation failed for %s: %s", slug, e)

    # 3. WAV → data/wav/
    wav_db_path = ''
    wav_file = request.files.get('wav_file')
    if wav_file and wav_file.filename:
        fname = make_filename(slug, 'beat', wav_file.filename)
        wav_db_path = save_data_file(wav_file, FOLDER_WAV, fname)

    # 4. Project file → data/flps/
    project_db_path = ''
    project_file = request.files.get('project_file')
    if project_file and project_file.filename:
        fname = make_filename(slug, 'project', project_file.filename)
        project_db_path = save_data_file(project_file, FOLDER_FLP, fname)

    # 5. Duration
    duration = request.form.get('duration_hidden', '').strip()

    # 6. Pack assignment
    pack_id = request.form.get('pack_id', type=int) or None

    beat_detail = BeatDetail(
        product_id=product.id,
        bpm=request.form.get('bpm', type=int),
        musical_key=request.form.get('musical_key', '').strip(),
        genre=request.form.get('beat_genre', '').strip(),
        duration=duration,
        preview_audio=preview_db_path,
        mp3_file=mp3_db_path,
        wav_file=wav_db_path,
        project_file=project_db_path,
        pack_id=pack_id,
    )
    db.session.add(beat_detail)
    db.session.flush()

    # 7. Create license price records
    _update_beat_licenses(product.id)

    # 7b. Sync product price with basic license price
    basic_price = request.form.get('basic_price', type=float)
    if basic_price is not None and basic_price > 0:
        product.price_cents = int(basic_price * 100)

    # 8. Regenerate pack ZIP if assigned to a pack
    if pack_id:
        pack = BeatPack.query.get(pack_id)
        if pack:
            _regenerate_pack_zip(pack)


def _update_beat_files(slug, beat_detail):
    files_changed = False

    # ── MP3 ──
    mp3_file = request.files.get('mp3_file')
    if mp3_file and mp3_file.filename:
        delete_old_file(beat_detail.mp3_file)
        delete_old_file(beat_detail.preview_audio)

        fname = make_filename(slug, 'full', mp3_file.filename)
        beat_detail.mp3_file = save_data_file(mp3_file, FOLDER_MP3, fname)
        mp3_abs_path = os.path.join(get_data_path(FOLDER_MP3), fname)

        preview_start = request.form.get('preview_start', '').strip()
        preview_end = request.form.get('preview_end', '').strip()

        if preview_start and preview_end:
            try:
                preview_fname = make_filename(slug, 'preview', mp3_file.filename)
                beat_detail.preview_audio = create_audio_preview(
                    mp3_abs_path,
                    float(preview_start),
                    float(preview_end),
                    preview_fname,
                )
            except Exception as e:
                logger.error("Preview creation failed for %s: %s", slug, e)

        duration = request.form.get('duration_hidden', '').strip()
        if duration:
            beat_detail.duration = duration

        files_changed = True

    # ── WAV ──
    wav_file = request.files.get('wav_file')
    if wav_file and wav_file.filename:
        delete_old_file(beat_detail.wav_file)
        fname = make_filename(slug, 'beat', wav_file.filename)
        beat_detail.wav_file = save_data_file(wav_file, FOLDER_WAV, fname)
        files_changed = True

    # ── PROJECT FILE ──
    project_file = request.files.get('project_file')
    if project_file and project_file.filename:
        delete_old_file(beat_detail.project_file)
        fname = make_filename(slug, 'project', project_file.filename)
        beat_detail.project_file = save_data_file(project_file, FOLDER_FLP, fname)
        files_changed = True
        logger.info("Project file saved: %s -> %s", project_file.filename, beat_detail.project_file)

    # ── Regenerate pack ZIP if files changed ──
    if files_changed and beat_detail.pack_id:
        pack = BeatPack.query.get(beat_detail.pack_id)
        if pack:
            _regenerate_pack_zip(pack)

def _create_preset_details(product, slug):
    supported_daw = request.form.get('supported_daw')
    preset_zip_path = ''

    zip_file = request.files.get('preset_zip')
    if zip_file and zip_file.filename:
        fname = make_filename(slug, 'preset', zip_file.filename)
        preset_zip_path = save_data_file(zip_file, FOLDER_PRESETS, fname)

    db.session.add(VocalPreset(
        product_id=product.id,
        supported_daw=supported_daw,
        preset_zip=preset_zip_path,
    ))


def _update_beat_licenses(product_id):
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

    # ✅ YEH LINE CHANGE KI HAI: Filter add kar diya hai email ke against
    pagination = User.query.filter(User.email != os.getenv('ADMIN_EMAIL')) \
        .order_by(User.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    # Count orders per user
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
    return render_template('admin/discounts.html', codes=codes)


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

    discount = DiscountCode(
        code=code,
        discount_type=request.form.get('discount_type'),
        discount_value=request.form.get('discount_value', type=int),
        min_order_cents=int(request.form.get('min_order', 0, type=float) * 100),
        max_uses=request.form.get('max_uses', 0, type=int),
        is_active=True,
    )
    db.session.add(discount)
    db.session.commit()
    flash(f'Discount code {code} created!', 'success')
    return redirect(url_for('admin.admin_discounts'))


@bp.route('/admin/discount/<int:discount_id>/toggle', methods=['POST'])
@admin_required
def admin_discount_toggle(discount_id):
    discount = DiscountCode.query.get_or_404(discount_id)
    discount.is_active = not discount.is_active
    db.session.commit()
    status = "activated" if discount.is_active else "deactivated"
    flash(f'Code {discount.code} {status}!', 'success')
    return redirect(url_for('admin.admin_discounts'))


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
#  LICENSE TIERS
# ═══════════════════════════════════════════════════════════════




# ═══════════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════════

@bp.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    keys = ['site_title', 'site_slogan', 'contact_email',
            'whatsapp_number', 'instagram_url', 'spotify_url', 'youtube_url']

    if request.method == 'POST':
        for key in keys:
            val = request.form.get(key)
            if val is not None:
                set_site_setting(key, val.strip())
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin.admin_settings'))

    settings = {k: get_site_setting(k, '') for k in keys}
    return render_template('admin/settings.html', settings=settings)


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