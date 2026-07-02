from flask import (
    Blueprint, render_template, flash, redirect,
    url_for, send_from_directory,send_file, current_app, request, jsonify, session,
)
from helpers.models import (
    db, Order, OrderItem, Download, Product,
    BeatDetail, VocalPreset, User, GeneratedLicense,
)
from helpers.utils import login_required, get_current_user
from helpers.services import get_user_orders, track_download
import os

bp = Blueprint('dashboard', __name__)


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD PAGE
# ═══════════════════════════════════════════════════════════════

@bp.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    orders = get_user_orders(user.id)
    downloads = Download.query.filter_by(user_id=user.id).all()

    purchased_ids = set()
    for order in orders:
        if order.payment_status == 'paid':
            for item in order.items:
                purchased_ids.add(item.product_id)

    purchased = Product.query.filter(Product.id.in_(purchased_ids)).all() if purchased_ids else []

    return render_template(
        'dashboard.html', user=user, orders=orders,
        downloads=downloads, purchased_products=purchased,
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
            'price_paid': (item.price_cents or 0) / 100,
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


# ═══════════════════════════════════════════════════════════════
#  DOWNLOAD: PRODUCT FILES
# ═══════════════════════════════════════════════════════════════

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

    # Determine file to serve
    filename = None
    subfolder = None

    if product.product_type == 'beat':
        detail = BeatDetail.query.filter_by(product_id=product_id).first()
        if detail:
            filename = detail.wav_file or detail.mp3_file
            if filename:
                subfolder = 'wav' if detail.wav_file else 'mp3'

    elif product.product_type == 'preset':
        preset = VocalPreset.query.filter_by(product_id=product_id).first()
        if preset and preset.preset_zip:
            filename = preset.preset_zip
            subfolder = 'presets'

    elif product.product_type == 'pack':
        flash('Beat packs: download individual beats from the pack page', 'info')
        return redirect(url_for('dashboard.dashboard'))

    if not filename:
        flash('Download file not available', 'error')
        return redirect(url_for('dashboard.dashboard'))

    track_download(user.id, product_id)

    # Serve from data directory
    data_dir = current_app.config.get('DATA_DIR', os.path.join(current_app.root_path, 'static', 'data'))
    if subfolder:
        file_dir = os.path.join(data_dir, subfolder)
    else:
        file_dir = data_dir

    abs_path = os.path.join(file_dir, os.path.basename(filename))
    if not os.path.exists(abs_path):
        # Fallback: try static directory
        abs_path = os.path.join(current_app.root_path, 'static', filename)

    if not os.path.exists(abs_path):
        flash('File not found on disk', 'error')
        return redirect(url_for('dashboard.dashboard'))

    return send_file(abs_path, as_attachment=True)


# ═══════════════════════════════════════════════════════════════
#  DOWNLOAD: LICENSE PDF
# ═══════════════════════════════════════════════════════════════

@bp.route('/download/license/<int:license_id>')
@login_required
def download_license(license_id):
    user = get_current_user()

    lic = GeneratedLicense.query.get(license_id)
    if not lic:
        flash('License not found', 'error')
        return redirect(url_for('dashboard.dashboard'))

    # Verify ownership
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

    abs_path = os.path.join(current_app.root_path, lic.pdf_path)
    if not os.path.exists(abs_path):
        flash('License PDF file not found', 'error')
        return redirect(url_for('dashboard.dashboard'))

    return send_file(abs_path, as_attachment=True)