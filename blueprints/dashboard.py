from flask import (
    Blueprint, render_template, flash, redirect,
    url_for, send_from_directory,send_file, current_app, request, jsonify, session,flash
)
from helpers.models import (
    db, Order, OrderItem, Download, Product,
    BeatDetail, VocalPreset, User, GeneratedLicense, BeatPack
)
from helpers.utils import login_required, get_current_user
from helpers.services import get_user_orders, track_download
from werkzeug.security import check_password_hash, generate_password_hash
import os
import logging

import zipfile
import io
import os

bp = Blueprint('dashboard', __name__)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD PAGE
# ═══════════════════════════════════════════════════════════════

@bp.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    orders = get_user_orders(user.id)
    downloads = Download.query.filter_by(user_id=user.id).all()

    # Build download count map: product_id → count
    dl_map = {d.product_id: d.download_count for d in downloads}

    # Collect all purchased order items from paid orders
    purchased_items = []
    for order in orders:
        if order.payment_status == 'paid':
            for item in order.items:
                purchased_items.append(item)

    # Unique purchased products (for stats card)
    purchased_ids = set(item.product_id for item in purchased_items)
    purchased = Product.query.filter(Product.id.in_(purchased_ids)).all() if purchased_ids else []

    # Generated licenses for this user's paid order items
    order_item_ids = [item.id for item in purchased_items]
    licenses = []
    if order_item_ids:
        licenses = (
            GeneratedLicense.query
            .filter(GeneratedLicense.order_item_id.in_(order_item_ids))
            .order_by(GeneratedLicense.generated_at.desc())
            .all()
        )

    return render_template(
        'dashboard.html',
        user=user,
        orders=orders,
        downloads=downloads,
        purchased_products=purchased,
        purchased_items=purchased_items,
        download_counts=dl_map,
        licenses=licenses,
    )

# ═══════════════════════════════════════════════════════════════
#  API: USER PURCHASES
# ═══════════════════════════════════════════════════════════════

@bp.route('/api/user/purchases')
def api_user_purchases():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    items = (
        OrderItem.query
        .join(Order)
        .join(Product)
        .options(db.joinedload(OrderItem.product))
        .options(db.joinedload(OrderItem.license))
        .filter(Order.user_id == user_id, Order.payment_status == 'paid')
        .order_by(Order.created_at.desc())
        .all()
    )

    purchases = []
    for item in items:
        product = item.product
        if not product:
            continue

        # Get download count
        dl = Download.query.filter_by(
            user_id=user_id, product_id=product.id
        ).first()

        license_name = item.license.name if item.license else 'Standard'

        purchases.append({
            'product_id': product.id,
            'product_name': product.name,
            'product_type': product.product_type,
            'license': license_name,
            'price_paid': (item.price_paid_cents or 0) / 100,
            'download_count': dl.download_count if dl else 0,
            'order_date': item.order.created_at.strftime('%d %b %Y') if item.order else '—',
        })

    return jsonify({'purchases': purchases})


# ═══════════════════════════════════════════════════════════════
#  API: USER LICENSES (Generated License PDFs)
# ═══════════════════════════════════════════════════════════════

@bp.route('/api/user/licenses')
def api_user_licenses():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    licenses = (
        GeneratedLicense.query
        .join(OrderItem, GeneratedLicense.order_item_id == OrderItem.id)
        .join(Order, OrderItem.order_id == Order.id)
        .join(Product, OrderItem.product_id == Product.id)
        .filter(Order.user_id == user_id, Order.payment_status == 'paid')
        .order_by(GeneratedLicense.generated_at.desc())
        .all()
    )

    result = []
    for lic in licenses:
        order_item = lic.order_item
        product = order_item.product if order_item else None
        license_name = order_item.license.name if order_item and order_item.license else 'License'

        result.append({
            'license_id': lic.id,
            'product_name': product.name if product else 'Unknown',
            'product_type': product.product_type if product else '—',
            'license_type': license_name,
            'pdf_filename': os.path.basename(lic.pdf_path) if lic.pdf_path else None,
            'has_pdf': bool(lic.pdf_path and os.path.exists(
                os.path.join(current_app.root_path, lic.pdf_path)
            )),
            'generated_at': lic.generated_at.strftime('%d %b %Y') if lic.generated_at else '—',
            'order_date': order_item.order.created_at.strftime('%d %b %Y') if order_item and order_item.order else '—',
        })

    return jsonify({'licenses': result})


# ═══════════════════════════════════════════════════════════════
#  API: USER PROFILE (GET & PUT)
# ═══════════════════════════════════════════════════════════════

@bp.route('/api/user/profile', methods=['GET'])
def api_get_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'username': user.username,
        'email': user.email,
        'is_admin': user.is_admin,
        'joined': user.created_at.strftime('%d %b %Y') if user.created_at else '—',
        'last_login': user.last_login.strftime('%d %b %Y, %I:%M %p') if user.last_login else 'Never',
    })


@bp.route('/api/user/profile', methods=['PUT'])
def api_update_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    new_username = data.get('username', '').strip()
    new_email = data.get('email', '').strip().lower()

    errors = []

    # Validate username
    if new_username:
        if len(new_username) < 3:
            errors.append('Username must be at least 3 characters')
        elif len(new_username) > 30:
            errors.append('Username must be at most 30 characters')
        else:
            existing = User.query.filter(
                db.func.lower(User.username) == new_username.lower(),
                User.id != user_id
            ).first()
            if existing:
                errors.append('Username is already taken')

    # Validate email
    if new_email:
        if '@' not in new_email or '.' not in new_email:
            errors.append('Invalid email address')
        else:
            existing = User.query.filter(
                db.func.lower(User.email) == new_email,
                User.id != user_id
            ).first()
            if existing:
                errors.append('Email is already registered')

    if errors:
        return jsonify({'error': '. '.join(errors)}), 400

    # Apply changes
    changed = False
    if new_username and new_username != user.username:
        user.username = new_username
        changed = True
    if new_email and new_email != user.email.lower():
        user.email = new_email
        changed = True

    if not changed:
        return jsonify({'message': 'No changes made', 'user': {
            'username': user.username,
            'email': user.email,
        }})

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Profile updated successfully',
        'user': {
            'username': user.username,
            'email': user.email,
        },
    })




@bp.route('/api/user/change-password', methods=['PUT'])
def api_change_password():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'error': 'Both current and new password are required'}), 400

    if not check_password_hash(user.password_hash, current_password):
        return jsonify({'error': 'Current password is incorrect'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Password changed successfully'
    })


# =====================Download=========
@bp.route('/download/<int:product_id>')
@login_required
def download_product(product_id):
    user = get_current_user()

    # Verify purchase
    order_item = (
        OrderItem.query.join(Order)
        .filter(Order.user_id == user.id, Order.payment_status == 'paid',
                OrderItem.product_id == product_id)
        .first()
    )
    if not order_item:
        flash('You have not purchased this product', 'error')
        return redirect(url_for('dashboard.dashboard'))

    product = Product.query.get(product_id)
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('dashboard.dashboard'))

    # Get the stored file path from DB
    file_path = None

    if product.product_type == 'beat':
        detail = BeatDetail.query.filter_by(product_id=product_id).first()
        if detail:
            # Prefer WAV, fall back to MP3
            file_path = detail.wav_file or detail.mp3_file

    elif product.product_type == 'preset':
        preset = VocalPreset.query.filter_by(product_id=product_id).first()
        if preset:
            file_path = preset.preset_zip

    elif product.product_type == 'pack':
        pack = BeatPack.query.filter_by(product_id=product_id).first()
        if pack:
            file_path = pack.zip_path

    if not file_path:
        flash('Download file not available', 'error')
        return redirect(url_for('dashboard.dashboard'))

    # file_path from DB looks like: "data/wav/beatname_beat.wav"
    # Files live at: static/data/wav/beatname_beat.wav
    abs_path = os.path.join(current_app.root_path, 'static', file_path)

    if not os.path.exists(abs_path):
        # Fallback: try DATA_DIR config directly
        data_dir = current_app.config.get('DATA_DIR')
        if data_dir:
            # Strip leading "data/" to get relative subfolder path
            relative = file_path
            if relative.startswith('data/'):
                relative = relative[5:]  # "data/wav/x.wav" → "wav/x.wav"
            abs_path = os.path.join(data_dir, relative)

    if not os.path.exists(abs_path):
        logger.error("Download file not found: %s (tried static and DATA_DIR)", file_path)
        flash('File not found on disk', 'error')
        return redirect(url_for('dashboard.dashboard'))

    track_download(user.id, product_id)

    return send_file(abs_path, as_attachment=True)


@bp.route('/download/license/<int:license_id>')
@login_required
def download_license(license_id):
    user = get_current_user()

    lic = GeneratedLicense.query.get(license_id)
    if not lic:
        flash('License not found', 'error')
        return redirect(url_for('dashboard.dashboard'))

    order_item = OrderItem.query.get(lic.order_item_id) if lic.order_item_id else None
    if not order_item:
        flash('License not associated with an order', 'error')
        return redirect(url_for('dashboard.dashboard'))

    order = Order.query.get(order_item.order_id)
    if not order or order.user_id != user.id:
        flash('You do not have access to this license', 'error')
        return redirect(url_for('dashboard.dashboard'))

    if not lic.pdf_path:
        flash('No PDF available for this license', 'error')
        return redirect(url_for('dashboard.dashboard'))

    # FIX: Add 'static' to the path
    abs_path = os.path.join(current_app.root_path, 'static', lic.pdf_path)

    if not os.path.exists(abs_path):
        logger.error("License PDF not found at: %s", abs_path)
        flash('License PDF file not found', 'error')
        return redirect(url_for('dashboard.dashboard'))

    return send_file(abs_path, as_attachment=True)

import zipfile
import io

@bp.route('/download/order/<int:order_id>')
@login_required
def download_order_files(order_id):
    user = get_current_user()

    order = Order.query.filter_by(id=order_id, user_id=user.id).first_or_404()

    if order.payment_status != 'paid':
        flash('Order not paid', 'error')
        return redirect(url_for('dashboard.dashboard'))

    files_to_zip = []

    for item in order.items:
        product = item.product
        if not product:
            continue

        file_path = None

        if product.product_type == 'beat':
            detail = BeatDetail.query.filter_by(product_id=product.id).first()
            if detail:
                file_path = detail.wav_file or detail.mp3_file

        elif product.product_type == 'preset':
            preset = VocalPreset.query.filter_by(product_id=product.id).first()
            if preset:
                file_path = preset.preset_zip

        elif product.product_type == 'pack':
            pack = BeatPack.query.filter_by(product_id=product.id).first()
            if pack:
                file_path = pack.zip_path

        if file_path:
            abs_path = os.path.join(current_app.root_path, 'static', file_path)
            if os.path.exists(abs_path):
                display_name = os.path.basename(file_path)
                files_to_zip.append((abs_path, display_name))

    if not files_to_zip:
        flash('No downloadable files found for this order', 'error')
        return redirect(url_for('dashboard.dashboard'))

    # If only one file, serve it directly
    if len(files_to_zip) == 1:
        track_download(user.id, order.items[0].product_id)
        return send_file(files_to_zip[0][0], as_attachment=True)

    # Multiple files → create ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for abs_path, display_name in files_to_zip:
            zf.write(abs_path, display_name)

    zip_buffer.seek(0)

    # Track downloads for all items
    for item in order.items:
        if item.product:
            track_download(user.id, item.product_id)

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f'XLoveBeats_Order_{order.id}.zip',
        mimetype='application/zip'
    )


@bp.route('/download/flp/<int:product_id>')
@login_required
def download_flp(product_id):
    user = get_current_user()

    # Get ALL paid order items for this product
    paid_items = (
        OrderItem.query.join(Order)
        .filter(
            Order.user_id == user.id,
            Order.payment_status == 'paid',
            OrderItem.product_id == product_id
        )
        .all()
    )

    if not paid_items:
        flash('You have not purchased this product', 'error')
        return redirect(url_for('dashboard.dashboard'))

    # Check if ANY purchased item has Premium or Exclusive license
    has_access = False
    for item in paid_items:
        # Check from order item license
        if item.license and item.license.name:
            if item.license.name.strip().lower() in ('premium', 'exclusive'):
                has_access = True
                break

        # Fallback: check from GeneratedLicense table
        gen_lic = GeneratedLicense.query.filter_by(order_item_id=item.id).first()
        if gen_lic and gen_lic.license_type:
            if gen_lic.license_type.strip().lower() in ('premium', 'exclusive'):
                has_access = True
                break

    if not has_access:
        flash('FLP files are available for Premium and Exclusive licenses only', 'error')
        return redirect(url_for('dashboard.dashboard'))

    product = Product.query.get(product_id)
    if not product or product.product_type != 'beat':
        flash('Product not found', 'error')
        return redirect(url_for('dashboard.dashboard'))

    detail = BeatDetail.query.filter_by(product_id=product_id).first()
    if not detail or not detail.project_file:
        flash('Project file not available for this beat', 'error')
        return redirect(url_for('dashboard.dashboard'))

    abs_path = os.path.join(current_app.root_path, 'static', detail.project_file)
    if not os.path.exists(abs_path):
        data_dir = current_app.config.get('DATA_DIR')
        if data_dir:
            relative = detail.project_file
            if relative.startswith('data/'):
                relative = relative[5:]
            abs_path = os.path.join(data_dir, relative)

    if not os.path.exists(abs_path):
        logger.error("Project file not found: %s", detail.project_file)
        flash('Project file not found on disk', 'error')
        return redirect(url_for('dashboard.dashboard'))

    track_download(user.id, product_id)

    return send_file(abs_path, as_attachment=True)