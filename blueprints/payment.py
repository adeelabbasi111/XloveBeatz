import logging
import os
import time
import hashlib
import hmac
from datetime import datetime

from flask import Blueprint, request, jsonify, render_template, session, current_app, redirect, url_for, flash, send_file
from helpers.models import Product, License, BeatLicensePrice, Cart, db, Order, OrderItem, User, GeneratedLicense, BeatDetail
from helpers.utils import get_current_user, login_required
from helpers.services import create_order, add_order_item, mark_order_paid, clear_cart
from helpers.license_generator import BeatLicenseGenerator
from helpers.models import DiscountCode


logger = logging.getLogger(__name__)
bp = Blueprint('payment', __name__)

# ⚠️ If True, bypasses Razorpay/PayPal completely (for local dev without valid keys)
TEST_MODE_PAYMENT = False


# ═══════════════════════════════════════════════════════════════
#  LICENSE GENERATION
# ═══════════════════════════════════════════════════════════════

def _generate_licenses_for_order(order):
    """DEPRECATED: Generate license PDFs for each beat item in the order."""

    generator = BeatLicenseGenerator()
    user = User.query.get(order.user_id) if order.user_id else None
    effective_date = order.created_at.strftime('%d-%m-%Y') if order.created_at else datetime.now().strftime('%d-%m-%Y')

    for item in order.items:
        product = item.product
        if not product or product.product_type != 'beat':
            continue

        if not item.license:
            continue

        license_type = item.license.name.lower()
        if license_type not in ('basic', 'premium', 'exclusive'):
            continue

        licensee_name = user.username if user else (order.email or 'Customer')
        beat_name = product.name
        price_paid = item.price_paid_cents / 100 if item.price_paid_cents else 0

        # Get beat details for specs
        beat_detail = BeatDetail.query.filter_by(product_id=product.id).first()

        license_data = {
            'licensee_legal_name': licensee_name,
            'artist_stage_name': '',
            'beat_name': beat_name,
            'effective_date': effective_date,
            'beat_price': str(int(price_paid)),
            'order_id': str(order.id),
            'transaction_id': order.transaction_id or '',
            'buyer_email': user.email if user else (order.email or ''),
            'bpm': beat_detail.bpm if beat_detail else None,
            'musical_key': beat_detail.musical_key if beat_detail else None,
            'genre': beat_detail.genre if beat_detail else None,
            'duration': beat_detail.duration if beat_detail else None,
        }

        try:
            if license_type == 'basic':
                story = generator.generate_basic_license(license_data)
            elif license_type == 'premium':
                story = generator.generate_premium_license(license_data)
            elif license_type == 'exclusive':
                story = generator.generate_exclusive_license(license_data)
            else:
                continue

            output_dir = os.path.join(current_app.root_path, 'static', 'data', 'licenses')
            os.makedirs(output_dir, exist_ok=True)

            safe_name = licensee_name.replace(' ', '_').replace('/', '_')
            safe_beat = beat_name.replace(' ', '_').replace('/', '_')
            filename = f"{safe_name}_{item.license.name}_{safe_beat}"

            generator.save_license(story, filename, output_dir)
            db_path = f"data/licenses/{filename}.pdf"

            gen_lic = GeneratedLicense(
                order_item_id=item.id,
                buyer_name=licensee_name,
                beat_name=beat_name,
                license_type=item.license.name,
                pdf_path=db_path,
            )
            db.session.add(gen_lic)
            logger.info("License generated: %s (%s) for order %s", filename, license_type, order.id)

        except Exception as e:
            logger.error("License generation failed for %s - %s: %s", licensee_name, beat_name, e)

    db.session.commit()


# ═══════════════════════════════════════════════════════════════
#  RAZORPAY ORDER CREATION
# ═══════════════════════════════════════════════════════════════

import razorpay
import requests

@bp.route('/api/create-razorpay-order', methods=['POST'])
@login_required
def create_razorpay_order():
    data = request.json or {}
    cart_items = data.get('items', [])
    coupon_code = (data.get('coupon_code') or '').strip().upper()

    # Block foreign users from Razorpay (INR-only gateway)
    from helpers.geo import get_geo_pricing
    geo_info = get_geo_pricing()
    if geo_info['is_foreign']:
        return jsonify({"error": "Razorpay is not available for international users. Please use PayPal."}), 400

    if not cart_items:
        return jsonify({"error": "Cart is empty"}), 400

    total_cents, line_items = 0, []
    for item in cart_items:
        product = Product.query.get(item.get('id'))
        if not product:
            continue
        item_type = item.get('type')
        license_type = item.get('license', 'basic')
        price_cents, name = 0, ""

        if item_type == 'beat':
            lic = License.query.filter_by(name=license_type.capitalize()).first()
            if lic:
                lp = BeatLicensePrice.query.filter_by(beat_id=product.id, license_id=lic.id).first()
                if lp:
                    price_cents = lp.price_cents
                    name = f"{product.name} ({lic.name} License)"
            if price_cents == 0:
                price_cents = product.price_cents
                name = product.name
        elif item_type in ('pack', 'preset'):
            price_cents = product.price_cents
            name = product.name

        if price_cents > 0:
            total_cents += price_cents
            line_items.append({
                'product_id': product.id, 'name': name,
                'price_cents': price_cents,
                'license_type': license_type if item_type == 'beat' else None,
            })

    if total_cents <= 0:
        return jsonify({"error": "Invalid items"}), 400

    discount_cents = 0
    applied_coupon = None

    if coupon_code:
        coupon = DiscountCode.query.filter_by(code=coupon_code).first()
        if coupon and coupon.is_active:
            expired = coupon.expires_at and coupon.expires_at < datetime.utcnow()
            maxed = coupon.max_uses > 0 and coupon.used_count >= coupon.max_uses
            min_not_met = coupon.min_order_cents > 0 and total_cents < coupon.min_order_cents
            if not expired and not maxed and not min_not_met:
                if coupon.discount_type == 'percentage':
                    raw_discount = int(total_cents * coupon.discount_value / 100)
                    cap = coupon.max_discount_cents if coupon.max_discount_cents > 0 else raw_discount
                    discount_cents = min(raw_discount, cap)
                elif coupon.discount_type == 'fixed':
                    discount_cents = min(coupon.discount_value * 100, total_cents)
                applied_coupon = coupon

    final_cents = max(100, total_cents - discount_cents)

    user = get_current_user()

    try:
        order = create_order(
            user_id=user.id,
            total_cents=final_cents,
            payment_method='razorpay',
            email=user.email,
        )

        if applied_coupon:
            order.coupon_code = applied_coupon.code
            order.discount_cents = discount_cents
            applied_coupon.used_count += 1

        for li in line_items:
            lic_id = None
            if li['license_type']:
                lic = License.query.filter_by(name=li['license_type'].capitalize()).first()
                if lic:
                    lic_id = lic.id
            add_order_item(order.id, li['product_id'], li['price_cents'], lic_id)

        db.session.commit()

        if TEST_MODE_PAYMENT:
            return jsonify({
                "test_mode_success": True,
                "db_order_id": order.id,
            })

        rzp_key = current_app.config.get('RAZORPAY_KEY_ID', '')
        rzp_secret = current_app.config.get('RAZORPAY_KEY_SECRET', '')
        client = razorpay.Client(auth=(rzp_key, rzp_secret))
        
        rzp_order = client.order.create({
            "amount": final_cents,
            "currency": "INR",
            "receipt": f"order_xlb_{order.id}",
            "notes": {"db_order_id": str(order.id)},
        })

        return jsonify({
            "order_id": rzp_order['id'],
            "db_order_id": order.id,
            "amount": rzp_order['amount'],
            "currency": rzp_order['currency'],
            "key_id": rzp_key,
        })
    except Exception as e:
        logger.error("Razorpay order creation failed: %s", e)
        db.session.rollback()
        return jsonify({"error": "Order creation error"}), 500


@bp.route('/api/verify-razorpay-payment', methods=['POST'])
@login_required
def verify_razorpay_payment():
    data = request.json or {}
    db_order_id = data.get('db_order_id')
    
    if TEST_MODE_PAYMENT:
        mark_order_paid(db_order_id, f"test_rzp_{db_order_id}")
        _clear_user_cart()
        return jsonify({"status": "success", "order_id": db_order_id})

    rzp_pay_id = data.get('razorpay_payment_id')
    rzp_order_id = data.get('razorpay_order_id')
    rzp_sig = data.get('razorpay_signature')

    rzp_secret = current_app.config.get('RAZORPAY_KEY_SECRET', '')

    expected_sig = hmac.new(
        rzp_secret.encode('utf-8'),
        f"{rzp_order_id}|{rzp_pay_id}".encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if expected_sig == rzp_sig:
        mark_order_paid(db_order_id, rzp_pay_id)
        _clear_user_cart()
        return jsonify({"status": "success", "order_id": db_order_id})
    else:
        logger.error("Invalid Razorpay signature for DB order %s", db_order_id)
        return jsonify({"status": "failed", "error": "Invalid signature"}), 400


# ═══════════════════════════════════════════════════════════════
#  PAYPAL ORDER CREATION
# ═══════════════════════════════════════════════════════════════

def get_paypal_access_token():
    client_id = current_app.config.get('PAYPAL_CLIENT_ID', '')
    client_secret = current_app.config.get('PAYPAL_CLIENT_SECRET', '')
    mode = current_app.config.get('PAYPAL_MODE', 'sandbox')
    base_url = "https://api-m.sandbox.paypal.com" if mode == 'sandbox' else "https://api-m.paypal.com"
    
    url = f"{base_url}/v1/oauth2/token"
    auth = (client_id, client_secret)
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    data = {"grant_type": "client_credentials"}
    
    resp = requests.post(url, auth=auth, headers=headers, data=data)
    if resp.status_code == 200:
        return resp.json().get('access_token')
    else:
        logger.error("Failed to get PayPal token: %s", resp.text)
        return None

@bp.route('/api/create-paypal-order', methods=['POST'])
@login_required
def create_paypal_order():
    data = request.json or {}
    cart_items = data.get('items', [])
    coupon_code = (data.get('coupon_code') or '').strip().upper()

    if not cart_items:
        return jsonify({"error": "Cart is empty"}), 400

    total_cents, line_items = 0, []
    # (Same item loop as razorpay)
    for item in cart_items:
        product = Product.query.get(item.get('id'))
        if not product:
            continue
        item_type = item.get('type')
        license_type = item.get('license', 'basic')
        price_cents, name = 0, ""

        if item_type == 'beat':
            lic = License.query.filter_by(name=license_type.capitalize()).first()
            if lic:
                lp = BeatLicensePrice.query.filter_by(beat_id=product.id, license_id=lic.id).first()
                if lp:
                    price_cents = lp.price_cents
                    name = f"{product.name} ({lic.name} License)"
            if price_cents == 0:
                price_cents = product.price_cents
                name = product.name
        elif item_type in ('pack', 'preset'):
            price_cents = product.price_cents
            name = product.name

        if price_cents > 0:
            total_cents += price_cents
            line_items.append({
                'product_id': product.id, 'name': name,
                'price_cents': price_cents,
                'license_type': license_type if item_type == 'beat' else None,
            })

    if total_cents <= 0:
        return jsonify({"error": "Invalid items"}), 400

    discount_cents = 0
    applied_coupon = None

    if coupon_code:
        coupon = DiscountCode.query.filter_by(code=coupon_code).first()
        if coupon and coupon.is_active:
            expired = coupon.expires_at and coupon.expires_at < datetime.utcnow()
            maxed = coupon.max_uses > 0 and coupon.used_count >= coupon.max_uses
            min_not_met = coupon.min_order_cents > 0 and total_cents < coupon.min_order_cents
            if not expired and not maxed and not min_not_met:
                if coupon.discount_type == 'percentage':
                    raw_discount = int(total_cents * coupon.discount_value / 100)
                    cap = coupon.max_discount_cents if coupon.max_discount_cents > 0 else raw_discount
                    discount_cents = min(raw_discount, cap)
                elif coupon.discount_type == 'fixed':
                    discount_cents = min(coupon.discount_value * 100, total_cents)
                applied_coupon = coupon

    final_cents = max(100, total_cents - discount_cents)
    
    # Check if user is foreign (prices already in USD from geo-pricing)
    from helpers.geo import get_geo_pricing
    geo_info = get_geo_pricing()
    
    rate = current_app.config.get('USD_INR_EXCHANGE_RATE', 85.0)
    if geo_info['is_foreign']:
        # Apply the geo multiplier to reflect the TRUE Indian Rupees equivalent in the database
        multiplier = geo_info['multiplier']
        final_cents = int(final_cents * multiplier)
        discount_cents = int(discount_cents * multiplier)
        for li in line_items:
            li['price_cents'] = int(li['price_cents'] * multiplier)

    final_inr = final_cents / 100.0
    usd_amount = round(final_inr / rate, 2)
    
    if usd_amount < 0.50:
        usd_amount = 0.50 # minimum for paypal typically

    user = get_current_user()

    try:
        order = create_order(
            user_id=user.id,
            total_cents=final_cents,
            payment_method='paypal',
            email=user.email,
        )
        order.currency = 'USD'
        if applied_coupon:
            order.coupon_code = applied_coupon.code
            order.discount_cents = discount_cents
            applied_coupon.used_count += 1

        for li in line_items:
            lic_id = None
            if li['license_type']:
                lic = License.query.filter_by(name=li['license_type'].capitalize()).first()
                if lic:
                    lic_id = lic.id
            add_order_item(order.id, li['product_id'], li['price_cents'], lic_id)

        db.session.commit()

        if TEST_MODE_PAYMENT:
            return jsonify({
                "test_mode_success": True,
                "db_order_id": order.id,
            })

        token = get_paypal_access_token()
        if not token:
            return jsonify({"error": "Failed to authenticate with PayPal"}), 500

        mode = current_app.config.get('PAYPAL_MODE', 'sandbox')
        base_url = "https://api-m.sandbox.paypal.com" if mode == 'sandbox' else "https://api-m.paypal.com"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": f"order_xlb_{order.id}",
                "amount": {
                    "currency_code": "USD",
                    "value": f"{usd_amount:.2f}"
                }
            }]
        }

        resp = requests.post(f"{base_url}/v2/checkout/orders", headers=headers, json=payload)
        
        if resp.status_code in (200, 201):
            paypal_data = resp.json()
            return jsonify({
                "paypal_order_id": paypal_data['id'],
                "db_order_id": order.id,
                "usd_amount": usd_amount
            })
        else:
            logger.error("PayPal order creation failed: %s", resp.text)
            return jsonify({"error": "PayPal order creation error"}), 500

    except Exception as e:
        logger.error("PayPal order creation failed: %s", e)
        db.session.rollback()
        return jsonify({"error": "Order creation error"}), 500


@bp.route('/api/capture-paypal-order', methods=['POST'])
@login_required
def capture_paypal_order():
    data = request.json or {}
    paypal_order_id = data.get('paypal_order_id')
    db_order_id = data.get('db_order_id')

    if TEST_MODE_PAYMENT:
        mark_order_paid(db_order_id, f"test_paypal_{db_order_id}")
        _clear_user_cart()
        return jsonify({"status": "success", "order_id": db_order_id})

    token = get_paypal_access_token()
    if not token:
        return jsonify({"error": "PayPal auth failed"}), 500

    mode = current_app.config.get('PAYPAL_MODE', 'sandbox')
    base_url = "https://api-m.sandbox.paypal.com" if mode == 'sandbox' else "https://api-m.paypal.com"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    resp = requests.post(f"{base_url}/v2/checkout/orders/{paypal_order_id}/capture", headers=headers)
    
    if resp.status_code in (200, 201):
        cap_data = resp.json()
        if cap_data.get('status') == 'COMPLETED':
            transaction_id = cap_data['purchase_units'][0]['payments']['captures'][0]['id']
            mark_order_paid(db_order_id, transaction_id)
            _clear_user_cart()
            return jsonify({"status": "success", "order_id": db_order_id})
        else:
            return jsonify({"status": "failed", "error": "Order not completed"}), 400
    else:
        logger.error("PayPal capture failed: %s", resp.text)
        return jsonify({"status": "failed", "error": "Capture failed"}), 400


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _clear_user_cart():
    """Clear cart after successful payment."""
    user = get_current_user()
    if user:
        cart = Cart.query.filter_by(user_id=user.id).first()
    elif 'session_id' in session:
        cart = Cart.query.filter_by(session_id=session['session_id']).first()
    else:
        cart = None
    if cart:
        clear_cart(cart.id)


# ═══════════════════════════════════════════════════════════════
#  SUCCESS PAGE
# ═══════════════════════════════════════════════════════════════

@bp.route('/payment/success/<int:order_id>')
@login_required
def payment_success(order_id):
    user = get_current_user()

    order = (
        Order.query
        .options(
            db.joinedload(Order.items).joinedload(OrderItem.product),
            db.joinedload(Order.items).joinedload(OrderItem.license),
        )
        .filter_by(id=order_id, user_id=user.id)
        .first_or_404()
    )

    if order.payment_status != 'paid':
        flash('This order has not been paid yet', 'error')
        return redirect(url_for('dashboard.dashboard'))

    return render_template('payment_success.html', order=order, user=user)


# ═══════════════════════════════════════════════════════════════
#  DOWNLOAD ALL FILES (ZIP)
# ═══════════════════════════════════════════════════════════════

import zipfile
import io
from helpers.models import BeatDetail, VocalPreset, BeatPack

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
        return redirect(url_for('payment.payment_success', order_id=order_id))

    # Single file → serve directly
    if len(files_to_zip) == 1:
        return send_file(files_to_zip[0][0], as_attachment=True)

    # Multiple files → ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for abs_path, display_name in files_to_zip:
            zf.write(abs_path, display_name)

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f'XLoveBeats_Order_{order.id}.zip',
        mimetype='application/zip'
    )